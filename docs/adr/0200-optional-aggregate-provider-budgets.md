# 0200: Optional aggregate provider budgets

Status: accepted implementation decision, 2026-10-19

## Problem

Numeric-only defaults mixed aggregate spending policy with provider capability.
Autopilot defaulted to 80 images/96 jobs, batch video to 64 jobs/512 requested
seconds, and QA scopes could express only finite budgets. UI ceilings also
differed from backend ceilings. Increasing an arbitrary number would preserve
that faulty model and still stop otherwise authorized work.

## Decision

New launch and batch setup requests default omitted aggregate limits to null
(Python None), meaning unlimited. Builders freeze both budget members explicitly
in launch policies and batch manifests. Optional finite limits are
strict integers with existing lower bounds (images/batch jobs 1, autopilot jobs
9, requested seconds 5), without artificial aggregate upper ceilings. Omission
in a new request uses null; invalid, blank, zero, boolean, string, fractional or
nonfinite values never mean unlimited. The UI offers explicit Unlimited and
finite modes, validates finite text before submission, freezes the actual choice
and reads it back with truthful summaries. A new setup/project resets to unlimited;
continuation explicitly carries the chosen existing policy and retains accounting.

Frozen authority has no omitted-budget default. Every retained launch policy
version requires explicit `maxImages` and `maxJobs`; portable batch admission
requires explicit `maxJobs` and `maxRequestedSeconds` in frozen setup. Explicit
null means unlimited, while missing either member is unsupported/corrupt evidence
and fails admission through the existing corruption contract. Hashing raw JSON
alone cannot prove an omitted member's intended authority: previously it could
have meant a finite request default. Reject that ambiguity rather than widening
authority, supplying compatibility defaults, migrating or rewriting evidence.

Trusted admission compares consumption only against a finite cap. Finite
preflight, reservation, cumulative dispatch and portable validation use the same
meaning. Prospective source-owned QA scopes may use null limits; a finite QA grant
requires a finite batch cap no greater than its authority. Existing serialized
finite policies, manifests and scope hashes are unchanged. No grant is widened,
new enrollment created, retained evidence rewritten or migration introduced.

Aggregate budget is independent of finite task scope and structural/schema
limits, H3's per-request duration/profile catalogue, selected source/project/
provider authority, local_capacity_v1 accounting, concurrency, one initial
attempt, idempotency, UNKNOWN/unsettled fencing, pause/cancel and actual review
attribution. Atlas Wan's pilot ledger and all other providers remain unchanged.
Unlimited grants neither retries nor endless experiments; authorization still
belongs to the actual task. Models do not choose caps. No prompt/schema ownership
moves from author or trusted code to model.

## Alternatives and consequences

Reject magic large numbers, removing safety checks, a flag that bypasses the
owning schemas, per-caller exceptions and a generic administrative framework.
Nullable caps must be handled by every consumer; regression checks cover default,
null and finite serialization, unchanged finite hashes, finite exhaustion,
prospective QA containment, failure/UNKNOWN accounting and explicit UI input.
Provider-free local roundtrips prove policy/persistence, not provider E2E or
creative acceptance. Full local qualification and activation remain separate
from the initial focused candidate checkpoint; hosted CI is optional and requires
Wenjun's explicit request under ADR 0199.
