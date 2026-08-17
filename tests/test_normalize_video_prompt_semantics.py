from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from normalize_video_prompt_semantics import normalize, normalize_record
from preprocess_video_prompt_sample import preprocess
from stratify_video_prompt_complexity import stratify


SOURCE_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE folders (
    folder_id TEXT PRIMARY KEY, parent_id TEXT, name TEXT NOT NULL,
    path TEXT, depth INTEGER NOT NULL, reported_asset_count INTEGER NOT NULL,
    derived_direct_asset_count INTEGER NOT NULL
);
CREATE TABLE prompts (
    prompt_sha256 TEXT PRIMARY KEY, prompt_text TEXT NOT NULL,
    source_prompt_chars INTEGER NOT NULL, analysis_prompt_chars INTEGER NOT NULL,
    url_redaction_count INTEGER NOT NULL, first_asset_id TEXT NOT NULL
);
CREATE TABLE assets (
    asset_id TEXT PRIMARY KEY, folder_id TEXT, item_type TEXT, asset_type TEXT,
    status TEXT, job_set_type TEXT, model TEXT, created_at_unix REAL,
    width INTEGER, height INTEGER, duration_seconds REAL, resolution TEXT,
    prompt_sha256 TEXT REFERENCES prompts(prompt_sha256), source_page INTEGER NOT NULL,
    source_item_index INTEGER NOT NULL, fetched_at TEXT NOT NULL
);
CREATE TABLE asset_folder_memberships (
    asset_id TEXT NOT NULL REFERENCES assets(asset_id), folder_id TEXT NOT NULL,
    first_seen_page INTEGER NOT NULL, PRIMARY KEY(asset_id, folder_id)
);
CREATE TABLE item_occurrences (
    page_number INTEGER NOT NULL, item_index INTEGER NOT NULL, asset_id TEXT,
    item_type TEXT, parse_status TEXT NOT NULL, PRIMARY KEY(page_number, item_index)
);
CREATE TABLE issues (
    issue_id INTEGER PRIMARY KEY, page_number INTEGER NOT NULL, item_index INTEGER,
    asset_id TEXT, severity TEXT NOT NULL, code TEXT NOT NULL, details_json TEXT NOT NULL
);
CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
"""


def direct_record(text: str, *, video: bool = True, damaged: bool = False, duration_values: tuple[str, str] = ("[4]", "[4.0]")) -> dict:
    prompt_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    ref_start = text.find("<<<image_1>>>")
    line_start = text.find('"Are you kidding me?"')
    facts = []
    if ref_start >= 0:
        facts.append(
            {
                "ordinal": 0,
                "fact_kind": "reference_block",
                "value_json": json.dumps({"label": "<<<image_1>>>", "role_candidate": "character"}),
                "evidence_start": ref_start,
                "evidence_end": len(text),
            }
        )
    if line_start >= 0:
        facts.append(
            {
                "ordinal": len(facts),
                "fact_kind": "dialogue",
                "value_json": json.dumps({"line": "Are you kidding me?", "speaker": "Jax"}),
                "evidence_start": line_start,
                "evidence_end": line_start + len('"Are you kidding me?"'),
            }
        )
    issues = []
    if damaged:
        issues.append({"ordinal": 0, "code": "unicode_replacement_character", "evidence_start": 0, "evidence_end": 1, "details_json": "{}"})
    structure = {
        "processing_status": "completed_with_issues" if damaged else "completed",
        "take_structure": "single",
        "declared_duration_values_json": duration_values[0],
        "metadata_duration_values_json": duration_values[1],
    }
    asset_rows = []
    if video:
        asset_rows.append({"asset_id": "a1", "asset_type": "video", "item_type": "job", "model": "seedance_2_0", "duration_seconds": 4.0, "resolution": "1080p"})
    return {
        "prompt_sha256": prompt_hash,
        "prompt_text": text,
        "source_prompt_chars": len(text),
        "analysis_prompt_chars": len(text),
        "source_prompt": {"source_input_sha256": "source-input", "content_digest": "content-digest"},
        "structure": structure,
        "facts": facts,
        "issues": issues,
        "assets": asset_rows,
        "asset_memberships": [],
        "strata": {
            "complexity_queue": "standard",
            "scene_tags_json": json.dumps(["character_performance"]),
            "risk_flags_json": json.dumps([]),
            "dialogue_state": "detected",
            "duration_state": "conflict" if duration_values[0] != duration_values[1] else "consistent",
        },
    }


class NormalizeVideoPromptSemanticsTests(unittest.TestCase):
    def test_model_syntax_is_removed_and_reference_binding_stays_described_only(self) -> None:
        record = direct_record(
            'SINGLE TAKE. <<<image_1>>> - character Jax stands screen-left and turns toward camera. DIALOGUE: "Are you kidding me?" No music.'
        )
        result = normalize_record(record)
        self.assertEqual(result["normalization_status"], "normalized")
        neutral = json.dumps({key: result[key] for key in ("objective", "subjects", "spatial_relations", "action_summary", "performance_dialogue_reaction", "camera_result", "lighting", "sound", "physics", "continuity", "constraints", "uncertainty")}, ensure_ascii=False)
        self.assertNotIn("<<<", neutral)
        self.assertEqual(result["material_references"][0]["binding_status"], "described_only")
        self.assertFalse(result["transferability"]["seedance"]["final_prompt_generated"])

    def test_duration_conflict_is_preserved_without_a_selection(self) -> None:
        record = direct_record(
            "Duration: 4s. A fighter stands screen-left in a concrete atrium, turns toward the locked camera, and raises a sword under cold daylight while room tone remains quiet.",
            duration_values=("[4]", "[5.0]"),
        )
        result = normalize_record(record)
        self.assertEqual(result["normalization_status"], "normalized")
        self.assertEqual(result["action_summary"]["duration"]["provenance"], "unresolved_conflict")
        self.assertEqual([item["field"] for item in result["source_conflicts"]], ["duration"])
        self.assertIsNone(result["action_summary"]["duration"]["value_seconds"])

    def test_damaged_and_underdefined_records_are_not_presented_as_normalized(self) -> None:
        damaged = direct_record("\ufffd damaged source", damaged=True)
        self.assertEqual(normalize_record(damaged)["normalization_status"], "needs_manual_review")
        short = direct_record("connect two clips")
        self.assertEqual(normalize_record(short)["normalization_status"], "needs_manual_review")

    def test_video_less_record_is_explicitly_excluded(self) -> None:
        record = direct_record("An image reference only.", video=False)
        result = normalize_record(record)
        self.assertEqual(result["normalization_status"], "excluded_with_reason")
        self.assertTrue(result["status_reasons"])

    def test_fixture_pipeline_is_idempotent_and_closes_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.sqlite3"
            preprocessed_dir = root / "preprocessed"
            stratification_dir = root / "stratification"
            normalization_dir = root / "normalization"
            text = 'Duration: 4s. SINGLE TAKE. <<<image_1>>> - character Jax stands screen-left. DIALOGUE: "Are you kidding me?" No music.'
            prompt_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            connection = sqlite3.connect(source)
            connection.executescript(SOURCE_SCHEMA)
            connection.execute("INSERT INTO folders VALUES ('f1',NULL,'Scene','/Scene',1,0,0)")
            connection.execute("INSERT INTO prompts VALUES (?,?,?,?,0,?)", (prompt_hash, text, len(text), len(text), "a1"))
            connection.execute(
                "INSERT INTO assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("a1", "f1", "job", "video", "completed", "seedance_2_0", "seedance_2_0", None, 1920, 1080, 4.0, "1080p", prompt_hash, 1, 0, "fixture"),
            )
            connection.execute("INSERT INTO asset_folder_memberships VALUES ('a1','f1',1)")
            connection.execute("INSERT INTO item_occurrences VALUES (1,0,'a1','job','parsed')")
            connection.commit()
            connection.close()

            preprocess(source, preprocessed_dir, [prompt_hash])
            preprocessed = preprocessed_dir / "preprocessed.sqlite3"
            stratify(source, preprocessed, stratification_dir, [prompt_hash], require_full_universe=False)
            stratification = stratification_dir / "stratification.sqlite3"
            first = normalize(source, preprocessed, stratification, normalization_dir, [prompt_hash], require_full_universe=False)
            second = normalize(source, preprocessed, stratification, normalization_dir, [prompt_hash], require_full_universe=False)
            self.assertEqual(first["status"], "pass")
            self.assertEqual(first["processed"], 1)
            self.assertEqual(second["status"], "pass")
            self.assertEqual(second["skipped"], 1)
            self.assertEqual(first["logical_target_digest"], second["logical_target_digest"])
            self.assertTrue((normalization_dir / "review-sample.json").is_file())
            target = sqlite3.connect(normalization_dir / "semantic_normalization.sqlite3")
            self.assertEqual(target.execute("SELECT count(*) FROM prompt_normalizations").fetchone()[0], 1)
            self.assertEqual(target.execute("SELECT count(*) FROM normalization_assets").fetchone()[0], 1)
            self.assertNotIn("prompt_text", {row[1] for row in target.execute("PRAGMA table_info(prompt_normalizations)")})
            target.close()


if __name__ == "__main__":
    unittest.main()
