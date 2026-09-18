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

F2B exploratory proposals and their explicit reference decisions name `cast`
authority and an accepted cast revision. They resolve the mapped cast subject
directly and freeze its display name, appearance/image direction, revision and
hash without loading a Story Bible. Story-Bible reference decisions name
`story_bible` authority explicitly; requests never fall back between owners.

Prepared or exported cast-reference proposal handoffs have an explicit local
cancellation transition. Cancellation records the operator reason, makes the
proposal non-current, rejects any later copy, and admits a late delivery only
as inapplicable evidence. It does not select a reference or alter canonical
cast/media state.

## Consequences and guardrails

- Cast IDs stay author/model-owned upstream facts, validated as nonblank and
  unique. Trusted code owns the explicit mapping and currentness projection.
- The frozen `characters` handoff instructions repeat that receiving contract
  without changing the vendored upstream schema or skill.
- Cast updates never replace original media bytes or silently rewrite a
  reference selection; a new current selection and review are required.
- F2B studies are exploratory reference evidence only. They do not manufacture
  a Shot binding or satisfy F5/F7 production cross-shot review requirements.
- The cancellation route is available only through the proposal's project and
  leaves the original package and any late-delivery evidence intact.
