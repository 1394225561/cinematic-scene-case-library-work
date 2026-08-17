# Cinematic Scene Case Library

This context defines the vocabulary for classifying reusable cinematic scene prompts. It separates what can be judged from prompt text and source metadata from claims that would require inspecting generated media.

## Source And Identity

**Source Prompt**:
The immutable original prompt text identified by its SHA-256 hash.
_Avoid_: Generated prompt, final prompt, template

**Exact Prompt Cluster**:
A set of source assets whose Prompt text is byte-for-byte identical and therefore has one source hash.
_Avoid_: Duplicate case, same video, quality group

**Source Asset Mapping**:
The complete relationship from one Exact Prompt Cluster to every source asset ID that used it.
_Avoid_: Evidence of quality, usage score, popularity

**Near-Duplicate Variant**:
A prompt that resembles another prompt after a declared normalization or numeric comparison, but is not automatically merged with it.
_Avoid_: Duplicate, interchangeable prompt

## Scene Meaning

**Scene Tag**:
A non-exclusive label describing a scene signal such as action interaction, character performance, or environment establishing.
_Avoid_: Primary category, single genre

**Scene Taxonomy**:
The multi-label vocabulary used to group prompts by observable scene intent and construction pattern.
_Avoid_: Model category, asset folder

**Scene Pattern**:
A reusable arrangement of objective, subjects, spatial relations, action causality, performance, camera, sound, physics, continuity, and constraints.
_Avoid_: Style preset, final prompt

**Case Tier**:
The selection disposition of a reviewed Scene Pattern: core pattern, effective variant, or special scene.
_Avoid_: Quality grade, media ranking

## Review And Evidence

**Prompt Content Score**:
A score of the prompt's observable construction quality across the approved dimensions, independent of asset counts and uninspected media results.
_Avoid_: Video quality score, generation success score, popularity score

**Evidence Span**:
A source-text range or source-metadata reference that supports a normalized field, score rationale, or classification decision.
_Avoid_: Model output, inferred fact

**Source Conflict**:
Two or more source observations that cannot be resolved without choosing an authority, such as conflicting duration or take structure.
_Avoid_: Parser error, normalized value

**Manual Review Record**:
A prompt whose source evidence is insufficient or damaged for automatic normalization or scoring.
_Avoid_: Failed prompt, excluded prompt

**Prompt-Only Review**:
An explicit review mode in which conclusions are limited to source Prompt text and metadata because generated media bytes were not inspected.
_Avoid_: Media quality review, visual validation
