# Candidate patch: minimax-h3-director

Status: review only; do not apply before Stage 8 approval.

Target: `C:\Users\Admin\.agents\skills\minimax-h3-director\SKILL.md`

Target SHA-256: `98296eaab78dc44444ad5f6196e266fb96e62be26dc9dc96280320e2b80b291c`

Insertion anchor: immediately before `## Select the H3 mode`

## Insert this section

```markdown
## Retrieve an optional scene case

Use `$cinematic-scene-case-library` only when the scene request is abstract,
lacks shootable scene structure, asks to repair a Prompt, or explicitly asks
for a case reference. Skip retrieval when the supplied scene is already
concrete, shootable, and complete enough for H3 assembly. Retrieve directly;
never invoke or route this H3 workflow through `$cinema-studio-production`.

When retrieval is triggered, resolve the case-library skill from the current
available-skills catalog and follow its progressive-loading instructions.
Load the index, guidance-package schema, and normally one relevant case. Ask it
for a filtered guidance package; never request or forward a complete case file
or source Prompt.

The source-authority order in this skill remains controlling. Case guidance is
only a transferable cinematic heuristic below user-locked facts, official H3
rules, this orchestrator, and selected expert output. Omit conflicting case
suggestions. Pass only `acting_handoff` performance facts to ACTING when that
specialist is selected. Use `directing_handoff` only as directing input for the
smallest necessary repair path. Keep H3 adapter notes inside this director for
final H3 translation; discard Seedance adapter notes and Seedance output
schema.

Never convert case provenance into active H3 references. Do not forward
historical `@tag` values, source asset IDs, media URLs, historical duration or
generation metadata, source model syntax, provenance, or Prompt score. Only
real supplied assets may receive H3 labels. `minimax-h3-director` still owns
Context-IR, mode selection, timing, official H3 syntax, final assembly, and QA.
```

## Integration effect

Insert optional retrieval after deliverable classification and media inventory
but before optional-specialist selection. The existing H3 reference-loading,
asset-truth, delivery, and final-check rules remain unchanged.
