from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import inventory_project_folders as inventory  # noqa: E402


ROOT_ID = "3caa2f3a-52b5-4293-9237-0c8f76c7158a"
CHILD_ID = "2f0e48fe-1bfb-46e2-b88d-443da2ee8f90"


def folder(
    folder_id: str,
    *,
    parent_id: str | None,
    name: str,
    count: int,
    subfolders_count: int,
    path: str,
) -> dict[str, object]:
    return {
        "folder_id": folder_id,
        "parent_id": parent_id,
        "root_folder_id": ROOT_ID,
        "project_id": ROOT_ID,
        "name": name,
        "path": path,
        "is_root": folder_id == ROOT_ID,
        "reported_asset_count": count,
        "reported_subfolders_count": subfolders_count,
        "reported_folders_count": 1 if folder_id == ROOT_ID else None,
        "created_at_unix": None,
        "updated_at_unix": None,
    }


class InventoryProjectFoldersTests(unittest.TestCase):
    def test_sanitize_folder_excludes_media_urls(self) -> None:
        value = {
            "id": CHILD_ID,
            "parent_id": ROOT_ID,
            "root_folder_id": ROOT_ID,
            "project_id": ROOT_ID,
            "name": "Scene",
            "path": f"/{ROOT_ID}/{CHILD_ID}/",
            "is_root": False,
            "count": 8,
            "subfolders_count": 0,
            "preview_url": "https://cdn.example.test/preview.webp",
            "cover_image_url": "https://cdn.example.test/cover.webp",
        }

        result = inventory.sanitize_folder(value)

        self.assertEqual(result["reported_asset_count"], 8)
        self.assertNotIn("preview_url", result)
        self.assertNotIn("cover_image_url", result)

    def test_derive_direct_counts_preserves_recursive_total(self) -> None:
        folders = {
            ROOT_ID: folder(
                ROOT_ID,
                parent_id=None,
                name="Root",
                count=10,
                subfolders_count=1,
                path=f"/{ROOT_ID}/",
            ),
            CHILD_ID: folder(
                CHILD_ID,
                parent_id=ROOT_ID,
                name="Child",
                count=7,
                subfolders_count=0,
                path=f"/{ROOT_ID}/{CHILD_ID}/",
            ),
        }

        result, errors = inventory.derive_direct_counts(folders, ROOT_ID)
        by_id = {item["folder_id"]: item for item in result}

        self.assertEqual(errors, [])
        self.assertEqual(by_id[ROOT_ID]["derived_direct_asset_count"], 3)
        self.assertEqual(by_id[CHILD_ID]["derived_direct_asset_count"], 7)
        self.assertEqual(
            sum(item["derived_direct_asset_count"] for item in result), 10
        )

    def test_derive_direct_counts_reports_negative_parent_remainder(self) -> None:
        folders = {
            ROOT_ID: folder(
                ROOT_ID,
                parent_id=None,
                name="Root",
                count=2,
                subfolders_count=1,
                path=f"/{ROOT_ID}/",
            ),
            CHILD_ID: folder(
                CHILD_ID,
                parent_id=ROOT_ID,
                name="Child",
                count=3,
                subfolders_count=0,
                path=f"/{ROOT_ID}/{CHILD_ID}/",
            ),
        }

        _, errors = inventory.derive_direct_counts(folders, ROOT_ID)

        self.assertEqual(errors[0]["code"], "negative_derived_direct_count")

    def test_public_child_count_mismatch_is_audited_without_stopping(self) -> None:
        root = folder(
            ROOT_ID,
            parent_id=None,
            name="Root",
            count=2,
            subfolders_count=1,
            path=f"/{ROOT_ID}/",
        )
        checkpoint = inventory.initial_checkpoint(root)
        page = {
            "parent_id": ROOT_ID,
            "page_number": 1,
            "cursor_requested": None,
            "next_cursor": None,
            "received_items": 0,
            "folders": [],
        }

        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = inventory.commit_children_page(
                checkpoint,
                page,
                event_log=Path(temporary) / "events.jsonl",
            )

        self.assertTrue(checkpoint["complete"])
        self.assertIsNone(checkpoint["fatal_error"])
        self.assertEqual(
            checkpoint["warnings"][0]["code"], "public_child_count_mismatch"
        )


if __name__ == "__main__":
    unittest.main()
