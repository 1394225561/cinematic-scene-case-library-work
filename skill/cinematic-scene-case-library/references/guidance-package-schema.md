# Guidance Package Schema

Version: `stage6-guidance-package-v1`

The case library returns a filtered recommendation package, not a final generation Prompt. The package should contain only the fields needed by the next owner.

## Required fields

```yaml
case_id: scene-case-...
retrieval_reason: abstract_request | missing_structure | prompt_repair | explicit_lookup
applicability: short explanation of why this family fits
prompt_only_evidence:
  score: integer audit value only
  confidence: structural confidence plus limitation
model_neutral_pattern:
  objective: user-specific slot or omitted
  subjects_and_space: user-specific slot or omitted
  beat_chain: user-specific slot or omitted
  camera_physics_continuity: user-specific slot or omitted
acting_handoff: only performance-layer facts
directing_handoff: only space/camera/physics/continuity facts
adapter_notes:
  seedance: boundary guidance only
  h3: boundary guidance only
forbidden_copies: explicit blocked source fields
quality_checks: checks to run before final assembly
```

## Ownership rules

- User-locked facts outrank case suggestions.
- The target model's official rules outrank case suggestions.
- `acting-for-ai-video` owns performance behavior.
- `cinedance-seedance-director` owns final Seedance structure and QA.
- `minimax-h3-director` owns final H3 structure and QA independently.
- This library owns retrieval and abstraction only; it does not generate images, videos, media bindings, or final Prompts.

## Forbidden source material

Never include the complete source Prompt, historical `@tag`, source asset IDs, media URLs, historical timing, model-specific syntax, or unfiltered reference blocks in a downstream guidance package. Source identifiers may appear only in the case file's audit-only provenance section.

## Current build

- Stage 5-2 report digest: `6ea489d7867feca7aaef56b68de00fe1d6c7018dc6a20b6b247c9c14bdcb9c77`
- Selected cases: `24`
- Build policy: Prompt-only evidence; no media inspection.
