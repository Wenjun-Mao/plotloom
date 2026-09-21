# ADR 0076: Reopened cast cancellation and bounded appearance comparison

**Status:** Accepted

## Context

Opening the accepted-cast editor is a durable F2A transition: it changes the
head to `reopened` and removes the cast identity projection used by F2B. The
old interface offered save only, so locally hiding edits would have falsely
suggested that authority had returned. Separately, a pair-only image comparison
could not support deliberate review of a larger retained gallery.

## Decision

Add a CAS-protected `POST /cast/reopen/cancel` operation. It restores the
existing `accepted` head only when the same accepted revision and its frozen
upstream binding remain current. It writes no new accepted revision and changes
no cast content, mappings, hash, or selection. If upstream context changed, it
rejects and leaves authority unavailable; the UI refreshes that durable stale
state rather than reviving it locally. Cancel, like reopen and save, invalidates
the Characters session before its request.

The appearance gallery retains an unrestricted number of delivered candidates.
Comparison is local presentation state: a creator explicitly adds any two to
four candidates to a review set. It is capped at four, supports removal and
replacement, and never changes the identity-reference decision. Candidate
labels derive from the frozen creator direction, with selected, viewed, and
compared roles shown independently. The local set is discarded when the cast
session or project changes.

## Guardrails

- A stale cancellation cannot restore F2B subject authority.
- There is no fake save, reacceptance, or revision increment on cancellation.
- Gallery size is not limited by the four-image comparison cap.
- The five-image browser proof is an isolated fake-runtime fixture. It uses
  mocked ImageGen delivery evidence to exercise the normal proposal UI and
  proves local comparison/state behavior only; it is not persistent production
  delivery evidence and does not replace separately retained live ImageGen
  proof.

## Evidence-boundary correction — 2026-09-21

The repository also has a truthful project-level managed-image import path, but
the Characters gallery only enumerates character-reference proposal deliveries.
Imported assets are project-scoped and have no character-owned gallery
membership, so they cannot be safely inferred as five unselected appearance
options. A character-scoped imported-appearance association is an unapproved
product seam, not part of this decision or implementation.
