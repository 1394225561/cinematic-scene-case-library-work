# Candidate patch: cinema-studio-production

Status: review only; do not apply before Stage 8 approval.

Target: `C:\Users\Admin\.agents\skills\cinema-studio-production\SKILL.md`

Target SHA-256: `891ddce7d62004900e6e67f5581d6dccfc9713dcc493ae2fc37ec92c26211034`

Insertion anchor: immediately before `## Compose mixed requests`

## Insert this section

```markdown
## Retrieve an optional scene case

Use `$cinematic-scene-case-library` only when the scene request is abstract,
lacks shootable scene structure, asks to repair a Prompt, or explicitly asks
for a case reference. Skip retrieval when the supplied scene is already
concrete, shootable, and complete enough for the owning specialist. This is an
optional retrieval step, not a required specialist in every pipeline.

When retrieval is triggered, resolve the case-library skill from the current
available-skills catalog and follow its progressive-loading instructions.
Load the index, guidance-package schema, and normally one relevant case. Ask it
for a filtered guidance package; never request or forward a complete case file
or source Prompt.

Apply authority in this order: user-locked facts, target-model rules, the
owning specialist's rules and final format, then case guidance. Omit a case
suggestion when it conflicts with a higher authority. Pass only
`acting_handoff` performance facts to ACTING and only `directing_handoff`
space, camera, physics, and continuity facts to CINEDANCE. Keep Seedance
adapter notes for CINEDANCE's final assembly; discard H3 adapter notes.

Never forward historical `@tag` values, source asset IDs, media URLs,
historical duration or generation metadata, source model syntax, provenance,
or Prompt score. Case retrieval does not change ownership: ACTING owns the
performance layer, and CINEDANCE still assembles and QA-checks every complete
Seedance Prompt last.
```

## Integration effect

If retrieval is triggered for a mixed request, run it before the selected
ACTING/CINEDANCE work so that each specialist receives only its role-specific
fragment. The existing `Compose mixed requests`, `Preserve handoffs`, delivery,
and final-check rules remain unchanged.
