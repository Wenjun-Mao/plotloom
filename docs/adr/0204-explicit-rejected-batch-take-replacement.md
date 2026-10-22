# 0204: Explicit rejected batch-take replacement

Status: accepted implementation decision, 2026-10-22

## Problem and root cause

The finished cinematic example has a current ingested H3 SH01 take explicitly
rejected for camera pullback, window drift and excessive steam. SH02 remains
usable. Batch setup deliberately treats any rejection or multiple retained jobs
as a conflict; execution requires one exact native job per target. Disposal
cannot remove a take with a retained segment proposal, and erasing that history
would lose the actual rejection and dispatched claim. Manual H3 directions
cannot carry the batch's typed QA endorsement, so manual preparation/selection
would misrepresent or bypass delegated whole-pack QA. The missing contract is
explicit batch succession, not provider retry or permissive inventory filtering.

## Decision

`POST /api/v2/projects/{project_id}/video-batch/replace-rejected` accepts
`batchId`, `expectedRevision`, nonempty unique `rejectedJobIds`, normal `setup`
and optional typed `attribution`. The existing control endpoint must first
cancel that exact current batch. Replacement requires its exact retained English
authorization and settled directions attempt. Listed jobs must belong to that
predecessor's execution, remain current, ingested, unselected and latest-rejected.
Every newly rejected shot must have exactly one fresh generation target; other
valid takes use existing reuse/observation and whole-pack review semantics.

One native command checks predecessor CAS and source/selection/work inventory,
then freezes a new batch identity. Its manifest retains the cancelled predecessor
ID/revision/hash and exact excluded rejection facts: job/shot/rejection IDs and a
hash of all native job, review, segment proposal and project dispatch-claim rows.
Nothing is erased or rewritten. Repeat replacement lists only newly rejected
jobs belonging to its immediate predecessor; all prior rejected facts carry
forward and must still match. Runtime preflight, preparation, dispatch and final
review revalidate this history. Portable admission also validates its lineage
and hashes; it grants no runtime execution authority.

Frozen superseded takes are immutable at the native write owners: repeat review,
human reopen, segment preparation/selection, cancellation and disposal refuse
before changing their retained rows, including after the successor completes or
is cancelled. Segment preparation checks both before deriving bytes and inside
the proposal transaction. This write contract is necessary: merely detecting a
later append as corrupt history on the next project open would let a valid public
operation make the project unreadable. Read/preview remains available.

Fresh targets start with no English directions or endorsement. Existing native
batch drafting/editing and explicit Start freeze a new English authorization,
batch/shot idempotency identity and native job link. The standard runner owns
single-attempt submission, reconciliation and proposal creation. The standard
atomic whole-pack confirmation requires current review hash and, for QA, actual
typed audiovisual inspection observations. Reused siblings remain part of that
confirmation. Old rejected takes remain unselected, with original evidence.

The operator owns explicit rejected IDs, settings, English clarification and QA
observations. Trusted code owns exclusion eligibility, frozen lineage, new batch
identity, native job identity/idempotency and currentness/CAS checks. Model output
still owns only the existing bounded English draft; no prompt/schema ownership
changes. All existing grants, cumulative QA claims, finite/null caps, UNKNOWN
fences, provider authority and source/material contracts remain enforced.

## Alternatives and guardrails

Reject automatic retry, ignoring retained jobs, clearing UNKNOWN, deleting review
or proposal history, manual selection bypass, changing original finite grants,
and a generic retry framework. Ordinary setup retains its strict conflict guard.
The explicit API is sufficient for this bounded operator workflow; frontend
replacement controls are deferred. Focused native tests cover one replacement,
repeat succession, unchanged reuse, fresh endorsement, exact attribution,
cumulative finite/unlimited claims, stale/selected/unknown/nonterminal/duplicate
refusal, mutated retained evidence and existing normal batch guards. Synthetic
media tests establish software behavior; activation and real example inspection
remain the manager's separate vertical slice.
