# ADR 0078: Accepted-art subject reference decisions

Status: Accepted, 2026-09-22.

## Context

F3B already owns accepted-art-bound exploratory proposals, verified managed
candidate bytes, and their currentness. It deliberately stops short of a
creator choice, so a gallery can be inspected but cannot truthfully answer
which reference belongs to an accepted environment or prop. Reusing the
character identity decision would wrongly import character context, multiple
assets, reviewer metadata, and downstream image-job meaning into F3B.

## Decision

Add one append-only Art subject reference decision and one mutable CAS state
pointer per `(project, subjectType, subjectId)`. A choice freezes the current
accepted-art revision/content hash, exact current subject content hash, managed
asset identity/original hash, and the originating F3B candidate/proposal. The
write admits only an active project, a current accepted `scene`/`prop`, and a
current accepted F3B candidate for that same subject. The state revision is the
only replacement concurrency token. Viewing and comparison never write.

The decision is historical evidence when its art binding, subject, candidate,
or asset becomes unavailable; it is not silently removed or revived. It is not
a shot/keyframe installation, production reference, F5/F7 approval, import
membership, refinement parent, generation request, or provider dispatch.

## Consequences and guardrails

- The UI may explicitly choose or replace the displayed same-subject candidate
  without reviewer/reason fields. It shows a chosen reference separately from
  the viewed candidate and states that downstream production does not consume
  it yet.
- Reopen, save, art/source currentness loss, cancellation, foreign project or
  subject mismatch, and managed-asset hash mismatch all make the old choice
  non-current. A later callback cannot restore it because the CAS state and
  frozen binding must both match.
- The project-folder schema receives one guarded additive transition for the
  two decision tables. Existing valued folders retain their records; unknown or
  non-immediate schemas remain refused rather than inferred or rewritten.
- No provider, manifest, fixture schema, generalized approval framework, or
  downstream production consumer is added.
