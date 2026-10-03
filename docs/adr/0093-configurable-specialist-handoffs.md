# 0093 — Configurable text and image specialists

The bounded non-success image terminal outcome is defined by
[ADR 0106](0106-reviewed-pre-generation-image-terminal-outcome.md); it does not
change cancellation-only or idle-only reservation safety.

## Decision

Provide two installation-local bindings (display name and Codex chat UUID):
text for outline/cast/art/script/storyboard, image for image jobs. No binding
belongs in exported project data. Bindings are editable without restarting;
existing server image configuration seeds the local registry once.

Prepare, explicitly send, observe validated delivery, and creatively accept
remain separate transitions. Each assignment's frozen package is complete
authority; previous chat history never supplies project facts. Text delivery
uses existing pinned validators and admission methods, never automatic acceptance.

Use the existing supported `codex queue` transport and durable no-retry lease.
One assignment per specialist, distinct chat IDs, retained receipts across
binding changes. Reject configuration changes while either slot is occupied.
Cancellation does not prove execution stopped and does not release a lease.
Unknown transport outcomes remain reserved; do not silently retry or swap chats.
Only validated terminal delivery releases a reservation. Queue acknowledgement
does not establish execution started: display queued/waiting, not invented progress.

Native image sends require an atomic `prepared → exported` transition inside
the project write transaction. A manually exported task cannot later be queued
automatically. Export/copy is not a send endpoint. Reserve the native slot before
the transition; release that empty reservation if the precondition fails before
any queue call. Cancelled/replaced text work can be reconciled from settings:
validate its request-bound terminal receipt, release the slot, and never install
the discarded candidate. An invalid current candidate retains its lease for
investigation instead of silently permitting another assignment.

## Amendment: cancelled-delivery reconciliation (2026-10-02)

A real cancelled Script retained its reservation because the check route's
discard branch first called ordinary request lookup, which rejects cancelled
rows. The unit fake did not implement that guard and hid the mismatch.
Outline additionally retains a cancelled row at its visible head; currentness
therefore requires a prepared status as well as matching job identity.

Terminal reconciliation now has a separately named project-persistence access
to the exact stage's retained cancelled/ready/accepted candidate row. A ready
candidate can be replaced after ordinary refresh admitted it but before the
specialist reservation completed; only a noncurrent check takes this ready-row
discard path. Storyboard preparation still blocks a ready candidate. It checks route
project/stage/job against the stored request and stored execution pin; package
bytes never select the request or recover a missing pin. Ordinary request,
handoff, resend and admission guards remain closed for cancelled jobs. The
confined exchange/pin handle adapter is separated from the oversized general
project handle; terminal metadata has its own cohesive persistence capability.

An explicit check validates the original frozen package and complete delivery
against that retained request/pin. Valid terminal delivery is discarded without
changing the project or its newer head. Missing, partial, tampered or foreign
delivery keeps the reservation. Invalid current delivery still requires
investigation and never automatically releases. Idle or cancellation alone is
not completion proof; valid terminal proof also resolves `outcome_unknown`.

Registry completion binds to saved project/stage dispatch context, one dispatch
root, and exact receipt job/task identity. A pending receipt cannot be relabelled
completed when its lease belongs to another owner or exact release fails.
Low-level dispatch release still compares the exact `{jobId, taskId}` record.
Completed receipt tombstones persist; repeated checks do not disturb a newer
lease. A pending owned receipt with no remaining lease can finish its tombstone
only after valid terminal proof, covering a crash between exact unlink and the
receipt write. No native dispatch means there is no reservation to release for a valid
manual-current admission. Real-store/exchange regressions cover every creative
stage and identity, receipt, pin, restart and competing-lease boundaries.

## Alternatives and consequences

One thread per stage adds setup without needed parallelism; one shared thread
mixes text and media capabilities. Two reusable slots fit current scope. A
thread picker/automatic thread creation, background server polling, providers,
and an entire auto-accepted pipeline are excluded. Observation occurs while
the relevant task UI is open, with an explicit check action also available.

## Guardrails

Test local persistence, configuration concurrency, duplicate/ambiguous sends,
all five text stage bindings, delivery admission without creative acceptance,
refresh/reload recovery, and same-task busy behavior. Never use live generation
in deterministic tests. Existing accepted project content remains unchanged.
