# ADR 0092: Project-scoped Voice Lab and independent published Voice IDs

**Status:** Accepted product direction, 2026-09-26. Implementation pending;
ADR 0091 remains the contract of the currently deployed pilot until this
cutover is verified.

## Context

The first Spark Voice Lab persists casting rounds globally and opens the most
recent one at `/`. Its retained verification audio therefore appears to a new
visitor, even though no generation happens on page load. The owner wants an
empty starting workspace, independently editable named projects, and
candidate-level add/regenerate actions. Plotloom should later accept a Voice
ID directly. Deleting or regenerating a candidate cannot silently break a
voice already referenced by Plotloom.

## Decision

- `/` opens a project chooser, not the newest saved round. A new project starts
  empty. Existing pilot rounds are preserved under an explicitly named pilot
  project during cutover rather than deleted or shown as new-project content.
- A project has an opaque stable `projectId` and an editable display name.
  Its audition line, shared brief, candidate directions and other author text
  are editable drafts. Saving text never changes already generated audio;
  generation snapshots the exact text it used. A project can be renamed,
  switched, and explicitly deleted with its unreferenced media.
- Each candidate slot has a globally unique, stable `candidateId`. Adding a
  candidate or regenerating one schedules only that candidate. Every attempt
  has a distinct immutable generation identity, audio hash, transcript,
  direction, seed and model provenance. A failed replacement leaves the
  previous usable audio intact. After a successful replacement, the old
  *unpublished* candidate WAV is removed and any lab-only selection of it is
  cleared; historical clone results retain their provenance but do not make
  the removed WAV silently current again.
- Publishing a chosen generation creates a separate immutable `voiceId` with
  its own retained audio, transcript, hash and source provenance. Publishing
  does not overwrite an earlier Voice ID. A project may be deleted without
  deleting its published voices; retiring those voices is a distinct explicit
  action with dependency checks. Plotloom can accept `voiceId` as its user
  input and resolve/import the frozen audio by that ID, pinning the hash in
  its own project so Lab availability or later project deletion cannot change
  an existing production reference.
- Project independence is a content boundary, not per-user access control.
  The current Tailnet-only service remains shared and unauthenticated until a
  separate access-control decision is made.

## Alternatives and consequences

Using mutable `candidateId` directly as Plotloom's Voice ID would cause a
regeneration to change the voice behind an existing reference. Retaining every
candidate WAV forever would contradict the owner's replacement preference and
grow storage without a decision. Deleting a published voice with its project
would break downstream work. Separate candidate, generation and published
voice identities preserve selective iteration while making deletion explicit.

The implementation must define project-scoped APIs and UI, a safe migration
for the existing pilot round, atomic replacement/cleanup, and a read-only
published-voice resolution contract. The specialist can build and verify the
Lab side, but the owner has not released the hold on contacting the Plotloom
director or integrating Plotloom itself.

The bounded [implementation plan](../roadmap/2026-09-26-spark-voice-lab-projects-plan.md)
turns this decision into ordered, testable specialist work.
