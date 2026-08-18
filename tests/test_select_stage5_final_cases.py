from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from select_stage5_final_cases import (  # noqa: E402
    eligibility_reasons,
    priority_key,
    select_final_cases,
)


def candidate(
    prompt_sha256: str,
    *,
    family: str = "camera_control",
    score: int = 32,
    minimum_dimension: int = 4,
    tier: str = "core_pattern",
    asset_count: int = 1,
    risks: list[str] | None = None,
    near_groups: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "candidate_family": family,
        "selection_rank": 1,
        "selection_rationale": "test",
        "prompt_sha256": prompt_sha256,
        "classification_status": "classified",
        "normalization_status": "normalized",
        "source_prompt_chars": 1000,
        "complexity_queue": "standard",
        "structure_state": "single_take",
        "duration_state": "consistent",
        "scene_tags": ["mixed_scene"],
        "risk_flags": risks or [],
        "missing_fields": [],
        "source_conflicts": [],
        "normalization_digest": f"digest-{prompt_sha256}",
        "pattern_families": [family],
        "near_duplicate_groups": near_groups or [],
        "near_duplicate_decision": "candidate_only_not_merged" if near_groups else "not_grouped",
        "asset_mapping_count_audit_only": asset_count,
        "prompt_content_score": score,
        "score_maximum": 32,
        "score_dimensions": {
            "shootability": {"score": minimum_dimension, "max_score": 4},
            "spatial_clarity": {"score": minimum_dimension, "max_score": 4},
        },
        "score_penalty": 0,
        "shared_evidence_fields": [],
        "case_tier": tier,
        "critical_missing_fields": [],
        "source_conflict_count": 0,
        "asset_ids": [f"asset-{index}" for index in range(asset_count)],
        "asset_count_audit_only": asset_count,
        "folder_ids": ["folder-1"],
        "folder_names": ["Scene 1"],
        "models": ["seedance_2_0"],
        "duration_seconds": [15.0],
        "resolutions": ["1080p"],
    }


class Stage5FinalSelectionTests(unittest.TestCase):
    def test_asset_count_does_not_affect_priority(self) -> None:
        low_count = candidate("same", asset_count=1)
        high_count = candidate("same", asset_count=999)
        self.assertEqual(priority_key(low_count), priority_key(high_count))

    def test_special_scene_below_gate_is_not_selected(self) -> None:
        record = candidate("special", score=6, minimum_dimension=0, tier="special_scene")
        self.assertIn("case_tier_below_final_selection_gate", eligibility_reasons(record))
        selected, decisions = select_final_cases([record])
        self.assertEqual(selected, [])
        self.assertEqual(decisions[0]["decision"], "not_selected")

    def test_family_quota_retains_eligible_alternatives(self) -> None:
        records = [candidate("a"), candidate("b"), candidate("c")]
        selected, decisions = select_final_cases(records, cases_per_family=2)
        self.assertEqual([item["prompt_sha256"] for item in selected], ["a", "b"])
        by_hash = {item["prompt_sha256"]: item for item in decisions}
        self.assertEqual(by_hash["c"]["decision"], "retained_alternative")
        self.assertIn("family_quota_exhausted", by_hash["c"]["decision_reason_codes"])

    def test_near_duplicate_is_retained_not_selected(self) -> None:
        group = [{"group_type": "format_normalized_groups", "group_index": "1", "fingerprint": "shared"}]
        records = [candidate("a", near_groups=group), candidate("b", near_groups=group)]
        selected, decisions = select_final_cases(records, cases_per_family=2)
        self.assertEqual([item["prompt_sha256"] for item in selected], ["a"])
        by_hash = {item["prompt_sha256"]: item for item in decisions}
        self.assertEqual(by_hash["b"]["decision"], "retained_alternative")
        self.assertEqual(by_hash["b"]["near_duplicate_of_case_id"], selected[0]["case_id"])

    def test_score_outranks_editorial_risk_tiebreak(self) -> None:
        lower = candidate("a", score=31)
        higher = candidate("z", score=32, risks=["very_long_prompt", "high_marker_density"])
        selected, _ = select_final_cases([lower, higher], cases_per_family=1)
        self.assertEqual(selected[0]["prompt_sha256"], "z")


if __name__ == "__main__":
    unittest.main()
