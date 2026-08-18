from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


WORK_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = WORK_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_stage7_integration import (  # noqa: E402
    INTEGRATION_DIR,
    decide_retrieval,
    handoff_violations,
    validate,
)


class Stage7IntegrationValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (INTEGRATION_DIR / "stage7-routing-contract.json").read_text(encoding="utf-8")
        )

    def test_retrieval_trigger_wins_for_underspecified_request(self) -> None:
        result = decide_retrieval(["missing_structure"], self.contract)
        self.assertEqual(result, {"retrieve": True, "reason": "missing_structure"})

    def test_complete_shootable_request_skips_retrieval(self) -> None:
        result = decide_retrieval(["concrete_shootable_complete"], self.contract)
        self.assertEqual(
            result,
            {"retrieve": False, "reason": "concrete_shootable_complete"},
        )

    def test_handoff_scanner_rejects_source_and_cross_model_leaks(self) -> None:
        leaking = {
            "task_id": "example",
            "case_id": "scene-case-example-01",
            "acting-for-ai-video": ["use @old_tag for 15 seconds"],
            "cinedance-seedance-director": ["Use <Picture 1> and asset 1258d035-2cac-4a3c-86c3-a491cebbb294"],
            "final_owner": "cinedance-seedance-director",
        }
        violations = handoff_violations(leaking, "seedance")
        self.assertIn("historical_at_tag", violations)
        self.assertIn("historical_duration", violations)
        self.assertIn("source_asset_id", violations)
        self.assertIn("h3_syntax:<Picture 1>", violations)

    def test_current_stage7_artifacts_pass(self) -> None:
        report = validate()
        self.assertEqual(report["status"], "pass")
        self.assertFalse(report["issues"])


if __name__ == "__main__":
    unittest.main()
