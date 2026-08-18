# scene-case-action_in_environment-03

## Case identity

- Case ID: `scene-case-action_in_environment-03`
- Pattern family: **Action in environment** (`action_in_environment`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when action must read against a location, landmark, terrain, or atmospheric field.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `2eb89fb8b38854ddf056bbf2ac5741b1ce25a2b91c21e678b8e4a3b2afc73a96`
- Source normalization digest: `d0a378b495967d5a3c8d21a4a66a611286cc846a389fdd8643e1a3831a6fb97e`
- Source Prompt character count: `17273` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 20, "continuity": 16, "dialogue_lines": 3, "lighting_segments": 10, "material_references": 3, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `dense_references`, `very_long_prompt`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `03c72694-ad9a-4e1f-ad07-b92d6178c39f`, `0855d080-793b-4a29-96e2-7a4f0271374c`, `0b82b3f4-0d90-4476-9ada-a5830e3c3a93`, `0c9bf771-1862-4c39-bb2b-faf47d161366`, `1e35e154-66d5-4e3d-b7f3-f87cdd7136cc`, `2427b2c4-d7f7-4c89-818e-cf3453407267`, `25553374-3ad3-42af-879c-33f08290824e`, `27f5c0a9-786d-455e-a2f2-95ab15df901a`, `36e3a583-5614-4660-945e-11d9cc3326d5`, `39898e2d-5ae0-4bec-ab91-41b09ef5a8c1`, `3b08c33a-b8fa-4bc0-af79-249a32704b23`, `4311a097-07e8-4ddd-a88d-0cedb8b2c000`, `489207fe-1d02-4425-b4a3-2395769887ef`, `4fad67cd-7991-49c3-84f6-30a2d10091b2`, `510dad4d-1a4f-4ef6-aca5-7ea5326c5274`, `533e1471-8ccd-42ff-ac55-c99ae135e92a`, `5800cc72-f1ea-4d29-a00a-69e4dba17c9f`, `590d894c-74e6-43de-beb4-a599768b8596`, `6e918ec0-9b75-4f76-84aa-58b38326878c`, `730a11dc-e98a-46f4-902e-e7ee213c74d4`, `74d38bf7-4337-42b5-bf20-28888e320fdf`, `7605b2ac-8253-4828-85a4-501dac6ec1af`, `8177714d-1122-47e2-b982-444f416fa9a1`, `95a447d2-3cdd-4a6b-943d-d44a2728c36b`, `97eccc96-c729-4d7c-a483-fc2d005a39ce`, `af1b73f9-ecbb-4bf5-96af-3aa6e8072267`, `b1779bdc-aecb-44af-9a2a-d175a7f472c5`, `b32424e1-58ab-4b6a-9c10-c2e65fab4e82`, `beaff31f-c111-4f2e-b474-a0ff3b0dbc92`, `bf7e9d67-ace8-49fe-966c-1c97b01a114c`, `c032c8d4-d816-475e-9262-660688cef0ab`, `c6f174e6-c9c9-4084-95ef-baeafaa80c8f`, `cc3f6f5b-00fd-414c-af4c-9d17a1c14b9f`, `cd8b5e70-e894-450c-81fa-29bfa624fcaa`, `d1c6acb9-527f-4e4d-be2f-4e147c0d7bb4`, `d2ea779b-d4b5-4054-b577-88ccc2408de0`, `d8ed186b-198f-4fbc-9e04-2cc87f039eea`, `db5f84a5-f0e8-488c-b6f9-25e829c8ba28`, `e522f17d-1486-4ccc-b593-db8477c3ff00`, `e8ee5bab-ad10-430d-9802-b84c62e619c3`, `f4e6f2ac-10d7-47d7-acdb-c8d678e899a2`, `fc87f06c-c042-4a6c-a824-aede073f2bc4`, `ff2edeaa-b6af-4a1e-bf80-064e7bdd500f`
- Source folders: `Scene 72B`
- Audit-only asset occurrence count: `43`

## Model-neutral scene pattern

Anchor the action to one stable environmental landmark; define where subjects enter, move, contact, and resolve; let environmental motion affect but not erase the action path.

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
