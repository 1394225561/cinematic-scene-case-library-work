from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from probe_higgsfield import utc_now, write_json_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = WORK_ROOT / "data" / "runs" / "project-corpus" / "corpus.sqlite3"
DEFAULT_OUTPUT = (
    WORK_ROOT
    / "data"
    / "runs"
    / "stage-4-normalization"
    / "selected-source-records.json"
)


def placeholders(values: Iterable[Any]) -> str:
    return ",".join("?" for _ in values)


def export_prompt_records(
    connection: sqlite3.Connection, prompt_hashes: list[str]
) -> list[dict[str, Any]]:
    if not prompt_hashes:
        return []
    unique_hashes = list(dict.fromkeys(prompt_hashes))
    prompt_rows = connection.execute(
        f"""
        SELECT prompt_sha256, prompt_text, source_prompt_chars,
               analysis_prompt_chars, url_redaction_count, first_asset_id
        FROM prompts
        WHERE prompt_sha256 IN ({placeholders(unique_hashes)})
        """,
        unique_hashes,
    ).fetchall()
    prompts = {
        row[0]: {
            "prompt_sha256": row[0],
            "prompt_text": row[1],
            "source_prompt_chars": row[2],
            "analysis_prompt_chars": row[3],
            "url_redaction_count": row[4],
            "first_asset_id": row[5],
            "assets": [],
        }
        for row in prompt_rows
    }
    missing = [prompt_hash for prompt_hash in unique_hashes if prompt_hash not in prompts]
    if missing:
        raise ValueError(f"Unknown prompt SHA-256: {', '.join(missing)}")

    asset_rows = connection.execute(
        f"""
        SELECT a.prompt_sha256, a.asset_id, a.folder_id,
               COALESCE(primary_folder.name, '<unknown>') AS primary_folder_name,
               a.item_type, a.asset_type, a.status, a.job_set_type, a.model,
               a.duration_seconds, a.width, a.height, a.resolution,
               a.source_page, a.source_item_index
        FROM assets a
        LEFT JOIN folders primary_folder ON primary_folder.folder_id = a.folder_id
        WHERE a.prompt_sha256 IN ({placeholders(unique_hashes)})
        ORDER BY a.prompt_sha256, a.asset_id
        """,
        unique_hashes,
    ).fetchall()
    assets_by_id: dict[str, dict[str, Any]] = {}
    for row in asset_rows:
        asset = {
            "asset_id": row[1],
            "primary_folder_id": row[2],
            "primary_folder_name": row[3],
            "folder_memberships": [],
            "item_type": row[4],
            "asset_type": row[5],
            "status": row[6],
            "job_set_type": row[7],
            "model": row[8],
            "duration_seconds": row[9],
            "width": row[10],
            "height": row[11],
            "resolution": row[12],
            "source_page": row[13],
            "source_item_index": row[14],
        }
        prompts[row[0]]["assets"].append(asset)
        assets_by_id[row[1]] = asset

    asset_ids = list(assets_by_id)
    if asset_ids:
        membership_rows = connection.execute(
            f"""
            SELECT m.asset_id, m.folder_id, COALESCE(f.name, '<unknown>'),
                   m.first_seen_page
            FROM asset_folder_memberships m
            LEFT JOIN folders f ON f.folder_id = m.folder_id
            WHERE m.asset_id IN ({placeholders(asset_ids)})
            ORDER BY m.asset_id, m.folder_id
            """,
            asset_ids,
        ).fetchall()
        for row in membership_rows:
            assets_by_id[row[0]]["folder_memberships"].append(
                {
                    "folder_id": row[1],
                    "folder_name": row[2],
                    "first_seen_page": row[3],
                }
            )

    return [prompts[prompt_hash] for prompt_hash in unique_hashes]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export exact Prompt text and complete source mappings by SHA-256."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--prompt-sha256", action="append", required=True, dest="prompt_hashes"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    connection = sqlite3.connect(f"file:{args.database.resolve()}?mode=ro", uri=True)
    try:
        records = export_prompt_records(connection, args.prompt_hashes)
    finally:
        connection.close()

    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "source_database": str(args.database.resolve()),
        "records": records,
    }
    write_json_atomic(args.output, report)
    print(
        {
            "prompt_count": len(records),
            "asset_count": sum(len(record["assets"]) for record in records),
            "output": str(args.output.resolve()),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
