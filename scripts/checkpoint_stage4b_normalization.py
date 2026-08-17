from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from normalize_video_prompt_semantics import (
    EXPECTED_VIDEO_PROMPTS,
    QUEUE_CODES,
    STATUS_CODES,
    canonical_json,
    sha256_text,
    source_snapshot_sha256,
    source_state,
)
from probe_higgsfield import write_json_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DATABASE = WORK_ROOT / "data" / "runs" / "project-corpus" / "corpus.sqlite3"
DEFAULT_PREPROCESSED_DATABASE = WORK_ROOT / "data" / "runs" / "stage-4b-preprocessing-full" / "preprocessed.sqlite3"
DEFAULT_STRATIFICATION_DATABASE = WORK_ROOT / "data" / "runs" / "stage-4b-stratification-final" / "stratification.sqlite3"
DEFAULT_NORMALIZATION_RUN = WORK_ROOT / "data" / "runs" / "stage-4b-semantic-normalization-full"
DEFAULT_AUDIT_RUN = WORK_ROOT / "data" / "runs" / "stage-4b-quality-audit-full"
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-4b-5-normalization-checkpoint"
CHECKPOINT_VERSION = "stage4b-normalization-checkpoint-v1"


def json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value


def row_value(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


def connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        connection.close()
        raise RuntimeError(f"integrity_check failed for {path}: {integrity}")
    foreign_keys = connection.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()[0]
    if foreign_keys:
        connection.close()
        raise RuntimeError(f"foreign_key_check failed for {path}: {foreign_keys}")
    return connection


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def count_json_values(rows: Iterable[sqlite3.Row], column: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        values = json_value(row[column], [])
        if isinstance(values, list):
            counts.update(value for value in values if isinstance(value, str))
    return dict(sorted(counts.items()))


def count_json_object_values(rows: Iterable[sqlite3.Row], column: str, key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        values = json_value(row[column], [])
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict) and isinstance(item.get(key), str):
                counts[item[key]] += 1
    return dict(sorted(counts.items()))


def build_hash_mapping(
    source_prompts: dict[str, dict[str, Any]],
    strata: dict[str, sqlite3.Row | dict[str, Any]],
    normalizations: dict[str, sqlite3.Row | dict[str, Any]],
    asset_counts: dict[str, int],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for prompt_sha256 in sorted(normalizations):
        normalization = normalizations[prompt_sha256]
        source = source_prompts.get(prompt_sha256, {})
        stratum = strata.get(prompt_sha256, {})
        records.append(
            {
                "prompt_sha256": prompt_sha256,
                "source_prompt_chars": source.get("source_prompt_chars"),
                "normalized_source_prompt_chars": normalization["source_prompt_chars"],
                "source_input_sha256": normalization["source_input_sha256"],
                "normalization_digest": normalization["normalization_digest"],
                "normalization_status": normalization["normalization_status"],
                "processing_status": normalization["processing_status"],
                "complexity_queue": normalization["complexity_queue"],
                "scene_tags": json_value(normalization["scene_tags_json"], []),
                "text_length_band": row_value(stratum, "text_length_band"),
                "asset_mapping_count": asset_counts.get(prompt_sha256, 0),
            }
        )
    return records


def hash_mapping_digest(records: list[dict[str, Any]]) -> str:
    return sha256_text(canonical_json(records))


def build_issue_register(
    normalizations: dict[str, sqlite3.Row | dict[str, Any]],
    strata: dict[str, sqlite3.Row | dict[str, Any]],
    preprocessing_issue_counts: dict[str, int],
    preprocessing_status_counts: dict[str, int],
) -> dict[str, Any]:
    manual_records: list[dict[str, Any]] = []
    excluded_records: list[dict[str, Any]] = []
    failed_records: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    for prompt_sha256 in sorted(normalizations):
        row = normalizations[prompt_sha256]
        status = row["normalization_status"]
        reasons = json_value(row["status_reasons_json"], [])
        if not isinstance(reasons, list):
            reasons = []
        if status != "normalized":
            reason_counts.update(item for item in reasons if isinstance(item, str))
        record = {
            "prompt_sha256": prompt_sha256,
            "normalization_status": status,
            "processing_status": row["processing_status"],
            "failure_code": row["failure_code"],
            "source_prompt_chars": row["source_prompt_chars"],
            "complexity_queue": row["complexity_queue"],
            "scene_tags": json_value(row_value(strata.get(prompt_sha256), "scene_tags_json"), []),
            "risk_flags": json_value(row["risk_flags_json"], []),
            "status_reasons": reasons,
        }
        if status == "needs_manual_review":
            manual_records.append(record)
        elif status == "excluded_with_reason":
            excluded_records.append(record)
        if row["processing_status"] == "failed" or row["failure_code"]:
            failed_records.append(record)
    return {
        "preprocessing": {
            "processing_status_counts": dict(sorted(preprocessing_status_counts.items())),
            "issue_code_counts": dict(sorted(preprocessing_issue_counts.items())),
        },
        "normalization": {
            "failed_records": failed_records,
            "failed_count": len(failed_records),
            "manual_review_records": manual_records,
            "manual_review_count": len(manual_records),
            "manual_review_reason_counts": dict(sorted(reason_counts.items())),
            "excluded_records": excluded_records,
            "excluded_count": len(excluded_records),
        },
    }


def distribution(rows: list[sqlite3.Row]) -> dict[str, dict[str, int]]:
    return {
        "structure_state": dict(sorted(Counter(row["structure_state"] for row in rows).items())),
        "dialogue_state": dict(sorted(Counter(row["dialogue_state"] for row in rows).items())),
        "duration_state": dict(sorted(Counter(row["duration_state"] for row in rows).items())),
        "text_length_band": dict(sorted(Counter(row["text_length_band"] for row in rows).items())),
        "marker_density_band": dict(sorted(Counter(row["marker_density_band"] for row in rows).items())),
        "reference_density_band": dict(sorted(Counter(row["reference_density_band"] for row in rows).items())),
        "scene_tags": count_json_values(rows, "scene_tags_json"),
        "risk_flags": count_json_values(rows, "risk_flags_json"),
    }


def checkpoint(
    source_database: Path = DEFAULT_SOURCE_DATABASE,
    preprocessed_database: Path = DEFAULT_PREPROCESSED_DATABASE,
    stratification_database: Path = DEFAULT_STRATIFICATION_DATABASE,
    normalization_run: Path = DEFAULT_NORMALIZATION_RUN,
    audit_run: Path = DEFAULT_AUDIT_RUN,
    run_dir: Path = DEFAULT_RUN_DIR,
) -> dict[str, Any]:
    source_database = source_database.resolve()
    preprocessed_database = preprocessed_database.resolve()
    stratification_database = stratification_database.resolve()
    normalization_run = normalization_run.resolve()
    audit_run = audit_run.resolve()
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    before = {
        "source": source_state(source_database),
        "preprocessed": source_state(preprocessed_database),
        "stratification": source_state(stratification_database),
        "normalization": source_state(normalization_run / "semantic_normalization.sqlite3"),
    }
    source = preprocessed = stratification = target = None
    try:
        normalization_report = read_json(normalization_run / "report.json")
        normalization_manifest = read_json(normalization_run / "manifest.json")
        stratification_report = read_json(stratification_database.parent / "report.json")
        stratification_manifest = read_json(stratification_database.parent / "manifest.json")
        audit_report = read_json(audit_run / "report.json")
        audit_manifest = read_json(audit_run / "manifest.json")

        source = connect_readonly(source_database)
        preprocessed = connect_readonly(preprocessed_database)
        stratification = connect_readonly(stratification_database)
        target = connect_readonly(normalization_run / "semantic_normalization.sqlite3")

        source_prompts: dict[str, dict[str, Any]] = {}
        source_hash_errors: list[str] = []
        source_length_errors: list[str] = []
        for row in source.execute("SELECT prompt_sha256,prompt_text,source_prompt_chars FROM prompts ORDER BY prompt_sha256"):
            prompt_sha256 = row["prompt_sha256"]
            source_prompts[prompt_sha256] = {"source_prompt_chars": row["source_prompt_chars"]}
            if sha256_text(row["prompt_text"]) != prompt_sha256:
                source_hash_errors.append(prompt_sha256)
            if len(row["prompt_text"]) != row["source_prompt_chars"]:
                source_length_errors.append(prompt_sha256)

        selected_hashes = set(source_prompts)
        structures = {
            row["prompt_sha256"]: dict(row)
            for row in preprocessed.execute("SELECT prompt_sha256 FROM prompt_structure ORDER BY prompt_sha256")
        }
        preprocessing_status_counts = dict(
            preprocessed.execute("SELECT processing_status,count(*) FROM prompt_structure GROUP BY processing_status ORDER BY processing_status")
        )
        preprocessing_issue_counts = dict(
            preprocessed.execute("SELECT code,count(*) FROM processing_issues GROUP BY code ORDER BY code")
        )
        strata_rows = list(stratification.execute("SELECT * FROM prompt_strata ORDER BY prompt_sha256"))
        strata = {row["prompt_sha256"]: row for row in strata_rows}
        normalization_rows = list(target.execute("SELECT * FROM prompt_normalizations ORDER BY prompt_sha256"))
        normalizations = {row["prompt_sha256"]: row for row in normalization_rows}

        source_assets: dict[str, set[str]] = defaultdict(set)
        for row in source.execute("SELECT prompt_sha256,asset_id FROM assets WHERE prompt_sha256 IS NOT NULL ORDER BY prompt_sha256,asset_id"):
            if row["prompt_sha256"] in normalizations:
                source_assets[row["prompt_sha256"]].add(row["asset_id"])
        target_assets: dict[str, set[str]] = defaultdict(set)
        for row in target.execute("SELECT prompt_sha256,asset_id FROM normalization_assets ORDER BY prompt_sha256,asset_id"):
            target_assets[row["prompt_sha256"]].add(row["asset_id"])
        asset_mapping_errors = [
            prompt_sha256
            for prompt_sha256 in sorted(normalizations)
            if source_assets.get(prompt_sha256, set()) != target_assets.get(prompt_sha256, set())
        ]
        asset_counts = {prompt_sha256: len(asset_ids) for prompt_sha256, asset_ids in target_assets.items()}

        mapping_records = build_hash_mapping(source_prompts, strata, normalizations, asset_counts)
        mapping_digest = hash_mapping_digest(mapping_records)
        issue_register = build_issue_register(
            normalizations,
            strata,
            preprocessing_issue_counts,
            preprocessing_status_counts,
        )

        integrity_check = target.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_error_count = int(target.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()[0])
        database_counts = {
            "prompt_normalizations": len(normalization_rows),
            "normalization_assets": int(target.execute("SELECT count(*) FROM normalization_assets").fetchone()[0]),
            "normalization_evidence": int(target.execute("SELECT count(*) FROM normalization_evidence").fetchone()[0]),
            "normalization_decisions": int(target.execute("SELECT count(*) FROM normalization_decisions").fetchone()[0]),
        }
        status_counts = dict(sorted(Counter(row["normalization_status"] for row in normalization_rows).items()))
        processing_status_counts = dict(sorted(Counter(row["processing_status"] for row in normalization_rows).items()))
        normalization_queue_counts = dict(sorted(Counter(row["complexity_queue"] for row in normalization_rows).items()))
        normalization_distribution = {
            "status": status_counts,
            "processing_status": processing_status_counts,
            "complexity_queue": normalization_queue_counts,
            "scene_tags": count_json_values(normalization_rows, "scene_tags_json"),
            "risk_flags": count_json_values(normalization_rows, "risk_flags_json"),
            "missing_fields": count_json_object_values(normalization_rows, "missing_fields_json", "field"),
            "source_conflicts": count_json_object_values(normalization_rows, "source_conflicts_json", "field"),
        }
        strata_distribution = distribution(strata_rows)

        source.rollback()
        preprocessed.rollback()
        stratification.rollback()
        target.rollback()
        source.close()
        preprocessed.close()
        stratification.close()
        target.close()
        source = preprocessed = stratification = target = None
        after = {
            "source": source_state(source_database),
            "preprocessed": source_state(preprocessed_database),
            "stratification": source_state(stratification_database),
            "normalization": source_state(normalization_run / "semantic_normalization.sqlite3"),
        }
        unchanged = {
            key: source_snapshot_sha256(before[key]) == source_snapshot_sha256(after[key])
            for key in before
        }

        closure_checks = {
            "selected_video_universe": len(normalizations) == EXPECTED_VIDEO_PROMPTS,
            "source_prompt_hash_closure": set(normalizations) <= selected_hashes,
            "preprocessed_prompt_closure": set(normalizations) == set(structures),
            "stratification_prompt_closure": set(normalizations) == set(strata),
            "normalization_status_codes": set(status_counts) <= set(STATUS_CODES),
            "complexity_queue_codes": set(normalization_queue_counts) <= set(QUEUE_CODES),
            "asset_mapping_closure": not asset_mapping_errors,
            "source_hashes": not source_hash_errors,
            "source_lengths": not source_length_errors,
            "target_integrity": integrity_check == "ok" and foreign_key_error_count == 0,
            "normalization_report_pass": normalization_report.get("status") == "pass",
            "stratification_report_pass": stratification_report.get("status") == "pass",
            "audit_report_pass": audit_report.get("status") == "pass" and audit_report.get("failure_count") == 0,
            "normalizer_version": normalization_manifest.get("normalizer_version") == "stage4b-light-semantic-normalization-v6",
            "normalization_digest_consistency": normalization_report.get("logical_target_digest") == audit_report.get("normalization_logical_target_digest"),
            "no_final_prompt_generated": normalization_report.get("final_prompt_generated_count") == 0,
            "source_states_unchanged": all(unchanged.values()),
        }
        recommendations = [
            "Use only normalized records as automatic Stage 5 classification inputs until manual-review records are resolved.",
            "Resolve or explicitly carry the 61 manual-review records; do not silently promote them to normalized.",
            "Preserve duration and take-structure conflicts as source uncertainties during Stage 5 scoring.",
            "Keep described_only reference bindings and do not infer media identity without accessible media bytes.",
            "Do not use duplicate generation counts as a quality score or selection signal.",
            "Do not generate full Seedance or H3 prompts for the entire corpus before Stage 5 selection.",
        ]
        report_payload: dict[str, Any] = {
            "schema_version": 1,
            "checkpoint_version": CHECKPOINT_VERSION,
            "status": "pass" if all(closure_checks.values()) else "fail",
            "selected_prompt_count": len(normalizations),
            "database_counts": database_counts,
            "normalization_distribution": normalization_distribution,
            "stratification_distribution": strata_distribution,
            "parse_failure_summary": issue_register["preprocessing"],
            "manual_review_summary": {
                "count": issue_register["normalization"]["manual_review_count"],
                "reason_counts": issue_register["normalization"]["manual_review_reason_counts"],
                "high_value_count": sum(
                    any(tag in {"action_interaction", "character_performance", "environment_establishing"} for tag in record["scene_tags"])
                    for record in issue_register["normalization"]["manual_review_records"]
                ),
            },
            "excluded_summary": {
                "count": issue_register["normalization"]["excluded_count"],
                "records": issue_register["normalization"]["excluded_records"],
            },
            "unresolved_issues": {
                "normalization_source_conflicts": normalization_distribution["source_conflicts"],
                "manual_review_reason_counts": issue_register["normalization"]["manual_review_reason_counts"],
                "preprocessing_issue_code_counts": preprocessing_issue_counts,
            },
            "recommendations_for_stage5": recommendations,
            "input_reports": {
                "normalization_logical_target_digest": normalization_report.get("logical_target_digest"),
                "stratification_logical_target_digest": stratification_report.get("logical_target_digest"),
                "audit_digest": audit_report.get("audit_digest"),
                "audit_sample_count": audit_report.get("sample_count"),
                "audit_failure_count": audit_report.get("failure_count"),
            },
            "source_snapshot_sha256": source_snapshot_sha256(before["source"]),
            "preprocessed_snapshot_sha256": source_snapshot_sha256(before["preprocessed"]),
            "stratification_snapshot_sha256": source_snapshot_sha256(before["stratification"]),
            "normalization_snapshot_sha256": source_snapshot_sha256(before["normalization"]),
            "source_state_unchanged": unchanged["source"],
            "preprocessed_state_unchanged": unchanged["preprocessed"],
            "stratification_state_unchanged": unchanged["stratification"],
            "normalization_state_unchanged": unchanged["normalization"],
            "hash_mapping_count": len(mapping_records),
            "hash_mapping_sha256": mapping_digest,
            "checks": closure_checks,
            "artifacts": {
                "manifest": str(run_dir / "manifest.json"),
                "hash_mapping": str(run_dir / "hash-mapping.json"),
                "issue_register": str(run_dir / "issue-register.json"),
                "report": str(run_dir / "report.json"),
            },
        }
        report_payload["checkpoint_digest"] = sha256_text(canonical_json(report_payload))
        issue_register_payload = {"schema_version": 1, **issue_register}
        manifest = {
            "schema_version": 1,
            "checkpoint_version": CHECKPOINT_VERSION,
            "normalizer_version": normalization_manifest.get("normalizer_version"),
            "normalizer_config_sha256": normalization_manifest.get("normalizer_config_sha256"),
            "stratifier_config_sha256": stratification_manifest.get("stratifier_config_sha256"),
            "audit_config_sha256": audit_manifest.get("audit_config_sha256"),
            "source_snapshot_sha256": report_payload["source_snapshot_sha256"],
            "preprocessed_snapshot_sha256": report_payload["preprocessed_snapshot_sha256"],
            "stratification_snapshot_sha256": report_payload["stratification_snapshot_sha256"],
            "normalization_snapshot_sha256": report_payload["normalization_snapshot_sha256"],
            "normalization_logical_target_digest": normalization_report.get("logical_target_digest"),
            "stratification_logical_target_digest": stratification_report.get("logical_target_digest"),
            "audit_digest": audit_report.get("audit_digest"),
            "selected_prompt_count": len(mapping_records),
            "hash_mapping_sha256": mapping_digest,
            "issue_register_sha256": sha256_text(canonical_json(issue_register_payload)),
            "checkpoint_digest": report_payload["checkpoint_digest"],
        }
        write_json_atomic(run_dir / "hash-mapping.json", {"schema_version": 1, "records": mapping_records})
        write_json_atomic(run_dir / "issue-register.json", issue_register_payload)
        write_json_atomic(run_dir / "manifest.json", manifest)
        write_json_atomic(run_dir / "report.json", report_payload)
        return report_payload
    finally:
        for connection in (target, source, preprocessed, stratification):
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
                try:
                    connection.close()
                except Exception:
                    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seal Stage 4B-3/4 results as the Stage 4B-5 checkpoint.")
    parser.add_argument("--source-database", type=Path, default=DEFAULT_SOURCE_DATABASE)
    parser.add_argument("--preprocessed-database", type=Path, default=DEFAULT_PREPROCESSED_DATABASE)
    parser.add_argument("--stratification-database", type=Path, default=DEFAULT_STRATIFICATION_DATABASE)
    parser.add_argument("--normalization-run", type=Path, default=DEFAULT_NORMALIZATION_RUN)
    parser.add_argument("--audit-run", type=Path, default=DEFAULT_AUDIT_RUN)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = checkpoint(
            args.source_database,
            args.preprocessed_database,
            args.stratification_database,
            args.normalization_run,
            args.audit_run,
            args.run_dir,
        )
    except Exception as error:
        print(json.dumps({"status": "fail", "error": type(error).__name__, "details": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({key: report[key] for key in ("status", "selected_prompt_count", "hash_mapping_count", "checkpoint_digest")}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
