# ADR 0191: Whole-pack human material confirmation

Status: accepted for implementation, 2026-10-17, under the approved
[delivery plan](../roadmap/2026-10-17-bulk-material-review.md).

Owner clarification, 2026-10-18: identified incompatible development projects
are disposable without backup/recovery; compatible data can remain. Do not add
compatibility/migration machinery solely for this data. The current JSON change
needs no reset or new historical adapter; supported existing readers stay intact.

## Problem

The current gallery requires authored intent, compatibility and character prose
for every frame. These requirements belong to the shared request, persistence
and receipt contract, not merely the UI. Filling them automatically would claim
observations the creator never wrote (ADR 0162).

## Decision

Add a distinct `pre-video.handoff.v3` whole-pack assertion. Its explicit final
action endorses the exact displayed references, ordered frames, saved intent
context and visible-character identity/state. Frame failures and unresolved
flags block the atomic transaction. Unassessable identity retains ADR 0146's
separate reason and hold/authorize choice. Opening the gallery grants no authority.

The new typed judgments store no invented notes or reviewer. Empty SQL note
values are permitted only with exact validated v3 receipt links. Comparison JSON
binds its assertion to receipt, bundle and shot. Shared binding/review admission
checks that receipt's historical shape and native links, separately from current
eligibility; historical receipt validation never calls admission, avoiding a
receipt → review → receipt recursion. Existing detailed requests stay strict;
supported v1/v2 receipts remain immutable and readable. No SQL migration.

Each current gallery frame includes either its complete exact saved intent
(ID, revision, hash and payload) or a deterministic canonical storyboard context
(entity revision, hash, shot and payload). The bundle hash binds that projection.
Unchanged context is endorsed source text, never new authored observation.
Explicit edits remain creator input. Existing cross-shot source authority and
ordinary shared-image intent streams remain unchanged.

Source text and authored input have separate types. Canonical shot direction is
not constrained by the manual 2,000-character authored-intent limit. Persist an
exact `sourceEndorsement` with canonical revision/hash/shot and unchanged source
text; validate it against its historical owner and exact v3 receipt on read.
Intentional edits remove that source assertion and use the existing bounded
manual input contract. Truncation and globally relaxed manual limits are rejected.

## Consequences and guardrails

The shared owners write/read the new basis and every consumer enforces receipt
linkage, source freshness, latest review and exact geometry/reference lineage.
Preflight precedes all writes; the existing lifecycle transaction rolls back the
whole pack. Manual per-shot authoring is unchanged. No video operation occurs.
The gallery follows ADR 0101's explicit modal action, cancellation, CAS and
uncertain-response observation rules. Failed bytes/reads block review and can
be retried. No scroll or per-frame consent gate is added.

Auto-filled essays, partial approval, blanket optional manual fields and a
general historical compatibility layer are rejected. A deployed reader must
understand v3 before any v3 receipt can be created; rollback cannot remove or
reinterpret retained v3 evidence.
