from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


WORK_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = WORK_ROOT / "integration"
SKILL_DIR = WORK_ROOT / "skill" / "cinematic-scene-case-library"
DEFAULT_TARGETS = {
    "seedance": Path(r"C:\Users\Admin\.agents\skills\cinema-studio-production\SKILL.md"),
    "h3": Path(r"C:\Users\Admin\.agents\skills\minimax-h3-director\SKILL.md"),
}
PATCH_FILES = {
    "seedance": INTEGRATION_DIR / "cinema-studio-production.patch.md",
    "h3": INTEGRATION_DIR / "minimax-h3-director.patch.md",
}
PATCH_ANCHORS = {
    "seedance": "## Compose mixed requests",
    "h3": "## Select the H3 mode",
}
STAGE8_MANIFEST = WORK_ROOT / "data" / "runs" / "stage-8-install" / "installation-manifest.json"
REQUIRED_PATCH_PHRASES = {
    "seedance": [
        "$cinematic-scene-case-library",
        "abstract",
        "lacks shootable scene structure",
        "repair a Prompt",
        "explicitly asks for a case reference",
        "already concrete, shootable, and complete",
        "acting_handoff",
        "directing_handoff",
        "CINEDANCE still assembles and QA-checks",
    ],
    "h3": [
        "$cinematic-scene-case-library",
        "abstract",
        "lacks shootable scene structure",
        "repair a Prompt",
        "explicitly asks for a case reference",
        "already concrete, shootable, and complete",
        "never invoke or route this H3 workflow through `$cinema-studio-production`",
        "acting_handoff",
        "directing_handoff",
        "`minimax-h3-director` still owns",
    ],
}
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
AT_TAG_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_-]+")
DURATION_RE = re.compile(r"(?:\b\d+(?:\.\d+)?\s*(?:s|sec|secs|second|seconds)\b|\d+(?:\.\d+)?\s*秒)", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decide_retrieval(signals: list[str], contract: dict[str, Any]) -> dict[str, Any]:
    triggers = contract["retrieval"]["triggers"]
    matched = [trigger for trigger in triggers if trigger in signals]
    if matched:
        return {"retrieve": True, "reason": matched[0]}
    skip_signal = contract["retrieval"]["skip_when"]
    if skip_signal in signals:
        return {"retrieve": False, "reason": skip_signal}
    return {"retrieve": False, "reason": "no_retrieval_trigger"}


def extract_declared_sha256(patch_text: str) -> str | None:
    match = re.search(r"^Target SHA-256: `([0-9a-f]{64})`$", patch_text, re.MULTILINE)
    return match.group(1) if match else None


def extract_patch_section(patch_text: str) -> str:
    match = re.search(r"## Insert this section\s+```markdown\s*(.*?)\s*```", patch_text, re.DOTALL)
    return match.group(1) if match else ""


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_case_catalog() -> tuple[set[str], set[str]]:
    index_text = (SKILL_DIR / "references" / "index.md").read_text(encoding="utf-8")
    families = set(re.findall(r"^\| `([a-z_]+)` \|", index_text, re.MULTILINE))
    case_ids: set[str] = set()
    for path in (SKILL_DIR / "references" / "cases").glob("*.md"):
        match = re.search(r"^# (scene-case-[a-z0-9_-]+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            case_ids.add(match.group(1))
    return families, case_ids


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(flatten_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(flatten_strings(item))
        return strings
    return []


def handoff_violations(handoff: dict[str, Any], target: str) -> list[str]:
    violations: list[str] = []
    payload = "\n".join(
        flatten_strings(
            {
                key: value
                for key, value in handoff.items()
                if key not in {"task_id", "case_id", "final_owner"}
            }
        )
    )
    if UUID_RE.search(payload):
        violations.append("source_asset_id")
    if URL_RE.search(payload):
        violations.append("media_url")
    if AT_TAG_RE.search(payload):
        violations.append("historical_at_tag")
    if DURATION_RE.search(payload):
        violations.append("historical_duration")

    if target == "seedance":
        for token in ("Context-IR", "<Picture 1>", "<Video 1>", "<Audio 1>"):
            if token in payload:
                violations.append(f"h3_syntax:{token}")
    elif target == "h3":
        for token in ("@source_tag", "Seedance adapter", "Seedance output schema"):
            if token in payload:
                violations.append(f"seedance_syntax:{token}")
    return violations


def check(checks: dict[str, bool], name: str, condition: bool) -> None:
    checks[name] = bool(condition)


def validate(targets: dict[str, Path] | None = None) -> dict[str, Any]:
    targets = targets or DEFAULT_TARGETS
    contract = json.loads((INTEGRATION_DIR / "stage7-routing-contract.json").read_text(encoding="utf-8"))
    fixtures = json.loads((INTEGRATION_DIR / "representative-tasks.json").read_text(encoding="utf-8"))
    stage8_manifest: dict[str, Any] = {}
    if STAGE8_MANIFEST.is_file():
        stage8_manifest = json.loads(STAGE8_MANIFEST.read_text(encoding="utf-8-sig"))
    families, case_ids = parse_case_catalog()
    checks: dict[str, bool] = {}
    issues: list[dict[str, str]] = []

    check(checks, "contract_version", contract.get("version") == "stage7-routing-contract-v1")
    check(
        checks,
        "trigger_set",
        contract["retrieval"]["triggers"]
        == ["abstract_request", "missing_structure", "prompt_repair", "explicit_lookup"],
    )
    check(checks, "single_case_default", contract["retrieval"]["maximum_cases_normally_loaded"] == 1)
    check(
        checks,
        "authority_order",
        contract["authority_order"]
        == [
            "user_locked_facts",
            "target_model_official_rules",
            "owning_skill_rules_and_final_format",
            "case_guidance",
        ],
    )
    check(
        checks,
        "final_owners",
        contract["final_owners"]
        == {"seedance": "cinedance-seedance-director", "h3": "minimax-h3-director"},
    )
    check(
        checks,
        "h3_path_is_independent",
        "cinema-studio-production" not in contract["paths"]["h3"]
        and contract["model_isolation"]["h3_forbids_cinema_studio_wrapper"] is True,
    )
    check(
        checks,
        "field_routes_are_role_specific",
        contract["field_routes"]["acting_handoff"] == "acting-for-ai-video"
        and contract["field_routes"]["adapter_notes.seedance"] == "cinedance-seedance-director"
        and contract["field_routes"]["adapter_notes.h3"] == "minimax-h3-director",
    )
    check(checks, "forbidden_fields_complete", len(contract["forbidden_downstream_fields"]) == 9)

    for target, patch_path in PATCH_FILES.items():
        target_path = targets[target]
        patch_text = patch_path.read_text(encoding="utf-8")
        target_text = target_path.read_text(encoding="utf-8") if target_path.is_file() else ""
        declared_sha = extract_declared_sha256(patch_text)
        actual_sha = sha256_file(target_path) if target_path.is_file() else None
        installed_sha = stage8_manifest.get("target_after_sha256", {}).get(target)
        has_installed_section = target_text.count("## Retrieve an optional scene case") == 1
        check(checks, f"patch_target_exists:{target}", target_path.is_file())
        check(
            checks,
            f"patch_target_hash:{target}",
            bool(declared_sha)
            and target_path.is_file()
            and (actual_sha == declared_sha or (has_installed_section and actual_sha == installed_sha)),
        )
        check(checks, f"patch_anchor_unique:{target}", target_text.count(PATCH_ANCHORS[target]) == 1)
        section = extract_patch_section(patch_text)
        check(checks, f"patch_has_single_section:{target}", bool(section) and section.count("## Retrieve an optional scene case") == 1)
        check(
            checks,
            f"patch_required_rules:{target}",
            all(
                normalize_whitespace(phrase) in normalize_whitespace(section)
                for phrase in REQUIRED_PATCH_PHRASES[target]
            ),
        )
        baseline_state = actual_sha == declared_sha and not has_installed_section
        installed_state = has_installed_section and actual_sha == installed_sha
        check(checks, f"patch_target_state:{target}", baseline_state or installed_state)

    tasks = fixtures.get("tasks", [])
    check(checks, "fixture_count", len(tasks) == 10)
    fixture_ids = [task.get("id") for task in tasks]
    check(checks, "fixture_ids_unique", len(fixture_ids) == len(set(fixture_ids)))
    for target in ("seedance", "h3"):
        target_tasks = [task for task in tasks if task.get("target") == target]
        covered = {signal for task in target_tasks for signal in task.get("signals", [])}
        check(
            checks,
            f"fixture_trigger_coverage:{target}",
            set(contract["retrieval"]["triggers"]).issubset(covered),
        )
        check(
            checks,
            f"fixture_skip_coverage:{target}",
            contract["retrieval"]["skip_when"] in covered,
        )

    task_by_id = {task["id"]: task for task in tasks}
    for task in tasks:
        task_id = task["id"]
        expected = task["expected"]
        actual = decide_retrieval(task["signals"], contract)
        check(checks, f"fixture_decision:{task_id}", actual == {"retrieve": expected["retrieve"], "reason": expected["reason"]})
        family = expected.get("family")
        check(checks, f"fixture_family:{task_id}", family is None or family in families)
        expected_count = expected.get("case_count", 0)
        check(
            checks,
            f"fixture_density:{task_id}",
            expected_count == (1 if expected["retrieve"] else 0)
            and expected_count <= contract["retrieval"]["maximum_cases_normally_loaded"],
        )

    handoffs = fixtures.get("filtered_handoffs", [])
    check(checks, "handoff_fixture_targets", len(handoffs) == 2)
    for handoff in handoffs:
        task_id = handoff["task_id"]
        task = task_by_id.get(task_id, {})
        target = task.get("target")
        owner = contract["final_owners"].get(target)
        allowed_payload_keys = {
            "seedance": {"acting-for-ai-video", "cinedance-seedance-director"},
            "h3": {"acting-for-ai-video", "minimax-h3-director"},
        }.get(target, set())
        payload_keys = set(handoff) - {"task_id", "case_id", "final_owner"}
        check(checks, f"handoff_task_retrieves:{task_id}", bool(task) and task["expected"]["retrieve"] is True)
        check(checks, f"handoff_case_exists:{task_id}", handoff["case_id"] in case_ids)
        check(checks, f"handoff_owner:{task_id}", handoff["final_owner"] == owner)
        check(checks, f"handoff_role_keys:{task_id}", payload_keys == allowed_payload_keys)
        item_lists = [value for key, value in handoff.items() if key in payload_keys]
        check(
            checks,
            f"handoff_density:{task_id}",
            all(isinstance(items, list) and 0 < len(items) <= 3 for items in item_lists)
            and sum(len("".join(items)) for items in item_lists) <= 500,
        )
        flattened_lists = [[str(item) for item in items] for items in item_lists]
        duplicate_fragments = set(flattened_lists[0]).intersection(*map(set, flattened_lists[1:])) if len(flattened_lists) > 1 else set()
        check(checks, f"handoff_no_duplicate_fragments:{task_id}", not duplicate_fragments)
        violations = handoff_violations(handoff, target)
        check(checks, f"handoff_no_leakage:{task_id}", not violations)
        for violation in violations:
            issues.append({"task_id": task_id, "issue": violation})

    status = "pass" if all(checks.values()) else "fail"
    return {
        "status": status,
        "contract_version": contract.get("version"),
        "checks": checks,
        "task_count": len(tasks),
        "handoff_fixture_count": len(handoffs),
        "case_catalog_count": len(case_ids),
        "family_count": len(families),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Stage 7 optional case-library integration artifacts.")
    parser.add_argument("--output", type=Path, help="Optional path for the JSON validation report.")
    args = parser.parse_args()
    report = validate()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
