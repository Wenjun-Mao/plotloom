# Testing health cleanup — full creator E2E completion track

Status: owner-approved implementation requirement added to the active
[Create → Revise → Recover run](2026-10-07-full-creator-e2e-repeat.md).
This is a supporting engineering track, not a replacement acceptance checklist.
The assigned cleanup subagent is the sole source writer while this track is in
progress; the manager pauses source edits and independently reviews its result.
Independent reviewers are read-only. The owner requested GPT-6 Luna / Max for
implementation; effective host settings require confirmation at dispatch.
No normal cutover, protected settings change or native generation is added.

## Evidence and diagnosis

The independent read-only audit examined the current suite inventory/configuration,
sampled test semantics and inspected exact `2a93649` hosted
[CI38009336409](https://github.com/Wenjun-Mao/plotloom/actions/runs/38009336409).
Root independently checked the source hotspots and primary job logs:

- Python:1,464 PASS in2,147.28s. The slowest20 calls total472.04s, about22% of
  suite wall time;18 belong to production bridge/rebuild/installed-state checks.
- Frontend:1,037 PASS/125 files,57.90s wall time. Test count alone is not a problem.
- Browser:143 PASS in34.6m versus132 PASS/one flaky in17.9m. The critical path is
  substantially imbalanced. The first-attempt failure was a proved released-port
  fixture defect, not unnecessary product coverage; its separate owning repair
  has now passed278 local browser tests in15.4m with zero retries.
- Synthetic creator-confirmation UI replaces its APIs in memory, but the shared
  browser fixture still starts provider/backend processes that it does not need.
- Responsibility hotspots: `test_work_unit_contracts.py`1,883 lines,
  `test_project_storage_video.py`1,551, `app-state.test.ts`1,204 and
  `video-pilot.test.ts`874. Cross-test-module helper imports compound coupling.

Collected counts include parameterized invalid states and independent admission
paths. No safe bulk-deletion target was established. Rejection of retired schema
versions enforces the current breaking contract; it is not compatibility support.
Measure before changing setup: reported call time does not itself isolate fixture
construction from the behavior under test.

## Required implementation

1. **Production setup:** profile representative slow bridge/intent/rebuild cases;
   identify the expensive owning layer, extract cohesive fixture builders and
   reduce genuinely repeated prerequisites. Use smaller valid material or isolated
   prepared-project copies only where they preserve the tested contract. Keep
   real transaction/currentness/rollback/dispatch paths and exact state assertions.
   Never share a mutable project or bypass production validation to gain speed.
2. **Browser execution:** balance the two hosted runner allocations using existing
   duration evidence. Preserve every selected test exactly once, one fixture stack
   per runner, unfiltered release coverage and unchanged diagnostic-filter meaning.
   Give proven UI-only journeys a narrower fixture without unrelated provider or
   backend processes; keep native keyboard/focus/modal browser assertions.
3. **Modularity:** split the four named hotspots and any oversized modules touched
   by this track along clear domain responsibilities. Move reusable builders to
   cohesive fixture modules rather than importing other collected test modules.
   Preserve setup/teardown, state isolation, parameter rows and test behavior.
4. **Deletion discipline:** remove only demonstrated duplicate or retired-contract
   tests, recording the proof and retained protection. No arbitrary count/percentage
   reduction, broad tolerance, compatibility adapter, increased retry allowance,
   weakened assertion or hidden skipped gate.

Pure frontend Node/jsdom separation and historical coverage-inventory redesign
were audit leads, not part of this accepted four-item cleanup. Do not expand this
track merely because those additional improvements look useful.

## Verification and stopping condition

- Record baseline collected cases and the touched-family behavior mapping before
  restructuring; reconcile moved/new/retired cases afterward. Counts alone do not
  establish equivalence.
- Measure representative before/after timings on the same host with no overlapping
  benchmark jobs. Attribute improvements to setup/action evidence, not a faster
  machine or to comparing hosted one-worker with local two-worker runs.
- Verify fixture isolation and cleanup, narrower browser startup, shard completeness
  and disjointness, diagnostic filtering and deterministic execution allocation.
- Run focused touched-family checks first; on the stable combined candidate run
  full Python/frontend/unfiltered browser gates, types/build/static parity, required
  lint/lock/packaging/installed smoke and independent source/evidence review.
- Publish exact source/test revision and one unfiltered hosted qualification.
  Preserve failure/retry evidence rather than counting retries as first-pass.
- The active goal still requires the finite remaining E22 action-reachability
  observation and the original native Create/Revise/Recover evidence. Cleanup
  cannot replace them; creative/media quality and new capability scope stay excluded.

Finish only when all four cleanup items are implemented or proven inapplicable
with concrete evidence, supported behaviors remain covered and the combined
qualification is complete. Record outcomes and material gaps in the dated
verification receipt; do not describe audit recommendations as applied changes.
