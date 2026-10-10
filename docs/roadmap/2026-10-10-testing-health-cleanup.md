# Testing health cleanup — full creator E2E completion track

Status: the original cleanup is implemented, independently reviewed and
locally/hosted qualified. The owner approved the **performance follow-up P0–P4**
below on October10 with an explicit Relay Direct “go.” P0 baseline and safety
mapping are recorded in the receipt; the P1 cache probe passed the fixed pair
and additional family. P2's three verification tiers and P3's independent
same-SHA hosted jobs are implemented, with focused guards and the selected
production integration family passing. P4's final benchmark, profile,
independent review and full local qualification are complete. Scoped main
publication and the one unfiltered hosted qualification remain pending.
The original cleanup supported the
[Create → Revise → Recover run](2026-10-07-full-creator-e2e-repeat.md), not a
replacement acceptance checklist. That technical run and normal cutover are
now complete; the running application baseline remains frozen for owner use.
Use one source writer and read-only independent review for the proposed follow-up.
The owner's prior preference is GPT-6 Luna / Max for bounded implementation;
effective host settings require confirmation at dispatch. No normal cutover,
protected settings change or native generation is added by this plan.

The [completion receipt](../verification/2026-10-10-testing-health-cleanup.md)
records exact `0b71359` CI38024405822 SUCCESS, preserved behavior and measured
browser allocation results. The later
[normal cutover receipt](../verification/2026-10-10-normal-cutover.md) owns the
completed main publication and activation, not this cleanup receipt.

## Original cleanup — evidence and diagnosis

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

## Original cleanup — required implementation

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

## Original cleanup — verification and stopping condition

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
- The original parent goal also required the finite E22 action-reachability
  observation and native Create/Revise/Recover evidence. Cleanup did not replace
  them; creative/media quality and new capability scope remained excluded.

Finish only when all four cleanup items are implemented or proven inapplicable
with concrete evidence, supported behaviors remain covered and the combined
qualification is complete. Record outcomes and material gaps in the dated
verification receipt; do not describe audit recommendations as applied changes.

## Performance follow-up — approved P0–P4 implementation

### Outcome and current evidence

Make ordinary edit/check cycles short and reduce full qualification elapsed time,
without weakening supported behavior coverage or changing product semantics.
Test count is not the optimization target. Keep this follow-up in this plan;
do not create a second overlapping cleanup plan or reopen the completed E2E run.

- At planning baseline `dbd0e246`, the working tree was clean. The retained
  cleanup receipt records two profiled cases at53.06s before and55.76s after:
  the first cleanup did not establish a Python speedup.
- In the after profile,1,571 total `subprocess.run` calls consumed47.31s
  cumulative; Cast currentness consumed31.78s and Art currentness15.37s.
  These nested measurements must not be summed as independent wall time or
  extrapolated to the full suite. Each style-currentness call starts Node to
  derive a deterministic contract; nested project-state reads repeat that work.
- Hosted CI38024405822 recorded1,469 Python cases in1,930.78s and1,047 frontend
  cases in59.01s. Browser groups reported20.5/24.0m and started only after
  `verify` finished. Total workflow elapsed time was about59.5m. These hosted
  measurements are not a same-host comparison with the local profile.
- The current development guide presents a flat full-verification sequence.
  Browser runners already own independent checkouts and fixture roots; the
  `needs: verify` dependency imposes sequencing, not an artifact transfer.

Root cause: repeated process startup for unchanged pure rule derivation, plus
an unnecessarily serial hosted critical path and an unclear everyday-check
entrypoint. Fix those owners, not assertions, fixture isolation or deadlines.

### Chosen direction and alternatives

Recommend bounded, process-local reuse of **pure style-contract derivation**,
keyed by exact inputs and a content fingerprint of the complete rule dependency
closure. The existing Node implementation remains the single rule owner;
currentness comparisons and real candidate validation still run normally.
Request-scoped derivation could avoid global cache lifetime, but would require
threading context through nested readers and may leave repeated requests costly.
A persistent Node worker could amortize startup too, but adds IPC, lifetime and
failure recovery machinery; it is not the first approach for this bounded task.
The first implementation probe must prove the recommended approach safe and
materially faster before broader qualification. Do not duplicate rules in Python.

### Ordered deliverables

**P0 — Reproducible baseline and safety map.**
Record source SHA, tool versions, host, explicit expanded case IDs and commands.
Use the existing representative pair:
`tests/test_production_rebuild_freshness.py::test_target_drift_is_visible_and_fresh_preparation_recovers_without_borrowing_reviews`
and
`tests/test_production_bridge_runtime_http.py::test_runtime_http_fake_inference_review_edit_save_then_explicit_install`.
Select a small additional bridge/rebuild/currentness family before implementation
so the pair cannot be the only performance evidence. Record three unprofiled
serial baseline samples for both the pair and that family, with isolated temporary
roots and no competing benchmark jobs; profile one separate pair sample for
attribution. Retain startup counts separately from wall time.
Do not launch a full suite just to repeat the known diagnosis.

P0 is complete: the approved pair and preselected four-case additional family
each have three serial unprofiled same-host samples and a separate pair profile.
The exact IDs, toolchain, timings, Node startup counts and dependency/safety map
are recorded in the [receipt](../verification/2026-10-10-testing-health-cleanup.md#performance-follow-up-p0p4-local-qualification-complete-hosted-pending).

The first P1 probe is materially faster on both fixed selections: the pair median
fell from46.964s to4.304s, and the four-case family from49.575s to5.347s, with
all samples passing. This unlocks the bounded P2/P3 work; P4 has completed its
stable-candidate benchmarks, independent reviews and full local qualification.
Scoped main publication and unfiltered hosted qualification remain.

**P1 — Remove repeated pure style derivation at its shared owner.**
Inspect `src/plotloom/cast_style.py`, `art_style.py`, the two `scripts/*-style.mjs`
entrypoints and their imported preset/rule dependencies. Put cohesive shared
mechanics in a small style-specific module if needed, not generic caching helpers.
Keep existing CLI outputs, frozen contract shapes, rule hashes and error meaning.
Avoid editing the Node rule owners merely to optimize Python calls: changing their
bytes changes frozen authority and is outside a behavior-preserving optimization.

Required guards:

- Key by style-owner identity, exact style and direction (including `None` versus
  an empty string), and content-derived dependency identity. Wrapper-only hashes,
  Git SHA alone and timestamp-only invalidation are insufficient: presets come
  from imported upstream modules. Inventory the actual dependency closure first.
- Inventory execution inputs too. Verify resolved Node executable availability
  and identity before returning a hit; executable identity or relevant Node-option
  changes require a miss and fresh derivation or the existing failure. Do not
  return a cached result when Node is unavailable. Cover PATH/executable changes
  and execution-option failure after a successful warmup; do not log environment
  values or credentials. If these inputs cannot be bounded safely, stop the probe
  rather than silently change the error/currentness contract.
- Rule or imported-preset edits, including same-size/same-timestamp replacement,
  must be observed within a long-lived process. Missing/unreadable dependencies
  and Node/JSON failures fail closed; do not reuse a last-good result on error.
  Guard a rule change during derivation so mixed-revision results are not cached.
- Bound entry count and keep cached values immutable; return independent JSON
  values so nested dictionary/list edits cannot poison later reads. Concurrency,
  eviction and repeated-test lifetime must not affect correctness.
- Never cache a project approval/currentness Boolean, accepted revision, request
  receipt or mutable candidate. Real admission/style validation, transaction/CAS,
  rollback, stale direction/target and unknown-dispatch protections remain active.
  No test-only cache, monkeypatched bypass or shared mutable prepared project.
- Demonstrate miss/hit/invalidation and real-validator refusal with focused tests;
  exercise retained project-state paths, not only a synthetic cache microbenchmark.

**P2 — Explicit quick, focused and full local verification.**
Add one small transparent entrypoint, proposed `scripts/verify.py`, using existing
`uv`, npm and checked configurations. Update `docs/development.md` and the visible
development instruction to name these three paths:

- `quick`: lock/API-scoped lint, frontend unit tests and type contracts; no Python
  integration/browser suite, bundle build or wheel. Report what was not run.
  This is feedback, never backend or release acceptance.
- `focused`: explicitly supplied pytest case/file selections, Vitest files and/or
  Playwright specs, preserving native test semantics. Require a nonempty selection,
  reject unknown selectors and propagate failures; print the exact commands and
  selected tier. The implementer maps changed owners to relevant families; do not
  introduce speculative automatic changed-file selection or a second test registry.
- `full`: all existing Python/frontend/browser, archived-reader, types, scoped
  lint/lock, deterministic bundle/parity, wheel and installed-smoke requirements.
  Refuse ambient diagnostic grep/shard/filter settings that would silently narrow
  the local release gate. Build frontend before wheel packaging in this checkout.

Publish profile-level elapsed time and exit status using lightweight existing
tooling, not a benchmark service. Preserve native console/failure evidence.
Test selection, subprocess failure propagation and full-tier filter refusal.

P2 is implemented in `scripts/verify.py`, with setup and tier guidance in
`docs/development.md` and the visible root `README.md`. Its command contract,
selector refusal, failure propagation and full filter guard pass in the focused
suite; the real CLI also collected and ran an explicitly selected pytest case.
The complete combined P2/P3 focused run passed 62 tests; the six selected bridge,
rebuild, rollback and stale-dispatch integration cases also pass. Full-tier
qualification is recorded under P4 below.

**P3 — Overlap independent hosted checks, not mutable local builds.**
Remove browser's sequencing dependency on `verify` in `.github/workflows/ci.yml`.
Retain independently installed dependencies, exact candidate SHA, fixture roots,
manual-only trigger, two whole-spec groups, one worker per browser runner, exact
case-union guard, filtered-diagnostic semantics, reports and existing retry/budgets.
`verify` still builds/parity-checks the production bundle before wheel/smoke.
Full release acceptance requires `verify` **and both** browser jobs to succeed;
one green job, a filtered run, setup failure or a skipped/cancelled job is insufficient.
Update `tests/test_ci_browser_contract.py` to guard this contract rather than its
old serial arrangement. Amend ADR0109; retain ADR0153's allocation/isolation rules.
Do not add pytest parallelization, more browser workers or more shards in this pass.

P3 is implemented: verify and browser checkouts explicitly use `${{ github.sha }}`;
the browser job has no `needs: verify` dependency. The workflow contract test
guards independent same-SHA jobs, required job completion, step failure handling,
the two existing browser groups, and report-upload-only conditions. The hosted
workflow has not yet been dispatched.

**P4 — Measure, independently review and qualify one stable candidate.**
Repeat P0's unprofiled samples on the same host, toolchain and isolation conditions.
Proposed target: at least50% lower representative-pair median plus improvement in
the preselected additional family; this is a target, not an achieved/guaranteed
speedup. Preserve real assertions and all original expanded cases. If the probe
does not achieve a material gain, stop and explain the evidence before expanding
scope; after two failed attempts reassess instead of launching broad retries.

Record quick-tier median separately (target <=2m with dependencies installed;
hardware-dependent, not a correctness timeout). Full candidate coverage must
reconcile original IDs/parameter rows and new guards, not just aggregate counts.
Run focused checks during editing; perform full local qualification once the
combined candidate is stable, then one exact-head unfiltered hosted run. Repeat
only gates whose inputs changed or whose concrete failures require diagnosis.
Use an independent read-only source/evidence review on the stable candidate.

The initial P2 quick tier passed three serial samples in **10.141s, 9.620s and
9.881s** (median **9.881s**), each with 1,047 frontend unit cases and both
typechecks. On the stable P4 candidate, the fixed pair passed three fresh-root
samples in **4.391s, 4.275s and 4.325s** (median **4.325s**, 90.8% below P0).
The preselected four-case family passed in **5.333s, 5.346s and 5.345s**
(median **5.345s**, 89.2% below P0). All six commands exited 0 on the same M5 Pro,
macOS 27.0.1, Python 3.12.13, `uv 0.12.19`, Node v24.18.0 and npm 11.16.0. Raw
commands and output are in `/tmp/plotloom-p4-final-baseline-20261010.log` and
`/tmp/plotloom-p4-final-baseline-20261010.json`.

The final quick tier passed three serial samples in **9.940s, 9.565s and
9.510s** (median **9.565s**), each with the same 1,047 frontend unit cases and
both typechecks; evidence is in `/tmp/plotloom-p4-quick-final-20261010.log`.
A final cProfile run of the approved pair passed in 7.050s. It counted 1,531
cache API calls, two actual rule derivations, four live Cast validators and
four live Art validators: **10 Node starts**, matching the P1 probe. See
`/tmp/plotloom-p4-profile-final-20261010.pstats` and its command/output log.

The first unfiltered local full tier completed with exit 0. After the independent
reviewer identified that the P3 guard omitted step-level `continue-on-error`
and skip conditions, the contract test was strengthened to reject those
overrides except for the two existing artifact uploads under `${{ !cancelled() }}`.
The same reviewer confirmed that guard; the affected focused suite passed 62
tests and Ruff passed. The final full tier then completed in **12m12.075s** with
exit 0: 1,492 Python tests, 1,047 frontend tests across 132 files, all 278 unsharded
Playwright cases, deterministic bundle parity, wheel build and installed-wheel
smoke passed. The full output is in
`/tmp/plotloom-p4-full-qualified-20261010.log`; Python emitted one existing
Starlette deprecation warning. The unrelated-to-product test-race repair and
preserved earlier failure trace are detailed in the receipt.

The stable candidate has completed two read-only reviews: the Playwright
failure-state synchronization was cleared, and the full P0–P4 diff had no
runtime blockers after the step-condition guard follow-up. Scoped main
publication and one exact-head, default-unfiltered hosted workflow remain.

Report controlled micro/family improvements separately from historical full-suite
comparisons. Hosted acceptance must show actual job overlap, all gates passing,
and total elapsed time: target <40m versus the recorded59.5m, subject to runner
availability. Separate queue, setup and test execution, retain retries/failures,
and disclose noise; do not call a single hosted difference causal proof of P1.
If a controlled full-suite speedup is claimed, obtain matching baseline/candidate
runs on the same host; otherwise label the comparison historical and non-controlled.
Extend the existing dated cleanup receipt with this follow-up's actual evidence.

### Authority, exclusions and stopping condition

The owner's October10 Relay Direct “go” approves P0–P4: named source/test/tooling/
CI/docs changes, disposable benchmark roots, necessary local qualification,
scoped default main publication and one unfiltered hosted qualification, without
renewed approval at each covered step.
It does not authorize normal8841 restart/cutover, database/schema changes, demo
resets, provider/specialist generation, settings/credentials changes or H3 quality
work. Keep the running baseline available for owner use. Deployment, if desired,
is a separate explicit decision; Git publication is not runtime activation.

Do not delete tests, relax assertions, add skips/retries/timeouts, bypass validators,
share mutable fixtures, add compatibility/replay layers or repeat file splitting
without a demonstrated bottleneck. General fixture seed cloning, Python sharding,
frontend runner redesign and broad currentness/DAG refactoring are deferred.

Before changing runtime reuse semantics, record a concise ADR linked to ADR0141
and ADR0094; no product/persistence format changes are planned. One source owner
works serially in the retained checkout, preserving unrelated edits. A bounded
independent review is read-only, not another parallel writer.

If safety or equivalence fails, remove/revert the exact scoped optimization or CI
change non-destructively, retain the original tests and failure evidence, and
recheck affected gates. No reset of the repository or owner data. Report the
follow-up incomplete if its performance or safety acceptance is unmet.
Finish when P0–P4 are proven with preserved coverage, measured gains, explicit
verification gaps and a reviewable receipt. No new E2E creative acceptance is
required or claimed by this engineering pass.
