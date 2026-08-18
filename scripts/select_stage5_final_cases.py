from __future__ import annotations

import argparse
import copy
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from normalize_video_prompt_semantics import canonical_json, sha256_text
from probe_higgsfield import write_json_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_RUN = WORK_ROOT / "data" / "runs" / "stage-5-1-prompt-classification"
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-5-2-final-selection"
SELECTION_VERSION = "stage5-final-selection-v1"
DEFAULT_CASES_PER_FAMILY = 3
MINIMUM_SCORE = 18
MINIMUM_DIMENSION_SCORE = 3
FINAL_FAMILY_ORDER = (
    "action_choreography",
    "action_in_environment",
    "character_performance",
    "dialogue_performance",
    "environment_establishing",
    "camera_control",
    "physics_continuity",
    "mixed_scene",
    "unspecified_scene",
)
ELIGIBLE_TIERS = {"core_pattern", "effective_variant"}
EDITORIAL_RISK_FLAGS = {
    "unresolved_reference_occurrence",
    "very_long_prompt",
    "high_marker_density",
}


def min_dimension_score(record: dict[str, Any]) -> int:
    dimensions = record.get("score_dimensions") or {}
    scores = [
        value.get("score")
        for value in dimensions.values()
        if isinstance(value, dict) and isinstance(value.get("score"), int)
    ]
    return min(scores) if scores else 0


def missing_field_names(record: dict[str, Any]) -> list[str]:
    return sorted(
        {
            item.get("field")
            for item in record.get("missing_fields", [])
            if isinstance(item, dict) and isinstance(item.get("field"), str)
        }
    )


def near_duplicate_keys(record: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for item in record.get("near_duplicate_groups", []):
        if not isinstance(item, dict):
            continue
        group_type = item.get("group_type")
        group_index = item.get("group_index")
        fingerprint = item.get("fingerprint")
        if all(isinstance(value, str) for value in (group_type, group_index, fingerprint)):
            keys.add(f"{group_type}:{group_index}:{fingerprint}")
    return keys


def editorial_priority_factors(record: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic tie-break data after the Stage 5-1 score."""
    risk_flags = set(record.get("risk_flags") or [])
    return {
        "minimum_dimension_score": min_dimension_score(record),
        "missing_field_count": len(missing_field_names(record)),
        "editorial_risk_count": len(risk_flags.intersection(EDITORIAL_RISK_FLAGS)),
        "source_prompt_chars": record.get("source_prompt_chars")
        if isinstance(record.get("source_prompt_chars"), int)
        else 0,
        "near_duplicate_group_count": len(near_duplicate_keys(record)),
    }


def priority_key(record: dict[str, Any]) -> tuple[Any, ...]:
    factors = editorial_priority_factors(record)
    score = record.get("prompt_content_score")
    return (
        -(score if isinstance(score, int) else -1),
        -factors["minimum_dimension_score"],
        factors["missing_field_count"],
        factors["editorial_risk_count"],
        factors["source_prompt_chars"],
        str(record.get("prompt_sha256") or ""),
    )


def eligibility_reasons(record: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if record.get("classification_status") != "classified":
        reasons.append("not_classified")
    if record.get("normalization_status") != "normalized":
        reasons.append("not_normalized")
    if record.get("case_tier") not in ELIGIBLE_TIERS:
        reasons.append("case_tier_below_final_selection_gate")
    score = record.get("prompt_content_score")
    if not isinstance(score, int) or score < MINIMUM_SCORE:
        reasons.append("prompt_content_score_below_gate")
    if min_dimension_score(record) < MINIMUM_DIMENSION_SCORE:
        reasons.append("minimum_dimension_score_below_gate")
    if record.get("source_conflicts"):
        reasons.append("source_conflict_present")
    if record.get("critical_missing_fields"):
        reasons.append("critical_field_missing")
    asset_ids = record.get("asset_ids")
    if not isinstance(asset_ids, list) or not asset_ids:
        reasons.append("source_asset_mapping_missing")
    return reasons


def family_records(records: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        family = record.get("candidate_family")
        if isinstance(family, str):
            grouped[family].append(record)
    return grouped


def select_final_cases(
    records: list[dict[str, Any]],
    *,
    cases_per_family: int = DEFAULT_CASES_PER_FAMILY,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if cases_per_family < 1:
        raise ValueError("cases_per_family must be at least 1")
    prompt_hashes = [record.get("prompt_sha256") for record in records]
    if any(not isinstance(value, str) or not value for value in prompt_hashes):
        raise ValueError("every candidate must have a prompt_sha256")
    if len(prompt_hashes) != len(set(prompt_hashes)):
        raise ValueError("Stage 5-1 candidates must contain unique Prompt hashes")

    grouped = family_records(records)
    decisions: dict[str, dict[str, Any]] = {}
    selected: list[dict[str, Any]] = []
    selected_hashes: set[str] = set()
    selected_near_keys: dict[str, str] = {}
    family_counts: Counter[str] = Counter()

    for family in FINAL_FAMILY_ORDER:
        candidates = sorted(grouped.get(family, []), key=priority_key)
        for record in candidates:
            prompt_sha256 = record["prompt_sha256"]
            reasons = eligibility_reasons(record)
            decision = {
                "prompt_sha256": prompt_sha256,
                "candidate_family": family,
                "decision": None,
                "decision_reason_codes": [],
                "decision_reason": None,
                "editorial_priority_factors": editorial_priority_factors(record),
                "near_duplicate_of_case_id": None,
                "case_id": None,
            }
            if reasons:
                decision["decision"] = "not_selected"
                decision["decision_reason_codes"] = reasons
                decision["decision_reason"] = (
                    "Fails the final Prompt-only eligibility gate: " + ", ".join(reasons) + "."
                )
                decisions[prompt_sha256] = decision
                continue
            if prompt_sha256 in selected_hashes:
                decision["decision"] = "retained_alternative"
                decision["decision_reason_codes"] = ["exact_prompt_already_selected"]
                decision["decision_reason"] = "The exact Prompt hash is already represented by a selected case."
                decisions[prompt_sha256] = decision
                continue

            duplicate_case_id = next(
                (
                    case_id
                    for key, case_id in selected_near_keys.items()
                    if key in near_duplicate_keys(record)
                ),
                None,
            )
            if duplicate_case_id is not None:
                decision["decision"] = "retained_alternative"
                decision["decision_reason_codes"] = ["near_duplicate_of_selected_case"]
                decision["decision_reason"] = (
                    f"Retained as a near-duplicate alternative to {duplicate_case_id}; "
                    "the final library keeps one representative pattern."
                )
                decision["near_duplicate_of_case_id"] = duplicate_case_id
                decisions[prompt_sha256] = decision
                continue

            if family_counts[family] >= cases_per_family:
                decision["decision"] = "retained_alternative"
                decision["decision_reason_codes"] = ["family_quota_exhausted"]
                decision["decision_reason"] = (
                    f"Eligible alternative retained outside the {cases_per_family}-case family quota."
                )
                decisions[prompt_sha256] = decision
                continue

            case_number = family_counts[family] + 1
            case_id = f"scene-case-{family}-{case_number:02d}"
            selected_record = copy.deepcopy(record)
            selected_record.update(
                {
                    "case_id": case_id,
                    "final_status": "selected",
                    "final_selection_rank": len(selected) + 1,
                    "selection_policy_version": SELECTION_VERSION,
                    "selection_reason_codes": [
                        "eligible",
                        "family_coverage",
                        "highest_priority_remaining",
                    ],
                    "selection_reason": (
                        f"Selected as family representative {case_number} of {cases_per_family} "
                        "after the Prompt-only quality and source-integrity gates."
                    ),
                    "editorial_priority_factors": editorial_priority_factors(record),
                }
            )
            selected.append(selected_record)
            selected_hashes.add(prompt_sha256)
            family_counts[family] += 1
            for key in near_duplicate_keys(record):
                selected_near_keys[key] = case_id
            decision.update(
                {
                    "decision": "selected",
                    "decision_reason_codes": selected_record["selection_reason_codes"],
                    "decision_reason": selected_record["selection_reason"],
                    "case_id": case_id,
                }
            )
            decisions[prompt_sha256] = decision

    # Candidate families are fixed by Stage 5-1, but retain any future family records
    # in the audit output instead of silently dropping them.
    for record in records:
        prompt_sha256 = record["prompt_sha256"]
        if prompt_sha256 in decisions:
            continue
        decision = {
            "prompt_sha256": prompt_sha256,
            "candidate_family": record.get("candidate_family"),
            "decision": "not_selected",
            "decision_reason_codes": ["family_not_in_selection_order"],
            "decision_reason": "Candidate family is outside the configured final selection order.",
            "editorial_priority_factors": editorial_priority_factors(record),
            "near_duplicate_of_case_id": None,
            "case_id": None,
        }
        decisions[prompt_sha256] = decision

    decision_records = []
    for record in records:
        decision = decisions[record["prompt_sha256"]]
        merged = copy.deepcopy(record)
        merged.update(decision)
        decision_records.append(merged)
    decision_records.sort(key=lambda item: (str(item.get("candidate_family")), str(item["prompt_sha256"])))
    return selected, decision_records


def load_stage5_1_input(input_run: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    candidate_path = input_run / "selection-candidates.json"
    report_path = input_run / "report.json"
    manifest_path = input_run / "manifest.json"
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if payload.get("schema_version") != 1 or not isinstance(records, list):
        raise ValueError("Stage 5-1 selection-candidates.json has an unsupported schema")
    if report.get("status") != "pass":
        raise ValueError("Stage 5-1 report is not passing")
    if report.get("candidate_record_count") != len(records):
        raise ValueError("Stage 5-1 candidate count does not match its report")
    candidate_digest = sha256_text(canonical_json(records))
    if report.get("candidate_digest") != candidate_digest or manifest.get("candidate_digest") != candidate_digest:
        raise ValueError("Stage 5-1 candidate digest mismatch")
    return report, manifest, records


def select(
    input_run: Path = DEFAULT_INPUT_RUN,
    run_dir: Path = DEFAULT_RUN_DIR,
    *,
    cases_per_family: int = DEFAULT_CASES_PER_FAMILY,
) -> dict[str, Any]:
    input_run = input_run.resolve()
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    input_report, input_manifest, records = load_stage5_1_input(input_run)
    selected, decisions = select_final_cases(records, cases_per_family=cases_per_family)

    status_counts = Counter(item["decision"] for item in decisions)
    family_counts = Counter(item["candidate_family"] for item in selected)
    reason_counts = Counter(
        code
        for item in decisions
        for code in item.get("decision_reason_codes", [])
    )
    selected_hashes = {item["prompt_sha256"] for item in selected}
    all_hashes = [item["prompt_sha256"] for item in records]
    checks = {
        "input_stage5_1_pass": input_report.get("status") == "pass",
        "input_candidate_digest_verified": input_report.get("candidate_digest")
        == sha256_text(canonical_json(records)),
        "candidate_universe_closed": len(records) == len(set(all_hashes)),
        "decision_universe_closed": len(decisions) == len(records),
        "selected_hashes_unique": len(selected) == len(selected_hashes),
        "selected_cases_have_source_mapping": all(
            isinstance(item.get("asset_ids"), list) and bool(item["asset_ids"]) for item in selected
        ),
        "selected_cases_pass_gate": all(not eligibility_reasons(item) for item in selected),
        "family_quotas_respected": all(count <= cases_per_family for count in family_counts.values()),
        "no_near_duplicate_selected": len(
            {
                key
                for item in selected
                for key in near_duplicate_keys(item)
            }
        )
        == sum(len(near_duplicate_keys(item)) for item in selected),
        "no_raw_prompt_text": all("prompt" not in item or item["prompt"] is None for item in selected),
        "prompt_only_review": True,
        "no_final_prompt_generated": True,
    }
    selected_digest = sha256_text(canonical_json(selected))
    decision_digest = sha256_text(canonical_json(decisions))
    report = {
        "schema_version": 1,
        "selection_version": SELECTION_VERSION,
        "status": "pass" if all(checks.values()) else "fail",
        "review_mode": "prompt_only",
        "policy": {
            "minimum_prompt_content_score": MINIMUM_SCORE,
            "minimum_dimension_score": MINIMUM_DIMENSION_SCORE,
            "eligible_case_tiers": sorted(ELIGIBLE_TIERS),
            "cases_per_family": cases_per_family,
            "near_duplicate_policy": "Keep one representative globally; retain other candidates as alternatives.",
            "asset_policy": "Asset IDs and counts remain source-audit metadata only; they never affect ordering.",
            "media_policy": "No media was inspected; no rendered quality claim is made.",
            "editorial_tiebreak_policy": "After content score and minimum dimension score, prefer fewer missing fields, fewer editorial risk flags, shorter source text, then SHA-256.",
        },
        "input_stage5_1_digest": input_report.get("stage5_1_digest"),
        "input_candidate_digest": input_report.get("candidate_digest"),
        "candidate_record_count": len(records),
        "selected_case_count": len(selected),
        "decision_counts": dict(sorted(status_counts.items())),
        "selected_counts_by_family": dict(sorted(family_counts.items())),
        "decision_reason_counts": dict(sorted(reason_counts.items())),
        "near_duplicate_suppressed_count": sum(
            "near_duplicate_of_selected_case" in item.get("decision_reason_codes", []) for item in decisions
        ),
        "selected_prompt_hashes": sorted(selected_hashes),
        "selected_digest": selected_digest,
        "decision_digest": decision_digest,
        "checks": checks,
        "artifacts": {
            "final_cases": str(run_dir / "final-cases.json"),
            "decision_records": str(run_dir / "decision-records.json"),
            "manifest": str(run_dir / "manifest.json"),
            "report": str(run_dir / "report.json"),
        },
    }
    report["stage5_2_digest"] = sha256_text(canonical_json(report))
    manifest = {
        "schema_version": 1,
        "selection_version": SELECTION_VERSION,
        "input_stage5_1_digest": input_report.get("stage5_1_digest"),
        "input_candidate_digest": input_report.get("candidate_digest"),
        "candidate_record_count": len(records),
        "selected_case_count": len(selected),
        "selected_digest": selected_digest,
        "decision_digest": decision_digest,
        "stage5_2_digest": report["stage5_2_digest"],
    }
    write_json_atomic(run_dir / "final-cases.json", {"schema_version": 1, "records": selected})
    write_json_atomic(run_dir / "decision-records.json", {"schema_version": 1, "records": decisions})
    write_json_atomic(run_dir / "manifest.json", manifest)
    write_json_atomic(run_dir / "report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select final cinematic scene cases from Stage 5-1 candidates.")
    parser.add_argument("--input-run", type=Path, default=DEFAULT_INPUT_RUN)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--cases-per-family", type=int, default=DEFAULT_CASES_PER_FAMILY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.cases_per_family < 1:
        raise SystemExit("--cases-per-family must be at least 1")
    try:
        report = select(args.input_run, args.run_dir, cases_per_family=args.cases_per_family)
    except Exception as error:
        raise SystemExit(str(error)) from error
    print(json.dumps({"status": report["status"], "selected_case_count": report["selected_case_count"], "run_dir": report["artifacts"]["report"]}, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
