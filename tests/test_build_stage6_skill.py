from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_stage6_skill import (  # noqa: E402
    render_case,
    render_index,
    signal_counts,
    safe_slug,
)


def row() -> dict[str, object]:
    return {
        "subjects_json": '[{"subject_id":"s1"}]',
        "spatial_relations_json": '["left of landmark"]',
        "action_summary_json": '{"beats":[{"summary":"moves"},{"summary":"reacts"}]}',
        "performance_dialogue_reaction_json": '{"performance_segments":["looks"],"dialogue_lines":[{"line":"line"}]}',
        "camera_result_json": '{"segments":["medium shot"]}',
        "lighting_json": '{"segments":["backlight"]}',
        "sound_json": '{"segments":["wind"]}',
        "physics_json": '{"segments":["weight transfer"]}',
        "continuity_json": '["same axis"]',
        "constraints_json": '["no drift"]',
        "material_references_json": '[{"binding_status":"described_only"}]',
    }


def record() -> dict[str, object]:
    return {
        "case_id": "scene-case-camera_control-01",
        "candidate_family": "camera_control",
        "prompt_sha256": "a" * 64,
        "normalization_digest": "b" * 64,
        "source_prompt_chars": 1200,
        "prompt_content_score": 32,
        "score_maximum": 32,
        "score_dimensions": {"camera_control": {"score": 4, "evidence_fields": ["camera_result"]}},
        "critical_missing_fields": [],
        "source_conflicts": [],
        "risk_flags": [],
        "structure_state": "single_take",
        "asset_ids": ["asset-audit-only"],
        "folder_names": ["Scene test"],
        "asset_count_audit_only": 1,
    }


class Stage6SkillBuildTests(unittest.TestCase):
    def test_signal_counts_are_structural_only(self) -> None:
        counts = signal_counts(row())
        self.assertEqual(counts["action_beats"], 2)
        self.assertEqual(counts["dialogue_lines"], 1)
        self.assertEqual(counts["camera_segments"], 1)
        self.assertEqual(counts["material_references"], 1)

    def test_case_does_not_copy_source_objective_or_prompt_text(self) -> None:
        source_row = row()
        source_row["objective_text"] = "SOURCE_SECRET_OBJECTIVE"
        rendered = render_case(record(), source_row)
        self.assertNotIn("SOURCE_SECRET_OBJECTIVE", rendered)
        self.assertIn("asset-audit-only", rendered)
        self.assertIn("never be copied", rendered)

    def test_index_uses_existing_slugged_case_links(self) -> None:
        self.assertEqual(safe_slug("scene-case-camera_control-01"), "scene-case-camera-control-01")
        index = render_index([record()], {"stage5_2_digest": "digest"})
        self.assertIn("cases/scene-case-camera-control-01.md", index)
        self.assertNotIn("cases/scene-case-camera_control-01.md", index)


if __name__ == "__main__":
    unittest.main()
