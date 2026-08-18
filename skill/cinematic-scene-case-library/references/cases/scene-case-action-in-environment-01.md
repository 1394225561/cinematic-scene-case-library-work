# scene-case-action_in_environment-01

## Case identity

- Case ID: `scene-case-action_in_environment-01`
- Pattern family: **Action in environment** (`action_in_environment`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when action must read against a location, landmark, terrain, or atmospheric field.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `2889a52ed802235bee0e3e11ffcc8d78e56ba5e0be1e3ad6631e664b4188fbf8`
- Source normalization digest: `0b1f9542f6e3f3c65a8253c9e07c85316366f76b38c804ffe56984df86f8b42c`
- Source Prompt character count: `11705` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 20, "continuity": 16, "dialogue_lines": 1, "lighting_segments": 10, "material_references": 4, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 1}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": true}`
- Source risk flags: `dense_references`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `065dafa2-0d91-4670-b9bd-d5b9efab9907`, `0a104261-b19f-47cd-9080-5e67e1c12206`, `0cd1b3fe-2d58-4878-b991-2121e6afe6db`, `0e18e087-7132-40ea-9a1d-60e5e7bb9bca`, `1526c92b-597f-4869-a783-202fee7d31fa`, `4134867c-5d0a-4409-9dfc-47c66bf3d61f`, `4578a6b1-a1ef-4e7a-a79b-dbc96c2541b0`, `4bfb0419-8058-46fa-87aa-9437210066da`, `53c2f205-d26c-427a-9ec0-044177c3e864`, `53c47f3f-1500-4bab-aa00-a8d4bddd27aa`, `596656e9-214d-48b6-9a82-a596aaa5a8b4`, `5f55dccf-b9a6-4c5d-a6ca-a22bba5974d9`, `65c0c7d5-fa67-42da-b496-b4d21e4ba06d`, `66a6b85b-f451-4cb7-a068-ce4b251d87f8`, `7b4594b6-6831-4793-a2c3-14d099b9282d`, `8870dcd0-fc1e-47ae-a5a4-a8f5dfd85115`, `9702d17a-d204-41d0-8a7a-29abc422ba8f`, `a321d040-565a-407a-8b02-6cde69881e14`, `a39f15d7-0749-4d96-9918-f1834af50b18`, `aa479366-56c7-4593-ae0b-74831a20c2b9`, `b267259f-450b-49fc-b193-990325d7dabd`, `bfcb40fd-7829-4e8a-af16-f291db5f55a7`, `c0bddde4-1958-497b-ab7c-1a88a2627010`, `c12174d4-fb17-458d-b1a8-f15db0260eae`, `c337fc7e-8035-4e19-99a2-1f75ac7f341c`, `c56175cd-8d11-4e31-ac81-8d83073d639f`, `c7ccb404-a40f-48b4-aa2a-202fb9b7f84b`, `c809381d-7588-4506-a078-b0b7391c3df4`, `c839df74-eb03-4b7f-a575-bccd6dcd2291`, `dc420934-1367-4480-a1ec-88c96f6e91a2`, `ee4c5c15-f608-4b30-b548-c92efe596d3b`, `f32bb6bb-14c3-492d-86f6-80610fef6a9e`
- Source folders: `Scene 72B`
- Audit-only asset occurrence count: `32`

## Model-neutral scene pattern

Anchor the action to one stable environmental landmark; define where subjects enter, move, contact, and resolve; let environmental motion affect but not erase the action path.

### Case-specific structural signals

- Declared structure: `single_take`
- Explicit dialogue signal is present; preserve speaker/listener boundaries.
- Performance signal is present; extract observable behavior, not diagnostic emotion labels.
- Normalized action-beat signal count: 14 (count only; source wording is not copied).
- Camera-result signal is present; final framing and syntax remain with the director skill.
- Physics/continuity signal is present; validate causal order and persistent state before assembly.
- Material-reference signal is present; treat source references as audit evidence, not automatic asset bindings.
- Source has dense references; compress them into role-specific facts before handoff.

### Variable slots

- `objective`: [replace with user-locked fact]
- `environment_anchor`: [replace with user-locked fact]
- `terrain_or_space`: [replace with user-locked fact]
- `actor_roles`: [replace with user-locked fact]
- `movement_path`: [replace with user-locked fact]
- `environmental_response`: [replace with user-locked fact]
- `end_state`: [replace with user-locked fact]

### Portable constraints

- Use the landmark as a continuity anchor, not as decorative prose.
- Separate subject movement from background motion.
- State whether the environment constrains, reacts to, or merely frames the action.

## Downstream handoff

### ACTING / performance layer

- Tie each actor's tactic to the environment's affordance or threat.
- Use gaze and footing to show spatial awareness.
- Make reactions proportionate to the environmental change.

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

- Establish landmark proximity and camera side before action beats.
- Protect movement direction and depth order.
- Define how atmospheric motion is layered in foreground, midground, and deep frame when relevant.

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

Keep environment anchors model-neutral until cinedance-seedance-director assigns target-model structure and locks.

### H3 adapter boundary

Let minimax-h3-director map environment anchors into its Context-IR and real-media rules without importing Seedance syntax.

The H3 path remains independent from `cinema-studio-production`; official H3 syntax, Context-IR, real-media labels, mode rules, and 4–15 second limits outrank this case reference.

## Forbidden copies

- The complete source Prompt or unfiltered source fragments.
- Historical `@tag` values, source asset IDs, CDN/media URLs, or hidden reference bindings.
- Historical duration, resolution, model names, or generation metadata as new user facts.
- Seedance-only syntax inside an H3 handoff, or H3-only syntax inside a Seedance handoff.
- Any claim that Prompt Content Score proves rendered video quality.

## Reuse, variation, and optimization

- Reuse: fill only the variable slots supported by the user's locked facts; preserve the family pattern and portable constraints.
- Variation: change one dominant variable at a time (objective, geography, beat order, performance tactic, or camera result) and re-check the causal chain.
- Optimization: shorten the handoff by removing repeated source detail, then let the owning expert add only its required syntax.

## Quality checks

- The landmark remains identifiable after the action begins.
- The action path is spatially traceable.
- Atmosphere does not replace the requested event.

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
