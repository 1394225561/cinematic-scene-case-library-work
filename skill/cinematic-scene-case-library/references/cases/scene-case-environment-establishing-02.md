# scene-case-environment_establishing-02

## Case identity

- Case ID: `scene-case-environment_establishing-02`
- Pattern family: **Environment establishing** (`environment_establishing`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when a location, atmosphere, architecture, or environmental state must become immediately legible.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `5c44b3000b2a446f400fa44863cbb338211f5d3710539fd010c72718dd277393`
- Source normalization digest: `e41c0631d3df962f5995bc7e6de6665cf866ccb860a3218a0442ad584721d214`
- Source Prompt character count: `7754` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 10, "continuity": 12, "dialogue_lines": 2, "lighting_segments": 4, "material_references": 4, "performance_segments": 10, "physics_segments": 10, "sound_segments": 9, "spatial_relations": 12, "subjects": 1}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": true}`
- Source risk flags: `dense_references`, `unresolved_reference_occurrence`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `0b36dc74-052d-4444-811a-164caadfc13c`, `123dd76b-aa05-497a-bfdd-85f584a184b5`, `16f267d5-83de-47d8-a8bd-2be5bb17b500`, `18fed041-0b67-4a72-ab96-eda99cb13345`, `2154d6bf-dd22-43fe-9f30-e783a372cd9a`, `2c07fe83-eb30-476f-b557-38278663dfe0`, `2e3ca931-26f5-4a96-b701-9eae23c31b42`, `6919d563-8ed1-4953-a4ad-e4237a84564e`, `6a170124-9282-487e-bf39-cb3e7f263e40`, `6ba4146a-6232-41a4-90c6-a8fb5e369594`, `75bf2181-38e7-475d-9d75-93b14cf12d06`, `79a652e0-5a58-494d-ae7f-7738fe4d712b`, `82115496-15bd-4885-92ab-9afdfea1d3ec`, `9155d078-ade0-466f-8a9d-cfab14ecbc76`, `9563d9d9-fdf6-4bff-bf8a-d9140f4fe0bf`, `b691c17e-8149-4cf6-874e-7152c6457ec7`, `b7d9ef9b-5510-408b-91e7-314f6406132d`, `d203c547-c032-4669-8797-6c4a6ef777cd`, `d51f305e-64b8-4030-aaa8-9bad6be2e6ec`, `d9eedb09-019c-4fad-8ec3-38d61f587c6c`, `ee13d9f5-8cdd-4b63-85ac-80653b405024`, `f073c7e8-12ef-4997-a803-f31aaa734b69`, `fb087a9d-afd6-4574-953f-ebbd44e06f93`
- Source folders: `Scene 72A`
- Audit-only asset occurrence count: `23`

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
- Source has unresolved reference occurrences; do not invent identity or media bindings.

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
