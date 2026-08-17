from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from audit_stage4b_semantic_normalization import (  # noqa: E402
    check_evidence,
    direct_field_values,
    sample_hashes,
)
from normalize_video_prompt_semantics import sha256_text  # noqa: E402


class AuditStage4BSemanticNormalizationTests(unittest.TestCase):
    def test_sampling_is_deterministic_and_includes_all_manual_records(self) -> None:
        hashes = [sha256_text(f"prompt-{index}") for index in range(24)]
        normalizations = {
            prompt_hash: {
                "normalization_status": "needs_manual_review" if index == 23 else "normalized",
                "complexity_queue": ("simple", "standard", "complex")[index % 3],
            }
            for index, prompt_hash in enumerate(hashes)
        }
        strata = {
            prompt_hash: {
                "complexity_queue": normalizations[prompt_hash]["complexity_queue"],
                "scene_tags_json": '["environment_establishing"]',
                "text_length_band": "long",
                "structure_state": "single_take",
                "duration_state": "consistent",
            }
            for prompt_hash in hashes
        }
        data = {"normalizations": normalizations, "strata": strata}
        first = sample_hashes(data)
        second = sample_hashes(data)
        self.assertEqual(first, second)
        self.assertIn(hashes[-1], first[0])
        self.assertTrue(set(hashes) >= first[0])

    def test_joined_objective_is_checked_as_source_ordered_parts(self) -> None:
        row = {
            "objective_text": "first source segment second source segment",
            "spatial_relations_json": "[]",
            "action_summary_json": '{"beats": []}',
            "performance_dialogue_reaction_json": '{"performance_segments": []}',
            "camera_result_json": '{"segments": []}',
            "lighting_json": '{"segments": []}',
            "sound_json": '{"segments": []}',
            "physics_json": '{"segments": []}',
            "continuity_json": "[]",
            "constraints_json": "[]",
        }
        self.assertEqual(
            direct_field_values(row, "objective"),
            ["first source segment second source segment"],
        )

    def test_issue_reference_without_span_is_valid_audit_evidence(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            CREATE TABLE normalization_evidence (
                prompt_sha256 TEXT, ordinal INTEGER, field_name TEXT, operation TEXT,
                evidence_kind TEXT, fact_kind TEXT, fact_ordinal INTEGER, issue_code TEXT,
                evidence_start INTEGER, evidence_end INTEGER, evidence_sha256 TEXT,
                evidence_preview TEXT
            );
            CREATE TABLE normalization_decisions (
                prompt_sha256 TEXT, ordinal INTEGER, field_name TEXT, operation TEXT,
                rationale TEXT, authority TEXT, evidence_ordinal INTEGER
            );
            """
        )
        prompt_hash = sha256_text("Source text.")
        connection.execute(
            "INSERT INTO normalization_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (prompt_hash, 0, "source_conflicts", "conflict", "issue_ref", None, None, "duration", None, None, None, "metadata"),
        )
        connection.execute(
            "INSERT INTO normalization_decisions VALUES (?,?,?,?,?,?,?)",
            (prompt_hash, 0, "duration", "conflict_choice", "retain", "policy", 0),
        )
        evidence, _, errors = check_evidence(connection, prompt_hash, "Source text.")
        self.assertEqual(len(evidence), 1)
        self.assertEqual(errors, [])
        connection.close()


if __name__ == "__main__":
    unittest.main()
