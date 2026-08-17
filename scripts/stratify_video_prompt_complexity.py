from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from preprocess_video_prompt_sample import canonical_json, sha256_text, source_state, source_snapshot_sha256
from probe_higgsfield import write_json_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DATABASE = WORK_ROOT / "data" / "runs" / "project-corpus" / "corpus.sqlite3"
DEFAULT_PREPROCESSED_DATABASE = WORK_ROOT / "data" / "runs" / "stage-4b-preprocessing-full" / "preprocessed.sqlite3"
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-4b-stratification"
DEFAULT_BATCH_NAME = "stage-4b-2-full-video-stratification"
STRATIFIER_VERSION = "stage4b-risk-stratification-v1"
EXPECTED_VIDEO_PROMPTS = 6555
QUEUE_CODES = ("simple", "standard", "complex", "manual_review")
REQUIRED_EVIDENCE_DIMENSIONS = {
    "queue",
    "structure",
    "dialogue",
    "duration",
    "text_length",
    "marker_density",
    "reference_density",
    "scene",
}

SCENE_PATTERNS = {
    "action_interaction": re.compile(
        r"\b(?:fight|fighting|combat|battle|punch|kick|strike|dodge|block|parry|grab|throw|slam|"
        r"chase|run|sprint|jump|fall|impact|collision|crash|explode|explosion|shoot|sword|weapon)\w*\b",
        re.I,
    ),
    "character_performance": re.compile(
        r"\b(?:perform|acting|reaction|reacts?|expression|emotion|gaze|eye contact|looks? at|listens?|"
        r"speaks?|says?|whispers?|shouts?|breathes?|hesitates?|subtext|gesture|posture)\w*\b",
        re.I,
    ),
    "environment_establishing": re.compile(
        r"\b(?:environment|establishing|location|interior|exterior|city|street|alley|road|room|warehouse|"
        r"station|forest|mountain|ocean|beach|desert|village|building|landscape|skyline|aerial|drone|"
        r"weather|rain|snow|storm|traffic|train|background)\w*\b",
        re.I,
    ),
}

CONFIG = {
    "queues": list(QUEUE_CODES),
    "text_length_bands": {"short_max": 1000, "standard_max": 6000, "long_max": 12000},
    "marker_density_bands": {"low_max": 2, "medium_max": 8},
    "reference_density_bands": {"light_max": 4},
    "duration_null_policy": "Exclude null from numeric comparison and flag missing_asset_duration.",
    "scene_pattern_sources": sorted(SCENE_PATTERNS),
    "queue_precedence": [
        "manual_review: source preprocessing failed or source text is damaged",
        "complex: explicit risks, very-long text, high marker density, or dense references",
        "standard: long text, medium marker density, light references, or mixed scene signals",
        "simple: remaining low-structure records",
    ],
    "frequency_features_forbidden": ["asset_count", "occurrence_count", "membership_count", "generation_count"],
}
CONFIG_SHA256 = sha256_text(canonical_json(CONFIG))

TARGET_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS batches (
    batch_id TEXT PRIMARY KEY,
    batch_name TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    expected_prompt_count INTEGER NOT NULL,
    source_snapshot_sha256 TEXT NOT NULL,
    preprocessed_snapshot_sha256 TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_strata (
    prompt_sha256 TEXT PRIMARY KEY,
    source_input_sha256 TEXT NOT NULL,
    stratifier_version TEXT NOT NULL,
    stratifier_config_sha256 TEXT NOT NULL,
    processing_status TEXT NOT NULL CHECK(processing_status IN ('completed', 'failed')),
    source_processing_status TEXT NOT NULL,
    complexity_queue TEXT NOT NULL CHECK(complexity_queue IN ('simple', 'standard', 'complex', 'manual_review')),
    queue_rule_id TEXT NOT NULL,
    structure_state TEXT NOT NULL,
    dialogue_state TEXT NOT NULL,
    duration_state TEXT NOT NULL,
    text_length_band TEXT NOT NULL,
    marker_density_band TEXT NOT NULL,
    reference_density_band TEXT NOT NULL,
    scene_tags_json TEXT NOT NULL,
    risk_flags_json TEXT NOT NULL,
    queue_reasons_json TEXT NOT NULL,
    features_json TEXT NOT NULL,
    classification_digest TEXT NOT NULL,
    failure_code TEXT
);
CREATE TABLE IF NOT EXISTS strata_evidence (
    prompt_sha256 TEXT NOT NULL REFERENCES prompt_strata(prompt_sha256) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    evidence_kind TEXT NOT NULL CHECK(evidence_kind IN ('source_span', 'fact_ref', 'issue_ref')),
    fact_kind TEXT,
    fact_ordinal INTEGER,
    evidence_start INTEGER NOT NULL,
    evidence_end INTEGER NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    evidence_preview TEXT NOT NULL,
    PRIMARY KEY(prompt_sha256, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_prompt_strata_queue ON prompt_strata(complexity_queue);
CREATE INDEX IF NOT EXISTS idx_prompt_strata_structure ON prompt_strata(structure_state);
CREATE INDEX IF NOT EXISTS idx_strata_evidence_dimension ON strata_evidence(dimension);
"""


def connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    if connection.execute("PRAGMA query_only").fetchone()[0] != 1:
        connection.close()
        raise RuntimeError(f"database did not enter query_only mode: {path}")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        connection.close()
        raise RuntimeError(f"integrity_check failed for {path}: {integrity}")
    if connection.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()[0]:
        connection.close()
        raise RuntimeError(f"foreign_key_check failed for {path}")
    connection.execute("BEGIN")
    return connection


def connect_target(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.executescript(TARGET_SCHEMA)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def text_length_band(char_count: int) -> str:
    if char_count <= 1000:
        return "short"
    if char_count <= 6000:
        return "standard"
    if char_count <= 12000:
        return "long"
    return "very_long"


def density_band(value: int, low_max: int, medium_max: int | None = None) -> str:
    if value == 0 and medium_max is None:
        return "none"
    if value <= low_max:
        return "low" if medium_max is not None else "light"
    if medium_max is not None and value <= medium_max:
        return "medium"
    return "high" if medium_max is not None else "dense"


def duration_state(structure: dict[str, Any]) -> str:
    declared = sorted({value for value in json.loads(structure["declared_duration_values_json"]) if isinstance(value, (int, float))})
    metadata = sorted({value for value in json.loads(structure["metadata_duration_values_json"]) if isinstance(value, (int, float))})
    if declared and metadata and declared != metadata:
        return "conflict"
    if len(declared) > 1:
        return "multiple_declared"
    if len(metadata) > 1:
        return "multiple_metadata"
    if declared and metadata:
        return "consistent"
    if declared:
        return "prompt_only"
    if metadata:
        return "asset_metadata_only"
    return "missing"


def full_evidence(prompt_text: str, dimension: str, rule_id: str, kind: str = "source_span") -> dict[str, Any]:
    return span_evidence(prompt_text, dimension, rule_id, kind, 0, len(prompt_text))


def span_evidence(
    prompt_text: str,
    dimension: str,
    rule_id: str,
    kind: str,
    start: int,
    end: int,
    *,
    fact_kind: str | None = None,
    fact_ordinal: int | None = None,
) -> dict[str, Any]:
    if not 0 <= start < end <= len(prompt_text):
        raise ValueError(f"invalid evidence range for {dimension}: {start}:{end}")
    evidence = prompt_text[start:end]
    return {
        "dimension": dimension,
        "rule_id": rule_id,
        "evidence_kind": kind,
        "fact_kind": fact_kind,
        "fact_ordinal": fact_ordinal,
        "evidence_start": start,
        "evidence_end": end,
        "evidence_sha256": sha256_text(evidence),
        "evidence_preview": evidence[:160],
    }


def fact_evidence(prompt_text: str, fact: dict[str, Any], dimension: str, rule_id: str) -> dict[str, Any] | None:
    start = fact.get("evidence_start")
    end = fact.get("evidence_end")
    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(prompt_text):
        return None
    return span_evidence(
        prompt_text,
        dimension,
        rule_id,
        "fact_ref",
        start,
        end,
        fact_kind=fact["fact_kind"],
        fact_ordinal=fact["ordinal"],
    )


def issue_evidence(prompt_text: str, issue: dict[str, Any], dimension: str) -> dict[str, Any]:
    start = issue.get("evidence_start")
    end = issue.get("evidence_end")
    if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(prompt_text):
        return span_evidence(
            prompt_text,
            dimension,
            f"issue:{issue['code']}",
            "issue_ref",
            start,
            end,
            fact_ordinal=issue["ordinal"],
        )
    return full_evidence(prompt_text, dimension, f"issue:{issue['code']}", "issue_ref")


def add_fact_evidence(
    evidence: list[dict[str, Any]],
    prompt_text: str,
    facts: Sequence[dict[str, Any]],
    dimension: str,
    rule_id: str,
    fact_kinds: set[str],
) -> None:
    added = 0
    for fact in facts:
        if fact["fact_kind"] not in fact_kinds:
            continue
        item = fact_evidence(prompt_text, fact, dimension, rule_id)
        if item is not None:
            evidence.append(item)
            added += 1
        if added == 3:
            break
    if not added:
        evidence.append(full_evidence(prompt_text, dimension, f"{rule_id}:full-scan"))


def scene_signals(prompt_text: str, structure: dict[str, Any], facts: Sequence[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    tags: list[str] = []
    evidence: list[dict[str, Any]] = []
    for tag, pattern in SCENE_PATTERNS.items():
        matches = list(pattern.finditer(prompt_text))[:3]
        if matches:
            tags.append(tag)
            evidence.extend(
                span_evidence(prompt_text, "scene", f"scene:{tag}", "source_span", match.start(), match.end())
                for match in matches
            )
    if structure["dialogue_evidence_count"] or structure["dialogue_utterance_count"]:
        if "character_performance" not in tags:
            tags.append("character_performance")
            dialogue_facts = [fact for fact in facts if fact["fact_kind"] == "dialogue"]
            if dialogue_facts:
                item = fact_evidence(prompt_text, dialogue_facts[0], "scene", "scene:dialogue-performance")
                if item is not None:
                    evidence.append(item)
    base_tags = sorted(set(tags))
    if len(base_tags) >= 2:
        base_tags.append("mixed_scene")
    if not base_tags:
        base_tags = ["unspecified_scene"]
        evidence.append(full_evidence(prompt_text, "scene", "scene:unspecified-full-scan"))
    return base_tags, evidence


def classify_record(record: dict[str, Any]) -> dict[str, Any]:
    prompt_text = record["prompt_text"]
    structure = record["structure"]
    facts = record["facts"]
    issues = record["issues"]
    issue_codes = sorted({issue["code"] for issue in issues})

    structure_state = {
        "single": "single_take",
        "multi": "multi_take",
        "conflict": "conflicted",
        "not_declared": "not_declared",
    }.get(structure["take_structure"], "not_declared")
    if "audio_dialogue_scope_ambiguity" in issue_codes:
        dialogue_state = "ambiguous"
    elif structure["dialogue_evidence_count"] or structure["dialogue_utterance_count"]:
        dialogue_state = "detected"
    else:
        dialogue_state = "none"
    duration = duration_state(structure)
    length_band = text_length_band(record["source_prompt_chars"])
    marker_total = structure["shot_marker_count"] + structure["cut_marker_count"] + structure["timestamp_count"]
    marker_band = density_band(marker_total, 2, 8)
    reference_total = structure["reference_tag_count"] + structure["reference_block_count"]
    reference_band = density_band(reference_total, 4)
    scene_tags, scene_evidence = scene_signals(prompt_text, structure, facts)

    risk_flags = set(issue_codes)
    if any(value is None for value in json.loads(structure["metadata_duration_values_json"])):
        risk_flags.add("missing_asset_duration")
    if length_band == "very_long":
        risk_flags.add("very_long_prompt")
    if marker_band == "high":
        risk_flags.add("high_marker_density")
    if reference_band == "dense":
        risk_flags.add("dense_references")
    if duration == "conflict":
        risk_flags.add("duration_conflict")
    if structure_state == "conflicted":
        risk_flags.add("structure_conflict")

    manual_issue_codes = {"parser_exception", "unicode_replacement_character"}
    manual_reasons = sorted(manual_issue_codes & set(issue_codes))
    if structure["processing_status"] not in {"completed", "completed_with_issues"} or manual_reasons:
        queue = "manual_review"
        queue_rule_id = "queue:manual-unreliable-source"
        queue_reasons = manual_reasons or ["source-processing-failed"]
    elif issue_codes or structure["processing_status"] == "completed_with_issues" or length_band == "very_long" or marker_band == "high" or reference_band == "dense":
        queue = "complex"
        queue_rule_id = "queue:complex-risk-or-density"
        queue_reasons = sorted(set(issue_codes + [
            reason
            for reason, active in (
                ("source-processing-issues", structure["processing_status"] == "completed_with_issues" and not issue_codes),
                ("very_long_prompt", length_band == "very_long"),
                ("high_marker_density", marker_band == "high"),
                ("dense_references", reference_band == "dense"),
            )
            if active
        ]))
    elif length_band == "long" or marker_band == "medium" or reference_band == "light" or "mixed_scene" in scene_tags:
        queue = "standard"
        queue_rule_id = "queue:standard-moderate-structure"
        queue_reasons = [
            reason
            for reason, active in (
                ("long_prompt", length_band == "long"),
                ("medium_marker_density", marker_band == "medium"),
                ("light_references", reference_band == "light"),
                ("mixed_scene", "mixed_scene" in scene_tags),
            )
            if active
        ]
    else:
        queue = "simple"
        queue_rule_id = "queue:simple-low-structure"
        queue_reasons = ["low-structure"]

    features = {
        "source_prompt_chars": record["source_prompt_chars"],
        "take_structure": structure["take_structure"],
        "shot_marker_count": structure["shot_marker_count"],
        "cut_marker_count": structure["cut_marker_count"],
        "timestamp_count": structure["timestamp_count"],
        "dialogue_evidence_count": structure["dialogue_evidence_count"],
        "dialogue_utterance_count": structure["dialogue_utterance_count"],
        "reference_tag_count": structure["reference_tag_count"],
        "reference_block_count": structure["reference_block_count"],
        "declared_duration_values": json.loads(structure["declared_duration_values_json"]),
        "metadata_duration_values": json.loads(structure["metadata_duration_values_json"]),
    }
    forbidden = set(CONFIG["frequency_features_forbidden"]) & set(features)
    if forbidden:
        raise RuntimeError(f"frequency features entered stratification: {sorted(forbidden)}")

    evidence: list[dict[str, Any]] = []
    add_fact_evidence(evidence, prompt_text, facts, "structure", "structure:fact", {"take_declaration", "shot_marker", "cut_marker"})
    add_fact_evidence(evidence, prompt_text, facts, "dialogue", "dialogue:fact", {"dialogue", "audio", "language"})
    add_fact_evidence(evidence, prompt_text, facts, "duration", "duration:fact", {"declared_duration"})
    evidence.append(full_evidence(prompt_text, "text_length", f"text-length:{length_band}"))
    add_fact_evidence(evidence, prompt_text, facts, "marker_density", f"marker-density:{marker_band}", {"shot_marker", "cut_marker", "timestamp"})
    add_fact_evidence(evidence, prompt_text, facts, "reference_density", f"reference-density:{reference_band}", {"reference_tag", "reference_block"})
    evidence.extend(scene_evidence)
    evidence.append(full_evidence(prompt_text, "queue", queue_rule_id))
    for issue in issues[:3]:
        evidence.append(issue_evidence(prompt_text, issue, "risk"))

    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in evidence:
        key = (
            item["dimension"],
            item["rule_id"],
            item["evidence_kind"],
            item["fact_kind"],
            item["fact_ordinal"],
            item["evidence_start"],
            item["evidence_end"],
        )
        if key not in seen:
            seen.add(key)
            deduplicated.append(item)

    result = {
        "source_processing_status": structure["processing_status"],
        "complexity_queue": queue,
        "queue_rule_id": queue_rule_id,
        "structure_state": structure_state,
        "dialogue_state": dialogue_state,
        "duration_state": duration,
        "text_length_band": length_band,
        "marker_density_band": marker_band,
        "reference_density_band": reference_band,
        "scene_tags": sorted(scene_tags),
        "risk_flags": sorted(risk_flags),
        "queue_reasons": sorted(queue_reasons),
        "features": features,
        "evidence": deduplicated,
    }
    result["classification_digest"] = sha256_text(canonical_json({key: value for key, value in result.items() if key != "evidence"}))
    return result


def load_records(source: sqlite3.Connection, preprocessed: sqlite3.Connection, prompt_hashes: Sequence[str] | None) -> dict[str, dict[str, Any]]:
    if prompt_hashes is None:
        hashes = [row[0] for row in preprocessed.execute("SELECT prompt_sha256 FROM prompt_structure ORDER BY prompt_sha256")]
    else:
        hashes = sorted(set(prompt_hashes))
    selected = set(hashes)
    records: dict[str, dict[str, Any]] = {}
    for row in source.execute("SELECT prompt_sha256,prompt_text,source_prompt_chars,analysis_prompt_chars FROM prompts ORDER BY prompt_sha256"):
        if row["prompt_sha256"] in selected:
            records[row["prompt_sha256"]] = {
                "prompt_sha256": row["prompt_sha256"],
                "prompt_text": row["prompt_text"],
                "source_prompt_chars": row["source_prompt_chars"],
                "analysis_prompt_chars": row["analysis_prompt_chars"],
                "facts": [],
                "issues": [],
            }
    missing_source = sorted(selected - set(records))
    if missing_source:
        raise RuntimeError(f"missing source prompts: {', '.join(missing_source[:10])}")
    for row in preprocessed.execute("SELECT * FROM source_prompts ORDER BY prompt_sha256"):
        if row["prompt_sha256"] in selected:
            record = records[row["prompt_sha256"]]
            record["source_input_sha256"] = row["source_input_sha256"]
            record["source_content_digest"] = row["content_digest"]
    for row in preprocessed.execute("SELECT * FROM prompt_structure ORDER BY prompt_sha256"):
        if row["prompt_sha256"] in selected:
            records[row["prompt_sha256"]]["structure"] = dict(row)
    for row in preprocessed.execute("SELECT * FROM extracted_facts ORDER BY prompt_sha256,ordinal"):
        if row["prompt_sha256"] in selected:
            records[row["prompt_sha256"]]["facts"].append(dict(row))
    for row in preprocessed.execute("SELECT * FROM processing_issues ORDER BY prompt_sha256,ordinal"):
        if row["prompt_sha256"] in selected:
            records[row["prompt_sha256"]]["issues"].append(dict(row))
    incomplete = [prompt_hash for prompt_hash in hashes if "structure" not in records[prompt_hash] or "source_input_sha256" not in records[prompt_hash]]
    if incomplete:
        raise RuntimeError(f"incomplete preprocessed records: {', '.join(incomplete[:10])}")
    return {prompt_hash: records[prompt_hash] for prompt_hash in hashes}


def record_input_digest(record: dict[str, Any]) -> str:
    payload = {
        "prompt_sha256": record["prompt_sha256"],
        "analysis_prompt_sha256": sha256_text(record["prompt_text"]),
        "source_prompt_chars": record["source_prompt_chars"],
        "analysis_prompt_chars": record["analysis_prompt_chars"],
        "source_input_sha256": record["source_input_sha256"],
        "source_content_digest": record["source_content_digest"],
        "structure": record["structure"],
        "facts": record["facts"],
        "issues": record["issues"],
    }
    return sha256_text(canonical_json(payload))


def should_skip(target: sqlite3.Connection, prompt_hash: str, input_digest: str) -> bool:
    row = target.execute(
        "SELECT source_input_sha256,stratifier_version,stratifier_config_sha256,processing_status FROM prompt_strata WHERE prompt_sha256=?",
        (prompt_hash,),
    ).fetchone()
    return bool(
        row
        and row["source_input_sha256"] == input_digest
        and row["stratifier_version"] == STRATIFIER_VERSION
        and row["stratifier_config_sha256"] == CONFIG_SHA256
        and row["processing_status"] == "completed"
        and target.execute("SELECT 1 FROM strata_evidence WHERE prompt_sha256=?", (prompt_hash,)).fetchone()
    )


def insert_result(target: sqlite3.Connection, prompt_hash: str, input_digest: str, result: dict[str, Any]) -> None:
    target.execute("DELETE FROM prompt_strata WHERE prompt_sha256=?", (prompt_hash,))
    target.execute(
        "INSERT INTO prompt_strata VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            prompt_hash,
            input_digest,
            STRATIFIER_VERSION,
            CONFIG_SHA256,
            "completed",
            result["source_processing_status"],
            result["complexity_queue"],
            result["queue_rule_id"],
            result["structure_state"],
            result["dialogue_state"],
            result["duration_state"],
            result["text_length_band"],
            result["marker_density_band"],
            result["reference_density_band"],
            canonical_json(result["scene_tags"]),
            canonical_json(result["risk_flags"]),
            canonical_json(result["queue_reasons"]),
            canonical_json(result["features"]),
            result["classification_digest"],
            None,
        ),
    )
    target.executemany(
        "INSERT INTO strata_evidence(prompt_sha256,ordinal,dimension,rule_id,evidence_kind,fact_kind,fact_ordinal,evidence_start,evidence_end,evidence_sha256,evidence_preview) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                prompt_hash,
                ordinal,
                item["dimension"],
                item["rule_id"],
                item["evidence_kind"],
                item["fact_kind"],
                item["fact_ordinal"],
                item["evidence_start"],
                item["evidence_end"],
                item["evidence_sha256"],
                item["evidence_preview"],
            )
            for ordinal, item in enumerate(result["evidence"])
        ],
    )


def logical_target_digest(target: sqlite3.Connection) -> str:
    tables = [row[0] for row in target.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    payload: list[Any] = []
    for table in tables:
        info = list(target.execute(f"PRAGMA table_info({table})"))
        columns = [row[1] for row in info]
        primary = [row[1] for row in info if row[5]]
        order = ",".join(primary or columns)
        rows = [list(row) for row in target.execute(f"SELECT {','.join(columns)} FROM {table} ORDER BY {order}")]
        payload.append({"table": table, "columns": columns, "rows": rows})
    return sha256_text(canonical_json(payload))


def validate_target(target: sqlite3.Connection, records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = target.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()[0]
    errors: list[str] = []
    hashes = set(records)
    rows = list(target.execute("SELECT * FROM prompt_strata ORDER BY prompt_sha256"))
    row_hashes = {row["prompt_sha256"] for row in rows}
    if row_hashes != hashes:
        errors.append(f"prompt_closure:{len(row_hashes)}!={len(hashes)}")
    for row in rows:
        prompt_hash = row["prompt_sha256"]
        if row["complexity_queue"] not in QUEUE_CODES:
            errors.append(f"{prompt_hash}:invalid_queue")
        scene_tags = json.loads(row["scene_tags_json"])
        risk_flags = json.loads(row["risk_flags_json"])
        features = json.loads(row["features_json"])
        if not scene_tags or scene_tags != sorted(set(scene_tags)):
            errors.append(f"{prompt_hash}:scene_tags")
        if risk_flags != sorted(set(risk_flags)):
            errors.append(f"{prompt_hash}:risk_flags")
        if set(CONFIG["frequency_features_forbidden"]) & set(features):
            errors.append(f"{prompt_hash}:frequency_feature")
        dimensions = {
            evidence[0]
            for evidence in target.execute("SELECT dimension FROM strata_evidence WHERE prompt_sha256=?", (prompt_hash,))
        }
        missing_dimensions = REQUIRED_EVIDENCE_DIMENSIONS - dimensions
        if missing_dimensions:
            errors.append(f"{prompt_hash}:missing_evidence:{','.join(sorted(missing_dimensions))}")
    for row in target.execute("SELECT prompt_sha256,ordinal,evidence_start,evidence_end,evidence_sha256 FROM strata_evidence ORDER BY prompt_sha256,ordinal"):
        prompt_text = records[row["prompt_sha256"]]["prompt_text"]
        start = row["evidence_start"]
        end = row["evidence_end"]
        if not 0 <= start < end <= len(prompt_text):
            errors.append(f"{row['prompt_sha256']}:{row['ordinal']}:range")
        elif sha256_text(prompt_text[start:end]) != row["evidence_sha256"]:
            errors.append(f"{row['prompt_sha256']}:{row['ordinal']}:hash")
    return {
        "integrity_check": integrity,
        "foreign_key_error_count": int(foreign_keys),
        "validation_error_count": len(errors),
        "validation_errors": errors[:20],
        "passed": integrity == "ok" and foreign_keys == 0 and not errors,
    }


def count_json_values(rows: Iterable[sqlite3.Row], column: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter.update(json.loads(row[column]))
    return dict(sorted(counter.items()))


def stratify(
    source_database: Path = DEFAULT_SOURCE_DATABASE,
    preprocessed_database: Path = DEFAULT_PREPROCESSED_DATABASE,
    run_dir: Path = DEFAULT_RUN_DIR,
    prompt_hashes: Sequence[str] | None = None,
    *,
    batch_name: str = DEFAULT_BATCH_NAME,
    require_full_universe: bool = True,
) -> dict[str, Any]:
    source_database = source_database.resolve()
    preprocessed_database = preprocessed_database.resolve()
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    source_before = source_state(source_database)
    preprocessed_before = source_state(preprocessed_database)
    source_snapshot = source_snapshot_sha256(source_before)
    preprocessed_snapshot = source_snapshot_sha256(preprocessed_before)
    source = connect_readonly(source_database)
    preprocessed = connect_readonly(preprocessed_database)
    target_path = run_dir / "stratification.sqlite3"
    manifest_path = run_dir / "manifest.json"
    report_path = run_dir / "report.json"
    target: sqlite3.Connection | None = None
    try:
        records = load_records(source, preprocessed, prompt_hashes)
        hashes = list(records)
        universe_check = not require_full_universe or len(hashes) == EXPECTED_VIDEO_PROMPTS
        if not universe_check:
            raise RuntimeError(f"expected {EXPECTED_VIDEO_PROMPTS} video Prompts, found {len(hashes)}")
        manifest = {
            "schema_version": 1,
            "batch_name": batch_name,
            "stratifier_version": STRATIFIER_VERSION,
            "stratifier_config_sha256": CONFIG_SHA256,
            "prompt_hashes": hashes,
        }
        manifest_sha = sha256_text(canonical_json(manifest))
        batch_id = manifest_sha[:24]
        target = connect_target(target_path)
        target.execute("BEGIN IMMEDIATE")
        target.execute("INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", ("schema_version", canonical_json(1)))
        target.execute("INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", ("stratifier_version", canonical_json(STRATIFIER_VERSION)))
        target.execute("INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", ("stratifier_config_sha256", canonical_json(CONFIG_SHA256)))
        target.execute("INSERT INTO batches VALUES (?,?,?,?,?,?,?) ON CONFLICT(batch_id) DO UPDATE SET source_snapshot_sha256=excluded.source_snapshot_sha256,preprocessed_snapshot_sha256=excluded.preprocessed_snapshot_sha256,status=excluded.status", (batch_id, batch_name, manifest_sha, len(hashes), source_snapshot, preprocessed_snapshot, "running"))
        target.execute("COMMIT")
        processed = skipped = 0
        for prompt_hash, record in records.items():
            input_digest = record_input_digest(record)
            if should_skip(target, prompt_hash, input_digest):
                skipped += 1
                continue
            result = classify_record(record)
            target.execute("BEGIN IMMEDIATE")
            try:
                insert_result(target, prompt_hash, input_digest, result)
                target.execute("COMMIT")
            except BaseException:
                target.execute("ROLLBACK")
                raise
            processed += 1
        target.execute("BEGIN IMMEDIATE")
        target.execute("UPDATE batches SET status='completed' WHERE batch_id=?", (batch_id,))
        target.execute("COMMIT")
        validation = validate_target(target, records)
        rows = list(target.execute("SELECT * FROM prompt_strata ORDER BY prompt_sha256"))
        queue_counts = dict(target.execute("SELECT complexity_queue,count(*) FROM prompt_strata GROUP BY complexity_queue ORDER BY complexity_queue"))
        dimensions = {
            "structure_state_counts": dict(target.execute("SELECT structure_state,count(*) FROM prompt_strata GROUP BY structure_state ORDER BY structure_state")),
            "dialogue_state_counts": dict(target.execute("SELECT dialogue_state,count(*) FROM prompt_strata GROUP BY dialogue_state ORDER BY dialogue_state")),
            "duration_state_counts": dict(target.execute("SELECT duration_state,count(*) FROM prompt_strata GROUP BY duration_state ORDER BY duration_state")),
            "text_length_band_counts": dict(target.execute("SELECT text_length_band,count(*) FROM prompt_strata GROUP BY text_length_band ORDER BY text_length_band")),
            "marker_density_band_counts": dict(target.execute("SELECT marker_density_band,count(*) FROM prompt_strata GROUP BY marker_density_band ORDER BY marker_density_band")),
            "reference_density_band_counts": dict(target.execute("SELECT reference_density_band,count(*) FROM prompt_strata GROUP BY reference_density_band ORDER BY reference_density_band")),
            "scene_tag_counts": count_json_values(rows, "scene_tags_json"),
            "risk_flag_counts": count_json_values(rows, "risk_flags_json"),
        }
        logical_digest = logical_target_digest(target)
        target.close()
        target = None
        source.rollback()
        source.close()
        preprocessed.rollback()
        preprocessed.close()
        source_after = source_state(source_database)
        preprocessed_after = source_state(preprocessed_database)
        source_unchanged = source_snapshot == source_snapshot_sha256(source_after)
        preprocessed_unchanged = preprocessed_snapshot == source_snapshot_sha256(preprocessed_after)
        report = {
            "schema_version": 1,
            "status": "pass" if validation["passed"] and source_unchanged and preprocessed_unchanged and universe_check else "fail",
            "batch_id": batch_id,
            "batch_name": batch_name,
            "manifest_sha256": manifest_sha,
            "source_database": str(source_database),
            "preprocessed_database": str(preprocessed_database),
            "target_database": str(target_path),
            "source_snapshot_sha256": source_snapshot,
            "preprocessed_snapshot_sha256": preprocessed_snapshot,
            "source_state_unchanged": source_unchanged,
            "preprocessed_state_unchanged": preprocessed_unchanged,
            "source_file_state_before": source_before,
            "source_file_state_after": source_after,
            "preprocessed_file_state_before": preprocessed_before,
            "preprocessed_file_state_after": preprocessed_after,
            "selected_prompt_count": len(hashes),
            "processed": processed,
            "skipped": skipped,
            "failed": 0,
            "queue_counts": queue_counts,
            **dimensions,
            "logical_target_digest": logical_digest,
            "checks": {"full_universe": universe_check, "target": validation},
        }
        write_json_atomic(manifest_path, manifest)
        write_json_atomic(report_path, report)
        return report
    finally:
        if target is not None:
            try:
                target.close()
            except Exception:
                pass
        for connection in (source, preprocessed):
            try:
                connection.rollback()
            except Exception:
                pass
            try:
                connection.close()
            except Exception:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic Stage 4B-2 risk and complexity queues.")
    parser.add_argument("--source-database", type=Path, default=DEFAULT_SOURCE_DATABASE)
    parser.add_argument("--preprocessed-database", type=Path, default=DEFAULT_PREPROCESSED_DATABASE)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--batch-name", default=DEFAULT_BATCH_NAME)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = stratify(args.source_database, args.preprocessed_database, args.run_dir, batch_name=args.batch_name)
    except Exception as error:
        print(json.dumps({"status": "fail", "error": type(error).__name__, "details": str(error)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "status",
                    "selected_prompt_count",
                    "processed",
                    "skipped",
                    "failed",
                    "queue_counts",
                    "source_state_unchanged",
                    "preprocessed_state_unchanged",
                    "logical_target_digest",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
