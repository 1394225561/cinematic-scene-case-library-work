# scene-case-dialogue_performance-01

## Case identity

- Case ID: `scene-case-dialogue_performance-01`
- Pattern family: **Dialogue performance** (`dialogue_performance`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when spoken text, delivery, listening, or turn-taking needs scene-level control.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `45abb83d334903849aef5002ede12ec75a281420223537e632f619ab7b60511e`
- Source normalization digest: `6c64c6558d52c14afeeeec3fb262494d722123b1a74434b66b78bf549863383f`
- Source Prompt character count: `10003` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 12, "continuity": 7, "dialogue_lines": 5, "lighting_segments": 10, "material_references": 0, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 0}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": false, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": false}`
- Source risk flags: `high_marker_density`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `9e68b581-f95b-499d-9092-334cd2b89771`, `e0ae0e5a-b550-43cc-aca6-c43fe48b845a`, `e84ec888-1300-432f-ad86-bb9ecd73abe9`, `fd844310-87e3-4c23-b2c4-5ff56bf358a3`
- Source folders: `Scene 51 Statue Assault`
- Audit-only asset occurrence count: `4`

## Model-neutral scene pattern

Define speaker, listener, objective, line or line slot, delivery, listening response, and the held beat after speech; keep spoken content separate from camera and action formatting.

### Case-specific structural signals

- Declared structure: `single_take`
- Explicit dialogue signal is present; preserve speaker/listener boundaries.
- Performance signal is present; extract observable behavior, not diagnostic emotion labels.
- Normalized action-beat signal count: 14 (count only; source wording is not copied).
- Camera-result signal is present; final framing and syntax remain with the director skill.
- Physics/continuity signal is present; validate causal order and persistent state before assembly.

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
