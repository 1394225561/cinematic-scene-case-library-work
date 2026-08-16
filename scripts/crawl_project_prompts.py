from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from crawl_folder_prompts import (
    append_event,
    cursor_key,
    load_json_object,
    redact_prompt_urls,
    request_page,
)
from fetch_prompts import DEFAULT_PROJECT_ID, build_url
from probe_higgsfield import utc_now, write_json_atomic, write_text_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "project-corpus"
DEFAULT_INVENTORY = (
    WORK_ROOT / "data" / "runs" / "project-inventory" / "folder-inventory.json"
)


SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS folders (
    folder_id TEXT PRIMARY KEY,
    parent_id TEXT,
    name TEXT NOT NULL,
    path TEXT,
    depth INTEGER NOT NULL,
    reported_asset_count INTEGER NOT NULL,
    derived_direct_asset_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS prompts (
    prompt_sha256 TEXT PRIMARY KEY,
    prompt_text TEXT NOT NULL,
    source_prompt_chars INTEGER NOT NULL,
    analysis_prompt_chars INTEGER NOT NULL,
    url_redaction_count INTEGER NOT NULL,
    first_asset_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    folder_id TEXT,
    item_type TEXT,
    asset_type TEXT,
    status TEXT,
    job_set_type TEXT,
    model TEXT,
    created_at_unix REAL,
    width INTEGER,
    height INTEGER,
    duration_seconds REAL,
    resolution TEXT,
    prompt_sha256 TEXT REFERENCES prompts(prompt_sha256),
    source_page INTEGER NOT NULL,
    source_item_index INTEGER NOT NULL,
    fetched_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS assets_folder_id_idx ON assets(folder_id);
CREATE INDEX IF NOT EXISTS assets_prompt_sha256_idx ON assets(prompt_sha256);
CREATE INDEX IF NOT EXISTS assets_model_idx ON assets(model);
CREATE INDEX IF NOT EXISTS assets_created_at_idx ON assets(created_at_unix);

CREATE TABLE IF NOT EXISTS asset_folder_memberships (
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    folder_id TEXT NOT NULL,
    first_seen_page INTEGER NOT NULL,
    PRIMARY KEY (asset_id, folder_id)
);

CREATE INDEX IF NOT EXISTS asset_folder_memberships_folder_idx
ON asset_folder_memberships(folder_id);

CREATE TABLE IF NOT EXISTS item_occurrences (
    page_number INTEGER NOT NULL,
    item_index INTEGER NOT NULL,
    asset_id TEXT,
    item_type TEXT,
    parse_status TEXT NOT NULL,
    PRIMARY KEY (page_number, item_index)
);

CREATE TABLE IF NOT EXISTS pages (
    page_number INTEGER PRIMARY KEY,
    cursor_requested_json TEXT NOT NULL,
    next_cursor_json TEXT NOT NULL,
    received_items INTEGER NOT NULL,
    asset_id_count INTEGER NOT NULL,
    prompt_record_count INTEGER NOT NULL,
    error_count INTEGER NOT NULL,
    warning_count INTEGER NOT NULL,
    raw_path TEXT NOT NULL,
    raw_bytes INTEGER NOT NULL,
    raw_sha256 TEXT NOT NULL,
    source_endpoint TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    request_attempts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS issues (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_number INTEGER NOT NULL,
    item_index INTEGER,
    asset_id TEXT,
    severity TEXT NOT NULL,
    code TEXT NOT NULL,
    details_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS issues_code_idx ON issues(code);
CREATE INDEX IF NOT EXISTS issues_severity_idx ON issues(severity);
"""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def inventory_fingerprint(folders: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_json(folders).encode("utf-8")).hexdigest()


def raw_page_path(run_dir: Path, page_number: int) -> Path:
    return run_dir / "pages" / "raw" / f"page-{page_number:06d}.json"


def scalar_cursor(value: Any, *, page_number: int) -> str | int | float | None:
    if value == "":
        return None
    if isinstance(value, bool) or (
        value is not None and not isinstance(value, (str, int, float))
    ):
        raise ValueError(f"page {page_number} cursor is not a supported scalar or null")
    return value


def issue(
    code: str,
    severity: str,
    *,
    item_index: int | None,
    asset_id: str | None,
    **details: Any,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "item_index": item_index,
        "asset_id": asset_id,
        "details": details,
    }


def parse_item(item: Any, *, item_index: int, page_number: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "item_index": item_index,
            "item_type": None,
            "asset_id": None,
            "asset": None,
            "prompt": None,
            "issues": [
                issue(
                    "item_not_object",
                    "error",
                    item_index=item_index,
                    asset_id=None,
                )
            ],
        }

    item_type = item.get("type")
    job = item.get("job")
    if item_type != "job" or not isinstance(job, dict):
        return {
            "item_index": item_index,
            "item_type": item_type,
            "asset_id": None,
            "asset": None,
            "prompt": None,
            "issues": [
                issue(
                    "unsupported_item_type",
                    "error",
                    item_index=item_index,
                    asset_id=None,
                    item_type=item_type,
                )
            ],
        }

    raw_asset_id = job.get("id")
    asset_id = raw_asset_id if isinstance(raw_asset_id, str) and raw_asset_id else None
    issues: list[dict[str, Any]] = []
    if asset_id is None:
        issues.append(
            issue(
                "missing_asset_id",
                "error",
                item_index=item_index,
                asset_id=None,
            )
        )

    raw_folder_id = job.get("folder_id")
    folder_id = (
        raw_folder_id if isinstance(raw_folder_id, str) and raw_folder_id else None
    )
    if folder_id is None:
        issues.append(
            issue(
                "missing_folder_id",
                "error",
                item_index=item_index,
                asset_id=asset_id,
            )
        )

    params = job.get("params")
    if not isinstance(params, dict):
        params = {}
        issues.append(
            issue(
                "missing_job_params",
                "error",
                item_index=item_index,
                asset_id=asset_id,
            )
        )

    raw_prompt = params.get("prompt")
    prompt: dict[str, Any] | None = None
    if isinstance(raw_prompt, str) and raw_prompt.strip():
        source_hash = hashlib.sha256(raw_prompt.encode("utf-8")).hexdigest()
        analysis_prompt, redaction_count = redact_prompt_urls(raw_prompt)
        prompt = {
            "prompt_sha256": source_hash,
            "prompt_text": analysis_prompt,
            "source_prompt_chars": len(raw_prompt),
            "analysis_prompt_chars": len(analysis_prompt),
            "url_redaction_count": redaction_count,
        }
        if redaction_count:
            issues.append(
                issue(
                    "prompt_url_redacted",
                    "warning",
                    item_index=item_index,
                    asset_id=asset_id,
                    count=redaction_count,
                )
            )
    else:
        issues.append(
            issue(
                "empty_prompt",
                "error",
                item_index=item_index,
                asset_id=asset_id,
            )
        )

    results = job.get("results")
    raw_result = results.get("raw") if isinstance(results, dict) else None
    asset_type = raw_result.get("type") if isinstance(raw_result, dict) else None
    asset = None
    if asset_id is not None:
        asset = {
            "asset_id": asset_id,
            "folder_id": folder_id,
            "item_type": item_type,
            "asset_type": asset_type,
            "status": job.get("status"),
            "job_set_type": job.get("job_set_type"),
            "model": params.get("model"),
            "created_at_unix": job.get("created_at"),
            "width": params.get("width"),
            "height": params.get("height"),
            "duration_seconds": params.get("duration"),
            "resolution": params.get("resolution"),
            "prompt_sha256": prompt["prompt_sha256"] if prompt else None,
            "source_page": page_number,
            "source_item_index": item_index,
        }

    return {
        "item_index": item_index,
        "item_type": item_type,
        "asset_id": asset_id,
        "asset": asset,
        "prompt": prompt,
        "issues": issues,
    }


def parse_page(
    response_text: str,
    *,
    page_number: int,
    cursor_requested: str | int | float | None,
    source_endpoint: str,
    fetched_at: str,
    request_attempts: int,
) -> dict[str, Any]:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"page {page_number} is invalid JSON: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"page {page_number} does not contain an items array")
    next_cursor = scalar_cursor(payload.get("cursor"), page_number=page_number)
    parsed_items = [
        parse_item(item, item_index=index, page_number=page_number)
        for index, item in enumerate(payload["items"])
    ]
    return {
        "page_number": page_number,
        "cursor_requested": cursor_requested,
        "next_cursor": next_cursor,
        "source_endpoint": source_endpoint,
        "fetched_at": fetched_at,
        "request_attempts": request_attempts,
        "received_items": len(payload["items"]),
        "items": parsed_items,
    }


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=60.0)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def seed_database(
    connection: sqlite3.Connection,
    *,
    config: dict[str, Any],
    folders: list[dict[str, Any]],
) -> None:
    existing = connection.execute(
        "SELECT value_json FROM metadata WHERE key = 'config'"
    ).fetchone()
    config_json = canonical_json(config)
    if existing is not None and existing["value_json"] != config_json:
        raise ValueError("SQLite configuration differs from config.json")
    with connection:
        connection.execute(
            "INSERT OR IGNORE INTO metadata(key, value_json) VALUES ('config', ?)",
            (config_json,),
        )
        for folder in folders:
            connection.execute(
                """
                INSERT INTO folders(
                    folder_id, parent_id, name, path, depth,
                    reported_asset_count, derived_direct_asset_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(folder_id) DO UPDATE SET
                    parent_id = excluded.parent_id,
                    name = excluded.name,
                    path = excluded.path,
                    depth = excluded.depth,
                    reported_asset_count = excluded.reported_asset_count,
                    derived_direct_asset_count = excluded.derived_direct_asset_count
                """,
                (
                    folder["folder_id"],
                    folder.get("parent_id"),
                    folder["name"],
                    folder.get("path"),
                    folder["depth"],
                    folder["reported_asset_count"],
                    folder["derived_direct_asset_count"],
                ),
            )
        connection.execute(
            """
            INSERT OR IGNORE INTO asset_folder_memberships(
                asset_id, folder_id, first_seen_page
            )
            SELECT asset_id, folder_id, source_page
            FROM assets WHERE folder_id IS NOT NULL
            """
        )


def backfill_duplicate_memberships(
    connection: sqlite3.Connection, run_dir: Path
) -> None:
    duplicates = connection.execute(
        """
        SELECT page_number, item_index, asset_id
        FROM issues WHERE code = 'duplicate_asset_id'
        ORDER BY issue_id
        """
    ).fetchall()
    with connection:
        for duplicate in duplicates:
            path = raw_page_path(run_dir, duplicate["page_number"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            item = payload["items"][duplicate["item_index"]]
            job = item.get("job") if isinstance(item, dict) else None
            folder_id = job.get("folder_id") if isinstance(job, dict) else None
            if isinstance(folder_id, str) and folder_id:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO asset_folder_memberships(
                        asset_id, folder_id, first_seen_page
                    ) VALUES (?, ?, ?)
                    """,
                    (duplicate["asset_id"], folder_id, duplicate["page_number"]),
                )


def insert_issue(
    connection: sqlite3.Connection,
    *,
    page_number: int,
    value: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO issues(
            page_number, item_index, asset_id, severity, code, details_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            page_number,
            value["item_index"],
            value["asset_id"],
            value["severity"],
            value["code"],
            canonical_json(value["details"]),
        ),
    )


def commit_page(
    connection: sqlite3.Connection,
    page: dict[str, Any],
    *,
    raw_path: Path,
) -> dict[str, Any]:
    page_number = page["page_number"]
    existing = connection.execute(
        "SELECT * FROM pages WHERE page_number = ?", (page_number,)
    ).fetchone()
    if existing is not None:
        return dict(existing)

    raw_bytes = raw_path.read_bytes()
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    asset_id_count = 0
    prompt_record_count = 0
    error_count = 0
    warning_count = 0
    with connection:
        for parsed in page["items"]:
            parse_status = "ok" if not parsed["issues"] else "issues"
            connection.execute(
                """
                INSERT INTO item_occurrences(
                    page_number, item_index, asset_id, item_type, parse_status
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    page_number,
                    parsed["item_index"],
                    parsed["asset_id"],
                    parsed["item_type"],
                    parse_status,
                ),
            )
            for value in parsed["issues"]:
                insert_issue(connection, page_number=page_number, value=value)
                if value["severity"] == "error":
                    error_count += 1
                else:
                    warning_count += 1

            asset = parsed["asset"]
            if asset is None:
                continue
            asset_id_count += 1
            prompt = parsed["prompt"]
            if prompt is not None:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO prompts(
                        prompt_sha256, prompt_text, source_prompt_chars,
                        analysis_prompt_chars, url_redaction_count, first_asset_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prompt["prompt_sha256"],
                        prompt["prompt_text"],
                        prompt["source_prompt_chars"],
                        prompt["analysis_prompt_chars"],
                        prompt["url_redaction_count"],
                        asset["asset_id"],
                    ),
                )
                prompt_record_count += 1
            try:
                connection.execute(
                    """
                    INSERT INTO assets(
                        asset_id, folder_id, item_type, asset_type, status,
                        job_set_type, model, created_at_unix, width, height,
                        duration_seconds, resolution, prompt_sha256, source_page,
                        source_item_index, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        asset["asset_id"],
                        asset["folder_id"],
                        asset["item_type"],
                        asset["asset_type"],
                        asset["status"],
                        asset["job_set_type"],
                        asset["model"],
                        asset["created_at_unix"],
                        asset["width"],
                        asset["height"],
                        asset["duration_seconds"],
                        asset["resolution"],
                        asset["prompt_sha256"],
                        asset["source_page"],
                        asset["source_item_index"],
                        page["fetched_at"],
                    ),
                )
            except sqlite3.IntegrityError:
                duplicate = issue(
                    "duplicate_asset_id",
                    "error",
                    item_index=parsed["item_index"],
                    asset_id=asset["asset_id"],
                    duplicate_page=page_number,
                )
                insert_issue(connection, page_number=page_number, value=duplicate)
                error_count += 1
            if asset["folder_id"] is not None:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO asset_folder_memberships(
                        asset_id, folder_id, first_seen_page
                    ) VALUES (?, ?, ?)
                    """,
                    (asset["asset_id"], asset["folder_id"], page_number),
                )

        connection.execute(
            """
            INSERT INTO pages(
                page_number, cursor_requested_json, next_cursor_json,
                received_items, asset_id_count, prompt_record_count,
                error_count, warning_count, raw_path, raw_bytes, raw_sha256,
                source_endpoint, fetched_at, request_attempts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                page_number,
                canonical_json(page["cursor_requested"]),
                canonical_json(page["next_cursor"]),
                page["received_items"],
                asset_id_count,
                prompt_record_count,
                error_count,
                warning_count,
                str(raw_path),
                len(raw_bytes),
                raw_hash,
                page["source_endpoint"],
                page["fetched_at"],
                page["request_attempts"],
            ),
        )
    row = connection.execute(
        "SELECT * FROM pages WHERE page_number = ?", (page_number,)
    ).fetchone()
    assert row is not None
    return dict(row)


def initial_checkpoint(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project_id": config["project_id"],
        "next_page_number": 1,
        "next_cursor": None,
        "seen_request_cursors": [],
        "received_items": 0,
        "asset_id_count": 0,
        "prompt_record_count": 0,
        "complete": False,
        "fatal_error": None,
        "last_error": None,
        "updated_at": utc_now(),
    }


def advance_checkpoint(
    checkpoint: dict[str, Any], page_row: dict[str, Any]
) -> dict[str, Any]:
    page_number = page_row["page_number"]
    if page_number != checkpoint["next_page_number"]:
        raise ValueError(
            f"cannot advance with page {page_number}; expected {checkpoint['next_page_number']}"
        )
    cursor_requested = json.loads(page_row["cursor_requested_json"])
    next_cursor = json.loads(page_row["next_cursor_json"])
    if cursor_requested != checkpoint["next_cursor"]:
        raise ValueError(f"page {page_number} cursor does not match checkpoint")
    requested_key = cursor_key(cursor_requested)
    if requested_key in checkpoint["seen_request_cursors"]:
        raise ValueError(f"page {page_number} repeats a requested cursor")

    updated = json.loads(json.dumps(checkpoint))
    updated["seen_request_cursors"].append(requested_key)
    updated["received_items"] += page_row["received_items"]
    updated["asset_id_count"] += page_row["asset_id_count"]
    updated["prompt_record_count"] += page_row["prompt_record_count"]
    updated["next_page_number"] += 1
    updated["next_cursor"] = next_cursor
    updated["last_error"] = None
    if page_row["received_items"] == 0 and next_cursor is not None:
        updated["fatal_error"] = "empty page returned a continuation cursor"
    elif (
        next_cursor is not None
        and cursor_key(next_cursor) in updated["seen_request_cursors"]
    ):
        updated["fatal_error"] = "API returned a repeated cursor"
    elif next_cursor is None:
        updated["complete"] = True
    updated["updated_at"] = utc_now()
    return updated


def query_distribution(
    connection: sqlite3.Connection, field: str
) -> dict[str, int]:
    allowed = {"asset_type", "job_set_type", "model", "status"}
    if field not in allowed:
        raise ValueError(f"unsupported distribution field: {field}")
    rows = connection.execute(
        f"SELECT COALESCE(CAST({field} AS TEXT), '<null>') AS value, COUNT(*) AS count "
        f"FROM assets GROUP BY {field} ORDER BY value"
    ).fetchall()
    return {row["value"]: row["count"] for row in rows}


def write_status(
    connection: sqlite3.Connection,
    *,
    run_dir: Path,
    config: dict[str, Any],
    checkpoint: dict[str, Any],
    network_requests_this_invocation: int,
) -> dict[str, Any]:
    scalar = lambda query: connection.execute(query).fetchone()[0]
    pages_committed = scalar("SELECT COUNT(*) FROM pages")
    received_items = scalar("SELECT COALESCE(SUM(received_items), 0) FROM pages")
    item_occurrences = scalar("SELECT COUNT(*) FROM item_occurrences")
    unique_assets = scalar("SELECT COUNT(*) FROM assets")
    prompt_assets = scalar(
        "SELECT COUNT(*) FROM assets WHERE prompt_sha256 IS NOT NULL"
    )
    unique_prompts = scalar("SELECT COUNT(*) FROM prompts")
    duplicate_prompt_groups = scalar(
        """
        SELECT COUNT(*) FROM (
            SELECT prompt_sha256 FROM assets
            WHERE prompt_sha256 IS NOT NULL
            GROUP BY prompt_sha256 HAVING COUNT(*) > 1
        )
        """
    )
    duplicate_asset_issues = scalar(
        "SELECT COUNT(*) FROM issues WHERE code = 'duplicate_asset_id'"
    )
    unsupported_item_issues = scalar(
        "SELECT COUNT(*) FROM issues WHERE code = 'unsupported_item_type'"
    )
    error_issues = scalar("SELECT COUNT(*) FROM issues WHERE severity = 'error'")
    warning_issues = scalar("SELECT COUNT(*) FROM issues WHERE severity = 'warning'")
    stored_prompt_urls = scalar(
        """
        SELECT COUNT(*) FROM prompts
        WHERE LOWER(prompt_text) LIKE '%http://%'
           OR LOWER(prompt_text) LIKE '%https://%'
        """
    )
    unknown_folder_assets = scalar(
        """
        SELECT COUNT(*) FROM assets a
        LEFT JOIN folders f ON f.folder_id = a.folder_id
        WHERE f.folder_id IS NULL
        """
    )
    issue_types = {
        row["code"]: row["count"]
        for row in connection.execute(
            "SELECT code, COUNT(*) AS count FROM issues GROUP BY code ORDER BY code"
        ).fetchall()
    }
    complete = bool(checkpoint["complete"])
    expected = config["expected_asset_count"]
    accounted_occurrences = (
        unique_assets + duplicate_asset_issues + unsupported_item_issues
    )
    checks = {
        "crawl_complete": {"actual": complete, "expected": True, "passed": complete},
        "api_item_count": {
            "actual": received_items,
            "expected": expected,
            "passed": complete and received_items == expected,
        },
        "item_occurrence_count": {
            "actual": item_occurrences,
            "expected": expected,
            "passed": complete and item_occurrences == expected,
        },
        "accounted_occurrence_count": {
            "actual": accounted_occurrences,
            "expected": expected,
            "passed": complete and accounted_occurrences == expected,
        },
        "stored_prompt_url_count": {
            "actual": stored_prompt_urls,
            "expected": 0,
            "passed": stored_prompt_urls == 0,
        },
    }
    coverage_checks_passed = all(check["passed"] for check in checks.values())
    if checkpoint.get("fatal_error") or checkpoint.get("last_error"):
        status = "failed"
    elif not complete:
        status = "paused"
    elif coverage_checks_passed and error_issues == 0:
        status = "passed"
    else:
        status = "completed_with_issues"

    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": status,
        "project_id": config["project_id"],
        "expected_asset_count": expected,
        "page_size": config["page_size"],
        "include_subfolders": True,
        "pages_committed": pages_committed,
        "received_items": received_items,
        "item_occurrence_count": item_occurrences,
        "unique_asset_count": unique_assets,
        "duplicate_asset_occurrence_count": duplicate_asset_issues,
        "unsupported_item_occurrence_count": unsupported_item_issues,
        "accounted_occurrence_count": accounted_occurrences,
        "assets_with_non_empty_prompt": prompt_assets,
        "assets_without_prompt": unique_assets - prompt_assets,
        "unique_prompt_count": unique_prompts,
        "exact_duplicate_prompt_groups": duplicate_prompt_groups,
        "exact_duplicate_prompt_extra_records": prompt_assets - unique_prompts,
        "unknown_folder_asset_count": unknown_folder_assets,
        "error_issue_count": error_issues,
        "warning_issue_count": warning_issues,
        "issue_types": issue_types,
        "distributions": {
            "asset_type": query_distribution(connection, "asset_type"),
            "job_set_type": query_distribution(connection, "job_set_type"),
            "model": query_distribution(connection, "model"),
            "status": query_distribution(connection, "status"),
        },
        "network_requests_this_invocation": network_requests_this_invocation,
        "checks": checks,
        "coverage_checks_passed": coverage_checks_passed,
        "checkpoint_complete": complete,
        "fatal_error": checkpoint.get("fatal_error"),
        "last_error": checkpoint.get("last_error"),
        "database_path": str(run_dir / "corpus.sqlite3"),
        "raw_pages_path": str(run_dir / "pages" / "raw"),
    }
    write_json_atomic(run_dir / "status.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Crawl every public Prompt in one Higgsfield project through a single "
            "root cursor, preserving raw pages and indexing unique Prompt text in SQLite."
        )
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--retry-base-delay", type=float, default=1.0)
    parser.add_argument("--retry-max-delay", type=float, default=8.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-response-bytes", type=int, default=30_000_000)
    parser.add_argument("--progress-every", type=int, default=10)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.page_size <= 100:
        raise ValueError("page size must be between 1 and 100")
    if args.max_pages is not None and args.max_pages < 1:
        raise ValueError("max pages must be positive")
    if args.request_delay < 0:
        raise ValueError("request delay cannot be negative")
    if args.max_attempts < 1:
        raise ValueError("max attempts must be positive")
    if args.progress_every < 1:
        raise ValueError("progress interval must be positive")


def load_inventory(path: Path, project_id: str) -> tuple[list[dict[str, Any]], int]:
    inventory = load_json_object(path)
    folders = inventory.get("folders")
    if inventory.get("status") != "passed" or not isinstance(folders, list):
        raise ValueError("folder inventory is not complete and passed")
    roots = [folder for folder in folders if folder["folder_id"] == project_id]
    if len(roots) != 1:
        raise ValueError("folder inventory does not contain the requested project root")
    return folders, roots[0]["reported_asset_count"]


def main() -> int:
    args = parse_args()
    connection: sqlite3.Connection | None = None
    try:
        validate_args(args)
        folders, expected_count = load_inventory(args.inventory, args.project_id)
        config = {
            "schema_version": 1,
            "project_id": args.project_id,
            "expected_asset_count": expected_count,
            "page_size": args.page_size,
            "include_subfolders": True,
            "inventory_fingerprint": inventory_fingerprint(folders),
        }
        args.run_dir.mkdir(parents=True, exist_ok=True)
        config_path = args.run_dir / "config.json"
        checkpoint_path = args.run_dir / "checkpoint.json"
        event_log = args.run_dir / "events.jsonl"
        if config_path.exists():
            if load_json_object(config_path) != config:
                raise ValueError("run configuration differs; use a new run directory")
        else:
            write_json_atomic(config_path, config)
        if checkpoint_path.exists():
            checkpoint = load_json_object(checkpoint_path)
        else:
            checkpoint = initial_checkpoint(config)
            write_json_atomic(checkpoint_path, checkpoint)

        connection = connect_database(args.run_dir / "corpus.sqlite3")
        seed_database(connection, config=config, folders=folders)
        backfill_duplicate_memberships(connection, args.run_dir)
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as error:
        if connection is not None:
            connection.close()
        print(f"Cannot prepare project crawl: {error}", file=sys.stderr)
        return 1

    stats = {"network_requests": 0}
    pages_committed_this_invocation = 0
    last_request_finished_at: float | None = None
    append_event(
        event_log,
        "info",
        "project_crawl_invocation_started",
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
            cursor = checkpoint["next_cursor"]
            committed = connection.execute(
                "SELECT * FROM pages WHERE page_number = ?", (page_number,)
            ).fetchone()
            if committed is not None:
                page_row = dict(committed)
                append_event(
                    event_log,
                    "info",
                    "recovered_committed_page",
                    page_number=page_number,
                )
            else:
                source_url = build_url(args.project_id, args.page_size, True, cursor)
                raw_path = raw_page_path(args.run_dir, page_number)
                if raw_path.exists():
                    response_text = raw_path.read_text(encoding="utf-8")
                    request_attempts = 0
                    fetched_at = utc_now()
                    append_event(
                        event_log,
                        "info",
                        "recovered_raw_project_page",
                        page_number=page_number,
                    )
                else:
                    if last_request_finished_at is not None:
                        elapsed = time.monotonic() - last_request_finished_at
                        if elapsed < args.request_delay:
                            time.sleep(args.request_delay - elapsed)
                    _, response_text, request_attempts = request_page(
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
                page = parse_page(
                    response_text,
                    page_number=page_number,
                    cursor_requested=cursor,
                    source_endpoint=source_url,
                    fetched_at=fetched_at,
                    request_attempts=request_attempts,
                )
                page_row = commit_page(connection, page, raw_path=raw_path)
            checkpoint = advance_checkpoint(checkpoint, page_row)
            write_json_atomic(checkpoint_path, checkpoint)
            pages_committed_this_invocation += 1
            if pages_committed_this_invocation % args.progress_every == 0:
                print(
                    json.dumps(
                        {
                            "progress_pages": checkpoint["next_page_number"] - 1,
                            "progress_items": checkpoint["received_items"],
                            "network_requests": stats["network_requests"],
                        }
                    ),
                    flush=True,
                )
    except KeyboardInterrupt:
        append_event(
            event_log,
            "warning",
            "project_crawl_interrupted",
            next_page_number=checkpoint["next_page_number"],
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, sqlite3.Error) as error:
        checkpoint["last_error"] = repr(error)
        checkpoint["updated_at"] = utc_now()
        write_json_atomic(checkpoint_path, checkpoint)
        append_event(event_log, "error", "project_crawl_stopped", error=repr(error))
        print(f"Project crawl stopped: {error}", file=sys.stderr)

    report = write_status(
        connection,
        run_dir=args.run_dir,
        config=config,
        checkpoint=checkpoint,
        network_requests_this_invocation=stats["network_requests"],
    )
    append_event(
        event_log,
        "info",
        "project_crawl_invocation_finished",
        status=report["status"],
        pages_committed=pages_committed_this_invocation,
        network_requests=stats["network_requests"],
    )
    connection.close()
    print(
        json.dumps(
            {
                "status": report["status"],
                "pages_committed": report["pages_committed"],
                "received_items": report["received_items"],
                "unique_asset_count": report["unique_asset_count"],
                "assets_with_non_empty_prompt": report[
                    "assets_with_non_empty_prompt"
                ],
                "unique_prompt_count": report["unique_prompt_count"],
                "error_issue_count": report["error_issue_count"],
                "warning_issue_count": report["warning_issue_count"],
                "network_requests_this_invocation": stats["network_requests"],
                "checkpoint_complete": report["checkpoint_complete"],
                "report": str(args.run_dir / "status.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if checkpoint.get("last_error") or checkpoint.get("fatal_error"):
        return 2
    if checkpoint["complete"] and not report["coverage_checks_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
