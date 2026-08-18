# Stage 7 Integration Candidates

This directory contains review-only integration artifacts for the optional
`cinematic-scene-case-library` retrieval layer. Nothing here modifies an
installed skill.

## Candidate patches

- [cinema-studio-production.patch.md](cinema-studio-production.patch.md) adds
  optional retrieval to the Seedance orchestration path while leaving final
  Seedance assembly and QA with `cinedance-seedance-director`.
- [minimax-h3-director.patch.md](minimax-h3-director.patch.md) adds the same
  optional retrieval triggers to the independent H3 path while leaving final
  H3 assembly and QA with `minimax-h3-director`.

Each patch is an insertion-only review artifact. Its target anchor and target
file SHA-256 are recorded so Stage 8 can detect drift before applying it.

## Validation artifacts

- [stage7-routing-contract.json](stage7-routing-contract.json) is the shared,
  machine-readable trigger, ownership, field-routing, and isolation contract.
- [representative-tasks.json](representative-tasks.json) contains positive and
  negative routing cases for Seedance and H3.
- `scripts/validate_stage7_integration.py` validates these files together with
  the Stage 6 candidate Skill and the current read-only patch targets.

The fixtures validate orchestration decisions and filtered handoffs. They do
not claim that a rendered video was generated or inspected.
