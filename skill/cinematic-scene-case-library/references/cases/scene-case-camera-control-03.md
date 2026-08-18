# scene-case-camera_control-03

## Case identity

- Case ID: `scene-case-camera_control-03`
- Pattern family: **Camera control** (`camera_control`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when framing, axis, movement, speed, endpoint, or camera continuity is the missing structure.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `87a6360bace5e638fe02dd760a0386e360fa554073fd9a7164a68396b02fae5d`
- Source normalization digest: `dc75d3de26cd863ebf1601fa1eece441fb4af19b3e9e44e3348112663ded80f7`
- Source Prompt character count: `10123` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 19, "continuity": 8, "dialogue_lines": 1, "lighting_segments": 4, "material_references": 3, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 2}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": true}`
- Source risk flags: `dense_references`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `0beebe16-14ac-48c2-b6b9-0e5644792436`, `16ca5619-1b77-4c4d-9d84-77df9aaec181`, `193a329c-e448-4fc0-a902-735f47680468`, `3e75960f-b289-4500-8cd7-3a8d5bdaa768`, `45df6c42-46ea-427c-b822-6d8b80ec4264`, `5ca6a24a-89b6-4e4c-9830-ae0a7e08d775`, `5cbfe7ca-1d90-4acc-a8f0-69ea8f6cf97c`, `63f330e6-ed0e-45c9-baa1-c1126cfbe9ec`, `7b6899d5-0b00-4767-8d66-a64571735e95`, `886d9121-9bdf-407f-8de5-0577db8a7002`, `ac55092e-0242-4416-870d-d79b1cd5ae20`, `c3120722-29db-4569-831f-1289ef4b95fc`, `ccc5b768-9664-4267-ade3-3796e2b9470d`, `dec96d52-4658-48b9-ae77-c975c8ff373f`, `ded47bf4-4c22-463d-b56d-1029abaa876f`, `f0da9de6-edb5-4c99-9859-ec294332473d`
- Source folders: `Scene 72: Roko vs Dagon`
- Audit-only asset occurrence count: `16`

## Model-neutral scene pattern

Define the starting viewpoint, subject relation, camera movement or hold, speed profile, endpoint, and continuity lock; camera language describes the result, not a list of gear.

### Case-specific structural signals

- Declared structure: `multi_take`
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
