# scene-case-dialogue_performance-03

## Case identity

- Case ID: `scene-case-dialogue_performance-03`
- Pattern family: **Dialogue performance** (`dialogue_performance`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when spoken text, delivery, listening, or turn-taking needs scene-level control.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `484651db56efa1ec4a2ee7a99644dad63ead557386caf1ce2d94e18383893359`
- Source normalization digest: `e8ae97894c2dd3cb9c09e38494059d364fed39a0f253eeebbb4a265833e5a6f7`
- Source Prompt character count: `12205` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 20, "continuity": 16, "dialogue_lines": 1, "lighting_segments": 10, "material_references": 3, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `dense_references`, `very_long_prompt`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `01af7efc-9aa4-4012-a88b-93cd7a9e3985`, `0268a615-18d5-477f-a011-92f4abbf96c7`, `153ca2fe-f8f9-46f2-aaf8-ad3887ad304e`, `4d4e767b-ea5a-445d-a1aa-f40d7c10aaae`, `5e2490a2-fff5-42b7-8a79-258a6dbfd5ff`, `665e18ca-6bba-4744-949b-a6488883f1d3`, `6b2d0af9-65fe-42df-be56-9b272842b5de`, `749a6199-8ab3-470e-ae4d-2606cbb1cc81`, `7ba61c01-ec81-4058-9f61-d818011b9d0e`, `7e632e81-f92e-449f-a502-650412e16f55`, `9b7eef26-c44c-48c3-a814-c3a15b60900f`, `a01f81a6-7f87-47c3-923f-93801aee9088`, `a16fba7b-400c-401b-8353-d5258fe3c33c`, `b1963ac2-68a2-4ab4-856c-990365023342`, `b3890e4b-92ef-4bce-ba24-924b12fa9307`, `ba9f3109-9ca1-473c-b7be-d965b090fca6`, `bab4550e-8cbc-4d8c-b976-8413e823ee0f`, `cccf85f3-cf34-4054-a347-9509bbe14934`, `fdd33c28-294f-4127-8f44-95e922296175`, `fec29787-d04d-487d-92a4-1e8d50de635f`
- Source folders: `Scene 72B`
- Audit-only asset occurrence count: `20`

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
