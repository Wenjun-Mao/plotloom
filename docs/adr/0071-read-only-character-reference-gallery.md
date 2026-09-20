# ADR 0071: Read-only character-reference gallery

Status: Accepted, 2026-09-20.

## Context

F2B already stores cast-owned exploratory reference proposals, their frozen
requests, delivery candidates, explicit reference decisions and immutable
managed assets. Its authoring panel intentionally combines preparation,
handoff, refresh and selection controls with review. That makes image
comparison difficult, although no new persistence or generation contract is
needed.

## Decision

Add `?view=character-reference-review&project=<id>` as a GET-only creator
surface. It composes the existing accepted-cast, character-reference decision,
proposal/delivery and managed-asset read owners directly. Accepted cast supplies
the admitted subject list; decisions supply the selected identity reference;
proposals and deliveries supply candidate state and refinement parent; managed
assets supply bytes. The route does not require a Story Bible, script or
storyboard and persists no selection, gallery state or projection.

The Chinese presentation marks selected-current, merely-current candidate,
historical/stale, missing and failed evidence separately. It exposes a frozen
direction only when the stored proposal's frozen snapshot actually contains it.
IDs, hashes and provenance remain in separate collapsed technical details. The
route has no preparation, generation, refresh, import, selection or disposal
action; existing authoring actions stay in F2B.

## Consequences and guardrails

- A stale or reopened cast is presented as stale evidence rather than silently
  promoted to current; its retained candidates and selections do not become
  usable merely by viewing them.
- Missing managed assets remain visible as missing evidence and are never
  replaced with a substitute image.
- A proposal's currentness and each delivery state remain distinct; a current
  proposal is not a selection, and a delivered output is not creative approval.
- The route links from the existing prototype creator navigation and back while
  retaining separate screenplay and storyboard routes.
