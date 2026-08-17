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

from preprocess_video_prompt_sample import extract_prompt, preprocess, select_sample_hashes, source_snapshot_sha256


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


class PreprocessVideoPromptSampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.source = root / "source.sqlite3"
        self.run_dir = root / "run"
        connection = sqlite3.connect(self.source)
        connection.executescript(SOURCE_SCHEMA)
        folders = [
            ("f1", None, "Scene Dialogue", "/Scene Dialogue", 1),
            ("f2", None, "Scene Action", "/Scene Action", 1),
            ("f3", None, "Scene Environment", "/Scene Environment", 1),
            ("f4", None, "Alternate", "/Alternate", 1),
        ]
        connection.executemany(
            "INSERT INTO folders VALUES (?, ?, ?, ?, ?, 0, 0)", folders
        )
        self.prompts = {
            "dialogue": (
                "JAX LOOKBACK\nAspect: 16:9. Duration: 4s. Mode: R2V.\n"
                "SHOT — close-up. REFERENCES:\n<<<image_1>>> - character Jax.\n"
                "DIALOGUE: Jax says: \"Are you kidding me?\"\n"
                "AUDIO (SFX only, no music): breath and voice."
            ),
            "action": (
                "CUT 1 — the fighter dodges a sword impact. CUT 2 — follow-through.\n"
                "Photoreal. NON-IP. 16:9. 10s. SFX only. NO CGI. Cinematic."
            ),
            "environment": (
                "2.39:1 cinemascope. SINGLE CONTINUOUS SHOT. No cuts.\n"
                "A fixed aerial city environment holds rain, traffic and a train."
            ),
            "short": "connect these two clips",
            "mixed": "Duration: 10s. CUT — image and video reference."
        }
        self.hashes = {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in self.prompts.items()}
        for name, text in self.prompts.items():
            prompt_hash = self.hashes[name]
            first_asset = f"{name}-asset-1"
            connection.execute(
                "INSERT INTO prompts VALUES (?, ?, ?, ?, 0, ?)",
                (prompt_hash, text, len(text), len(text), first_asset),
            )
        assets = [
            ("dialogue-asset-1", "f1", "video", "seedance_2_0", 4.0, self.hashes["dialogue"], 1, 0),
            ("dialogue-asset-2", "f1", "video", "seedance_2_0", 4.0, self.hashes["dialogue"], 1, 1),
            ("action-asset-1", "f2", "video", "seedance_2_0", 15.0, self.hashes["action"], 2, 0),
            ("environment-asset-1", "f3", "video", "seedance_2_0", 10.0, self.hashes["environment"], 3, 0),
            ("short-asset-1", "f2", "video", "seedance_2_0", 15.0, self.hashes["short"], 4, 0),
            ("mixed-image", "f3", "image", None, None, self.hashes["mixed"], 5, 0),
            ("mixed-video", "f3", "video", None, 10.0, self.hashes["mixed"], 5, 1),
        ]
        for asset_id, folder_id, asset_type, model, duration, prompt_hash, page, index in assets:
            connection.execute(
                "INSERT INTO assets VALUES (?, ?, 'job', ?, 'completed', 'seedance_2_0', ?, NULL, 1920, 1080, ?, '1080p', ?, ?, ?, 'fixture')",
                (asset_id, folder_id, asset_type, model, duration, prompt_hash, page, index),
            )
            connection.execute(
                "INSERT INTO asset_folder_memberships VALUES (?, ?, ?)",
                (asset_id, folder_id, page),
            )
            connection.execute(
                "INSERT INTO item_occurrences VALUES (?, ?, ?, 'job', 'parsed')",
                (page, index, asset_id),
            )
        connection.execute(
            "INSERT INTO asset_folder_memberships VALUES (?, ?, ?)",
            ("mixed-video", "f4", 6),
        )
        connection.execute(
            "INSERT INTO issues VALUES (1, 5, 1, 'mixed-video', 'warning', 'fixture_warning', '{}')"
        )
        connection.commit()
        connection.close()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_extracts_evidence_and_conflicts_without_frequency_effect(self) -> None:
        text = self.prompts["dialogue"]
        one = extract_prompt(text, {"duration_values": [4.0], "url_redaction_count": 0})
        repeated = extract_prompt(text, {"duration_values": [4.0, 4.0], "url_redaction_count": 0})
        self.assertEqual(one["facts"], repeated["facts"])
        self.assertEqual(one["structure"], repeated["structure"])
        self.assertEqual(one["structure"]["declared_duration_values"], [4])
        dialogue = [fact for fact in one["facts"] if fact["fact_kind"] == "dialogue"]
        self.assertEqual(len(dialogue), 1)
        evidence = dialogue[0]["evidence"]
        self.assertEqual(text[evidence["start"] : evidence["end"]], '"Are you kidding me?"')

    def test_parser_avoids_common_numeric_false_positives(self) -> None:
        result = extract_prompt(
            'Color 60:30:10. 3/4 angle. 350cm. T2.8. At ~1.2s. 60fps. 1920-1080. 24-70mm. Title: "The Arena".',
            {"duration_values": [], "url_redaction_count": 0},
        )
        self.assertEqual(result["structure"]["declared_duration_values"], [])
        self.assertEqual(result["structure"]["declared_aspect_ratios"], [])
        self.assertEqual(result["structure"]["dialogue_utterance_count"], 0)
        self.assertEqual(result["structure"]["timestamp_count"], 1)

    def test_parses_complete_json_settings_with_source_spans(self) -> None:
        text = '{"model":"seedance_2_0","duration":8,"aspect_ratio":"16:9"}'
        result = extract_prompt(
            text,
            {"duration_values": [8.0], "url_redaction_count": 0},
        )
        self.assertEqual(result["structure"]["declared_duration_values"], [8])
        self.assertEqual(result["structure"]["declared_aspect_ratios"], ["16:9"])
        model_facts = [fact for fact in result["facts"] if fact["fact_kind"] == "declared_model"]
        self.assertEqual(len(model_facts), 1)
        span = model_facts[0]["evidence"]
        self.assertEqual(text[span["start"] : span["end"]], '"model":"seedance_2_0"')

    def test_source_snapshot_ignores_mtime_but_detects_content_changes(self) -> None:
        before = {
            "files": [
                {"path": "source.sqlite3", "exists": True, "size": 3, "mtime_ns": 1, "sha256": "abc"}
            ]
        }
        mtime_only = {
            "files": [
                {"path": "source.sqlite3", "exists": True, "size": 3, "mtime_ns": 2, "sha256": "abc"}
            ]
        }
        different_size = {
            "files": [
                {"path": "source.sqlite3", "exists": True, "size": 4, "mtime_ns": 2, "sha256": "abc"}
            ]
        }
        different_hash = {
            "files": [
                {"path": "source.sqlite3", "exists": True, "size": 3, "mtime_ns": 2, "sha256": "def"}
            ]
        }

        self.assertEqual(source_snapshot_sha256(before), source_snapshot_sha256(mtime_only))
        self.assertNotEqual(source_snapshot_sha256(before), source_snapshot_sha256(different_size))
        self.assertNotEqual(source_snapshot_sha256(before), source_snapshot_sha256(different_hash))

    def test_all_video_selection_is_deterministic_and_excludes_no_video_prompts(self) -> None:
        connection = sqlite3.connect(f"file:{self.source}?mode=ro", uri=True)
        try:
            hashes, reasons = select_sample_hashes(connection, None, all_video_prompts=True)
        finally:
            connection.close()

        self.assertEqual(hashes, sorted(self.hashes.values()))
        self.assertEqual(set(reasons), set(hashes))
        self.assertTrue(all(reason == ["full-video-universe"] for reason in reasons.values()))

    def test_all_video_selection_cannot_be_combined_with_explicit_hashes(self) -> None:
        connection = sqlite3.connect(f"file:{self.source}?mode=ro", uri=True)
        try:
            with self.assertRaisesRegex(ValueError, "cannot be combined"):
                select_sample_hashes(connection, [self.hashes["dialogue"]], all_video_prompts=True)
        finally:
            connection.close()

    def test_realistic_batch_is_auditable_and_idempotent(self) -> None:
        hashes = [self.hashes[name] for name in ("dialogue", "action", "environment", "short", "mixed")]
        first = preprocess(self.source, self.run_dir, hashes)
        self.assertEqual(first["status"], "pass")
        self.assertEqual(first["processed"], 5)
        self.assertEqual(first["skipped"], 0)
        self.assertTrue(first["source_state_unchanged"])

        second = preprocess(self.source, self.run_dir, hashes)
        self.assertEqual(second["status"], "pass")
        self.assertEqual(second["processed"], 0)
        self.assertEqual(second["skipped"], 5)
        self.assertEqual(first["logical_target_digest"], second["logical_target_digest"])

        target = sqlite3.connect(self.run_dir / "preprocessed.sqlite3")
        target.row_factory = sqlite3.Row
        self.assertNotIn("prompt_text", {row[1] for row in target.execute("PRAGMA table_info(source_prompts)")})
        self.assertEqual(target.execute("SELECT count(*) FROM source_assets").fetchone()[0], 7)
        self.assertEqual(target.execute("SELECT count(*) FROM source_asset_folders").fetchone()[0], 8)
        self.assertEqual(target.execute("SELECT count(*) FROM source_issues").fetchone()[0], 1)
        action_structure = target.execute(
            "SELECT declared_duration_values_json,metadata_duration_values_json FROM prompt_structure WHERE prompt_sha256=?",
            (self.hashes["action"],),
        ).fetchone()
        self.assertEqual(json.loads(action_structure[0]), [10])
        self.assertEqual(json.loads(action_structure[1]), [15])
        self.assertEqual(
            target.execute(
                "SELECT cut_marker_count FROM prompt_structure WHERE prompt_sha256=?",
                (self.hashes["action"],),
            ).fetchone()[0],
            2,
        )
        target.close()

    def test_parser_failure_is_explicit_and_leaves_no_partial_facts(self) -> None:
        def fail(_text: str, _metadata: dict[str, object]) -> dict[str, object]:
            raise RuntimeError("injected")

        prompt_hash = self.hashes["short"]
        report = preprocess(self.source, self.run_dir, [prompt_hash], extractor=fail)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["failed"], 1)
        target = sqlite3.connect(self.run_dir / "preprocessed.sqlite3")
        self.assertEqual(target.execute("SELECT count(*) FROM extracted_facts").fetchone()[0], 0)
        self.assertEqual(target.execute("SELECT count(*) FROM prompt_structure").fetchone()[0], 0)
        self.assertEqual(target.execute("SELECT code FROM processing_issues").fetchone()[0], "parser_exception")
        target.close()


if __name__ == "__main__":
    unittest.main()
