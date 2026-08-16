from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import crawl_folder_prompts as crawler  # noqa: E402


def sample_payload(prompt: str, cursor: str | None = None) -> str:
    return json.dumps(
        {
            "items": [
                {
                    "type": "job",
                    "job": {
                        "id": "asset-1",
                        "folder_id": crawler.DEFAULT_FOLDER_ID,
                        "status": "completed",
                        "job_set_type": "video",
                        "params": {
                            "prompt": prompt,
                            "model": "Seedance 2.0",
                            "width": 2016,
                            "height": 864,
                            "duration": 15,
                        },
                        "results": {"raw": {"type": "video"}},
                    },
                }
            ],
            "cursor": cursor,
        }
    )


def normalized_page(prompt: str = "A clean action prompt.") -> dict[str, object]:
    return crawler.normalize_page(
        sample_payload(prompt),
        project_id=crawler.DEFAULT_PROJECT_ID,
        folder_id=crawler.DEFAULT_FOLDER_ID,
        folder_name=crawler.DEFAULT_FOLDER_NAME,
        page_number=1,
        cursor_requested=None,
        source_url="https://fnf-api-gw.higgsfield.ai/fnf/test",
        fetched_at="2026-08-16T00:00:00+00:00",
        http={"status": 200, "content_type": "application/json"},
        request_attempts=1,
    )


class CrawlFolderPromptsTests(unittest.TestCase):
    def test_normalize_page_redacts_prompt_urls_and_logs_warning(self) -> None:
        page = normalized_page("Fight near https://cdn.example.test/clip.mp4 then stop.")

        self.assertEqual(page["record_count"], 1)
        self.assertNotIn("https://", page["records"][0]["prompt"])
        self.assertEqual(page["records"][0]["prompt_url_redactions"], 1)
        self.assertEqual(page["warnings"][0]["code"], "prompt_url_redacted")

    def test_commit_page_stops_on_repeated_cursor(self) -> None:
        config = {
            "project_id": crawler.DEFAULT_PROJECT_ID,
            "folder_id": crawler.DEFAULT_FOLDER_ID,
            "folder_name": crawler.DEFAULT_FOLDER_NAME,
        }
        checkpoint = crawler.initial_checkpoint(config)
        page_one = normalized_page()
        page_one["next_cursor"] = 1785977309.882066

        with tempfile.TemporaryDirectory() as temporary:
            event_log = Path(temporary) / "events.jsonl"
            checkpoint = crawler.commit_page(
                checkpoint, page_one, event_log=event_log
            )
            page_two = dict(page_one)
            page_two["page_number"] = 2
            page_two["cursor_requested"] = 1785977309.882066
            checkpoint = crawler.commit_page(
                checkpoint, page_two, event_log=event_log
            )

        self.assertEqual(checkpoint["fatal_error"], "API returned a repeated cursor")

    def test_complete_run_rerun_makes_no_network_request(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            normalized_dir = run_dir / "pages" / "normalized"
            raw_dir = run_dir / "pages" / "raw"
            normalized_dir.mkdir(parents=True)
            raw_dir.mkdir(parents=True)
            config = {
                "schema_version": 1,
                "project_id": crawler.DEFAULT_PROJECT_ID,
                "folder_id": crawler.DEFAULT_FOLDER_ID,
                "folder_name": crawler.DEFAULT_FOLDER_NAME,
                "expected_count": 1,
                "page_size": 50,
                "include_subfolders": False,
            }
            page = normalized_page()
            checkpoint = crawler.commit_page(
                crawler.initial_checkpoint(config),
                page,
                event_log=run_dir / "events.jsonl",
            )
            crawler.write_json_atomic(run_dir / "config.json", config)
            crawler.write_json_atomic(run_dir / "checkpoint.json", checkpoint)
            crawler.write_json_atomic(normalized_dir / "page-000001.json", page)
            crawler.write_text_atomic(
                raw_dir / "page-000001.json", sample_payload("A clean action prompt.")
            )

            argv = [
                "crawl_folder_prompts.py",
                "--run-dir",
                str(run_dir),
                "--expected-count",
                "1",
                "--page-size",
                "50",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(
                    crawler,
                    "request_page",
                    side_effect=AssertionError("network request was attempted"),
                ) as request_mock,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                exit_code = crawler.main()

            self.assertEqual(exit_code, 0)
            request_mock.assert_not_called()
            report = crawler.load_json_object(run_dir / "reconciliation.json")
            self.assertEqual(report["network_requests_this_invocation"], 0)
            self.assertEqual(report["unique_prompt_count"], 1)
            self.assertEqual(len(report["page_manifest"]), 1)
            self.assertTrue(report["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
