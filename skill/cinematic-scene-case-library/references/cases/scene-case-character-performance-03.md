# scene-case-character_performance-03

## Case identity

- Case ID: `scene-case-character_performance-03`
- Pattern family: **Character performance** (`character_performance`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when the main value is a readable objective, reaction, gaze, gesture, or internal shift.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `38eed8353c418d4a5f35e42a54f6601e6a7a2d3f139e108c044dec7457884380`
- Source normalization digest: `82e282bf819c6c0821931ba54cbddb5e3c288a4e9f5f13c2d4ab2925e57316f1`
- Source Prompt character count: `12133` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 20, "continuity": 11, "dialogue_lines": 4, "lighting_segments": 10, "material_references": 5, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `dense_references`, `very_long_prompt`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `02c2b5ed-c263-471d-876c-157a119f3fe7`, `1f4c72a5-0dac-4919-9991-0006f3966a13`, `2248bdaa-7a9c-4bdd-a8d5-22f7b081429b`, `26550ba9-39ca-4989-9359-384a0eae79ff`, `2b45e0dd-c035-44ca-956c-c60355b24222`, `340fde3c-c535-464c-8c95-892f6de7e000`, `52cff48a-ff55-4e92-9128-62d947b76827`, `590b0eef-4f6e-46e3-912a-e2b027932b93`, `737e14a2-f191-482d-8303-56f3998e308f`, `73b6a2f0-9aec-4725-835f-70552e6b99fc`, `74c8c0a8-17ee-4b30-8e41-ec0ce1fbcffa`, `7df5eb85-db63-434e-b00c-985040d8004e`, `7e91c160-21e1-4cb8-906b-1965edec7f8e`, `92ebb68c-61d1-49e9-949a-a6321a5fe331`, `9a995a1d-0131-4c81-bfe8-3c425bc4f4c8`, `a22fec14-607e-4ee3-b604-1772dce67e21`, `acd7c322-1396-48ef-93ab-b92f9008022a`, `af596c3c-679d-4e57-a5fc-70fd996b9381`, `bc2e2a36-fbd3-4ad7-abad-5cd880e55c66`, `bd56f1bb-806c-4344-b1bb-d741214ed5c2`, `c14f7bd4-dfc7-41e0-8af6-8bc92408162f`, `c79ce6a7-c6f3-4ac8-931b-790fe8b73ff3`, `ce471e65-e1f9-4e80-995b-72fb75110b37`, `f111c176-553e-42ae-bd83-e34dd0e2e68c`
- Source folders: `Scene 28`
- Audit-only asset occurrence count: `24`

## Model-neutral scene pattern

Set the performer’s immediate objective and obstacle; give a small sequence of listening, tactic, physical business, and reaction; end on a held readable state rather than generic emotion words.

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
- `obstacle`: [replace with user-locked fact]
- `status`: [replace with user-locked fact]
- `gaze_target`: [replace with user-locked fact]
- `physical_business`: [replace with user-locked fact]
- `tactic_shift`: [replace with user-locked fact]
- `reaction`: [replace with user-locked fact]
- `held_end_state`: [replace with user-locked fact]

### Portable constraints

- Describe observable behavior instead of diagnosing an emotion.
- Make the reaction answer a preceding stimulus.
- Keep identity and performance facts separate from camera instructions.

## Downstream handoff

### ACTING / performance layer

- ACTING owns objective, obstacle, tactics, beats, listening, subtext, gaze, and embodied reaction.
- Use silence, breath, micro-gesture, and status only when they serve the beat.
- Do not let the case supply character identity that the user has not locked.

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

- CINEDANCE/directing owns framing, camera distance, axis, movement, and continuity around the performance.
- Place the performer in a readable relation to the listener or landmark.

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

Send only the performance-layer facts to acting-for-ai-video and the spatial/camera facts to cinedance-seedance-director.

### H3 adapter boundary

Use the performance pattern as optional expert guidance; minimax-h3-director remains the final H3 prompt owner.

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

- The behavior is shootable and externally legible.
- A listener or stimulus exists when a reaction is claimed.
- No claim is made about the rendered acting result.

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
