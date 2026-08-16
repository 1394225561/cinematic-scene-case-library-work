from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


DEFAULT_URL = (
    "https://higgsfield.ai/generate"
    "?projectId=3caa2f3a-52b5-4293-9237-0c8f76c7158a"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "reports" / "probe-page.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36 CodexPromptCorpusProbe/1.0"
)
MEDIA_SUFFIXES = {
    ".avif",
    ".gif",
    ".jpeg",
    ".jpg",
    ".m3u8",
    ".mov",
    ".mp3",
    ".mp4",
    ".png",
    ".svg",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
}
FIRST_PARTY_SCRIPT_HOSTS = {"higgsfield.ai", "assets.higgsfield.ai"}
SEARCH_TERMS = (
    "3caa2f3a-52b5-4293-9237-0c8f76c7158a",
    "bf48d11b-4b06-4429-84fa-3822399d5418",
    "projectId",
    "project_id",
    "folderId",
    "folder_id",
    "assetId",
    "asset_id",
    "graphql",
    "trpc",
    "/api/",
)
ABSOLUTE_URL_RE = re.compile(r"https?://[^\"'`\\\s]+")
QUOTED_PATH_RE = re.compile(r"[\"'`](/[^\"'`\\\s]{2,300})[\"'`]")


class ResourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scripts: list[str] = []
        self.preloads: list[str] = []
        self.title_parts: list[str] = []
        self._inside_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"] or "")
        if tag == "link" and values.get("href"):
            relation = (values.get("rel") or "").lower()
            if "preload" in relation or "modulepreload" in relation:
                self.preloads.append(values["href"] or "")
        if tag == "title":
            self._inside_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self.title_parts.append(data)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_text(url: str, *, timeout: float, max_bytes: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/javascript,application/json;q=0.9,*/*;q=0.1",
            "User-Agent": USER_AGENT,
        },
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError(f"response exceeded byte limit ({max_bytes}) for {url}")
        charset = response.headers.get_content_charset() or "utf-8"
        text = body.decode(charset, errors="replace")
        return {
            "requested_url": url,
            "final_url": response.geturl(),
            "status": response.status,
            "content_type": response.headers.get_content_type(),
            "content_length_header": response.headers.get("Content-Length"),
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "text": text,
        }


def context_matches(
    text: str,
    terms: tuple[str, ...],
    radius: int = 180,
    per_term_limit: int = 20,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    lowered = text.lower()
    for term in terms:
        start = 0
        term_matches = 0
        term_lower = term.lower()
        while term_matches < per_term_limit:
            index = lowered.find(term_lower, start)
            if index < 0:
                break
            matches.append(
                {
                    "term": term,
                    "offset": index,
                    "context": text[max(0, index - radius) : index + len(term) + radius],
                }
            )
            term_matches += 1
            start = index + len(term)
    return matches


def looks_like_endpoint(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    path = parsed.path.lower()
    if Path(path).suffix in MEDIA_SUFFIXES:
        return False
    return any(term in value.lower() for term in ("api", "graphql", "trpc", "project", "folder", "asset"))


def is_first_party_script(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.hostname in FIRST_PARTY_SCRIPT_HOSTS and parsed.path.lower().endswith(".js")


def endpoint_candidates(text: str, base_url: str) -> list[str]:
    values: set[str] = set()
    for match in ABSOLUTE_URL_RE.findall(text):
        value = match.rstrip(")]},;:")
        if looks_like_endpoint(value):
            values.add(value)
    for match in QUOTED_PATH_RE.findall(text):
        value = urllib.parse.urljoin(base_url, match)
        if looks_like_endpoint(value):
            values.add(value)
    return sorted(values)[:500]


def scan_script(
    script_url: str,
    *,
    timeout: float,
    max_bytes: int,
) -> dict[str, Any]:
    result = fetch_text(script_url, timeout=timeout, max_bytes=max_bytes)
    text = result.pop("text")
    return {
        **result,
        "matches": context_matches(text, SEARCH_TERMS),
        "endpoint_candidates": endpoint_candidates(text, result["final_url"]),
    }


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def write_text_atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe a public Higgsfield project page without downloading media."
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-html-bytes", type=int, default=8_000_000)
    parser.add_argument("--scan-scripts", action="store_true")
    parser.add_argument("--max-scripts", type=int, default=20)
    parser.add_argument("--max-script-bytes", type=int, default=8_000_000)
    parser.add_argument("--request-delay", type=float, default=0.25)
    parser.add_argument(
        "--save-response-text",
        type=Path,
        help="Optionally save the primary non-media text response for local inspection.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {
        "schema_version": 1,
        "started_at": utc_now(),
        "target_url": args.url,
        "dependency_policy": "python-standard-library-only",
        "media_downloaded": False,
        "page": None,
        "script_scans": [],
        "errors": [],
    }

    try:
        page_result = fetch_text(
            args.url,
            timeout=args.timeout,
            max_bytes=args.max_html_bytes,
        )
    except (OSError, ValueError, urllib.error.URLError) as error:
        report["errors"].append({"url": args.url, "error": repr(error)})
        report["finished_at"] = utc_now()
        write_json_atomic(args.output, report)
        print(f"Page probe failed: {error}", file=sys.stderr)
        print(f"Report: {args.output}", file=sys.stderr)
        return 1

    html_text = page_result.pop("text")
    if args.save_response_text:
        write_text_atomic(args.save_response_text, html_text)
        report["saved_response_text"] = str(args.save_response_text)
    parser = ResourceParser()
    parser.feed(html_text)
    script_urls = list(
        dict.fromkeys(urllib.parse.urljoin(page_result["final_url"], src) for src in parser.scripts)
    )
    preload_urls = list(
        dict.fromkeys(urllib.parse.urljoin(page_result["final_url"], href) for href in parser.preloads)
    )
    report["page"] = {
        **page_result,
        "title": "".join(parser.title_parts).strip(),
        "script_count": len(script_urls),
        "script_urls": script_urls,
        "preload_urls": preload_urls,
        "matches": context_matches(html_text, SEARCH_TERMS),
        "endpoint_candidates": endpoint_candidates(html_text, page_result["final_url"]),
    }

    if args.scan_scripts:
        script_candidates = list(
            dict.fromkeys(
                url
                for url in [*script_urls, *preload_urls]
                if is_first_party_script(url)
            )
        )
        report["page"]["script_scan_candidates"] = script_candidates
        for script_url in script_candidates[: args.max_scripts]:
            try:
                report["script_scans"].append(
                    scan_script(
                        script_url,
                        timeout=args.timeout,
                        max_bytes=args.max_script_bytes,
                    )
                )
            except (OSError, ValueError, urllib.error.URLError) as error:
                report["errors"].append({"url": script_url, "error": repr(error)})
                print(f"Script probe failed: {script_url}: {error}", file=sys.stderr)
            time.sleep(max(0.0, args.request_delay))

    report["finished_at"] = utc_now()
    write_json_atomic(args.output, report)
    print(
        json.dumps(
            {
                "status": report["page"]["status"],
                "page_bytes": report["page"]["bytes"],
                "script_count": report["page"]["script_count"],
                "page_matches": len(report["page"]["matches"]),
                "script_scans": len(report["script_scans"]),
                "errors": len(report["errors"]),
                "report": str(args.output),
            },
            indent=2,
        )
    )
    return 0 if not report["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
