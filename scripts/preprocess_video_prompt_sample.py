from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from probe_higgsfield import utc_now, write_json_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DATABASE = WORK_ROOT / "data" / "runs" / "project-corpus" / "corpus.sqlite3"
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-4b-preprocessing-sample"
DEFAULT_BATCH_NAME = "stage-4b-1-approved-sample"
EXTRACTOR_VERSION = "stage4b-structure-v1"

APPROVED_SAMPLE_HASHES = {
    "086a04b7f0f8e168bfcbf3183684e1cf275d57e59a3c639dbdabc0713867d658": "approved-dialogue-sample",
    "166a0440f6f01e02419b42f47d088e1919dedd1800b62b4b632e0047cb446ba0": "approved-action-sample",
    "00e4c15e723379bb862770bb9c4a46093978048a29e2426de31e3c39fb512c89": "approved-environment-sample",
}
REGRESSION_SAMPLE_HASHES = {
    **APPROVED_SAMPLE_HASHES,
    "6fa9b80340f7687453c55a0ea663414aaf63fb04b2f5a04066d9481527716095": "short-prompt",
    "c5fd19556a918b65ba0fd4a44fdcb27321e60391b54c56351ee756753ee395a6": "long-prompt",
    "4b03eb316c71b5651f9729e9e35afdcb6f1533a25036885c21991f62dded35fd": "mixed-image-video",
    "001974c55eb04ce39405bc668773ab703c6e6d493061d995719ca9239b53e77f": "multi-duration",
    "06dd14a0547f35ba2821a3f6e49214cf499335b7c981559cc33e0687557e6d26": "null-model",
    "875fd06de19abfc521f9d176224cc51be08f6b6ee4c8df5e9ce1b3c4c880fd0a": "multi-folder",
    "084f62c9a2c6aa19f0058be94c38c00275ac194ca3e8ffeb35384f7a89f83757": "unicode-replacement",
}

TRIPLE_REFERENCE_RE = re.compile(r"<<<(?P<label>[^<>\r\n]{1,150})>>>")
AT_REFERENCE_RE = re.compile(r"(?<![\w@])@(?P<label>[A-Za-z][A-Za-z0-9_.-]*[A-Za-z0-9_])\b")
H3_MEDIA_REFERENCE_RE = re.compile(r"<(?P<kind>Picture|Subject|Video|Audio)\s+(?P<number>\d+)>", re.I)
REFERENCE_DEFINITION_RE = re.compile(
    r"(?m)^[ \t]*(?P<label><<<[^<>\r\n]{1,150}>>>|@[A-Za-z][A-Za-z0-9_.-]*[A-Za-z0-9_]*)"
    r"[ \t]*(?:[-\u2013\u2014:=]|\[)"
)
LABELED_DURATION_RE = re.compile(
    r"\b(?:total\s+)?duration\s*(?::|=|-)?\s*(?P<approx>[~\u2248])?"
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>s\b|secs?\b|seconds?\b|\u79d2\b|\u0441\u0435\u043a(?:\u0443\u043d\u0434[\u0430\u044b]?)?\b)",
    re.I,
)
DURATION_TOKEN_RE = re.compile(
    r"(?<![\w.])(?P<approx>[~\u2248])?(?P<value>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>s\b|secs?\b|seconds?\b|\u79d2\b|\u0441\u0435\u043a(?:\u0443\u043d\u0434[\u0430\u044b]?)?\b)",
    re.I,
)
ASPECT_TOKEN_RE = re.compile(
    r"(?<![\d:])(?P<width>\d{1,2}(?:\.\d+)?)\s*:\s*(?P<height>\d{1,2}(?:\.\d+)?)(?![\d:])"
)
LABELED_ASPECT_RE = re.compile(
    r"\b(?:aspect(?:\s+ratio)?|ratio)\s*(?::|=|-)?\s*(?P<value>\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?)",
    re.I,
)
MODE_RE = re.compile(r"\b(?:R2V|T2V|I2V|T2VA|I2VA|FL2VA|L2VA|Ref2VA)\b", re.I)
NATURAL_MODE_RE = re.compile(r"\b(?:image-to-video|text-to-video|reference-to-video)\b", re.I)
MODE_LABEL_RE = re.compile(r"\b(?:mode|prompt\s+mode|generation\s+mode)\s*[:=]\s*(?P<value>[^,.;\n]+)", re.I)
MODEL_LABEL_RE = re.compile(r"\bmodel\s*[:=]\s*(?P<value>[^,.;\n]+)", re.I)
TIMECODE_RE = re.compile(
    r"(?<![\d:])(?:(?:[01]?\d|2[0-3]):)?(?:[0-5]?\d):[0-5]\d(?:\.\d{1,3})?(?![\d:])"
)
TIMELINE_RANGE_RE = re.compile(
    r"(?<![\w.])(?:"
    r"\d+(?:\.\d+)?(?:s|\u79d2)\s*(?:[-\u2013\u2014]|to)\s*\d+(?:\.\d+)?(?:s|\u79d2)?|"
    r"\d+(?:\.\d+)?\s*(?:[-\u2013\u2014]|to)\s*\d+(?:\.\d+)?(?:s|\u79d2)"
    r")\b",
    re.I,
)
TIMELINE_POINT_RE = re.compile(r"\b(?:at|t\s*=)\s*[~\u2248]?\d+(?:\.\d+)?\s*s\b", re.I)
SHOT_LINE_RE = re.compile(
    r"(?:^|(?<=[.;]))[ \t]*(?:[-*]\s*)?(?:\[\s*)?(?P<kind>(?:SMASH|HARD|MATCH)\s+CUT|CUT(?:\s+TO)?|SHOT|BEAT|BLOCK|SEGMENT|PHASE|ACT|\u955c\u5934|\u573a\u666f|\u0421\u0426\u0415\u041d\u0410|\u041a\u0410\u0414\u0420)\b",
    re.I,
)
SINGLE_TAKE_RE = re.compile(
    r"\b(?:single(?:[- ]continuous)?(?:[- ](?:shot|take))?|one continuous (?:shot|take)|single uninterrupted shot|no cuts?)\b",
    re.I,
)
MULTI_TAKE_RE = re.compile(r"\b(?:multi[- ]shot|multiple shots?|montage|sequence of \d+ shots?|\d+ cuts?)\b", re.I)
QUOTE_PATTERNS = (
    re.compile(r'"(?P<line>[^"\r\n]{1,500})"'),
    re.compile(r"\u201c(?P<line>[^\u201d\r\n]{1,500})\u201d"),
    re.compile(r"\u00ab(?P<line>[^\u00bb\r\n]{1,500})\u00bb"),
    re.compile(r"\u300c(?P<line>[^\u300d\r\n]{1,500})\u300d"),
)
DIALOGUE_CONTEXT_RE = re.compile(
    r"\b(?:dialogue|spoken\s+line|says?|speaks?|shouts?|whispers?|asks?|replies?|murmurs?|delivers?|voice|lip[- ]sync)\b|\u5bf9\u767d|\u53f0\u8bcd",
    re.I,
)
LANGUAGE_RE = re.compile(
    r"\b(?:in|speaks?|spoken|language)\s+(?P<language>Japanese|English|Chinese|Russian|Korean|Spanish|French)\b|"
    r"(?P<cjk>\u65e5\u8bed|\u82f1\u8bed|\u4e2d\u6587)",
    re.I,
)
SPEAKER_LABEL_RE = re.compile(r"(?m)(?:^|\n)[ \t]*(?P<speaker>[A-Z][A-Za-z0-9_<>-]{1,80})(?:\s*\([^\n)]{1,80}\))?\s*:\s*$")
JSON_SETTING_KEYS = {
    "duration": "declared_duration",
    "aspect_ratio": "declared_aspect_ratio",
    "aspect": "declared_aspect_ratio",
    "model": "declared_model",
    "mode": "generation_mode",
}
AUDIO_PATTERNS = (
    ("negative_music", re.compile(r"\bno\s+(?:music|score)\b", re.I)),
    ("negative_voiceover", re.compile(r"\bno\s+(?:voiceover|voice[- ]over)\b", re.I)),
    ("negative_subtitles", re.compile(r"\bno\s+subtitles?\b", re.I)),
    ("sfx_only", re.compile(r"\bSFX\s+only\b", re.I)),
    ("silence", re.compile(r"\b(?:complete|near|total)\s+silence\b|\bsilent\b", re.I)),
    ("audio_heading", re.compile(r"(?im)^[ \t]*(?:AUDIO|SOUND|SFX|SOUNDSCAPE|MUSIC)\s*:")),
)
ENTITY_ROLE_PATTERNS = {
    "character": re.compile(r"\b(?:character|person|man|woman|boy|girl|male|female|actor|monster|subject)\b", re.I),
    "environment": re.compile(r"\b(?:environment|location|arena|room|hall|city|street|interior|exterior|landscape|building)\b", re.I),
    "prop": re.compile(r"\b(?:prop|weapon|sword|katana|gun|shield|object|vehicle|train)\b", re.I),
}

TARGET_SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA synchronous = FULL;
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY NOT NULL, value_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS batches (
    batch_id TEXT PRIMARY KEY NOT NULL,
    batch_name TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL UNIQUE,
    expected_prompt_count INTEGER NOT NULL,
    source_snapshot_sha256 TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS batch_prompts (
    batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    prompt_sha256 TEXT NOT NULL REFERENCES source_prompts(prompt_sha256),
    PRIMARY KEY(batch_id, prompt_sha256), UNIQUE(batch_id, ordinal)
);
CREATE TABLE IF NOT EXISTS selection_reasons (
    batch_id TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY(batch_id, prompt_sha256, reason),
    FOREIGN KEY(batch_id, prompt_sha256) REFERENCES batch_prompts(batch_id, prompt_sha256) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS source_prompts (
    prompt_sha256 TEXT PRIMARY KEY NOT NULL,
    source_prompt_chars INTEGER NOT NULL,
    analysis_prompt_chars INTEGER NOT NULL,
    url_redaction_count INTEGER NOT NULL,
    first_asset_id TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    source_input_sha256 TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    extractor_config_sha256 TEXT NOT NULL,
    processing_status TEXT NOT NULL,
    content_digest TEXT,
    failure_code TEXT
);
CREATE TABLE IF NOT EXISTS source_folders (
    folder_id TEXT PRIMARY KEY NOT NULL,
    parent_id TEXT,
    name TEXT NOT NULL,
    path TEXT,
    depth INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS source_assets (
    asset_id TEXT PRIMARY KEY NOT NULL,
    prompt_sha256 TEXT NOT NULL REFERENCES source_prompts(prompt_sha256) ON DELETE CASCADE,
    primary_folder_id TEXT,
    primary_folder_name TEXT,
    primary_folder_path TEXT,
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
    source_page INTEGER,
    source_item_index INTEGER
);
CREATE INDEX IF NOT EXISTS source_assets_prompt_idx ON source_assets(prompt_sha256);
CREATE TABLE IF NOT EXISTS source_asset_folders (
    prompt_sha256 TEXT NOT NULL,
    asset_id TEXT NOT NULL REFERENCES source_assets(asset_id) ON DELETE CASCADE,
    folder_id TEXT NOT NULL,
    folder_name TEXT NOT NULL,
    folder_path TEXT,
    first_seen_page INTEGER,
    PRIMARY KEY(asset_id, folder_id)
);
CREATE TABLE IF NOT EXISTS source_occurrences (
    prompt_sha256 TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    item_index INTEGER NOT NULL,
    asset_id TEXT,
    item_type TEXT,
    parse_status TEXT NOT NULL,
    PRIMARY KEY(page_number, item_index),
    FOREIGN KEY(asset_id) REFERENCES source_assets(asset_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS source_issues (
    source_issue_id INTEGER PRIMARY KEY NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    item_index INTEGER,
    asset_id TEXT,
    severity TEXT NOT NULL,
    code TEXT NOT NULL,
    details_json TEXT NOT NULL,
    FOREIGN KEY(asset_id) REFERENCES source_assets(asset_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS extracted_facts (
    prompt_sha256 TEXT NOT NULL REFERENCES source_prompts(prompt_sha256) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    fact_kind TEXT NOT NULL,
    fact_subtype TEXT NOT NULL,
    value_json TEXT NOT NULL,
    evidence_start INTEGER NOT NULL,
    evidence_end INTEGER NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    evidence_preview TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    confidence TEXT NOT NULL,
    parse_status TEXT NOT NULL,
    PRIMARY KEY(prompt_sha256, ordinal)
);
CREATE INDEX IF NOT EXISTS extracted_facts_kind_idx ON extracted_facts(fact_kind, fact_subtype);
CREATE TABLE IF NOT EXISTS prompt_structure (
    prompt_sha256 TEXT PRIMARY KEY NOT NULL REFERENCES source_prompts(prompt_sha256) ON DELETE CASCADE,
    declared_duration_values_json TEXT NOT NULL,
    metadata_duration_values_json TEXT NOT NULL,
    declared_aspect_ratios_json TEXT NOT NULL,
    generation_modes_json TEXT NOT NULL,
    take_structure TEXT NOT NULL,
    heading_count INTEGER NOT NULL,
    shot_marker_count INTEGER NOT NULL,
    cut_marker_count INTEGER NOT NULL,
    timestamp_count INTEGER NOT NULL,
    dialogue_evidence_count INTEGER NOT NULL,
    dialogue_utterance_count INTEGER NOT NULL,
    reference_tag_count INTEGER NOT NULL,
    reference_label_count INTEGER NOT NULL,
    reference_block_count INTEGER NOT NULL,
    audio_signal_count INTEGER NOT NULL,
    processing_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processing_issues (
    prompt_sha256 TEXT NOT NULL REFERENCES source_prompts(prompt_sha256) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    severity TEXT NOT NULL,
    code TEXT NOT NULL,
    evidence_start INTEGER,
    evidence_end INTEGER,
    details_json TEXT NOT NULL,
    PRIMARY KEY(prompt_sha256, ordinal)
);
"""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_unique(values: Iterable[Any]) -> list[Any]:
    return sorted(set(values), key=lambda value: (value is None, str(value)))


def placeholders(values: Sequence[Any]) -> str:
    if not values:
        raise ValueError("placeholders requires at least one value")
    return ",".join("?" for _ in values)


def chunks(values: Sequence[str], size: int = 400) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


def evidence(prompt_text: str, start: int, end: int) -> dict[str, Any]:
    exact = prompt_text[start:end]
    return {
        "start": start,
        "end": end,
        "sha256": sha256_text(exact),
        "preview": re.sub(r"\s+", " ", exact).strip()[:240],
    }


def numeric(value: str) -> int | float:
    result = float(value.replace(",", "."))
    return int(result) if result.is_integer() else result


def match_value(match: re.Match[str], name: str) -> str:
    value = match.groupdict().get(name)
    return value.strip() if isinstance(value, str) else ""


def infer_entity_role(block: str) -> str | None:
    matched = [name for name, pattern in ENTITY_ROLE_PATTERNS.items() if pattern.search(block)]
    return matched[0] if len(matched) == 1 else None


def extract_prompt(prompt_text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    facts: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    occupied: set[tuple[str, int, int, str]] = set()

    def add_fact(
        kind: str,
        subtype: str,
        start: int,
        end: int,
        value: Any,
        rule_id: str,
        *,
        confidence: str = "high",
        parse_status: str = "asserted",
    ) -> None:
        if not 0 <= start < end <= len(prompt_text):
            raise ValueError(f"invalid evidence span: {start}:{end}")
        key = (kind, start, end, canonical_json(value))
        if key in occupied:
            return
        occupied.add(key)
        facts.append(
            {
                "fact_kind": kind,
                "fact_subtype": subtype,
                "value": value,
                "evidence": evidence(prompt_text, start, end),
                "rule_id": rule_id,
                "confidence": confidence,
                "parse_status": parse_status,
            }
        )

    def add_issue(
        code: str,
        severity: str,
        details: dict[str, Any],
        start: int | None = None,
        end: int | None = None,
    ) -> None:
        issues.append({"code": code, "severity": severity, "details": details, "start": start, "end": end})

    stripped = prompt_text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            json_prompt = json.loads(stripped)
        except json.JSONDecodeError as error:
            add_issue(
                "invalid_json_prompt",
                "warning",
                {"line": error.lineno, "column": error.colno},
            )
        else:
            if isinstance(json_prompt, dict):
                for key, kind in JSON_SETTING_KEYS.items():
                    if key not in json_prompt:
                        continue
                    field_match = re.search(
                        rf'"{re.escape(key)}"\s*:\s*(?:"(?:\\.|[^"\\])*"|[-+]?\d+(?:\.\d+)?|true|false|null)',
                        prompt_text,
                    )
                    if field_match is None:
                        add_issue("json_field_span_not_found", "warning", {"field": key})
                        continue
                    raw_value = json_prompt[key]
                    if kind == "declared_duration" and isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
                        value: Any = {"seconds": raw_value, "approximate": False}
                        subtype = "json"
                    elif kind == "declared_aspect_ratio" and isinstance(raw_value, str):
                        value = re.sub(r"\s+", "", raw_value)
                        subtype = "output"
                    elif isinstance(raw_value, (str, int, float)) and not isinstance(raw_value, bool):
                        value = raw_value
                        subtype = "json"
                    else:
                        add_issue("unsupported_json_setting_value", "warning", {"field": key, "type": type(raw_value).__name__}, field_match.start(), field_match.end())
                        continue
                    add_fact(kind, subtype, field_match.start(), field_match.end(), value, f"json.{key}.v1")

    for match in LABELED_DURATION_RE.finditer(prompt_text):
        add_fact(
            "declared_duration",
            "prompt_label",
            match.start(),
            match.end(),
            {"seconds": numeric(match_value(match, "value")), "approximate": bool(match_value(match, "approx"))},
            "duration.labeled.v1",
        )

    for line_match in re.finditer(r"(?m)^.*$", prompt_text):
        line = line_match.group(0)
        if not re.search(r"(?:16\s*:\s*9|2\.3\d\s*:\s*1|\b(?:SFX|Photoreal|NON-IP|Cinematic|Output|Settings)\b)", line, re.I):
            continue
        for match in DURATION_TOKEN_RE.finditer(line):
            start = line_match.start() + match.start()
            end = line_match.start() + match.end()
            if any(start < fact["evidence"]["end"] and end > fact["evidence"]["start"] for fact in facts if fact["fact_kind"] == "declared_duration"):
                continue
            add_fact(
                "declared_duration",
                "settings_line",
                start,
                end,
                {"seconds": numeric(match_value(match, "value")), "approximate": bool(match_value(match, "approx"))},
                "duration.settings-line.v1",
                confidence="medium",
            )

    for match in LABELED_ASPECT_RE.finditer(prompt_text):
        value = re.sub(r"\s+", "", match_value(match, "value"))
        add_fact("declared_aspect_ratio", "output", match.start(), match.end(), value, "aspect.labeled.v1")

    for line_match in re.finditer(r"(?m)^.*$", prompt_text):
        line = line_match.group(0)
        if not re.search(r"(?:aspect|ratio|cinemascope|anamorphic|letterbox|output|16\s*:\s*9|2\.3\d\s*:\s*1)", line, re.I):
            continue
        for match in ASPECT_TOKEN_RE.finditer(line):
            value = f"{match_value(match, 'width').replace(' ', '')}:{match_value(match, 'height').replace(' ', '')}"
            subtype = "optical" if re.search(r"cinemascope|anamorphic|letterbox", line, re.I) else "output"
            add_fact("declared_aspect_ratio", subtype, line_match.start() + match.start(), line_match.start() + match.end(), value, "aspect.context.v1", confidence="medium")

    for match in MODE_LABEL_RE.finditer(prompt_text):
        add_fact("generation_mode", "label", match.start(), match.end(), match_value(match, "value"), "mode.labeled.v1")
    for match in MODE_RE.finditer(prompt_text):
        add_fact("generation_mode", "token", match.start(), match.end(), match.group(0).upper(), "mode.token.v1", confidence="medium")
    for match in NATURAL_MODE_RE.finditer(prompt_text):
        add_fact("generation_mode", "natural_language", match.start(), match.end(), match.group(0).lower(), "mode.natural-language.v1", confidence="medium")
    for match in MODEL_LABEL_RE.finditer(prompt_text):
        add_fact("declared_model", "label", match.start(), match.end(), match_value(match, "value"), "model.labeled.v1", confidence="medium")

    for match in TRIPLE_REFERENCE_RE.finditer(prompt_text):
        add_fact("reference_tag", "triple", match.start(), match.end(), match_value(match, "label"), "reference.triple.v1")
    for match in AT_REFERENCE_RE.finditer(prompt_text):
        add_fact("reference_tag", "at_tag", match.start(), match.end(), match_value(match, "label"), "reference.at.v1")
    for match in H3_MEDIA_REFERENCE_RE.finditer(prompt_text):
        add_fact("reference_tag", "h3_media", match.start(), match.end(), {"kind": match_value(match, "kind"), "number": int(match_value(match, "number"))}, "reference.h3.v1")

    definitions = list(REFERENCE_DEFINITION_RE.finditer(prompt_text))
    defined_labels: set[str] = set()
    for index, definition in enumerate(definitions):
        end_candidates = [len(prompt_text)]
        if index + 1 < len(definitions):
            end_candidates.append(definitions[index + 1].start())
        blank = re.search(r"\n\s*\n", prompt_text[definition.end() :])
        if blank:
            end_candidates.append(definition.end() + blank.start())
        end = min(end_candidates)
        label = match_value(definition, "label")
        defined_labels.add(label)
        add_fact("reference_block", "definition", definition.start(), max(definition.end(), end), {"label": label, "role_candidate": infer_entity_role(prompt_text[definition.start() : end])}, "reference.block.v1", confidence="medium", parse_status="candidate")
        role = infer_entity_role(prompt_text[definition.start() : end])
        if role:
            add_fact("entity_reference_span", role, definition.start(), max(definition.end(), end), {"label": label, "role": role}, "entity.role-explicit-keyword.v1", confidence="medium", parse_status="candidate")

    for match in TRIPLE_REFERENCE_RE.finditer(prompt_text):
        label = match.group(0)
        if label not in defined_labels:
            add_issue("unresolved_reference_occurrence", "warning", {"label": label}, match.start(), match.end())
            break

    for line_match in re.finditer(r"(?m)^.*$", prompt_text):
        line = line_match.group(0)
        stripped = line.strip()
        if not stripped or re.fullmatch(r"[=\-_*\u2500\u2501\u2502\s]{3,}", stripped):
            continue
        markers = list(SHOT_LINE_RE.finditer(line))
        if markers:
            for marker in markers:
                kind = re.sub(r"\s+", "_", match_value(marker, "kind").lower())
                fact_kind = "cut_marker" if "cut" in kind else "shot_marker"
                add_fact(
                    fact_kind,
                    kind,
                    line_match.start() + marker.start(),
                    line_match.start() + marker.end(),
                    marker.group(0).strip(),
                    "shot-line.v1",
                )
            continue
        heading = False
        heading_value = stripped
        if re.match(r"^#{1,6}\s+", stripped):
            heading = True
        elif re.fullmatch(r"\[[^\]\r\n]{2,80}\]", stripped):
            heading = True
        elif re.fullmatch(r"[A-Z][A-Z0-9 /&+_()\-]{2,90}:?", stripped) and not re.search(r"\b(?:CUT|SHOT)\b", stripped):
            heading = True
        elif stripped.rstrip(":").upper() in {"REFERENCES", "ACTIVE REFERENCES", "DIALOGUE", "AUDIO", "SOUND", "SFX", "LIGHTING", "STYLE", "HARD LOCKS", "OUTPUT SETTINGS", "CAMERA"}:
            heading = True
        if heading:
            add_fact("heading", "section", line_match.start(), line_match.end(), heading_value, "heading.line.v1", confidence="medium")

    for match in TIMECODE_RE.finditer(prompt_text):
        add_fact("timestamp", "timecode", match.start(), match.end(), match.group(0), "timestamp.timecode.v1", confidence="medium")
    for match in TIMELINE_RANGE_RE.finditer(prompt_text):
        add_fact("timestamp", "range", match.start(), match.end(), match.group(0), "timestamp.range.v1", confidence="medium")
    for match in TIMELINE_POINT_RE.finditer(prompt_text):
        add_fact("timestamp", "point", match.start(), match.end(), match.group(0), "timestamp.point.v1", confidence="medium")

    single_matches = list(SINGLE_TAKE_RE.finditer(prompt_text))
    multi_matches = list(MULTI_TAKE_RE.finditer(prompt_text))
    for match in single_matches:
        add_fact("take_declaration", "single", match.start(), match.end(), "single", "take.single.v1")
    for match in multi_matches:
        add_fact("take_declaration", "multi", match.start(), match.end(), "multi", "take.multi.v1")

    dialogue_facts: list[tuple[str | None, str]] = []
    for match in re.finditer(r"(?is)<d>\s*\[(?P<label>[^\]\r\n]+)\](?P<line>.*?)</d>", prompt_text):
        line = re.sub(r"\s+", " ", match_value(match, "line")).strip()
        speaker = match_value(match, "label") or None
        dialogue_facts.append((speaker, line))
        add_fact("dialogue", "h3_block", match.start(), match.end(), {"speaker": speaker, "line": line}, "dialogue.h3.v1")
    for quote_pattern in QUOTE_PATTERNS:
        for match in quote_pattern.finditer(prompt_text):
            line = match_value(match, "line").strip()
            context = prompt_text[max(0, match.start() - 180) : min(len(prompt_text), match.end() + 80)]
            speaker_match = list(SPEAKER_LABEL_RE.finditer(prompt_text[max(0, match.start() - 220) : match.start()]))
            speaker = speaker_match[-1].group("speaker") if speaker_match else None
            if speaker in {"DIALOGUE", "AUDIO", "SOUND", "SFX", "VOICE"}:
                speaker = None
            explicit = bool(DIALOGUE_CONTEXT_RE.search(context)) or speaker is not None
            if not explicit:
                continue
            dialogue_facts.append((speaker, line))
            add_fact("dialogue", "quoted_line", match.start(), match.end(), {"speaker": speaker, "line": line}, "dialogue.quote-context.v1", confidence="medium")

    for match in LANGUAGE_RE.finditer(prompt_text):
        language = match_value(match, "language") or match_value(match, "cjk")
        add_fact("language", "explicit", match.start(), match.end(), language, "language.explicit.v1")

    for subtype, pattern in AUDIO_PATTERNS:
        for match in pattern.finditer(prompt_text):
            add_fact("audio", subtype, match.start(), match.end(), {"signal": match.group(0), "polarity": "negative" if subtype.startswith("negative") else "positive"}, "audio.signal.v1", confidence="medium")

    declared_durations = stable_unique(
        fact["value"]["seconds"] for fact in facts if fact["fact_kind"] == "declared_duration"
    )
    metadata_durations = stable_unique(metadata.get("duration_values", []))
    declared_aspects = stable_unique(
        fact["value"] for fact in facts if fact["fact_kind"] == "declared_aspect_ratio" and fact["fact_subtype"] == "output"
    )
    generation_modes = stable_unique(fact["value"] for fact in facts if fact["fact_kind"] == "generation_mode")
    take_values = {fact["value"] for fact in facts if fact["fact_kind"] == "take_declaration"}
    cut_count = sum(fact["fact_kind"] == "cut_marker" for fact in facts)
    if len(take_values) > 1 or ("single" in take_values and cut_count):
        take_structure = "conflict"
        add_issue("take_structure_conflict", "warning", {"declared": sorted(take_values), "cut_marker_count": cut_count})
    elif "single" in take_values:
        take_structure = "single"
    elif "multi" in take_values or cut_count:
        take_structure = "multi"
    else:
        take_structure = "not_declared"
    if len(declared_durations) > 1:
        add_issue("multiple_declared_duration_values", "warning", {"values": declared_durations})
    metadata_non_null = [value for value in metadata_durations if value is not None]
    if declared_durations and metadata_non_null and set(declared_durations).isdisjoint(metadata_non_null):
        add_issue("duration_metadata_conflict", "warning", {"declared": declared_durations, "metadata": metadata_durations})
    if len(declared_aspects) > 1:
        add_issue("multiple_output_aspect_values", "warning", {"values": declared_aspects})
    if any(fact["fact_subtype"] == "sfx_only" for fact in facts if fact["fact_kind"] == "audio") and dialogue_facts:
        add_issue("audio_dialogue_scope_ambiguity", "warning", {"sfx_only": True, "dialogue_count": len(dialogue_facts)})
    if "\ufffd" in prompt_text:
        position = prompt_text.index("\ufffd")
        add_issue("unicode_replacement_character", "warning", {}, position, position + 1)
    if metadata.get("url_redaction_count", 0):
        add_issue("prompt_url_redacted", "warning", {"count": metadata["url_redaction_count"]})

    facts.sort(key=lambda fact: (fact["evidence"]["start"], fact["evidence"]["end"], fact["fact_kind"], fact["fact_subtype"], canonical_json(fact["value"])))
    issues.sort(key=lambda issue: (issue["code"], issue["start"] if issue["start"] is not None else -1, canonical_json(issue["details"])))
    structure = {
        "declared_duration_values": declared_durations,
        "metadata_duration_values": metadata_durations,
        "declared_aspect_ratios": declared_aspects,
        "generation_modes": generation_modes,
        "take_structure": take_structure,
        "heading_count": sum(fact["fact_kind"] == "heading" for fact in facts),
        "shot_marker_count": sum(fact["fact_kind"] == "shot_marker" for fact in facts),
        "cut_marker_count": cut_count,
        "timestamp_count": sum(fact["fact_kind"] == "timestamp" for fact in facts),
        "dialogue_evidence_count": sum(fact["fact_kind"] == "dialogue" for fact in facts),
        "dialogue_utterance_count": len(set(dialogue_facts)),
        "reference_tag_count": sum(fact["fact_kind"] == "reference_tag" for fact in facts),
        "reference_label_count": len({fact["value"] if isinstance(fact["value"], str) else canonical_json(fact["value"]) for fact in facts if fact["fact_kind"] == "reference_tag"}),
        "reference_block_count": sum(fact["fact_kind"] == "reference_block" for fact in facts),
        "audio_signal_count": sum(fact["fact_kind"] == "audio" for fact in facts),
        "processing_status": "completed_with_issues" if issues else "completed",
    }
    content = {"facts": facts, "issues": issues, "structure": structure}
    return {"facts": facts, "issues": issues, "structure": structure, "content_digest": sha256_text(canonical_json(content))}


def source_file_state(path: Path) -> dict[str, Any]:
    state: dict[str, Any] = {"path": str(path.resolve()), "exists": path.exists()}
    if not path.exists():
        return state
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    stat = path.stat()
    state.update({"size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest.hexdigest()})
    return state


def source_state(database: Path) -> dict[str, Any]:
    files = [database, Path(str(database) + "-wal"), Path(str(database) + "-shm")]
    return {"files": [source_file_state(path) for path in files]}


def source_snapshot_sha256(state: dict[str, Any]) -> str:
    return sha256_text(canonical_json([{key: item.get(key) for key in ("path", "exists", "size", "sha256")} for item in state["files"]]))


def load_source_completion(database: Path) -> dict[str, Any] | None:
    status_path = database.parent / "status.json"
    if not status_path.exists():
        return None
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if not isinstance(status, dict) or status.get("checkpoint_complete") is not True:
        raise RuntimeError("source corpus checkpoint is not complete")
    return {
        "status": status.get("status"),
        "checkpoint_complete": status.get("checkpoint_complete"),
        "pages_committed": status.get("pages_committed"),
        "unique_prompt_count": status.get("unique_prompt_count"),
    }


def connect_source(database: Path) -> sqlite3.Connection:
    if not database.exists():
        raise FileNotFoundError(database)
    connection = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    if connection.execute("PRAGMA query_only").fetchone()[0] != 1:
        connection.close()
        raise RuntimeError("source database did not enter query_only mode")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        connection.close()
        raise RuntimeError(f"source integrity_check failed: {integrity}")
    if connection.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()[0]:
        connection.close()
        raise RuntimeError("source foreign_key_check failed")
    connection.execute("BEGIN")
    return connection


def load_source_records(connection: sqlite3.Connection, prompt_hashes: Sequence[str]) -> dict[str, dict[str, Any]]:
    hashes = sorted(set(prompt_hashes))
    records: dict[str, dict[str, Any]] = {}
    for batch in chunks(hashes):
        marks = placeholders(batch)
        for row in connection.execute(
            f"SELECT prompt_sha256,prompt_text,source_prompt_chars,analysis_prompt_chars,url_redaction_count,first_asset_id FROM prompts WHERE prompt_sha256 IN ({marks}) ORDER BY prompt_sha256",
            batch,
        ):
            records[row["prompt_sha256"]] = {"prompt_sha256": row["prompt_sha256"], "prompt_text": row["prompt_text"], "source_prompt_chars": row["source_prompt_chars"], "analysis_prompt_chars": row["analysis_prompt_chars"], "url_redaction_count": row["url_redaction_count"], "first_asset_id": row["first_asset_id"], "assets": [], "memberships": [], "occurrences": [], "issues": [], "folders": {}}
        for row in connection.execute(
            f"SELECT a.prompt_sha256,a.asset_id,a.folder_id,primary_folder.name AS primary_folder_name,primary_folder.path AS primary_folder_path,a.item_type,a.asset_type,a.status,a.job_set_type,a.model,a.created_at_unix,a.width,a.height,a.duration_seconds,a.resolution,a.source_page,a.source_item_index FROM assets a LEFT JOIN folders primary_folder ON primary_folder.folder_id=a.folder_id WHERE a.prompt_sha256 IN ({marks}) ORDER BY a.prompt_sha256,a.asset_id",
            batch,
        ):
            record = records[row["prompt_sha256"]]
            asset = dict(row)
            record["assets"].append(asset)
            if asset["folder_id"]:
                record["folders"][asset["folder_id"]] = {"folder_id": asset["folder_id"], "parent_id": None, "name": asset["primary_folder_name"] or "<unknown>", "path": asset["primary_folder_path"], "depth": None}
        asset_ids = [asset["asset_id"] for record in (records[sha] for sha in batch if sha in records) for asset in record["assets"]]
        if not asset_ids:
            continue
        asset_marks = placeholders(asset_ids)
        for row in connection.execute(
            f"SELECT m.asset_id,m.folder_id,f.parent_id,f.name,f.path,f.depth,m.first_seen_page,a.prompt_sha256 FROM asset_folder_memberships m JOIN assets a ON a.asset_id=m.asset_id LEFT JOIN folders f ON f.folder_id=m.folder_id WHERE m.asset_id IN ({asset_marks}) ORDER BY a.prompt_sha256,m.asset_id,m.folder_id",
            asset_ids,
        ):
            records[row["prompt_sha256"]]["memberships"].append(dict(row))
            records[row["prompt_sha256"]]["folders"][row["folder_id"]] = {"folder_id": row["folder_id"], "parent_id": row["parent_id"], "name": row["name"] or "<unknown>", "path": row["path"], "depth": row["depth"]}
        for row in connection.execute(
            f"SELECT o.page_number,o.item_index,o.asset_id,o.item_type,o.parse_status,a.prompt_sha256 FROM item_occurrences o JOIN assets a ON a.asset_id=o.asset_id WHERE o.asset_id IN ({asset_marks}) ORDER BY a.prompt_sha256,o.page_number,o.item_index",
            asset_ids,
        ):
            records[row["prompt_sha256"]]["occurrences"].append(dict(row))
        for row in connection.execute(
            f"SELECT i.issue_id,i.page_number,i.item_index,i.asset_id,i.severity,i.code,i.details_json,a.prompt_sha256 FROM issues i JOIN assets a ON a.asset_id=i.asset_id WHERE i.asset_id IN ({asset_marks}) ORDER BY a.prompt_sha256,i.issue_id",
            asset_ids,
        ):
            records[row["prompt_sha256"]]["issues"].append(dict(row))
    missing = [prompt_hash for prompt_hash in hashes if prompt_hash not in records]
    if missing:
        raise ValueError(f"Unknown prompt SHA-256: {', '.join(missing)}")
    return records


def source_record_digest(record: dict[str, Any]) -> str:
    payload = {
        "prompt_sha256": record["prompt_sha256"],
        "prompt_text": record["prompt_text"],
        "source_prompt_chars": record["source_prompt_chars"],
        "analysis_prompt_chars": record["analysis_prompt_chars"],
        "url_redaction_count": record["url_redaction_count"],
        "first_asset_id": record["first_asset_id"],
        "assets": sorted(record["assets"], key=lambda row: row["asset_id"]),
        "memberships": sorted(record["memberships"], key=lambda row: (row["asset_id"], row["folder_id"])),
        "occurrences": sorted(record["occurrences"], key=lambda row: (row["page_number"], row["item_index"])),
        "issues": sorted(record["issues"], key=lambda row: row["issue_id"]),
        "folders": sorted(record["folders"].values(), key=lambda row: row["folder_id"]),
    }
    return sha256_text(canonical_json(payload))


def video_universe(connection: sqlite3.Connection) -> tuple[int, int]:
    count = connection.execute("SELECT count(*) FROM prompts p WHERE EXISTS (SELECT 1 FROM assets a WHERE a.prompt_sha256=p.prompt_sha256 AND a.asset_type='video')").fetchone()[0]
    empty_video_assets = connection.execute("SELECT count(*) FROM assets WHERE asset_type='video' AND prompt_sha256 IS NULL").fetchone()[0]
    return int(count), int(empty_video_assets)


def target_connection(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.executescript(TARGET_SCHEMA)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def clear_prompt(target: sqlite3.Connection, prompt_hash: str) -> None:
    for table in ("processing_issues", "extracted_facts", "prompt_structure", "source_issues", "source_occurrences", "source_asset_folders", "source_assets"):
        target.execute(f"DELETE FROM {table} WHERE prompt_sha256=?", (prompt_hash,))


def insert_source_record(target: sqlite3.Connection, record: dict[str, Any], input_digest: str) -> None:
    prompt_hash = record["prompt_sha256"]
    target.execute(
        "INSERT INTO source_prompts(prompt_sha256,source_prompt_chars,analysis_prompt_chars,url_redaction_count,first_asset_id,source_locator,source_input_sha256,extractor_version,extractor_config_sha256,processing_status,content_digest,failure_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(prompt_sha256) DO UPDATE SET source_prompt_chars=excluded.source_prompt_chars,analysis_prompt_chars=excluded.analysis_prompt_chars,url_redaction_count=excluded.url_redaction_count,first_asset_id=excluded.first_asset_id,source_locator=excluded.source_locator,source_input_sha256=excluded.source_input_sha256,extractor_version=excluded.extractor_version,extractor_config_sha256=excluded.extractor_config_sha256,processing_status=excluded.processing_status,content_digest=excluded.content_digest,failure_code=excluded.failure_code",
        (prompt_hash, record["source_prompt_chars"], record["analysis_prompt_chars"], record["url_redaction_count"], record["first_asset_id"], f"sqlite:prompts/{prompt_hash}", input_digest, EXTRACTOR_VERSION, CONFIG_SHA256, "pending", None, None),
    )
    for folder in record["folders"].values():
        target.execute("INSERT INTO source_folders(folder_id,parent_id,name,path,depth) VALUES (?,?,?,?,?) ON CONFLICT(folder_id) DO UPDATE SET parent_id=excluded.parent_id,name=excluded.name,path=excluded.path,depth=excluded.depth", (folder["folder_id"], folder["parent_id"], folder["name"], folder["path"], folder["depth"] if folder["depth"] is not None else -1))
    for asset in record["assets"]:
        target.execute("INSERT INTO source_assets(asset_id,prompt_sha256,primary_folder_id,primary_folder_name,primary_folder_path,item_type,asset_type,status,job_set_type,model,created_at_unix,width,height,duration_seconds,resolution,source_page,source_item_index) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(asset.get(key) for key in ("asset_id", "prompt_sha256", "folder_id", "primary_folder_name", "primary_folder_path", "item_type", "asset_type", "status", "job_set_type", "model", "created_at_unix", "width", "height", "duration_seconds", "resolution", "source_page", "source_item_index")))
    for membership in record["memberships"]:
        folder = record["folders"][membership["folder_id"]]
        target.execute("INSERT INTO source_asset_folders(prompt_sha256,asset_id,folder_id,folder_name,folder_path,first_seen_page) VALUES (?,?,?,?,?,?)", (prompt_hash, membership["asset_id"], membership["folder_id"], folder["name"], folder["path"], membership["first_seen_page"]))
    for occurrence in record["occurrences"]:
        target.execute("INSERT INTO source_occurrences(prompt_sha256,page_number,item_index,asset_id,item_type,parse_status) VALUES (?,?,?,?,?,?)", (prompt_hash, occurrence["page_number"], occurrence["item_index"], occurrence["asset_id"], occurrence["item_type"], occurrence["parse_status"]))
    for issue in record["issues"]:
        target.execute("INSERT INTO source_issues(source_issue_id,prompt_sha256,page_number,item_index,asset_id,severity,code,details_json) VALUES (?,?,?,?,?,?,?,?)", (issue["issue_id"], prompt_hash, issue["page_number"], issue["item_index"], issue["asset_id"], issue["severity"], issue["code"], issue["details_json"]))


def insert_extraction(target: sqlite3.Connection, prompt_hash: str, extraction: dict[str, Any]) -> None:
    for ordinal, fact in enumerate(extraction["facts"]):
        ev = fact["evidence"]
        target.execute("INSERT INTO extracted_facts(prompt_sha256,ordinal,fact_kind,fact_subtype,value_json,evidence_start,evidence_end,evidence_sha256,evidence_preview,rule_id,confidence,parse_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (prompt_hash, ordinal, fact["fact_kind"], fact["fact_subtype"], canonical_json(fact["value"]), ev["start"], ev["end"], ev["sha256"], ev["preview"], fact["rule_id"], fact["confidence"], fact["parse_status"]))
    for ordinal, issue in enumerate(extraction["issues"]):
        target.execute("INSERT INTO processing_issues(prompt_sha256,ordinal,severity,code,evidence_start,evidence_end,details_json) VALUES (?,?,?,?,?,?,?)", (prompt_hash, ordinal, issue["severity"], issue["code"], issue["start"], issue["end"], canonical_json(issue["details"])))
    structure = extraction["structure"]
    target.execute("INSERT INTO prompt_structure(prompt_sha256,declared_duration_values_json,metadata_duration_values_json,declared_aspect_ratios_json,generation_modes_json,take_structure,heading_count,shot_marker_count,cut_marker_count,timestamp_count,dialogue_evidence_count,dialogue_utterance_count,reference_tag_count,reference_label_count,reference_block_count,audio_signal_count,processing_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (prompt_hash, canonical_json(structure["declared_duration_values"]), canonical_json(structure["metadata_duration_values"]), canonical_json(structure["declared_aspect_ratios"]), canonical_json(structure["generation_modes"]), structure["take_structure"], structure["heading_count"], structure["shot_marker_count"], structure["cut_marker_count"], structure["timestamp_count"], structure["dialogue_evidence_count"], structure["dialogue_utterance_count"], structure["reference_tag_count"], structure["reference_label_count"], structure["reference_block_count"], structure["audio_signal_count"], structure["processing_status"]))
    target.execute("UPDATE source_prompts SET processing_status=?,content_digest=?,failure_code=NULL WHERE prompt_sha256=?", (structure["processing_status"], extraction["content_digest"], prompt_hash))


def mark_failure(target: sqlite3.Connection, record: dict[str, Any], input_digest: str, error: BaseException) -> None:
    prompt_hash = record["prompt_sha256"]
    clear_prompt(target, prompt_hash)
    target.execute("INSERT INTO source_prompts(prompt_sha256,source_prompt_chars,analysis_prompt_chars,url_redaction_count,first_asset_id,source_locator,source_input_sha256,extractor_version,extractor_config_sha256,processing_status,content_digest,failure_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(prompt_sha256) DO UPDATE SET source_prompt_chars=excluded.source_prompt_chars,analysis_prompt_chars=excluded.analysis_prompt_chars,url_redaction_count=excluded.url_redaction_count,first_asset_id=excluded.first_asset_id,source_locator=excluded.source_locator,source_input_sha256=excluded.source_input_sha256,extractor_version=excluded.extractor_version,extractor_config_sha256=excluded.extractor_config_sha256,processing_status=excluded.processing_status,content_digest=NULL,failure_code=excluded.failure_code", (prompt_hash, record["source_prompt_chars"], record["analysis_prompt_chars"], record["url_redaction_count"], record["first_asset_id"], f"sqlite:prompts/{prompt_hash}", input_digest, EXTRACTOR_VERSION, CONFIG_SHA256, "failed", None, type(error).__name__))
    target.execute("INSERT INTO processing_issues(prompt_sha256,ordinal,severity,code,evidence_start,evidence_end,details_json) VALUES (?,?,?,?,?,?,?)", (prompt_hash, 0, "error", "parser_exception", None, None, canonical_json({"exception_type": type(error).__name__})))


def should_skip(target: sqlite3.Connection, record: dict[str, Any], input_digest: str) -> bool:
    row = target.execute("SELECT source_input_sha256,extractor_version,extractor_config_sha256,processing_status FROM source_prompts WHERE prompt_sha256=?", (record["prompt_sha256"],)).fetchone()
    return bool(row and row["source_input_sha256"] == input_digest and row["extractor_version"] == EXTRACTOR_VERSION and row["extractor_config_sha256"] == CONFIG_SHA256 and row["processing_status"] in {"completed", "completed_with_issues"} and target.execute("SELECT 1 FROM prompt_structure WHERE prompt_sha256=?", (record["prompt_sha256"],)).fetchone())


def logical_target_digest(target: sqlite3.Connection) -> str:
    tables = [row[0] for row in target.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    payload: list[Any] = []
    for table in tables:
        columns = [row[1] for row in target.execute(f"PRAGMA table_info({table})")]
        pk_columns = [row[1] for row in target.execute(f"PRAGMA table_info({table})") if row[5]]
        order = ",".join(pk_columns or columns)
        rows = [list(row) for row in target.execute(f"SELECT {','.join(columns)} FROM {table} ORDER BY {order}")]
        payload.append({"table": table, "columns": columns, "rows": rows})
    return sha256_text(canonical_json(payload))


def validate_target(target: sqlite3.Connection, records: dict[str, dict[str, Any]], prompt_hashes: Sequence[str]) -> dict[str, Any]:
    integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = target.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()[0]
    evidence_errors: list[str] = []
    for prompt_hash in prompt_hashes:
        record = records[prompt_hash]
        fact_rows = target.execute("SELECT ordinal,fact_kind,value_json,evidence_start,evidence_end,evidence_sha256 FROM extracted_facts WHERE prompt_sha256=? ORDER BY ordinal", (prompt_hash,)).fetchall()
        for row in fact_rows:
            if not 0 <= row["evidence_start"] < row["evidence_end"] <= len(record["prompt_text"]):
                evidence_errors.append(f"{prompt_hash}:{row['ordinal']}:range")
            elif sha256_text(record["prompt_text"][row["evidence_start"] : row["evidence_end"]]) != row["evidence_sha256"]:
                evidence_errors.append(f"{prompt_hash}:{row['ordinal']}:hash")
        structure = target.execute("SELECT * FROM prompt_structure WHERE prompt_sha256=?", (prompt_hash,)).fetchone()
        status = target.execute("SELECT processing_status FROM source_prompts WHERE prompt_sha256=?", (prompt_hash,)).fetchone()[0]
        if status in {"completed", "completed_with_issues"} and structure is None:
            evidence_errors.append(f"{prompt_hash}:missing_structure")
            continue
        if status not in {"completed", "completed_with_issues"}:
            continue
        expected_counts = {
            "heading_count": sum(row["fact_kind"] == "heading" for row in fact_rows),
            "shot_marker_count": sum(row["fact_kind"] == "shot_marker" for row in fact_rows),
            "cut_marker_count": sum(row["fact_kind"] == "cut_marker" for row in fact_rows),
            "timestamp_count": sum(row["fact_kind"] == "timestamp" for row in fact_rows),
            "dialogue_evidence_count": sum(row["fact_kind"] == "dialogue" for row in fact_rows),
            "reference_tag_count": sum(row["fact_kind"] == "reference_tag" for row in fact_rows),
            "reference_block_count": sum(row["fact_kind"] == "reference_block" for row in fact_rows),
            "audio_signal_count": sum(row["fact_kind"] == "audio" for row in fact_rows),
        }
        for column, expected in expected_counts.items():
            if structure[column] != expected:
                evidence_errors.append(f"{prompt_hash}:{column}:{structure[column]}!={expected}")
        if target.execute("SELECT count(*) FROM source_assets WHERE prompt_sha256=?", (prompt_hash,)).fetchone()[0] != len(record["assets"]):
            evidence_errors.append(f"{prompt_hash}:asset_mapping_count")
        if target.execute("SELECT count(*) FROM source_asset_folders WHERE prompt_sha256=?", (prompt_hash,)).fetchone()[0] != len(record["memberships"]):
            evidence_errors.append(f"{prompt_hash}:membership_mapping_count")
        if target.execute("SELECT count(*) FROM source_occurrences WHERE prompt_sha256=?", (prompt_hash,)).fetchone()[0] != len(record["occurrences"]):
            evidence_errors.append(f"{prompt_hash}:occurrence_mapping_count")
        if not any(asset.get("asset_type") == "video" for asset in record["assets"]):
            evidence_errors.append(f"{prompt_hash}:not_video_related")
        if record["analysis_prompt_chars"] != len(record["prompt_text"]):
            evidence_errors.append(f"{prompt_hash}:analysis_length")
        if not record["url_redaction_count"] and sha256_text(record["prompt_text"]) != prompt_hash:
            evidence_errors.append(f"{prompt_hash}:prompt_hash")
    return {"integrity_check": integrity, "foreign_key_error_count": int(foreign_keys), "evidence_error_count": len(evidence_errors), "evidence_errors": evidence_errors[:20], "passed": integrity == "ok" and foreign_keys == 0 and not evidence_errors}


def select_sample_hashes(connection: sqlite3.Connection, explicit: Sequence[str] | None, all_video_prompts: bool = False) -> tuple[list[str], dict[str, list[str]]]:
    if explicit and all_video_prompts:
        raise ValueError("--all-video-prompts cannot be combined with --prompt-sha256")
    if explicit:
        hashes = sorted(set(explicit))
        reasons = {prompt_hash: ["explicit_cli"] for prompt_hash in hashes}
    elif all_video_prompts:
        hashes = [
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT p.prompt_sha256 FROM prompts p JOIN assets a ON a.prompt_sha256=p.prompt_sha256 WHERE a.asset_type='video' ORDER BY p.prompt_sha256"
            )
        ]
        reasons = {prompt_hash: ["full-video-universe"] for prompt_hash in hashes}
    else:
        hashes = sorted(REGRESSION_SAMPLE_HASHES)
        reasons = {prompt_hash: [reason] for prompt_hash, reason in REGRESSION_SAMPLE_HASHES.items()}
    if all_video_prompts:
        found = set(hashes)
    else:
        marks = placeholders(hashes)
        rows = connection.execute(f"SELECT DISTINCT p.prompt_sha256 FROM prompts p JOIN assets a ON a.prompt_sha256=p.prompt_sha256 WHERE a.asset_type='video' AND p.prompt_sha256 IN ({marks}) ORDER BY p.prompt_sha256", hashes).fetchall()
        found = {row[0] for row in rows}
    missing = [prompt_hash for prompt_hash in hashes if prompt_hash not in found]
    if missing:
        raise ValueError(f"selected prompts are not video-related or missing: {', '.join(missing)}")
    return hashes, reasons


def preprocess(
    source_database: Path = DEFAULT_SOURCE_DATABASE,
    run_dir: Path = DEFAULT_RUN_DIR,
    prompt_hashes: Sequence[str] | None = None,
    *,
    extractor: Callable[[str, dict[str, Any]], dict[str, Any]] = extract_prompt,
    batch_name: str = DEFAULT_BATCH_NAME,
    all_video_prompts: bool = False,
) -> dict[str, Any]:
    source_database = source_database.resolve()
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    source_completion = load_source_completion(source_database)
    before_state = source_state(source_database)
    before_snapshot = source_snapshot_sha256(before_state)
    source = connect_source(source_database)
    target_path = run_dir / "preprocessed.sqlite3"
    report_path = run_dir / "report.json"
    manifest_path = run_dir / "manifest.json"
    target: sqlite3.Connection | None = None
    try:
        target = target_connection(target_path)
        universe_count, empty_video_asset_count = video_universe(source)
        hashes, reasons = select_sample_hashes(source, prompt_hashes, all_video_prompts)
        records = load_source_records(source, hashes)
        manifest = {"schema_version": 1, "batch_name": batch_name, "prompt_hashes": hashes, "selection_reasons": reasons}
        manifest_sha = sha256_text(canonical_json(manifest))
        batch_id = manifest_sha[:24]
        assert target is not None
        target.execute("INSERT INTO metadata(key,value_json) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", ("schema_version", canonical_json(1)))
        target.execute("INSERT INTO metadata(key,value_json) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", ("extractor_version", canonical_json(EXTRACTOR_VERSION)))
        target.execute("INSERT INTO metadata(key,value_json) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", ("extractor_config_sha256", canonical_json(CONFIG_SHA256)))
        target.execute("INSERT INTO metadata(key,value_json) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", ("source_snapshot_sha256", canonical_json(before_snapshot)))
        target.execute("INSERT INTO batches(batch_id,batch_name,manifest_sha256,expected_prompt_count,source_snapshot_sha256,status) VALUES (?,?,?,?,?,?) ON CONFLICT(batch_id) DO UPDATE SET source_snapshot_sha256=excluded.source_snapshot_sha256,status=excluded.status", (batch_id, batch_name, manifest_sha, len(hashes), before_snapshot, "running"))
        processed = skipped = failed = 0
        status_counts: dict[str, int] = {}
        for prompt_hash in hashes:
            record = records[prompt_hash]
            input_digest = source_record_digest(record)
            if should_skip(target, record, input_digest):
                skipped += 1
                status = target.execute("SELECT processing_status FROM source_prompts WHERE prompt_sha256=?", (prompt_hash,)).fetchone()[0]
                status_counts[status] = status_counts.get(status, 0) + 1
                continue
            target.execute("BEGIN IMMEDIATE")
            try:
                clear_prompt(target, prompt_hash)
                insert_source_record(target, record, input_digest)
                metadata = {"duration_values": stable_unique(asset.get("duration_seconds") for asset in record["assets"]), "resolution_values": stable_unique(asset.get("resolution") for asset in record["assets"]), "model_values": stable_unique(asset.get("model") for asset in record["assets"]), "url_redaction_count": record["url_redaction_count"]}
                try:
                    extraction = extractor(record["prompt_text"], metadata)
                except Exception as error:
                    target.execute("ROLLBACK")
                    target.execute("BEGIN IMMEDIATE")
                    mark_failure(target, record, input_digest, error)
                    target.execute("COMMIT")
                    failed += 1
                    status_counts["failed"] = status_counts.get("failed", 0) + 1
                    continue
                insert_extraction(target, prompt_hash, extraction)
                target.execute("COMMIT")
                processed += 1
                status = extraction["structure"]["processing_status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            except BaseException:
                if target.in_transaction:
                    target.execute("ROLLBACK")
                raise
        target.execute("BEGIN IMMEDIATE")
        try:
            target.execute("UPDATE batches SET status=? WHERE batch_id=?", ("completed" if failed == 0 else "completed_with_failures", batch_id))
            for ordinal, prompt_hash in enumerate(hashes):
                target.execute("INSERT OR IGNORE INTO batch_prompts(batch_id,ordinal,prompt_sha256) VALUES (?,?,?)", (batch_id, ordinal, prompt_hash))
                for reason in reasons[prompt_hash]:
                    target.execute("INSERT OR IGNORE INTO selection_reasons(batch_id,prompt_sha256,reason) VALUES (?,?,?)", (batch_id, prompt_hash, reason))
            target.execute("COMMIT")
        except BaseException:
            target.execute("ROLLBACK")
            raise
        target_validation = validate_target(target, records, hashes)
        selected_marks = placeholders(hashes)
        fact_kind_counts = {
            row[0]: row[1]
            for row in target.execute(
                f"SELECT fact_kind,count(*) FROM extracted_facts WHERE prompt_sha256 IN ({selected_marks}) GROUP BY fact_kind ORDER BY fact_kind",
                hashes,
            )
        }
        fact_prompt_coverage = {
            row[0]: row[1]
            for row in target.execute(
                f"SELECT fact_kind,count(DISTINCT prompt_sha256) FROM extracted_facts WHERE prompt_sha256 IN ({selected_marks}) GROUP BY fact_kind ORDER BY fact_kind",
                hashes,
            )
        }
        processing_issue_code_counts = {
            row[0]: row[1]
            for row in target.execute(
                f"SELECT code,count(*) FROM processing_issues WHERE prompt_sha256 IN ({selected_marks}) GROUP BY code ORDER BY code",
                hashes,
            )
        }
        logical_digest = logical_target_digest(target)
        target.close()
        source.rollback()
        source.close()
        after_state = source_state(source_database)
        source_unchanged = before_snapshot == source_snapshot_sha256(after_state)
        universe_check = prompt_hashes is not None or universe_count == 6555
        report = {
            "schema_version": 1,
            "status": "pass" if failed == 0 and target_validation["passed"] and source_unchanged and universe_check else "fail",
            "batch_id": batch_id,
            "batch_name": batch_name,
            "manifest_sha256": manifest_sha,
            "source_database": str(source_database),
            "target_database": str(target_path),
            "source_snapshot_sha256": before_snapshot,
            "source_completion": source_completion,
            "source_state_unchanged": source_unchanged,
            "source_file_state_before": before_state,
            "source_file_state_after": after_state,
            "video_unique_prompt_count": universe_count,
            "excluded_empty_video_asset_count": empty_video_asset_count,
            "selected_prompt_count": len(hashes),
            "selected_asset_count": sum(len(record["assets"]) for record in records.values()),
            "selected_occurrence_count": sum(len(record["occurrences"]) for record in records.values()),
            "selected_membership_count": sum(len(record["memberships"]) for record in records.values()),
            "processed": processed,
            "skipped": skipped,
            "failed": failed,
            "processing_status_counts": status_counts,
            "fact_kind_counts": fact_kind_counts,
            "fact_prompt_coverage": fact_prompt_coverage,
            "processing_issue_code_counts": processing_issue_code_counts,
            "logical_target_digest": logical_digest,
            "checks": {"video_universe_expected": universe_check, "target": target_validation, "source_unchanged": source_unchanged},
            "selected_prompts": [{"prompt_sha256": prompt_hash, "reasons": reasons[prompt_hash]} for prompt_hash in hashes],
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
        try:
            source.rollback()
            source.close()
        except Exception:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an auditable, deterministic Stage 4B-1 Prompt structure sample.")
    parser.add_argument("--source-database", type=Path, default=DEFAULT_SOURCE_DATABASE)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--prompt-sha256", action="append", dest="prompt_hashes", help="Process only the explicitly listed Prompt hashes.")
    selection.add_argument("--all-video-prompts", action="store_true", help="Process the complete video-related Prompt universe.")
    parser.add_argument("--batch-name", default=DEFAULT_BATCH_NAME)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = preprocess(args.source_database, args.run_dir, args.prompt_hashes, batch_name=args.batch_name, all_video_prompts=args.all_video_prompts)
    except Exception as error:
        print(json.dumps({"status": "fail", "error": type(error).__name__, "details": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({key: report[key] for key in ("status", "selected_prompt_count", "processed", "skipped", "failed", "source_state_unchanged", "logical_target_digest")}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


CONFIG_SHA256 = sha256_text(canonical_json({"extractor_version": EXTRACTOR_VERSION, "coordinate_system": "python_unicode_codepoint_half_open", "regex_rules": "v1"}))


if __name__ == "__main__":
    raise SystemExit(main())
