from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from normalize_video_prompt_semantics import canonical_json, sha256_text


WORK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FINAL_CASES = WORK_ROOT / "data" / "runs" / "stage-5-2-final-selection" / "final-cases.json"
DEFAULT_FINAL_REPORT = WORK_ROOT / "data" / "runs" / "stage-5-2-final-selection" / "report.json"
DEFAULT_NORMALIZATION_DATABASE = WORK_ROOT / "data" / "runs" / "stage-4b-semantic-normalization-full" / "semantic_normalization.sqlite3"
DEFAULT_SKILL_DIR = WORK_ROOT / "skill" / "cinematic-scene-case-library"
BUILD_VERSION = "stage6-skill-build-v1"

FAMILY_ORDER = (
    "action_choreography",
    "action_in_environment",
    "character_performance",
    "dialogue_performance",
    "environment_establishing",
    "camera_control",
    "physics_continuity",
    "mixed_scene",
)

FAMILY_GUIDANCE: dict[str, dict[str, Any]] = {
    "action_choreography": {
        "label": "Action choreography",
        "trigger": "Use when a physical interaction needs ordered, causally legible beats.",
        "pattern": "Establish subject roles and spatial relation; stage a readable initiation, response or redirection, and visible end state; keep the action continuous enough to hand off to a shot director.",
        "slots": ["objective", "actor_roles", "starting_positions", "beat_1", "beat_2", "beat_3", "end_state"],
        "constraints": ["Name the cause before the reaction.", "Keep contact, weight transfer, and recovery legible.", "Preserve the chosen screen geography across beats."],
        "acting": ["Give each actor an objective and obstacle.", "Specify anticipation, commitment, reaction, and listening after impact.", "Keep gaze and status changes tied to the beat sequence."],
        "directing": ["Block the axis, subject order, contact points, and endpoint.", "Choose one camera result per beat and protect continuity.", "Resolve physical uncertainty before formatting the final prompt."],
        "seedance": "Pass the abstract beat chain to cinedance-seedance-director; let it own @tag use, shot sections, lock syntax, and final QA.",
        "h3": "Pass the beat chain to minimax-h3-director; it owns Context-IR, operation type, timing, and official H3 structure.",
        "checks": ["Every beat changes the physical or dramatic state.", "The final state is observable without relying on a source asset.", "No action is credited solely because the source had many generated assets."],
    },
    "action_in_environment": {
        "label": "Action in environment",
        "trigger": "Use when action must read against a location, landmark, terrain, or atmospheric field.",
        "pattern": "Anchor the action to one stable environmental landmark; define where subjects enter, move, contact, and resolve; let environmental motion affect but not erase the action path.",
        "slots": ["objective", "environment_anchor", "terrain_or_space", "actor_roles", "movement_path", "environmental_response", "end_state"],
        "constraints": ["Use the landmark as a continuity anchor, not as decorative prose.", "Separate subject movement from background motion.", "State whether the environment constrains, reacts to, or merely frames the action."],
        "acting": ["Tie each actor's tactic to the environment's affordance or threat.", "Use gaze and footing to show spatial awareness.", "Make reactions proportionate to the environmental change."],
        "directing": ["Establish landmark proximity and camera side before action beats.", "Protect movement direction and depth order.", "Define how atmospheric motion is layered in foreground, midground, and deep frame when relevant."],
        "seedance": "Keep environment anchors model-neutral until cinedance-seedance-director assigns target-model structure and locks.",
        "h3": "Let minimax-h3-director map environment anchors into its Context-IR and real-media rules without importing Seedance syntax.",
        "checks": ["The landmark remains identifiable after the action begins.", "The action path is spatially traceable.", "Atmosphere does not replace the requested event."],
    },
    "character_performance": {
        "label": "Character performance",
        "trigger": "Use when the main value is a readable objective, reaction, gaze, gesture, or internal shift.",
        "pattern": "Set the performer’s immediate objective and obstacle; give a small sequence of listening, tactic, physical business, and reaction; end on a held readable state rather than generic emotion words.",
        "slots": ["objective", "obstacle", "status", "gaze_target", "physical_business", "tactic_shift", "reaction", "held_end_state"],
        "constraints": ["Describe observable behavior instead of diagnosing an emotion.", "Make the reaction answer a preceding stimulus.", "Keep identity and performance facts separate from camera instructions."],
        "acting": ["ACTING owns objective, obstacle, tactics, beats, listening, subtext, gaze, and embodied reaction.", "Use silence, breath, micro-gesture, and status only when they serve the beat.", "Do not let the case supply character identity that the user has not locked."],
        "directing": ["CINEDANCE/directing owns framing, camera distance, axis, movement, and continuity around the performance.", "Place the performer in a readable relation to the listener or landmark."],
        "seedance": "Send only the performance-layer facts to acting-for-ai-video and the spatial/camera facts to cinedance-seedance-director.",
        "h3": "Use the performance pattern as optional expert guidance; minimax-h3-director remains the final H3 prompt owner.",
        "checks": ["The behavior is shootable and externally legible.", "A listener or stimulus exists when a reaction is claimed.", "No claim is made about the rendered acting result."],
    },
    "dialogue_performance": {
        "label": "Dialogue performance",
        "trigger": "Use when spoken text, delivery, listening, or turn-taking needs scene-level control.",
        "pattern": "Define speaker, listener, objective, line or line slot, delivery, listening response, and the held beat after speech; keep spoken content separate from camera and action formatting.",
        "slots": ["speaker", "listener", "objective", "line_or_line_slot", "delivery", "listening_reaction", "held_afterbeat"],
        "constraints": ["Only treat explicitly bounded speech as dialogue.", "Keep delivery and listening behavior observable.", "Do not invent extra lines, ad-libs, subtitles, or offscreen voices."],
        "acting": ["ACTING owns delivery, subtext, listening, interruption, breath, and afterbeat.", "Specify why the speaker chooses this tactic now.", "Give the listener a playable response even when silent."],
        "directing": ["CINEDANCE/directing owns eyelines, shot-reverse-shot logic, mic/camera relation, and continuity.", "Keep the speaking body and reaction body readable in the selected framing."],
        "seedance": "Hand off dialogue behavior, not source wording or tags; cinedance-seedance-director decides final Seedance dialogue structure.",
        "h3": "Let minimax-h3-director own audio/dialogue syntax, duration, and official H3 mode constraints.",
        "checks": ["The speaker and listener are unambiguous.", "The line has a playable intention and afterbeat.", "No source Prompt text is copied into a final model prompt by this skill."],
    },
    "environment_establishing": {
        "label": "Environment establishing",
        "trigger": "Use when a location, atmosphere, architecture, or environmental state must become immediately legible.",
        "pattern": "Reveal a location through one dominant landmark, scale relation, atmospheric condition, light behavior, and a clear camera viewpoint; hold long enough for the audience to orient.",
        "slots": ["location_type", "dominant_landmark", "scale_cue", "atmosphere", "light_behavior", "camera_viewpoint", "hold_or_transition"],
        "constraints": ["Choose a landmark that can survive the shot transition.", "Separate stable geography from moving atmosphere.", "Avoid adding unrequested landmarks or story facts."],
        "acting": ["If a performer is present, give them a simple relation to the environment rather than a second competing objective.", "Use gaze and posture to reveal scale or threat."],
        "directing": ["Own viewpoint, lens result, horizon/axis, reveal order, and transition point.", "Make foreground, midground, and deep-frame layers intentional."],
        "seedance": "Use the environment pattern as a shot-design input; cinedance-seedance-director owns final camera and syntax decisions.",
        "h3": "Map only the environment intent into H3 Context-IR; minimax-h3-director owns media references and final mode formatting.",
        "checks": ["A viewer can name the location from observable evidence.", "The camera viewpoint is explicit.", "Atmosphere supports orientation instead of obscuring it."],
    },
    "camera_control": {
        "label": "Camera control",
        "trigger": "Use when framing, axis, movement, speed, endpoint, or camera continuity is the missing structure.",
        "pattern": "Define the starting viewpoint, subject relation, camera movement or hold, speed profile, endpoint, and continuity lock; camera language describes the result, not a list of gear.",
        "slots": ["starting_frame", "axis_and_subject_relation", "camera_move_or_hold", "speed_profile", "endpoint", "continuity_lock"],
        "constraints": ["State what the audience sees at the endpoint.", "Keep camera movement consistent with subject geography.", "Use camera terms only when they change the visual result."],
        "acting": ["ACTING receives only the performance facts needed to play into the camera result.", "Do not let camera vocabulary replace an actor objective or reaction."],
        "directing": ["CINEDANCE/directing owns final blocking, lens/framing result, camera movement, axis, and continuity.", "Resolve conflicts between camera motion and physical action before final assembly."],
        "seedance": "Do not emit Seedance @tag or chapter syntax here; cinedance-seedance-director is the sole final formatter.",
        "h3": "Do not import Seedance camera tags; minimax-h3-director chooses H3-compatible camera description and timing.",
        "checks": ["Start and endpoint are both observable.", "The move has a reason and a stable axis.", "Camera guidance does not claim a rendered result."],
    },
    "physics_continuity": {
        "label": "Physics and continuity",
        "trigger": "Use when weight, momentum, contact, trajectories, state persistence, or take continuity is the fragile part.",
        "pattern": "Anchor the initial state, force or cause, path/contact, consequence, and persistent end state; keep the camera and subject relation stable enough that the audience can follow the physical chain.",
        "slots": ["initial_state", "force_or_cause", "path_or_contact", "physical_consequence", "persistent_state", "take_or_axis_lock"],
        "constraints": ["Name the state that must persist between beats.", "Use only physical claims that can be staged or observed.", "Separate source conflict warnings from instructions to the target model."],
        "acting": ["Give performers playable weight, resistance, breath, and recovery cues.", "Reactions must follow contact or force rather than generic emphasis."],
        "directing": ["Own contact geometry, timing, axis, continuity, and the visual endpoint.", "Treat physics as a constraint to stage, not a claim that the model will solve it."],
        "seedance": "Hand off physical and continuity constraints; cinedance-seedance-director owns Seedance locks and final shot assembly.",
        "h3": "Pass the causal chain to minimax-h3-director without importing Seedance tags or historical timing.",
        "checks": ["Cause, path, and consequence form one readable chain.", "Persistent state is named.", "No rendered-physics quality claim is made."],
    },
    "mixed_scene": {
        "label": "Mixed scene",
        "trigger": "Use when action, performance, environment, and camera structure all interact and no single family is sufficient.",
        "pattern": "Choose one dominant scene objective; layer environment anchor, actor objective, ordered action/performance beats, camera result, and continuity locks around it; remove any detail that does not support the dominant objective.",
        "slots": ["dominant_objective", "environment_anchor", "actor_objectives", "beat_chain", "camera_result", "continuity_locks", "end_state"],
        "constraints": ["Declare the dominant objective before adding secondary layers.", "Keep ownership boundaries between acting, directing, and model formatting.", "Prefer a compact beat chain over a copied source Prompt."],
        "acting": ["Extract only performance facts: objective, obstacle, tactic, gaze, listening, and reaction.", "Do not inherit source identities, tags, or incidental prose."],
        "directing": ["Extract only spatial, camera, physical, and continuity facts.", "Resolve competing anchors and choose one readable camera result."],
        "seedance": "Use as a routing aid only; cinedance-seedance-director owns all final Seedance syntax and QA.",
        "h3": "Use the abstract layers as optional input; minimax-h3-director independently owns H3 assembly and official constraints.",
        "checks": ["One objective remains dominant.", "Each downstream handoff receives only its role-specific fields.", "No cross-model syntax or source identifiers leak into the guidance package."],
    },
}

FIELD_KEYS = (
    "subjects",
    "spatial_relations",
    "action_beats",
    "performance_segments",
    "dialogue_lines",
    "camera_segments",
    "lighting_segments",
    "sound_segments",
    "physics_segments",
    "continuity",
    "constraints",
    "material_references",
)


def json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value


def list_value(row: sqlite3.Row, column: str) -> list[Any]:
    value = json_value(row[column], [])
    return value if isinstance(value, list) else []


def dict_value(row: sqlite3.Row, column: str) -> dict[str, Any]:
    value = json_value(row[column], {})
    return value if isinstance(value, dict) else {}


def signal_counts(row: sqlite3.Row) -> dict[str, int]:
    subjects = list_value(row, "subjects_json")
    spatial = list_value(row, "spatial_relations_json")
    action = [item for item in dict_value(row, "action_summary_json").get("beats", []) if isinstance(item, dict)]
    performance = dict_value(row, "performance_dialogue_reaction_json")
    camera = dict_value(row, "camera_result_json").get("segments", [])
    lighting = dict_value(row, "lighting_json").get("segments", [])
    sound = dict_value(row, "sound_json").get("segments", [])
    physics = dict_value(row, "physics_json").get("segments", [])
    return {
        "subjects": len(subjects),
        "spatial_relations": len(spatial),
        "action_beats": len(action),
        "performance_segments": len([item for item in performance.get("performance_segments", []) if isinstance(item, str) and item.strip()]),
        "dialogue_lines": len([item for item in performance.get("dialogue_lines", []) if isinstance(item, dict) and item.get("line")]),
        "camera_segments": len([item for item in camera if isinstance(item, str) and item.strip()]),
        "lighting_segments": len([item for item in lighting if isinstance(item, str) and item.strip()]),
        "sound_segments": len([item for item in sound if isinstance(item, str) and item.strip()]),
        "physics_segments": len([item for item in physics if isinstance(item, str) and item.strip()]),
        "continuity": len(list_value(row, "continuity_json")),
        "constraints": len(list_value(row, "constraints_json")),
        "material_references": len(list_value(row, "material_references_json")),
    }


def field_presence(counts: dict[str, int]) -> dict[str, bool]:
    return {key: counts.get(key, 0) > 0 for key in FIELD_KEYS}


def safe_slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "case"


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def signal_profile(record: dict[str, Any], row: sqlite3.Row, counts: dict[str, int]) -> list[str]:
    profile: list[str] = []
    if record.get("structure_state") in {"single_take", "multi_take"}:
        profile.append(f"Declared structure: `{record['structure_state']}`")
    if counts["dialogue_lines"]:
        profile.append("Explicit dialogue signal is present; preserve speaker/listener boundaries.")
    if counts["performance_segments"]:
        profile.append("Performance signal is present; extract observable behavior, not diagnostic emotion labels.")
    if counts["action_beats"]:
        profile.append(f"Normalized action-beat signal count: {counts['action_beats']} (count only; source wording is not copied).")
    if counts["camera_segments"]:
        profile.append("Camera-result signal is present; final framing and syntax remain with the director skill.")
    if counts["physics_segments"] or counts["continuity"]:
        profile.append("Physics/continuity signal is present; validate causal order and persistent state before assembly.")
    if counts["material_references"]:
        profile.append("Material-reference signal is present; treat source references as audit evidence, not automatic asset bindings.")
    if "dense_references" in (record.get("risk_flags") or []):
        profile.append("Source has dense references; compress them into role-specific facts before handoff.")
    if "unresolved_reference_occurrence" in (record.get("risk_flags") or []):
        profile.append("Source has unresolved reference occurrences; do not invent identity or media bindings.")
    return profile or ["The selected source provides a reusable scene-pattern anchor without a copied source description."]


def render_case(record: dict[str, Any], row: sqlite3.Row) -> str:
    family = record["candidate_family"]
    guidance = FAMILY_GUIDANCE[family]
    counts = signal_counts(row)
    fields = field_presence(counts)
    dimensions = record.get("score_dimensions") or {}
    evidence_fields = sorted(
        {
            field
            for value in dimensions.values()
            if isinstance(value, dict)
            for field in value.get("evidence_fields", [])
            if isinstance(field, str)
        }
    )
    risks = record.get("risk_flags") or []
    confidence = "high structural confidence" if not record.get("source_conflicts") and not record.get("critical_missing_fields") else "limited structural confidence"
    return f"""# {record['case_id']}

## Case identity

- Case ID: `{record['case_id']}`
- Pattern family: **{guidance['label']}** (`{family}`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

{guidance['trigger']}

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `{record['prompt_sha256']}`
- Source normalization digest: `{record['normalization_digest']}`
- Source Prompt character count: `{record['source_prompt_chars']}` (audit metadata; never copy as a target length)
- Prompt Content Score: `{record['prompt_content_score']}/{record['score_maximum']}`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `{min((item.get('score', 0) for item in dimensions.values() if isinstance(item, dict)), default=0)}/4`
- Confidence: **{confidence}**; no source media was inspected.
- Source evidence fields: {', '.join(f'`{item}`' for item in evidence_fields) or 'none'}
- Normalized signal counts: `{json.dumps(counts, sort_keys=True)}`
- Normalized field presence: `{json.dumps(fields, sort_keys=True)}`
- Source risk flags: {', '.join(f'`{item}`' for item in risks) if risks else 'none'}

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: {', '.join(f'`{item}`' for item in record.get('asset_ids', []))}
- Source folders: {', '.join(f'`{item}`' for item in record.get('folder_names', [])) or 'unknown'}
- Audit-only asset occurrence count: `{record.get('asset_count_audit_only', 0)}`

## Model-neutral scene pattern

{guidance['pattern']}

### Case-specific structural signals

{bullets(signal_profile(record, row, counts))}

### Variable slots

{bullets([f'`{slot}`: [replace with user-locked fact]' for slot in guidance['slots']])}

### Portable constraints

{bullets(guidance['constraints'])}

## Downstream handoff

### ACTING / performance layer

{bullets(guidance['acting'])}

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

{bullets(guidance['directing'])}

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

{guidance['seedance']}

### H3 adapter boundary

{guidance['h3']}

The H3 path remains independent from `cinema-studio-production`; official H3 syntax, Context-IR, real-media labels, mode rules, and 4–15 second limits outrank this case reference.

## Forbidden copies

{bullets([
    'The complete source Prompt or unfiltered source fragments.',
    'Historical `@tag` values, source asset IDs, CDN/media URLs, or hidden reference bindings.',
    'Historical duration, resolution, model names, or generation metadata as new user facts.',
    'Seedance-only syntax inside an H3 handoff, or H3-only syntax inside a Seedance handoff.',
    'Any claim that Prompt Content Score proves rendered video quality.',
])}

## Reuse, variation, and optimization

- Reuse: fill only the variable slots supported by the user's locked facts; preserve the family pattern and portable constraints.
- Variation: change one dominant variable at a time (objective, geography, beat order, performance tactic, or camera result) and re-check the causal chain.
- Optimization: shorten the handoff by removing repeated source detail, then let the owning expert add only its required syntax.

## Quality checks

{bullets(guidance['checks'])}

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
"""


def render_index(records: list[dict[str, Any]], report: dict[str, Any]) -> str:
    by_family: dict[str, list[dict[str, Any]]] = {family: [] for family in FAMILY_ORDER}
    for record in records:
        by_family.setdefault(record["candidate_family"], []).append(record)
    lines = [
        "# Cinematic Scene Case Library Index",
        "",
        "This index routes optional, model-neutral scene-pattern retrieval. It is not a final Prompt catalog.",
        "",
        "## Retrieval policy",
        "",
        "- Retrieve a case only for an abstract request, missing scene structure, Prompt repair, or an explicit case lookup.",
        "- Skip retrieval when the request is already concrete, shootable, and complete enough for the owning director skill.",
        "- Load the smallest relevant set, normally one case; do not load every case by default.",
        "- Return a filtered guidance package, never a complete case-file copy and never a final Seedance/H3 Prompt.",
        "",
        "## Family routing",
        "",
        "| Family | Use when | Cases |",
        "| --- | --- | --- |",
    ]
    for family in FAMILY_ORDER:
        guidance = FAMILY_GUIDANCE[family]
        links = ", ".join(
            f"[{record['case_id']}](cases/{safe_slug(record['case_id'])}.md)"
            for record in sorted(by_family.get(family, []), key=lambda item: item["case_id"])
        )
        lines.append(f"| `{family}` | {guidance['trigger']} | {links} |")
    lines.extend(
        [
            "",
            "## Handoff routing",
            "",
            "- Seedance: `cinema-studio-production` may retrieve a case, then pass only role-specific fragments to ACTING and/or CINEDANCE; CINEDANCE owns final Seedance assembly and QA.",
            "- H3: `minimax-h3-director` may retrieve a case independently, then owns all H3 assembly and QA; it is not wrapped by `cinema-studio-production`.",
            "- Schema: read [guidance-package-schema.md](guidance-package-schema.md) before returning a retrieval result.",
            "",
            "## Provenance",
            "",
            f"- Stage 5-2 input digest: `{report.get('input_stage5_2_digest', 'not-recorded')}`",
            f"- Selected case count: `{len(records)}`",
            "- Media policy: no media was inspected; provenance is Prompt-only and audit-only.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_schema(report: dict[str, Any]) -> str:
    return f"""# Guidance Package Schema

Version: `stage6-guidance-package-v1`

The case library returns a filtered recommendation package, not a final generation Prompt. The package should contain only the fields needed by the next owner.

## Required fields

```yaml
case_id: scene-case-...
retrieval_reason: abstract_request | missing_structure | prompt_repair | explicit_lookup
applicability: short explanation of why this family fits
prompt_only_evidence:
  score: integer audit value only
  confidence: structural confidence plus limitation
model_neutral_pattern:
  objective: user-specific slot or omitted
  subjects_and_space: user-specific slot or omitted
  beat_chain: user-specific slot or omitted
  camera_physics_continuity: user-specific slot or omitted
acting_handoff: only performance-layer facts
directing_handoff: only space/camera/physics/continuity facts
adapter_notes:
  seedance: boundary guidance only
  h3: boundary guidance only
forbidden_copies: explicit blocked source fields
quality_checks: checks to run before final assembly
```

## Ownership rules

- User-locked facts outrank case suggestions.
- The target model's official rules outrank case suggestions.
- `acting-for-ai-video` owns performance behavior.
- `cinedance-seedance-director` owns final Seedance structure and QA.
- `minimax-h3-director` owns final H3 structure and QA independently.
- This library owns retrieval and abstraction only; it does not generate images, videos, media bindings, or final Prompts.

## Forbidden source material

Never include the complete source Prompt, historical `@tag`, source asset IDs, media URLs, historical timing, model-specific syntax, or unfiltered reference blocks in a downstream guidance package. Source identifiers may appear only in the case file's audit-only provenance section.

## Current build

- Stage 5-2 report digest: `{report.get('input_stage5_2_digest', 'not-recorded')}`
- Selected cases: `{report.get('selected_case_count', len(report.get('selected_prompt_hashes', [])))}`
- Build policy: Prompt-only evidence; no media inspection.
"""


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def connect_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        connection.close()
        raise RuntimeError(f"integrity_check failed for {path}")
    return connection


def build(
    final_cases_path: Path = DEFAULT_FINAL_CASES,
    final_report_path: Path = DEFAULT_FINAL_REPORT,
    normalization_database: Path = DEFAULT_NORMALIZATION_DATABASE,
    skill_dir: Path = DEFAULT_SKILL_DIR,
) -> dict[str, Any]:
    final_cases_path = final_cases_path.resolve()
    final_report_path = final_report_path.resolve()
    normalization_database = normalization_database.resolve()
    skill_dir = skill_dir.resolve()
    payload = json.loads(final_cases_path.read_text(encoding="utf-8"))
    report = json.loads(final_report_path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if payload.get("schema_version") != 1 or not isinstance(records, list) or not records:
        raise ValueError("final-cases.json must contain a non-empty schema-v1 records list")
    if report.get("status") != "pass":
        raise ValueError("Stage 5-2 report is not passing")
    selected_digest = sha256_text(canonical_json(records))
    if selected_digest != report.get("selected_digest"):
        raise ValueError("Stage 5-2 selected digest mismatch")
    if len({item.get("prompt_sha256") for item in records}) != len(records):
        raise ValueError("selected cases must have unique Prompt hashes")
    if any(item.get("final_status") != "selected" for item in records):
        raise ValueError("final-cases.json contains a non-selected record")

    database = connect_database(normalization_database)
    try:
        hashes = [item["prompt_sha256"] for item in records]
        rows = {
            row["prompt_sha256"]: row
            for row in database.execute(
                f"SELECT * FROM prompt_normalizations WHERE prompt_sha256 IN ({','.join('?' for _ in hashes)})",
                hashes,
            )
        }
        if set(rows) != set(hashes):
            raise ValueError("normalization database does not cover every selected case")
        if any(row["normalization_status"] != "normalized" for row in rows.values()):
            raise ValueError("selected cases must be normalized")

        cases_dir = skill_dir / "references" / "cases"
        cases_dir.mkdir(parents=True, exist_ok=True)
        file_hashes: dict[str, str] = {}
        for record in records:
            content = render_case(record, rows[record["prompt_sha256"]])
            case_path = cases_dir / f"{safe_slug(record['case_id'])}.md"
            atomic_write(case_path, content)
            file_hashes[str(case_path.relative_to(skill_dir)).replace("\\", "/")] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        atomic_write(skill_dir / "references" / "index.md", render_index(records, {**report, "input_stage5_2_digest": report.get("stage5_2_digest")}))
        atomic_write(skill_dir / "references" / "guidance-package-schema.md", render_schema({**report, "input_stage5_2_digest": report.get("stage5_2_digest")}))
        build_manifest = {
            "schema_version": 1,
            "build_version": BUILD_VERSION,
            "stage5_2_digest": report.get("stage5_2_digest"),
            "stage5_2_selected_digest": selected_digest,
            "selected_case_count": len(records),
            "case_ids": [record["case_id"] for record in records],
            "case_file_sha256": dict(sorted(file_hashes.items())),
            "source_policy": "Prompt-only evidence; no media inspected; source identifiers audit-only.",
            "forbidden_injection_fields": ["full_source_prompt", "historical_at_tags", "source_asset_ids", "historical_duration", "model_specific_syntax", "media_urls"],
        }
        atomic_write(skill_dir / "references" / "build-manifest.json", json.dumps(build_manifest, ensure_ascii=False, indent=2) + "\n")
        return build_manifest
    finally:
        database.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Stage 6 cinematic scene case library Skill references.")
    parser.add_argument("--final-cases", type=Path, default=DEFAULT_FINAL_CASES)
    parser.add_argument("--final-report", type=Path, default=DEFAULT_FINAL_REPORT)
    parser.add_argument("--normalization-database", type=Path, default=DEFAULT_NORMALIZATION_DATABASE)
    parser.add_argument("--skill-dir", type=Path, default=DEFAULT_SKILL_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build(args.final_cases, args.final_report, args.normalization_database, args.skill_dir)
    except Exception as error:
        raise SystemExit(str(error)) from error
    print(json.dumps({"status": "pass", "selected_case_count": manifest["selected_case_count"], "skill_dir": str(args.skill_dir.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
