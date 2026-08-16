from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from export_prompt_sources import export_prompt_records


class ExportPromptSourcesTests(unittest.TestCase):
    def connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(":memory:")
        connection.executescript(
            """
            CREATE TABLE prompts (
                prompt_sha256 TEXT PRIMARY KEY, prompt_text TEXT,
                source_prompt_chars INTEGER, analysis_prompt_chars INTEGER,
                url_redaction_count INTEGER, first_asset_id TEXT
            );
            CREATE TABLE folders (folder_id TEXT PRIMARY KEY, name TEXT);
            CREATE TABLE assets (
                asset_id TEXT PRIMARY KEY, folder_id TEXT, item_type TEXT,
                asset_type TEXT, status TEXT, job_set_type TEXT, model TEXT,
                duration_seconds REAL, width INTEGER, height INTEGER,
                resolution TEXT, source_page INTEGER, source_item_index INTEGER,
                prompt_sha256 TEXT
            );
            CREATE TABLE asset_folder_memberships (
                asset_id TEXT, folder_id TEXT, first_seen_page INTEGER
            );
            """
        )
        connection.execute(
            "INSERT INTO prompts VALUES (?, ?, ?, ?, ?, ?)",
            ("hash", "prompt", 6, 6, 0, "asset"),
        )
        connection.executemany(
            "INSERT INTO folders VALUES (?, ?)",
            (("folder-a", "A"), ("folder-b", "B")),
        )
        connection.execute(
            "INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "asset",
                "folder-a",
                "video",
                "video",
                "completed",
                "seedance_2_0",
                "seedance_2_0",
                10.0,
                1920,
                1080,
                "1080p",
                1,
                0,
                "hash",
            ),
        )
        connection.executemany(
            "INSERT INTO asset_folder_memberships VALUES (?, ?, ?)",
            (("asset", "folder-a", 1), ("asset", "folder-b", 2)),
        )
        return connection

    def test_exports_all_folder_memberships(self) -> None:
        connection = self.connection()

        records = export_prompt_records(connection, ["hash"])

        memberships = records[0]["assets"][0]["folder_memberships"]
        self.assertEqual([row["folder_name"] for row in memberships], ["A", "B"])

    def test_rejects_unknown_prompt_hash(self) -> None:
        connection = self.connection()

        with self.assertRaisesRegex(ValueError, "Unknown prompt SHA-256"):
            export_prompt_records(connection, ["missing"])


if __name__ == "__main__":
    unittest.main()
