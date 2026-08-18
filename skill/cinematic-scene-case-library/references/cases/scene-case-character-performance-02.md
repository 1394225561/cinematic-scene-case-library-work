# scene-case-character_performance-02

## Case identity

- Case ID: `scene-case-character_performance-02`
- Pattern family: **Character performance** (`character_performance`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when the main value is a readable objective, reaction, gaze, gesture, or internal shift.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `3be1958efd0486b3d5544a004867e4db97a99775a26b098abc0b05138811a59e`
- Source normalization digest: `a9bdd03406de0d6c82d871f9fdc7dd0a014ca0f204457090a0ce87dfc86844f5`
- Source Prompt character count: `9262` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 10, "continuity": 7, "dialogue_lines": 3, "lighting_segments": 10, "material_references": 0, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": false, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `high_marker_density`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `6a89c9fe-3b8a-4c91-9894-7ce5ab0a0741`, `aea3fb61-db7e-4d89-b119-7503903f2652`, `b76ab75c-7fab-42fe-b48e-74a271d142fb`, `c8be16c2-8725-454b-bb56-3a4be584ffa3`
- Source folders: `Scene 51 Statue Assault`
- Audit-only asset occurrence count: `4`

## Model-neutral scene pattern

Set the performer’s immediate objective and obstacle; give a small sequence of listening, tactic, physical business, and reaction; end on a held readable state rather than generic emotion words.

### Case-specific structural signals

- Declared structure: `single_take`
- Explicit dialogue signal is present; preserve speaker/listener boundaries.
- Performance signal is present; extract observable behavior, not diagnostic emotion labels.
- Normalized action-beat signal count: 14 (count only; source wording is not copied).
- Camera-result signal is present; final framing and syntax remain with the director skill.
- Physics/continuity signal is present; validate causal order and persistent state before assembly.

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
