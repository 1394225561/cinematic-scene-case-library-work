# scene-case-action_choreography-01

## Case identity

- Case ID: `scene-case-action_choreography-01`
- Pattern family: **Action choreography** (`action_choreography`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when a physical interaction needs ordered, causally legible beats.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `126e93913c44a0b1b94f0763908904ff53c9b7519ee57ac98bbcc6ae7dbdcb11`
- Source normalization digest: `5e7bb89b90ef4c88faa0eabed8c1aa566d5a19270598f3619d6cdcedf5dfe0f2`
- Source Prompt character count: `9805` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 20, "continuity": 16, "dialogue_lines": 1, "lighting_segments": 10, "material_references": 4, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 1}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": true}`
- Source risk flags: `dense_references`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `1258d035-2cac-4a3c-86c3-a491cebbb294`, `29d801b8-1f9b-4842-92d2-e5271dd6d265`, `2a8a43bf-82a4-4b6a-931e-b8c6e4b423b0`, `30deec8e-3ec2-4c9c-ae43-ccc2610868fa`, `34635e2f-901d-45d6-9aaf-86b0fe1e1653`, `41e5065b-8f02-474a-8a53-56c4909b4d4b`, `4612641f-5474-476c-8fa9-af0d3ab329ee`, `46a0726c-4fa7-4c85-88ff-35f1bb285702`, `4a8f824f-92b7-4c78-9664-86f1d558ec49`, `4aab8324-5a10-4871-be13-15c62f1cc1ad`, `4bec225d-21db-4f8c-8ad2-4877a83e0d0d`, `53c84e33-a2cc-48a6-b40e-a42a13f1ee5f`, `56015547-54b7-4d6a-9293-6bb5c6acea1d`, `5d5f9f58-019a-4f56-998b-5734cf9aee5b`, `6727eac4-166f-42d9-a674-c6a3b253bd67`, `892cb861-2a4b-46be-aca0-ce4607def0b8`, `8a25849e-9af0-4d67-875a-2dc20d959508`, `91dc81ec-7447-437b-acb3-7754c44ec242`, `a1232959-e27f-4e18-a966-402921cda353`, `bb8d3b40-252f-4905-84d3-96efbd0f13d2`, `c4b3b522-94f4-4136-9518-9daa5f55b971`, `ce0b5d51-45d7-4c79-8bfb-477b2587a36c`, `ce8889d0-edef-494e-9227-6c705332ef15`, `e95cc36d-85ee-44d1-98d3-c4de59e9b5f5`, `e98b4b73-b3c2-44c8-bad1-3ae8fdcaf4ff`, `ebe9e50e-dfa4-46f0-9ae9-00a2763082e0`, `ee91d140-3e8f-4e36-8c76-72c3a12c13cf`, `ffeb7e19-371a-44a3-875b-76e26aa5160d`
- Source folders: `Scene 72A`
- Audit-only asset occurrence count: `28`

## Model-neutral scene pattern

Establish subject roles and spatial relation; stage a readable initiation, response or redirection, and visible end state; keep the action continuous enough to hand off to a shot director.

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
