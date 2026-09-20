# ADR 0071: Character-stage image review

Status: Accepted, 2026-09-20.

## Context

F2B already stores cast-owned exploratory reference proposals, their frozen
requests, delivery candidates, explicit reference decisions and immutable
managed assets. Its authoring panel intentionally combines preparation,
handoff, refresh and selection controls with review. That makes image
comparison difficult, although no new persistence or generation contract is
needed.

## Decision

The original decision added a separate GET-only gallery. Review showed it
separated readable images from the decisions a creator came to make. Replace it
with the focused `stage=characters` workspace surface: existing F2A cast text
review followed by the image-first F2B review. It composes the existing
accepted-cast, character-reference decision, proposal/delivery and managed-asset
owners directly. Accepted cast supplies the admitted subject list; decisions
supply the selected identity reference; proposals and deliveries supply candidate
state and refinement parent; managed assets supply bytes. It needs no Story
Bible, script or storyboard and persists no presentation state or projection.

The Chinese presentation marks selected-current, merely-current candidate,
historical/stale, missing and failed evidence separately. It exposes a frozen
direction only when the stored proposal's frozen snapshot actually contains it.
IDs, hashes and provenance remain in separate collapsed technical details.
Ordinary viewing performs only reads. Explicit controls beside the images retain
the existing selection CAS/reviewer/notes request and manual proposal prepare,
copy, refresh and cancel lifecycle. Preparation is only a manual specialist
handoff, not ImageGen dispatch. Reopened or stale cast retains evidence but
disables selection, refinement and preparation.

## Consequences and guardrails

- A stale or reopened cast is presented as stale evidence rather than silently
  promoted to current; its retained candidates and selections do not become
  usable merely by viewing them.
- Missing managed assets remain visible as missing evidence and are never
  replaced with a substitute image.
- A proposal's currentness and each delivery state remain distinct; a current
  proposal is not a selection, and a delivered output is not creative approval.
- Retire the standalone `?view=character-reference-review` destination, its
  duplicate creator-stage navigation and `CastReferenceStudiesPanel`. Reuse its
  image/lineage/status presentation with CastPanel/API owners. Story, Art,
  screenplay, storyboard and Play remain independently owned.

## Acceptance correction — 2026-09-20

The initial gallery presentation did not fully preserve those owners at the
image boundary. A current decision is now the exclusive hero owner: when its
primary asset record is absent or its image cannot be read, the hero states
that selected reference as unavailable and does not substitute a current or
historical candidate. Alternatives remain visible only in their own comparison
cards.

One error-aware asset presentation owns absent metadata and browser HTTP/decode
failure for selected, candidate, complementary, historical, and lineage-parent
images. Its failure state is keyed by project, subject, and asset identity, so
an old failure cannot carry into another subject or project. Gallery fetches
are abortable and invalidate their request owner on unmount and project change.

Refinement lineage is now a recognizable parent card with its image, role, and
focusable link to the parent candidate; unavailable or missing parent evidence
remains explicitly unavailable. These are presentation-only corrections: they
do not change the canonical decision, proposal, delivery, or managed-asset
owners. In the integrated Characters stage, ordinary viewing remains GET-only;
only the explicit decision and handoff controls write through their existing
owners.
