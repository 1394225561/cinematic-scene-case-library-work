# scene-case-environment_establishing-03

## Case identity

- Case ID: `scene-case-environment_establishing-03`
- Pattern family: **Environment establishing** (`environment_establishing`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when a location, atmosphere, architecture, or environmental state must become immediately legible.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `72a5cfe70d955aaac61cd622a69bcac2cc37bcb03e9e699ad945cb484f036168`
- Source normalization digest: `c3cf6b512dc4724d51000310db5d1f591e0fb2047567a21246282803424d0975`
- Source Prompt character count: `17750` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 20, "continuity": 16, "dialogue_lines": 5, "lighting_segments": 10, "material_references": 3, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 2}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": true}`
- Source risk flags: `dense_references`, `very_long_prompt`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `161503f3-8b89-4b4f-9e15-3dae22dd97a2`, `2d59ed04-b25f-40b7-9826-27522ba81867`, `440dad98-d318-43d4-81f6-187339f69378`, `f6195f6f-2a73-42dd-8a31-0a7746311653`
- Source folders: `Scene 36`
- Audit-only asset occurrence count: `4`

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
