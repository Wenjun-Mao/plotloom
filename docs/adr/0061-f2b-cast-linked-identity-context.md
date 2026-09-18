# ADR 0061: F2B cast-linked identity context

Status: Accepted, 2026-09-18.

## Context

F2A accepts one upstream-shaped cast revision with an explicit mapping to the
existing Story Bible/media consumer IDs. The existing P1.5 reference owner
previously froze only Story Bible identity facts. That left accepted cast
appearance direction and its revision/hash outside reference, generated-image,
and same-person-review currentness.

## Decision

The existing character-reference context now projects a mapped, current
accepted cast's revision, content hash, character ID, and appearance/image
direction. It remains one small consumer-ID seam: F2B creates neither a Bible,
media store, reference store, nor alternate image workflow. Existing imported
reference originals remain immutable and selectable through the same route.

An accepted cast that is reopened or stale has no current projection. A
reference selected while it was current then fails its frozen context hash;
dependent image jobs and same-person reviews consequently become inapplicable
through their existing currentness checks. The image production snapshot also
retains the accepted-cast projection beside its existing reference lineage.

## Consequences and guardrails

- Cast IDs stay author/model-owned upstream facts, validated as nonblank and
  unique. Trusted code owns the explicit mapping and currentness projection.
- The frozen `characters` handoff instructions repeat that receiving contract
  without changing the vendored upstream schema or skill.
- Cast updates never replace original media bytes or silently rewrite a
  reference selection; a new current selection and review are required.
