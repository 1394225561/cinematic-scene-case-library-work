from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from probe_higgsfield import utc_now, write_json_atomic


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = WORK_ROOT / "data" / "runs" / "stage-4-normalization"
DEFAULT_SCHEMA = DEFAULT_RUN_DIR / "normalization-schema.json"
DEFAULT_SAMPLES = DEFAULT_RUN_DIR / "normalized-samples.json"
DEFAULT_SOURCES = DEFAULT_RUN_DIR / "selected-source-records.json"
DEFAULT_OUTPUT = DEFAULT_RUN_DIR / "normalization-validation.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def resolve_local_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local JSON Schema references are supported: {ref}")
    value: Any = root_schema
    for segment in ref[2:].split("/"):
        key = segment.replace("~1", "/").replace("~0", "~")
        value = value[key]
    if not isinstance(value, dict):
        raise ValueError(f"Schema reference does not resolve to an object: {ref}")
    return value


def type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate_schema_value(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: str,
) -> list[dict[str, str]]:
    if "$ref" in schema:
        schema = resolve_local_ref(root_schema, schema["$ref"])

    problems: list[dict[str, str]] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(type_matches(value, item) for item in allowed):
            return [
                issue(
                    "schema_type",
                    path,
                    f"Expected type {allowed}, got {type(value).__name__}",
                )
            ]

    if "const" in schema and value != schema["const"]:
        problems.append(issue("schema_const", path, f"Expected {schema['const']!r}"))
    if "enum" in schema and value not in schema["enum"]:
        problems.append(issue("schema_enum", path, f"Unexpected value {value!r}"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            problems.append(issue("schema_min_length", path, "String is too short"))
        pattern = schema.get("pattern")
        if pattern and re.search(pattern, value) is None:
            problems.append(issue("schema_pattern", path, "String does not match pattern"))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            problems.append(issue("schema_minimum", path, "Number is below minimum"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            problems.append(issue("schema_min_items", path, "Array is too short"))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            problems.append(issue("schema_max_items", path, "Array is too long"))
        prefix_items = schema.get("prefixItems", [])
        for index, item_schema in enumerate(prefix_items[: len(value)]):
            problems.extend(
                validate_schema_value(
                    value[index], item_schema, root_schema, f"{path}[{index}]"
                )
            )
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            start = len(prefix_items) if prefix_items else 0
            for index, item in enumerate(value[start:], start=start):
                problems.extend(
                    validate_schema_value(
                        item, item_schema, root_schema, f"{path}[{index}]"
                    )
                )
    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                problems.append(
                    issue("schema_required", f"{path}.{key}", "Required field is missing")
                )
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in properties:
                problems.extend(
                    validate_schema_value(
                        child, properties[key], root_schema, child_path
                    )
                )
            elif additional is False:
                problems.append(
                    issue("schema_additional_property", child_path, "Field is not allowed")
                )
            elif isinstance(additional, dict):
                problems.extend(
                    validate_schema_value(child, additional, root_schema, child_path)
                )
    return problems


def unique(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def all_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from all_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from all_strings(item)


def validate_domain(
    samples: dict[str, Any], sources: dict[str, Any]
) -> list[dict[str, str]]:
    problems: list[dict[str, str]] = []
    records = samples.get("records", [])
    source_records = sources.get("records", [])
    source_by_hash = {record["prompt_sha256"]: record for record in source_records}

    if len(records) != 3:
        problems.append(issue("record_count", "$.records", "Expected exactly 3 samples"))
    if len(source_by_hash) != 3:
        problems.append(
            issue("source_count", "$.source_records", "Expected exactly 3 source records")
        )
    expected_categories = {
        "dialogue_performance",
        "action_fight",
        "environment_establishing",
    }
    actual_categories = {record.get("category") for record in records}
    if actual_categories != expected_categories:
        problems.append(
            issue("category_coverage", "$.records", "Required category coverage is incomplete")
        )

    for index, record in enumerate(records):
        record_path = f"$.records[{index}]"
        record_id = record.get("record_id", f"record-{index}")
        source_layer = record.get("source_layer", {})
        pointer = source_layer.get("source_record", {})
        prompt_hash = pointer.get("prompt_sha256")
        source = source_by_hash.get(prompt_hash)
        if source is None:
            problems.append(
                issue("source_pointer", record_path, f"Unknown source hash for {record_id}")
            )
            continue

        prompt_text = source.get("prompt_text", "")
        calculated_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
        if calculated_hash != prompt_hash:
            problems.append(
                issue("source_hash", record_path, "Source Prompt SHA-256 does not match")
            )
        if len(prompt_text) != source.get("source_prompt_chars"):
            problems.append(
                issue("source_length", record_path, "Source Prompt length does not match")
            )

        if source_layer.get("source_prompt_chars") != source.get("source_prompt_chars"):
            problems.append(
                issue("source_chars", record_path, "Source character count does not match")
            )
        if source_layer.get("first_asset_id") != source.get("first_asset_id"):
            problems.append(
                issue("first_asset", record_path, "First asset ID does not match")
            )

        assets = source.get("assets", [])
        asset_ids = [asset.get("asset_id") for asset in assets]
        if len(asset_ids) != len(set(asset_ids)):
            problems.append(
                issue("source_asset_duplicate", record_path, "Source asset IDs are not unique")
            )
        if source.get("first_asset_id") not in asset_ids:
            problems.append(
                issue("source_first_asset", record_path, "First asset ID is not mapped")
            )
        observations = source_layer.get("asset_metadata_observations", {})
        expected_values = {
            "asset_count": len(assets),
            "duration_seconds_values": unique(
                asset.get("duration_seconds") for asset in assets
            ),
            "model_values": unique(asset.get("model") for asset in assets),
            "resolution_values": unique(asset.get("resolution") for asset in assets),
        }
        for key, expected in expected_values.items():
            if observations.get(key) != expected:
                problems.append(
                    issue(
                        "source_observation",
                        f"{record_path}.source_layer.asset_metadata_observations.{key}",
                        f"Expected {expected!r}",
                    )
                )

        neutral = record.get("model_neutral_scene_layer", {})
        duration = neutral.get("duration", {}).get("value_seconds")
        if duration != record.get("seedance_adapter_layer", {}).get("settings", {}).get(
            "duration_seconds"
        ):
            problems.append(
                issue("duration_drift", record_path, "Seedance duration differs from neutral")
            )
        if duration != record.get("h3_adapter_layer", {}).get("settings", {}).get(
            "duration_seconds"
        ):
            problems.append(
                issue("duration_drift", record_path, "H3 duration differs from neutral")
            )
        if not isinstance(duration, (int, float)) or not 4 <= duration <= 15:
            problems.append(
                issue("h3_duration", record_path, "H3 duration must be 4 to 15 seconds")
            )

        beats = neutral.get("action_beats", [])
        previous_end = 0.0
        for beat_index, beat in enumerate(beats):
            start, end = beat.get("time_range_seconds", [None, None])
            if start != previous_end or not isinstance(end, (int, float)) or end <= start:
                problems.append(
                    issue(
                        "beat_timeline",
                        f"{record_path}.model_neutral_scene_layer.action_beats[{beat_index}]",
                        "Beats must be contiguous and increasing",
                    )
                )
            previous_end = end if isinstance(end, (int, float)) else previous_end
        if beats and previous_end != duration:
            problems.append(
                issue("beat_duration", record_path, "Final beat does not end at duration")
            )

        neutral_text = "\n".join(all_strings(neutral))
        if any(token in neutral_text for token in ("<<<", "@", "<Picture ", "<Subject ")):
            problems.append(
                issue(
                    "neutral_model_syntax",
                    record_path,
                    "Model-specific reference syntax leaked into the neutral layer",
                )
            )

        seedance_prompt = record.get("seedance_adapter_layer", {}).get("prompt", "")
        h3_prompt = record.get("h3_adapter_layer", {}).get("prompt", "")
        if "<<<" in seedance_prompt or re.search(r"(?<!\w)@[A-Za-z0-9_]", seedance_prompt):
            problems.append(
                issue(
                    "seedance_unbound_reference",
                    record_path,
                    "Seedance validation prompt contains an unbound source label",
                )
            )
        if any(
            token in h3_prompt
            for token in ("<Picture ", "<Subject ", "<Video ", "<Audio ")
        ):
            problems.append(
                issue(
                    "h3_fabricated_reference",
                    record_path,
                    "T2VA prompt contains an active H3 media label",
                )
            )
        h3_fields = (
            "integrated_multimodal_description:",
            "overall_soundscape:",
            "non_diegetic_music:",
        )
        positions = [h3_prompt.find(field) for field in h3_fields]
        if positions[0] != 0 or not (positions[0] < positions[1] < positions[2]):
            problems.append(
                issue("h3_structure", record_path, "H3 base fields are missing or out of order")
            )
        for field in h3_fields:
            if h3_prompt.count(field) != 1:
                problems.append(
                    issue("h3_structure", record_path, f"Expected one {field}")
                )

        for dialogue in neutral.get("sound", {}).get("dialogue", []):
            line = dialogue.get("line", "")
            if line not in seedance_prompt or line not in h3_prompt:
                problems.append(
                    issue(
                        "dialogue_drift",
                        record_path,
                        f"Exact dialogue is not preserved: {line!r}",
                    )
                )
            language = dialogue.get("language", "")
            expected_block = f"<d>[{language}] {line}</d>"
            if expected_block not in h3_prompt:
                problems.append(
                    issue(
                        "h3_dialogue_block",
                        record_path,
                        f"Expected exact H3 dialogue block: {expected_block!r}",
                    )
                )

        for conflict in source_layer.get("source_conflicts", []):
            if conflict.get("resolution", {}).get("status") != "resolved":
                problems.append(
                    issue("unresolved_conflict", record_path, "Source conflict is unresolved")
                )

        if record.get("cross_model_validation", {}).get("blocked_items"):
            problems.append(
                issue("blocked_item", record_path, "Sample still contains a blocked item")
            )

    by_category = {record.get("category"): record for record in records}
    action = by_category.get("action_fight", {})
    if len(action.get("model_neutral_scene_layer", {}).get("action_beats", [])) != 5:
        problems.append(issue("action_beat_count", "$.records", "Action must use 5 beats"))
    if action.get("model_neutral_scene_layer", {}).get("duration", {}).get(
        "provenance"
    ) != "user_resolved_source_conflict":
        problems.append(
            issue("action_duration_resolution", "$.records", "Action conflict was not recorded")
        )
    decisions = action.get("adaptation_decisions", [])
    required_user_decisions = {
        "action-duration-resolution",
        "action-five-beat-consolidation",
    }
    actual_user_decisions = {
        item.get("decision_id")
        for item in decisions
        if item.get("authority") == "user_approved"
    }
    if not required_user_decisions <= actual_user_decisions:
        problems.append(
            issue("user_decision_audit", "$.records", "Approved action decisions are missing")
        )

    environment = by_category.get("environment_establishing", {})
    if environment.get("source_layer", {}).get("source_record", {}).get(
        "prompt_sha256"
    ) != "00e4c15e723379bb862770bb9c4a46093978048a29e2426de31e3c39fb512c89":
        problems.append(
            issue("environment_source", "$.records", "Approved environment source is missing")
        )
    if environment.get("model_neutral_scene_layer", {}).get("duration", {}).get(
        "provenance"
    ) != "asset_metadata_only":
        problems.append(
            issue("environment_duration", "$.records", "Environment duration provenance drifted")
        )

    serialized = json.dumps(samples, ensure_ascii=False)
    if "asset_count_audit_only" in serialized:
        problems.append(
            issue("frequency_quality_leak", "$", "Candidate frequency field leaked into samples")
        )
    if re.search(r"https?://", serialized, re.IGNORECASE):
        problems.append(issue("url_leak", "$", "URL found in normalized samples"))
    if re.search(r"\.(?:mp4|mov|webm|png|jpe?g|webp|gif|wav|mp3)\b", serialized, re.I):
        problems.append(issue("media_reference", "$", "Media filename found in samples"))
    total_source_assets = sum(len(record.get("assets", [])) for record in source_records)
    if total_source_assets != 40:
        problems.append(
            issue("source_asset_total", "$.source_records", "Expected 40 mapped assets")
        )
    return problems


def validate_data(
    schema: dict[str, Any], samples: dict[str, Any], sources: dict[str, Any]
) -> list[dict[str, str]]:
    problems: list[dict[str, str]] = []
    for index, record in enumerate(samples.get("records", [])):
        problems.extend(
            validate_schema_value(record, schema, schema, f"$.records[{index}]")
        )
    problems.extend(validate_domain(samples, sources))
    return problems


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Stage 4 normalization samples without third-party packages."
    )
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schema = load_json(args.schema)
    samples = load_json(args.samples)
    sources = load_json(args.sources)
    problems = validate_data(schema, samples, sources)
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "pass" if not problems else "fail",
        "record_count": len(samples.get("records", [])),
        "source_record_count": len(sources.get("records", [])),
        "source_asset_count": sum(
            len(record.get("assets", [])) for record in sources.get("records", [])
        ),
        "issue_count": len(problems),
        "issues": problems,
    }
    write_json_atomic(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
