# scene-case-mixed_scene-02

## Case identity

- Case ID: `scene-case-mixed_scene-02`
- Pattern family: **Mixed scene** (`mixed_scene`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when action, performance, environment, and camera structure all interact and no single family is sufficient.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `bc740ea7c083fa2d4f332cee4c994ff567132aad02e48fbcc765b2b4c49c9947`
- Source normalization digest: `c0dbbb4de28645b7e4c2db4dab2535a6dd4211edbae4fb60272f430d47fa39ab`
- Source Prompt character count: `11481` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 10, "continuity": 8, "dialogue_lines": 4, "lighting_segments": 10, "material_references": 0, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": false, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `high_marker_density`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `063b95e3-0af1-41f4-9deb-2b177ff82496`, `187058aa-33d5-4a13-bb8a-fa986745a3dd`, `6a5f11e9-7813-428b-abf6-ac9db737298a`, `6ba47849-7f8a-44d1-aee7-975d85e825cc`, `6fd34e38-86e1-4a53-92fe-fc7c042a6803`, `85c0b848-e344-48af-9742-a26fed51cfa7`, `c5bb5305-2b80-4682-9684-86b76e8c33dd`, `c8090959-1c69-4d34-a643-ca428f362fb5`, `cfd52767-d9ad-4913-aa53-f56f14f0c40a`, `d3f307fd-50e2-4438-8553-ff621a91c6bc`, `d4b26b30-17c7-4a1e-bf81-9b38dc9b93b7`, `d723081d-f456-471a-9f90-066eea4db1c3`
- Source folders: `Scene 51 Statue Assault`
- Audit-only asset occurrence count: `12`

## Model-neutral scene pattern

Choose one dominant scene objective; layer environment anchor, actor objective, ordered action/performance beats, camera result, and continuity locks around it; remove any detail that does not support the dominant objective.

### Case-specific structural signals

- Declared structure: `single_take`
- Explicit dialogue signal is present; preserve speaker/listener boundaries.
- Performance signal is present; extract observable behavior, not diagnostic emotion labels.
- Normalized action-beat signal count: 14 (count only; source wording is not copied).
- Camera-result signal is present; final framing and syntax remain with the director skill.
- Physics/continuity signal is present; validate causal order and persistent state before assembly.

### Variable slots

- `dominant_objective`: [replace with user-locked fact]
- `environment_anchor`: [replace with user-locked fact]
- `actor_objectives`: [replace with user-locked fact]
- `beat_chain`: [replace with user-locked fact]
- `camera_result`: [replace with user-locked fact]
- `continuity_locks`: [replace with user-locked fact]
- `end_state`: [replace with user-locked fact]

### Portable constraints

- Declare the dominant objective before adding secondary layers.
- Keep ownership boundaries between acting, directing, and model formatting.
- Prefer a compact beat chain over a copied source Prompt.

## Downstream handoff

### ACTING / performance layer

- Extract only performance facts: objective, obstacle, tactic, gaze, listening, and reaction.
- Do not inherit source identities, tags, or incidental prose.

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

- Extract only spatial, camera, physical, and continuity facts.
- Resolve competing anchors and choose one readable camera result.

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

Use as a routing aid only; cinedance-seedance-director owns all final Seedance syntax and QA.

### H3 adapter boundary

Use the abstract layers as optional input; minimax-h3-director independently owns H3 assembly and official constraints.

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

- One objective remains dominant.
- Each downstream handoff receives only its role-specific fields.
- No cross-model syntax or source identifiers leak into the guidance package.

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
