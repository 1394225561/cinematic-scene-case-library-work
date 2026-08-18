# scene-case-environment_establishing-01

## Case identity

- Case ID: `scene-case-environment_establishing-01`
- Pattern family: **Environment establishing** (`environment_establishing`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when a location, atmosphere, architecture, or environmental state must become immediately legible.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `5f865f590962a1c15799ed27fc38d3842acb91c0ec23c131e23b904da53f706f`
- Source normalization digest: `84657b086d97cc3bcfbbbd22e096b0d976a362159705b96f3b346d91aa564559`
- Source Prompt character count: `10249` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 20, "continuity": 9, "dialogue_lines": 2, "lighting_segments": 10, "material_references": 5, "performance_segments": 10, "physics_segments": 10, "sound_segments": 9, "spatial_relations": 12, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `dense_references`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `0d3c71a6-2027-4792-b638-8831c9998861`, `0e9c1646-4565-4b96-a678-5e7d5e0600ba`, `14825f0d-42ed-4f33-9425-a168613efe23`, `18f0d607-01c4-49f7-99b8-fab54a5f6994`, `2322dbd8-b7bb-4eec-9fe1-336bfc929999`, `59946084-9999-47be-9cb7-63a75ff422d2`, `626abc10-aec1-49ac-a67d-3ebae18b591c`, `6d82d2e1-9559-4548-a5b1-5f9437117029`, `6f8c09d3-f247-49d2-9553-6ecab427829c`, `7c3b5796-636c-4905-9f65-4bf6e55f482f`, `84acd61c-95c2-45b0-8962-e68521cb2b00`, `905c6660-5fe3-47ec-9d61-21564f9a5643`, `9847081d-da31-4f3b-943a-75b654e5dd57`, `a13ffa1e-95a8-4cd6-b0ec-6a615596bbc7`, `a6d4b2f1-25a3-495d-95ac-f5f71658039f`, `af2a0410-9a25-4398-8e2c-5add73e2564c`
- Source folders: `Scene 28`
- Audit-only asset occurrence count: `16`

## Model-neutral scene pattern

Reveal a location through one dominant landmark, scale relation, atmospheric condition, light behavior, and a clear camera viewpoint; hold long enough for the audience to orient.

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

- `location_type`: [replace with user-locked fact]
- `dominant_landmark`: [replace with user-locked fact]
- `scale_cue`: [replace with user-locked fact]
- `atmosphere`: [replace with user-locked fact]
- `light_behavior`: [replace with user-locked fact]
- `camera_viewpoint`: [replace with user-locked fact]
- `hold_or_transition`: [replace with user-locked fact]

### Portable constraints

- Choose a landmark that can survive the shot transition.
- Separate stable geography from moving atmosphere.
- Avoid adding unrequested landmarks or story facts.

## Downstream handoff

### ACTING / performance layer

- If a performer is present, give them a simple relation to the environment rather than a second competing objective.
- Use gaze and posture to reveal scale or threat.

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

- Own viewpoint, lens result, horizon/axis, reveal order, and transition point.
- Make foreground, midground, and deep-frame layers intentional.

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

Use the environment pattern as a shot-design input; cinedance-seedance-director owns final camera and syntax decisions.

### H3 adapter boundary

Map only the environment intent into H3 Context-IR; minimax-h3-director owns media references and final mode formatting.

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

- A viewer can name the location from observable evidence.
- The camera viewpoint is explicit.
- Atmosphere supports orientation instead of obscuring it.

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
