from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from fetch_prompts import DEFAULT_PROJECT_ID, build_url, extract_record
from probe_higgsfield import fetch_text, utc_now, write_json_atomic, write_text_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOLDER_ID = "52eefbe6-4d49-405a-a244-24ead11f2887"
DEFAULT_FOLDER_NAME = "Scene 69 - Fight"
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "scene-69-fight"
URL_MARKER = "<URL_REDACTED>"
PROMPT_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def page_path(directory: Path, page_number: int) -> Path:
    return directory / f"page-{page_number:06d}.json"


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def append_event(path: Path, level: str, code: str, **details: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"at": utc_now(), "level": level, "code": code, **details}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        handle.flush()


def redact_prompt_urls(prompt: str) -> tuple[str, int]:
    return PROMPT_URL_RE.subn(URL_MARKER, prompt)


def error_code(error: dict[str, Any]) -> str:
    reason = str(error.get("reason", "unknown extraction error")).lower()
    mappings = (
        ("item is not an object", "item_not_object"),
        ("unsupported item type", "unsupported_item_type"),
        ("params are missing", "missing_job_params"),
        ("prompt is empty", "empty_prompt"),
        ("asset id is missing", "missing_asset_id"),
        ("folder id is missing", "missing_folder_id"),
    )
    return next((code for phrase, code in mappings if phrase in reason), "record_parse_error")


def normalize_page(
    response_text: str,
    *,
    project_id: str,
    folder_id: str,
    folder_name: str,
    page_number: int,
    cursor_requested: str | int | float | None,
    source_url: str,
    fetched_at: str,
    http: dict[str, Any],
    request_attempts: int,
) -> dict[str, Any]:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"page {page_number} is not valid JSON: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"page {page_number} does not contain an items array")

    next_cursor = payload.get("cursor")
    if next_cursor == "":
        next_cursor = None
    if isinstance(next_cursor, bool) or (
        next_cursor is not None and not isinstance(next_cursor, (str, int, float))
    ):
        raise ValueError(
            f"page {page_number} cursor is not a supported scalar or null"
        )

    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    page_asset_ids: set[str] = set()
    asset_ids: list[str] = []
    for index, item in enumerate(payload["items"]):
        job = item.get("job") if isinstance(item, dict) else None
        item_asset_id = job.get("id") if isinstance(job, dict) else None
        if isinstance(item_asset_id, str) and item_asset_id:
            asset_ids.append(item_asset_id)
            if item_asset_id in page_asset_ids:
                errors.append(
                    {
                        "code": "duplicate_asset_in_page",
                        "page_number": page_number,
                        "index": index,
                        "asset_id": item_asset_id,
                    }
                )
            page_asset_ids.add(item_asset_id)

        record, extraction_error = extract_record(
            item,
            index=index,
            project_id=project_id,
            source_url=source_url,
        )
        if extraction_error is not None:
            errors.append(
                {
                    "code": error_code(extraction_error),
                    "page_number": page_number,
                    **extraction_error,
                }
            )
            continue

        assert record is not None
        record["folder_name"] = folder_name
        record["source_page"] = page_number
        record["fetched_at"] = fetched_at
        if record["folder_id"] != folder_id:
            errors.append(
                {
                    "code": "folder_mismatch",
                    "page_number": page_number,
                    "index": index,
                    "asset_id": record["asset_id"],
                    "expected_folder_id": folder_id,
                    "actual_folder_id": record["folder_id"],
                }
            )

        redacted_prompt, redaction_count = redact_prompt_urls(record["prompt"])
        if redaction_count:
            original_hash = record["prompt_sha256"]
            record["prompt"] = redacted_prompt
            record["prompt_chars"] = len(redacted_prompt)
            record["prompt_sha256"] = hashlib.sha256(
                redacted_prompt.encode("utf-8")
            ).hexdigest()
            record["source_prompt_sha256"] = original_hash
            record["prompt_url_redactions"] = redaction_count
            warnings.append(
                {
                    "code": "prompt_url_redacted",
                    "page_number": page_number,
                    "index": index,
                    "asset_id": record["asset_id"],
                    "count": redaction_count,
                }
            )
        records.append(record)

    return {
        "schema_version": 1,
        "project_id": project_id,
        "folder_id": folder_id,
        "folder_name": folder_name,
        "include_subfolders": False,
        "page_number": page_number,
        "cursor_requested": cursor_requested,
        "next_cursor": next_cursor,
        "source_endpoint": source_url,
        "fetched_at": fetched_at,
        "http": http,
        "request_attempts": request_attempts,
        "received_items": len(payload["items"]),
        "asset_ids": asset_ids,
        "record_count": len(records),
        "records": records,
        "errors": errors,
        "warnings": warnings,
    }


def request_page(
    url: str,
    *,
    timeout: float,
    max_response_bytes: int,
    max_attempts: int,
    retry_base_delay: float,
    retry_max_delay: float,
    event_log: Path,
    page_number: int,
    stats: dict[str, int],
) -> tuple[dict[str, Any], str, int]:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        stats["network_requests"] += 1
        append_event(
            event_log,
            "info",
            "http_request",
            page_number=page_number,
            attempt=attempt,
        )
        try:
            response = fetch_text(
                url,
                timeout=timeout,
                max_bytes=max_response_bytes,
            )
            response_text = response.pop("text")
            if response["status"] != 200:
                raise ValueError(f"unexpected HTTP status {response['status']}")
            if response["content_type"] != "application/json":
                raise ValueError(
                    f"unexpected Content-Type {response['content_type']!r}"
                )
            append_event(
                event_log,
                "info",
                "http_success",
                page_number=page_number,
                attempt=attempt,
                status=response["status"],
                response_bytes=response["bytes"],
            )
            return response, response_text, attempt
        except urllib.error.HTTPError as error:
            last_error = error
            retryable = error.code in {408, 425, 429} or 500 <= error.code <= 599
            append_event(
                event_log,
                "error",
                "http_error",
                page_number=page_number,
                attempt=attempt,
                status=error.code,
                retryable=retryable,
                error=repr(error),
            )
            if not retryable:
                break
        except (OSError, ValueError, urllib.error.URLError) as error:
            last_error = error
            append_event(
                event_log,
                "error",
                "request_error",
                page_number=page_number,
                attempt=attempt,
                retryable=True,
                error=repr(error),
            )

        if attempt < max_attempts:
            delay = min(retry_max_delay, retry_base_delay * (2 ** (attempt - 1)))
            append_event(
                event_log,
                "warning",
                "retry_wait",
                page_number=page_number,
                attempt=attempt,
                delay_seconds=delay,
            )
            time.sleep(delay)

    assert last_error is not None
    raise RuntimeError(
        f"page {page_number} failed after at most {max_attempts} attempts: {last_error!r}"
    ) from last_error


def initial_checkpoint(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project_id": config["project_id"],
        "folder_id": config["folder_id"],
        "folder_name": config["folder_name"],
        "next_page_number": 1,
        "next_cursor": None,
        "seen_request_cursors": [],
        "seen_asset_ids": [],
        "received_items": 0,
        "record_count": 0,
        "complete": False,
        "fatal_error": None,
        "last_error": None,
        "updated_at": utc_now(),
    }


def cursor_key(cursor: str | int | float | None) -> str:
    if cursor is None:
        return "<FIRST_PAGE>"
    return f"{type(cursor).__name__}:{json.dumps(cursor, ensure_ascii=False)}"


def commit_page(
    checkpoint: dict[str, Any],
    page: dict[str, Any],
    *,
    event_log: Path,
) -> dict[str, Any]:
    expected_page = checkpoint["next_page_number"]
    if page.get("page_number") != expected_page:
        raise ValueError(
            f"cannot commit page {page.get('page_number')}; expected page {expected_page}"
        )
    if page.get("cursor_requested") != checkpoint.get("next_cursor"):
        raise ValueError(f"page {expected_page} cursor does not match checkpoint")

    requested_key = cursor_key(page.get("cursor_requested"))
    if requested_key in checkpoint["seen_request_cursors"]:
        raise ValueError(f"page {expected_page} repeats a previously requested cursor")

    updated = json.loads(json.dumps(checkpoint))
    updated["seen_request_cursors"].append(requested_key)
    seen_asset_ids = set(updated["seen_asset_ids"])
    for asset_id in page["asset_ids"]:
        if asset_id in seen_asset_ids:
            append_event(
                event_log,
                "error",
                "duplicate_asset_across_pages",
                page_number=expected_page,
                asset_id=asset_id,
            )
        else:
            updated["seen_asset_ids"].append(asset_id)
            seen_asset_ids.add(asset_id)

    updated["received_items"] += page["received_items"]
    updated["record_count"] += page["record_count"]
    updated["next_page_number"] += 1
    updated["next_cursor"] = page["next_cursor"]
    updated["last_error"] = None

    if page["received_items"] == 0 and page["next_cursor"] is not None:
        updated["fatal_error"] = "empty page returned a continuation cursor"
    elif (
        page["next_cursor"] is not None
        and cursor_key(page["next_cursor"]) in updated["seen_request_cursors"]
    ):
        updated["fatal_error"] = "API returned a repeated cursor"
    elif page["next_cursor"] is None:
        updated["complete"] = True

    updated["updated_at"] = utc_now()
    return updated


def distribution(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts = Counter(
        str(record.get(field)) if record.get(field) is not None else "<null>"
        for record in records
    )
    return dict(sorted(counts.items()))


def aggregate_run(
    *,
    run_dir: Path,
    config: dict[str, Any],
    checkpoint: dict[str, Any],
    network_requests_this_invocation: int,
) -> dict[str, Any]:
    normalized_dir = run_dir / "pages" / "normalized"
    pages = [load_json_object(path) for path in sorted(normalized_dir.glob("page-*.json"))]
    records = [record for page in pages for record in page.get("records", [])]
    errors = [error for page in pages for error in page.get("errors", [])]
    warnings = [warning for page in pages for warning in page.get("warnings", [])]

    asset_occurrences: dict[str, list[int]] = defaultdict(list)
    prompt_occurrences: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        for asset_id in page.get("asset_ids", []):
            asset_occurrences[asset_id].append(page["page_number"])
    for record in records:
        prompt_occurrences[record["prompt_sha256"]].append(record["asset_id"])

    duplicate_assets = {
        asset_id: pages_seen
        for asset_id, pages_seen in sorted(asset_occurrences.items())
        if len(pages_seen) > 1
    }
    duplicate_prompts = [
        {"prompt_sha256": prompt_hash, "asset_ids": asset_ids}
        for prompt_hash, asset_ids in sorted(prompt_occurrences.items())
        if len(asset_ids) > 1
    ]
    error_types = dict(sorted(Counter(error["code"] for error in errors).items()))
    warning_types = dict(sorted(Counter(warning["code"] for warning in warnings).items()))
    page_manifest: list[dict[str, Any]] = []
    for page in pages:
        page_number = page["page_number"]
        raw_path = page_path(run_dir / "pages" / "raw", page_number)
        normalized_path = page_path(normalized_dir, page_number)
        raw_bytes = raw_path.read_bytes()
        normalized_bytes = normalized_path.read_bytes()
        page_manifest.append(
            {
                "page_number": page_number,
                "received_items": page["received_items"],
                "record_count": page["record_count"],
                "raw_path": str(raw_path),
                "raw_bytes": len(raw_bytes),
                "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
                "normalized_path": str(normalized_path),
                "normalized_bytes": len(normalized_bytes),
                "normalized_sha256": hashlib.sha256(normalized_bytes).hexdigest(),
            }
        )

    http_request_events = 0
    event_log_parse_errors: list[dict[str, Any]] = []
    event_log_path = run_dir / "events.jsonl"
    if event_log_path.exists():
        for line_number, line in enumerate(
            event_log_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                event_log_parse_errors.append(
                    {"line_number": line_number, "error": str(error)}
                )
                continue
            if isinstance(event, dict) and event.get("code") == "http_request":
                http_request_events += 1
    received_items = sum(page.get("received_items", 0) for page in pages)
    non_empty_prompts = sum(
        isinstance(record.get("prompt"), str) and bool(record["prompt"].strip())
        for record in records
    )
    prompt_urls_remaining = sum(
        "http://" in record["prompt"].lower()
        or "https://" in record["prompt"].lower()
        for record in records
    )
    expected_count = config["expected_count"]
    complete = bool(checkpoint.get("complete"))

    checks = {
        "run_complete": {"actual": complete, "expected": True, "passed": complete},
        "api_item_count": {
            "actual": received_items,
            "expected": expected_count,
            "passed": complete and received_items == expected_count,
        },
        "unique_asset_count": {
            "actual": len(asset_occurrences),
            "expected": expected_count,
            "passed": complete and len(asset_occurrences) == expected_count,
        },
        "non_empty_prompt_count": {
            "actual": non_empty_prompts,
            "expected": expected_count,
            "passed": complete and non_empty_prompts == expected_count,
        },
        "duplicate_asset_count": {
            "actual": len(duplicate_assets),
            "expected": 0,
            "passed": not duplicate_assets,
        },
        "record_error_count": {
            "actual": len(errors),
            "expected": 0,
            "passed": not errors,
        },
        "prompt_urls_remaining": {
            "actual": prompt_urls_remaining,
            "expected": 0,
            "passed": prompt_urls_remaining == 0,
        },
    }
    all_checks_passed = all(check["passed"] for check in checks.values())
    if checkpoint.get("fatal_error") or checkpoint.get("last_error"):
        status = "failed"
    elif not complete:
        status = "paused"
    elif all_checks_passed:
        status = "passed"
    else:
        status = "failed"

    corpus = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": status,
        "project_id": config["project_id"],
        "folder_id": config["folder_id"],
        "folder_name": config["folder_name"],
        "include_subfolders": False,
        "records": records,
    }
    write_json_atomic(run_dir / "corpus.json", corpus)

    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": status,
        "project_id": config["project_id"],
        "folder_id": config["folder_id"],
        "folder_name": config["folder_name"],
        "expected_asset_count": expected_count,
        "include_subfolders": False,
        "page_size": config["page_size"],
        "pages_committed": len(pages),
        "network_requests_this_invocation": network_requests_this_invocation,
        "request_attempts_in_committed_pages": sum(
            page.get("request_attempts", 0) for page in pages
        ),
        "received_items": received_items,
        "record_count": len(records),
        "unique_asset_count": len(asset_occurrences),
        "non_empty_prompt_count": non_empty_prompts,
        "exact_duplicate_prompt_groups": len(duplicate_prompts),
        "exact_duplicate_prompt_extra_records": sum(
            len(group["asset_ids"]) - 1 for group in duplicate_prompts
        ),
        "unique_prompt_count": len(prompt_occurrences),
        "duplicate_assets": duplicate_assets,
        "duplicate_prompts": duplicate_prompts,
        "errors": errors,
        "error_types": error_types,
        "warnings": warnings,
        "warning_types": warning_types,
        "page_manifest": page_manifest,
        "logged_http_request_attempts_total": http_request_events,
        "event_log_parse_errors": event_log_parse_errors,
        "distributions": {
            "asset_type": distribution(records, "asset_type"),
            "job_set_type": distribution(records, "job_set_type"),
            "model": distribution(records, "model"),
        },
        "checks": checks,
        "all_checks_passed": all_checks_passed,
        "checkpoint_complete": complete,
        "fatal_error": checkpoint.get("fatal_error"),
        "corpus_path": str(run_dir / "corpus.json"),
    }
    write_json_atomic(run_dir / "reconciliation.json", report)
    return report


def expected_config(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project_id": args.project_id,
        "folder_id": args.folder_id,
        "folder_name": args.folder_name,
        "expected_count": args.expected_count,
        "page_size": args.page_size,
        "include_subfolders": False,
    }


def prepare_run(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    args.run_dir.mkdir(parents=True, exist_ok=True)
    (args.run_dir / "pages" / "raw").mkdir(parents=True, exist_ok=True)
    (args.run_dir / "pages" / "normalized").mkdir(parents=True, exist_ok=True)
    config_path = args.run_dir / "config.json"
    checkpoint_path = args.run_dir / "checkpoint.json"
    config = expected_config(args)
    if config_path.exists():
        existing = load_json_object(config_path)
        if existing != config:
            raise ValueError(
                "run configuration differs from existing config.json; use a new run directory"
            )
    else:
        write_json_atomic(config_path, config)

    if checkpoint_path.exists():
        checkpoint = load_json_object(checkpoint_path)
    else:
        checkpoint = initial_checkpoint(config)
        write_json_atomic(checkpoint_path, checkpoint)
    return config, checkpoint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Crawl one public Higgsfield folder's Prompt text with atomic pages, "
            "resume checkpoints, bounded retries, and reconciliation."
        )
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--folder-id", default=DEFAULT_FOLDER_ID)
    parser.add_argument("--folder-name", default=DEFAULT_FOLDER_NAME)
    parser.add_argument("--expected-count", type=int, default=146)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Pause cleanly after committing this many pages in the current invocation.",
    )
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--retry-base-delay", type=float, default=1.0)
    parser.add_argument("--retry-max-delay", type=float, default=8.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-response-bytes", type=int, default=30_000_000)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.page_size <= 100:
        raise ValueError("page size must be between 1 and 100")
    if args.expected_count < 1:
        raise ValueError("expected count must be positive")
    if args.max_pages is not None and args.max_pages < 1:
        raise ValueError("max pages must be positive")
    if args.request_delay < 0:
        raise ValueError("request delay cannot be negative")
    if args.max_attempts < 1:
        raise ValueError("max attempts must be positive")
    if args.retry_base_delay < 0 or args.retry_max_delay < 0:
        raise ValueError("retry delays cannot be negative")


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        config, checkpoint = prepare_run(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Cannot prepare run: {error}", file=sys.stderr)
        return 1

    event_log = args.run_dir / "events.jsonl"
    checkpoint_path = args.run_dir / "checkpoint.json"
    stats = {"network_requests": 0}
    pages_committed_this_invocation = 0
    last_request_finished_at: float | None = None

    append_event(
        event_log,
        "info",
        "invocation_started",
        checkpoint_complete=checkpoint["complete"],
        next_page_number=checkpoint["next_page_number"],
    )

    try:
        while not checkpoint["complete"] and not checkpoint.get("fatal_error"):
            if (
                args.max_pages is not None
                and pages_committed_this_invocation >= args.max_pages
            ):
                break

            page_number = checkpoint["next_page_number"]
            cursor = checkpoint.get("next_cursor")
            source_url = build_url(args.folder_id, args.page_size, False, cursor)
            raw_path = page_path(args.run_dir / "pages" / "raw", page_number)
            normalized_path = page_path(
                args.run_dir / "pages" / "normalized", page_number
            )

            if normalized_path.exists():
                if not raw_path.exists():
                    raise ValueError(
                        f"normalized page {page_number} exists without its raw page"
                    )
                normalized_page = load_json_object(normalized_path)
                append_event(
                    event_log,
                    "info",
                    "recovered_normalized_page",
                    page_number=page_number,
                )
            else:
                if raw_path.exists():
                    response_text = raw_path.read_text(encoding="utf-8")
                    response_bytes = response_text.encode("utf-8")
                    http = {
                        "recovered_from_raw": True,
                        "bytes": len(response_bytes),
                        "sha256": hashlib.sha256(response_bytes).hexdigest(),
                    }
                    fetched_at = utc_now()
                    request_attempts = 0
                    append_event(
                        event_log,
                        "info",
                        "recovered_raw_page",
                        page_number=page_number,
                    )
                else:
                    if last_request_finished_at is not None:
                        elapsed = time.monotonic() - last_request_finished_at
                        if elapsed < args.request_delay:
                            time.sleep(args.request_delay - elapsed)
                    http, response_text, request_attempts = request_page(
                        source_url,
                        timeout=args.timeout,
                        max_response_bytes=args.max_response_bytes,
                        max_attempts=args.max_attempts,
                        retry_base_delay=args.retry_base_delay,
                        retry_max_delay=args.retry_max_delay,
                        event_log=event_log,
                        page_number=page_number,
                        stats=stats,
                    )
                    last_request_finished_at = time.monotonic()
                    fetched_at = utc_now()
                    write_text_atomic(raw_path, response_text)
                    append_event(
                        event_log,
                        "info",
                        "raw_page_written",
                        page_number=page_number,
                        bytes=len(response_text.encode("utf-8")),
                    )

                normalized_page = normalize_page(
                    response_text,
                    project_id=args.project_id,
                    folder_id=args.folder_id,
                    folder_name=args.folder_name,
                    page_number=page_number,
                    cursor_requested=cursor,
                    source_url=source_url,
                    fetched_at=fetched_at,
                    http=http,
                    request_attempts=request_attempts,
                )
                write_json_atomic(normalized_path, normalized_page)
                append_event(
                    event_log,
                    "info",
                    "normalized_page_written",
                    page_number=page_number,
                    received_items=normalized_page["received_items"],
                    record_count=normalized_page["record_count"],
                    error_count=len(normalized_page["errors"]),
                    warning_count=len(normalized_page["warnings"]),
                )
                for error in normalized_page["errors"]:
                    append_event(
                        event_log,
                        "error",
                        error["code"],
                        **{key: value for key, value in error.items() if key != "code"},
                    )
                for warning in normalized_page["warnings"]:
                    append_event(
                        event_log,
                        "warning",
                        warning["code"],
                        **{
                            key: value
                            for key, value in warning.items()
                            if key != "code"
                        },
                    )

            checkpoint = commit_page(checkpoint, normalized_page, event_log=event_log)
            write_json_atomic(checkpoint_path, checkpoint)
            pages_committed_this_invocation += 1
            append_event(
                event_log,
                "info",
                "checkpoint_written",
                page_number=page_number,
                complete=checkpoint["complete"],
                next_page_number=checkpoint["next_page_number"],
            )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        checkpoint["last_error"] = repr(error)
        checkpoint["updated_at"] = utc_now()
        write_json_atomic(checkpoint_path, checkpoint)
        append_event(event_log, "error", "crawl_stopped", error=repr(error))
        print(f"Crawl stopped: {error}", file=sys.stderr)

    report = aggregate_run(
        run_dir=args.run_dir,
        config=config,
        checkpoint=checkpoint,
        network_requests_this_invocation=stats["network_requests"],
    )
    append_event(
        event_log,
        "info",
        "invocation_finished",
        status=report["status"],
        network_requests=stats["network_requests"],
        pages_committed=pages_committed_this_invocation,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "pages_committed": report["pages_committed"],
                "received_items": report["received_items"],
                "unique_asset_count": report["unique_asset_count"],
                "non_empty_prompt_count": report["non_empty_prompt_count"],
                "record_errors": len(report["errors"]),
                "warnings": len(report["warnings"]),
                "network_requests_this_invocation": stats["network_requests"],
                "checkpoint_complete": report["checkpoint_complete"],
                "all_checks_passed": report["all_checks_passed"],
                "report": str(args.run_dir / "reconciliation.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if checkpoint.get("last_error") or checkpoint.get("fatal_error"):
        return 2
    if checkpoint["complete"] and not report["all_checks_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
