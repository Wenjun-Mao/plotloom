# 0176 — Receipt-command-local material projections

Status: owner-authorized October 14, 2026; independently design-reviewed and
implemented, with independent stable-candidate review finding no actionable
issue. Focused qualification is recorded in the plan. No performance result or
release qualification.
Tracked in the [Python optimization plan](../roadmap/2026-10-14-python-context-and-workers.md).

## Problem and evidence

The current complete-pack diagnostic profile attributes 650 material-closure
calls / 6.366121430 cumulative seconds to `autopilot_command`. These are nested
instrumented costs, not an attainable saving or benchmark. Under ADR 0166,
receipt reconciliation needs protected and full hashes before its command and
again afterward. Each pair independently selects, projects and sorts the same
protected rows. The transaction composition owns this duplication; ordinary
closure callers and fresh admission do not.

## Decision

Within each separate uninterrupted receipt pre-command or post-command segment,
project and sort every protected material row once. Hash that payload, then add
managed assets and the unchanged geometry/cancellation extras for the full hash.
Return only the two hash strings; no payload or resolved authority survives the
helper return or the yielded command. Call the helper afresh after the command.

In the post-command segment, compare the protected hash and raise the existing
`InvalidTransitionError` before reading, projecting or hashing any allowed asset
or cancellation/geometry extras. An eager pair would change failure priority
and is rejected. Explicitly flush pending writes at each segment's start.

Keep all current table columns, row datetime ISO conversion, row-hash sorting,
payload keys, geometry filtering and cancellation IDs. Canonical JSON already
sorts dictionary keys, so adding managed assets after protected rows preserves
the exact full identity. The public `material_closure` signature and behavior,
including custom tables and cancellation options, remain unchanged.

This is operation-local construction reuse, not a database snapshot guarantee.
It adds no cache, caller validation flag or authority bypass. Existing lifecycle
leases, admission, command yield, mutation, rollback/commit, controller claim,
CAS, run revision/time, current-versus-stale receipt rebasing, ordinary-open
validation, inventory and other lifecycle writes remain unchanged.

## Alternatives and guardrails

Reject cross-command/session/global/result caching, reduced row projections,
gate pruning, hash-format changes and coalescing fresh views/admission checks.
The paired helper is private to receipt command composition; ordinary owners
continue constructing their own fresh closures.

Focused guards must establish exact existing hashes (including populated rows,
Unicode/nested JSON/null/datetime values, geometry and each cancellation owner),
one protected projection per segment, pending-write flush, independent calls and
segments, protected-failure precedence, unexpected-error rollback, allowed asset
changes and current/stale closure update rules. Reuse existing scope, admission,
claim, corruption/open, recovery and cancellation regressions. Independently
review the stable candidate. Benchmark/profile/full work requires a separate
allocation; no speed claim follows from call counts or focused correctness.
