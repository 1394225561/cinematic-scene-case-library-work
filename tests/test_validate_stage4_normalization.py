from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


WORK_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = WORK_ROOT / "scripts"
RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-4-normalization"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_stage4_normalization import validate_data


class ValidateStage4NormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(
            (RUN_DIR / "normalization-schema.json").read_text(encoding="utf-8")
        )
        cls.samples = json.loads(
            (RUN_DIR / "normalized-samples.json").read_text(encoding="utf-8")
        )
        cls.sources = json.loads(
            (RUN_DIR / "selected-source-records.json").read_text(encoding="utf-8")
        )

    def issue_codes(self, samples: dict) -> set[str]:
        return {
            item["code"]
            for item in validate_data(self.schema, samples, self.sources)
        }

    def test_current_bundle_passes(self) -> None:
        self.assertEqual(validate_data(self.schema, self.samples, self.sources), [])

    def test_rejects_fabricated_h3_media_binding(self) -> None:
        samples = copy.deepcopy(self.samples)
        samples["records"][0]["h3_adapter_layer"]["prompt"] += " <Picture 1>"

        self.assertIn("h3_fabricated_reference", self.issue_codes(samples))

    def test_rejects_source_mapping_drift(self) -> None:
        samples = copy.deepcopy(self.samples)
        samples["records"][0]["source_layer"]["source_prompt_chars"] += 1

        self.assertIn("source_chars", self.issue_codes(samples))

    def test_rejects_source_prompt_hash_drift(self) -> None:
        sources = copy.deepcopy(self.sources)
        sources["records"][0]["prompt_text"] += " changed"

        codes = {
            item["code"]
            for item in validate_data(self.schema, self.samples, sources)
        }
        self.assertIn("source_hash", codes)

    def test_rejects_action_beat_count_drift(self) -> None:
        samples = copy.deepcopy(self.samples)
        action = next(
            record for record in samples["records"] if record["category"] == "action_fight"
        )
        action["model_neutral_scene_layer"]["action_beats"].pop()

        self.assertIn("action_beat_count", self.issue_codes(samples))

    def test_rejects_unapproved_extra_schema_field(self) -> None:
        samples = copy.deepcopy(self.samples)
        samples["records"][0]["quality_score"] = 99

        self.assertIn("schema_additional_property", self.issue_codes(samples))

    def test_rejects_dialogue_drift(self) -> None:
        samples = copy.deepcopy(self.samples)
        samples["records"][0]["h3_adapter_layer"]["prompt"] = samples["records"][0][
            "h3_adapter_layer"
        ]["prompt"].replace("Are you kidding me?", "Seriously?")

        self.assertIn("dialogue_drift", self.issue_codes(samples))


if __name__ == "__main__":
    unittest.main()
