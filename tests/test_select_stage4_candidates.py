from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from select_stage4_candidates import PromptCandidate, rank_candidates


class SelectStage4CandidatesTests(unittest.TestCase):
    def candidate(self, prompt_hash: str, asset_count: int) -> PromptCandidate:
        return PromptCandidate(
            prompt_sha256=prompt_hash,
            prompt_text=(
                "A fight begins as the camera frames both opponents in the foreground. "
                "They face each other, one dodges a sword impact, and debris reacts to "
                "the collision with visible inertia."
            ),
            source_prompt_chars=800,
            first_asset_id=f"asset-{prompt_hash}",
            asset_count=asset_count,
            folder_names=("Scene 69 - Fight",),
            models=("seedance_2_0",),
        )

    def test_asset_count_does_not_influence_candidate_order(self) -> None:
        candidates = [self.candidate("b-hash", 999), self.candidate("a-hash", 1)]

        ranked = rank_candidates(
            candidates,
            "action_fight",
            min_chars=0,
            max_chars=1000,
            limit=10,
        )

        self.assertEqual([row["prompt_sha256"] for row in ranked], ["a-hash", "b-hash"])
        self.assertEqual(ranked[0]["asset_count_audit_only"], 1)

    def test_dialogue_candidate_requires_all_core_dimensions(self) -> None:
        candidate = PromptCandidate(
            prompt_sha256="dialogue",
            prompt_text=(
                "The camera holds a close-up with the listener in the background. "
                "Her eyes hesitate before she whispers the dialogue in a restrained voice: "
                '"Wait for me."'
            ),
            source_prompt_chars=700,
            first_asset_id="asset-dialogue",
            asset_count=20,
            folder_names=("Scene 28",),
            models=("seedance_2_0",),
        )

        ranked = rank_candidates(
            [candidate],
            "dialogue_performance",
            min_chars=0,
            max_chars=1000,
            limit=10,
        )

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["coverage_dimension_count"], 5)

    def test_character_voice_description_is_not_dialogue(self) -> None:
        candidate = PromptCandidate(
            prompt_sha256="voice-only",
            prompt_text=(
                "The camera frames her in the foreground. Her eyes are sharp and her "
                "character description says she speaks with a sarcastic voice."
            ),
            source_prompt_chars=700,
            first_asset_id="asset-voice-only",
            asset_count=1,
            folder_names=("Scene 23",),
            models=("seedance_2_0",),
        )

        ranked = rank_candidates(
            [candidate],
            "dialogue_performance",
            min_chars=0,
            max_chars=1000,
            limit=10,
        )

        self.assertEqual(ranked, [])


if __name__ == "__main__":
    unittest.main()
