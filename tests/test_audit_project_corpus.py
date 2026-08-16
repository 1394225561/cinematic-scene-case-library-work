from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import audit_project_corpus as audit  # noqa: E402


class AuditProjectCorpusTests(unittest.TestCase):
    def test_format_normalize_only_ignores_case_and_whitespace(self) -> None:
        self.assertEqual(
            audit.format_normalize("  Shot  ONE\n\nAction "),
            "shot one action",
        )
        self.assertNotEqual(
            audit.format_normalize("Shot 1"), audit.format_normalize("Shot 2")
        )

    def test_numeric_normalize_marks_standalone_numeric_variants(self) -> None:
        self.assertEqual(
            audit.numeric_normalize("Shot 1 lasts 3.5 seconds"),
            audit.numeric_normalize("Shot 2 lasts 4.0 seconds"),
        )
        self.assertNotEqual(
            audit.numeric_normalize("Image1 moves"),
            audit.numeric_normalize("Image2 moves"),
        )

    def test_percentile_uses_nearest_rank_index(self) -> None:
        values = [10, 20, 30, 40, 50]

        self.assertEqual(audit.percentile(values, 0.0), 10)
        self.assertEqual(audit.percentile(values, 0.5), 30)
        self.assertEqual(audit.percentile(values, 1.0), 50)
        self.assertIsNone(audit.percentile([], 0.5))


if __name__ == "__main__":
    unittest.main()
