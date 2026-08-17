from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from normalize_video_prompt_semantics import canonical_json, sha256_text, source_snapshot_sha256, source_state
from probe_higgsfield import write_json_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DATABASE = WORK_ROOT / "data" / "runs" / "project-corpus" / "corpus.sqlite3"
DEFAULT_STRATIFICATION_DATABASE = WORK_ROOT / "data" / "runs" / "stage-4b-stratification-final" / "stratification.sqlite3"
DEFAULT_NORMALIZATION_RUN = WORK_ROOT / "data" / "runs" / "stage-4b-semantic-normalization-full"
DEFAULT_CHECKPOINT_RUN = WORK_ROOT / "data" / "runs" / "stage-4b-5-normalization-checkpoint"
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-5-1-prompt-classification"
TAXONOMY_VERSION = "stage5-scene-taxonomy-v1"
SCORING_VERSION = "stage5-prompt-content-score-v2"
EXPECTED_PROMPTS = 6555
EXPECTED_NORMALIZED = 6494
PRIMARY_TAGS = (
    "action_interaction",
    "character_performance",
    "environment_establishing",
    "mixed_scene",
    "unspecified_scene",
)
DERIVED_FAMILIES = (
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
DIMENSION_NAMES = (
    "shootability",
    "spatial_clarity",
    "action_causality",
    "performance_detail",
    "camera_control",
    "physics_plausibility",
    "continuity_control",
    "reusability",
)


TAXONOMY = {
    "version": TAXONOMY_VERSION,
    "review_mode": "prompt_only",
    "primary_scene_tags": {
        "action_interaction": "Observable physical interaction or action progression.",
        "character_performance": "Observable acting, reaction, gaze, gesture, or embodied performance.",
        "environment_establishing": "Observable location, atmosphere, architecture, or environmental state used to establish a scene.",
        "mixed_scene": "The source combines two or more primary scene intents; this tag is retained as a source-derived signal.",
        "unspecified_scene": "The source does not provide enough scene evidence for a more specific primary tag.",
    },
    "derived_pattern_families": {
        "action_choreography": "Action interaction with one or more explicit action beats.",
        "action_in_environment": "Action interaction and environment establishing signals co-occur.",
        "character_performance": "Character performance signal without requiring dialogue.",
        "dialogue_performance": "At least one explicit dialogue line or detected dialogue scope with performance evidence.",
        "environment_establishing": "Environment establishing signal with observable environment or lighting structure.",
        "camera_control": "Camera result evidence is a reusable part of the scene pattern.",
        "physics_continuity": "Physics or continuity evidence is a reusable part of the scene pattern.",
        "mixed_scene": "Mixed-scene source tag is retained as a review family.",
        "unspecified_scene": "No derived family can be supported without inventing scene meaning.",
    },
    "selection_policy": "Score Prompt construction only; asset counts, duplicate frequency, model frequency, and uninspected media are never quality evidence.",
}


SCORING_RULES = {
    "version": SCORING_VERSION,
    "max_score_per_dimension": 4,
    "dimensions": {
        "shootability": "objective plus subjects or environment, spatial layout, camera result, and continuity or constraints; capped at 4",
        "spatial_clarity": "spatial relations are required before placement, scene content, camera viewpoint, and continuity can add evidence",
        "action_causality": "action beats are required before multiple beats, causal links, physics, and continuity can add evidence",
        "performance_detail": "performance segments, multiple performance segments, dialogue lines, and detected dialogue scope",
        "camera_control": "camera segments are required before multiple camera segments, spatial layout, and continuity or constraints can add evidence",
        "physics_plausibility": "physics segments are required before multiple physics segments, action evidence, constraints, and continuity can add evidence",
        "continuity_control": "continuity segments are required before multiple continuity segments, constraints, and declared take structure can add evidence",
        "reusability": "portable scene intent, critical-field coverage, no unresolved source conflict, and a scene-pattern anchor",
    },
    "tier_rules": {
        "core_pattern": "total >= 24, no source conflict, no critical missing field, and no cross-field-only evidence penalty",
        "effective_variant": "total >= 18 and not core_pattern",
        "special_scene": "total < 18",
        "manual_review": "Source status is needs_manual_review; no automatic score is assigned.",
    },
    "evidence_quality_gate": "When every extracted value for a normalized field is duplicated in another scored field, that field is recorded as cross-field-only evidence and applies one point of noise penalty, capped at four points per Prompt.",
}


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


def list_payload(row: Any, column: str) -> list[Any]:
    value = json_value(row_value(row, column), [])
    return value if isinstance(value, list) else []


def dict_payload(row: Any, column: str) -> dict[str, Any]:
    value = json_value(row_value(row, column), {})
    return value if isinstance(value, dict) else {}


def nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def nonempty_segments(payload: dict[str, Any], key: str = "segments") -> list[str]:
    return [item for item in payload.get(key, []) if isinstance(item, str) and item.strip()]


def action_features(row: Any) -> tuple[list[dict[str, Any]], int]:
    beats = [item for item in dict_payload(row, "action_summary_json").get("beats", []) if isinstance(item, dict)]
    causal = sum(bool(item.get("causal_link")) for item in beats)
    return beats, causal


def performance_features(row: Any) -> tuple[list[str], list[dict[str, Any]], str]:
    payload = dict_payload(row, "performance_dialogue_reaction_json")
    segments = [item for item in payload.get("performance_segments", []) if isinstance(item, str) and item.strip()]
    dialogue = [item for item in payload.get("dialogue_lines", []) if isinstance(item, dict) and isinstance(item.get("line"), str)]
    return segments, dialogue, str(payload.get("dialogue_scope") or "none")


def evidence_features(row: Any, stratum: Any) -> dict[str, Any]:
    scene_tags = set(item for item in list_payload(row, "scene_tags_json") if isinstance(item, str))
    action_beats, causal_count = action_features(row)
    performance_segments, dialogue_lines, dialogue_scope = performance_features(row)
    camera_segments = nonempty_segments(dict_payload(row, "camera_result_json"))
    lighting_segments = nonempty_segments(dict_payload(row, "lighting_json"))
    sound_segments = nonempty_segments(dict_payload(row, "sound_json"))
    physics_segments = nonempty_segments(dict_payload(row, "physics_json"))
    continuity = list_payload(row, "continuity_json")
    constraints = list_payload(row, "constraints_json")
    spatial = list_payload(row, "spatial_relations_json")
    subjects = list_payload(row, "subjects_json")
    missing_fields = {
        item.get("field")
        for item in list_payload(row, "missing_fields_json")
        if isinstance(item, dict) and isinstance(item.get("field"), str)
    }
    source_conflicts = list_payload(row, "source_conflicts_json")
    return {
        "scene_tags": scene_tags,
        "objective": bool(str(row_value(row, "objective_text") or "").strip()),
        "subjects": subjects,
        "spatial": spatial,
        "action_beats": action_beats,
        "causal_count": causal_count,
        "performance_segments": performance_segments,
        "dialogue_lines": dialogue_lines,
        "dialogue_scope": dialogue_scope,
        "camera_segments": camera_segments,
        "lighting_segments": lighting_segments,
        "sound_segments": sound_segments,
        "physics_segments": physics_segments,
        "continuity": continuity,
        "constraints": constraints,
        "missing_fields": missing_fields,
        "source_conflicts": source_conflicts,
        "structure_state": str(row_value(stratum, "structure_state") or "not_declared"),
        "transferability": dict_payload(row, "transferability_json"),
        "references": list_payload(row, "material_references_json"),
    }


def dimension(score: int, evidence: Iterable[str], rationale: str) -> dict[str, Any]:
    return {
        "score": max(0, min(4, score)),
        "max_score": 4,
        "evidence_fields": sorted(set(evidence)),
        "rationale": rationale,
    }


def cross_field_only_evidence(features: dict[str, Any]) -> list[str]:
    """Find normalized fields whose extracted values are all duplicated elsewhere."""
    values: dict[str, list[str]] = {
        "spatial_relations": [item for item in features["spatial"] if isinstance(item, str)],
        "action_summary": [
            item.get("summary", "")
            for item in features["action_beats"]
            if isinstance(item, dict) and isinstance(item.get("summary"), str)
        ],
        "performance_dialogue_reaction": [
            *features["performance_segments"],
            *[
                item.get("line", "")
                for item in features["dialogue_lines"]
                if isinstance(item, dict) and isinstance(item.get("line"), str)
            ],
        ],
        "camera_result": features["camera_segments"],
        "physics": features["physics_segments"],
        "continuity": features["continuity"],
        "constraints": features["constraints"],
    }
    occurrences: Counter[str] = Counter(
        item.strip()
        for field_values in values.values()
        for item in set(field_values)
        if isinstance(item, str) and item.strip()
    )
    return sorted(
        field
        for field, field_values in values.items()
        if field_values
        and all(occurrences[item.strip()] > 1 for item in field_values if isinstance(item, str) and item.strip())
    )


def score_record(row: Any, stratum: Any) -> dict[str, Any] | None:
    if row_value(row, "normalization_status") != "normalized":
        return None
    features = evidence_features(row, stratum)
    scene_or_subject = bool(features["subjects"]) or "environment_establishing" in features["scene_tags"]
    continuity_or_constraints = bool(features["continuity"] or features["constraints"])
    spatial = features["spatial"]
    camera = features["camera_segments"]
    action = features["action_beats"]
    performance = features["performance_segments"]
    physics = features["physics_segments"]
    continuity = features["continuity"]
    constraints = features["constraints"]
    critical_missing = features["missing_fields"].intersection({"objective", "camera_result", "spatial_relations"})
    shared_evidence_fields = cross_field_only_evidence(features)
    score_penalty = min(4, len(shared_evidence_fields))

    dimensions = {
        "shootability": dimension(
            min(4, sum(bool(item) for item in (features["objective"], scene_or_subject, spatial, camera, continuity_or_constraints))),
            [
                field
                for field, present in (
                    ("objective", features["objective"]),
                    ("subjects_or_environment", scene_or_subject),
                    ("spatial_relations", spatial),
                    ("camera_result", camera),
                    ("continuity_or_constraints", continuity_or_constraints),
                )
                if present
            ],
            "Counts observable objective, scene content, spatial, camera, and continuity/constraint evidence.",
        ),
        "spatial_clarity": dimension(
            0
            if not spatial
            else min(4, 1 + int(len(spatial) >= 3) + int(scene_or_subject) + int(bool(camera))),
            [field for field, present in (("spatial_relations", spatial), ("subjects_or_environment", scene_or_subject), ("camera_result", camera), ("continuity", continuity)) if present],
            "Counts explicit placement and viewpoint evidence without inferring geography.",
        ),
        "action_causality": dimension(
            0
            if not action
            else min(4, 1 + int(len(action) >= 3) + int(features["causal_count"] > 0) + int(bool(physics))),
            [field for field, present in (("action_summary", action), ("causal_links", features["causal_count"] > 0), ("physics", physics), ("continuity", continuity)) if present],
            "Counts action beats, source causal links, physical evidence, and continuity evidence.",
        ),
        "performance_detail": dimension(
            min(4, int(bool(performance)) + int(len(performance) >= 3) + int(bool(features["dialogue_lines"])) + int(features["dialogue_scope"] == "detected")),
            [field for field, present in (("performance_segments", performance), ("dialogue_lines", features["dialogue_lines"]), ("dialogue_scope", features["dialogue_scope"] == "detected")) if present],
            "Counts explicit performance and dialogue evidence; voice wording alone is not treated as dialogue.",
        ),
        "camera_control": dimension(
            0
            if not camera
            else min(4, 1 + int(len(camera) >= 3) + int(bool(spatial)) + int(continuity_or_constraints)),
            [field for field, present in (("camera_result", camera), ("spatial_relations", spatial), ("continuity_or_constraints", continuity_or_constraints)) if present],
            "Counts explicit camera result, placement, and control locks.",
        ),
        "physics_plausibility": dimension(
            0
            if not physics
            else min(4, 1 + int(len(physics) >= 3) + int(bool(action)) + int(bool(continuity_or_constraints))),
            [field for field, present in (("physics", physics), ("action_summary", action), ("constraints", constraints), ("continuity", continuity)) if present],
            "Counts explicit physics, action, constraints, and continuity evidence; it does not validate rendered physics.",
        ),
        "continuity_control": dimension(
            0
            if not continuity
            else min(4, 1 + int(len(continuity) >= 3) + int(bool(constraints)) + int(features["structure_state"] in {"single_take", "multi_take"})),
            [field for field, present in (("continuity", continuity), ("constraints", constraints), ("structure_state", features["structure_state"] in {"single_take", "multi_take"})) if present],
            "Counts source continuity, constraints, and declared take structure.",
        ),
        "reusability": dimension(
            min(4, int(all(features["transferability"].get(adapter, {}).get("status") == "portable_scene_intent" for adapter in ("seedance", "h3"))) + int(not critical_missing) + int(not features["source_conflicts"]) + int(bool(scene_or_subject and (action or performance or camera or spatial)))),
            [field for field, present in (("transferability", all(features["transferability"].get(adapter, {}).get("status") == "portable_scene_intent" for adapter in ("seedance", "h3"))), ("missing_fields", not critical_missing), ("source_conflicts", not features["source_conflicts"]), ("scene_pattern_anchor", bool(scene_or_subject and (action or performance or camera or spatial)))) if present],
            "Counts portable scene intent once, critical-field coverage, resolved source state, and an observable scene-pattern anchor.",
        ),
    }
    total_score = max(0, min(32, sum(item["score"] for item in dimensions.values()) - score_penalty))
    if total_score >= 24 and not features["source_conflicts"] and not critical_missing and not shared_evidence_fields:
        case_tier = "core_pattern"
    elif total_score >= 18:
        case_tier = "effective_variant"
    else:
        case_tier = "special_scene"
    return {
        "prompt_content_score": total_score,
        "score_maximum": 32,
        "score_dimensions": dimensions,
        "score_penalty": score_penalty,
        "shared_evidence_fields": shared_evidence_fields,
        "case_tier": case_tier,
        "critical_missing_fields": sorted(critical_missing),
        "source_conflict_count": len(features["source_conflicts"]),
    }


def pattern_families(row: Any, score: dict[str, Any] | None) -> list[str]:
    if score is None:
        return ["manual_review"]
    features = evidence_features(row, None)
    tags = features["scene_tags"]
    families: list[str] = []
    has_action = "action_interaction" in tags and bool(features["action_beats"])
    has_environment = "environment_establishing" in tags
    has_performance = "character_performance" in tags
    if has_action:
        families.append("action_choreography")
    if has_action and has_environment:
        families.append("action_in_environment")
    if has_performance:
        families.append("character_performance")
    if features["dialogue_lines"] or features["dialogue_scope"] == "detected":
        families.append("dialogue_performance")
    if has_environment:
        families.append("environment_establishing")
    if features["camera_segments"]:
        families.append("camera_control")
    if features["physics_segments"] or features["continuity"]:
        families.append("physics_continuity")
    if "mixed_scene" in tags:
        families.append("mixed_scene")
    if not families:
        families.append("unspecified_scene")
    return sorted(set(families), key=lambda item: DERIVED_FAMILIES.index(item) if item in DERIVED_FAMILIES else item)


def asset_metadata(asset_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "asset_ids": sorted(item["asset_id"] for item in asset_rows),
        "asset_count_audit_only": len(asset_rows),
        "folder_ids": sorted({item["folder_id"] for item in asset_rows if item.get("folder_id")}),
        "folder_names": sorted({item["folder_name"] for item in asset_rows if item.get("folder_name")}),
        "models": sorted({item["model"] for item in asset_rows if item.get("model")}),
        "duration_seconds": sorted({item["duration_seconds"] for item in asset_rows if item.get("duration_seconds") is not None}),
        "resolutions": sorted({item["resolution"] for item in asset_rows if item.get("resolution")}),
    }


def load_near_duplicate_membership(path: Path, selected_hashes: set[str]) -> tuple[dict[str, list[dict[str, str]]], dict[str, int]]:
    if not path.exists():
        return {}, {"format_normalized_groups": 0, "numeric_normalized_groups": 0}
    payload = json.loads(path.read_text(encoding="utf-8"))
    memberships: dict[str, list[dict[str, str]]] = defaultdict(list)
    counts: dict[str, int] = {}
    for group_type in ("format_normalized_groups", "numeric_normalized_groups"):
        groups = payload.get(group_type, [])
        counts[group_type] = len(groups) if isinstance(groups, list) else 0
        if not isinstance(groups, list):
            continue
        for index, group in enumerate(groups):
            if not isinstance(group, dict):
                continue
            fingerprint = group.get("normalized_fingerprint")
            if not isinstance(fingerprint, str):
                continue
            for prompt in group.get("prompts", []):
                prompt_hash = prompt.get("prompt_sha256") if isinstance(prompt, dict) else None
                if prompt_hash in selected_hashes:
                    memberships[prompt_hash].append({"group_type": group_type, "group_index": str(index), "fingerprint": fingerprint})
    return dict(memberships), counts


def rank_candidates(records: list[dict[str, Any]], family: str, limit: int) -> list[dict[str, Any]]:
    eligible = [item for item in records if item["classification_status"] == "classified" and family in item["pattern_families"]]
    eligible.sort(
        key=lambda item: (
            -item["prompt_content_score"],
            -min(value["score"] for value in item["score_dimensions"].values()),
            item["prompt_sha256"],
        )
    )
    return eligible[:limit]


def classify(
    source_database: Path = DEFAULT_SOURCE_DATABASE,
    stratification_database: Path = DEFAULT_STRATIFICATION_DATABASE,
    normalization_run: Path = DEFAULT_NORMALIZATION_RUN,
    checkpoint_run: Path = DEFAULT_CHECKPOINT_RUN,
    run_dir: Path = DEFAULT_RUN_DIR,
    *,
    candidates_per_family: int = 20,
) -> dict[str, Any]:
    source_database = source_database.resolve()
    stratification_database = stratification_database.resolve()
    normalization_run = normalization_run.resolve()
    checkpoint_run = checkpoint_run.resolve()
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    before = {
        "source": source_state(source_database),
        "stratification": source_state(stratification_database),
        "normalization": source_state(normalization_run / "semantic_normalization.sqlite3"),
    }
    source = stratification = target = None
    try:
        checkpoint_report = json.loads((checkpoint_run / "report.json").read_text(encoding="utf-8"))
        checkpoint_manifest = json.loads((checkpoint_run / "manifest.json").read_text(encoding="utf-8"))
        near_duplicate_path = source_database.parent / "audit" / "near-duplicate-candidates.json"
        source = connect_readonly(source_database)
        stratification = connect_readonly(stratification_database)
        target = connect_readonly(normalization_run / "semantic_normalization.sqlite3")
        strata = {row["prompt_sha256"]: row for row in stratification.execute("SELECT * FROM prompt_strata ORDER BY prompt_sha256")}
        normalization_rows = list(target.execute("SELECT * FROM prompt_normalizations ORDER BY prompt_sha256"))
        normalizations = {row["prompt_sha256"]: row for row in normalization_rows}
        source_assets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        folder_names = {row["folder_id"]: row["name"] for row in source.execute("SELECT folder_id,name FROM folders")}
        for row in source.execute("SELECT prompt_sha256,asset_id,folder_id,item_type,asset_type,model,duration_seconds,resolution FROM assets WHERE prompt_sha256 IS NOT NULL ORDER BY prompt_sha256,asset_id"):
            if row["prompt_sha256"] not in normalizations:
                continue
            item = dict(row)
            item["folder_name"] = folder_names.get(row["folder_id"])
            source_assets[row["prompt_sha256"]].append(item)
        near_membership, near_counts = load_near_duplicate_membership(near_duplicate_path, set(normalizations))

        classified_records: list[dict[str, Any]] = []
        source_mapping_errors: list[str] = []
        for prompt_sha256 in sorted(normalizations):
            row = normalizations[prompt_sha256]
            stratum = strata.get(prompt_sha256)
            if stratum is None:
                source_mapping_errors.append(prompt_sha256)
                continue
            status = row["normalization_status"]
            mapping = asset_metadata(source_assets.get(prompt_sha256, []))
            score = score_record(row, stratum)
            families = pattern_families(row, score)
            base = {
                "prompt_sha256": prompt_sha256,
                "classification_status": "classified" if status == "normalized" else "manual_review",
                "normalization_status": status,
                "source_prompt_chars": row["source_prompt_chars"],
                "complexity_queue": row["complexity_queue"],
                "structure_state": stratum["structure_state"],
                "duration_state": stratum["duration_state"],
                "scene_tags": json_value(row["scene_tags_json"], []),
                "risk_flags": json_value(row["risk_flags_json"], []),
                "missing_fields": json_value(row["missing_fields_json"], []),
                "source_conflicts": json_value(row["source_conflicts_json"], []),
                "normalization_digest": row["normalization_digest"],
                "pattern_families": families,
                "near_duplicate_groups": near_membership.get(prompt_sha256, []),
                "near_duplicate_decision": "candidate_only_not_merged" if prompt_sha256 in near_membership else "not_grouped",
                "asset_mapping_count_audit_only": mapping["asset_count_audit_only"],
            }
            if score is None:
                base.update({"case_tier": "manual_review", "prompt_content_score": None, "score_maximum": 32, "score_dimensions": {}, "score_penalty": None, "shared_evidence_fields": []})
            else:
                base.update(score)
            classified_records.append(base)

        candidate_records: list[dict[str, Any]] = []
        for family in DERIVED_FAMILIES:
            for rank, record in enumerate(rank_candidates(classified_records, family, candidates_per_family), 1):
                mapping = asset_metadata(source_assets.get(record["prompt_sha256"], []))
                candidate_records.append(
                    {
                        "candidate_family": family,
                        "selection_rank": rank,
                        "selection_rationale": "Ranked by Prompt Content Score, minimum dimension score, and Prompt SHA-256 only; source asset mapping is audit metadata.",
                        **record,
                        **mapping,
                    }
                )

        classified_only = [item for item in classified_records if item["classification_status"] == "classified"]
        tier_counts = dict(sorted(Counter(item["case_tier"] for item in classified_only).items()))
        tag_counts: Counter[str] = Counter()
        family_counts: Counter[str] = Counter()
        score_bands: Counter[str] = Counter()
        dimension_totals: Counter[str] = Counter()
        score_penalties: Counter[str] = Counter()
        shared_evidence_counts: Counter[str] = Counter()
        for item in classified_only:
            tag_counts.update(item["scene_tags"])
            family_counts.update(item["pattern_families"])
            total = item["prompt_content_score"]
            score_bands["0-7"] += int(total < 8)
            score_bands["8-15"] += int(8 <= total < 16)
            score_bands["16-23"] += int(16 <= total < 24)
            score_bands["24-32"] += int(total >= 24)
            score_penalties[str(item["score_penalty"])] += 1
            shared_evidence_counts.update(item["shared_evidence_fields"])
            for name, value in item["score_dimensions"].items():
                dimension_totals[name] += value["score"]
        after = {
            "source": source_state(source_database),
            "stratification": source_state(stratification_database),
            "normalization": source_state(normalization_run / "semantic_normalization.sqlite3"),
        }
        unchanged = {key: source_snapshot_sha256(before[key]) == source_snapshot_sha256(after[key]) for key in before}
        checks = {
            "checkpoint_pass": checkpoint_report.get("status") == "pass" and checkpoint_report.get("selected_prompt_count") == EXPECTED_PROMPTS,
            "full_universe_closure": len(normalizations) == EXPECTED_PROMPTS,
            "normalized_count": len(classified_only) == EXPECTED_NORMALIZED,
            "manual_review_not_scored": all(item["prompt_content_score"] is None for item in classified_records if item["classification_status"] == "manual_review"),
            "excluded_records_preserved": sum(item["normalization_status"] == "excluded_with_reason" for item in classified_records) == 0,
            "strata_closure": set(normalizations) == set(strata),
            "source_asset_mapping": not source_mapping_errors and all(item["asset_mapping_count_audit_only"] > 0 for item in classified_records),
            "no_near_duplicate_merge": all(item["near_duplicate_decision"] in {"candidate_only_not_merged", "not_grouped"} for item in classified_records),
            "no_frequency_scoring": True,
            "prompt_only_review": True,
            "no_final_prompt_generated": checkpoint_report.get("input_reports", {}).get("audit_failure_count") == 0,
            "score_quality_adjustment_bounded": all(item["score_penalty"] == min(4, len(item["shared_evidence_fields"])) for item in classified_only),
            "input_states_unchanged": all(unchanged.values()),
        }
        taxonomy_payload = {
            "schema_version": 1,
            "taxonomy": TAXONOMY,
            "scoring": SCORING_RULES,
            "classification_policy": "Only normalized records receive automatic Prompt Content Scores; manual-review records remain unscored and excluded records remain explicit.",
            "asset_policy": "asset_count_audit_only is retained for source mapping and never enters score or ordering.",
            "near_duplicate_policy": "Near-duplicate groups remain candidate-only relationships; no records are merged or removed.",
        }
        classification_digest = sha256_text(canonical_json(classified_records))
        candidate_digest = sha256_text(canonical_json(candidate_records))
        taxonomy_digest = sha256_text(canonical_json(taxonomy_payload))
        report = {
            "schema_version": 1,
            "taxonomy_version": TAXONOMY_VERSION,
            "scoring_version": SCORING_VERSION,
            "status": "pass" if all(checks.values()) else "fail",
            "review_mode": "prompt_only",
            "exact_prompt_cluster_count": len(normalizations),
            "classified_count": len(classified_only),
            "manual_review_count": sum(item["classification_status"] == "manual_review" for item in classified_records),
            "excluded_count": sum(item["normalization_status"] == "excluded_with_reason" for item in classified_records),
            "case_tier_counts": tier_counts,
            "primary_scene_tag_counts": dict(sorted(tag_counts.items())),
            "pattern_family_counts": dict(sorted(family_counts.items())),
            "score_band_counts": dict(sorted(score_bands.items())),
            "dimension_score_totals": dict(sorted(dimension_totals.items())),
            "score_penalty_counts": dict(sorted(score_penalties.items(), key=lambda item: int(item[0]))),
            "shared_evidence_field_counts": dict(sorted(shared_evidence_counts.items())),
            "candidate_counts_by_family": dict(sorted(Counter(item["candidate_family"] for item in candidate_records).items())),
            "near_duplicate_candidate_groups": near_counts,
            "near_duplicate_prompt_membership_count": len(near_membership),
            "source_mapping_error_count": len(source_mapping_errors),
            "source_snapshot_sha256": source_snapshot_sha256(before["source"]),
            "stratification_snapshot_sha256": source_snapshot_sha256(before["stratification"]),
            "normalization_snapshot_sha256": source_snapshot_sha256(before["normalization"]),
            "source_state_unchanged": unchanged["source"],
            "stratification_state_unchanged": unchanged["stratification"],
            "normalization_state_unchanged": unchanged["normalization"],
            "input_checkpoint_digest": checkpoint_report.get("checkpoint_digest"),
            "classification_digest": classification_digest,
            "candidate_digest": candidate_digest,
            "taxonomy_digest": taxonomy_digest,
            "candidate_limit_per_family": candidates_per_family,
            "checks": checks,
            "artifacts": {
                "taxonomy_and_scoring": str(run_dir / "taxonomy-and-scoring.json"),
                "classified_records": str(run_dir / "classified-records.json"),
                "selection_candidates": str(run_dir / "selection-candidates.json"),
                "manifest": str(run_dir / "manifest.json"),
                "report": str(run_dir / "report.json"),
            },
        }
        report["stage5_1_digest"] = sha256_text(canonical_json(report))
        manifest = {
            "schema_version": 1,
            "taxonomy_version": TAXONOMY_VERSION,
            "scoring_version": SCORING_VERSION,
            "checkpoint_digest": checkpoint_report.get("checkpoint_digest"),
            "checkpoint_manifest_sha256": sha256_text((checkpoint_run / "manifest.json").read_bytes().decode("utf-8")),
            "source_snapshot_sha256": report["source_snapshot_sha256"],
            "stratification_snapshot_sha256": report["stratification_snapshot_sha256"],
            "normalization_snapshot_sha256": report["normalization_snapshot_sha256"],
            "exact_prompt_cluster_count": len(normalizations),
            "classified_count": len(classified_only),
            "manual_review_count": report["manual_review_count"],
            "excluded_count": report["excluded_count"],
            "classification_digest": classification_digest,
            "candidate_digest": candidate_digest,
            "taxonomy_digest": taxonomy_digest,
            "stage5_1_digest": report["stage5_1_digest"],
        }
        write_json_atomic(run_dir / "taxonomy-and-scoring.json", taxonomy_payload)
        write_json_atomic(run_dir / "classified-records.json", {"schema_version": 1, "records": classified_records})
        write_json_atomic(run_dir / "selection-candidates.json", {"schema_version": 1, "records": candidate_records})
        write_json_atomic(run_dir / "manifest.json", manifest)
        write_json_atomic(run_dir / "report.json", report)
        return report
    finally:
        for connection in (target, source, stratification):
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
    parser = argparse.ArgumentParser(description="Classify Stage 5 prompt candidates with an auditable Prompt-only score.")
    parser.add_argument("--source-database", type=Path, default=DEFAULT_SOURCE_DATABASE)
    parser.add_argument("--stratification-database", type=Path, default=DEFAULT_STRATIFICATION_DATABASE)
    parser.add_argument("--normalization-run", type=Path, default=DEFAULT_NORMALIZATION_RUN)
    parser.add_argument("--checkpoint-run", type=Path, default=DEFAULT_CHECKPOINT_RUN)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--candidates-per-family", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.candidates_per_family < 1:
        raise SystemExit("--candidates-per-family must be at least 1")
    try:
        report = classify(
            args.source_database,
            args.stratification_database,
            args.normalization_run,
            args.checkpoint_run,
            args.run_dir,
            candidates_per_family=args.candidates_per_family,
        )
    except Exception as error:
        print(json.dumps({"status": "fail", "error": type(error).__name__, "details": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({key: report[key] for key in ("status", "exact_prompt_cluster_count", "classified_count", "manual_review_count", "excluded_count", "stage5_1_digest")}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
