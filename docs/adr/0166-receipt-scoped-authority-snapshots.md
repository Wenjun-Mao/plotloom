# 0166 — Receipt reconciliation owns its pre-mutation snapshots

Status: accepted for qualification, 2026-10-13. The owner approved this narrow
production query-placement change; release qualification remains pending.

## Problem and evidence

`autopilot_command` computes a protected-material snapshot and previous closure
currentness for every command. Only receipt reconciliation consumes them:
late transport evidence may be admitted after creative authority goes stale,
but must neither mutate protected material nor rebase stale creative authority.
Ordinary commands already validate their authority afresh at admission.

An isolated main-thread profile of the real 27-frame complete-pack journey
recorded 1,931 closure calculations, 590 directly from `autopilot_command`.
Moving the two receipt-only reads under their consuming scope reduced that
profile to 1,695 calculations. Profiler times are diagnostic, not speed claims;
that probe also contained the separate, unqualified installation-reader change.

## Decision

Compute both pre-mutation reads only for `receipt_reconciliation`, inside the
same lifecycle transaction and after normal command validation. Leave fresh
admission, the post-command full closure, protected receipt comparison, change
detection, revision updates, rollback and context cleanup unchanged. Current
receipt authority rebases after a permitted managed-asset write; stale authority
keeps its previous closure. No closure or admission result is cached or reused
between commands. Human, creative and transport authority remain distinct.

The transaction owner is the right layer: it knows which operation needs each
snapshot. Skipping validation in callers or teaching tests to bypass commands
would weaken the contract and is rejected. Cross-command caches introduce
invalidation and concurrency risks without addressing this unnecessary work.

## Guardrails and qualification

Regressions cover ordinary projection avoidance plus fresh stale-admission
rejection, protected receipt mutation with atomic rollback, and real managed
asset writes under current and stale receipt authority. Existing scope, handoff,
recovery and cancellation owners remain required. Qualify on the released
baseline plus the independently reviewed fixture refinement, without the older
installation-reader proposal. Measure unprofiled runtime before claiming a gain;
the complete Python target remains 85 percent less wall time with full coverage.
