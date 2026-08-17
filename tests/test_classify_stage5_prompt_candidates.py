from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from classify_stage5_prompt_candidates import (  # noqa: E402
    pattern_families,
    rank_candidates,
    score_record,
)


def row(status: str = "normalized", *, asset_count: int = 1) -> dict[str, object]:
    return {
        "normalization_status": status,
        "objective_text": "A person crosses the room and turns toward the camera.",
        "scene_tags_json": '["action_interaction","character_performance"]',
        "subjects_json": '["one person"]',
        "spatial_relations_json": '["screen-left to screen-right","foreground"]',
        "action_summary_json": '{"beats":[{"summary":"crosses","causal_link":"then","source_derivation":"direct"},{"summary":"turns","causal_link":"as","source_derivation":"direct"},{"summary":"holds","causal_link":"while","source_derivation":"direct"}]}',
        "performance_dialogue_reaction_json": '{"performance_segments":["eyes track the camera"],"dialogue_lines":[{"line":"Wait.","speaker":"S1"}],"dialogue_scope":"detected"}',
        "camera_result_json": '{"segments":["locked medium shot","slow pan"]}',
        "lighting_json": '{"segments":["soft window light"]}',
        "sound_json": '{"segments":["footsteps"]}',
        "physics_json": '{"segments":["weight transfers through the turn"]}',
        "continuity_json": '["one continuous take"]',
        "constraints_json": '["no identity drift"]',
        "missing_fields_json": "[]",
        "source_conflicts_json": "[]",
        "transferability_json": '{"seedance":{"status":"portable_scene_intent"},"h3":{"status":"portable_scene_intent"}}',
        "material_references_json": '[{"binding_status":"described_only"}]',
        "asset_mapping_count_audit_only": asset_count,
    }


class Stage5PromptCandidateTests(unittest.TestCase):
    def test_score_is_independent_of_asset_count(self) -> None:
        stratum = {"structure_state": "single_take"}
        low = score_record(row(asset_count=1), stratum)
        high = score_record(row(asset_count=999), stratum)
        self.assertEqual(low, high)

    def test_manual_review_is_not_scored(self) -> None:
        self.assertIsNone(score_record(row("needs_manual_review"), {"structure_state": "single_take"}))

    def test_pattern_families_are_multi_label_and_dialogue_is_explicit(self) -> None:
        result = score_record(row(), {"structure_state": "single_take"})
        families = pattern_families(row(), result)
        self.assertIn("action_choreography", families)
        self.assertIn("dialogue_performance", families)
        self.assertIn("character_performance", families)

    def test_candidate_order_uses_score_then_hash_only(self) -> None:
        records = [
            {"classification_status": "classified", "pattern_families": ["action_choreography"], "prompt_content_score": 20, "score_dimensions": {"a": {"score": 2}}, "prompt_sha256": "b"},
            {"classification_status": "classified", "pattern_families": ["action_choreography"], "prompt_content_score": 20, "score_dimensions": {"a": {"score": 2}}, "prompt_sha256": "a"},
        ]
        ranked = rank_candidates(records, "action_choreography", 10)
        self.assertEqual([item["prompt_sha256"] for item in ranked], ["a", "b"])

    def test_candidate_diversity_only_breaks_exact_score_ties(self) -> None:
        records = [
            {"classification_status": "classified", "pattern_families": ["camera_control"], "prompt_content_score": 21, "score_dimensions": {"a": {"score": 2}}, "prompt_sha256": "used-higher"},
            {"classification_status": "classified", "pattern_families": ["camera_control"], "prompt_content_score": 20, "score_dimensions": {"a": {"score": 2}}, "prompt_sha256": "new-lower"},
            {"classification_status": "classified", "pattern_families": ["camera_control"], "prompt_content_score": 21, "score_dimensions": {"a": {"score": 2}}, "prompt_sha256": "new-equal"},
        ]
        ranked = rank_candidates(records, "camera_control", 3, {"used-higher"})
        self.assertEqual([item["prompt_sha256"] for item in ranked], ["new-equal", "used-higher", "new-lower"])

    def test_dimension_gates_do_not_cross_credit_missing_evidence(self) -> None:
        candidate = row()
        candidate["camera_result_json"] = '{"segments": []}'
        candidate["physics_json"] = '{"segments": []}'
        candidate["continuity_json"] = "[]"
        result = score_record(candidate, {"structure_state": "single_take"})
        self.assertEqual(result["score_dimensions"]["camera_control"]["score"], 0)
        self.assertEqual(result["score_dimensions"]["physics_plausibility"]["score"], 0)
        self.assertEqual(result["score_dimensions"]["continuity_control"]["score"], 0)

    def test_cross_field_only_evidence_is_penalized_and_not_core(self) -> None:
        candidate = row()
        candidate["spatial_relations_json"] = '["shared evidence"]'
        candidate["action_summary_json"] = '{"beats":[{"summary":"shared evidence","causal_link":"then"}]}'
        candidate["performance_dialogue_reaction_json"] = '{"performance_segments":["shared evidence"],"dialogue_lines":[],"dialogue_scope":"none"}'
        candidate["camera_result_json"] = '{"segments":["shared evidence"]}'
        candidate["physics_json"] = '{"segments":["shared evidence"]}'
        candidate["continuity_json"] = '["shared evidence"]'
        candidate["constraints_json"] = '["shared evidence"]'
        result = score_record(candidate, {"structure_state": "single_take"})
        self.assertGreater(result["score_penalty"], 0)
        self.assertIn("spatial_relations", result["shared_evidence_fields"])
        self.assertNotEqual(result["case_tier"], "core_pattern")


if __name__ == "__main__":
    unittest.main()
