from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from checkpoint_stage4b_normalization import (  # noqa: E402
    build_hash_mapping,
    build_issue_register,
    hash_mapping_digest,
)


class CheckpointStage4BNormalizationTests(unittest.TestCase):
    def test_hash_mapping_is_sorted_and_digest_is_deterministic(self) -> None:
        source = {
            "b": {"source_prompt_chars": 20},
            "a": {"source_prompt_chars": 10},
        }
        strata = {
            "a": {"text_length_band": "short"},
            "b": {"text_length_band": "long"},
        }
        normalizations = {
            "b": {
                "source_prompt_chars": 20,
                "source_input_sha256": "input-b",
                "normalization_digest": "norm-b",
                "normalization_status": "normalized",
                "processing_status": "completed",
                "complexity_queue": "complex",
                "scene_tags_json": '["action_interaction"]',
            },
            "a": {
                "source_prompt_chars": 10,
                "source_input_sha256": "input-a",
                "normalization_digest": "norm-a",
                "normalization_status": "needs_manual_review",
                "processing_status": "completed",
                "complexity_queue": "standard",
                "scene_tags_json": "[]",
            },
        }
        first = build_hash_mapping(source, strata, normalizations, {"a": 1, "b": 2})
        second = build_hash_mapping(source, strata, normalizations, {"a": 1, "b": 2})
        self.assertEqual([item["prompt_sha256"] for item in first], ["a", "b"])
        self.assertEqual(first, second)
        self.assertEqual(hash_mapping_digest(first), hash_mapping_digest(second))

    def test_issue_register_keeps_manual_review_and_failed_records_explicit(self) -> None:
        normalizations = {
            "manual": {
                "normalization_status": "needs_manual_review",
                "processing_status": "completed",
                "failure_code": None,
                "source_prompt_chars": 120,
                "complexity_queue": "complex",
                "risk_flags_json": '["very_long_prompt"]',
                "status_reasons_json": '["tail requires review"]',
            },
            "failed": {
                "normalization_status": "excluded_with_reason",
                "processing_status": "failed",
                "failure_code": "parse_error",
                "source_prompt_chars": 5,
                "complexity_queue": "manual_review",
                "risk_flags_json": "[]",
                "status_reasons_json": '["parse failed"]',
            },
        }
        strata = {
            "manual": {"scene_tags_json": '["environment_establishing"]'},
            "failed": {"scene_tags_json": "[]"},
        }
        result = build_issue_register(normalizations, strata, {"unicode": 1}, {"completed_with_issues": 1})
        self.assertEqual(result["normalization"]["manual_review_count"], 1)
        self.assertEqual(result["normalization"]["excluded_count"], 1)
        self.assertEqual(result["normalization"]["failed_count"], 1)
        self.assertEqual(result["normalization"]["manual_review_reason_counts"], {"parse failed": 1, "tail requires review": 1})
        self.assertEqual(result["preprocessing"]["issue_code_counts"], {"unicode": 1})


if __name__ == "__main__":
    unittest.main()
