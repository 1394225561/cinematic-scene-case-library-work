# scene-case-physics_continuity-03

## Case identity

- Case ID: `scene-case-physics_continuity-03`
- Pattern family: **Physics and continuity** (`physics_continuity`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when weight, momentum, contact, trajectories, state persistence, or take continuity is the fragile part.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `97a1c9557ab36e9e55b1bb698bb73660d47621a5897ba99cfa61bce7f9502785`
- Source normalization digest: `0308a659c6e4cff2896715549a147cb928e153383a0d37148d43b55c4b18e2fb`
- Source Prompt character count: `2390` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 7, "camera_segments": 5, "constraints": 3, "continuity": 4, "dialogue_lines": 1, "lighting_segments": 4, "material_references": 0, "performance_segments": 3, "physics_segments": 4, "sound_segments": 3, "spatial_relations": 6, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": false, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `unresolved_reference_occurrence`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `31dde637-5861-4866-9d00-6f985ec083c0`, `7a86dbcf-e0b5-4199-b64f-71ffbcdf93de`, `ac51472c-5b6c-4e92-aa3b-88529b892d64`
- Source folders: `Scene 66`
- Audit-only asset occurrence count: `3`

## Model-neutral scene pattern

Anchor the initial state, force or cause, path/contact, consequence, and persistent end state; keep the camera and subject relation stable enough that the audience can follow the physical chain.

### Case-specific structural signals

- Declared structure: `single_take`
- Explicit dialogue signal is present; preserve speaker/listener boundaries.
- Performance signal is present; extract observable behavior, not diagnostic emotion labels.
- Normalized action-beat signal count: 7 (count only; source wording is not copied).
- Camera-result signal is present; final framing and syntax remain with the director skill.
- Physics/continuity signal is present; validate causal order and persistent state before assembly.
- Source has unresolved reference occurrences; do not invent identity or media bindings.

### Variable slots

- `initial_state`: [replace with user-locked fact]
- `force_or_cause`: [replace with user-locked fact]
- `path_or_contact`: [replace with user-locked fact]
- `physical_consequence`: [replace with user-locked fact]
- `persistent_state`: [replace with user-locked fact]
- `take_or_axis_lock`: [replace with user-locked fact]

### Portable constraints

- Name the state that must persist between beats.
- Use only physical claims that can be staged or observed.
- Separate source conflict warnings from instructions to the target model.

## Downstream handoff

### ACTING / performance layer

- Give performers playable weight, resistance, breath, and recovery cues.
- Reactions must follow contact or force rather than generic emphasis.

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

- Own contact geometry, timing, axis, continuity, and the visual endpoint.
- Treat physics as a constraint to stage, not a claim that the model will solve it.

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

Hand off physical and continuity constraints; cinedance-seedance-director owns Seedance locks and final shot assembly.

### H3 adapter boundary

Pass the causal chain to minimax-h3-director without importing Seedance tags or historical timing.

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

- Cause, path, and consequence form one readable chain.
- Persistent state is named.
- No rendered-physics quality claim is made.

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
