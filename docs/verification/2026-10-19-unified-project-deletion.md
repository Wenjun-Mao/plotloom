# Unified project deletion — first source checkpoint

Scope: owner-approved one directory deletion entry and one explicit confirmation
flow, implemented in the retained `b30f/plotloom` checkout on local `main`, based
on `665d3b4d0774415e94a9cceef2c7fda72b89350c`.
[ADR 0201](../adr/0201-unified-project-deletion-preparation.md) records the contract.
This is a focused implementation checkpoint for independent review, not final
cross-layer qualification, installation, live deletion or product acceptance.

## Root causes and resulting behavior

- Two unconditional row controls delegated prerequisite discovery to failures.
  Abandonment neither cancelled paused runs nor supported empty automatic history.
  One passive server preview now selects the least-powerful supported operation.
- Pause was absent from ordinary close blockers. Final ordinary erasure now
  separately refuses every raw automatic-run state that still needs explicit stop.
  It also refuses all retained Exec attempt records: cancelled publication rows
  cannot hide UNKNOWN attempts, and terminal records still require the final
  host-owned quiescence/revocation gate rather than an earlier absence observation.
- Generic/global feedback hid exact reasons. Deletion owns project/phase feedback;
  prior and pending entries render their own progress/refusals, including a pending
  project whose manifest has already been withdrawn.
- A run revision alone can name a replacement run. Stop checks exact run ID,
  revision and consent scope in the actual lifecycle-write transaction. Both final
  erasers recheck scope under their exclusive project lease.
- An admitted draft can settle after preview. Old consent then refuses, keeps the
  project and newer local typing, and resumes existing queues. The browser fixture
  settles those edits, obtains fresh explicit consent, and successfully deletes.
- Post-stop GET would deadlock behind this client's suspended reads. The stop
  endpoint rereads preparation after its control transaction closes and returns
  that observation with its cancellation ACK. It never auto-deletes.
- Host erasure quiescence is distinct from permission to request existing exact
  cancellation. Recorded running-task fixtures cover both becoming quiescent and
  remaining blocked. Local authority cancellation never proves remote cancellation
  or process termination; unchanged host ownership predicates decide signalling.
- The running-image regression exposed text and image controllers both cancelling
  one executor attempt. Each now handles only its actual dispatch-owner domain.
  A mixed text/bridge/image/unknown-owner regression proves one cancellation per
  owned attempt and none for an unrelated owner. Host signalling code is unchanged.

The lifecycle hook is split into cohesive lifecycle/deletion owners (under 400
lines each), sharing the existing synchronous command token and draft/read barriers.
No refused or unacknowledged command triggers fallback or replay. UNKNOWN evidence,
reservations and revocation scope retain their original contracts. Acknowledged
pending-erasure retry preserves its original scope hash and exact receipt/consent.

## Small real journey and focused checks

The earliest real journey used two fresh isolated projects through production UI,
API and filesystem persistence: one idle home disappeared, fixture backend restart
returned target 404 and neighbor 200. No provider dispatch was needed. Test-owned
temporary roots/processes own cleanup; existing projects and installation data were
not inspected or mutated by this worker.

Executed with `uv run --locked --no-sync python scripts/verify.py focused`:

- `tests/test_project_deletion_preparation.py` plus exact existing reference-stop
  and queued-image-cancel cases: 16 Python cases passed; mixed owner partition,
  idle passive/no-host preview, paused ordinary refusal, run/scope/revision CAS,
  both final-scope erasers and both post-stop host outcomes are covered.
- `frontend/tests/project-lifecycle-command.test.ts`: 8 passed, including same-tick
  preparation exclusion and superseded-response retirement.
- `frontend/e2e/project-direct-delete.spec.ts` and
  `frontend/e2e/project-unified-delete.spec.ts`: 16 passed together. Real idle,
  active/archived/closed, prior-layout guarded deletion, durable retry, manual
  blocker/draft retention, stronger stale consent, late admitted draft/fresh consent,
  UNKNOWN acknowledgement and lost-stop/delete-ACK/no-replay paths are covered.
- Earlier directly affected checks passed: 10 ordinary eraser Python cases,
  7 original abandonment cases, 10 native host abandonment cases, and 5 lifecycle
  error browser cases. These are retained scoped evidence, not a new aggregate/full
  result on this checkpoint.
- Scope-bearing pending erasure retry: both original and scoped forms pass after
  manifest withdrawal and application reopen (2 Python). The affected direct-delete
  browser file passes again (11), including a scope-preserving explicitly confirmed
  pending retry whose refusal remains beside its exact pending entry.
- Final host/ordinary boundary rerun: `tests/test_project_deletion_preparation.py`
  and `tests/test_direct_project_deletion.py` pass together (22 Python), including
  the new cancelled-publication/retained-UNKNOWN ordinary-bypass regression.

Frontend and browser TypeScript checks pass. API/changed-module unused-import
checks and `git diff --check` pass. Deterministic checked assets are generated and
two production-build SHA-256 file trees compare equal. Desktop pixels were inspected
for idle consent and target-scoped partial-stop refusal at 1280×720; this does not
claim complete responsive or checked-static browser qualification.

Initial failures are retained as failures: invalid selector invocations were
refused before tests; an overly broad fixture locator matched its project title;
one fixture serialized snake_case then asserted camelCase; prior browser assertions
expected weaker revision errors/automatic scope widening. The running-task check
also exposed the actual duplicate-cancel defect described above. Each was corrected
at its owning layer and rerun with the stated focused selections.

## Boundary and handoff

Independent review and final risk-scoped qualification remain manager-owned. The
updated long lifecycle browser spec is typechecked but not executed in this source
checkpoint. There is no new full gate, hosted CI, push, provider/remote cancellation
experiment, installed-static journey, service restart, deployment or activation.
Running-worker tests use recorded production project state plus a provider-free
host-response seam; they do not establish a real OS worker termination outcome.
Actual owner projects and every live UNKNOWN reservation remain untouched.

The effective inherited worker model/settings are unverified. No paid usage was
incurred by these provider-free fixtures; product/infrastructure/coordination time
breakdowns are unavailable. Per-run durations remain in verification output; no
aggregate timing or acceptance percentage is inferred.
