from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from crawl_folder_prompts import (
    append_event,
    cursor_key,
    load_json_object,
    request_page,
)
from fetch_prompts import API_BASE, DEFAULT_PROJECT_ID, UUID_RE
from probe_higgsfield import utc_now, write_json_atomic, write_text_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "project-inventory"


def children_url(
    folder_id: str,
    *,
    size: int,
    cursor: str | int | float | None,
) -> str:
    if not UUID_RE.fullmatch(folder_id):
        raise ValueError(f"folder ID is not a UUID: {folder_id}")
    query: dict[str, str | int | float] = {"size": size, "sort_by": "name"}
    if cursor is not None:
        query["cursor"] = cursor
    return f"{API_BASE}/folders/{folder_id}/children?{urllib.parse.urlencode(query)}"


def root_folder_url(folder_id: str) -> str:
    if not UUID_RE.fullmatch(folder_id):
        raise ValueError(f"folder ID is not a UUID: {folder_id}")
    return f"{API_BASE}/folders/{folder_id}?include_folders_count=true"


def page_path(directory: Path, parent_id: str, page_number: int) -> Path:
    return directory / parent_id / f"page-{page_number:06d}.json"


def sanitize_folder(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("folder record is not an object")
    folder_id = value.get("id")
    name = value.get("name")
    count = value.get("count")
    subfolders_count = value.get("subfolders_count")
    if not isinstance(folder_id, str) or not UUID_RE.fullmatch(folder_id):
        raise ValueError("folder record has an invalid ID")
    if not isinstance(name, str) or not name:
        raise ValueError(f"folder {folder_id} has an invalid name")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError(f"folder {folder_id} has an invalid asset count")
    if (
        isinstance(subfolders_count, bool)
        or not isinstance(subfolders_count, int)
        or subfolders_count < 0
    ):
        raise ValueError(f"folder {folder_id} has an invalid subfolder count")
    parent_id = value.get("parent_id")
    if parent_id is not None and not isinstance(parent_id, str):
        raise ValueError(f"folder {folder_id} has an invalid parent ID")
    return {
        "folder_id": folder_id,
        "parent_id": parent_id,
        "root_folder_id": value.get("root_folder_id"),
        "project_id": value.get("project_id"),
        "name": name,
        "path": value.get("path"),
        "is_root": value.get("is_root"),
        "reported_asset_count": count,
        "reported_subfolders_count": subfolders_count,
        "reported_folders_count": value.get("folders_count"),
        "created_at_unix": value.get("created_at"),
        "updated_at_unix": value.get("updated_at"),
    }


def normalize_children_page(
    response_text: str,
    *,
    parent_id: str,
    page_number: int,
    cursor_requested: str | int | float | None,
    source_endpoint: str,
    fetched_at: str,
    http: dict[str, Any],
    request_attempts: int,
) -> dict[str, Any]:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"children page {page_number} is invalid JSON: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"children page {page_number} does not contain an items array")
    next_cursor = payload.get("cursor")
    if next_cursor == "":
        next_cursor = None
    if isinstance(next_cursor, bool) or (
        next_cursor is not None and not isinstance(next_cursor, (str, int, float))
    ):
        raise ValueError("children cursor is not a supported scalar or null")

    folders = [sanitize_folder(item) for item in payload["items"]]
    seen_ids: set[str] = set()
    errors: list[dict[str, Any]] = []
    for index, folder in enumerate(folders):
        if folder["parent_id"] != parent_id:
            errors.append(
                {
                    "code": "parent_mismatch",
                    "index": index,
                    "folder_id": folder["folder_id"],
                    "expected_parent_id": parent_id,
                    "actual_parent_id": folder["parent_id"],
                }
            )
        if folder["folder_id"] in seen_ids:
            errors.append(
                {
                    "code": "duplicate_folder_in_page",
                    "index": index,
                    "folder_id": folder["folder_id"],
                }
            )
        seen_ids.add(folder["folder_id"])

    return {
        "schema_version": 1,
        "parent_id": parent_id,
        "page_number": page_number,
        "cursor_requested": cursor_requested,
        "next_cursor": next_cursor,
        "source_endpoint": source_endpoint,
        "fetched_at": fetched_at,
        "http": http,
        "request_attempts": request_attempts,
        "received_items": len(payload["items"]),
        "folders": folders,
        "errors": errors,
    }


def initial_checkpoint(root: dict[str, Any]) -> dict[str, Any]:
    root_id = root["folder_id"]
    return {
        "schema_version": 1,
        "root_folder_id": root_id,
        "folders": {root_id: root},
        "pending_parent_ids": [root_id],
        "completed_parent_ids": [],
        "parent_states": {},
        "complete": False,
        "fatal_error": None,
        "last_error": None,
        "warnings": [],
        "updated_at": utc_now(),
    }


def state_for_parent(checkpoint: dict[str, Any], parent_id: str) -> dict[str, Any]:
    state = checkpoint["parent_states"].get(parent_id)
    if state is None:
        state = {
            "next_page_number": 1,
            "next_cursor": None,
            "seen_request_cursors": [],
            "child_ids": [],
        }
        checkpoint["parent_states"][parent_id] = state
    return state


def commit_children_page(
    checkpoint: dict[str, Any],
    page: dict[str, Any],
    *,
    event_log: Path,
) -> dict[str, Any]:
    parent_id = page["parent_id"]
    if not checkpoint["pending_parent_ids"] or checkpoint["pending_parent_ids"][0] != parent_id:
        raise ValueError(f"parent {parent_id} is not at the front of the pending queue")
    state = state_for_parent(checkpoint, parent_id)
    if page["page_number"] != state["next_page_number"]:
        raise ValueError(f"unexpected page number for parent {parent_id}")
    if page["cursor_requested"] != state["next_cursor"]:
        raise ValueError(f"cursor does not match checkpoint for parent {parent_id}")
    requested_key = cursor_key(page["cursor_requested"])
    if requested_key in state["seen_request_cursors"]:
        raise ValueError(f"parent {parent_id} repeats a requested cursor")

    updated = json.loads(json.dumps(checkpoint))
    updated.setdefault("warnings", [])
    state = state_for_parent(updated, parent_id)
    state["seen_request_cursors"].append(requested_key)
    existing_ids = set(updated["folders"])
    child_ids = set(state["child_ids"])
    for folder in page["folders"]:
        folder_id = folder["folder_id"]
        if folder_id in child_ids:
            append_event(
                event_log,
                "error",
                "duplicate_folder_across_pages",
                parent_id=parent_id,
                folder_id=folder_id,
            )
            continue
        if folder_id in existing_ids and updated["folders"][folder_id] != folder:
            raise ValueError(f"folder {folder_id} was discovered with conflicting metadata")
        updated["folders"][folder_id] = folder
        existing_ids.add(folder_id)
        state["child_ids"].append(folder_id)
        child_ids.add(folder_id)
        if folder["reported_subfolders_count"] > 0:
            if (
                folder_id not in updated["pending_parent_ids"]
                and folder_id not in updated["completed_parent_ids"]
            ):
                updated["pending_parent_ids"].append(folder_id)

    state["next_page_number"] += 1
    state["next_cursor"] = page["next_cursor"]
    if page["received_items"] == 0 and page["next_cursor"] is not None:
        updated["fatal_error"] = f"parent {parent_id} returned an empty page with a cursor"
    elif (
        page["next_cursor"] is not None
        and cursor_key(page["next_cursor"]) in state["seen_request_cursors"]
    ):
        updated["fatal_error"] = f"parent {parent_id} returned a repeated cursor"
    elif page["next_cursor"] is None:
        parent = updated["folders"][parent_id]
        if len(state["child_ids"]) != parent["reported_subfolders_count"]:
            warning = {
                "code": "public_child_count_mismatch",
                "parent_id": parent_id,
                "reported_subfolders_count": parent["reported_subfolders_count"],
                "public_children_returned": len(state["child_ids"]),
            }
            updated["warnings"].append(warning)
            append_event(
                event_log,
                "warning",
                warning["code"],
                parent_id=parent_id,
                reported_subfolders_count=parent["reported_subfolders_count"],
                public_children_returned=len(state["child_ids"]),
            )
        updated["pending_parent_ids"].pop(0)
        updated["completed_parent_ids"].append(parent_id)

    if not updated["pending_parent_ids"] and not updated["fatal_error"]:
        updated["complete"] = True
    updated["last_error"] = None
    updated["updated_at"] = utc_now()
    return updated


def derive_direct_counts(
    folders_by_id: dict[str, dict[str, Any]], root_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    children: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors: list[dict[str, Any]] = []
    for folder in folders_by_id.values():
        if folder["folder_id"] == root_id:
            continue
        parent_id = folder["parent_id"]
        if parent_id not in folders_by_id:
            errors.append(
                {
                    "code": "missing_parent",
                    "folder_id": folder["folder_id"],
                    "parent_id": parent_id,
                }
            )
            continue
        children[parent_id].append(folder)

    inventory: list[dict[str, Any]] = []
    for folder in folders_by_id.values():
        child_reported_count = sum(
            child["reported_asset_count"] for child in children[folder["folder_id"]]
        )
        direct_count = folder["reported_asset_count"] - child_reported_count
        if direct_count < 0:
            errors.append(
                {
                    "code": "negative_derived_direct_count",
                    "folder_id": folder["folder_id"],
                    "reported_asset_count": folder["reported_asset_count"],
                    "child_reported_asset_count": child_reported_count,
                }
            )
        path = folder.get("path")
        depth = 0
        if isinstance(path, str):
            depth = max(0, len([part for part in path.split("/") if part]) - 1)
        inventory.append(
            {
                **folder,
                "depth": depth,
                "discovered_child_count": len(children[folder["folder_id"]]),
                "child_reported_asset_count": child_reported_count,
                "derived_direct_asset_count": direct_count,
            }
        )
    inventory.sort(key=lambda folder: (folder["depth"], folder.get("path") or ""))
    return inventory, errors


def write_outputs(
    run_dir: Path,
    checkpoint: dict[str, Any],
    *,
    network_requests_this_invocation: int,
) -> dict[str, Any]:
    root_id = checkpoint["root_folder_id"]
    inventory, errors = derive_direct_counts(checkpoint["folders"], root_id)
    root = checkpoint["folders"][root_id]
    total_direct = sum(folder["derived_direct_asset_count"] for folder in inventory)
    expected_folder_count = root.get("reported_folders_count")
    descendant_count = len(inventory) - 1
    complete = bool(checkpoint["complete"])
    checks = {
        "inventory_complete": {
            "actual": complete,
            "expected": True,
            "passed": complete,
        },
        "descendant_folder_count": {
            "actual": descendant_count,
            "expected": expected_folder_count,
            "passed": complete and descendant_count == expected_folder_count,
        },
        "derived_direct_asset_total": {
            "actual": total_direct,
            "expected": root["reported_asset_count"],
            "passed": complete and total_direct == root["reported_asset_count"],
        },
        "derivation_error_count": {
            "actual": len(errors),
            "expected": 0,
            "passed": not errors,
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
        status = "completed_with_warnings"

    write_json_atomic(
        run_dir / "folder-inventory.json",
        {
            "schema_version": 1,
            "generated_at": utc_now(),
            "status": status,
            "root_folder_id": root_id,
            "folders": inventory,
        },
    )
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": status,
        "root_folder_id": root_id,
        "project_name": root["name"],
        "reported_project_asset_count": root["reported_asset_count"],
        "reported_descendant_folder_count": expected_folder_count,
        "discovered_folder_count_including_root": len(inventory),
        "discovered_descendant_folder_count": descendant_count,
        "derived_direct_asset_total": total_direct,
        "folders_with_direct_assets": sum(
            folder["derived_direct_asset_count"] > 0 for folder in inventory
        ),
        "folders_with_subfolders": sum(
            folder["reported_subfolders_count"] > 0 for folder in inventory
        ),
        "maximum_depth": max((folder["depth"] for folder in inventory), default=0),
        "direct_asset_count_distribution": dict(
            sorted(
                Counter(
                    folder["derived_direct_asset_count"] for folder in inventory
                ).items()
            )
        ),
        "network_requests_this_invocation": network_requests_this_invocation,
        "errors": errors,
        "warnings": checkpoint.get("warnings", []),
        "checks": checks,
        "all_checks_passed": all_checks_passed,
        "fatal_error": checkpoint.get("fatal_error"),
        "last_error": checkpoint.get("last_error"),
        "inventory_path": str(run_dir / "folder-inventory.json"),
    }
    write_json_atomic(run_dir / "inventory-report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory a public Higgsfield project folder tree without requesting media."
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--retry-base-delay", type=float, default=1.0)
    parser.add_argument("--retry-max-delay", type=float, default=8.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-response-bytes", type=int, default=10_000_000)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not UUID_RE.fullmatch(args.project_id):
        raise ValueError("project ID is not a UUID")
    if not 1 <= args.page_size <= 100:
        raise ValueError("page size must be between 1 and 100")
    if args.max_pages is not None and args.max_pages < 1:
        raise ValueError("max pages must be positive")
    if args.request_delay < 0:
        raise ValueError("request delay cannot be negative")
    if args.max_attempts < 1:
        raise ValueError("max attempts must be positive")


def main() -> int:
    args = parse_args()
    event_log = args.run_dir / "events.jsonl"
    config_path = args.run_dir / "config.json"
    checkpoint_path = args.run_dir / "checkpoint.json"
    raw_root_path = args.run_dir / "raw" / "root-folder.json"
    normalized_root_path = args.run_dir / "normalized" / "root-folder.json"
    stats = {"network_requests": 0}
    pages_committed = 0
    last_request_finished_at: float | None = None

    def fetch_api(url: str, page_number: int) -> tuple[dict[str, Any], str, int]:
        nonlocal last_request_finished_at
        if last_request_finished_at is not None:
            elapsed = time.monotonic() - last_request_finished_at
            if elapsed < args.request_delay:
                time.sleep(args.request_delay - elapsed)
        result = request_page(
            url,
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
        return result

    try:
        validate_args(args)
        args.run_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "schema_version": 1,
            "project_id": args.project_id,
            "page_size": args.page_size,
        }
        if config_path.exists():
            if load_json_object(config_path) != config:
                raise ValueError("run configuration differs; use a new run directory")
        else:
            write_json_atomic(config_path, config)

        if checkpoint_path.exists():
            checkpoint = load_json_object(checkpoint_path)
            checkpoint.setdefault("warnings", [])
            legacy_fatal = checkpoint.get("fatal_error")
            if (
                isinstance(legacy_fatal, str)
                and "reported" in legacy_fatal
                and "subfolders but returned" in legacy_fatal
            ):
                checkpoint["warnings"].append(
                    {
                        "code": "public_child_count_mismatch",
                        "detail": legacy_fatal,
                        "recovered_from_legacy_fatal": True,
                    }
                )
                checkpoint["fatal_error"] = None
                checkpoint["updated_at"] = utc_now()
                write_json_atomic(checkpoint_path, checkpoint)
        else:
            source_url = root_folder_url(args.project_id)
            if raw_root_path.exists():
                response_text = raw_root_path.read_text(encoding="utf-8")
            else:
                http, response_text, _ = fetch_api(source_url, 0)
                write_text_atomic(raw_root_path, response_text)
            root_payload = json.loads(response_text)
            root = sanitize_folder(root_payload)
            if root["folder_id"] != args.project_id or not root["is_root"]:
                raise ValueError("root folder response does not match the project ID")
            write_json_atomic(normalized_root_path, root)
            checkpoint = initial_checkpoint(root)
            write_json_atomic(checkpoint_path, checkpoint)

        append_event(
            event_log,
            "info",
            "inventory_invocation_started",
            checkpoint_complete=checkpoint["complete"],
            pending_parents=len(checkpoint["pending_parent_ids"]),
        )
        while not checkpoint["complete"] and not checkpoint.get("fatal_error"):
            if args.max_pages is not None and pages_committed >= args.max_pages:
                break
            parent_id = checkpoint["pending_parent_ids"][0]
            state = state_for_parent(checkpoint, parent_id)
            page_number = state["next_page_number"]
            cursor = state["next_cursor"]
            source_url = children_url(parent_id, size=args.page_size, cursor=cursor)
            raw_path = page_path(args.run_dir / "raw" / "children", parent_id, page_number)
            normalized_path = page_path(
                args.run_dir / "normalized" / "children", parent_id, page_number
            )
            if normalized_path.exists():
                if not raw_path.exists():
                    raise ValueError("normalized children page exists without raw response")
                page = load_json_object(normalized_path)
            else:
                if raw_path.exists():
                    response_text = raw_path.read_text(encoding="utf-8")
                    http = {"recovered_from_raw": True}
                    attempts = 0
                else:
                    http, response_text, attempts = fetch_api(
                        source_url, page_number
                    )
                    write_text_atomic(raw_path, response_text)
                page = normalize_children_page(
                    response_text,
                    parent_id=parent_id,
                    page_number=page_number,
                    cursor_requested=cursor,
                    source_endpoint=source_url,
                    fetched_at=utc_now(),
                    http=http,
                    request_attempts=attempts,
                )
                write_json_atomic(normalized_path, page)
            if page["errors"]:
                raise ValueError(
                    f"children page for parent {parent_id} contains validation errors"
                )
            checkpoint = commit_children_page(checkpoint, page, event_log=event_log)
            write_json_atomic(checkpoint_path, checkpoint)
            pages_committed += 1
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        if "checkpoint" not in locals():
            print(f"Inventory preparation failed: {error}", file=sys.stderr)
            return 1
        checkpoint["last_error"] = repr(error)
        checkpoint["updated_at"] = utc_now()
        write_json_atomic(checkpoint_path, checkpoint)
        append_event(event_log, "error", "inventory_stopped", error=repr(error))
        print(f"Inventory stopped: {error}", file=sys.stderr)

    report = write_outputs(
        args.run_dir,
        checkpoint,
        network_requests_this_invocation=stats["network_requests"],
    )
    append_event(
        event_log,
        "info",
        "inventory_invocation_finished",
        status=report["status"],
        network_requests=stats["network_requests"],
        pages_committed=pages_committed,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "folders_including_root": report[
                    "discovered_folder_count_including_root"
                ],
                "derived_direct_asset_total": report["derived_direct_asset_total"],
                "reported_project_asset_count": report[
                    "reported_project_asset_count"
                ],
                "network_requests_this_invocation": stats["network_requests"],
                "all_checks_passed": report["all_checks_passed"],
                "report": str(args.run_dir / "inventory-report.json"),
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
