# scene-case-camera_control-01

## Case identity

- Case ID: `scene-case-camera_control-01`
- Pattern family: **Camera control** (`camera_control`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when framing, axis, movement, speed, endpoint, or camera continuity is the missing structure.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `7bea017cc3e18d34b5a74edb6709a450531fb21b1a72adb0892416d2e2271e29`
- Source normalization digest: `4bf941985e96c24dd49811d627f05d194458e3530c9c00a950acd5a4f9a245f0`
- Source Prompt character count: `8164` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 20, "continuity": 13, "dialogue_lines": 1, "lighting_segments": 10, "material_references": 4, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 1}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": true}`
- Source risk flags: `dense_references`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `187aa59d-3ee3-4269-b74f-2ecf6c32ce10`, `2b2e1d93-bc79-4729-9140-d10b7ddb62ea`, `2c10a4eb-83e5-474f-a455-1358a9cf1b01`, `30fb9f76-8353-4758-b1d0-0efc1fb1889c`, `34290150-b8c8-492f-af98-cb3e86c0d8d8`, `34ce3060-79b8-43b4-9e84-b0825f2e9ed3`, `3742d154-6c56-43d5-8a1a-4b472b3f0d45`, `416e5698-d00a-4ccd-9694-735caf8ab679`, `43472032-7949-444a-9a1a-de2a82245b86`, `5df7a2fe-6e81-47b3-b06d-1bc751d4e4e7`, `69a66711-ca41-428d-a59a-bde8d34fbf99`, `98a10b72-23e7-428d-a0be-c25f9bf9389b`, `adc8d97f-f717-44d8-9acb-924c39bee8cd`, `c12b6ab6-d715-40fb-926f-cea5e1da78a8`, `cde84fe5-fe4e-410e-89ef-d4bff33bba8a`, `dd26bd16-3a3c-4f93-9727-f6bc0f8280d9`
- Source folders: `Scene 72B`
- Audit-only asset occurrence count: `16`

## Model-neutral scene pattern

Define the starting viewpoint, subject relation, camera movement or hold, speed profile, endpoint, and continuity lock; camera language describes the result, not a list of gear.

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

- `starting_frame`: [replace with user-locked fact]
- `axis_and_subject_relation`: [replace with user-locked fact]
- `camera_move_or_hold`: [replace with user-locked fact]
- `speed_profile`: [replace with user-locked fact]
- `endpoint`: [replace with user-locked fact]
- `continuity_lock`: [replace with user-locked fact]

### Portable constraints

- State what the audience sees at the endpoint.
- Keep camera movement consistent with subject geography.
- Use camera terms only when they change the visual result.

## Downstream handoff

### ACTING / performance layer

- ACTING receives only the performance facts needed to play into the camera result.
- Do not let camera vocabulary replace an actor objective or reaction.

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

- CINEDANCE/directing owns final blocking, lens/framing result, camera movement, axis, and continuity.
- Resolve conflicts between camera motion and physical action before final assembly.

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

Do not emit Seedance @tag or chapter syntax here; cinedance-seedance-director is the sole final formatter.

### H3 adapter boundary

Do not import Seedance camera tags; minimax-h3-director chooses H3-compatible camera description and timing.

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

- Start and endpoint are both observable.
- The move has a reason and a stable axis.
- Camera guidance does not claim a rendered result.

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
