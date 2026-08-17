from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from normalize_video_prompt_semantics import (
    CONFIG,
    EXTRACTION_PATTERNS,
    MODEL_SYNTAX_RE,
    NORMALIZER_VERSION,
    QUEUE_CODES,
    STATUS_CODES,
    candidate_segments,
    clean_model_syntax,
    duration_observation,
    iter_segments,
    sha256_text,
    source_snapshot_sha256,
    source_state,
)
from preprocess_video_prompt_sample import APPROVED_SAMPLE_HASHES
from probe_higgsfield import write_json_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DATABASE = WORK_ROOT / "data" / "runs" / "project-corpus" / "corpus.sqlite3"
DEFAULT_PREPROCESSED_DATABASE = WORK_ROOT / "data" / "runs" / "stage-4b-preprocessing-full" / "preprocessed.sqlite3"
DEFAULT_STRATIFICATION_DATABASE = WORK_ROOT / "data" / "runs" / "stage-4b-stratification-final" / "stratification.sqlite3"
DEFAULT_NORMALIZATION_RUN = WORK_ROOT / "data" / "runs" / "stage-4b-semantic-normalization-full"
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-4b-quality-audit-full"
AUDIT_VERSION = "stage4b-quality-audit-v1"
EXPECTED_PROMPTS = 6555
PER_STRATUM_SAMPLE = 20

NORMALIZATION_JSON_COLUMNS = (
    "subjects_json",
    "spatial_relations_json",
    "action_summary_json",
    "performance_dialogue_reaction_json",
    "camera_result_json",
    "lighting_json",
    "sound_json",
    "physics_json",
    "continuity_json",
    "constraints_json",
    "material_references_json",
    "missing_fields_json",
    "source_conflicts_json",
    "uncertainty_json",
    "transferability_json",
    "status_reasons_json",
)
NEUTRAL_JSON_COLUMNS = (
    "subjects_json",
    "spatial_relations_json",
    "action_summary_json",
    "performance_dialogue_reaction_json",
    "camera_result_json",
    "lighting_json",
    "sound_json",
    "physics_json",
    "continuity_json",
    "constraints_json",
    "missing_fields_json",
    "source_conflicts_json",
    "uncertainty_json",
    "transferability_json",
)
PROVENANCE_FIELDS = {
    "objective": "objective_text",
    "spatial_relations": "spatial_relations_json",
    "action_summary": "action_summary_json",
    "performance_dialogue_reaction": "performance_dialogue_reaction_json",
    "camera_result": "camera_result_json",
    "lighting": "lighting_json",
    "sound": "sound_json",
    "physics": "physics_json",
    "continuity": "continuity_json",
    "constraints": "constraints_json",
}
AUDIT_CONFIG = {
    "audit_version": AUDIT_VERSION,
    "normalizer_version": NORMALIZER_VERSION,
    "expected_prompt_count": EXPECTED_PROMPTS,
    "per_stratum_sample": PER_STRATUM_SAMPLE,
    "sampling_dimensions": ["complexity_queue", "normalization_status", "scene_tag", "text_length_band", "structure_state", "duration_state"],
    "manual_review_policy": "Include every needs_manual_review record in manual-review.json and every high-value manual record in the main sample.",
    "checks": [
        "source_hash_and_length",
        "prompt_and_strata_closure",
        "asset_mapping_closure",
        "evidence_ranges_and_hashes",
        "decision_evidence_links",
        "field_provenance",
        "dialogue_verbatim",
        "duration_and_conflict_preservation",
        "reference_binding_policy",
        "model_syntax_isolation",
        "transferability_policy",
        "long_prompt_tail_coverage",
        "compressed_candidate_tail_coverage",
        "approved_regression_samples",
    ],
}
AUDIT_CONFIG_SHA256 = sha256_text(json.dumps(AUDIT_CONFIG, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list, str, int, float, bool)):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return value
    return default


def connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        connection.close()
        raise RuntimeError(f"integrity_check failed for {path}")
    if connection.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()[0]:
        connection.close()
        raise RuntimeError(f"foreign_key_check failed for {path}")
    return connection


def group_rows(rows: Iterable[sqlite3.Row], key_name: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        item = dict(row)
        grouped[item[key_name]].append(item)
    return dict(grouped)


def load_inputs(
    source: sqlite3.Connection,
    preprocessed: sqlite3.Connection,
    stratification: sqlite3.Connection,
    target: sqlite3.Connection,
) -> dict[str, Any]:
    prompts = {
        row["prompt_sha256"]: dict(row)
        for row in source.execute("SELECT prompt_sha256,prompt_text,source_prompt_chars,analysis_prompt_chars FROM prompts ORDER BY prompt_sha256")
    }
    source_assets = group_rows(
        source.execute(
            "SELECT prompt_sha256,asset_id,asset_type,item_type,model,duration_seconds,resolution FROM assets WHERE prompt_sha256 IS NOT NULL ORDER BY prompt_sha256,asset_id"
        ),
        "prompt_sha256",
    )
    structures = {
        row["prompt_sha256"]: dict(row)
        for row in preprocessed.execute("SELECT * FROM prompt_structure ORDER BY prompt_sha256")
    }
    issues = group_rows(
        preprocessed.execute("SELECT * FROM processing_issues ORDER BY prompt_sha256,ordinal"),
        "prompt_sha256",
    )
    strata = {
        row["prompt_sha256"]: dict(row)
        for row in stratification.execute("SELECT * FROM prompt_strata ORDER BY prompt_sha256")
    }
    normalizations = {
        row["prompt_sha256"]: dict(row)
        for row in target.execute("SELECT * FROM prompt_normalizations ORDER BY prompt_sha256")
    }
    return {
        "prompts": prompts,
        "source_assets": source_assets,
        "structures": structures,
        "issues": issues,
        "strata": strata,
        "normalizations": normalizations,
    }


def check_value(
    check_counts: dict[str, dict[str, int]],
    sample_checks: dict[str, dict[str, bool]],
    failures: list[dict[str, Any]],
    name: str,
    passed: bool,
    prompt_sha256: str | None,
    details: str | dict[str, Any] | None = None,
) -> bool:
    counts = check_counts.setdefault(name, {"evaluated": 0, "passed": 0, "failed": 0})
    counts["evaluated"] += 1
    if passed:
        counts["passed"] += 1
    else:
        counts["failed"] += 1
        failure = {"check": name, "prompt_sha256": prompt_sha256, "details": details or "check failed"}
        failures.append(failure)
    if prompt_sha256 is not None and prompt_sha256 in sample_checks:
        sample_checks[prompt_sha256][name] = passed
    return passed


def output_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from output_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from output_strings(item)


def direct_field_values(row: dict[str, Any], field: str) -> list[str]:
    payload = json_value(row[PROVENANCE_FIELDS[field]], {})
    if field == "objective":
        return [row["objective_text"]] if row["objective_text"] else []
    if field == "spatial_relations":
        return payload if isinstance(payload, list) else []
    if field == "action_summary":
        return [item.get("summary") for item in payload.get("beats", []) if isinstance(item, dict) and isinstance(item.get("summary"), str)]
    if field == "performance_dialogue_reaction":
        return [item for item in payload.get("performance_segments", []) if isinstance(item, str)]
    if field in {"camera_result", "lighting", "sound", "physics"}:
        return [item for item in payload.get("segments", []) if isinstance(item, str)]
    if field in {"continuity", "constraints"}:
        return payload if isinstance(payload, list) else []
    return []


def check_evidence(
    target: sqlite3.Connection,
    prompt_sha256: str,
    prompt_text: str,
) -> tuple[list[sqlite3.Row], dict[int, sqlite3.Row], list[str]]:
    evidence = list(target.execute("SELECT * FROM normalization_evidence WHERE prompt_sha256=? ORDER BY ordinal", (prompt_sha256,)))
    decisions = list(target.execute("SELECT * FROM normalization_decisions WHERE prompt_sha256=? ORDER BY ordinal", (prompt_sha256,)))
    errors: list[str] = []
    by_ordinal = {row["ordinal"]: row for row in evidence}
    for row in evidence:
        kind = row["evidence_kind"]
        start, end = row["evidence_start"], row["evidence_end"]
        if kind in {"source_span", "full_scan", "fact_ref"} or (kind == "issue_ref" and start is not None):
            if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(prompt_text):
                errors.append(f"evidence_range:{row['ordinal']}")
            elif row["evidence_sha256"] != sha256_text(prompt_text[start:end]):
                errors.append(f"evidence_hash:{row['ordinal']}")
            elif kind == "full_scan" and (start != 0 or end != len(prompt_text)):
                errors.append(f"full_scan_range:{row['ordinal']}")
        elif kind in {"metadata", "none"} and any(value is not None for value in (start, end, row["evidence_sha256"])):
            errors.append(f"non_span_payload:{row['ordinal']}")
    for row in decisions:
        if row["evidence_ordinal"] is None or row["evidence_ordinal"] not in by_ordinal:
            errors.append(f"decision_link:{row['ordinal']}")
    return evidence, by_ordinal, errors


def sample_hashes(data: dict[str, Any]) -> tuple[set[str], dict[str, list[dict[str, str]]], dict[str, list[str]]]:
    normalizations = data["normalizations"]
    strata = data["strata"]
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    memberships: dict[str, list[dict[str, str]]] = defaultdict(list)
    dimension_values: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for prompt_sha256 in sorted(normalizations):
        normalization = normalizations[prompt_sha256]
        stratum = strata.get(prompt_sha256, {})
        values = {
            "complexity_queue": [stratum.get("complexity_queue")],
            "normalization_status": [normalization.get("normalization_status")],
            "scene_tag": json_value(stratum.get("scene_tags_json"), []),
            "text_length_band": [stratum.get("text_length_band")],
            "structure_state": [stratum.get("structure_state")],
            "duration_state": [stratum.get("duration_state")],
        }
        for dimension, raw_values in values.items():
            for value in sorted({item for item in raw_values if isinstance(item, str) and item}):
                dimension_values[dimension][value].append(prompt_sha256)
    selected: set[str] = {prompt_sha256 for prompt_sha256 in APPROVED_SAMPLE_HASHES if prompt_sha256 in normalizations}
    for dimension, value_groups in dimension_values.items():
        for value, hashes in value_groups.items():
            ordered = sorted(hashes, key=lambda item: sha256_text(f"{AUDIT_VERSION}|{dimension}|{value}|{item}"))
            for prompt_sha256 in ordered[: min(PER_STRATUM_SAMPLE, len(ordered))]:
                selected.add(prompt_sha256)
                memberships[prompt_sha256].append({"dimension": dimension, "value": value})
    for prompt_sha256, normalization in normalizations.items():
        if normalization["normalization_status"] == "needs_manual_review":
            selected.add(prompt_sha256)
            memberships[prompt_sha256].append({"dimension": "manual_review", "value": "all"})
    coverage = {
        dimension: {
            value: [prompt_sha256 for prompt_sha256 in hashes if prompt_sha256 in selected]
            for value, hashes in value_groups.items()
        }
        for dimension, value_groups in dimension_values.items()
    }
    return selected, dict(memberships), coverage


def audit(
    source_database: Path = DEFAULT_SOURCE_DATABASE,
    preprocessed_database: Path = DEFAULT_PREPROCESSED_DATABASE,
    stratification_database: Path = DEFAULT_STRATIFICATION_DATABASE,
    normalization_run: Path = DEFAULT_NORMALIZATION_RUN,
    run_dir: Path = DEFAULT_RUN_DIR,
) -> dict[str, Any]:
    source_database = source_database.resolve()
    preprocessed_database = preprocessed_database.resolve()
    stratification_database = stratification_database.resolve()
    normalization_run = normalization_run.resolve()
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    before = {
        "source": source_state(source_database),
        "preprocessed": source_state(preprocessed_database),
        "stratification": source_state(stratification_database),
        "normalization": source_state(normalization_run / "semantic_normalization.sqlite3"),
    }
    source = preprocessed = stratification = target = None
    check_counts: dict[str, dict[str, int]] = {}
    failures: list[dict[str, Any]] = []
    normalization_report = json.loads((normalization_run / "report.json").read_text(encoding="utf-8"))
    normalization_manifest = json.loads((normalization_run / "manifest.json").read_text(encoding="utf-8"))
    try:
        source = connect_readonly(source_database)
        preprocessed = connect_readonly(preprocessed_database)
        stratification = connect_readonly(stratification_database)
        target = connect_readonly(normalization_run / "semantic_normalization.sqlite3")
        data = load_inputs(source, preprocessed, stratification, target)
        selected, memberships, stratum_coverage = sample_hashes(data)
        sample_checks = {prompt_sha256: {} for prompt_sha256 in selected}

        source_hashes = set(data["prompts"])
        strata_hashes = set(data["strata"])
        normalization_hashes = set(data["normalizations"])
        check_value(check_counts, sample_checks, failures, "prompt_and_strata_closure", normalization_hashes == strata_hashes == set(data["structures"]) & normalization_hashes, None, {"normalization": len(normalization_hashes), "strata": len(strata_hashes)})
        check_value(check_counts, sample_checks, failures, "full_universe", len(normalization_hashes) == EXPECTED_PROMPTS and normalization_hashes <= source_hashes, None, {"normalization": len(normalization_hashes), "source": len(source_hashes)})
        check_value(check_counts, sample_checks, failures, "normalization_report_passed", normalization_report.get("status") == "pass" and normalization_manifest.get("normalizer_version") == NORMALIZER_VERSION, None, normalization_manifest.get("normalizer_version"))

        for prompt_sha256, row in data["normalizations"].items():
            prompt = data["prompts"].get(prompt_sha256)
            stratum = data["strata"].get(prompt_sha256)
            structure = data["structures"].get(prompt_sha256)
            issues = data["issues"].get(prompt_sha256, [])
            if prompt is None or stratum is None or structure is None:
                check_value(check_counts, sample_checks, failures, "source_hash_and_length", False, prompt_sha256, "missing source, structure, or stratum")
                continue
            prompt_text = prompt["prompt_text"]
            check_value(check_counts, sample_checks, failures, "source_hash_and_length", sha256_text(prompt_text) == prompt_sha256 and len(prompt_text) == prompt["source_prompt_chars"] == row["source_prompt_chars"], prompt_sha256, {"source_chars": len(prompt_text), "normalized_chars": row["source_prompt_chars"]})
            check_value(check_counts, sample_checks, failures, "stratum_alignment", row["complexity_queue"] == stratum["complexity_queue"] and json_value(row["scene_tags_json"], []) == json_value(stratum["scene_tags_json"], []) and row["complexity_queue"] in QUEUE_CODES, prompt_sha256, {"normalization_queue": row["complexity_queue"], "stratum_queue": stratum["complexity_queue"]})
            for column in NORMALIZATION_JSON_COLUMNS:
                try:
                    json.loads(row[column])
                    ok = True
                except (TypeError, json.JSONDecodeError):
                    ok = False
                check_value(check_counts, sample_checks, failures, "normalization_json", ok, prompt_sha256, column)

            source_asset_ids = {item["asset_id"] for item in data["source_assets"].get(prompt_sha256, [])}
            normalized_assets = list(target.execute("SELECT * FROM normalization_assets WHERE prompt_sha256=? ORDER BY asset_id", (prompt_sha256,)))
            normalized_asset_ids = {item["asset_id"] for item in normalized_assets}
            check_value(check_counts, sample_checks, failures, "asset_mapping_closure", source_asset_ids == normalized_asset_ids and bool(normalized_asset_ids), prompt_sha256, {"source": len(source_asset_ids), "normalized": len(normalized_asset_ids)})
            check_value(check_counts, sample_checks, failures, "asset_media_policy", all(item["media_status"] == "metadata_only" for item in normalized_assets), prompt_sha256)

            evidence, evidence_by_ordinal, evidence_errors = check_evidence(target, prompt_sha256, prompt_text)
            check_value(check_counts, sample_checks, failures, "evidence_ranges_and_hashes", not evidence_errors, prompt_sha256, evidence_errors[:10])
            decisions = list(target.execute("SELECT * FROM normalization_decisions WHERE prompt_sha256=? ORDER BY ordinal", (prompt_sha256,)))
            check_value(check_counts, sample_checks, failures, "decision_evidence_links", all(item["evidence_ordinal"] in evidence_by_ordinal for item in decisions), prompt_sha256)

            neutral_payload = {column: json_value(row[column], None) for column in NEUTRAL_JSON_COLUMNS}
            neutral_text = canonical_json(neutral_payload)
            check_value(check_counts, sample_checks, failures, "model_syntax_isolation", not MODEL_SYNTAX_RE.search(neutral_text) and "<<<" not in neutral_text and ">>>" not in neutral_text, prompt_sha256)
            transferability = json_value(row["transferability_json"], {})
            expected_transfer_status = "portable_scene_intent" if row["normalization_status"] == "normalized" else "blocked_needs_manual_review"
            transfer_ok = all(transferability.get(adapter, {}).get("status") == expected_transfer_status and transferability.get(adapter, {}).get("media_binding") == "none" and not transferability.get(adapter, {}).get("final_prompt_generated") for adapter in ("seedance", "h3")) and transferability.get("model_specific_syntax_removed") == bool(MODEL_SYNTAX_RE.search(prompt_text))
            check_value(check_counts, sample_checks, failures, "transferability_policy", transfer_ok, prompt_sha256, transferability)

            direct_by_field: dict[str, set[str]] = defaultdict(set)
            direct_ranges: dict[str, set[tuple[int, int]]] = defaultdict(set)
            for item in evidence:
                if item["operation"] == "direct" and item["evidence_start"] is not None:
                    start, end = item["evidence_start"], item["evidence_end"]
                    direct_by_field[item["field_name"]].add(clean_model_syntax(prompt_text[start:end]))
                    direct_ranges[item["field_name"]].add((start, end))
            provenance_ok = True
            for field, values in PROVENANCE_FIELDS.items():
                output_values = direct_field_values(row, field)
                expected_values = direct_by_field.get(field, set())
                if field == "objective":
                    provenance_field_ok = not output_values or bool(expected_values) and all(value in output_values[0] for value in expected_values)
                else:
                    provenance_field_ok = not output_values or bool(expected_values) and all(value in expected_values for value in output_values)
                if not provenance_field_ok:
                    provenance_ok = False
            check_value(check_counts, sample_checks, failures, "field_provenance", provenance_ok, prompt_sha256)

            performance = json_value(row["performance_dialogue_reaction_json"], {})
            dialogue_ok = all(isinstance(item.get("line"), str) and item["line"] in prompt_text and not MODEL_SYNTAX_RE.search(item["line"]) for item in performance.get("dialogue_lines", []) if isinstance(item, dict))
            check_value(check_counts, sample_checks, failures, "dialogue_verbatim", dialogue_ok, prompt_sha256)

            duration = json_value(json_value(row["action_summary_json"], {}), {}).get("duration", {})
            expected_duration = duration_observation({"structure": structure})
            conflict_fields = {item.get("field") for item in json_value(row["source_conflicts_json"], []) if isinstance(item, dict)}
            duration_ok = duration == expected_duration
            if expected_duration["provenance"] == "unresolved_conflict":
                duration_ok = duration_ok and "duration" in conflict_fields
            take_conflict = any(item.get("code") == "take_structure_conflict" for item in issues)
            if take_conflict:
                duration_ok = duration_ok and "take_structure" in conflict_fields
            unresolved_ok = all(item.get("resolution", {}).get("status") == "unresolved" and item.get("resolution", {}).get("selected_value") is None for item in json_value(row["source_conflicts_json"], []))
            check_value(check_counts, sample_checks, failures, "duration_and_conflict_preservation", duration_ok and unresolved_ok, prompt_sha256, {"expected_duration": expected_duration, "actual_duration": duration, "conflict_fields": sorted(conflict_fields)})

            references = json_value(row["material_references_json"], [])
            refs_ok = all(item.get("binding_status") == "described_only" and (item.get("source_label") is None or item["source_label"] in prompt_text) and isinstance(item.get("description"), str) and item["description"] for item in references)
            check_value(check_counts, sample_checks, failures, "reference_binding_policy", refs_ok, prompt_sha256)

            tail_covered = any(item["evidence_end"] == len(prompt_text) for item in evidence if item["evidence_end"] is not None)
            check_value(check_counts, sample_checks, failures, "long_prompt_tail_coverage", len(prompt_text) <= 12000 or tail_covered, prompt_sha256, {"source_chars": len(prompt_text), "tail_covered": tail_covered})
            compressed_ok = True
            all_segments = iter_segments(prompt_text)
            for field, pattern in EXTRACTION_PATTERNS.items():
                if not target.execute("SELECT 1 FROM normalization_decisions WHERE prompt_sha256=? AND field_name=? AND operation='compress'", (prompt_sha256, field)).fetchone():
                    continue
                candidates: list[dict[str, Any]] = []
                seen: set[str] = set()
                for segment in all_segments:
                    if pattern.search(segment["text"]) and segment["text"].casefold() not in seen:
                        seen.add(segment["text"].casefold())
                        candidates.append(segment)
                limit = CONFIG["max_candidates"].get(field, 10)
                selected_candidates, compressed = candidate_segments(candidates, pattern, limit)
                if not compressed or not selected_candidates or (selected_candidates[-1]["start"], selected_candidates[-1]["end"]) not in direct_ranges.get(field, set()):
                    compressed_ok = False
            check_value(check_counts, sample_checks, failures, "compressed_candidate_tail_coverage", compressed_ok, prompt_sha256)

        regression_results: dict[str, dict[str, Any]] = {}
        for prompt_sha256, label in APPROVED_SAMPLE_HASHES.items():
            row = data["normalizations"].get(prompt_sha256)
            result = {"label": label, "passed": row is not None, "checks": {}}
            if row is not None:
                payload = {
                    "action_summary": json_value(row["action_summary_json"], {}),
                    "performance_dialogue_reaction": json_value(row["performance_dialogue_reaction_json"], {}),
                    "source_conflicts": json_value(row["source_conflicts_json"], []),
                }
                dialogue_lines = payload["performance_dialogue_reaction"].get("dialogue_lines", [])
                if label == "approved-dialogue-sample":
                    result["checks"]["exact_dialogue"] = any(item.get("line") == "Are you kidding me?" for item in dialogue_lines)
                    result["checks"]["duration_4_seconds"] = payload["action_summary"]["duration"].get("value_seconds") == 4
                elif label == "approved-action-sample":
                    result["checks"]["exact_japanese_dialogue"] = any(item.get("line") == "ほう...少しだけ、感じたぞ。" for item in dialogue_lines)
                    result["checks"]["duration_conflict_unresolved"] = any(item.get("field") == "duration" and item.get("resolution", {}).get("status") == "unresolved" for item in payload["source_conflicts"])
                elif label == "approved-environment-sample":
                    result["checks"]["asset_metadata_only_10_seconds"] = payload["action_summary"]["duration"].get("provenance") == "asset_metadata_only" and payload["action_summary"]["duration"].get("value_seconds") == 10.0
                    result["checks"]["no_dialogue"] = dialogue_lines == []
                result["passed"] = all(result["checks"].values()) and row["normalization_status"] == "normalized"
            regression_results[prompt_sha256] = result
            check_value(check_counts, sample_checks, failures, "approved_regression_samples", result["passed"], prompt_sha256, result)

        source.rollback()
        preprocessed.rollback()
        stratification.rollback()
        target.close()
        source.close()
        preprocessed.close()
        stratification.close()
        target = source = preprocessed = stratification = None
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
        manual_records = []
        for prompt_sha256, row in sorted(data["normalizations"].items()):
            if row["normalization_status"] == "needs_manual_review":
                stratum = data["strata"].get(prompt_sha256, {})
                tags = json_value(stratum.get("scene_tags_json"), [])
                manual_records.append({
                    "prompt_sha256": prompt_sha256,
                    "status_reasons": json_value(row["status_reasons_json"], []),
                    "source_prompt_chars": row["source_prompt_chars"],
                    "complexity_queue": row["complexity_queue"],
                    "scene_tags": tags,
                    "high_value": any(tag in {"action_interaction", "character_performance", "environment_establishing"} for tag in tags),
                    "sampled": prompt_sha256 in selected,
                })
        sample_records = []
        for prompt_sha256 in sorted(selected):
            row = data["normalizations"][prompt_sha256]
            stratum = data["strata"][prompt_sha256]
            sample_records.append({
                "prompt_sha256": prompt_sha256,
                "normalization_status": row["normalization_status"],
                "complexity_queue": row["complexity_queue"],
                "source_prompt_chars": row["source_prompt_chars"],
                "scene_tags": json_value(stratum["scene_tags_json"], []),
                "text_length_band": stratum["text_length_band"],
                "structure_state": stratum["structure_state"],
                "duration_state": stratum["duration_state"],
                "strata_memberships": memberships.get(prompt_sha256, []),
                "check_results": sample_checks.get(prompt_sha256, {}),
            })
        check_failures_by_code = Counter(item["check"] for item in failures)
        report_payload = {
            "schema_version": 1,
            "audit_version": AUDIT_VERSION,
            "audit_config_sha256": AUDIT_CONFIG_SHA256,
            "status": "pass" if not failures and all(unchanged.values()) else "fail",
            "normalizer_version": NORMALIZER_VERSION,
            "normalization_logical_target_digest": normalization_report.get("logical_target_digest"),
            "selected_prompt_count": len(data["normalizations"]),
            "normalized_count": sum(row["normalization_status"] == "normalized" for row in data["normalizations"].values()),
            "manual_review_count": len(manual_records),
            "excluded_count": sum(row["normalization_status"] == "excluded_with_reason" for row in data["normalizations"].values()),
            "sample_count": len(sample_records),
            "sample_dimension_coverage": {dimension: {value: len(hashes) for value, hashes in values.items()} for dimension, values in stratum_coverage.items()},
            "manual_review_high_value_count": sum(item["high_value"] for item in manual_records),
            "check_counts": check_counts,
            "failure_counts": dict(sorted(check_failures_by_code.items())),
            "failure_count": len(failures),
            "regression_results": regression_results,
            "source_state_unchanged": unchanged["source"],
            "preprocessed_state_unchanged": unchanged["preprocessed"],
            "stratification_state_unchanged": unchanged["stratification"],
            "normalization_state_unchanged": unchanged["normalization"],
            "checks": {"source_files_unchanged": all(unchanged.values()), "all_checks_passed": not failures},
            "sample_artifact": str(run_dir / "audit-sample.json"),
            "manual_review_artifact": str(run_dir / "manual-review.json"),
            "failure_artifact": str(run_dir / "failures.json"),
        }
        report_payload["audit_digest"] = sha256_text(canonical_json(report_payload))
        manifest = {
            "schema_version": 1,
            "audit_version": AUDIT_VERSION,
            "audit_config_sha256": AUDIT_CONFIG_SHA256,
            "normalizer_version": NORMALIZER_VERSION,
            "normalization_logical_target_digest": normalization_report.get("logical_target_digest"),
            "sampling_policy": "Deterministic SHA-256 order, up to 20 per queue/status/scene/length/structure/duration value, all approved regressions, and every manual-review record.",
            "selected_prompt_hashes": sorted(selected),
            "source_snapshot_sha256": source_snapshot_sha256(before["source"]),
            "preprocessed_snapshot_sha256": source_snapshot_sha256(before["preprocessed"]),
            "stratification_snapshot_sha256": source_snapshot_sha256(before["stratification"]),
            "normalization_snapshot_sha256": source_snapshot_sha256(before["normalization"]),
        }
        write_json_atomic(run_dir / "manifest.json", manifest)
        write_json_atomic(run_dir / "audit-sample.json", {"schema_version": 1, "records": sample_records})
        write_json_atomic(run_dir / "manual-review.json", {"schema_version": 1, "records": manual_records})
        write_json_atomic(run_dir / "failures.json", {"schema_version": 1, "records": failures})
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
    parser = argparse.ArgumentParser(description="Audit Stage 4B-3 semantic normalization with deterministic strata and source evidence checks.")
    parser.add_argument("--source-database", type=Path, default=DEFAULT_SOURCE_DATABASE)
    parser.add_argument("--preprocessed-database", type=Path, default=DEFAULT_PREPROCESSED_DATABASE)
    parser.add_argument("--stratification-database", type=Path, default=DEFAULT_STRATIFICATION_DATABASE)
    parser.add_argument("--normalization-run", type=Path, default=DEFAULT_NORMALIZATION_RUN)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = audit(args.source_database, args.preprocessed_database, args.stratification_database, args.normalization_run, args.run_dir)
    except Exception as error:
        print(json.dumps({"status": "fail", "error": type(error).__name__, "details": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({key: report[key] for key in ("status", "selected_prompt_count", "sample_count", "manual_review_count", "failure_count", "audit_digest")}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
