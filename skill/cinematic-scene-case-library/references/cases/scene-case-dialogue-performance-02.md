# scene-case-dialogue_performance-02

## Case identity

- Case ID: `scene-case-dialogue_performance-02`
- Pattern family: **Dialogue performance** (`dialogue_performance`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when spoken text, delivery, listening, or turn-taking needs scene-level control.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `4877eb3098a4b5b16bb4a0854a26f9fbb0b816dc785d849af179107d903a54d7`
- Source normalization digest: `209205068c7f5acd001cdb888016725ee8acce66d1f7beccc95dcce28a92c4d7`
- Source Prompt character count: `10902` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 15, "continuity": 12, "dialogue_lines": 2, "lighting_segments": 4, "material_references": 4, "performance_segments": 10, "physics_segments": 10, "sound_segments": 9, "spatial_relations": 12, "subjects": 1}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": true}`
- Source risk flags: `dense_references`, `unresolved_reference_occurrence`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `0e09b494-99bf-46e7-bdf5-68dfa1064792`, `11fbe04b-f662-418b-bc3a-a30d5467eb37`, `1584872c-73c9-4f11-9db6-adc3b3064024`, `2653d333-0b8b-4d81-86c0-270e7f2f4e3f`, `38c94d88-6466-4d3d-a2d0-c5a320e18aad`, `38f135b0-8430-4468-a4b9-cd41ff2ce437`, `50d2b0c6-3476-468b-9b99-7ec44510c6bf`, `6ad81b49-0503-46af-b210-c83b3baf2144`, `790828b6-327b-4c3e-ac79-1791db21a4b9`, `7c1ca814-3ccf-4a86-b234-b2a04c544646`, `84a56cbc-9f0d-4348-9a69-0aa75ca86642`, `853690aa-9b83-4b3a-ba50-5e7328c9b890`, `90543b34-9a8c-4a58-9997-52b8d2a49ab6`, `91e42c14-94de-45bc-8923-b1a4110f3bf3`, `9cadca96-da27-4480-baa9-2e41b48e7e46`, `b36fd9af-3ff3-4e86-ad78-ab5a28b9c882`, `b65bd30b-102a-4b8b-8a1b-ba7d1cc4a534`, `c11ffb24-f4ea-4127-a6ff-6a3464c55821`, `cdaf0cb8-b6ec-4c4a-bf95-f95438883eb2`, `d5cb901a-63c3-4acd-96cd-f9cfd426c11d`, `d9590c9d-93e6-401d-94b5-e534ed73f7c2`, `e0a470e8-960e-46a2-ab23-b2b3457a0b63`, `e91cc30f-d664-4cc4-8b08-4c58c04f3666`, `ef6bf4ab-6c7b-463d-b2e5-4a9e6c8351b0`
- Source folders: `Scene 72A`
- Audit-only asset occurrence count: `24`

## Model-neutral scene pattern

Define speaker, listener, objective, line or line slot, delivery, listening response, and the held beat after speech; keep spoken content separate from camera and action formatting.

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

- `speaker`: [replace with user-locked fact]
- `listener`: [replace with user-locked fact]
- `objective`: [replace with user-locked fact]
- `line_or_line_slot`: [replace with user-locked fact]
- `delivery`: [replace with user-locked fact]
- `listening_reaction`: [replace with user-locked fact]
- `held_afterbeat`: [replace with user-locked fact]

### Portable constraints

- Only treat explicitly bounded speech as dialogue.
- Keep delivery and listening behavior observable.
- Do not invent extra lines, ad-libs, subtitles, or offscreen voices.

## Downstream handoff

### ACTING / performance layer

- ACTING owns delivery, subtext, listening, interruption, breath, and afterbeat.
- Specify why the speaker chooses this tactic now.
- Give the listener a playable response even when silent.

Pass only performance facts that belong to ACTING: objective, obstacle, tactics, beats, gaze, listening, delivery, and reaction. Do not pass source identifiers, reference tags, historical timing, or complete source text.

### CINEDANCE / directing layer

- CINEDANCE/directing owns eyelines, shot-reverse-shot logic, mic/camera relation, and continuity.
- Keep the speaking body and reaction body readable in the selected framing.

Pass only spatial, camera, physics, and continuity facts to the owning Seedance director. This case does not assemble the final shot Prompt.

### Seedance adapter boundary

Hand off dialogue behavior, not source wording or tags; cinedance-seedance-director decides final Seedance dialogue structure.

### H3 adapter boundary

Let minimax-h3-director own audio/dialogue syntax, duration, and official H3 mode constraints.

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

- The speaker and listener are unambiguous.
- The line has a playable intention and afterbeat.
- No source Prompt text is copied into a final model prompt by this skill.

- User-locked facts outrank this case reference.
- The target model's official rules outrank this case reference.
- The owning downstream skill must produce and QA the final Prompt.
- If the case conflicts with user facts or target-model rules, report the conflict and omit the conflicting suggestion.
