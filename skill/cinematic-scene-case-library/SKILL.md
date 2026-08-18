---
name: cinematic-scene-case-library
description: "Retrieve and adapt model-neutral cinematic scene patterns for abstract, underspecified, repair, or explicit case-reference requests; do not use it as a final Prompt generator."
---

# Cinematic Scene Case Library

Use this skill as an optional, low-permission retrieval layer for cinematic scene structure. It supplies reusable scene patterns and filtered handoff facts; it does not generate images, videos, media bindings, or final Seedance/H3 Prompts.

## Retrieve only when useful

Retrieve a case when the request is abstract, lacks scene structure, asks to repair a Prompt, or explicitly asks for a case reference. Skip retrieval when the request is already concrete, shootable, and complete enough for the owning director skill. Load the smallest relevant set, normally one case from the [index](references/index.md).

## Workflow

1. Classify the request into one family in the index: action, performance, dialogue, environment, camera, physics/continuity, or mixed scene.
2. Read the selected case file and extract only the model-neutral pattern, variable slots, portable constraints, and the handoff fields needed by the next owner.
3. Treat the Prompt score and all provenance as Prompt-only audit evidence. It is not evidence of rendered-video quality, and no source media was inspected.
4. Apply user-locked facts and target-model rules first. If a case conflicts with either, report the conflict and omit the conflicting suggestion.
5. Return a filtered guidance package using [guidance-package-schema.md](references/guidance-package-schema.md), not a copied case file and not a final Prompt.

## Ownership and isolation

- Seedance path: `cinema-studio-production` may retrieve a case, then pass performance facts to ACTING and spatial/camera/physics/continuity facts to CINEDANCE. `cinedance-seedance-director` owns final Seedance assembly and QA.
- H3 path: `minimax-h3-director` may retrieve a case independently, then owns Context-IR, operation type, real-media labels, official H3 syntax, timing, and final QA. It is not wrapped by `cinema-studio-production`.
- `acting-for-ai-video` owns objective, obstacle, tactics, beats, gaze, listening, delivery, and embodied reaction. This skill does not take that ownership.

Never inject a complete source Prompt, historical `@tag`, source asset ID, media URL, historical duration, model-specific syntax, or unfiltered reference block. Source identifiers appear only in the case file's audit-only provenance section.

## Supporting references

- Read [index.md](references/index.md) for family routing and progressive case loading.
- Read [guidance-package-schema.md](references/guidance-package-schema.md) before returning a retrieval result.
- Read only the one or few linked files needed for the current scene; do not load the full case library by default.
