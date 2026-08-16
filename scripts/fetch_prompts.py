from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from probe_higgsfield import fetch_text, utc_now, write_json_atomic, write_text_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_ID = "3caa2f3a-52b5-4293-9237-0c8f76c7158a"
DEFAULT_OUTPUT = WORK_ROOT / "data" / "reports" / "five-prompt-samples.json"
API_BASE = "https://fnf-api-gw.higgsfield.ai/fnf"
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def raw_output_path(folder_id: str, size: int) -> Path:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return WORK_ROOT / "data" / "raw" / "pages" / f"{run_id}-{folder_id}-size-{size}.json"


def build_url(folder_id: str, size: int, include_subfolders: bool, cursor: str | None) -> str:
    if not UUID_RE.fullmatch(folder_id):
        raise ValueError(f"folder ID is not a UUID: {folder_id}")
    query = {
        "include_subfolders": str(include_subfolders).lower(),
        "size": str(size),
    }
    if cursor:
        query["cursor"] = cursor
    return f"{API_BASE}/folders/{folder_id}/items/v2?{urllib.parse.urlencode(query)}"


def extract_record(
    item: Any,
    *,
    index: int,
    project_id: str,
    source_url: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(item, dict):
        return None, {"index": index, "reason": "item is not an object"}
    if item.get("type") != "job" or not isinstance(item.get("job"), dict):
        return None, {
            "index": index,
            "reason": "unsupported item type",
            "item_type": item.get("type"),
        }

    job = item["job"]
    params = job.get("params")
    if not isinstance(params, dict):
        return None, {
            "index": index,
            "asset_id": job.get("id"),
            "reason": "job params are missing or invalid",
        }
    prompt = params.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None, {
            "index": index,
            "asset_id": job.get("id"),
            "reason": "Prompt is empty or invalid",
        }
    asset_id = job.get("id")
    folder_id = job.get("folder_id")
    if not isinstance(asset_id, str) or not asset_id:
        return None, {"index": index, "reason": "asset ID is missing"}
    if not isinstance(folder_id, str) or not folder_id:
        return None, {
            "index": index,
            "asset_id": asset_id,
            "reason": "folder ID is missing",
        }

    results = job.get("results")
    raw_result = results.get("raw") if isinstance(results, dict) else None
    asset_type = raw_result.get("type") if isinstance(raw_result, dict) else None
    return (
        {
            "project_id": project_id,
            "folder_id": folder_id,
            "asset_id": asset_id,
            "asset_type": asset_type,
            "status": job.get("status"),
            "job_set_type": job.get("job_set_type"),
            "model": params.get("model"),
            "created_at_unix": job.get("created_at"),
            "width": params.get("width"),
            "height": params.get("height"),
            "duration_seconds": params.get("duration"),
            "resolution": params.get("resolution"),
            "prompt": prompt,
            "prompt_chars": len(prompt),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "source_endpoint": source_url,
            "source_item_index": index,
        },
        None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch public Higgsfield asset Prompts without downloading media."
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--folder-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--size", type=int, default=5)
    parser.add_argument(
        "--include-subfolders",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--cursor")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-response-bytes", type=int, default=25_000_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {
        "schema_version": 1,
        "started_at": utc_now(),
        "project_id": args.project_id,
        "folder_id": args.folder_id,
        "requested_size": args.size,
        "include_subfolders": args.include_subfolders,
        "cursor_requested": args.cursor,
        "media_downloaded": False,
        "records": [],
        "errors": [],
    }
    if not 1 <= args.size <= 100:
        report["errors"].append({"reason": "size must be between 1 and 100"})
        report["finished_at"] = utc_now()
        write_json_atomic(args.output, report)
        print("Invalid size; report written", file=sys.stderr)
        return 1

    try:
        source_url = build_url(
            args.folder_id,
            args.size,
            args.include_subfolders,
            args.cursor,
        )
        response = fetch_text(
            source_url,
            timeout=args.timeout,
            max_bytes=args.max_response_bytes,
        )
        response_text = response.pop("text")
        raw_path = args.raw_output or raw_output_path(args.folder_id, args.size)
        write_text_atomic(raw_path, response_text)
        report["source_endpoint"] = source_url
        report["raw_response"] = str(raw_path)
        report["http"] = response
        if response["content_type"] != "application/json":
            raise ValueError(f"unexpected Content-Type: {response['content_type']}")
        payload = json.loads(response_text)
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("response does not contain an items array")
        report["received_items"] = len(payload["items"])
        report["next_cursor"] = payload.get("cursor")
        for index, item in enumerate(payload["items"]):
            record, error = extract_record(
                item,
                index=index,
                project_id=args.project_id,
                source_url=source_url,
            )
            if record is not None:
                report["records"].append(record)
            if error is not None:
                report["errors"].append(error)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        urllib.error.URLError,
    ) as error:
        report["errors"].append({"reason": repr(error)})

    report["prompt_count"] = len(report["records"])
    if report["prompt_count"] != args.size:
        report["errors"].append(
            {
                "reason": "Prompt count does not match requested size",
                "requested_size": args.size,
                "prompt_count": report["prompt_count"],
            }
        )
    report["finished_at"] = utc_now()
    write_json_atomic(args.output, report)
    print(
        json.dumps(
            {
                "received_items": report.get("received_items", 0),
                "prompt_count": report["prompt_count"],
                "errors": len(report["errors"]),
                "next_cursor": report.get("next_cursor"),
                "output": str(args.output),
                "raw_response": report.get("raw_response"),
            },
            indent=2,
        )
    )
    return 0 if not report["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
