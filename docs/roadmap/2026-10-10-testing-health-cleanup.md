# Testing health cleanup — full creator E2E completion track

Status: the original cleanup is implemented, independently reviewed and
locally/hosted qualified. The owner approved the **performance follow-up P0–P4**
below on October10 with an explicit Relay Direct “go.” P0 baseline and safety
mapping are recorded in the receipt; the P1 cache probe passed the fixed pair
and additional family. P2's three verification tiers and P3's independent
same-SHA hosted jobs are implemented, with focused guards and the selected
production integration family passing. P4's final benchmark, profile,
independent reviews and full local qualification are complete. The scoped
source commit is published on `main`, and the one exact-head, unfiltered hosted
qualification passed all three jobs. This follow-up leaves the running
application baseline unchanged and does not authorize activation.
The original cleanup supported the
[Create → Revise → Recover run](2026-10-07-full-creator-e2e-repeat.md), not a
replacement acceptance checklist. That technical run and normal cutover are
now complete; the running application baseline remains frozen for owner use.
The approved follow-up used one source writer and bounded read-only independent
review.
The owner's prior preference is GPT-6 Luna / Max for bounded implementation;
effective host settings require confirmation at dispatch. No normal cutover,
protected settings change or native generation is added by this plan.

The owner-approved M0–M5 modular verification and remaining-runtime follow-up
is appended below. Its implementation is isolated from the completed P0–P4
work and from the active owner walkthrough.

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
are recorded in the [receipt](../verification/2026-10-10-testing-health-cleanup.md#performance-follow-up-p0p4-local-and-hosted-qualification-complete).

The first P1 probe is materially faster on both fixed selections: the pair median
fell from46.964s to4.304s, and the four-case family from49.575s to5.347s, with
all samples passing. This unlocks the bounded P2/P3 work; P4 has completed its
stable-candidate benchmarks, independent reviews, full local qualification,
scoped main publication and the one unfiltered hosted qualification. No normal
runtime activation is authorized; the running baseline remains available for
owner use.

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
workflow passed in the one unfiltered, exact-SHA run recorded under P4.

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
runtime blockers after the step-condition guard follow-up. The scoped source
commit and one exact-head, default-unfiltered hosted workflow are complete.

The single hosted run [38081918996](https://github.com/Wenjun-Mao/plotloom/actions/runs/38081918996)
used `workflow_dispatch` with `browser_grep='.*'` on
`b47e8d7952fc21ba38ceb90f28f35b858255e2b2`; it concluded successfully. All
three jobs started at 19:58:58Z, confirming real overlap. The verify job passed
at 20:14:07Z (15m09s); browser shard 1 passed all 122 cases in 27.9m and
finished at 20:28:04Z; shard 2 passed all 156 cases in 30.3m and finished at
20:30:26Z. The manifest guard reported 84 specs and exactly 278 cases split
122/156 with no overlap or omissions. No failures, flakes or retries appeared.
The API run interval was 19:58:55Z–20:30:27Z (31m32s total), under the planned
40-minute target; dispatch-to-first-job was 3s, browser setup was 53–56s, and
the Playwright durations are reported separately above. All jobs completed on
the same SHA.

The local full Playwright suite took 392.242s (6m32s) on the M5 Pro, while the
hosted single-worker shards took 27.9m and 30.3m. This runner-to-runner,
unsharded-to-sharded comparison is not controlled evidence of a causal speed
change. The 31m32s hosted total meets the under-40m target against the recorded
historical 59.5m run, but that historical comparison is also not controlled.
Both shard result and HTML report artifacts were uploaded by the run. GitHub
reported nonblocking Node.js 20 action deprecation warnings (the actions were
forced to Node.js 24) and the upcoming `ubuntu-latest` migration to Ubuntu 26
on October 19, 2026; all gates still passed.

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

## Modular verification and remaining runtime — approved M0–M5 follow-up

Status: owner-approved for implementation on October 10 in an isolated worktree, including bounded final qualification and ordinary scoped branch publication after independent review. The work addresses local runs above 12 minutes and hosted full verification above 30 minutes. Completed P0–P4 remains completed and is not reopened. M0–M5 is separate from the workflow-guide UI/policy delivery and improves reliable selection without weakening full coverage. The risk-scoped frontend policy is ADR 0156.

### Outcome and evidence

Make ordinary checks short and explainable, run all affected test modules, and lower full-suite runtime without changing product contracts, sacrificing isolation or deleting behavior coverage. Existing scripts/verify.py already supports quick/focused/full. Focused accepts native pytest, Vitest and Playwright files/cases, but has no product-module ownership or dependency map. Python discovery remains tests/ and Vitest uses tests/**/*.test.ts in jsdom. tests/generation and tests/backend_core already have partial domain organization; do not reorganize everything just for directory symmetry.

The trusted completed baseline b47e8d7 recorded local full at 732.075s, Python at 320.90s (runner step 325.292s), browser at 392.242s and quick median at 9.565s. Hosted run 38081918996 recorded verify at 15m09s, browser groups at 27.9m and 30.3m, and workflow total at 31m32s. These are different hosts, concurrency and configurations, not controlled speed comparisons. The owner-guide candidate adds tests and is not this baseline. M0 must freeze the post-guide source before measuring.

frontend/e2e/fixture.ts creates test-scoped backend, provider and Vite stacks with isolated roots. vite-only-fixture.ts already offers worker-scoped Vite for proven UI-only tests. Browser local configuration has four workers; hosted CI deliberately uses one worker per each of two whole-spec groups. CI is workflow_dispatch and all three jobs overlap on the same SHA. These are leads to measure, not proof of which part causes the remaining wall time. The profiled full Python log's slowest single calls are about five seconds, so investigate cumulative repeated setup as well as outliers; top twenty alone is insufficient.

### Design and alternatives

Recommended: explicit capability modules with small reviewed source/fixture dependency metadata, expanding into native test selectors in the existing verify runner. Explain the selected tests/checks and why dependents are included before execution. Native discovery and results remain the authority for which test cases exist. Avoid manually enumerating parameterized case IDs or adding another test framework. Keep the existing browser shard manifest as execution allocation, not a second semantic coverage map.

Directory-only selection is simple but misses cross-domain consumers and shared-fixture effects. Automatic changed-file/import inference is attractive but cannot safely infer dynamic schemas, prompts, routes and lifecycle consumers yet; defer it. Do not infer minimal coverage from a file extension or claim the selector proves semantic completeness.

Initial module vocabulary: story-authoring (brief/source/outline/branches), graph, creative-production (cast/art/script/storyboard; split subfamilies when evidence warrants), media-lifecycle, playback, project-lifecycle (save/stale/revise/recover/snapshot), shared-contracts/tooling (schema/API/security/provider/prompt/build/package owners with explicit subfamilies). This taxonomy is proposed, not a command contract. Assign every native test/spec a primary owner; cross-module checks can be included by several profiles but execute once in a combined selection. Shared fixtures/helpers need dependent ownership even though they are not collected tests. Preserve dedicated lifecycle journeys; modules define selection and ownership, not permission to replace cross-stack tests with mocks.

Use distinct paths: fast (`quick`) feedback, exact `focused` selectors, named `module` profiles and full release verification. The implemented command is `scripts/verify.py module --module NAME --depth DEPTH`, where `contract` selects pytest and Vitest files, `browser` selects Playwright specs, and `complete` selects every nonempty suite for the owner plus its explicitly declared complete gates. Repeated module arguments make one deduplicated union; `--show` prints the selectors, dependencies, gates, omissions and commands without running checks. The verification-tooling module currently owns the lock, static bundle build/parity, browser-allocation and wheel/package gates. Module profiles do not replace the risk-appropriate final gate or required full hosted CI. Schema, persistence, admission, authentication, provider, prompt or build dependency changes and unresolved impact default to broad/full checks until a reviewed narrower closure is proven. Unknown modules, unknown selectors, empty selection, stale maps or conflicting ambient filters must fail explicitly; never silently pass.

### Ordered deliverables

#### M0 — Freeze baseline and profile the remaining costs

After the guide/policy assignment ends, record exact SHA, toolchain, expanded native inventory/parameter rows, module candidates and existing gate inputs. Reuse trustworthy current full logs/artifacts first; do not launch full suites merely for discovery. Choose representative source, graph, media and recovery families before optimization and measure three serial same-host warm-dependency samples with isolated roots and no competing benchmarks. Separately profile setup, action, teardown and process-start/readiness costs; use existing runner elapsed output, pytest/JUnit/Playwright reports or bounded instrumentation, not a benchmark service. Separate queue/setup/test time for hosted evidence. Identify top cumulative costs and publish a concrete prioritized shortlist. This precedes any conditional concurrency or prepared-seed change.

#### M1 — Review ownership and dependent selection

Add one cohesive selection/dependency metadata home alongside existing verification tools. Resolve modules to real native file/case selectors; prefer file-level ownership, splitting mixed files only when needed for useful isolation/selection. Report the union/dependent reasons, checks omitted and final-gate category. Add an inventory guard: all module-complete selections cover the full native collected suite/parameter rows, with no unknown or unowned tests and no accidental duplicate execution. For moved tests reconcile identities/parameter rows and behavior, not just counts. Addition of a new unowned test/source/fixture cannot narrow coverage silently. Amend ADR 0156 or add a linked concise ADR when the module contract is actually approved for implementation.

#### M2 — Explicit module commands in scripts/verify.py (implemented locally)

Preserve quick/focused/full and native failure semantics. Support named modules, explicit depth, multiple-module union/deduplication and a show/plan-only mode that prints expanded selectors and impact rationale. Unknown, empty or invalid selection fails before launching suites; module success cannot mean pass-with-no-tests. Include always-required shared gates where appropriate. Test selector correctness, cross-module expansion, moved/new parameter rows, ambient filter refusal, failure propagation and complete-union guard. Update AGENTS.md and docs/development.md with when to choose fast/contract/browser/module-complete/full and exact runnable examples. Do not add an automatic changed-file engine in this phase.

#### M3 — Optimize measured owning fixture/setup costs

Apply only M0-supported changes, not another cosmetic file split. Candidates: smaller valid fixtures for narrow refusal/read-only contracts, immutable validated preparation reused via isolated per-test copies where preparation itself is not under test, and worker-scoped Vite/narrow frontend fixtures for genuinely API-mocked UI cases. Never reuse mutable databases/projects/provider state, bypass real validators/transactions/CAS/currentness/rollback/dispatch, or rewrite evidence. Tests of startup/restart/preparation/recovery retain those actual paths. Profile process teardown/readiness before altering waits; do not substitute sleeps for observability, add retries, weaken assertions or inflate deadlines. Prove repeated/order-independent/cross-root execution and cleanup. Any production/runtime semantic change uncovered by profiling is a separate scope decision, not blanket permission to cache approvals or refactor the DAG.

#### M4 — Reduce full CI critical path through bounded measured execution changes

First rebalance whole-spec groups from fresh durations and eliminate proven setup waste using M3. If hosted browser remains dominant, probe four duration-balanced hosted shards, still one real fixture stack per runner, against the existing two. Retain exact case-union/disjointness, same SHA, fail-fast false, full reports, no skips/retry inflation. Limit changes to existing GitHub runner infrastructure/capacity; add no paid runners.

Python process parallelism (start two workers) is conditional on a demonstrated bottleneck and isolation audit of ports/roots/env/monkeypatch/process ownership/caches. Compare serial results and investigate nondeterminism. Do not increase local browser concurrency above the current four by default. Keep frontend builds and package creation serialized within a checkout; use separate process roots/outputs for concurrent gates. A module-only hosted run, if exposed, must be distinctly named diagnostic/scoped, never full release success. Required full hosted coverage remains unchanged. Stop a concurrency probe after two unsuccessful attempts and reassess rather than increasing resources/retries indefinitely.

#### M5 — Independently review, benchmark and qualify the stable combined candidate

Repeat preselected M0 family samples on the same host and conditions; record local module timings and setup attribution, and actual hosted critical-path/result artifacts. Demonstrate complete collected-case/parameter coverage preservation, selected-module dependency correctness, cross-root fixture safety, union/allocation guards and failure/unknown-selection refusal. Run one complete local and one unfiltered same-SHA hosted qualification for this cross-layer verification/tooling change; reuse valid unchanged inputs and avoid repeated full reruns after documentation-only adjustments. Preserve prior failed attempts and candidate identity. Publish scoped source/docs through the normal non-force main workflow after approval; report pending CI separately. Extend the existing cleanup receipt; do not invent another suite dashboard or qualification system.

### Proposed acceptance targets and boundaries

Correctness gates are nonnegotiable: retain existing supported assertions/parameter rows/lifecycle/negative states, exact native full-union coverage, refusal of unsafe/unknown selections, no live owner data/settings/jobs altered, and no overlapping shared build output.

Performance targets are provisional until M0 sizes modules: current quick stays at or below 30s warm median; ordinary selected frontend checks plus affected browser journey aim at or below 90s; a typical affected backend contract module aims at or below 3m (some genuine cross-stack journeys may remain larger and must be reported separately); full local aims at or below 8m; full hosted aims at or below 20m with a 15m stretch. Targets are not test deadlines, guaranteed estimates or grounds to delete tests. For optimized bottleneck families seek at least 30% median improvement with no regression in preselected other families. If M0 shows an infeasible target, explain measurement and revise the budget before expanding scope; do not relabel an unmet target as success.

Scope includes selection/tooling metadata, relevant tests/config/fixtures, documentation and bounded standard-runner CI allocation. It excludes product/UI redesign, provider/specialist/native-media generation, real image/video quality acceptance, owner project/schema migration/reset, normal8841 restart/cutover, credential/settings changes, unsupported narrow-screen tests, new compatibility adapters, broad test deletion, speculative dependency inference and new paid infrastructure.

The owner approved M0–M5 source/test/fixture/tooling/CI/docs, disposable verification roots, bounded process/shard probes, final gates and ordinary scoped branch publication after independent review, without extra milestone approvals. Shared normal static assets must not be rewritten during an active owner walkthrough; use an isolated qualification checkout/build output when required. No service restart or operational cutover is needed for test tooling; if one becomes necessary, stop and obtain separate authority. Use one retained-checkout source writer, bounded read-only independent review and serial performance samples.

On unsafe or regressing optimization, revert only its exact scoped changes non-destructively, preserve original tests/logs and run affected checks; retain the unfiltered full path as fallback. Completion requires both trustworthy useful module selection and measured final latency improvement, not merely a new command or directory layout.

### Execution checkpoint — 2026-10-10

The owner approved M0–M5 after the initial read-only plan review. Work is isolated on branch **codex/testing-health-m0-m5**, created at **4955bbf1d64edbc2d432dc99bfc88b8faaeb3e8c**. M0 is complete on that candidate. Executable, test and dependency inputs match guide commit **e6ca2d18448c24cc4129670df4df41e166551cc3**; the only e6ca2d1..4955bbf change at freeze was this roadmap draft. Native inventory, family samples, setup/action/teardown attribution and the M3/M4 shortlist are recorded in the verification receipt.

M1 ownership/dependency closure and its native full-union guard are implemented in the isolated worktree; the exact map, consumers and guard result are recorded in the receipt. M1 was reconciled after rebasing on guide correction **63b25f461367b5732e08e6aac5eef3c429721f75**: 1,497 pytest / 156 files, 1,072 Vitest / 133 files, and 280 Playwright / 85 files. The precise hashes are recorded below. The owner then published shared-graph UI commit **7da7b6efa20e43a3b2d692eeac7defe6838a1e1c** and documentation-only receipt **51cb4080200a6cca524fec2b2844022564d3707f**. The UI commit adds two Vitest cases and extends one existing browser case; the Playwright native count remains 280. This worktree is now rebased onto 51cb408 and its refreshed inventory is recorded in the receipt. Track unfiltered runs 38098197412 on exact SHA 4955bbf1d64edbc2d432dc99bfc88b8faaeb3e8c, 38101073289 on exact SHA 63b25f461367b5732e08e6aac5eef3c429721f75, and 38101824564 on exact SHA 7da7b6efa20e43a3b2d692eeac7defe6838a1e1c; do not duplicate any run. The first run failed in both browser shards. At the latest readback, run 38101073289's verify job passed and both browser shards remained in progress; all jobs in run 38101824564 remained in progress. Main publication waits for the manager's quiet-checkpoint coordination while the owner walkthrough is active.

### M1 execution checkpoint — native ownership map

At worktree HEAD **4955bbf1d64edbc2d432dc99bfc88b8faaeb3e8c**, the reviewed
manifest assigns all 156 pytest, 133 Vitest and 85 Playwright files to 11
nonempty product/verification modules. It records 59 configuration, setup,
fixture and helper dependencies with explicit consuming modules. The native
guard expands and verifies all 1,497 pytest, 1,058 Vitest and 279 Playwright
case rows exactly once without executing test bodies. The Python inventory now
includes five ownership-guard unit tests. The Vitest native list contains 19
rows across four file/name pairs whose JSON omits parameter identity; the
guard keeps the 15 repeated occurrences beyond the first and assigns
deterministic collection-occurrence suffixes. The Playwright normalized ID
hash remains equal to M0. This table is the exact historical 4955bbf inventory.
After rebasing onto 63b25f461367b5732e08e6aac5eef3c429721f75, the map guard
passed with 1,497 pytest cases (same hash), 1,072 Vitest cases / 133 files
(hash 11b554c8714fd1842dc4f14ef234c78f3f1f7f084b940139e5ed3586a9c70278), and
280 Playwright cases / 85 files (hash
4d0020410503c0d1bedcfb33d3323535d755ba43cb59943ff1337a47c8cb08c1). That
guide correction added 14 Vitest and one browser case to already-owned files.
The newer owner UI change at 7da7b6e adds two Vitest cases and extends an
existing Playwright case across the two graph views and three supported desktop
sizes. The Playwright native case count remains 280.

### M2 execution checkpoint — 2026-10-11

Root cause: the existing quick/focused/full runner had no product-module
selector, so developers had to manually reconstruct cross-suite selectors and
could omit an owner or its parameterized file cases. M1 established the reviewed
owner and dependency contract. M2 adds an explicit module planner and runner in
scripts/testing/module_selection.py without changing existing tier behavior.
The module command supports contract (pytest and Vitest), browser (Playwright),
and complete (all nonempty module suites plus gates declared in the manifest).
It deduplicates multi-module selectors, explains shared dependencies and
omitted gates, refuses unknown/empty/ambient-filtered selections, and runs the
full native ownership guard before any selected test body. The `--show` plan
executes no checks. verification-tooling owns declared lock, static bundle
build/parity, browser-allocation and wheel/package gates at complete depth.

The CLI guidance and gate contract are recorded in AGENTS.md,
docs/development.md, README.md, docs/verification/testing-module-ownership.md
and ADR 0157. Focused `verify.py` selectors for the runner and ownership guard
passed 26 cases. Native inventory guard passed with 1,506 pytest / 156 files,
1,072 Vitest / 133 files and 280 Playwright / 85 files; its hashes were
558d7528a855e49581582c81bc3f41bb4f5c3559fb7cf61987d30745909cb6aa,
11b554c8714fd1842dc4f14ef234c78f3f1f7f084b940139e5ed3586a9c70278 and
4d0020410503c0d1bedcfb33d3323535d755ba43cb59943ff1337a47c8cb08c1. Quick
passed in 11.046s with all 1,072 Vitest cases and both TypeScript checks. A real
shared-api-security contract selection passed all 49 pytest and 41 Vitest cases
in 15.782s including full-map preflight and app typecheck. Ruff and diff checks
passed. The refreshed post-rebase inventory and M3 fixture optimization are
recorded below; M4–M5, independent review and final qualification remain.

### M2 reconciliation and M3 execution checkpoint — 2026-10-11

The M2 branch is rebased onto `51cb4080200a6cca524fec2b2844022564d3707f`.
Two consecutive collection-only ownership checks produced the same current
inventory: 1,507 pytest / 156 files, 1,074 Vitest / 133 files, and 280
Playwright / 85 files. Exact hashes and module counts are in the verification
receipt. The only native-count change from the owner UI commit was two Vitest
cases; its existing Playwright guide case was extended without changing the
native Playwright case count.

M3 reduces repeated graph-command fixture setup by building one accepted-source
seed through the existing prepare, deliver, admit and accept path per pytest
session, then closing it and opening a full project-folder copy under each
command case's isolated temporary root. Each command case still edits its own
database through `ProjectFolderStorage`; other graph suites retain their
function-scoped accepted-source setup. Reusable source/outline and graph
authoring builders are in cohesive fixture modules rather than imported test
modules. A separate regression confirms writes to one copy do not appear in
another. The root-cause evidence, exact before/after timings and focused checks
are in the receipt. M3 is implemented; the M4 four-shard allocation is
implemented locally and passes its complete verification-tooling module gate.
M5 review and final qualification remain. ADR 0158 records the seed lifecycle
and isolation contract. Hosted run 38101073289 is terminal failure on exact
SHA 63b25f4 with verify passing and both browser shards failing. Run 38101824564
on exact SHA 7da7b6e is terminal failure: verify passed and both browser shards
failed. Neither carried-over run is to be duplicated.

### M4 execution checkpoint — 2026-10-11

The two-shard hosted assignment remains the observed baseline. M4 uses its
whole-spec timestamps to propose four LPT-balanced groups; the estimated
14.35–14.41 minute groups are not a hosted result or a causal speed claim.
ADR 0159 records the four-shard candidate, its exact native union guard and the
decision to use one unfiltered hosted run as both the M4 probe and M5 hosted
qualification.

Local M4 checks passed: the browser contract selector passed all five tests;
the manifest guard listed all 280 native cases across shards 81/61/67/71 with
zero overlap or omissions; and the complete verification-tooling profile
passed in 40.869 seconds, including both type checks, locked dependencies,
deterministic static build/parity, wheel/package smoke, 54 pytest cases, 2
Vitest cases and 6 browser tests. A hosted four-shard result, same-host family
retiming, independent review and the one full local gate remain outstanding.
