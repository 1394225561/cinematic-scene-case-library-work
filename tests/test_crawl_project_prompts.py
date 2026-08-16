from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import crawl_project_prompts as crawler  # noqa: E402


def job_item(
    asset_id: str,
    prompt: str | None,
    folder_id: str = "52eefbe6-4d49-405a-a244-24ead11f2887",
) -> dict[str, object]:
    return {
        "type": "job",
        "job": {
            "id": asset_id,
            "folder_id": folder_id,
            "status": "completed",
            "job_set_type": "seedance_2_0",
            "created_at": 1785977309.0,
            "params": {
                "prompt": prompt,
                "model": "seedance_2_0",
                "width": 2016,
                "height": 864,
                "duration": 15,
            },
            "results": {"raw": {"type": "video"}},
        },
    }


class CrawlProjectPromptsTests(unittest.TestCase):
    def test_parse_item_preserves_empty_prompt_asset_and_logs_error(self) -> None:
        parsed = crawler.parse_item(
            job_item("asset-empty", ""), item_index=0, page_number=1
        )

        self.assertEqual(parsed["asset"]["asset_id"], "asset-empty")
        self.assertIsNone(parsed["asset"]["prompt_sha256"])
        self.assertEqual(parsed["issues"][0]["code"], "empty_prompt")

    def test_commit_page_deduplicates_prompt_text_but_preserves_assets(self) -> None:
        payload = {
            "items": [
                job_item("asset-1", "Fight in one continuous shot."),
                job_item("asset-2", "Fight in one continuous shot."),
            ],
            "cursor": None,
        }
        response_text = json.dumps(payload)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw_path = root / "page-000001.json"
            crawler.write_text_atomic(raw_path, response_text)
            connection = crawler.connect_database(root / "corpus.sqlite3")
            page = crawler.parse_page(
                response_text,
                page_number=1,
                cursor_requested=None,
                source_endpoint="https://fnf-api-gw.higgsfield.ai/fnf/test",
                fetched_at="2026-08-16T00:00:00+00:00",
                request_attempts=1,
            )
            row = crawler.commit_page(connection, page, raw_path=raw_path)

            self.assertEqual(row["received_items"], 2)
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0], 2
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM prompts").fetchone()[0], 1
            )
            connection.close()

    def test_advance_checkpoint_stops_on_repeated_float_cursor(self) -> None:
        checkpoint = crawler.initial_checkpoint(
            {"project_id": crawler.DEFAULT_PROJECT_ID}
        )
        first = {
            "page_number": 1,
            "cursor_requested_json": "null",
            "next_cursor_json": "1785977309.5",
            "received_items": 100,
            "asset_id_count": 100,
            "prompt_record_count": 100,
        }
        checkpoint = crawler.advance_checkpoint(checkpoint, first)
        second = {
            "page_number": 2,
            "cursor_requested_json": "1785977309.5",
            "next_cursor_json": "1785977309.5",
            "received_items": 100,
            "asset_id_count": 100,
            "prompt_record_count": 100,
        }

        checkpoint = crawler.advance_checkpoint(checkpoint, second)

        self.assertEqual(checkpoint["fatal_error"], "API returned a repeated cursor")

    def test_duplicate_asset_preserves_multiple_folder_memberships(self) -> None:
        first_payload = {
            "items": [job_item("asset-shared", "Shared prompt.", "folder-a")],
            "cursor": 2.0,
        }
        second_payload = {
            "items": [job_item("asset-shared", "Shared prompt.", "folder-b")],
            "cursor": None,
        }

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            connection = crawler.connect_database(root / "corpus.sqlite3")
            for page_number, (payload, requested) in enumerate(
                ((first_payload, None), (second_payload, 2.0)), start=1
            ):
                response_text = json.dumps(payload)
                raw_path = root / f"page-{page_number:06d}.json"
                crawler.write_text_atomic(raw_path, response_text)
                page = crawler.parse_page(
                    response_text,
                    page_number=page_number,
                    cursor_requested=requested,
                    source_endpoint="https://fnf-api-gw.higgsfield.ai/fnf/test",
                    fetched_at="2026-08-16T00:00:00+00:00",
                    request_attempts=1,
                )
                crawler.commit_page(connection, page, raw_path=raw_path)

            memberships = connection.execute(
                """
                SELECT folder_id FROM asset_folder_memberships
                WHERE asset_id = 'asset-shared' ORDER BY folder_id
                """
            ).fetchall()
            duplicate_count = connection.execute(
                "SELECT COUNT(*) FROM issues WHERE code = 'duplicate_asset_id'"
            ).fetchone()[0]
            connection.close()

        self.assertEqual([row[0] for row in memberships], ["folder-a", "folder-b"])
        self.assertEqual(duplicate_count, 1)

    def test_prompt_url_is_redacted_but_source_hash_uses_original_text(self) -> None:
        prompt = "Use [reference](https://cdn.example.test/reference.webp) now."
        parsed = crawler.parse_item(
            job_item("asset-url", prompt), item_index=0, page_number=1
        )

        self.assertNotIn("https://", parsed["prompt"]["prompt_text"])
        self.assertEqual(
            parsed["prompt"]["prompt_sha256"],
            crawler.hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(parsed["issues"][0]["code"], "prompt_url_redacted")


if __name__ == "__main__":
    unittest.main()
