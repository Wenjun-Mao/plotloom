# ADR 0240 — Prospective retention-aware task dispatch guard

Accepted November 8, 2026 for new exact grants in this story continuation.

## Context

The old task guard expected fixed aggregate job and DONE-lane counts forever.
Four old unowned successful records and their matching DONE allocations disappeared
at a time compatible with the installed gateway's retention rule. The old guard
correctly held; its failed evidence and immutable original rowset remain unchanged.
Further normal retention boundaries occur during this overnight run.

## Decision

Use a separately pinned task-operator candidate for prospective grants. It checks
exact current permitted state, not deletion actor/time. Permit absence only of
enumerated unowned original identities that satisfy the pinned installed cleanup
predicate at the atomic SQLite observation time, together with exactly their
matching gateway/h3_video DONE allocation. Require explicit acknowledgment of
the four already missing identities. Their actual deletion cause/time and
intervening Voice state remain unwitnessed; compatibility is not a retroactive pass.

Retain the original base hash and captured row projections, the exact prior own
additions, and all 54 known owned native/output bindings. New owned completions
are sealed and remain protected. Reject changed surviving projections, extras,
noneligible/unlisted or owned deletions, mismatched allocation removal, UNKNOWN,
nonterminal state, source/configuration drift and rollback. Derive aggregates from
the exact accepted identity delta; allow no count tolerance or automatic rebaseline.

The installed predicate is successful terminal output with no unreleased Voice
binding and `output_expires_at <= datetime(snapshotNow, '-648 hours')`, reflecting
30-day record retention minus 72-hour output retention. Eligibility does not
require deletion. Capture tables and SQLite time in one read transaction; retain
the existing native/shared/Voice/service/idle and one-POST guards. A race between
the stock observer and row snapshot may conservatively hold.

Durable checkpoints, owned seal hashes and a separate batch head detect missing
or rolled-back task evidence. Partial/crash states hold; do not reconstruct a
missing seal/head, replay a known submission, mutate gateway state or clear
UNKNOWN. The trusted host/clock/filesystem boundary is not an authentication
claim against coordinated malicious evidence rewriting. Original baseline
protection covers its captured columns, not every historical database column.

## Qualification and activation boundary

The local seven-member candidate bundle is
`31d828742ade9d988ba0b3139f531e415fd6ee106ba23c8fbac39ab2f13b11bd`;
contract `b006d316cbe673575d2820bbd6dcfb0ddcc57979a87466c3969f7f21db77c380`.
Root checked member hashes, code/contract changes and retained evidence. The
specialist executed 47 passing offline tests, including the actual owning SQL
in a disposable fixture, and obtained independent Terra/high static review.
This qualifies the bounded candidate; live integration and future retention
transitions are separate observations.

Stage it separately from the stock bundle, preserve old held grants, and issue
a new finite exact packet grant after current story/checking/admission readiness.
The unchanged H3 recipe, services, cleanup code and production database are not
modified. No unrelated producer or gateway API semantics change, and no CI/push
is implied. The owning execution plan is
`docs/roadmap/2026-11-08-checking-extensions-and-complete-story.md`.
