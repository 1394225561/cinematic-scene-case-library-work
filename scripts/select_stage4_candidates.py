from __future__ import annotations

import argparse
import re
import sqlite3
from dataclasses import dataclass
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
    / "sample-candidates.json"
)


SIGNAL_PATTERNS = {
    "action": (
        r"\bfight(?:ing)?\b",
        r"\bpunch(?:es|ed|ing)?\b",
        r"\bkick(?:s|ed|ing)?\b",
        r"\bstrike(?:s|n)?\b",
        r"\battack(?:s|ed|ing)?\b",
        r"\bdodg(?:e|es|ed|ing)\b",
        r"\bgrappl(?:e|es|ed|ing)\b",
        r"\bslam(?:s|med|ming)?\b",
        r"\bblade\b",
        r"\bsword\b",
        r"\bweapon\b",
    ),
    "camera": (
        r"\bcamera\b",
        r"\blens\b",
        r"\bshot\b",
        r"\bframing\b",
        r"\bfield of view\b",
        r"\bclose-up\b",
    ),
    "spatial": (
        r"\bscreen[- ]left\b",
        r"\bscreen[- ]right\b",
        r"\bforeground\b",
        r"\bmidground\b",
        r"\bbackground\b",
        r"\bfac(?:e|es|ing)\b",
        r"\bgaze\b",
        r"\bwithin \d+(?:\.\d+)? (?:meter|metre|foot|feet)\b",
    ),
    "physics": (
        r"\bimpact\b",
        r"\binertia\b",
        r"\bweight transfer\b",
        r"\bground contact\b",
        r"\bcollision\b",
        r"\bfriction\b",
        r"\bgravity\b",
        r"\bfollow-through\b",
        r"\bdebris\b",
    ),
    "dialogue": (
        r"\bdialogue\b",
        r"\b(?:says|speaks|shouts|whispers|asks|replies|murmurs)\b",
        r"\blip[- ]sync\b",
        r"\bspoken line\b",
        r"\bvoice\b",
    ),
    "quoted_speech": (
        r"<d>\s*\[[^\]]+\][\s\S]{2,}?</d>",
        r"[\"“][^\"”\r\n]{3,}[\"”]",
    ),
    "performance": (
        r"\bsubtext\b",
        r"\breaction\b",
        r"\beyes?\b",
        r"\bbreath(?:es|ing)?\b",
        r"\bhesitat(?:e|es|ed|ing|ion)\b",
        r"\bexpression\b",
        r"\bposture\b",
        r"\bgesture\b",
    ),
    "environment": (
        r"\bestablishing\b",
        r"\baerial\b",
        r"\benvironment\b",
        r"\bexterior\b",
        r"\binterior\b",
        r"\blandscape\b",
        r"\barchitecture\b",
        r"\blocation\b",
        r"\bgeography\b",
    ),
    "lighting": (
        r"\blighting\b",
        r"\bbacklight\b",
        r"\brim light\b",
        r"\bshadow\b",
        r"\bexposure\b",
        r"\bsunlight\b",
        r"\bmoonlight\b",
        r"\bneon\b",
    ),
    "atmosphere": (
        r"\brain\b",
        r"\bfog\b",
        r"\bsmoke\b",
        r"\bdust\b",
        r"\bsnow\b",
        r"\bwind\b",
        r"\bmist\b",
        r"\bambience\b",
    ),
}

FOLDER_PATTERNS = {
    "action_fight": re.compile(r"fight|attack|battle|\bvs\b|bomb", re.IGNORECASE),
    "environment_establishing": re.compile(
        r"aerial|opening|museum|orphanage|pizzeria|sanctum|roof|environment|location",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class PromptCandidate:
    prompt_sha256: str
    prompt_text: str
    source_prompt_chars: int
    first_asset_id: str
    asset_count: int
    folder_names: tuple[str, ...]
    models: tuple[str, ...]


def contains_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def signal_names(prompt_text: str) -> tuple[str, ...]:
    return tuple(
        name
        for name, patterns in SIGNAL_PATTERNS.items()
        if contains_any(prompt_text, patterns)
    )


def category_dimensions(candidate: PromptCandidate, category: str) -> tuple[str, ...]:
    signals = set(signal_names(candidate.prompt_text))
    folder_text = " | ".join(candidate.folder_names)
    if category == "action_fight":
        dimensions = signals.intersection({"action", "camera", "spatial", "physics"})
        if FOLDER_PATTERNS[category].search(folder_text):
            dimensions.add("action_folder")
        return tuple(sorted(dimensions))
    if category == "dialogue_performance":
        return tuple(
            sorted(
                signals.intersection(
                    {"dialogue", "quoted_speech", "performance", "camera", "spatial"}
                )
            )
        )
    if category == "environment_establishing":
        dimensions = signals.intersection(
            {"environment", "camera", "lighting", "atmosphere", "spatial"}
        )
        if FOLDER_PATTERNS[category].search(folder_text):
            dimensions.add("environment_folder")
        return tuple(sorted(dimensions))
    raise ValueError(f"Unsupported category: {category}")


def qualifies(dimensions: tuple[str, ...], category: str) -> bool:
    present = set(dimensions)
    if category == "action_fight":
        return {"action", "camera", "spatial", "physics", "action_folder"} <= present
    if category == "dialogue_performance":
        return {
            "dialogue",
            "quoted_speech",
            "performance",
            "camera",
            "spatial",
        } <= present
    if category == "environment_establishing":
        return {"environment", "camera", "lighting", "environment_folder"} <= present
    raise ValueError(f"Unsupported category: {category}")


def rank_candidates(
    candidates: Iterable[PromptCandidate],
    category: str,
    *,
    min_chars: int,
    max_chars: int,
    limit: int,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        if not min_chars <= candidate.source_prompt_chars <= max_chars:
            continue
        dimensions = category_dimensions(candidate, category)
        if not qualifies(dimensions, category):
            continue
        excerpt = re.sub(r"\s+", " ", candidate.prompt_text).strip()[:1200]
        ranked.append(
            {
                "prompt_sha256": candidate.prompt_sha256,
                "source_prompt_chars": candidate.source_prompt_chars,
                "first_asset_id": candidate.first_asset_id,
                "asset_count_audit_only": candidate.asset_count,
                "folder_names": list(candidate.folder_names),
                "models": list(candidate.models),
                "coverage_dimensions": list(dimensions),
                "coverage_dimension_count": len(dimensions),
                "prompt_excerpt": excerpt,
            }
        )

    ranked.sort(
        key=lambda row: (-row["coverage_dimension_count"], row["prompt_sha256"])
    )
    return ranked[:limit]


def load_video_prompt_candidates(connection: sqlite3.Connection) -> list[PromptCandidate]:
    rows = connection.execute(
        """
        SELECT p.prompt_sha256, p.prompt_text, p.source_prompt_chars,
               p.first_asset_id, COUNT(DISTINCT a.asset_id) AS asset_count,
               GROUP_CONCAT(DISTINCT COALESCE(f.name, '<unknown>')) AS folder_names,
               GROUP_CONCAT(DISTINCT COALESCE(a.model, '<null>')) AS models
        FROM prompts p
        JOIN assets a ON a.prompt_sha256 = p.prompt_sha256
        LEFT JOIN asset_folder_memberships m ON m.asset_id = a.asset_id
        LEFT JOIN folders f ON f.folder_id = m.folder_id
        WHERE a.asset_type = 'video'
        GROUP BY p.prompt_sha256, p.prompt_text, p.source_prompt_chars, p.first_asset_id
        ORDER BY p.prompt_sha256
        """
    )
    return [
        PromptCandidate(
            prompt_sha256=row[0],
            prompt_text=row[1],
            source_prompt_chars=row[2],
            first_asset_id=row[3],
            asset_count=row[4],
            folder_names=tuple(sorted((row[5] or "<unknown>").split(","))),
            models=tuple(sorted((row[6] or "<null>").split(","))),
        )
        for row in rows
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select auditable Stage 4 normalization candidates without frequency scoring."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--min-chars", type=int, default=500)
    parser.add_argument("--max-chars", type=int, default=30000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")
    if args.min_chars < 0 or args.max_chars < args.min_chars:
        raise SystemExit("Invalid character bounds")

    connection = sqlite3.connect(f"file:{args.database.resolve()}?mode=ro", uri=True)
    try:
        candidates = load_video_prompt_candidates(connection)
    finally:
        connection.close()

    categories = {
        category: rank_candidates(
            candidates,
            category,
            min_chars=args.min_chars,
            max_chars=args.max_chars,
            limit=args.limit,
        )
        for category in (
            "action_fight",
            "dialogue_performance",
            "environment_establishing",
        )
    }
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "policy": (
            "Candidates are ranked only by semantic coverage dimensions and prompt hash. "
            "asset_count_audit_only is never used for ranking or quality inference."
        ),
        "source_database": str(args.database.resolve()),
        "video_unique_prompt_count": len(candidates),
        "character_bounds": {"minimum": args.min_chars, "maximum": args.max_chars},
        "limit_per_category": args.limit,
        "categories": categories,
    }
    write_json_atomic(args.output, report)
    print(
        {
            "video_unique_prompt_count": len(candidates),
            "category_counts": {key: len(value) for key, value in categories.items()},
            "output": str(args.output.resolve()),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
