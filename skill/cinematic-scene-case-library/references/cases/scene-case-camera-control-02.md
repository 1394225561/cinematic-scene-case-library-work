# scene-case-camera_control-02

## Case identity

- Case ID: `scene-case-camera_control-02`
- Pattern family: **Camera control** (`camera_control`)
- Selection status: `selected` by Stage 5-2 Prompt-only review
- This file is a reusable scene-pattern reference, not a final video Prompt.

## Applicability

Use when framing, axis, movement, speed, endpoint, or camera continuity is the missing structure.

Use this case when the request is abstract, structurally incomplete, asks for repair, or explicitly asks for a scene example. Skip retrieval when the user's request is already concrete, shootable, and complete enough for the owning director skill.

## Prompt-only evidence (audit only)

- Prompt SHA-256: `8909c13fd1fb4ca13d66c858b757ba9d11a98084b6db016601412496e977c50d`
- Source normalization digest: `82068bdfba0398c361931ebfbbf31d4da9ebcb69debfef87a98ad958d49e1d08`
- Source Prompt character count: `10036` (audit metadata; never copy as a target length)
- Prompt Content Score: `32/32`; this is structural evidence, not rendered-video quality.
- Minimum dimension score: `4/4`
- Confidence: **high structural confidence**; no source media was inspected.
- Source evidence fields: `action_summary`, `camera_result`, `causal_links`, `constraints`, `continuity`, `continuity_or_constraints`, `dialogue_lines`, `dialogue_scope`, `missing_fields`, `objective`, `performance_segments`, `physics`, `scene_pattern_anchor`, `source_conflicts`, `spatial_relations`, `structure_state`, `subjects_or_environment`, `transferability`
- Normalized signal counts: `{"action_beats": 14, "camera_segments": 10, "constraints": 20, "continuity": 16, "dialogue_lines": 1, "lighting_segments": 10, "material_references": 4, "performance_segments": 10, "physics_segments": 12, "sound_segments": 10, "spatial_relations": 12, "subjects": 1}`
- Normalized field presence: `{"action_beats": true, "camera_segments": true, "constraints": true, "continuity": true, "dialogue_lines": true, "lighting_segments": true, "material_references": true, "performance_segments": true, "physics_segments": true, "sound_segments": true, "spatial_relations": true, "subjects": true}`
- Source risk flags: `dense_references`

### Audit-only source mapping

The following identifiers prove provenance and must never be copied into a downstream generation Prompt, reference tag, or media binding:

- Source asset IDs: `18a4ddc1-5745-44af-b7f8-7f60dcd18739`, `213d78e1-5c8b-4f6d-b60b-b222e09c3a9f`, `25c065fb-153f-4e60-afca-1888c156763f`, `2dd83c0f-6301-4eb4-a55d-52f8110f0129`, `49b31459-87af-4837-b3ed-35a258fdaafc`, `4de97b33-1731-4f84-a706-88878563d96b`, `50948cfc-1e5f-4e4c-b14f-180744587ee7`, `59e69fa9-376d-4f91-9440-e0a8ae1b9010`, `5dedb6c0-cd85-43bf-85e4-26a22944f4b1`, `654742cb-23da-4d3e-9f2f-a6ade79b4f08`, `6ed2f512-f83b-4416-a9dc-3534e46d2c8f`, `719dd597-319d-4ab5-a09b-7ec1d14a5821`, `73088681-81bc-4289-973b-73d67d22317f`, `81718d0c-9c1b-4754-85b1-51e950ad6043`, `84242c47-4fd9-4dea-8e34-2f1610e5a91e`, `87fabad9-b322-4070-9974-510626d40280`, `8a12466a-7301-4079-8c90-031f02ce6cfc`, `a2d342c6-3159-4199-9a74-ce55a997a838`, `abd87579-adc4-418a-9d86-47baa0173699`, `b37e9902-a37d-47f4-afb8-fbfe30d797fb`, `b45007a7-93ab-42a1-ba79-89d58bb5b8b7`, `b889488a-202a-4915-adc4-5f765dd3e347`, `bd5f9cb0-9649-4b75-adad-c09842c5f54f`, `ce17af5c-0584-48c2-a0c1-38ea76219969`, `db0fc12b-1de7-4fdd-b05b-ac2dbf8c5e53`, `dd349971-1cd7-4faa-9a20-bdff52022885`, `df70e5f5-b1d3-4628-aa3f-ef4750982f6a`, `e4d3483c-6b57-4726-86a2-bc2bafe89d21`, `e8938410-c2f2-4cc5-8634-a5e5a5175149`, `e8d1dd4a-712e-4e3a-8a29-84f539099e4d`, `f175142e-6316-44b4-a6c1-13e24d56062a`, `f988c521-4f31-41d4-9cda-ca198bf176dc`
- Source folders: `Scene 72B`
- Audit-only asset occurrence count: `32`

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
