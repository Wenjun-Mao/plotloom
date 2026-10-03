# ADR 0106: Reviewed pre-generation image terminal outcome

**Status:** Accepted — owner approved the bounded recovery change on 2026-10-03.

## Context

A native shot-image specialist correctly stopped before ImageGen on conflicting
frozen directions. Its executor pin and final blocked report existed, but no
successful image delivery could exist. Product cancellation succeeded while
the reservation remained busy, as ADRs 0074/0093 require. That is not a broken
cancel endpoint: the handoff lacked a non-success terminal outcome.

## Decision

Add a separate `terminal.json` acknowledgement for **cancelled native image
attempts with a successful original pin, blocked before generation**. Apply the
same contract to shot images, character-reference proposals and art-reference
proposals. It declares exact job/request/task identity, original executor
provenance, a bounded reason, and boolean false for generation started,
active tools and produced outputs. It is not a completion manifest or an asset.

An explicit preview/settlement path resolves the retained project-owned request,
verifies the unchanged package/references and original executor pin, rejects
malformed/foreign/symlinked markers, simultaneous completion or staged output,
then verifies exact dispatch receipt/lease ownership. Operator review binds the
marker byte hash and task, records the observed terminal turn/revision and idle
blocked verdict. Those observations are **operator attestations**, not automatic
verification that an idle thread consumed a particular queue message. The
worker's job-bound declaration supplies the missing attempt binding.

Persist this reviewed proof before exact lease release, then retain a completed
receipt tombstone identifying the blocked outcome. A crash after proof persistence
or unlink can be reconciled with identical proof. If a cooperating successor has
already acquired the released slot, finalize only the old tombstone from its
already-persisted identical proof; never remove the successor lease. First-time
proof against a competing lease remains rejected. Repeated settlement is
idempotent only for identical reviewed proof.

No image candidate, delivery success, selection, canonical edit or resend occurs.
Ordinary refresh does not settle this outcome automatically. Keep the original
immutable package projection and executor pin unchanged; a supplementary
acknowledgement describes the stopped original attempt, not execution of the
later acknowledgement at the old code revision. New terminal/lifecycle owners
join the preflight's committed-source boundary.

## Alternatives and consequences

Cancellation-only release, idle-only release, manual lease deletion, assistant
swapping, fake zero-output completion and replay were rejected: they weaken
attempt identity or can overlap uncertain work. A general failed-generation
protocol is deferred; started/uncertain generation, tool failure with output,
missing preflight and all creative-text outcomes remain outside this bounded
path. Their reservations remain closed until separately admitted terminal proof.

Regression coverage includes all three real repository owners, unknown queue
acknowledgement, pin/package/reference integrity, exact boolean declarations,
explicit review, conflicts/staging, noncancelled jobs, identity/competing leases,
restart/crash/repeat settlement, no publication and dirty execution-source pinning.
See the [operator procedure](../operations/image-pre-generation-blocked-settlement.md).
