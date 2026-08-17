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

from preprocess_video_prompt_sample import preprocess
from stratify_video_prompt_complexity import classify_record, duration_state, stratify


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


class StratifyVideoPromptComplexityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.source = root / "source.sqlite3"
        self.preprocessed_run = root / "preprocessed"
        self.strata_run = root / "strata"
        prompts = {
            "action": (
                "Duration: 10s. CUT 1 - the fighter dodges a sword strike. CUT 2 - she punches back. "
                "DIALOGUE: She says: \"Move!\""
            ),
            "environment": "SINGLE CONTINUOUS SHOT. A fixed aerial city environment holds rain and traffic.",
        }
        self.hashes = {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in prompts.items()}
        connection = sqlite3.connect(self.source)
        connection.executescript(SOURCE_SCHEMA)
        connection.execute("INSERT INTO folders VALUES ('f1',NULL,'Scene','/Scene',1,0,0)")
        for name, text in prompts.items():
            prompt_hash = self.hashes[name]
            asset_id = f"{name}-asset"
            connection.execute(
                "INSERT INTO prompts VALUES (?,?,?,?,0,?)",
                (prompt_hash, text, len(text), len(text), asset_id),
            )
            duration = 15.0 if name == "action" else 10.0
            connection.execute(
                "INSERT INTO assets VALUES (?, 'f1', 'job', 'video', 'completed', 'seedance_2_0', 'seedance_2_0', NULL, 1920, 1080, ?, '1080p', ?, 1, ?, 'fixture')",
                (asset_id, duration, prompt_hash, 0 if name == "action" else 1),
            )
            connection.execute("INSERT INTO asset_folder_memberships VALUES (?, 'f1', 1)", (asset_id,))
            connection.execute("INSERT INTO item_occurrences VALUES (1, ?, ?, 'job', 'parsed')", (0 if name == "action" else 1, asset_id))
        connection.commit()
        connection.close()
        preprocess(self.source, self.preprocessed_run, list(self.hashes.values()))
        self.preprocessed = self.preprocessed_run / "preprocessed.sqlite3"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_full_fixture_is_partitioned_once_and_idempotently(self) -> None:
        first = stratify(
            self.source,
            self.preprocessed,
            self.strata_run,
            require_full_universe=False,
        )
        self.assertEqual(first["status"], "pass")
        self.assertEqual(first["processed"], 2)
        self.assertEqual(first["failed"], 0)
        self.assertEqual(sum(first["queue_counts"].values()), 2)

        second = stratify(
            self.source,
            self.preprocessed,
            self.strata_run,
            require_full_universe=False,
        )
        self.assertEqual(second["status"], "pass")
        self.assertEqual(second["processed"], 0)
        self.assertEqual(second["skipped"], 2)
        self.assertEqual(first["logical_target_digest"], second["logical_target_digest"])

        target = sqlite3.connect(self.strata_run / "stratification.sqlite3")
        target.row_factory = sqlite3.Row
        self.assertEqual(target.execute("SELECT count(*) FROM prompt_strata").fetchone()[0], 2)
        self.assertEqual(target.execute("SELECT count(DISTINCT prompt_sha256) FROM prompt_strata").fetchone()[0], 2)
        self.assertNotIn("prompt_text", {row[1] for row in target.execute("PRAGMA table_info(prompt_strata)")})
        action = target.execute("SELECT * FROM prompt_strata WHERE prompt_sha256=?", (self.hashes["action"],)).fetchone()
        self.assertEqual(action["complexity_queue"], "complex")
        self.assertIn("action_interaction", json.loads(action["scene_tags_json"]))
        self.assertFalse({"asset_count", "occurrence_count", "membership_count", "generation_count"} & set(json.loads(action["features_json"])))
        target.close()

    def test_classifier_uses_multiple_scene_tags_without_quality_score(self) -> None:
        text = "A fighter punches in a rainy city street while her partner reacts and shouts."
        structure = {
            "take_structure": "multi",
            "processing_status": "completed",
            "dialogue_evidence_count": 1,
            "dialogue_utterance_count": 1,
            "shot_marker_count": 3,
            "cut_marker_count": 2,
            "timestamp_count": 0,
            "reference_tag_count": 0,
            "reference_block_count": 0,
            "declared_duration_values_json": "[]",
            "metadata_duration_values_json": "[10]",
        }
        result = classify_record(
            {
                "prompt_text": text,
                "source_prompt_chars": len(text),
                "structure": structure,
                "facts": [],
                "issues": [],
            }
        )
        self.assertEqual(
            result["scene_tags"],
            ["action_interaction", "character_performance", "environment_establishing", "mixed_scene"],
        )
        self.assertNotIn("quality_score", result)
        self.assertIn(result["complexity_queue"], {"simple", "standard", "complex", "manual_review"})

    def test_null_asset_duration_is_flagged_but_not_compared_as_a_number(self) -> None:
        structure = {
            "take_structure": "single",
            "processing_status": "completed",
            "dialogue_evidence_count": 0,
            "dialogue_utterance_count": 0,
            "shot_marker_count": 0,
            "cut_marker_count": 0,
            "timestamp_count": 0,
            "reference_tag_count": 0,
            "reference_block_count": 0,
            "declared_duration_values_json": "[10]",
            "metadata_duration_values_json": "[10, null]",
        }
        self.assertEqual(duration_state(structure), "consistent")
        result = classify_record(
            {
                "prompt_text": "A single shot holds on the room.",
                "source_prompt_chars": 32,
                "structure": structure,
                "facts": [],
                "issues": [],
            }
        )
        self.assertIn("missing_asset_duration", result["risk_flags"])

    def test_damaged_source_text_is_reserved_for_manual_review(self) -> None:
        text = "\ufffd damaged source text"
        structure = {
            "take_structure": "not_declared",
            "processing_status": "completed_with_issues",
            "dialogue_evidence_count": 0,
            "dialogue_utterance_count": 0,
            "shot_marker_count": 0,
            "cut_marker_count": 0,
            "timestamp_count": 0,
            "reference_tag_count": 0,
            "reference_block_count": 0,
            "declared_duration_values_json": "[]",
            "metadata_duration_values_json": "[]",
        }
        result = classify_record(
            {
                "prompt_text": text,
                "source_prompt_chars": len(text),
                "structure": structure,
                "facts": [],
                "issues": [
                    {
                        "ordinal": 0,
                        "code": "unicode_replacement_character",
                        "evidence_start": 0,
                        "evidence_end": 1,
                    }
                ],
            }
        )
        self.assertEqual(result["complexity_queue"], "manual_review")


if __name__ == "__main__":
    unittest.main()
