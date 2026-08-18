# scene-case-action_in_environment-02

## Case identity

- Case ID: `scene-case-action_in_environment-02`
- Pattern family: **Action in environment** (`action_in_environment`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when action must read against a location, landmark, terrain, or atmospheric field.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `2be273490eb3403bc97d9608ebaba4afa575c2514a87b3e76c7381a7c935b84c`
- Source normalization digest: `943134bc21608eca4714e647414ad667c4594f081ac6dff9f432cb9ea012f818`
- Source Prompt character count: `11020` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 7, "continuity": 4, "dialogue_lines": 1, "lighting_segments": 10, "material_references": 0, "performance_segments": 9, "physics_segments": 12, "sound_segments": 8, "spatial_relations": 12, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": false, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `high_marker_density`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `3d13a903-06b4-49b9-882a-9da19f35769f`, `4832dc0e-d4f6-4fb5-8ad1-29b7b6e90806`, `514ece7a-41af-45cb-8a2e-07ac0555dd4b`, `c77af197-4621-40b4-ac73-5b442a50b559`
- Source folders: `Scene 51 Statue Assault`
- Audit-only asset occurrence count: `4`

## Model-neutral scene pattern

Anchor the action to one stable environmental landmark; define where subjects enter, move, contact, and resolve; let environmental motion affect but not erase the action path.

### Case-specific structural signals

- Declared structure: `single_take`
- Explicit dialogue signal is present; preserve speaker/listener boundaries.
- Performance signal is present; extract observable behavior, not diagnostic emotion labels.
- Normalized action-beat signal count: 14 (count only; source wording is not copied).
- Camera-result signal is present; final framing and syntax remain with the director skill.
- Physics/continuity signal is present; validate causal order and persistent state before assembly.

### Variable slots

- `objective`: [replace with user-locked fact]
- `environment_anchor`: [replace with user-locked fact]
- `terrain_or_space`: [replace with user-locked fact]
- `actor_roles`: [replace with user-locked fact]
- `movement_path`: [replace with user-locked fact]
- `environmental_response`: [replace with user-locked fact]
- `end_state`: [replace with user-locked fact]

### Portable constraints

- Use the landmark as a continuity anchor, not as decorative prose.
- Separate subject movement from background motion.
- State whether the environment constrains, reacts to, or merely frames the action.

## Downstream handoff

### ACTING / performance layer

- Tie each actor's tactic to the environment's affordance or threat.
- Use gaze and footing to show spatial awareness.
- Make reactions proportionate to the environmental change.

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

- Establish landmark proximity and camera side before action beats.
- Protect movement direction and depth order.
- Define how atmospheric motion is layered in foreground, midground, and deep frame when relevant.

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

Keep environment anchors model-neutral until cinedance-seedance-director assigns target-model structure and locks.

### H3 adapter boundary

Let minimax-h3-director map environment anchors into its Context-IR and real-media rules without importing Seedance syntax.

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

- The landmark remains identifiable after the action begins.
- The action path is spatially traceable.
- Atmosphere does not replace the requested event.

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
