# 0093 — Configurable text and image specialists

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
