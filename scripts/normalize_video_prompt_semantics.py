from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

from preprocess_video_prompt_sample import (
    REGRESSION_SAMPLE_HASHES,
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
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-4b-semantic-normalization-sample"
DEFAULT_BATCH_NAME = "stage-4b-3-approved-sample-semantic-normalization"
NORMALIZER_VERSION = "stage4b-light-semantic-normalization-v2"
EXPECTED_VIDEO_PROMPTS = 6555
STATUS_CODES = ("normalized", "needs_manual_review", "excluded_with_reason")
PROCESSING_CODES = ("completed", "failed")

MODEL_SYNTAX_RE = re.compile(
    r"<<<[^<>\r\n]{1,150}>>>|<(?:Picture|Subject|Video|Audio)\s+\d+>|"
    r"(?<![\w@])@[A-Za-z][A-Za-z0-9_.-]*\b",
    re.I,
)
MODEL_NAME_RE = re.compile(r"\b(?:seedance|h3|t2va|i2va|fl2va|l2va|ref2va|r2v|i2v|t2v)\b", re.I)
HEADING_RE = re.compile(r"^[\s\-_=*|:]+$|^[A-Z][A-Z0-9 /&()'\-]{1,80}:?$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\u3002\uff01\uff1f])\s+")

FIELD_NAMES = (
    "objective",
    "subjects",
    "spatial_relations",
    "action_summary",
    "performance_dialogue_reaction",
    "camera_result",
    "lighting",
    "sound",
    "physics",
    "continuity",
    "constraints",
    "material_references",
    "missing_fields",
    "source_conflicts",
    "uncertainty",
    "transferability",
)

CONFIG = {
    "max_candidates": {
        "objective": 2,
        "spatial_relations": 12,
        "action_summary": 14,
        "performance_dialogue_reaction": 10,
        "camera_result": 10,
        "lighting": 10,
        "sound": 10,
        "physics": 12,
        "continuity": 16,
        "constraints": 20,
    },
    "minimum_normalizable_chars": 80,
    "model_syntax_policy": "Remove model-specific reference labels and adapter tokens from neutral summaries; retain provenance in material_references and evidence only.",
    "media_policy": "Corpus contains source metadata but no accessible media bytes; reference bindings therefore remain described_only.",
    "status_policy": "Damaged, failed, video-less, or semantically underdetermined records are explicit non-normalized statuses; no record is silently skipped.",
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
    stratification_snapshot_sha256 TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_normalizations (
    prompt_sha256 TEXT PRIMARY KEY,
    source_input_sha256 TEXT NOT NULL,
    normalizer_version TEXT NOT NULL,
    normalizer_config_sha256 TEXT NOT NULL,
    processing_status TEXT NOT NULL CHECK(processing_status IN ('completed', 'failed')),
    normalization_status TEXT NOT NULL CHECK(normalization_status IN ('normalized', 'needs_manual_review', 'excluded_with_reason')),
    source_processing_status TEXT NOT NULL,
    complexity_queue TEXT NOT NULL,
    scene_tags_json TEXT NOT NULL,
    risk_flags_json TEXT NOT NULL,
    source_prompt_chars INTEGER NOT NULL,
    objective_text TEXT,
    subjects_json TEXT NOT NULL,
    spatial_relations_json TEXT NOT NULL,
    action_summary_json TEXT NOT NULL,
    performance_dialogue_reaction_json TEXT NOT NULL,
    camera_result_json TEXT NOT NULL,
    lighting_json TEXT NOT NULL,
    sound_json TEXT NOT NULL,
    physics_json TEXT NOT NULL,
    continuity_json TEXT NOT NULL,
    constraints_json TEXT NOT NULL,
    material_references_json TEXT NOT NULL,
    missing_fields_json TEXT NOT NULL,
    source_conflicts_json TEXT NOT NULL,
    uncertainty_json TEXT NOT NULL,
    transferability_json TEXT NOT NULL,
    status_reasons_json TEXT NOT NULL,
    normalization_digest TEXT NOT NULL,
    failure_code TEXT
);
CREATE TABLE IF NOT EXISTS normalization_assets (
    prompt_sha256 TEXT NOT NULL REFERENCES prompt_normalizations(prompt_sha256) ON DELETE CASCADE,
    asset_id TEXT NOT NULL,
    asset_type TEXT,
    item_type TEXT,
    model TEXT,
    duration_seconds REAL,
    resolution TEXT,
    media_status TEXT NOT NULL CHECK(media_status IN ('metadata_only', 'real_media_available', 'unknown')),
    PRIMARY KEY(prompt_sha256, asset_id)
);
CREATE TABLE IF NOT EXISTS normalization_evidence (
    prompt_sha256 TEXT NOT NULL REFERENCES prompt_normalizations(prompt_sha256) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    operation TEXT NOT NULL CHECK(operation IN ('direct', 'merge', 'compress', 'conflict', 'infer', 'omit', 'unknown', 'flag')),
    evidence_kind TEXT NOT NULL CHECK(evidence_kind IN ('source_span', 'full_scan', 'fact_ref', 'issue_ref', 'metadata', 'none')),
    fact_kind TEXT,
    fact_ordinal INTEGER,
    issue_code TEXT,
    evidence_start INTEGER,
    evidence_end INTEGER,
    evidence_sha256 TEXT,
    evidence_preview TEXT NOT NULL,
    PRIMARY KEY(prompt_sha256, ordinal)
);
CREATE TABLE IF NOT EXISTS normalization_decisions (
    prompt_sha256 TEXT NOT NULL REFERENCES prompt_normalizations(prompt_sha256) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    operation TEXT NOT NULL CHECK(operation IN ('preserve', 'merge', 'compress', 'conflict_choice', 'infer', 'omit', 'flag', 'unknown', 'exclude')),
    rationale TEXT NOT NULL,
    authority TEXT NOT NULL,
    evidence_ordinal INTEGER,
    PRIMARY KEY(prompt_sha256, ordinal),
    FOREIGN KEY(prompt_sha256, evidence_ordinal) REFERENCES normalization_evidence(prompt_sha256, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_prompt_normalizations_status ON prompt_normalizations(normalization_status);
CREATE INDEX IF NOT EXISTS idx_prompt_normalizations_queue ON prompt_normalizations(complexity_queue);
CREATE INDEX IF NOT EXISTS idx_normalization_evidence_field ON normalization_evidence(field_name);
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
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        connection.close()
        raise RuntimeError(f"integrity_check failed for {path}")
    if connection.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()[0]:
        connection.close()
        raise RuntimeError(f"foreign key check failed for {path}")
    return connection


def target_connection(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.executescript(TARGET_SCHEMA)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def unique_values(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = canonical_json(value)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def clip_text(value: str, limit: int = 520) -> str:
    value = re.sub(r"\s+", " ", value).strip(" \t\r\n-\u2014:;,|")
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."


def clean_model_syntax(value: str) -> str:
    value = MODEL_SYNTAX_RE.sub(" ", value)
    value = MODEL_NAME_RE.sub(" ", value)
    value = re.sub(r"\b(?:mode|prompt\s*mode|runtime\s*task)\s*[:=]\s*[A-Za-z0-9_-]+", " ", value, flags=re.I)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n-\u2014:;,|")


def iter_segments(prompt_text: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for line_match in re.finditer(r"[^\r\n]+", prompt_text):
        raw_line = line_match.group(0)
        stripped = raw_line.strip()
        if not stripped or HEADING_RE.fullmatch(stripped) or set(stripped) <= set("-=_*| "):
            continue
        leading = len(raw_line) - len(raw_line.lstrip())
        line_start = line_match.start() + leading
        parts = list(re.finditer(r"[^.!?\u3002\uff01\uff1f]+[.!?\u3002\uff01\uff1f]?", stripped))
        if len(parts) == 1 and len(stripped) > 900:
            parts = list(re.finditer(r"[^;\uff1b]+[;\uff1b]?", stripped))
        for part in parts:
            raw = part.group(0).strip()
            if not raw:
                continue
            raw_offset = part.start() + (len(part.group(0)) - len(part.group(0).lstrip()))
            start = line_start + raw_offset
            end = start + len(raw)
            cleaned = clean_model_syntax(raw)
            if cleaned and not HEADING_RE.fullmatch(cleaned):
                segments.append({"text": cleaned, "start": start, "end": end, "raw": prompt_text[start:end]})
    return segments


def candidate_segments(
    segments: Sequence[dict[str, Any]],
    pattern: re.Pattern[str],
    maximum: int,
) -> tuple[list[dict[str, Any]], bool]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for segment in segments:
        text = segment["text"]
        if not pattern.search(text):
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        selected.append(segment)
    return selected[:maximum], len(selected) > maximum


def parse_fact_value(fact: dict[str, Any]) -> Any:
    return json_value(fact.get("value_json"), None)


def fact_rows(record: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [fact for fact in record["facts"] if fact["fact_kind"] == kind]


def source_span(record: dict[str, Any], start: Any, end: Any) -> tuple[int | None, int | None, str | None, str]:
    text = record["prompt_text"]
    if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
        value = text[start:end]
        return start, end, sha256_text(value), clip_text(value, 240)
    return None, None, None, "No source span was available; the field is explicitly unknown or metadata-derived."


def reference_role(role_candidate: Any, description: str) -> str:
    role = str(role_candidate or "").lower()
    if "transform" in role:
        return "character_transformation"
    if "character" in role or "person" in role:
        return "character_identity"
    if "environment" in role or "location" in role:
        return "environment"
    if "prop" in role or "object" in role:
        return "prop"
    if "style" in role:
        return "style"
    lowered = description.lower()
    if re.search(r"\b(?:man|woman|person|character|fighter|demon|creature|human|face|body)\b", lowered):
        return "character_identity"
    if re.search(r"\b(?:weapon|sword|gun|prop|object|vehicle)\b", lowered):
        return "prop"
    return "environment"


def reference_description(raw: str, label: str | None) -> str:
    value = raw
    if label:
        value = value.replace(label, " ", 1)
    value = re.sub(r"^\s*(?:[-\u2014:=]|\[[^\]]+\])\s*", "", value)
    value = clean_model_syntax(value)
    return clip_text(value, 700)


def safe_speaker(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return clean_model_syntax(value).lower() or None


def duration_observation(record: dict[str, Any]) -> dict[str, Any]:
    structure = record["structure"]
    declared = unique_values(json_value(structure["declared_duration_values_json"], []))
    metadata = unique_values(json_value(structure["metadata_duration_values_json"], []))
    numeric_metadata = [value for value in metadata if isinstance(value, (int, float))]
    numeric_declared = [value for value in declared if isinstance(value, (int, float))]
    conflict = bool(numeric_declared and numeric_metadata and set(numeric_declared) != set(numeric_metadata))
    multiple = len(set(numeric_declared)) > 1 or len(set(numeric_metadata)) > 1
    if conflict or multiple:
        provenance = "unresolved_conflict"
        selected = None
    elif numeric_declared and numeric_metadata:
        provenance = "prompt_and_asset_agree"
        selected = numeric_declared[0]
    elif numeric_declared:
        provenance = "prompt_only"
        selected = numeric_declared[0]
    elif numeric_metadata:
        provenance = "asset_metadata_only"
        selected = numeric_metadata[0]
    else:
        provenance = "missing"
        selected = None
    return {
        "value_seconds": selected,
        "provenance": provenance,
        "prompt_declared_values": declared,
        "asset_metadata_values": metadata,
    }


def load_records(
    source: sqlite3.Connection,
    preprocessed: sqlite3.Connection,
    stratification: sqlite3.Connection,
    prompt_hashes: Sequence[str],
) -> dict[str, dict[str, Any]]:
    hashes = sorted(set(prompt_hashes))
    marks = ",".join("?" for _ in hashes)
    records: dict[str, dict[str, Any]] = {}
    for row in source.execute(
        f"SELECT prompt_sha256,prompt_text,source_prompt_chars,analysis_prompt_chars,url_redaction_count,first_asset_id FROM prompts WHERE prompt_sha256 IN ({marks}) ORDER BY prompt_sha256",
        hashes,
    ):
        records[row["prompt_sha256"]] = {
            "prompt_sha256": row["prompt_sha256"],
            "prompt_text": row["prompt_text"],
            "source_prompt_chars": row["source_prompt_chars"],
            "analysis_prompt_chars": row["analysis_prompt_chars"],
            "url_redaction_count": row["url_redaction_count"],
            "first_asset_id": row["first_asset_id"],
            "facts": [],
            "issues": [],
            "assets": [],
            "asset_memberships": [],
        }
    missing = sorted(set(hashes) - set(records))
    if missing:
        raise RuntimeError(f"missing source prompts: {', '.join(missing[:10])}")
    for row in preprocessed.execute(f"SELECT * FROM source_prompts WHERE prompt_sha256 IN ({marks}) ORDER BY prompt_sha256", hashes):
        records[row["prompt_sha256"]]["source_prompt"] = dict(row)
    for row in preprocessed.execute(f"SELECT * FROM prompt_structure WHERE prompt_sha256 IN ({marks}) ORDER BY prompt_sha256", hashes):
        records[row["prompt_sha256"]]["structure"] = dict(row)
    for row in preprocessed.execute(f"SELECT * FROM extracted_facts WHERE prompt_sha256 IN ({marks}) ORDER BY prompt_sha256,ordinal", hashes):
        records[row["prompt_sha256"]]["facts"].append(dict(row))
    for row in preprocessed.execute(f"SELECT * FROM processing_issues WHERE prompt_sha256 IN ({marks}) ORDER BY prompt_sha256,ordinal", hashes):
        records[row["prompt_sha256"]]["issues"].append(dict(row))
    for row in preprocessed.execute(f"SELECT * FROM source_assets WHERE prompt_sha256 IN ({marks}) ORDER BY prompt_sha256,asset_id", hashes):
        records[row["prompt_sha256"]]["assets"].append(dict(row))
    for row in preprocessed.execute(f"SELECT * FROM source_asset_folders WHERE prompt_sha256 IN ({marks}) ORDER BY prompt_sha256,asset_id,folder_id", hashes):
        records[row["prompt_sha256"]]["asset_memberships"].append(dict(row))
    for row in stratification.execute(f"SELECT * FROM prompt_strata WHERE prompt_sha256 IN ({marks}) ORDER BY prompt_sha256", hashes):
        records[row["prompt_sha256"]]["strata"] = dict(row)
    for prompt_hash in hashes:
        record = records[prompt_hash]
        missing_parts = [key for key in ("source_prompt", "structure", "strata") if key not in record]
        if missing_parts:
            raise RuntimeError(f"incomplete derived record {prompt_hash}: {','.join(missing_parts)}")
    return {prompt_hash: records[prompt_hash] for prompt_hash in hashes}


def select_prompt_hashes(source: sqlite3.Connection, explicit: Sequence[str] | None, all_video_prompts: bool) -> tuple[list[str], dict[str, list[str]]]:
    if explicit and all_video_prompts:
        raise ValueError("--all-video-prompts cannot be combined with --prompt-sha256")
    if explicit:
        hashes = sorted(set(explicit))
        reasons = {prompt_hash: ["explicit_cli"] for prompt_hash in hashes}
    elif all_video_prompts:
        hashes = [
            row[0]
            for row in source.execute(
                "SELECT DISTINCT p.prompt_sha256 FROM prompts p JOIN assets a ON a.prompt_sha256=p.prompt_sha256 WHERE a.asset_type='video' ORDER BY p.prompt_sha256"
            )
        ]
        reasons = {prompt_hash: ["full-video-universe"] for prompt_hash in hashes}
    else:
        hashes = sorted(REGRESSION_SAMPLE_HASHES)
        reasons = {prompt_hash: [REGRESSION_SAMPLE_HASHES[prompt_hash]] for prompt_hash in hashes}
    if not hashes:
        raise RuntimeError("no Prompt hashes selected")
    marks = ",".join("?" for _ in hashes)
    found = {
        row[0]
        for row in source.execute(
            f"SELECT DISTINCT p.prompt_sha256 FROM prompts p JOIN assets a ON a.prompt_sha256=p.prompt_sha256 WHERE a.asset_type='video' AND p.prompt_sha256 IN ({marks})",
            hashes,
        )
    }
    missing = sorted(set(hashes) - found)
    if missing and all_video_prompts:
        raise RuntimeError(f"selected prompts are not video-related: {', '.join(missing[:10])}")
    return hashes, reasons


def record_input_digest(record: dict[str, Any]) -> str:
    payload = {
        "prompt_sha256": record["prompt_sha256"],
        "prompt_text_sha256": sha256_text(record["prompt_text"]),
        "source_prompt_chars": record["source_prompt_chars"],
        "source_input_sha256": record["source_prompt"]["source_input_sha256"],
        "source_content_digest": record["source_prompt"]["content_digest"],
        "structure": record["structure"],
        "facts": record["facts"],
        "issues": record["issues"],
        "strata": record["strata"],
        "assets": record["assets"],
        "asset_memberships": record["asset_memberships"],
    }
    return sha256_text(canonical_json(payload))


def issue_by_code(record: dict[str, Any], code: str) -> dict[str, Any] | None:
    for issue in record["issues"]:
        if issue.get("code") == code:
            return issue
    return None


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    text = record["prompt_text"]
    strata = record["strata"]
    issues = record["issues"]
    evidence: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    evidence_keys: set[tuple[Any, ...]] = set()

    def add_evidence(
        field_name: str,
        operation: str,
        *,
        start: int | None = None,
        end: int | None = None,
        evidence_kind: str = "source_span",
        fact_kind: str | None = None,
        fact_ordinal: int | None = None,
        issue_code: str | None = None,
    ) -> int:
        key = (field_name, operation, evidence_kind, fact_kind, fact_ordinal, issue_code, start, end)
        if key in evidence_keys:
            for item in evidence:
                if item["_key"] == key:
                    return item["ordinal"]
        evidence_keys.add(key)
        actual_start, actual_end, digest, preview = source_span(record, start, end)
        if evidence_kind in {"metadata", "none"}:
            actual_start = actual_end = None
            digest = None
            preview = "Metadata observation or explicit absence; no Prompt source span is claimed."
        elif evidence_kind == "full_scan":
            actual_start, actual_end, digest, preview = source_span(record, 0, len(text))
        item = {
            "_key": key,
            "ordinal": len(evidence),
            "field_name": field_name,
            "operation": operation,
            "evidence_kind": evidence_kind,
            "fact_kind": fact_kind,
            "fact_ordinal": fact_ordinal,
            "issue_code": issue_code,
            "evidence_start": actual_start,
            "evidence_end": actual_end,
            "evidence_sha256": digest,
            "evidence_preview": preview or "No source evidence available.",
        }
        evidence.append(item)
        return item["ordinal"]

    def add_decision(field_name: str, operation: str, rationale: str, evidence_ordinal: int, authority: str = "normalization_policy") -> None:
        decisions.append(
            {
                "ordinal": len(decisions),
                "field_name": field_name,
                "operation": operation,
                "rationale": rationale,
                "authority": authority,
                "evidence_ordinal": evidence_ordinal,
            }
        )

    def add_unknown(field_name: str, reason: str) -> None:
        evidence_ordinal = add_evidence(field_name, "unknown", evidence_kind="none")
        add_decision(field_name, "unknown", reason, evidence_ordinal)

    def choose(field_name: str, pattern: re.Pattern[str], maximum: int | None = None) -> list[dict[str, Any]]:
        limit = maximum or CONFIG["max_candidates"].get(field_name, 10)
        selected, compressed = candidate_segments(segments, pattern, limit)
        if compressed:
            evidence_ordinal = add_evidence(field_name, "compress", evidence_kind="full_scan")
            add_decision(field_name, "compress", f"Lightweight normalization retained the first {limit} source-ordered matches and recorded the full-scan evidence; omitted matches remain available in the immutable source Prompt.", evidence_ordinal)
        for item in selected:
            evidence_ordinal = add_evidence(field_name, "direct", start=item["start"], end=item["end"])
            add_decision(field_name, "preserve", "Summary preserves a source-proven segment after removing model-specific syntax and normalizing whitespace.", evidence_ordinal)
        return selected

    has_video = any(asset.get("asset_type") == "video" for asset in record["assets"])
    source_processing_status = record["structure"].get("processing_status", "failed")
    damaged = bool(issue_by_code(record, "unicode_replacement_character")) or "\ufffd" in text
    parser_failed = source_processing_status not in {"completed", "completed_with_issues"}
    manual_reasons: list[str] = []
    status = "normalized"
    if not has_video:
        status = "excluded_with_reason"
        manual_reasons.append("record has no video asset in the selected source mapping")
    elif damaged:
        status = "needs_manual_review"
        manual_reasons.append("source text contains a Unicode replacement character")
    elif parser_failed:
        status = "needs_manual_review"
        manual_reasons.append("4B-1 source preprocessing failed")

    segments = [] if damaged or parser_failed else iter_segments(text)
    model_syntax_matches = list(MODEL_SYNTAX_RE.finditer(text))
    if model_syntax_matches and not (damaged or parser_failed):
        first = model_syntax_matches[0]
        evidence_ordinal = add_evidence("transferability", "omit", start=first.start(), end=first.end())
        add_decision("model_syntax", "omit", "Seedance/H3 reference labels and adapter tokens are provenance syntax, not model-neutral scene facts; they are removed from neutral summaries.", evidence_ordinal, "model_neutral_contract")

    refs: list[dict[str, Any]] = []
    ref_seen: set[str] = set()
    for fact in fact_rows(record, "reference_block"):
        value = parse_fact_value(fact) or {}
        label = value.get("label") if isinstance(value, dict) else None
        raw = text[fact["evidence_start"] : fact["evidence_end"]]
        description = reference_description(raw, label)
        if not description:
            continue
        ref_id = "ref-" + sha256_text(str(label or description))[:12]
        if ref_id in ref_seen:
            continue
        ref_seen.add(ref_id)
        role = reference_role(value.get("role_candidate") if isinstance(value, dict) else None, description)
        evidence_ordinal = add_evidence("material_references", "direct", start=fact["evidence_start"], end=fact["evidence_end"], fact_kind=fact["fact_kind"], fact_ordinal=fact["ordinal"])
        add_decision("material_references", "preserve", "Reference role and description remain source-derived; the source label is kept only as provenance.", evidence_ordinal)
        refs.append(
            {
                "reference_id": ref_id,
                "source_label": label,
                "role": role,
                "description": description,
                "active_in_scene": True,
                "binding_status": "described_only",
                "media_status_reason": CONFIG["media_policy"],
            }
        )
    if not refs and re.search(r"\breference\s+image\b|\buploaded\s+image\b", text, re.I) and not (damaged or parser_failed):
        match = re.search(r"\b(?:reference\s+image|uploaded\s+image)\b", text, re.I)
        assert match is not None
        evidence_ordinal = add_evidence("material_references", "direct", start=match.start(), end=match.end())
        add_decision("material_references", "preserve", "An implicit image reference is recorded as described_only because no active media binding is present in the source corpus.", evidence_ordinal)
        refs.append(
            {
                "reference_id": "ref-implicit-" + sha256_text(match.group(0).lower())[:8],
                "source_label": None,
                "role": "environment",
                "description": "Implicit image reference described in the Prompt; exact pixels are unavailable.",
                "active_in_scene": True,
                "binding_status": "described_only",
                "media_status_reason": CONFIG["media_policy"],
            }
        )

    subject_refs = [ref for ref in refs if ref["role"] in {"character_identity", "character_transformation", "prop"}]
    subjects = [
        {
            "subject_id": ref["reference_id"],
            "description": ref["description"],
            "current_state": None,
            "reference_id": ref["reference_id"],
        }
        for ref in subject_refs
    ]

    objective_matches = choose(
        "objective",
        re.compile(r"\b(?:objective|goal|purpose|narrative\s+summary|scene\s+context|establish|show|stage|connect|edit|transform|presents?|holds?)\b", re.I),
        2,
    )
    if not objective_matches and segments:
        objective_matches = [segments[0]]
        evidence_ordinal = add_evidence("objective", "direct", start=segments[0]["start"], end=segments[0]["end"])
        add_decision("objective", "preserve", "No explicit objective label was found; the first source-ordered scene-bearing segment is retained without adding an unstated goal.", evidence_ordinal)
    objective_text = " ".join(item["text"] for item in objective_matches) or None

    spatial_matches = choose(
        "spatial_relations",
        re.compile(r"\b(?:screen[- ]?left|screen[- ]?right|left|right|front|behind|near|center|west|east|north|south|above|below|across|between|inside|outside|toward|away|diagonal|ground floor|side of|height|distance)\b", re.I),
    )
    action_matches = choose(
        "action_summary",
        re.compile(r"\b(?:fight|fighting|attack|strike|punch|kick|dodge|block|parry|grab|throw|slam|chase|run|walk|jump|fall|rise|turn|look|glide|cross|move|hold|rain|connect|edit|transform|shoot|says?|speaks?|react|reaction|deliver|stands?|standing|appears?|clears?|threads?|crawls?)\w*\b", re.I),
    )
    causal_beats = []
    for order, item in enumerate(action_matches, 1):
        causal_link = "explicit temporal or causal connector in source segment" if re.search(r"\b(?:after|before|because|therefore|so|then|until|while|when|as)\b", item["text"], re.I) else "source order only; no explicit causal connector extracted"
        causal_beats.append({"order": order, "summary": item["text"], "causal_link": causal_link, "source_derivation": "direct"})
    if not causal_beats:
        add_unknown("action_summary", "No source segment met the deterministic action signal rules.")

    dialogue_lines: list[dict[str, Any]] = []
    seen_lines: set[str] = set()
    for fact in fact_rows(record, "dialogue"):
        value = parse_fact_value(fact) or {}
        line = value.get("line") if isinstance(value, dict) else None
        if not isinstance(line, str) or len(line.strip()) < 2 or line.strip().lower() in {"k", "ng", "m"}:
            continue
        key = line.strip()
        if key.casefold() in seen_lines:
            continue
        seen_lines.add(key.casefold())
        evidence_ordinal = add_evidence("performance_dialogue_reaction", "direct", start=fact.get("evidence_start"), end=fact.get("evidence_end"), fact_kind=fact["fact_kind"], fact_ordinal=fact["ordinal"])
        add_decision("performance_dialogue_reaction", "preserve", "Dialogue text is retained verbatim from the extracted quoted-line fact; no translation or speaker invention is applied.", evidence_ordinal)
        dialogue_lines.append({"speaker": safe_speaker(value.get("speaker")), "line": key, "delivery": None})
    performance_matches = choose(
        "performance_dialogue_reaction",
        re.compile(r"\b(?:performance|perform|reaction|reacts?|expression|emotion|gaze|eye contact|looks?|listens?|speaks?|says?|whispers?|shouts?|breathes?|hesitates?|smirk|blink|eyebrow|delivery|register|tone|voice|grin)\w*\b", re.I),
    )
    performance = {
        "dialogue_lines": dialogue_lines,
        "performance_segments": [item["text"] for item in performance_matches],
        "dialogue_scope": "ambiguous" if strata.get("dialogue_state") == "ambiguous" else ("detected" if dialogue_lines else "none"),
    }

    camera_matches = choose("camera_result", re.compile(r"\b(?:camera|lens|framing|shot|close[- ]?up|wide|angle|viewpoint|handheld|locked|stabilized|gimbal|zoom|drift|dolly|pan|tilt|focus|depth of field|reframe|parallax|shutter|focal)\w*\b", re.I))
    lighting_matches = choose("lighting", re.compile(r"\b(?:light|lighting|lit|illumination|sconce|amber|sodium|daylight|night|black sky|shadow|backlit|edge-lit|practical|haze|glow|neon|exposure|contrast|palette)\w*\b", re.I))
    sound_matches = choose("sound", re.compile(r"\b(?:audio|sound|sfx|music|dialogue|voice|rumble|traffic|rain|thunder|hum|breath|rustle|creak|noise|ambience|ambient|mechanical)\w*\b", re.I))
    physics_matches = choose("physics", re.compile(r"\b(?:force|momentum|gravity|friction|impact|fall|speed|steady|weight|mass|height|rail|road|wind|rain|motion|parallax|damage|intact|floor|collision|pressure|direction)\w*\b", re.I))
    continuity_matches = choose("continuity", re.compile(r"\b(?:throughout|remain|remains|always|never|fixed|consistent|same|one character|one train|one continuous|no cuts|no change|persist|returns|normal speed|slow motion)\w*\b", re.I))
    constraint_matches = choose("constraints", re.compile(r"\b(?:no|not|never|do not|must|only|without|exclude|excluded|avoid|prohibit|keep|lock|hard lock|negative)\w*\b", re.I))

    missing_fields: list[dict[str, str]] = []
    if not objective_text:
        missing_fields.append({"field": "objective", "reason": "No source-bearing objective segment was extracted."})
    if not subjects and "environment_establishing" not in json_value(strata.get("scene_tags_json"), []):
        missing_fields.append({"field": "subjects", "reason": "No character, prop, or transformation reference block was extracted."})
    if not spatial_matches:
        missing_fields.append({"field": "spatial_relations", "reason": "No explicit spatial or directional relation was extracted."})
    if not causal_beats:
        missing_fields.append({"field": "action_summary", "reason": "No source action segment was extracted."})
    if not performance["dialogue_lines"] and not performance["performance_segments"]:
        missing_fields.append({"field": "performance_dialogue_reaction", "reason": "No dialogue or performance signal was extracted."})
    for name, matches in (("camera_result", camera_matches), ("lighting", lighting_matches), ("sound", sound_matches), ("physics", physics_matches), ("continuity", continuity_matches), ("constraints", constraint_matches)):
        if not matches:
            missing_fields.append({"field": name, "reason": "No source segment matched the deterministic extraction rules."})
    if missing_fields:
        evidence_ordinal = add_evidence("missing_fields", "flag", evidence_kind="none")
        add_decision("missing_fields", "flag", "Missing fields remain explicit rather than being filled with generic cinematic assumptions.", evidence_ordinal)

    source_conflicts: list[dict[str, Any]] = []
    duration = duration_observation(record)
    if duration["provenance"] == "unresolved_conflict":
        issue = issue_by_code(record, "duration_metadata_conflict")
        evidence_ordinal = add_evidence("source_conflicts", "conflict", start=issue.get("evidence_start") if issue else None, end=issue.get("evidence_end") if issue else None, evidence_kind="issue_ref" if issue else "metadata", issue_code=issue.get("code") if issue else "duration")
        add_decision("duration", "conflict_choice", "Prompt-declared and asset-metadata durations are preserved side by side; 4B-3 makes no user-authority choice.", evidence_ordinal)
        source_conflicts.append({"field": "duration", "observed_values": duration, "resolution": {"status": "unresolved", "selected_value": None, "authority": "none", "rationale": "Conflicting source layers require explicit review before a model adapter chooses a runtime."}})
    for issue in issues:
        code = issue.get("code")
        if code == "take_structure_conflict":
            evidence_ordinal = add_evidence("source_conflicts", "conflict", start=issue.get("evidence_start"), end=issue.get("evidence_end"), evidence_kind="issue_ref", issue_code=code)
            add_decision("take_structure", "conflict_choice", "Conflicting single-take and multi-take declarations remain unresolved; no cut structure is invented.", evidence_ordinal)
            source_conflicts.append({"field": "take_structure", "observed_values": ["conflicted"], "resolution": {"status": "unresolved", "selected_value": None, "authority": "none", "rationale": "The deterministic preprocessor reported a structure conflict."}})
        elif code not in {"duration_metadata_conflict"}:
            evidence_ordinal = add_evidence("uncertainty", "flag", start=issue.get("evidence_start"), end=issue.get("evidence_end"), evidence_kind="issue_ref", issue_code=code)
            add_decision(code or "source_issue", "flag", "Source issue is retained as an uncertainty; the normalizer does not silently resolve it.", evidence_ordinal)

    uncertainties: list[dict[str, Any]] = []
    for item in missing_fields:
        uncertainties.append({"kind": "missing_field", **item})
    for issue in issues:
        raw_details = json_value(issue.get("details_json"), {})
        uncertainties.append({"kind": "processing_issue", "code": issue.get("code"), "details": clean_model_syntax(canonical_json(raw_details))})
    if any(line["speaker"] is None for line in dialogue_lines):
        uncertainties.append({"kind": "dialogue_speaker", "reason": "One or more extracted dialogue lines have no source-proven speaker."})
    if any(ref["binding_status"] == "described_only" for ref in refs):
        uncertainties.append({"kind": "media_binding", "reason": "Reference roles are described, but no accessible media bytes are bound in this corpus."})
    if strata.get("duration_state") in {"conflict", "multiple_metadata"} and not source_conflicts:
        uncertainties.append({"kind": "duration", "reason": "4B-2 flagged duration uncertainty; both source layers are retained."})

    if status == "normalized":
        semantic_signal_count = sum(bool(value) for value in (objective_text, subjects, spatial_matches, causal_beats, performance_matches, camera_matches, lighting_matches, sound_matches, physics_matches, continuity_matches, constraint_matches))
        if len(text) < CONFIG["minimum_normalizable_chars"] or semantic_signal_count < 2:
            status = "needs_manual_review"
            manual_reasons.append("source text is too short or semantically underdetermined for a reliable neutral summary")
    if not refs and "dense_references" in json_value(strata.get("risk_flags_json"), []):
        uncertainties.append({"kind": "reference_resolution", "reason": "4B-2 observed dense or unresolved reference syntax without a reliable role mapping."})
    if manual_reasons:
        evidence_ordinal = add_evidence("status", "flag", evidence_kind="full_scan" if text else "none")
        add_decision("status", "flag" if status != "excluded_with_reason" else "exclude", "; ".join(manual_reasons), evidence_ordinal, "normalization_status_policy")

    transfer_status = "portable_scene_intent" if status == "normalized" else "blocked_needs_manual_review"
    transferability = {
        "seedance": {"status": transfer_status, "media_binding": "none", "final_prompt_generated": False},
        "h3": {"status": transfer_status, "media_binding": "none", "final_prompt_generated": False},
        "model_specific_syntax_removed": bool(model_syntax_matches),
        "blocked_items": [reason for reason in manual_reasons],
    }
    status_reasons = sorted(set(manual_reasons))
    if not status_reasons and status == "normalized":
        status_reasons = ["source-provable neutral summary completed"]

    payload = {
        "normalization_status": status,
        "source_processing_status": source_processing_status,
        "complexity_queue": strata.get("complexity_queue", "unknown"),
        "scene_tags": json_value(strata.get("scene_tags_json"), []),
        "risk_flags": json_value(strata.get("risk_flags_json"), []),
        "objective": objective_text,
        "subjects": subjects,
        "spatial_relations": [item["text"] for item in spatial_matches],
        "action_summary": {"duration": duration, "beats": causal_beats},
        "performance_dialogue_reaction": performance,
        "camera_result": {"segments": [item["text"] for item in camera_matches]},
        "lighting": {"segments": [item["text"] for item in lighting_matches]},
        "sound": {"segments": [item["text"] for item in sound_matches]},
        "physics": {"segments": [item["text"] for item in physics_matches]},
        "continuity": [item["text"] for item in continuity_matches],
        "constraints": [item["text"] for item in constraint_matches],
        "material_references": refs,
        "missing_fields": missing_fields,
        "source_conflicts": source_conflicts,
        "uncertainty": uncertainties,
        "transferability": transferability,
        "status_reasons": status_reasons,
    }
    normalization_digest = sha256_text(canonical_json(payload))
    for item in evidence:
        item.pop("_key", None)
    return {
        **payload,
        "normalization_digest": normalization_digest,
        "evidence": evidence,
        "decisions": decisions,
        "assets": record["assets"],
        "processing_status": "completed",
        "failure_code": None,
    }


def failure_result(record: dict[str, Any], error: BaseException) -> dict[str, Any]:
    strata = record.get("strata", {})
    empty = {"segments": []}
    reason = f"normalizer exception {type(error).__name__}: {error}"
    evidence = [{
        "ordinal": 0,
        "field_name": "status",
        "operation": "flag",
        "evidence_kind": "none",
        "fact_kind": None,
        "fact_ordinal": None,
        "issue_code": type(error).__name__,
        "evidence_start": None,
        "evidence_end": None,
        "evidence_sha256": None,
        "evidence_preview": "No source span; processing failed visibly and requires manual review.",
    }]
    decisions = [{"ordinal": 0, "field_name": "status", "operation": "flag", "rationale": reason, "authority": "processing_failure", "evidence_ordinal": 0}]
    payload = {
        "normalization_status": "needs_manual_review",
        "source_processing_status": record.get("structure", {}).get("processing_status", "failed"),
        "complexity_queue": strata.get("complexity_queue", "unknown"),
        "scene_tags": json_value(strata.get("scene_tags_json"), []),
        "risk_flags": json_value(strata.get("risk_flags_json"), []),
        "objective": None,
        "subjects": [],
        "spatial_relations": [],
        "action_summary": {"duration": duration_observation(record), "beats": []},
        "performance_dialogue_reaction": {"dialogue_lines": [], "performance_segments": [], "dialogue_scope": "unknown"},
        "camera_result": empty,
        "lighting": empty,
        "sound": empty,
        "physics": empty,
        "continuity": [],
        "constraints": [],
        "material_references": [],
        "missing_fields": [{"field": field, "reason": "normalizer exception"} for field in FIELD_NAMES],
        "source_conflicts": [],
        "uncertainty": [{"kind": "processing_failure", "reason": reason}],
        "transferability": {"seedance": {"status": "blocked_needs_manual_review", "media_binding": "none", "final_prompt_generated": False}, "h3": {"status": "blocked_needs_manual_review", "media_binding": "none", "final_prompt_generated": False}, "model_specific_syntax_removed": False, "blocked_items": [reason]},
        "status_reasons": [reason],
    }
    return {**payload, "normalization_digest": sha256_text(canonical_json(payload)), "evidence": evidence, "decisions": decisions, "assets": record.get("assets", []), "processing_status": "failed", "failure_code": type(error).__name__}


def should_skip(target: sqlite3.Connection, prompt_hash: str, input_digest: str) -> bool:
    row = target.execute(
        "SELECT source_input_sha256,normalizer_version,normalizer_config_sha256,processing_status FROM prompt_normalizations WHERE prompt_sha256=?",
        (prompt_hash,),
    ).fetchone()
    if not row or row["source_input_sha256"] != input_digest or row["normalizer_version"] != NORMALIZER_VERSION or row["normalizer_config_sha256"] != CONFIG_SHA256 or row["processing_status"] != "completed":
        return False
    return bool(
        target.execute("SELECT 1 FROM normalization_evidence WHERE prompt_sha256=? LIMIT 1", (prompt_hash,)).fetchone()
        and target.execute("SELECT 1 FROM normalization_decisions WHERE prompt_sha256=? LIMIT 1", (prompt_hash,)).fetchone()
        and target.execute("SELECT 1 FROM normalization_assets WHERE prompt_sha256=? LIMIT 1", (prompt_hash,)).fetchone()
    )


def insert_result(target: sqlite3.Connection, prompt_hash: str, input_digest: str, result: dict[str, Any], record: dict[str, Any]) -> None:
    target.execute("DELETE FROM prompt_normalizations WHERE prompt_sha256=?", (prompt_hash,))
    target.execute(
        """INSERT INTO prompt_normalizations (
            prompt_sha256,source_input_sha256,normalizer_version,normalizer_config_sha256,processing_status,
            normalization_status,source_processing_status,complexity_queue,scene_tags_json,risk_flags_json,
            source_prompt_chars,objective_text,subjects_json,spatial_relations_json,action_summary_json,
            performance_dialogue_reaction_json,camera_result_json,lighting_json,sound_json,physics_json,
            continuity_json,constraints_json,material_references_json,missing_fields_json,source_conflicts_json,
            uncertainty_json,transferability_json,status_reasons_json,normalization_digest,failure_code
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            prompt_hash,
            input_digest,
            NORMALIZER_VERSION,
            CONFIG_SHA256,
            result["processing_status"],
            result["normalization_status"],
            result["source_processing_status"],
            result["complexity_queue"],
            canonical_json(result["scene_tags"]),
            canonical_json(result["risk_flags"]),
            record["source_prompt_chars"],
            result["objective"],
            canonical_json(result["subjects"]),
            canonical_json(result["spatial_relations"]),
            canonical_json(result["action_summary"]),
            canonical_json(result["performance_dialogue_reaction"]),
            canonical_json(result["camera_result"]),
            canonical_json(result["lighting"]),
            canonical_json(result["sound"]),
            canonical_json(result["physics"]),
            canonical_json(result["continuity"]),
            canonical_json(result["constraints"]),
            canonical_json(result["material_references"]),
            canonical_json(result["missing_fields"]),
            canonical_json(result["source_conflicts"]),
            canonical_json(result["uncertainty"]),
            canonical_json(result["transferability"]),
            canonical_json(result["status_reasons"]),
            result["normalization_digest"],
            result["failure_code"],
        ),
    )
    target.executemany(
        "INSERT INTO normalization_assets(prompt_sha256,asset_id,asset_type,item_type,model,duration_seconds,resolution,media_status) VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                prompt_hash,
                asset["asset_id"],
                asset.get("asset_type"),
                asset.get("item_type"),
                asset.get("model"),
                asset.get("duration_seconds"),
                asset.get("resolution"),
                "metadata_only",
            )
            for asset in result["assets"]
        ],
    )
    target.executemany(
        """INSERT INTO normalization_evidence(
            prompt_sha256,ordinal,field_name,operation,evidence_kind,fact_kind,fact_ordinal,issue_code,
            evidence_start,evidence_end,evidence_sha256,evidence_preview
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (
                prompt_hash,
                item["ordinal"],
                item["field_name"],
                item["operation"],
                item["evidence_kind"],
                item["fact_kind"],
                item["fact_ordinal"],
                item["issue_code"],
                item["evidence_start"],
                item["evidence_end"],
                item["evidence_sha256"],
                item["evidence_preview"],
            )
            for item in result["evidence"]
        ],
    )
    target.executemany(
        "INSERT INTO normalization_decisions(prompt_sha256,ordinal,field_name,operation,rationale,authority,evidence_ordinal) VALUES (?,?,?,?,?,?,?)",
        [
            (
                prompt_hash,
                item["ordinal"],
                item["field_name"],
                item["operation"],
                item["rationale"],
                item["authority"],
                item["evidence_ordinal"],
            )
            for item in result["decisions"]
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
    errors: list[str] = []
    integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = target.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()[0]
    rows = list(target.execute("SELECT * FROM prompt_normalizations ORDER BY prompt_sha256"))
    expected_hashes = set(records)
    actual_hashes = {row["prompt_sha256"] for row in rows}
    if actual_hashes != expected_hashes:
        errors.append(f"prompt_closure:{len(actual_hashes)}!={len(expected_hashes)}")
    neutral_columns = [
        "objective_text", "subjects_json", "spatial_relations_json", "action_summary_json", "performance_dialogue_reaction_json",
        "camera_result_json", "lighting_json", "sound_json", "physics_json", "continuity_json", "constraints_json",
        "missing_fields_json", "source_conflicts_json", "uncertainty_json", "transferability_json",
    ]
    for row in rows:
        prompt_hash = row["prompt_sha256"]
        if row["normalization_status"] not in STATUS_CODES:
            errors.append(f"{prompt_hash}:status")
        if not json_value(row["status_reasons_json"], []):
            errors.append(f"{prompt_hash}:missing_status_reason")
        evidence = list(target.execute("SELECT * FROM normalization_evidence WHERE prompt_sha256=? ORDER BY ordinal", (prompt_hash,)))
        decisions = list(target.execute("SELECT * FROM normalization_decisions WHERE prompt_sha256=? ORDER BY ordinal", (prompt_hash,)))
        if not evidence or not decisions:
            errors.append(f"{prompt_hash}:missing_audit_rows")
        evidence_ordinals = {item["ordinal"] for item in evidence}
        if any(item["evidence_ordinal"] is None or item["evidence_ordinal"] not in evidence_ordinals for item in decisions):
            errors.append(f"{prompt_hash}:decision_evidence_link")
        record = records.get(prompt_hash)
        if record is None:
            continue
        prompt_text = record["prompt_text"]
        for item in evidence:
            start, end = item["evidence_start"], item["evidence_end"]
            if item["evidence_kind"] in {"source_span", "full_scan", "fact_ref"}:
                if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(prompt_text):
                    errors.append(f"{prompt_hash}:{item['ordinal']}:range")
                elif item["evidence_sha256"] != sha256_text(prompt_text[start:end]):
                    errors.append(f"{prompt_hash}:{item['ordinal']}:hash")
            elif item["evidence_kind"] == "issue_ref" and start is not None and end is not None:
                if not 0 <= start < end <= len(prompt_text):
                    errors.append(f"{prompt_hash}:{item['ordinal']}:range")
                elif item["evidence_sha256"] != sha256_text(prompt_text[start:end]):
                    errors.append(f"{prompt_hash}:{item['ordinal']}:hash")
        asset_ids = {row[0] for row in target.execute("SELECT asset_id FROM normalization_assets WHERE prompt_sha256=?", (prompt_hash,))}
        if asset_ids != {asset["asset_id"] for asset in record["assets"]}:
            errors.append(f"{prompt_hash}:asset_mapping")
        for column in neutral_columns:
            value = row[column]
            if value is not None and MODEL_SYNTAX_RE.search(value):
                errors.append(f"{prompt_hash}:{column}:model_syntax")
    return {
        "integrity_check": integrity,
        "foreign_key_error_count": int(foreign_keys),
        "validation_error_count": len(errors),
        "validation_errors": errors[:20],
        "passed": integrity == "ok" and foreign_keys == 0 and not errors,
    }


def count_json_values(rows: Iterable[sqlite3.Row], column: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(json_value(row[column], []))
    return dict(sorted(counts.items()))


def normalize(
    source_database: Path = DEFAULT_SOURCE_DATABASE,
    preprocessed_database: Path = DEFAULT_PREPROCESSED_DATABASE,
    stratification_database: Path = DEFAULT_STRATIFICATION_DATABASE,
    run_dir: Path = DEFAULT_RUN_DIR,
    prompt_hashes: Sequence[str] | None = None,
    *,
    all_video_prompts: bool = False,
    batch_name: str = DEFAULT_BATCH_NAME,
    require_full_universe: bool = True,
) -> dict[str, Any]:
    source_database = source_database.resolve()
    preprocessed_database = preprocessed_database.resolve()
    stratification_database = stratification_database.resolve()
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    source_before = source_state(source_database)
    preprocessed_before = source_state(preprocessed_database)
    stratification_before = source_state(stratification_database)
    source_snapshot = source_snapshot_sha256(source_before)
    preprocessed_snapshot = source_snapshot_sha256(preprocessed_before)
    stratification_snapshot = source_snapshot_sha256(stratification_before)
    source: sqlite3.Connection | None = None
    preprocessed: sqlite3.Connection | None = None
    stratification: sqlite3.Connection | None = None
    target: sqlite3.Connection | None = None
    try:
        source = connect_readonly(source_database)
        hashes, selection_reasons = select_prompt_hashes(source, prompt_hashes, all_video_prompts)
        universe_check = not require_full_universe or (all_video_prompts and len(hashes) == EXPECTED_VIDEO_PROMPTS)
        if require_full_universe and all_video_prompts and not universe_check:
            raise RuntimeError(f"expected {EXPECTED_VIDEO_PROMPTS} video Prompts, found {len(hashes)}")
        preprocessed = connect_readonly(preprocessed_database)
        stratification = connect_readonly(stratification_database)
        records = load_records(source, preprocessed, stratification, hashes)
        manifest = {
            "schema_version": 1,
            "batch_name": batch_name,
            "normalizer_version": NORMALIZER_VERSION,
            "normalizer_config_sha256": CONFIG_SHA256,
            "prompt_hashes": hashes,
            "selection_reasons": selection_reasons,
        }
        manifest_sha = sha256_text(canonical_json(manifest))
        batch_id = manifest_sha[:24]
        target_path = run_dir / "semantic_normalization.sqlite3"
        target = target_connection(target_path)
        target.execute("BEGIN IMMEDIATE")
        for key, value in (("schema_version", 1), ("normalizer_version", NORMALIZER_VERSION), ("normalizer_config_sha256", CONFIG_SHA256)):
            target.execute("INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", (key, canonical_json(value)))
        target.execute(
            """INSERT INTO batches(batch_id,batch_name,manifest_sha256,expected_prompt_count,source_snapshot_sha256,preprocessed_snapshot_sha256,stratification_snapshot_sha256,status)
            VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(batch_id) DO UPDATE SET source_snapshot_sha256=excluded.source_snapshot_sha256,preprocessed_snapshot_sha256=excluded.preprocessed_snapshot_sha256,stratification_snapshot_sha256=excluded.stratification_snapshot_sha256,status=excluded.status""",
            (batch_id, batch_name, manifest_sha, len(hashes), source_snapshot, preprocessed_snapshot, stratification_snapshot, "running"),
        )
        target.execute("COMMIT")
        processed = skipped = failed = 0
        for prompt_hash, record in records.items():
            input_digest = record_input_digest(record)
            if should_skip(target, prompt_hash, input_digest):
                skipped += 1
                continue
            try:
                result = normalize_record(record)
            except Exception as error:
                result = failure_result(record, error)
                failed += 1
            target.execute("BEGIN IMMEDIATE")
            try:
                insert_result(target, prompt_hash, input_digest, result, record)
                target.execute("COMMIT")
            except BaseException:
                target.execute("ROLLBACK")
                raise
            processed += 1
        target.execute("BEGIN IMMEDIATE")
        target.execute("UPDATE batches SET status=? WHERE batch_id=?", ("completed" if failed == 0 else "failed", batch_id))
        target.execute("COMMIT")
        validation = validate_target(target, records)
        rows = list(target.execute("SELECT * FROM prompt_normalizations ORDER BY prompt_sha256"))
        status_counts = dict(target.execute("SELECT normalization_status,count(*) FROM prompt_normalizations GROUP BY normalization_status ORDER BY normalization_status"))
        queue_counts = dict(target.execute("SELECT complexity_queue,count(*) FROM prompt_normalizations GROUP BY complexity_queue ORDER BY complexity_queue"))
        risk_counts = count_json_values(rows, "risk_flags_json")
        review_records = []
        for row in rows:
            prompt_hash = row["prompt_sha256"]
            review_records.append(
                {
                    "prompt_sha256": prompt_hash,
                    "normalization_status": row["normalization_status"],
                    "complexity_queue": row["complexity_queue"],
                    "scene_tags": json_value(row["scene_tags_json"], []),
                    "risk_flags": json_value(row["risk_flags_json"], []),
                    "source_prompt_chars": row["source_prompt_chars"],
                    "objective": row["objective_text"],
                    "subjects": json_value(row["subjects_json"], []),
                    "spatial_relations": json_value(row["spatial_relations_json"], []),
                    "action_summary": json_value(row["action_summary_json"], {}),
                    "performance_dialogue_reaction": json_value(row["performance_dialogue_reaction_json"], {}),
                    "camera_result": json_value(row["camera_result_json"], {}),
                    "lighting": json_value(row["lighting_json"], {}),
                    "sound": json_value(row["sound_json"], {}),
                    "physics": json_value(row["physics_json"], {}),
                    "continuity": json_value(row["continuity_json"], []),
                    "constraints": json_value(row["constraints_json"], []),
                    "material_references": json_value(row["material_references_json"], []),
                    "missing_fields": json_value(row["missing_fields_json"], []),
                    "source_conflicts": json_value(row["source_conflicts_json"], []),
                    "uncertainty": json_value(row["uncertainty_json"], []),
                    "transferability": json_value(row["transferability_json"], {}),
                    "status_reasons": json_value(row["status_reasons_json"], []),
                    "asset_mapping_count": target.execute("SELECT count(*) FROM normalization_assets WHERE prompt_sha256=?", (prompt_hash,)).fetchone()[0],
                    "evidence_count": target.execute("SELECT count(*) FROM normalization_evidence WHERE prompt_sha256=?", (prompt_hash,)).fetchone()[0],
                    "decision_count": target.execute("SELECT count(*) FROM normalization_decisions WHERE prompt_sha256=?", (prompt_hash,)).fetchone()[0],
                }
            )
        logical_digest = logical_target_digest(target)
        target.close()
        target = None
        source.rollback()
        source.close()
        source = None
        preprocessed.rollback()
        preprocessed.close()
        preprocessed = None
        stratification.rollback()
        stratification.close()
        stratification = None
        source_after = source_state(source_database)
        preprocessed_after = source_state(preprocessed_database)
        stratification_after = source_state(stratification_database)
        source_unchanged = source_snapshot == source_snapshot_sha256(source_after)
        preprocessed_unchanged = preprocessed_snapshot == source_snapshot_sha256(preprocessed_after)
        stratification_unchanged = stratification_snapshot == source_snapshot_sha256(stratification_after)
        report = {
            "schema_version": 1,
            "status": "pass" if validation["passed"] and source_unchanged and preprocessed_unchanged and stratification_unchanged and failed == 0 else "fail",
            "batch_id": batch_id,
            "batch_name": batch_name,
            "manifest_sha256": manifest_sha,
            "source_database": str(source_database),
            "preprocessed_database": str(preprocessed_database),
            "stratification_database": str(stratification_database),
            "target_database": str(target_path),
            "source_snapshot_sha256": source_snapshot,
            "preprocessed_snapshot_sha256": preprocessed_snapshot,
            "stratification_snapshot_sha256": stratification_snapshot,
            "source_state_unchanged": source_unchanged,
            "preprocessed_state_unchanged": preprocessed_unchanged,
            "stratification_state_unchanged": stratification_unchanged,
            "selected_prompt_count": len(hashes),
            "processed": processed,
            "skipped": skipped,
            "failed": failed,
            "status_counts": status_counts,
            "queue_counts": queue_counts,
            "risk_flag_counts": risk_counts,
            "logical_target_digest": logical_digest,
            "review_sample": str(run_dir / "review-sample.json"),
            "checks": {"full_universe": universe_check, "target": validation},
            "source_file_state_before": source_before,
            "source_file_state_after": source_after,
            "preprocessed_file_state_before": preprocessed_before,
            "preprocessed_file_state_after": preprocessed_after,
            "stratification_file_state_before": stratification_before,
            "stratification_file_state_after": stratification_after,
        }
        write_json_atomic(run_dir / "manifest.json", manifest)
        write_json_atomic(run_dir / "review-sample.json", {"schema_version": 1, "normalizer_version": NORMALIZER_VERSION, "records": review_records})
        write_json_atomic(run_dir / "report.json", report)
        return report
    finally:
        if target is not None:
            try:
                target.close()
            except Exception:
                pass
        for connection in (source, preprocessed, stratification):
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
    parser = argparse.ArgumentParser(description="Build deterministic Stage 4B-3 lightweight semantic records.")
    parser.add_argument("--source-database", type=Path, default=DEFAULT_SOURCE_DATABASE)
    parser.add_argument("--preprocessed-database", type=Path, default=DEFAULT_PREPROCESSED_DATABASE)
    parser.add_argument("--stratification-database", type=Path, default=DEFAULT_STRATIFICATION_DATABASE)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--batch-name", default=DEFAULT_BATCH_NAME)
    parser.add_argument("--prompt-sha256", action="append")
    parser.add_argument("--all-video-prompts", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = normalize(
            args.source_database,
            args.preprocessed_database,
            args.stratification_database,
            args.run_dir,
            args.prompt_sha256,
            all_video_prompts=args.all_video_prompts,
            batch_name=args.batch_name,
            require_full_universe=True,
        )
    except Exception as error:
        print(json.dumps({"status": "fail", "error": type(error).__name__, "details": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({key: report[key] for key in ("status", "selected_prompt_count", "processed", "skipped", "failed", "status_counts", "queue_counts", "logical_target_digest")}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
