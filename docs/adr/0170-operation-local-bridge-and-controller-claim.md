# 0170 — Operation-local Bridge reads and controller-claim transactions

Status: owner-approved October 14, 2026; independently design-reviewed;
implementation and qualification pending. Delivery is tracked in the
[Bridge / claim plan](../roadmap/2026-10-14-bridge-claim-optimization.md).

## Problem and evidence

The retained complete-pack profile attributes overlapping costs to material
closure (1,695 calls / 20.708s) and Bridge state reads (131 / 10.383s).
Bridge resolves the same accepted Storyboard/Script inputs repeatedly during
one presentation read. Controller `claim` uses the generic manual-material
lease, comparing material before and after changing only controller metadata.
Neither finding authorizes fewer admission checks or a different material hash.

## Decision

Storyboard owns a private resolved value containing its existing five-part
context and the section map from that same Script resolution. Existing context
entrypoints retain their return shapes and frozen timing/render projections.
Bridge resolves that value once and applies the existing ordered binding
diagnostics and full-equality fallback, preserving its generic stale-F5 error.

One Bridge `get_state` lazily shares its context or expected transition error
between proposal, installed-production and preparation projections. Each
consumer gets a new ordered stale-reason list. Pending proposals still compare
their replacement target; accepted proposals do not. Installation evidence and
canonical identities retain hard failures and ordered checks. Quiescence and
replacement-target reads stay fresh. The independent installation entrypoint
continues resolving its own context; no public already-validated argument exists.

This is bounded reuse inside an uninterrupted presentation operation, not a
database snapshot guarantee: a read session alone provides no such isolation.
No resolved authority survives into another read, mutation, admission,
dispatch, commit or rollback. Unexpected storage/model errors still propagate.

Inject a dedicated claim lease only into `AutopilotPersistence`. It uses the
same lifecycle transaction primitive: SQLite `BEGIN IMMEDIATE`, lifecycle
contention error/retry metadata, non-SQLite write lease and rollback semantics.
Inside an existing manual/autopilot command it joins that command's session;
the outer command retains its closure/revision/rollback responsibilities.
Only the standalone generic manual-material before/after comparison is omitted.

The claim body and returned `RunView` stay unchanged. Missing, recovered and
durably handed-off runs retain their refusal order. Identical claims remain
no-ops; changed claims advance revision/time once. Claim is metadata ownership,
not dispatch admission: paused, waiting, blocked, cancelled, taken-over and
material-stale runs retain their existing reconciliation behavior. Run-view
material/policy/checkpoint/frame validation remains inside the transaction, and
the service's subsequent current-state read remains fresh.

## Alternatives, consequences and guardrails

Reject session/global caches, material-hash changes, skipped ordinary-open
corruption checks, caller-supplied validation flags and discarded claim returns.
Do not substitute the work-unit claim lease: its errors/backend contract differ.
The dedicated injected lease avoids exposing a general metadata bypass to every
project owner. Other lifecycle writes keep their full before/after protection.

Regression checks cover exact ordered and independent diagnostics, empty and
dual Bridge states, frozen timing/render modes, hard installation errors,
successive-read and write-boundary freshness; claim state/refusal/revision
semantics, unchanged nonmetadata fields, same-session composition, contention,
return-validation rollback, non-SQLite delegation and surviving view closures.
Measure an unchanged preselected test union before/after. Neither the profile
nor this decision establishes the whole-suite 85-percent speed target.
