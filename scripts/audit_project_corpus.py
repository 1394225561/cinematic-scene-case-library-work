from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from crawl_folder_prompts import load_json_object
from probe_higgsfield import utc_now, write_json_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "project-corpus"
WHITESPACE_RE = re.compile(r"\s+")
NUMBER_RE = re.compile(r"(?<![\w.])[+-]?\d+(?:\.\d+)?%?(?![\w.])")


def format_normalize(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip().casefold()


def numeric_normalize(text: str) -> str:
    return NUMBER_RE.sub("<number>", format_normalize(text))


def percentile(sorted_values: list[int], fraction: float) -> int | None:
    if not sorted_values:
        return None
    index = round((len(sorted_values) - 1) * fraction)
    return sorted_values[index]


def dict_rows(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def query_distribution(
    connection: sqlite3.Connection, field: str
) -> dict[str, int]:
    allowed = {"asset_type", "job_set_type", "model", "status"}
    if field not in allowed:
        raise ValueError(f"unsupported distribution field: {field}")
    rows = connection.execute(
        f"SELECT COALESCE(CAST({field} AS TEXT), '<null>') AS value, "
        f"COUNT(*) AS count FROM assets GROUP BY {field} ORDER BY value"
    ).fetchall()
    return {row["value"]: row["count"] for row in rows}


def prompt_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return dict_rows(
        connection.execute(
            """
            SELECT p.prompt_sha256, p.prompt_text, p.source_prompt_chars,
                   p.analysis_prompt_chars, p.url_redaction_count,
                   p.first_asset_id, COUNT(a.asset_id) AS asset_count
            FROM prompts p
            JOIN assets a ON a.prompt_sha256 = p.prompt_sha256
            GROUP BY p.prompt_sha256
            ORDER BY p.prompt_sha256
            """
        )
    )


def exact_clusters(
    connection: sqlite3.Connection,
    prompts_by_hash: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    assets_by_prompt: dict[str, list[str]] = defaultdict(list)
    for row in connection.execute(
        """
        SELECT prompt_sha256, asset_id FROM assets
        WHERE prompt_sha256 IS NOT NULL
        ORDER BY prompt_sha256, asset_id
        """
    ):
        assets_by_prompt[row["prompt_sha256"]].append(row["asset_id"])
    return [
        {
            "prompt_sha256": prompt_hash,
            "source_prompt_chars": prompts_by_hash[prompt_hash][
                "source_prompt_chars"
            ],
            "asset_count": len(asset_ids),
            "asset_ids": asset_ids,
        }
        for prompt_hash, asset_ids in sorted(assets_by_prompt.items())
    ]


def normalized_candidate_groups(
    prompts: list[dict[str, Any]],
    *,
    normalizer: Any,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for prompt in prompts:
        normalized = normalizer(prompt["prompt_text"])
        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        grouped[fingerprint].append(prompt)
    candidates = []
    for fingerprint, group in grouped.items():
        if len(group) < 2:
            continue
        candidates.append(
            {
                "normalized_fingerprint": fingerprint,
                "unique_prompt_count": len(group),
                "total_asset_count": sum(prompt["asset_count"] for prompt in group),
                "prompts": [
                    {
                        "prompt_sha256": prompt["prompt_sha256"],
                        "source_prompt_chars": prompt["source_prompt_chars"],
                        "asset_count": prompt["asset_count"],
                    }
                    for prompt in sorted(
                        group, key=lambda value: value["prompt_sha256"]
                    )
                ],
            }
        )
    candidates.sort(
        key=lambda group: (
            -group["unique_prompt_count"],
            -group["total_asset_count"],
            group["normalized_fingerprint"],
        )
    )
    return candidates


def verify_raw_pages(
    connection: sqlite3.Connection,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for row in connection.execute(
        """
        SELECT page_number, received_items, raw_path, raw_bytes, raw_sha256
        FROM pages ORDER BY page_number
        """
    ):
        path = Path(row["raw_path"])
        if not path.exists():
            mismatches.append(
                {"page_number": row["page_number"], "code": "raw_page_missing"}
            )
            continue
        body = path.read_bytes()
        actual_hash = hashlib.sha256(body).hexdigest()
        entry = {
            "page_number": row["page_number"],
            "received_items": row["received_items"],
            "raw_path": str(path),
            "raw_bytes": len(body),
            "raw_sha256": actual_hash,
        }
        manifest.append(entry)
        if len(body) != row["raw_bytes"] or actual_hash != row["raw_sha256"]:
            mismatches.append(
                {
                    "page_number": row["page_number"],
                    "code": "raw_page_hash_or_size_mismatch",
                    "expected_bytes": row["raw_bytes"],
                    "actual_bytes": len(body),
                    "expected_sha256": row["raw_sha256"],
                    "actual_sha256": actual_hash,
                }
            )
    return manifest, mismatches


def event_counts(path: Path) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts: Counter[str] = Counter()
    errors: list[dict[str, Any]] = []
    if not path.exists():
        return {}, [{"code": "event_log_missing"}]
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(
                {
                    "code": "event_log_parse_error",
                    "line_number": line_number,
                    "error": str(error),
                }
            )
            continue
        if isinstance(event, dict):
            counts[str(event.get("code"))] += 1
    return dict(sorted(counts.items())), errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a completed Higgsfield project Prompt SQLite corpus."
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir or args.run_dir / "audit"
    status = load_json_object(args.run_dir / "status.json")
    checkpoint = load_json_object(args.run_dir / "checkpoint.json")
    if not checkpoint.get("complete"):
        raise SystemExit("project crawl checkpoint is not complete")

    connection = sqlite3.connect(args.run_dir / "corpus.sqlite3")
    connection.row_factory = sqlite3.Row
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    prompts = prompt_rows(connection)
    prompts_by_hash = {prompt["prompt_sha256"]: prompt for prompt in prompts}
    clusters = exact_clusters(connection, prompts_by_hash)
    cluster_sizes = Counter(cluster["asset_count"] for cluster in clusters)

    format_candidates = normalized_candidate_groups(
        prompts, normalizer=format_normalize
    )
    numeric_candidates = normalized_candidate_groups(
        prompts, normalizer=numeric_normalize
    )
    write_json_atomic(
        output_dir / "near-duplicate-candidates.json",
        {
            "schema_version": 1,
            "generated_at": utc_now(),
            "policy": (
                "Candidate-only grouping. Do not merge or score by frequency. "
                "format groups ignore case and whitespace; numeric groups also "
                "replace standalone numeric tokens."
            ),
            "format_normalized_groups": format_candidates,
            "numeric_normalized_groups": numeric_candidates,
        },
    )

    write_json_atomic(
        output_dir / "exact-prompt-clusters.json",
        {
            "schema_version": 1,
            "generated_at": utc_now(),
            "policy": (
                "Preserve every asset ID. Analyze each exact Prompt hash once; "
                "asset frequency is not a quality score."
            ),
            "clusters": clusters,
        },
    )

    lengths = sorted(prompt["source_prompt_chars"] for prompt in prompts)
    short_threshold = percentile(lengths, 0.01)
    long_threshold = percentile(lengths, 0.99)
    outlier_record = lambda prompt: {
        "prompt_sha256": prompt["prompt_sha256"],
        "source_prompt_chars": prompt["source_prompt_chars"],
        "asset_count": prompt["asset_count"],
        "first_asset_id": prompt["first_asset_id"],
    }
    short_candidates = [
        outlier_record(prompt)
        for prompt in prompts
        if short_threshold is not None
        and prompt["source_prompt_chars"] <= short_threshold
    ]
    long_candidates = [
        outlier_record(prompt)
        for prompt in prompts
        if long_threshold is not None
        and prompt["source_prompt_chars"] >= long_threshold
    ]
    short_candidates.sort(key=lambda value: value["source_prompt_chars"])
    long_candidates.sort(key=lambda value: -value["source_prompt_chars"])
    write_json_atomic(
        output_dir / "prompt-length-outliers.json",
        {
            "schema_version": 1,
            "generated_at": utc_now(),
            "method": "Candidate-only bottom/top one percent of unique Prompt length.",
            "statistics": {
                "unique_prompt_count": len(lengths),
                "minimum": lengths[0] if lengths else None,
                "p01": short_threshold,
                "p05": percentile(lengths, 0.05),
                "median": percentile(lengths, 0.50),
                "p95": percentile(lengths, 0.95),
                "p99": long_threshold,
                "maximum": lengths[-1] if lengths else None,
            },
            "short_candidates": short_candidates,
            "long_candidates": long_candidates,
        },
    )

    primary_folder_distribution = dict_rows(
        connection.execute(
            """
            SELECT a.folder_id, COALESCE(f.name, '<unknown>') AS folder_name,
                   COUNT(*) AS asset_count,
                   SUM(CASE WHEN a.prompt_sha256 IS NOT NULL THEN 1 ELSE 0 END)
                       AS assets_with_prompt,
                   COUNT(DISTINCT a.prompt_sha256) AS unique_prompt_count
            FROM assets a LEFT JOIN folders f ON f.folder_id = a.folder_id
            GROUP BY a.folder_id, f.name
            ORDER BY asset_count DESC, a.folder_id
            """
        )
    )
    membership_distribution = dict_rows(
        connection.execute(
            """
            SELECT m.folder_id, COALESCE(f.name, '<unknown>') AS folder_name,
                   COUNT(*) AS asset_membership_count
            FROM asset_folder_memberships m
            LEFT JOIN folders f ON f.folder_id = m.folder_id
            GROUP BY m.folder_id, f.name
            ORDER BY asset_membership_count DESC, m.folder_id
            """
        )
    )
    multi_folder_assets = dict_rows(
        connection.execute(
            """
            SELECT m.asset_id, COUNT(*) AS folder_count,
                   GROUP_CONCAT(m.folder_id, ',') AS folder_ids
            FROM asset_folder_memberships m
            GROUP BY m.asset_id HAVING COUNT(*) > 1
            ORDER BY m.asset_id
            """
        )
    )
    write_json_atomic(
        output_dir / "folder-statistics.json",
        {
            "schema_version": 1,
            "generated_at": utc_now(),
            "primary_folder_distribution": primary_folder_distribution,
            "membership_distribution": membership_distribution,
            "multi_folder_assets": multi_folder_assets,
        },
    )

    monthly_distribution = {
        row["month"]: row["count"]
        for row in connection.execute(
            """
            SELECT COALESCE(strftime('%Y-%m', created_at_unix, 'unixepoch'),
                            '<null>') AS month,
                   COUNT(*) AS count
            FROM assets GROUP BY month ORDER BY month
            """
        )
    }
    empty_prompt_distribution = dict_rows(
        connection.execute(
            """
            SELECT COALESCE(a.job_set_type, '<null>') AS job_set_type,
                   COALESCE(a.model, '<null>') AS model,
                   COALESCE(a.asset_type, '<null>') AS asset_type,
                   COUNT(*) AS count
            FROM assets a WHERE a.prompt_sha256 IS NULL
            GROUP BY a.job_set_type, a.model, a.asset_type
            ORDER BY count DESC
            """
        )
    )
    write_json_atomic(
        output_dir / "prompt-statistics.json",
        {
            "schema_version": 1,
            "generated_at": utc_now(),
            "asset_distributions": {
                "asset_type": query_distribution(connection, "asset_type"),
                "job_set_type": query_distribution(connection, "job_set_type"),
                "model": query_distribution(connection, "model"),
                "status": query_distribution(connection, "status"),
                "created_month": monthly_distribution,
            },
            "exact_prompt_cluster_size_distribution": dict(
                sorted(cluster_sizes.items())
            ),
            "exact_prompt_singleton_count": cluster_sizes.get(1, 0),
            "exact_prompt_duplicate_group_count": sum(
                count for size, count in cluster_sizes.items() if size > 1
            ),
            "largest_exact_prompt_groups": sorted(
                (
                    {
                        "prompt_sha256": cluster["prompt_sha256"],
                        "asset_count": cluster["asset_count"],
                        "source_prompt_chars": cluster["source_prompt_chars"],
                    }
                    for cluster in clusters
                ),
                key=lambda value: (-value["asset_count"], value["prompt_sha256"]),
            )[:100],
            "empty_prompt_distribution": empty_prompt_distribution,
        },
    )

    manifest, raw_mismatches = verify_raw_pages(connection)
    write_json_atomic(
        output_dir / "raw-page-manifest.json",
        {
            "schema_version": 1,
            "generated_at": utc_now(),
            "pages": manifest,
        },
    )
    event_code_counts, event_errors = event_counts(args.run_dir / "events.jsonl")
    issues = dict_rows(
        connection.execute(
            """
            SELECT issue_id, page_number, item_index, asset_id,
                   severity, code, details_json
            FROM issues ORDER BY issue_id
            """
        )
    )
    page_numbers = [
        row[0]
        for row in connection.execute(
            "SELECT page_number FROM pages ORDER BY page_number"
        )
    ]
    cursor_values = [
        row[0]
        for row in connection.execute(
            "SELECT cursor_requested_json FROM pages ORDER BY page_number"
        )
    ]
    expected_occurrences = status["expected_asset_count"]
    accounted_occurrences = (
        status["unique_asset_count"]
        + status.get("duplicate_asset_occurrence_count", 0)
        + status.get("unsupported_item_occurrence_count", 0)
    )
    checks = {
        "sqlite_integrity": integrity == "ok",
        "checkpoint_complete": bool(checkpoint["complete"]),
        "api_item_count": status["received_items"] == expected_occurrences,
        "item_occurrence_count": status["item_occurrence_count"]
        == expected_occurrences,
        "accounted_occurrence_count": accounted_occurrences
        == expected_occurrences,
        "page_sequence_contiguous": page_numbers
        == list(range(1, len(page_numbers) + 1)),
        "requested_cursors_unique": len(cursor_values) == len(set(cursor_values)),
        "last_cursor_is_null": connection.execute(
            "SELECT next_cursor_json FROM pages ORDER BY page_number DESC LIMIT 1"
        ).fetchone()[0]
        == "null",
        "raw_page_count_matches": len(manifest) == len(page_numbers),
        "raw_page_hashes_match": not raw_mismatches,
        "event_log_parses": not event_errors,
        "stored_prompt_urls_absent": status["checks"]["stored_prompt_url_count"][
            "passed"
        ],
        "unknown_folder_assets_absent": status["unknown_folder_asset_count"] == 0,
    }
    reconciliation = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "passed_with_audited_source_issues"
        if all(checks.values())
        else "failed",
        "project_id": status["project_id"],
        "expected_api_occurrences": expected_occurrences,
        "api_occurrences": status["received_items"],
        "unique_assets": status["unique_asset_count"],
        "duplicate_asset_occurrences": status.get(
            "duplicate_asset_occurrence_count", 0
        ),
        "unsupported_item_occurrences": status.get(
            "unsupported_item_occurrence_count", 0
        ),
        "accounted_occurrences": accounted_occurrences,
        "assets_with_non_empty_prompt": status["assets_with_non_empty_prompt"],
        "assets_without_prompt": status["assets_without_prompt"],
        "unique_prompts": status["unique_prompt_count"],
        "exact_duplicate_prompt_extra_records": status[
            "exact_duplicate_prompt_extra_records"
        ],
        "format_normalized_candidate_groups": len(format_candidates),
        "numeric_normalized_candidate_groups": len(numeric_candidates),
        "sqlite_integrity_check": integrity,
        "raw_page_count": len(manifest),
        "raw_bytes": sum(page["raw_bytes"] for page in manifest),
        "event_code_counts": event_code_counts,
        "issues": issues,
        "raw_page_mismatches": raw_mismatches,
        "event_log_errors": event_errors,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }
    write_json_atomic(output_dir / "reconciliation.json", reconciliation)
    connection.close()
    print(
        json.dumps(
            {
                "status": reconciliation["status"],
                "api_occurrences": reconciliation["api_occurrences"],
                "unique_assets": reconciliation["unique_assets"],
                "assets_with_non_empty_prompt": reconciliation[
                    "assets_with_non_empty_prompt"
                ],
                "unique_prompts": reconciliation["unique_prompts"],
                "raw_page_count": reconciliation["raw_page_count"],
                "raw_page_hash_mismatches": len(raw_mismatches),
                "format_candidate_groups": len(format_candidates),
                "numeric_candidate_groups": len(numeric_candidates),
                "output": str(output_dir / "reconciliation.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if reconciliation["all_checks_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
