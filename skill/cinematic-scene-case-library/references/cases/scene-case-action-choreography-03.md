# scene-case-action_choreography-03

## Case identity

- Case ID: `scene-case-action_choreography-03`
- Pattern family: **Action choreography** (`action_choreography`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when a physical interaction needs ordered, causally legible beats.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `19a08b7ded63e6ab827910ab52b05d02a7324cef12535a65b8ad6db3442217e7`
- Source normalization digest: `4d14cbce32e1d364625aaeaea912f88226bd8f47f4544bdfba8085662165eeeb`
- Source Prompt character count: `9310` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 15, "continuity": 7, "dialogue_lines": 2, "lighting_segments": 10, "material_references": 0, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": false, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `high_marker_density`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `0c1bd899-5658-4f8f-8143-75a23505aea9`, `265eaf70-550d-4a1d-bbd6-c34bbbb70aa1`, `4979385f-623a-4c68-bcb5-ad03a9bc0b78`, `6abb6a5a-570a-4723-97c4-b3456506ebd6`, `76f57b5d-d461-4227-9cba-30590830440c`, `79ea6122-f58a-4658-a5f0-7a2e2b6bbeb5`, `7d3d2c08-5de5-458d-9caf-bca748a08eef`, `80511191-263d-4035-bf6d-079a1dd805ee`, `8474f8e9-7d77-4c68-b4ab-d95328800fd7`, `8ac18618-8944-4c7e-b3fb-524780ddaa8f`, `99f032db-4503-4269-bb7b-4ec1d42ab837`, `a76dd2ca-af4c-4808-b3bb-82aef614f0ae`, `abc09790-23a9-4c95-b130-bda3cdeca3ea`, `b5800558-e408-451b-af25-17dfd9c6e3d5`, `bf9aa481-e8f9-42fd-848e-c0446b351df4`, `d6344603-fdab-4e64-8664-899c64b65a45`
- Source folders: `Scene 51 Statue Assault`
- Audit-only asset occurrence count: `16`

## Model-neutral scene pattern

Establish subject roles and spatial relation; stage a readable initiation, response or redirection, and visible end state; keep the action continuous enough to hand off to a shot director.

### Case-specific structural signals

- Declared structure: `single_take`
- Explicit dialogue signal is present; preserve speaker/listener boundaries.
- Performance signal is present; extract observable behavior, not diagnostic emotion labels.
- Normalized action-beat signal count: 14 (count only; source wording is not copied).
- Camera-result signal is present; final framing and syntax remain with the director skill.
- Physics/continuity signal is present; validate causal order and persistent state before assembly.

### Variable slots

- `objective`: [replace with user-locked fact]
- `actor_roles`: [replace with user-locked fact]
- `starting_positions`: [replace with user-locked fact]
- `beat_1`: [replace with user-locked fact]
- `beat_2`: [replace with user-locked fact]
- `beat_3`: [replace with user-locked fact]
- `end_state`: [replace with user-locked fact]

### Portable constraints

- Name the cause before the reaction.
- Keep contact, weight transfer, and recovery legible.
- Preserve the chosen screen geography across beats.

## Downstream handoff

### ACTING / performance layer

- Give each actor an objective and obstacle.
- Specify anticipation, commitment, reaction, and listening after impact.
- Keep gaze and status changes tied to the beat sequence.

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

- Block the axis, subject order, contact points, and endpoint.
- Choose one camera result per beat and protect continuity.
- Resolve physical uncertainty before formatting the final prompt.

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

Pass the abstract beat chain to cinedance-seedance-director; let it own @tag use, shot sections, lock syntax, and final QA.

### H3 adapter boundary

Pass the beat chain to minimax-h3-director; it owns Context-IR, operation type, timing, and official H3 structure.

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

- Every beat changes the physical or dramatic state.
- The final state is observable without relying on a source asset.
- No action is credited solely because the source had many generated assets.

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
