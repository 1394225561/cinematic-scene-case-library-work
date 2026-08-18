# Cinematic Scene Case Library Index

This index routes optional, model-neutral scene-pattern retrieval. It is not a final Prompt catalog.

## Retrieval policy

- Retrieve a case only for an abstract request, missing scene structure, Prompt repair, or an explicit case lookup.
- Skip retrieval when the request is already concrete, shootable, and complete enough for the owning director skill.
- Load the smallest relevant set, normally one case; do not load every case by default.
- Return a filtered guidance package, never a complete case-file copy and never a final Seedance/H3 Prompt.

## Family routing

| Family | Use when | Cases |
| --- | --- | --- |
| `action_choreography` | Use when a physical interaction needs ordered, causally legible beats. | [scene-case-action_choreography-01](cases/scene-case-action-choreography-01.md), [scene-case-action_choreography-02](cases/scene-case-action-choreography-02.md), [scene-case-action_choreography-03](cases/scene-case-action-choreography-03.md) |
| `action_in_environment` | Use when action must read against a location, landmark, terrain, or atmospheric field. | [scene-case-action_in_environment-01](cases/scene-case-action-in-environment-01.md), [scene-case-action_in_environment-02](cases/scene-case-action-in-environment-02.md), [scene-case-action_in_environment-03](cases/scene-case-action-in-environment-03.md) |
| `character_performance` | Use when the main value is a readable objective, reaction, gaze, gesture, or internal shift. | [scene-case-character_performance-01](cases/scene-case-character-performance-01.md), [scene-case-character_performance-02](cases/scene-case-character-performance-02.md), [scene-case-character_performance-03](cases/scene-case-character-performance-03.md) |
| `dialogue_performance` | Use when spoken text, delivery, listening, or turn-taking needs scene-level control. | [scene-case-dialogue_performance-01](cases/scene-case-dialogue-performance-01.md), [scene-case-dialogue_performance-02](cases/scene-case-dialogue-performance-02.md), [scene-case-dialogue_performance-03](cases/scene-case-dialogue-performance-03.md) |
| `environment_establishing` | Use when a location, atmosphere, architecture, or environmental state must become immediately legible. | [scene-case-environment_establishing-01](cases/scene-case-environment-establishing-01.md), [scene-case-environment_establishing-02](cases/scene-case-environment-establishing-02.md), [scene-case-environment_establishing-03](cases/scene-case-environment-establishing-03.md) |
| `camera_control` | Use when framing, axis, movement, speed, endpoint, or camera continuity is the missing structure. | [scene-case-camera_control-01](cases/scene-case-camera-control-01.md), [scene-case-camera_control-02](cases/scene-case-camera-control-02.md), [scene-case-camera_control-03](cases/scene-case-camera-control-03.md) |
| `physics_continuity` | Use when weight, momentum, contact, trajectories, state persistence, or take continuity is the fragile part. | [scene-case-physics_continuity-01](cases/scene-case-physics-continuity-01.md), [scene-case-physics_continuity-02](cases/scene-case-physics-continuity-02.md), [scene-case-physics_continuity-03](cases/scene-case-physics-continuity-03.md) |
| `mixed_scene` | Use when action, performance, environment, and camera structure all interact and no single family is sufficient. | [scene-case-mixed_scene-01](cases/scene-case-mixed-scene-01.md), [scene-case-mixed_scene-02](cases/scene-case-mixed-scene-02.md), [scene-case-mixed_scene-03](cases/scene-case-mixed-scene-03.md) |

## Handoff routing

- Seedance: `cinema-studio-production` may retrieve a case, then pass only role-specific fragments to ACTING and/or CINEDANCE; CINEDANCE owns final Seedance assembly and QA.
- H3: `minimax-h3-director` may retrieve a case independently, then owns all H3 assembly and QA; it is not wrapped by `cinema-studio-production`.
- Schema: read [guidance-package-schema.md](guidance-package-schema.md) before returning a retrieval result.

## Provenance

- Stage 5-2 input digest: `6ea489d7867feca7aaef56b68de00fe1d6c7018dc6a20b6b247c9c14bdcb9c77`
- Selected case count: `24`
- Media policy: no media was inspected; provenance is Prompt-only and audit-only.
