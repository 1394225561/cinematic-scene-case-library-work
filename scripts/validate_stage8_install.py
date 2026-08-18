from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from validate_stage6_skill import validate as validate_stage6


WORK_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-8-install"
MANIFEST_PATH = RUN_DIR / "installation-manifest.json"
SOURCE_SKILL = WORK_ROOT / "skill" / "cinematic-scene-case-library"
INSTALLED_SKILL = Path(r"C:\Users\Admin\.agents\skills\cinematic-scene-case-library")
SEEDANCE_TARGET = Path(r"C:\Users\Admin\.agents\skills\cinema-studio-production\SKILL.md")
H3_TARGET = Path(r"C:\Users\Admin\.agents\skills\minimax-h3-director\SKILL.md")
MEDIA_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".webm",
    ".mp3", ".wav", ".m4a", ".ogg", ".avi", ".mkv",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(checks: dict[str, bool], name: str, condition: bool) -> None:
    checks[name] = bool(condition)


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): sha256(path)
        for path in root.rglob("*")
        if path.is_file()
    }


def validate() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    issues: list[str] = []
    check(checks, "run_dir_exists", RUN_DIR.is_dir())
    check(checks, "manifest_exists", MANIFEST_PATH.is_file())
    if not all(checks.values()):
        return {"status": "fail", "checks": checks, "issues": issues}

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    check(checks, "manifest_stage", manifest.get("stage") == "8")
    check(checks, "manifest_status", manifest.get("status") == "installed")
    check(checks, "installed_skill_exists", INSTALLED_SKILL.is_dir())
    check(checks, "seedance_target_exists", SEEDANCE_TARGET.is_file())
    check(checks, "h3_target_exists", H3_TARGET.is_file())

    installed_files = [path for path in INSTALLED_SKILL.rglob("*") if path.is_file()] if INSTALLED_SKILL.is_dir() else []
    check(checks, "installed_file_count", len(installed_files) == manifest.get("installed_file_count") == 29)
    source_hashes = tree_hashes(SOURCE_SKILL) if SOURCE_SKILL.is_dir() else {}
    installed_hashes = tree_hashes(INSTALLED_SKILL) if INSTALLED_SKILL.is_dir() else {}
    check(checks, "installed_tree_matches_source", source_hashes == installed_hashes)
    check(checks, "installed_manifest_hash", sha256(INSTALLED_SKILL / "references" / "build-manifest.json") == manifest.get("installed_skill_manifest_sha256"))
    media_files = [path for path in installed_files if path.suffix.lower() in MEDIA_EXTENSIONS]
    check(checks, "installed_no_media", not media_files)
    check(checks, "installed_stage6_validator", validate_stage6(INSTALLED_SKILL).get("status") == "pass")

    backup_paths = [Path(path) for path in manifest.get("backups", [])]
    check(checks, "backup_count", len(backup_paths) == 2 and all(path.is_file() for path in backup_paths))
    before = manifest.get("target_before_sha256", {})
    after = manifest.get("target_after_sha256", {})
    check(checks, "seedance_backup_matches_before", backup_paths[0].is_file() and sha256(backup_paths[0]) == before.get("seedance"))
    check(checks, "h3_backup_matches_before", backup_paths[1].is_file() and sha256(backup_paths[1]) == before.get("h3"))
    check(checks, "seedance_after_hash", sha256(SEEDANCE_TARGET) == after.get("seedance") and sha256(SEEDANCE_TARGET) != before.get("seedance"))
    check(checks, "h3_after_hash", sha256(H3_TARGET) == after.get("h3") and sha256(H3_TARGET) != before.get("h3"))

    seedance_text = SEEDANCE_TARGET.read_text(encoding="utf-8")
    h3_text = H3_TARGET.read_text(encoding="utf-8")
    check(checks, "seedance_insert_once", seedance_text.count("## Retrieve an optional scene case") == 1)
    check(checks, "h3_insert_once", h3_text.count("## Retrieve an optional scene case") == 1)
    check(checks, "seedance_anchor_once", seedance_text.count("## Compose mixed requests") == 1)
    check(checks, "h3_anchor_once", h3_text.count("## Select the H3 mode") == 1)
    check(checks, "seedance_final_owner_text", "CINEDANCE still assembles and QA-checks" in seedance_text)
    check(checks, "h3_independence_text", "never invoke or route this H3 workflow through `$cinema-studio-production`" in h3_text)
    check(checks, "h3_final_owner_text", "`minimax-h3-director` still owns" in h3_text)
    check(checks, "no_stage8_temp_files", not any(path.name.startswith(".stage8-") for path in SEEDANCE_TARGET.parent.iterdir()))
    check(checks, "no_stage8_temp_files_h3", not any(path.name.startswith(".stage8-") for path in H3_TARGET.parent.iterdir()))

    if media_files:
        issues.extend(str(path) for path in media_files)
    if not checks.get("installed_stage6_validator", False):
        issues.append("installed Stage 6 Skill validator did not pass")
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "installed_skill": str(INSTALLED_SKILL),
        "installed_file_count": len(installed_files),
        "media_files": [str(path) for path in media_files],
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Stage 8 installed Skill and integration patches.")
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()
    report = validate()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
