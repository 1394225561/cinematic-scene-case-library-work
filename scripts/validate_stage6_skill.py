from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_DIR = WORK_ROOT / "skill" / "cinematic-scene-case-library"
EXPECTED_CASE_HEADINGS = {
    "## Case identity",
    "## Applicability",
    "## Prompt-only evidence (audit only)",
    "## Model-neutral scene pattern",
    "## Downstream handoff",
    "## Forbidden copies",
    "## Reuse, variation, and optimization",
    "## Quality checks",
}
MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".webm", ".mp3", ".wav", ".m4a", ".ogg", ".avi", ".mkv"}


def fail(checks: dict[str, bool], name: str, condition: bool) -> None:
    checks[name] = bool(condition)


def parse_frontmatter(skill_path: Path) -> tuple[dict[str, str], str]:
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields, text[end + 4 :]


def validate(skill_dir: Path = DEFAULT_SKILL_DIR) -> dict[str, object]:
    skill_dir = skill_dir.resolve()
    checks: dict[str, bool] = {}
    skill_path = skill_dir / "SKILL.md"
    yaml_path = skill_dir / "agents" / "openai.yaml"
    index_path = skill_dir / "references" / "index.md"
    schema_path = skill_dir / "references" / "guidance-package-schema.md"
    manifest_path = skill_dir / "references" / "build-manifest.json"

    fail(checks, "skill_exists", skill_path.is_file())
    fail(checks, "openai_yaml_exists", yaml_path.is_file())
    fail(checks, "index_exists", index_path.is_file())
    fail(checks, "schema_exists", schema_path.is_file())
    fail(checks, "manifest_exists", manifest_path.is_file())
    if not all(checks.values()):
        return {"status": "fail", "checks": checks}

    frontmatter, skill_body = parse_frontmatter(skill_path)
    fail(checks, "frontmatter_name", frontmatter.get("name") == "cinematic-scene-case-library")
    fail(checks, "frontmatter_description", bool(frontmatter.get("description")) and "TODO" not in frontmatter.get("description", ""))
    fail(checks, "skill_has_no_todo", "TODO" not in skill_body)
    fail(checks, "skill_links_index", "references/index.md" in skill_body)
    fail(checks, "skill_links_schema", "references/guidance-package-schema.md" in skill_body)

    yaml_text = yaml_path.read_text(encoding="utf-8")
    fail(checks, "openai_display_name", re.search(r"^\s*display_name:\s*\"[^\"]+\"\s*$", yaml_text, re.MULTILINE) is not None)
    short_match = re.search(r"^\s*short_description:\s*\"([^\"]+)\"\s*$", yaml_text, re.MULTILINE)
    fail(checks, "openai_short_description", short_match is not None and 25 <= len(short_match.group(1)) <= 64)
    default_match = re.search(r"^\s*default_prompt:\s*\"([^\"]+)\"\s*$", yaml_text, re.MULTILINE)
    fail(checks, "openai_default_prompt", default_match is not None and "$cinematic-scene-case-library" in default_match.group(1))
    fail(checks, "openai_implicit_policy", "allow_implicit_invocation: true" in yaml_text)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case_files = sorted((skill_dir / "references" / "cases").glob("*.md"))
    fail(checks, "case_count", len(case_files) == manifest.get("selected_case_count") == 24)
    manifest_hashes = manifest.get("case_file_sha256", {})
    actual_hashes: dict[str, str] = {}
    case_ids: list[str] = []
    for path in case_files:
        relative = str(path.relative_to(skill_dir)).replace("\\", "/")
        content = path.read_text(encoding="utf-8")
        actual_hashes[relative] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        heading_lines = {line.strip() for line in content.splitlines() if line.startswith("## ")}
        case_ids.extend(re.findall(r"^# (scene-case-[a-z0-9_-]+)$", content, re.MULTILINE))
        fail(checks, f"case_sections:{path.name}", EXPECTED_CASE_HEADINGS.issubset(heading_lines))
        fail(checks, f"case_no_todo:{path.name}", "TODO" not in content)
        fail(checks, f"case_audit_boundary:{path.name}", "Audit-only source mapping" in content and "Forbidden copies" in content)
        fail(checks, f"case_no_source_prompt_field:{path.name}", "SOURCE_SECRET" not in content and "full_source_prompt:" not in content)
    fail(checks, "case_ids_unique", len(case_ids) == len(set(case_ids)) == 24)
    fail(checks, "manifest_hashes_match", actual_hashes == manifest_hashes)

    index = index_path.read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)]+)\)", index)
    link_targets = [index_path.parent / target for target in links if not target.startswith("http")]
    fail(checks, "index_links_resolve", bool(links) and all(path.is_file() for path in link_targets))
    fail(checks, "index_has_all_case_ids", all(case_id in index for case_id in case_ids))
    fail(checks, "schema_has_ownership", "Ownership rules" in schema_path.read_text(encoding="utf-8"))

    media_files = [path for path in skill_dir.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS]
    fail(checks, "no_media_files", not media_files)
    fail(checks, "no_unfinished_scaffold", all("TODO" not in path.read_text(encoding="utf-8") for path in skill_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".md", ".yaml", ".json"}))
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "case_count": len(case_files),
        "case_ids": case_ids,
        "media_files": [str(path) for path in media_files],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Stage 6 candidate Skill without third-party packages.")
    parser.add_argument("skill_dir", type=Path, nargs="?", default=DEFAULT_SKILL_DIR)
    args = parser.parse_args()
    report = validate(args.skill_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
