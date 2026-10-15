# Python context reuse and bounded worker experiment

Status: the first owner-approved slice was independently reviewed, locally
full-qualified and integrated on October 14, 2026. The later historical-scheduler
and geometry-fixture continuation is implemented with focused checks and
independent review; scoped geometry measurement passed. A historical 2,239-case
Python-only observation passed at `7638964`, as recorded below. The later
ordinary-open profile implementation at `db021699` has 142 focused passes and
one accepted unchanged-case pair; a fresh current whole-Python measurement,
matched whole-suite gains and combined full qualification remain open. This continues the
[testing-health plan](2026-10-10-testing-health-cleanup.md),
not a redefinition of its 85-percent complete-suite wall-time target.

## Authority and baseline

The owner approved operation-local production Script/Storyboard context reuse
and experimentation with four Python workers. Eight workers are permitted only
after measured memory/isolation headroom. The released default remains two.
The initial slice excluded broader Production Bridge reuse; its separately
approved follow-up is below. Cross-operation caching and coverage reduction
remain excluded. [ADR 0167](../adr/0167-operation-local-storyboard-context.md)
records the production boundary before implementation.

The isolated checkout is `python85-profiling`, branch
`codex/python85-query-qualification`, starting at `a14e81ed4cc3c3e601771e3aa7b720c678dc49ce`.
Its executable source matches the current released main baseline. The last
qualified complete Python measurement was 1,859 cases / 182 files in 633.23s
externally at `bafb1587`: 9.21% below the previous 697.496s, one comparison
combining fixture and schedule changes. The original 85-percent target is open.

The CLI worker committed its diagnostic checkpoint at `7b30ad3d`, is idle and
released the shared source/check window. The manager is the sole writer and
check owner for this Python slice. CLI generation, native probes and source
changes stay held; read-only review may proceed independently.

## Deliverables

1. Resolve Script context once in each Storyboard context operation. Reuse one
   resolved base context for accepted and candidate projections inside one
   uninterrupted `get_state` read, preserving each frozen timing/render mode.
   Empty state resolves no upstream context. Every separate read resolves fresh
   context; write/admission/commit/rollback boundaries are unchanged.
2. Expose an explicit experimental worker count through the existing complete
   Python runner, not an alternate runner or environment override. Default two;
   experimental choices two/four/eight. Verify each worker's exact assigned
   native case-ID fingerprint, not just file membership or case counts.
3. Run a matched quiet two-versus-four complete Python comparison on the same
   reviewed candidate, dependency/toolchain inputs and native case inventory,
   with fresh temporary roots and exact coverage. Capture external wall time,
   simultaneous aggregate owned-process-tree RSS (including Node), memory
   pressure/swap observations and cleanup. Consider eight only if four supplies
   evidence of headroom. More compute is not original fixed-resource success.

## Root cause and verification

Storyboard currently asks Script to resolve context in its stale check and then
resolves it again; accepted plus candidate state repeats that pair. The owner
read knows these comparisons belong to one uninterrupted operation. Pure
binding comparison belongs at that boundary, not in caller-side validation
bypasses or a session/global cache.

Before production edits, time these unchanged whole files through `focused`:
`test_script_storyboard_diagnostics.py`, `test_accepted_review_lifecycle.py`,
`test_storyboard_brief_style.py`, `test_storyboard_review_timing.py`,
`test_autopilot_image_safety.py` and `test_production_bridge.py` (all under
`tests/`). Repeat that exact union after the change. New focused guards cover
diagnostic ordering and all accepted-Script error mappings, empty/dual state,
independent 8/12-second and omitted/frozen render policies, successive-read
freshness and fresh write-boundary refusal. Do not add nested profile timings
or extrapolate these file measurements into whole-suite gains.

Runner checks cover exact case-ID proof, malformed/missing/duplicate completion
markers, four-worker whole-file isolation, partial startup failure and SIGTERM
descendant cleanup. Then independently review the stable combined candidate.
Reserve the final full release gate for that stable candidate; focused checks
or the Python-only experiment do not qualify the other release gates. Preserve
unchanged evidence only where its actual source/dependency inputs still match.

## Stopping and release

Stop for new authority if a finding requires scope beyond the operation-local
read or bounded concurrency experiment. Do not weaken diagnostics, skip tests,
increase default concurrency or claim 85 percent from estimates. Record actual
measurements and limitations, qualify the release candidate, then integrate and
push the scoped work under the normal repository policy. CLI integration and
live activation remain separate; no existing creative run is resumed here.

## Operation-local checkpoint

The first production slice is implemented. Twelve new focused regressions
passed, including one Script resolution for dual state, zero for empty state,
distinct error mappings, independent frozen policies and fresh refusal after a
normal Script mutation. Independent read-only review (requested GPT-6.1 Sol /
Medium; effective settings unverified) found no concrete findings. Existing
accepted-lifecycle cases cover retained-stale/current-candidate separation.

The exact six-file, 77-case union above passed before and after the source
change. External wall time was **130.15s before / 117.79s after** (9.50% less);
pytest reported 121.74s / 109.51s. Both commands exited zero. This is one quiet
focused pair, not a whole-suite or repeated-median speed claim. Logs are in
`.local/remaining-cost/operation-context-before-fGZr2z/focused.log` and
`.local/remaining-cost/operation-context-after-JDkaf0/focused.log`.
At this checkpoint, the full gate and worker experiment were still pending;
their executed evidence follows below.

## Runner checkpoint

The same runner now supports explicit experimental counts while its release
entrypoint remains two. Exact native case proofs and four-worker startup,
failure, interruption and representative SQLite/Storyboard/Node/image isolation
guards passed: 88 focused checks across completion, runner, experiment, cleanup,
module ownership and verify-command tests. The first preflight caught a marker
line-boundary defect in the producer; ADR 0168 records its root-cause repair.
Independent read-only review (requested GPT-6.1 Sol / Medium; effective settings
unverified) found no correctness issue. Its support-dependency registration
suggestion is included.

Native ownership discovery passed with 1,911 Python cases / 185 files
(`6c202360bb4dea63a47ccfa1cd4539f5af6ae8bf529452f76fd911d2eedb61a1`),
1,377 Vitest / 158 files and 318 Playwright / 93 files. This discovery did not
run test bodies. Both subsequent worker measurements use the same committed
candidate and unchanged timing input. The old timing manifest is ineligible;
the explicit case-count fallback is the matched experimental basis. No full
gate or whole-suite speed claim is established by this checkpoint.

## Matched worker experiment — October 14

Both complete runs at clean `656f5fcd5e4388d2e1a3b9745c06f6743565f64b`
passed all 1,911 native cases / 185 files. Exact coordinator and worker case
proofs passed. Source, toolchain, host and timing-manifest fingerprints stayed
unchanged before/after each run and between runs. The common schedule was the
explicit case-count fallback, not the previous release's duration schedule.

| Workers | External wall | Worker elapsed times | Sampled aggregate RSS peak |
| --- | --- | --- | --- |
| 2 | 797.745s | 309.167s / 791.610s | 1.443 GiB |
| 4 | 472.179s | 237.538s / 220.585s / 466.802s / 251.430s | 2.188 GiB |

This one pair observed **40.81% less wall time with added compute**, not the
original fixed-resource 85-percent target or a repeated-median result. External
timing includes startup, collection, reporting and cleanup, with up to roughly
one second of observer polling quantization. RSS is a one-second sampled sum of
the owned process tree, including observed Node children, not an instantaneous
maximum. Both runs left no observed owned processes/groups or runner temporary
roots. Representative isolation and interruption guards are separate focused
evidence, not implied by the speed result.

The two-worker run's memory-pressure signal temporarily rose from 1 to 2 and
returned to 1 before completion; swap use decreased from 3432.94 to 3424.94 MiB.
The four-worker run started after pressure recovered, stayed at 1 in all
samples, and swap use decreased to 3408.94 MiB. This difference limits how
precisely the pair isolates concurrency. No eight-worker run was executed and
the release default remains two.

Retained command, observer, fingerprints, pressure samples and reports are in
`.local/remaining-cost/worker-comparison-uQuPIx6t/`. Suite-log SHA-256 hashes:
two `899c16f85213988cf593a056bf38e16f4649827682c83b54e9715b8f08ae94ab`;
four `4d8c455300bf15647038eba92469c0526ab141daaa711acdf8a90ca108ff743f`.

### Refresh the released two-worker schedule before qualification

The complete two-worker report contains 185 unique timing rows covering all
1,911 cases, totaling 1080.758s of pytest phase work. Case-count assignment put
302.046s in one group and 778.712s in the other. Its largest indivisible file,
`test_autopilot_geometry.py`, cost 161.077s. More workers do not eliminate that
work. Restore current measured duration weights before considering another
concurrency increase; eight-worker headroom alone would not fix this imbalance
or establish the fixed-resource target.

The refreshed `python_suite_timings.json` uses those complete rows, current
native case IDs, host fingerprint, and executable-input fingerprint
`ba57bfa2c56d911e1652eeb3e283440c1294285ec89f0bcd17df8a588810c20f`.
A fresh native collection and the real scheduler accepted it with
`schedule=duration`, no fallback, and exact 93/92-file coverage. Estimated phase
loads are 540.379s each, **not measured wall time**. The final full gate below
measures the default two-worker candidate and qualifies all remaining local
release surfaces. The current 1,911-case measurements are not an exact-inventory speed
comparison to the older 1,859-case / 633.23s release. No 85-percent or full
release success is claimed by the experiment alone.

## Complete local qualification — October 14

Clean candidate `4bc1d62a5532a7da429d991b210b3c8c6317c0b3` passed
`/usr/bin/time -p uv run --locked --no-sync python scripts/verify.py full`.
The full gate exited zero in 1064.824s (1064.87s external), including:

- all 1,911 Python cases / 185 files, with the unchanged exact native inventory;
- all 1,377 frontend unit tests / 158 files and frontend type contracts;
- deterministic production assets, checked-bundle parity and unfiltered shard
  coverage, followed by all 318 browser tests;
- locked dependencies, media probes, API unused imports, archived prompt reader,
  wheel build and installed-wheel smoke.

The default **two-worker Python command took 578.639s**, including startup,
collection, reports and cleanup. Its post-collection runner summary was
572.809s; pytest reported 990 cases in 550.31s and 921 in 563.16s. Both exact
assigned-ID completion proofs passed and `schedule=duration` had no fallback.
The runner temporary root was absent after completion, the checkout remained
clean, and the executable-input and host fingerprints still matched the
experiment's recorded values. Deprecation warnings concerned Starlette/httpx
and three existing fork-based crash cases; no test failed or was omitted.

Retained log: `.local/remaining-cost/python-context-final-j87N9xwN/full.log`,
SHA-256 `13279c4660dd562aef42108c991e64199422e2db9c5d4fd06a6f9e959304c3cf`.
The preceding timing-data refresh also passed all 33 completion/runner checks.
No repeated full gate is needed for the subsequent documentation-only receipt
or an integration whose executable/dependency/configuration trees match this
candidate. Verify that equality before carrying the evidence to main.

The 578.639s observation is not a matched old-versus-new production comparison:
the former 633.23s release had 1,859 cases, while this candidate has 1,911.
The fixed-resource 85-percent target remains unmet. Four-worker results remain
separate added-compute evidence; eight was not run and default concurrency is
unchanged. Hosted CI was not dispatched and remains separately unqualified.
CLI integration, provider execution, deployment and live activation are not
covered by this local gate.

The complete final capture contains 185 unique timing rows / 1,911 cases and
1110.509s of aggregate pytest phase work. Even ideal two-way allocation at
those observed costs needs 555.254s before overhead. The 578.639s command is
already near that packing floor; further scheduling tweaks cannot produce the
original 85-percent result. Geometry (155.776s), handoff (139.887s), image safety
(103.576s) and images (99.435s) remain the largest files. These are residual
costs, not authority to remove their behavior coverage or broaden production
caching. Any next production change needs its own measured cause and scope.

### Integration

The manager selectively integrated only this slice's four commits into main
through `aa926b03`, preserving the newer CLI roadmap and previous publication
receipts. The sole conflict was the testing roadmap heading adjacent to its
older publication receipt; both the receipt and new approval were retained.
All source, scripts, tests, frontend, dependency, workflow and submodule inputs
match qualified `4bc1d62a`; a complete tracked diff contains only documentation.
The actual main input/host fingerprints also match. The subsequent receipt
updates are documentation-only and do not require another full run. Ordinary
main publication does not dispatch hosted CI or activate CLI generation.

The qualified integration was pushed as
`e391b8b86e10a38b7193404060d6cefedbbc25ad`; remote `refs/heads/main` was read
back at that exact SHA. The isolated profiling checkout and its raw evidence
remain retained. Hosted qualification and the overall two-part goal are open.

## Owner's unattended-work preapproval — October 14

After the Bridge/claim focused checkpoint, the owner approved further measured
local fixture reuse, test scheduling and operation-local duplicate parsing/read
elimination. Historical timings may predict scheduling order, but never serve as
new performance evidence. Preserve complete native coverage, genuine validation,
fixture isolation, transaction/recovery contracts and the two-worker release
default. Cross-operation authority caching and ordinary-open validation bypass
remain excluded; materially wider scope still requires an explained decision.

The manager retains the sole source/check window for this Python qualification.
Review the scheduling contract independently before changing it: current
inventory and exact worker completion own coverage, whereas stale duration
weights are predictions. Avoid an extra full-suite capture solely to make old
weights eligible. Run focused regressions and independently review the stable
candidate before one final local full gate; report observed time and remaining
distance to the target, not an estimated speedup.

The attended design review (requested GPT-6.1 Sol / High, effective settings
unverified) is collected with no implementation or checks by the reviewer.
[ADR 0171](../adr/0171-historical-python-scheduling-predictions.md) records the
selected minimal contract and edge-case guards. Keep this scheduling change
separate from the Bridge/claim production change when reporting evidence.

The latest release instruction is **local verification and push only: no hosted
CI and no live activation**. This overrides earlier anticipated hosted/deploy
steps for the current work. The CI workflow is dispatch-only; do not dispatch
it. Leave valued projects, existing executors and old unknown attempts intact.

### Priority change and held scheduler checkpoint

The owner subsequently made parallel generation the higher priority and asked
for a Sol coordinator to carry most of that work. Python optimization is now
held, not a prerequisite to CLI progress. The manager releases the source/check
window to the existing CLI assignment after this checkpoint; no Python full
gate or further optimization runs while that window is held.

The historical-scheduling implementation passed 60 focused schedule/runner
cases, scoped F401 and diff checks. Its dedicated regression file owns the
relocated timing tests. Log:
`.local/remaining-cost/historical-schedule-checkpoint.log`. This is **not a
reviewed release candidate**: real-runner historical reporting/changed-ID
integration guards, broader completion/cleanup/ownership checks, independent
code review and full local qualification remain pending. Preserve this work,
but do not integrate it into the CLI candidate or claim measured improvement.
The earlier Bridge/claim code `d09322cb` has its own collected code review and
matched focused evidence; its full qualification can be combined with CLI.

## Separately requested Python coordinator — October 14

The owner requested a separate GPT-6.1 Sol / High Python coordinator so this
approved work can progress alongside higher-priority CLI generation. Native task
`01a13bfd-1979-7b12-9f0d-54a80eeee329` registered Relay to manager
`01a04525-e907-7630-9640-78790d69e8ae`; effective model/effort are unverified.
This supersedes the held status above. The coordinator owns the sole writer in
retained `autopilot-ux-release`, admitted clean at `6b6c2e09`; the manager is
read-only there. The separate CLI coordinator owns its own checkout. No second
source handoff is required.

Source investigation, implementation, attended read-only reviews and small
focused correctness checks may proceed concurrently. Full suites, broad module
or profile sweeps, worker experiments and timing benchmarks require the
manager's quiet-window allocation; CLI matched comparisons and final full gates
have priority. Contended diagnostic timings cannot support speed claims. Keep
default two, complete native coverage, fixture isolation, production validation
and operation-local authority boundaries. No live checkout changes, provider
generation, hosted CI, activation, global configuration or valued-data changes.
The manager owns eventual integration/publication; retain scoped commits here.

The first deliverable completes ADR 0171 real-runner history-reporting and
changed-ID integration guards, affected completion/cleanup/experiment/ownership
checks and independent stable code review. The diagnosed gap is integration
proof, not a scheduler failure: historical weights already predict ordering,
while fresh collection and worker case-ID proofs own execution coverage. Real
subprocess regressions belong at the runner boundary, without relaxing proof
validation or relabelling retained timing provenance. A ready-for-measurement
checkpoint precedes broad qualification; no measured speed gain is claimed yet.

### Reviewed historical-scheduler readiness checkpoint

The real runner now has two disposable subprocess regressions: successful
historical scheduling with changed source/IDs/counts/new/removed files, and
refusal of a zero-exit worker proving equal-count obsolete parameter IDs. Both
preserve timing-manifest bytes and verify distinct cleaned worker roots. Their
synthetic weights are test inputs, not captured performance evidence.

Focused verification passed **141 cases** across `test_python_suite_schedule`,
`test_python_suite_history_integration`, `test_python_suite_runner`,
`test_python_suite_completion`, `test_python_suite_cleanup`,
`test_python_suite_experiment`, `test_verification_module_ownership` and
`test_verify_script` (all `tests/*.py` through `verify.py focused --pytest`).
Scoped Ruff F401 and `git diff --check` passed. Log:
`.local/remaining-cost/historical-schedule-guards.log`, SHA-256
`89e235791abe3e6612355b0cecb7034d61e0bf1a1d750ec170e160629b826b07`.
The first two-case run exposed only a new test's incorrect expected diagnostic
wording; its retained log is `historical-schedule-integration.log`. Correcting
that assertion left production/runner code unchanged; the complete affected
union above passed afterwards. Contended elapsed times are not benchmarks.

Attended independent read-only review (requested GPT-6.1 Sol / Medium,
effective settings unverified) found no actionable correctness, security or
regression issues in `65cf84cd..6b6c2e09` plus the integration additions. The
reviewer ran no checks. This closes scheduler guard/review readiness, not full
local release qualification. No timing manifest was refreshed or relabelled.

CLI integration `c5c2414d` retains Bridge/claim but intentionally omits historical
scheduling and retires legacy schema2 image-receipt tests. Those removals cannot
count as Python savings. Before a fresh full/profile/matched benchmark, the
manager must reconcile current supported inventory and allocate a quiet window.
The 578.639s earlier complete run and 65.21s Bridge pair retain their original
scope; neither qualifies this checkpoint or establishes the 151.733s target.

Read-only next-slice lead: the seven geometry-lineage corruption variants each
build the same valid geometry-frame project before injecting their own fault.
A real closed seed copied into isolated roots might avoid duplicate setup while
preserving every ordinary-open corruption check. This is an unmeasured lead;
no fixture change or new authority decision is implied by this observation.

### Frozen CLI integration baseline

The manager explicitly released frozen CLI `c5c2414d` for local integration,
overriding this task's earlier no-merge restriction only. Clean merge baseline
`e1a798300b25047a92f4a7f3ea71b21a77b0ea9b` has parents `0a515687` and
`c5c2414d`; production `src`, `services`, frontend and dependency inputs exactly
match the frozen CLI tree. Scheduler code, guards, ADR and development commands
are unchanged from the Python parent. The roadmap-only conflict retains current
per-checkout ownership and historical evidence. A bounded independent Sol/Medium
read-only merge review found no blockers; no reviewer checks were run.

Minimal affected `focused` verification passed **63 cases**:
`test_python_suite_history_integration`, `test_python_suite_completion`,
`test_python_suite_runner`, `test_verification_module_ownership` and
`test_verify_script` (all under `tests/`). Log
`.local/remaining-cost/python-cli-merge-guards.log`, SHA-256
`34dc7f28cf8195242cc7c5723f6cc8fffc1c619e9c85041c3b990c5a66343576`.
The diff against frozen CLI passes whitespace checks. A merge-wide whitespace
check also reports two already-imported trailing blank lines in the frozen CLI
validator services; those source bytes were preserved. This is local merge
preservation and focused readiness, not release or performance qualification.
No separate scheduler-only full run is allocated; combined final qualification
can cover the stable source later. No push, hosted CI or activation was done.

### Current-contract geometry seed slice — preselected before implementation

Use clean integrated `e1a79830` as the before revision. The bounded target is
only the seven variants of
`tests/test_autopilot_geometry.py::test_tampered_or_missing_lineage_refuses_ordinary_open`.
The fault mutations and ordinary-open assertions stay unchanged. Exclude the
handoff matrix from this slice. Preselect the same matched union before/after:

- that seven-case geometry corruption function;
- `tests/test_autopilot_geometry.py::test_geometry_derivative_retains_original_and_no_native_job_increment`;
- `tests/test_autopilot_geometry.py::test_failure_then_restart_reuses_local_identity_without_regeneration` (two cases);
- `tests/test_autopilot_geometry.py::test_recipe_is_exif_transposed_centered_cover_at_exact_dimensions`.

This is eleven current supported cases, including unchanged real-generation,
restart/rollback and pure geometry controls. Retain collected IDs and exact
revisions; no before timing has run yet. New seed/isolation guards run separately
and cannot alter the matched inventory. Any later benchmark needs the manager's
quiet window and fresh roots, and includes real seed setup/copy cost.

Design proposed for attended independent review: create the same real current-
policy fake-host geometry-frame project once per pytest session; require no
pending fake-host work or unsettled durable attempts, close the service and all
project handles, and reject any remaining SQLite sidecars or links. Freeze the
entire fixture root, including project bytes and disposable application state.
Each case receives a complete physical copy under its unique temporary root,
a fresh storage/catalog and independent locks. Reopen through normal project
admission, recover a new typed view from the copy, then run the unchanged fault
and refusal logic. Never recreate host/service objects or dispatch from a copy;
retained attempt identities remain evidence and are neither rebound nor replayed.

Guard that seed and copies have independent file inodes, application/controller
and project locks are independent, completed CLI attempt/receipt bytes remain
unchanged, ordinary admission reads only copied project assets despite retained
absolute execution provenance, sibling copies stay valid after database/asset
mutations, seed bytes remain unchanged and active-resource/sidecar/link inputs
are refused. Preserve the logically running run and future unstarted work from
the original corruption scenario; do not pause it or invoke product snapshot/
restore. This fixture-only quiescence means stopped service, closed handles and
no unresolved native attempts, not production lifecycle-close eligibility.
No writable handles or parsed authority are shared; no production validation
is skipped or cached. Extend ADR 0158's existing closed-seed contract
with this narrowly scoped geometry consumer after review. Retain unchanged
whole-generation paths outside the seven corruption variants.

### Geometry fixture implementation checkpoint

The reviewed seed/copy design is implemented under ADR 0158's narrow extension.
One real current-contract setup reaches the first geometry frame; all fake-host
statuses/persisted attempts are terminal, pending work is empty and service/
project resources are closed. Copies retain exact evidence but never construct
a host/controller or dispatch. Each copy uses independent physical files,
application state, catalogs and locks and opens through full ordinary admission.
The seven original fault mutations and refusal assertions are AST-identical to
clean integrated `e1a79830`; generation/restart controls retain fresh setup.

The first **23 focused cases passed** (nine seed guards, seven corruption
variants and seven ownership checks). After preflight tightening to reject links
before opening even lock paths, **27 focused cases passed**: the eleven
preselected cases, nine isolation guards and seven module-ownership checks.
Log `.local/remaining-cost/geometry-seed-guards.log`, SHA-256
`ec2931f40b8891aed08759b7098bb73a2e4173f4a83d648aab05b7cc1c8cd56e`.
Scoped Ruff F401 and diff checks passed. Two already-unused imports in the
touched geometry module were removed. The root conftest's declared consumers
now include story-authoring as well as graph; all seven ownership guards passed
again for that manifest-only correction (`geometry-seed-ownership.log`).
No production source or dependencies changed.

The attended independent Sol/Medium stable code review found no actionable
issues and ran no checks. It confirmed resource closure, independent copies,
normal admission and unchanged corruption coverage. Guard evidence includes
successful copied asset reads while the seed location is unavailable, exact
attempt/receipt preservation, sibling database/asset/application mutation
isolation, independent project/controller locks, and refusal of active resource,
sidecar, symlink, hard-link, FIFO or changed-byte seeds. Seed hashes stay intact.

The exact preselected eleven IDs match before/after in
`.local/remaining-cost/geometry-seed-{before,after}-native-cases.txt`; their
sorted native-ID fingerprint is
`68c0c97fad698898aad733dc81c9299573c1e7038c34056c4cab06f781047ad0`.
Before is immutable integrated `e1a798300b25047a92f4a7f3ea71b21a77b0ea9b`;
after is committed `b8b6b8868980baf1103a196bcef9b457a1a6f69e`. Fresh benchmark commands must include session
seed creation and physical copy cost, use the same eleven selectors and fresh
temporary roots, and run only in a manager-allocated quiet window. New guards
remain outside that matched union. Contended correctness runtimes are not
performance evidence, and no timing manifest was rewritten.

This is implementation/focused-review readiness, not measured speed or full
release qualification. Combined final full qualification, quiet before/after
measurement, publication and product acceptance remain separate. The original
85-percent / 151.733s fixed-resource target remains unmet; keep default two.

### Geometry matched quiet measurement — October 14

The manager explicitly allocated one short quiet pair after verifying the CLI
run was terminal and provider/heavy checks were held. Both exact preselected
**eleven-case** native focused commands passed, with byte-identical collected
inventories and the previously recorded `68c0c97f...` native-ID fingerprint.
Before: clean detached `e1a798300b25047a92f4a7f3ea71b21a77b0ea9b`.
After: clean detached `b8b6b8868980baf1103a196bcef9b457a1a6f69e`.
The observer restored clean main at preserved
`d039efedabf614809ca111998699f1b7c0e93234` in its finally path; the quiet window
was promptly released before this documentation-only receipt.

External complete-command time was **89.454s before /
38.556s after**, a **56.90% reduction**
in this one scoped pair. Pytest reported **83.53s / 33.83s**. The measured command
is `uv run --locked --no-sync python scripts/verify.py focused`, with the exact
four `--pytest` selectors frozen above (seven corruption cases plus derivative,
two restart cases and pure-recipe control). External timing includes command
startup, all four native selector preflights, pytest collection, real session
seed creation, full physical copies and all test/cleanup work. Separate native
inventory capture and fingerprint reads occurred outside the timed command.
No new isolation-guard cases enter this matched performance union.

Both runs used the same absolute checkout, locked interpreter and dependency
inputs. Each used a fresh distinct `TMPDIR` under its retained evidence root;
`PYTHONDONTWRITEBYTECODE=1` and no ambient pytest selection were present. Input
fingerprints remained stable before/after each run: before
`64469ddc503f2c11ff2de2b05853eb1b9cb1b50d26c6e6ef6b321ca66a4c2630`;
after `c1abfaab446925b8ac5c0630f3d55e6ef77256faca0ff4622b297668f7c609e4`.
The common host fingerprint was
`e157fcd2c8db7127845d443a20785aff48490f424fcbfe1eb56ec31bb040db92`.
Python executable/version, lockfile, project dependency declaration, Python
version file and retained timing-manifest hashes matched across the pair. The
timing manifest was never rewritten. Metadata retains the exact environment
whitelist and full dependency hashes without credentials.

Evidence root: `.local/remaining-cost/geometry-quiet-6gvu0pg8/`.
Each `before/` and `after/` contains `focused.log`, `collection.log`, `cases.txt`
and `metadata.json`; `result.json` binds the command, revisions, environment,
inputs, times, exit codes, reduction and restored main. SHA-256 values:

- before `focused.log`: `8c1c2d18a75a46e09d97b060ad071e1f36256f67f648cff7629f84aa1cbd9499`;
- after `focused.log`: `76e6d6757c080f5c7ec50a1469f95d8ad70d25a8d884df602ad0711edb00d44b`;
- byte-identical ordered `cases.txt`: `d69c7a611d6574ce09d7c0e32385ba396fe2c69ff65130f8b93e9cade19121a6`;
- `result.json`: `8bcfc999055fa62fd13dd103339b033543ed70b30074ae17993bcb6694b43aa2`;
- observer `.local/remaining-cost/geometry_quiet_pair.py`: `b89c2795af125f13db374934501df479117facf98cc6983f334b2e57b7e9edf9`.

This demonstrates a measured saving for repeated real geometry setup while
preserving all eleven selected cases, including unchanged generation/restart
controls. It is one ordered pair, not a repeated median, whole-suite gain or
release qualification. Starlette/httpx emitted its existing deprecation warning
in both runs; no case failed or was omitted. Complete-suite measurement and the
combined stable final full gate remain pending. The original fixed-resource
85-percent / 151.733s target remains unmet; default workers remain two.
No handoff implementation, provider execution, hosted CI, push or activation
was performed by this measurement.

### Five-defect handoff fixture slice — frozen before implementation

After auditing the geometry pair, the manager released the proposed handoff
fixture implementation under the existing owner fixture-reuse preapproval.
Clean before baseline is `140b4a3117d49908e761fe72925c24f14dd8bc2b`.
Preselected native cases, captured before editing, are exactly eight:

- `tests/test_autopilot_handoff.py::test_invalid_whole_handoff_creates_no_partial_human_authority` (five defects);
- `tests/test_autopilot_handoff.py::test_exact_human_handoff_preserves_machine_origin_and_withdraws_after_edit`;
- `tests/test_autopilot_handoff.py::test_mid_handoff_failure_rolls_back_all_native_human_rows`;
- `tests/test_autopilot_handoff.py::test_takeover_accepts_current_bundle_and_explicit_unassessable_authorization`.

Ordered IDs are retained in
`.local/remaining-cost/handoff-seed-before-native-cases.txt`; sorted native-ID
fingerprint: `25b6162b971cf349bb919944219bf3f8144401ef15d2b90d4ade0a9d0a9f254f`.
A future matched pair must use these same eight cases and unchanged controls,
fresh roots and complete command time including real seed construction/copies.
No handoff timing, broad/module/profile/full run or provider call is allocated.
The manager will separately allocate a quiet measurement window.

Build one genuinely completed current-policy two-route/six-frame/two-reference
`awaiting_review` seed, with terminal successful attempts, no pending host work,
stopped controller, closed DB/lease resources and zero human facts. Reuse full
physical copies only for the five invalid cases. Each copy computes fresh
`review_material` and request observations, preserving all six original
zero-partial-authority table assertions. The three controls retain real fresh
setup; never pre-create human authority or cache a review/request in seed data.

Reuse only the already-proven closed-tree hash/physical-copy/lock guards in a
cohesive test helper. Geometry and handoff builders keep separate state-specific
preconditions; do not turn either into a permissive generic state factory.
Keep completed attempt identities and absolute execution provenance immutable.
Add a positive-copy guard exercising genuine human handoff and video eligibility
in one disposable copy while seed and sibling remain `awaiting_review` with
zero human authority. Verify copied assets/evidence, independent physical files,
seed immutability and fresh rollback/refusal paths. Scope stays test-only; no
production admission, identity, rollback, validation or ordinary-open bypass.

### Handoff fixture implementation readiness

The five invalid consumers now use a real completed awaiting-review seed. Its
builder preserves two routes, six frames, two references and sixteen successful
terminal attempts/receipts, with no pending host work or reserved output and
zero rows in all six human-authority/video tables. Service/thread/controller and
project handles close before the complete project/application root is frozen.
Only reviewed physical-copy/hash/inode/OS-lock guards moved into
`tests/autopilot_seed_fixtures.py`; state-specific geometry and handoff builders
and copy wrappers remain distinct. Copies create fresh storage/catalog owners
and never construct a host/controller, continue native work or rebind evidence.

The five fault mutations, fresh review/request construction, rejection checks
and all six zero-table assertions are AST-identical to baseline, as are the
complete three fresh-setup controls. Native collection retains the exact eight
before/after IDs in
`.local/remaining-cost/handoff-seed-{before,after}-native-cases.txt`.
New isolation guards are outside this prospective matched union.

**23 focused cases passed**: five invalid handoffs, two new handoff copy guards,
nine affected geometry-copy guards and seven module-ownership checks. The three
unchanged successful API/withdrawal, mid-handoff rollback and takeover controls
then passed separately with their original fresh setup (**26 distinct cases**
in total). Retained logs and SHA-256:

- `.local/remaining-cost/handoff-seed-guards-first.log`:
  `33599292c2fd738d9b7963cb08d54683b3325af0b03b3ea4701cb1dd06302862`;
- `.local/remaining-cost/handoff-seed-controls.log`:
  `bf3c2280a9261a2399c8c2a73200d042f82240f35d141c58480f04c41e329141`.

Scoped Ruff F401 and diff checks passed. Both focused commands used native
`verify.py focused --pytest` selections; their elapsed times are correctness
observations under concurrent CLI priority, not speed evidence. The existing
Starlette/httpx warning remains; no selected case failed or was omitted.

Attended independent stable Sol/Medium read-only code review found no actionable
findings; effective settings are unverified and the reviewer ran no checks. The
positive-copy guard executed a real human handoff and video-eligibility check in
one disposable copy while the seed location was unavailable, preserved exact
sixteen attempt/receipt rows, established independent file inodes and left the
sibling and a new seed copy awaiting review with all six authority tables empty.
The seed's complete hashes stayed unchanged. A second guard rejects mixing the
first-geometry and completed-handoff seed states. Production source, frontend,
dependencies, ordinary-open validation, identity and rollback are unchanged.

The before revision remains clean
`140b4a3117d49908e761fe72925c24f14dd8bc2b`; the after executable checkpoint is
`f1e72a3099ddc228c40fc1918512f9fd1470ba74`. Handoff performance, full release qualification
and publication remain open pending manager allocation. The earlier geometry
pair stays bound to its exact `e1a79830`/`b8b6b886` inputs; extracting common
copy code does not relabel it as a fresh measurement of this newer candidate.
No timing manifest rewrite, moving-CLI merge, provider call, broad/module/full
run, push, activation or cleanup was performed for this slice.

### Additional original geometry-consumer check

The manager's read-only source audit found no concrete issue and requested the
original seven geometry corruption cases in addition to the nine copy-isolation
guards already run. On clean executable `f1e72a30`,
`uv run --locked --no-sync python scripts/verify.py focused --pytest tests/test_autopilot_geometry.py::test_tampered_or_missing_lineage_refuses_ordinary_open`
passed **all seven cases**. Log:
`.local/remaining-cost/handoff-seed-geometry-consumers.log`, SHA-256
`fea0ba239975d505f8c76d952c58a64e00217112d85fc42eec3cecc89190f72c`.
This closes the affected consumer selection after extraction. Together with the
23-case guard union and three fresh handoff controls, **33 distinct focused
cases passed**. No failures or omitted selected cases remain. This additional
check is correctness coverage, not another timing claim or full gate.

The stable implementation remains `f1e72a30`; subsequent receipt changes are
documentation-only. Before/after eight-case inventory and sorted native-ID
fingerprint `25b6162b971cf349bb919944219bf3f8144401ef15d2b90d4ade0a9d0a9f254f`
remain frozen. The clean reviewed checkpoint is ready for a separately allocated
quiet matched pair; no handoff benchmark, combined full qualification, push or
activation is claimed.

### Handoff matched quiet pair — October 14

The manager allocated a natural CLI quiescent window after confirming no native
or check processes. Both exact preselected **eight-case** complete native
`verify.py focused` commands passed. Before was clean detached `140b4a31`;
after was clean detached `f1e72a30`. The observer's finally path restored clean
main at `cd3a99ad46983f527ba37fbe596907a0791e8584`; the timing/check window was
promptly released before this documentation-only receipt.

External complete-command time was **99.715s before /
53.505s after**, **46.34% less wall time**
in one scoped ordered pair. Pytest reported **93.17s / 48.45s**. Timing includes
command startup, all four native selector preflights, collection, real session
seed setup, physical copies and all eight tests/cleanup. Separate collection
proof/fingerprint reads are outside the timed command; no extra guard cases
entered the matched union. Fresh distinct per-run temporary roots, same absolute
checkout, interpreter/version, locked dependencies and environment were used.
No ambient pytest selection was present. The existing Starlette/httpx warning
appeared in both runs; no selected case failed or was omitted.

Input fingerprints stayed stable within each run: before
`c1abfaab446925b8ac5c0630f3d55e6ef77256faca0ff4622b297668f7c609e4`; after
`7c6ac6ccde2a226dc34ce49ed29d2b1c4eee737bf93246fdb760a17c8321c20f`.
Host, interpreter/version, dependency declaration, lockfile, Python version file
and timing-manifest hashes matched between runs. The timing manifest was never
rewritten. Ordered eight-case lists are byte-identical and retain sorted-ID
fingerprint `25b6162b971cf349bb919944219bf3f8144401ef15d2b90d4ade0a9d0a9f254f`.

Retained root: `.local/remaining-cost/handoff-quiet-1l6f0mdj/`, with per-run
`focused.log`, `collection.log`, `cases.txt`, `metadata.json` and pair
`result.json`. SHA-256:

- before `focused.log`: `0ad337a3330b926a10e96435ec71a9c4fa6e7b489ec8a6e7c0c472bdfd13f84c`;
- after `focused.log`: `8edee4fe89a9ad528f6c58401ba3425196559e65a840ea802e52028684a5ec08`;
- byte-identical ordered `cases.txt`: `1452d54ba461ffafedc9dbb760d69b8e4d6fc0788ba834680374e3ad528550a4`;
- `result.json`: `f02e8cd51af7f3089e3a5782213794a445c07d2a967a1b3764ff7777653a6e2e`;
- observer `.local/remaining-cost/handoff_quiet_pair.py`: `c36fbd0600771a801b505d9ba9a9f82f135c762cca03090dbe610f5e33a9ee1c`.

This is a measured saving for the exact eight cases, including three unchanged
fresh end-to-end controls. It is not a repeated median, whole-suite saving,
85-percent result or full release qualification. Keep the original fixed-resource
151.733s target open and default workers two. No broad/module/full run,
profiling, provider execution, push, live activation or data cleanup occurred.
The manager retains final integration/publication and quiet-window allocation.

### Terminal-reconciliation accepted-Script reuse — design selection

Continue the owner's approved local fixture-reuse track from clean
`4f6f6804438f346e50b920a69351602d68a550ae`. Retained schema-1 history records
`tests/test_specialist_terminal_reconciliation.py` with 62 cases, 38.642s setup,
20.656s call and 0.067s teardown (59.366s total). This is historical
prioritization, not a fresh timing claim. That test file and its
`specialist_reconciliation_support.py` are unchanged from `b4f831da`.
`ReconciliationRuntime` source shows every case rebuilds the same real accepted
Source/Cast/Art/Script precondition before creating fresh registry/dispatch state.
This setup, unlike each case's terminal/refusal behavior, is repeated work.

Bound the candidate to three failure matrices (38 cases):
`test_missing_or_invalid_terminal_delivery_holds_all_stage_reservations` (18),
`test_terminal_identity_and_pin_failures_never_release_or_relabel` (15), and
`test_terminal_exchange_identity_and_provenance_failures_hold_reservation` (5),
all in `tests/test_specialist_terminal_reconciliation.py`. Keep its six-case
`test_cancelled_terminal_proof_survives_restart_and_never_changes_new_head_or_another_lease`
control on the original fully fresh runtime. These exact **44 native IDs** are
frozen before code in
`.local/remaining-cost/reconciliation-seed-before-native-cases.txt`, sorted-ID
fingerprint `0b834fbf99b6b8829b740ba7846f3c9cc53e4d3a1b0fe3a8d7a92e0a4dad9010`. All other runtime consumers
retain their existing default fresh setup. No test selection/count is removed.

Proposed new boundary for independent design review: build the exact real
accepted F4 Script project once, validate accepted owners and absence of any
active candidate, autopilot/native attempt or publication reservation, then
close every handle and freeze its complete project home. Copy only that home
physically into each selected case's fresh output root, re-open through normal
admission and configure a completely new application/registry/task binding/
dispatch tree for that case. Never copy active dispatch, queued/unknown work,
registry roots or a controller. Keep per-case prepare/export/send/delivery/
cancel/check and every reservation/database/file invariant unchanged.

Reuse the already-reviewed pure complete-tree hash/regular-file/sidecar/link
validation, and explicit physical-copy/inode/project-lock checks. The project
has no autopilot controller, so do not create a fake lock or weaken the existing
autopilot two-lock contract to fit it. Keep the new accepted-Script preconditions
separate; no generic permissive seed state factory or production change.
Positive isolation guards should prove independent registries/dispatch paths,
projects/locks/files and mutation isolation with original seed unavailable and
unchanged. Native sends stay fake, while actual package/terminal validation and
OS/SQLite authority remain real. Stable code review and small focused checks
precede the clean checkpoint; a matched pair needs a new manager quiet window.

### Terminal-reconciliation implementation readiness

The reviewed accepted-Script seed boundary is implemented only for the selected
38 failure cases. The real builder verifies current accepted owners, all
candidate rows terminal accepted, no close/publication blockers and absence of
autopilot/native/media work, then closes the handle and freezes only the whole
project home. Copies retain exact hashes/inodes and exclusive source project
locking and enter normal admission. Application state, registry/task UUIDs,
dispatch roots and queue-call lists are fresh per case. The default runtime and
all other consumers retain their original fresh construction. Autopilot copy
code/two-lock semantics are unchanged; only its pure file-validation function
is reused with declared transitive ownership.

**47 focused cases passed**: 38 selected refusal/identity/provenance variants,
two new seed-isolation/proof guards and seven ownership checks. The six unchanged
all-stage fresh controls passed separately (**53 distinct focused passes**).
All failure-case bodies and the fresh control are AST-identical to baseline,
except the explicit seeded-fixture argument/local alias. No assertion or case
was removed. Native before/after collection retains the same 44 IDs and sorted
fingerprint `0b834fbf99b6b8829b740ba7846f3c9cc53e4d3a1b0fe3a8d7a92e0a4dad9010`.
Retained logs and SHA-256:

- `.local/remaining-cost/reconciliation-seed-guards-first.log`:
  `eb0bfcac85efe0ff6bf3126aba84454660f271611f45fc20cfeca21d9767e4c4`;
- `.local/remaining-cost/reconciliation-seed-fresh-controls.log`:
  `c5ce527e774a8b85f759b17b9ff1143b9caf348e76c8d8408a8c1400add66df0`.

Scoped Ruff F401 and diff checks passed. The existing Starlette/httpx warning
appeared; no selected case failed or was omitted. Focused elapsed times are
concurrent correctness evidence, not a performance comparison.

Attended independent Sol/Medium design and stable code reviews found no
blocker/actionable finding; effective settings are unverified, and the reviewer
ran no checks. New guards prove normal copied branch-package paths, fresh task
UUIDs/registries/calls/jobs, independent inodes and reservations, terminal proof
releasing only its own copy's lease while the original seed is unavailable,
exact database/package preservation, separate project locks, refusal of an
active seed and database/package mutation isolation. Seed hashes remain intact.
Accepted package evidence is neither rewritten nor rebound. No parsed authority,
registry reservation or active job is shared between cases.

Before stays immutable `4f6f6804438f346e50b920a69351602d68a550ae`; executable
after is `8aedede95f38ab8511bd296195fdf5c4d815ba70`.
Production/frontend/dependencies/timing-manifest inputs have
no diff from that baseline. This is reviewed implementation/focused readiness,
not measured speed, full qualification, hosted CI or product acceptance. A
quiet matched complete-command pair needs manager allocation. Keep default two,
complete native coverage and the original 85-percent target open; no broad,
module/full, profile, provider, moving-CLI merge, push, live or cleanup occurred.

### Terminal reconciliation quiet pair — October 14

After CLI explicitly released the quiet resource window, the manager allocated
exactly one matched complete-command pair against immutable before
`4f6f6804438f346e50b920a69351602d68a550ae` and executable after
`8aedede95f38ab8511bd296195fdf5c4d815ba70`. The four frozen selectors above
retained all 44 native IDs, including six unchanged fresh all-stage controls.
Sorted native fingerprint stayed
`0b834fbf99b6b8829b740ba7846f3c9cc53e4d3a1b0fe3a8d7a92e0a4dad9010`.

Both commands passed all 44 cases, exit zero. External complete-command wall
time was **40.95796179199533 → 22.25733779199072 seconds**, a
**45.65809230199387-percent reduction** in this selected group. Pytest reported
36.71 → 18.23 seconds. The external timer includes the runner's native-selector
preflight, collection, real seed construction, complete physical copies, test
execution and cleanup. A separate native collection retains the exact inventory.
Fresh per-run TMPDIR roots, the same absolute checkout/interpreter/dependencies/
environment policy and unchanged manifest were used. Input fingerprints were
stable before/after each pinned run; host/interpreter/dependency/manifest values
matched across the pair. The input fingerprint itself intentionally differs
between executable revisions. No manifest was rewritten or relabelled.

Evidence root `.local/remaining-cost/reconciliation-quiet-ajfc16x2/` retains
`before/` and `after/` collection logs, native cases, focused logs and metadata,
plus `result.json`. SHA-256:

- before `focused.log`:
  `5914081bfab4e6f3e81f043a860d4d987a73bd333df29b80bceb5a29067fbae9`;
- after `focused.log`:
  `eb67c3e4a121229acd6c13f7da8ea0dd1b83a1777c1740c3f12f694a5831aaf2`;
- `result.json`:
  `f3ef0e7a92ee10115b252e32b21eb8a7142c36606aa6fcbfd53a88d62ee97404`;
- observer `.local/remaining-cost/reconciliation_quiet_pair.py`:
  `1aaf70371576bd38726eea88c498fa64f68192748b51878f8796bd409cafa130`.

Native session 22282 completed once, with no retries. Its `finally` restored the
exact clean starting `main` at `9161caea84a02bcb2fd4c766b10bd8dd5136b0ee`.
The manager independently inspected the observer, actual logs/hashes, native
inventory equality, assertions and restored checkout, and accepted the one-pair
measurement. Resources were idle before a separately authorized Bridge pair.
The existing Starlette/httpx warning appeared. No whole-suite speed, 85-percent
achievement, combined full qualification, hosted CI or product acceptance is
established by this scoped comparison; default workers remain two.

## Pending native Bridge seed — selected implementation

Historical manifest attribution assigns repeated accepted-project construction
to the native intent/presentation setup owners (22/21 cases; 19.515/23.473 setup
seconds). This is prioritization evidence, not current measured speed. The
reviewed fix belongs in test setup: share a closed real nine-shot pending project
only across 22 specified negative cases; keep native authority/dispatch fresh.
No production optimization or admission bypass is needed. ADR 0158 records the
boundary and independent Sol/Medium design review found no blocker.

Frozen before is `99954dc584060266790d4df90825e8fd0c3a8312`. The 26-case
matched union comprises presentation's eight invalid-candidate and five invalid
delivery variants, intent's five identity/pin and four send-recheck failures,
and four unchanged fresh positive/unknown-dispatch controls:
`test_delivery_prefills_advice_without_changing_proposal_then_explicit_save`,
`test_prepare_send_validated_delivery_requires_explicit_whole_package_review`,
`test_unknown_send_and_reopen_never_resends`, and
`test_unknown_send_reopens_same_job_without_resending_or_api_reconciliation`.
Before IDs are retained in
`.local/remaining-cost/native-bridge-seed-before-native-cases.txt`; sorted
fingerprint `365c4c8fc6e9a8af90bfb80d49cb9167912abd84a6f993a67c2e3bf4a593383d`.
New copy/closure guards run separately. No timing/full/profile/provider work is
authorized by this selection; the terminal pair remains queued separately.

The implementation builds the original `_pending_project` 9/9 project, verifies
current source/outline/map/graph and all four accepted creative owners, only
accepted candidate rows, no close/publication blockers, no native/autopilot/
generation/media/reference work, a current pending noninstallable Bridge with
reviewed presentation, blank pending intent and no installation/job/candidate.
The store closes before the complete home is frozen under its existing project
lock. Application/registry/dispatch state is never copied. Accepted execution
pins and completed package bytes are preserved; only closed-home freeze metadata
was extracted from reconciliation, leaving its builder conditions and the
autopilot two-lock path unchanged.

Copies pass full-tree hashes and independent inode checks, normal project
admission and the same pending-state assertions, then read proposal identity
anew. Each runtime creates fresh settings/task UUIDs, registry, native service,
pin, job, export and queue-call list. Presentation's prepare/author-intent edit
still runs per case. Default fresh fixture behavior, including its original
pin seams, remains equivalent. All 19 original test-function ASTs are identical
to baseline except four selected fixture arguments/local aliases; no failure
assertion or fresh control was removed.

**34 focused cases passed**: 22 selected failures, three new guards, two
reconciliation-copy guards and seven ownership checks. The four unchanged fresh
positive/unknown-dispatch controls passed separately (**38 distinct cases**).
The earlier three-guard smoke run also passed. Exact 26 native IDs and the
recorded fingerprint match before/after; after inventory is
`.local/remaining-cost/native-bridge-seed-after-native-cases.txt`.
Retained evidence SHA-256:

- `native-bridge-seed-isolation-first.log`:
  `be05bdb661712d1d4f9b03148e683746c2ccb4a6b87a05861f21f5a1ad18e429`;
- `native-bridge-seed-guards.log`:
  `26d45df91f2b71a9f0f4a275adcb45352f0c99d94df959e048472d548f53e14a`;
- `native-bridge-seed-fresh-controls.log`:
  `1ff787e6fe8cfd417f007fd2f3ec9771b5d76263450e1690df2b9810c818b062`.

Logs are under `.local/remaining-cost/`. Scoped Ruff F401 and diff checks passed;
the existing Starlette/httpx warning remains. These concurrent focused results
are correctness evidence, not measured performance. Attended independent
Sol/Medium design and stable code reviews found no blocker/actionable finding;
effective settings are unverified and the reviewer ran no checks.

New guards admit both real fake-native intent and presentation advice and serve
their derived reports while the original seed is renamed unavailable. No copy
is installed/approved. The sibling keeps its exact proposal/database/reservation
while only the completed copy releases its own lease; task IDs, jobs, call lists,
project/package/dispatch paths and inodes are independent. Separate project locks,
active-source refusal, package mutation isolation and incompatible Script-only
seed refusal pass. Seed hashes remain exact. No production/frontend/dependency/
timing-manifest changes, full/module/profile/provider calls, moving CLI merges,
push, live checkout changes or cleanup occurred. Scoped readiness does not claim
full qualification, hosted CI, product acceptance, measured Bridge savings or
achievement of the unchanged 85-percent target. Default workers remain two.

Frozen executable after is `3c17594927cfb43ea65ef77ac31a08e41826d675`;
before remains `99954dc584060266790d4df90825e8fd0c3a8312`. The retained
checkout is clean at the local checkpoint, with no push. The earlier terminal
pair remains bound to `4f6f6804` → `8aedede9`; do not silently retarget either
comparison to a later source revision.

### Native Bridge quiet pair — October 14

The manager separately allocated exactly one Bridge comparison while CLI kept
the explicit quiet window held. Immutable before was
`99954dc584060266790d4df90825e8fd0c3a8312`; executable after was
`3c17594927cfb43ea65ef77ac31a08e41826d675`. All 26 native IDs matched,
including the four unchanged fresh positive/unknown-dispatch controls. Sorted
fingerprint stayed
`365c4c8fc6e9a8af90bfb80d49cb9167912abd84a6f993a67c2e3bf4a593383d`.

Both complete focused commands passed all 26 cases, exit zero. External wall
time was **32.44459995800571 → 18.408682709006825 seconds**, a
**43.261181420532566-percent reduction** for this selected group. Pytest
reported 24.93 → 11.23 seconds. The timer includes runner selector preflight,
collection, real seed build, full physical copies, execution and cleanup. Fresh
per-run temporary roots and the same checkout/interpreter/dependencies/host and
environment policy were used. Within-pin input fingerprints stayed stable;
host/interpreter/dependency/manifest values matched across the pair. Separate
native collection proved inventory equality. Manifest bytes remained unchanged.

Evidence `.local/remaining-cost/native-bridge-quiet-1h38zjcz/` retains per-run
`collection.log`, `cases.txt`, `focused.log`, `metadata.json` and `result.json`.
SHA-256:

- before `focused.log`:
  `e4f3ce73c085788500bf8d63952f53e768ba1e6a773b744fc22e5b7af7ebe03d`;
- after `focused.log`:
  `7024c823572eeabebc21027b1f336531d3930ee615220908a3a11c6c3c3c47a6`;
- `result.json`:
  `4cf5a3e7b75458c4cca4c4319161c6692a2fa8d86204bbb2d5649c726ea6adec`;
- observer `.local/remaining-cost/native_bridge_quiet_pair.py`:
  `edf07a85ec1e9d849a9a93cdee35a5fc971568e24fac5730fff2d8b8cf15c06e`.

Native session 6478 completed once without retry and restored exact clean
starting `main` `9161caea84a02bcb2fd4c766b10bd8dd5136b0ee` in `finally`.
The manager received the terminal result and idle-resource notification before
this documentation-only receipt. The existing Starlette/httpx warning appeared.
These are separate one-pair observations; do not add their percentages or infer
whole-suite timing, 85-percent achievement, full qualification, hosted CI or
creative/product acceptance. No production/frontend/dependency/timing-manifest
change, broad/full/module/profile/provider call, push or live-checkout write
occurred during either comparison. Default workers remain two.

## Text lifecycle-ownership seed — selected implementation

The manager released the prior quiet window and authorized the independently
reviewed next bounded consumer extension. Historical attribution for
`test_project_specialist_ownership.py` is 22 cases / 20.238 call seconds;
inspection shows the selected text cases repeatedly build the same accepted
F4 Script project in `ReconciliationRuntime`. This setup duplication belongs
in the existing optional seed path, preserving fresh dispatch/lifecycle work.
No production optimization or authority change is required. ADR 0158 records
the selected boundary; independent Sol/Medium design review found it safe and
requested a close/snapshot proof with the original seed unavailable.

Frozen before is `7fb557c96e11d02e8d175b33199659cc0f2574d5`.
Seed only ten `test_cancelled_text_blocks_only_owner_until_exact_proof`
variants and four `test_crash_windows_retain_owner_without_guessing_from_publication`
variants. Preserve all refusal/settlement/restart/lifecycle assertions. The six
`test_cancelled_images_are_project_owned_until_reviewed_terminal` variants,
`test_unsent_cancel_does_not_invent_ownership` and
`test_dispatch_and_lifecycle_use_project_before_registry_lock` keep fresh setup.
The entire affected file is the frozen 22-case comparison. Native collection
is retained at `.local/remaining-cost/ownership-seed-before-cases.txt` and
`ownership-seed-before-native-cases.txt`; sorted fingerprint is
`485f16674e0d55e7409c2d43a7d8e015c13b57fa9035e25e24a00bec35c0c86f`.
The extended positive guard and ownership checks run separately. No timing,
profile/module/full/provider work or moving CLI integration is authorized by
this selection. Default workers and the original 85-percent target stay fixed.

The implementation only adds the existing seed fixture argument and optional
runtime keyword to the two selected test functions. Their lifecycle refusal,
queued/unknown terminal proof, restart, settlement, close/snapshot and crash
mutations are unchanged. All five test-function ASTs match baseline after
normalizing those two setup arguments; the eight fresh controls are unchanged.
No helper, application, registry, native execution or production code changed.
The existing seed guard now closes its settled copied store and project, then
creates a real copy-local snapshot while the original seed is unavailable.
It proves the active sibling's exact database/lease and busy state remain
unchanged, then restores the seed and verifies its complete inventory/hashes.

**23 focused cases passed**: 14 selected lifecycle cases, two seed guards and
seven ownership checks. All eight unchanged fresh controls passed separately
(**31 distinct focused passes**). Exact 22 native IDs and sorted fingerprint
match before/after; after inventory is
`.local/remaining-cost/ownership-seed-after-native-cases.txt`.
Scoped Ruff F401 and diff checks passed. Retained evidence under
`.local/remaining-cost/`:

- `ownership-seed-guards-first.log`, SHA-256
  `93d73279a6231a29e5a9f9412a4319a07b8b437560ffe3b27782aa97a2aefd07`;
- `ownership-seed-fresh-controls.log`, SHA-256
  `c9d506b46c6bbdf537e720278d55d4067deecee057019c998b7e3024dc0db4da`.

An attended independent Sol/Medium stable code review found no actionable
finding and ran no checks; effective settings remain unverified. The existing
Starlette/httpx warning appeared. Concurrent focused command times are not a
performance comparison. No production/frontend/dependency/manifest changes,
provider calls, broad/module/full/profile runs, moving CLI merges, push, live
checkout writes or cleanup occurred. Implementation/focused readiness is
separate from measured savings, combined full/hosted qualification and product
acceptance. This 22-case speed comparison remains queued for a quiet allocation;
prior accepted pair refs/results remain immutable.

Frozen executable after is `83e2275d04d3192c36162503a1e63751560cad55`;
before remains `7fb557c96e11d02e8d175b33199659cc0f2574d5`. These refs qualify
the bounded readiness above. A later docs-only receipt does not retarget this
comparison or earlier accepted pairs.

## Fake API Bridge seed — selected implementation

The next reviewed lead reuses the already qualified exact 9/9 pending Bridge
seed for five fake API failures. Inspection of
`tests/test_production_bridge_intent.py` shows identical `_pending_project`
construction; historical ten-case call cost was 10.251 seconds, used only for
prioritization. Copying closed state belongs in test setup; fresh worker/profile/
service/job authority and all original assertions remain per case. Independent
Sol/Medium read-only design review found no mismatch and selected an API-specific
seed-unavailable positive guard. ADR 0158 records this boundary.

Frozen before is `2f57f598f9bdac67f6bce10012b351344b4bf7a3`. Select three
`test_invalid_or_unknown_result_never_mutates_proposal` variants,
`test_late_model_result_cannot_replace_author_edit_or_cancellation` and
`test_stale_brief_cannot_admit_late_inference`. All five remaining native
cases stay fresh. The complete original file is the frozen ten-case comparison;
before collection/native IDs live at
`.local/remaining-cost/api-bridge-seed-before-{cases,native-cases}.txt`, sorted
fingerprint `ffc5c5553ba6c48263cbddbcb8422cec3b43a398467a8bc9ef05f2969f9cc0ca`.
New positive/affected copy guards and ownership checks run separately. No
benchmark, broad/module/full/profile/provider run or production change is
authorized by this selection; prior timing refs remain frozen and default
workers stay two.

Only the three selected test functions acquire a complete physical pending
project copy; fake adapter/resolver/broker/profile/service/thread/job creation
and all original sequencing/assertions remain unchanged. All eight original
test-function ASTs match baseline after normalizing those three setup arguments
and project-acquisition statements. The five remaining native cases stay fresh,
including installation, author edit/reinference, target binding, unknown restart
and secret nonpersistence. Existing seed/copy helpers are unchanged; declared
creative-production ownership covers the new/transitive support dependencies.

The new API-specific guard opens two normal copies, freezes sibling database/
proposal, then renames the original seed unavailable before constructing its
fresh fake API service and creating a job. It proves dispatched text-API/profile
ownership, one adapter call, ready model advice, exact expected revision and job
provenance, no installation, and unchanged sibling database/proposal. Cleanup
releases the held adapter before executor shutdown, restores the seed even if
shutdown fails, and verifies its full original inventory/hashes. Existing native
guards continue to prove locks, complete copies, independent inodes and leases.

**16 focused cases passed**: five selected failures, the new API guard, three
native seed guards and seven ownership checks. Five unchanged fresh controls
passed separately (**21 distinct focused passes**). Exact ten native IDs and
the recorded sorted fingerprint match before/after; after inventory is
`.local/remaining-cost/api-bridge-seed-after-native-cases.txt`. Retained logs
under `.local/remaining-cost/` and SHA-256:

- `api-bridge-seed-guards-first.log`:
  `ca46b037243d79bbb1354f01e44294ecca55203cf804851ced18316a943a5558`;
- `api-bridge-seed-fresh-controls.log`:
  `d5776c269ac05058fe35a0c336c12770bfb13e89a735a75517bbd8f07844dae2`.

Scoped Ruff F401 and diff checks passed. Attended independent Sol/Medium stable
code review found no actionable finding and ran no checks; effective settings
remain unverified. The existing Starlette/httpx warning appeared in the union
that imports route helpers. Concurrent focused results establish scoped
correctness, not speed. No helper/production/frontend/dependency/timing-manifest
changes, real provider calls, broad/module/full/profile checks, moving CLI merge,
push, live checkout write or cleanup occurred. This ten-case comparison needs
its own quiet allocation. Combined full/hosted qualification, creative/product
acceptance, whole-suite speed and the original 85-percent target remain open.

Frozen executable after is `201adc21dc6ff4bd1f9c413d377f6056dac48bd6`;
before remains `2f57f598f9bdac67f6bce10012b351344b4bf7a3`. Later docs-only
HEADs do not retarget this ten-case comparison or any earlier accepted pair.

## Art/Script operation-local upstream resolution — selected implementation

The manager requested prioritizing the largest remaining source-backed costs.
Current native collection of image safety, complete images and creator
confirmation contains 11/10/16 cases (37 total). Their historical phase totals
(about 101.6/99.9/71.2 seconds) guide this investigation only; the old image-safety
count does not describe the current source.

Image-flow cases create real controller steps/native admission, pending fake
host work, selection, stop/resume and unknown-attempt recovery; gallery and
ceiling cases change inputs/policy. Existing closed seeds cannot replace these
boundaries without reconstructing native ownership. Only two creator-confirmation
corruption cases directly match the existing six-frame completed seed; retain
the positive/recovery controls fresh. That small reuse is deferred in favor of
the larger repeated read path below. Independent Sol/Medium source triage agrees;
it ran no checks or profiling.

Art `_context` calls Cast `_context`, then Cast `_stale` resolves it again.
Script `_context` resolves Art through `_stale`, then calls Art `_context`
again. One normal Script context therefore reaches Cast four times, propagating
through Storyboard/Bridge into image inventory. Inventory's separate
Cast/Art/Bridge reads can reach Cast approximately seven times on the ordinary
accepted-only path. These are static call-path counts, not timings. Existing
Bridge-local reuse does not remove the upstream duplication.

The selected fix resolves once inside each existing Art/Script `_context`, with
private Cast/Art comparison helpers that do not resolve/cache upstream state.
It preserves diagnostic/style/section order, Art's source-before-Cast readiness,
Script's accepted-Art readiness/binding-validation before resolution, expected
resolution-error mapping before target validation, unexpected failures and the
accepted receipt's frozen render ownership. ADR 0167 records the exact extension;
independent Sol/High design review found it safe within existing authority.
Effective delegated settings remain unverified. No production edit preceded
that design review. Separate reads/transactions/write/admission/currentness/open
validation, native execution/recovery, material hashes and default workers stay
unchanged. Inventory/review-bundle cross-owner reuse requires new authority and
is excluded.

Frozen before is `598c21f063ac4a820dae6b8e3b10f8c395c48fe4`. The prospective
quiet measurement union is all three unchanged files above, 37 native IDs at
`.local/remaining-cost/art-script-context-before-{cases,native-cases}.txt`;
sorted fingerprint `f89dadafd5d4bf75e3657968b92f6c700a84f7f2b57662678c18065ee8ea678f`.
No benchmark is allocated. New guards plus the reviewed exact existing
Art/Cast/Script/Storyboard/Bridge/lifecycle/style selectors establish focused
correctness before stable independent review. Full/hosted qualification remains
a later combined-candidate gate; do not infer whole-suite speed or 85 percent.

The reviewed implementation adds private comparison boundaries to Cast and Art,
passing the already resolved Cast base inside Art and resolving Art once inside
Script. Cast and Art's post-resolution comparison bodies and `get_state`
methods are AST-identical to baseline. Script validates the accepted ArtBinding
before resolution, catches only the expected resolution error, compares outside
that catch and keeps target/route work and `ScriptBinding(**accepted.binding)`
unchanged. Its generic error has no chained resolution exception. The source
remains cohesive (Cast 485 lines, Art 343, Script 364); no framework, public
already-validated flag or cache was added.

**32 new focused guards passed**, covering exact ordered diagnostics and text,
style evaluation despite field changes, expected/unexpected failures, source/
head/binding/target precedence, empty-state zero reads, one upstream resolution
per owner call, repeated fresh calls within a session, frozen accepted output,
two distinct accepted/candidate Art comparisons and normal Art-reopen refusal.
The real accepted-project guard proves one Cast resolution for each Art or
Script context call; this is structural call-count evidence, not measured speed.

**67 existing focused cases passed** with these explicit selections:

- whole files `test_storyboard_operation_context.py`,
  `test_bridge_operation_context.py`, `test_accepted_review_lifecycle.py`,
  `test_project_storage_script.py`, `test_script_storyboard_diagnostics.py`
  and `test_verification_module_ownership.py` under `tests/`;
- `test_project_storage_art.py::test_art_accept_reopen_cancel_and_currentness`;
- `test_project_storage_cast.py::test_cast_acceptance_preserves_authored_edit_and_rejects_stale_context`;
- `test_cast_style.py::test_persisted_cast_style_change_revokes_art_consumption_without_mutation`;
- `test_art_style.py::test_stale_prepared_task_cannot_send_or_admit_and_retains_evidence`;
- `test_art_style.py::test_live_action_api_delivery_accept_save_and_staleness`.

**Four fresh downstream cases passed**: complete 27-frame/29-image pack with
zero human facts; native unknown-image restart without resend; takeover after
delivered Art reference; and creator handoff/recovery with comment `None`.
Their full native selectors and commands are retained in the downstream log.
Total is **103 distinct focused passes**. The first 27-case smoke and expanded
32-case guard runs both passed; duplicate smoke cases are not added to this
total. No original assertion or test was weakened. Exact 37 native IDs remain
unchanged in `.local/remaining-cost/art-script-context-after-native-cases.txt`.

Retained logs under `.local/remaining-cost/`, SHA-256:

- `art-script-context-guards.log` (32):
  `faba02c145c597e8f25a871939c7a935d0ae1286247f7db9e6f616f1677de0f3`;
- `art-script-context-regressions.log` (67):
  `8126e0a32363feb31dc1d8e710166cebe2d63537bc4c19841c29e4d0f7f5c49f`;
- `art-script-context-downstream.log` (4):
  `69175dc45766e1a354b11e0c4639729cc8874c7eb7f7633327e73917e8688d29`.

Scoped Ruff F401 and diff checks passed. The existing Starlette/httpx warning
appeared in route-consuming unions. Independent Sol/High design and Sol/Medium
stable code reviews found no actionable finding and ran no checks; effective
settings are unverified. Concurrent test times are correctness evidence only.
No benchmark, broad/module/full/profile run, real provider, frontend/dependency/
timing-manifest change, resumed native seed, moving CLI merge, push, live write
or cleanup occurred. Combined full qualification must be refreshed for the
stable integrated production candidate; earlier release evidence does not
qualify these changes. Whole-suite speed and 85 percent remain open.

Frozen executable after is `5516f5a09808968fb535e54e818ef057608074dd`;
before remains `598c21f063ac4a820dae6b8e3b10f8c395c48fe4`. Any future
37-case quiet comparison must use those exact refs and the frozen inventory;
later documentation commits do not silently retarget it.

### Art/Script quiet pair — no observed speed gain

After explicit CLI quiet release and manager START, the inspected observer ran
exactly one complete-command pair: before
`598c21f063ac4a820dae6b8e3b10f8c395c48fe4` versus executable after
`5516f5a09808968fb535e54e818ef057608074dd`. Both passed all 37 unchanged
native cases. External focused-verify wall time was
**245.64915658300743 → 246.6204901250021 seconds**, a recorded reduction of
**-0.3954149712972699 percent**. Pytest reported 236.71 → 237.71 seconds.
This one pair establishes **no observed speed gain**; it does not establish a
statistical regression, whole-suite timing or achievement of the 85-percent
target. The separate 103-case correctness readiness remains as recorded above.

The external timer included native-selector preflight, collection, fresh setup,
execution, reporting and cleanup. Each leg used its own fresh temporary root.
Native case files were byte-identical with sorted fingerprint
`f89dadafd5d4bf75e3657968b92f6c700a84f7f2b57662678c18065ee8ea678f`.
Input probes stayed stable within each pin; host/interpreter/dependency and
manifest records matched across the pair. No manifest was rewritten. Native
session 78826 completed once, and the observer's `finally` restored exact clean
starting `main` `7a2d677b2590d8440fb1c18ac39c436b02c1e5a8`.

Evidence `.local/remaining-cost/art-script-context-quiet-qoax2cd5/` retains
per-leg collection logs, native IDs, focused logs and metadata plus `result.json`.
SHA-256:

- before `focused.log`:
  `6af106b328024a80167e442680cd9b801e804ecfa0e2b99da696e58600b2e984`;
- after `focused.log`:
  `b55ec0fb8d9261986f3519babf602a7ab1f2582df2109793436ef6874de8a4f1`;
- `result.json`:
  `c74464853c1e588f953a7e221730e2d86b2368d0a66939b1979446fcf5b56e43`;
- observer `.local/remaining-cost/art_script_context_quiet_pair.py`:
  `3f2125ad69ab17815733df7be61298e0ef1c3d02730ad482819e02776c70dc7e`.

The manager independently verified logs/hashes, all 37 passes, matched IDs,
source/host/dependency probes, arithmetic and clean restoration, accepting the
measurement as scoped evidence. CLI's quiet interval was then explicitly
released. No retry, profiling, full gate, provider work or source edit ran in
the allocation. Do not tune tests, infer speed from fewer resolutions, revert
structural correctness work from this one small timing difference, or introduce
speculative caching. The inspected one-case current-source attribution proposal
is the next evidence need; it remains unexecuted pending a separate START.
All earlier pair pins remain unchanged; combined full qualification stays open.

### Current complete-pack attribution — one instrumentation-only observation

After a separate manager START and CLI source-only quiet allocation, one
prepared observer ran at exact clean `47921934650398fc6db2278f361702bf917c9ba8`
(executable inputs unchanged from `5516f5a0`). Native session 22518 completed
once, exit zero. Exact one-case collection and the existing completion marker
proved execution of
`tests/test_autopilot_images.py::test_complete_pack_selects_all_subjects_and_unique_route_frames_without_human_facts`,
fingerprint `4a5688a8f77a9eefd4132e4753046ad0532ff693c4c84d60c8905ead6e1d6e55`.
The case passed. Instrumented process plus immediate owned-group cleanup wall
time was 68.57601454098767 seconds; pytest reported 66.76 seconds and cProfile
recorded 67.189792731 total own seconds. These are instrumentation diagnostics,
not a verify tier, benchmark, full gate, old/current timing comparison or CPU
accounting. The profile includes imports/collection/setup/reporting, unlike the
historical call-body profile; child-process CPU is not attributed internally.

Fresh absolute evidence/tmp/pytest roots were used. Input fingerprint
`8d4e31819de9b4ea9b6473ff0691a43e0afa741148c3596d3c9e011af58b056f`
and host fingerprint
`e157fcd2c8db7127845d443a20785aff48490f424fcbfe1eb56ec31bb040db92`
stayed equal through preflight, collection, profiling and extraction, alongside
interpreter/dependency/environment records. Ambient selectors/plugin overrides
were refused. Owned groups 95995 and 96013 were settled at their subprocess
boundaries and independently confirmed absent by the manager. Final branch/HEAD
and clean status remained unchanged. The completed 37-case observer remained
byte-identical; no other pair pin was changed.

Current instrumented costs (nested and **nonadditive**):

| Source owner | Calls | Cumulative seconds |
| --- | ---: | ---: |
| `material_closure` | 1,893 | 23.771952773 |
| ordinary-open `assert_autopilot_contracts` | 499 | 22.257937291 |
| `view_in_session` | 580 | 10.598581195 |
| global `stable_hash` | 937,669 | 8.376394673 |
| `initial_inventory` | 119 | 5.555415830 |
| Bridge `get_state` | 131 | 2.800959918 |
| Cast / Art / Script `_context` | 799 / 308 / 165 | 1.394033082 / 0.857814955 / 0.694213782 |

Direct `material_closure` caller edges were view construction (580 calls /
9.043170293 seconds), `autopilot_command` (650 / 6.366121430),
`production_closure` (470 / 6.086276384), command validation (192 /
2.268556541) and start (1 / 0.007828125). Direct callee edges include row
iteration (942,031 / 6.105906277), Session execute (43,999 / 4.702106737),
sorting (46,313 / 4.590567458), final closure hash (1,893 / 2.681738006),
row-mapping items (899,189 / 1.321742894) and select construction (47,470 /
0.104851798). Iterator/mapping counts are work-call counts, not per-table
cumulative SQL row counts. This still does not support speculative plan caching.

Within ordinary-open validation, the direct checkpoint-binding edge was
26,115 calls / 13.523123488 seconds, and Bridge-adoption validation 499 /
5.524274377. Checkpoint binding globally occurred 27,558 times / 15.904585684
seconds, including those nested callers; it must not be added to their costs.
Its direct execution-attempt helper edge was 19,643 / 6.238519702, and trusted
text-plan construction 8,272 / 3.405148526. These identify possible future
validation-layer investigations without authorizing skipped fresh-open checks.

Post-profile read-only endpoint extraction found one awaiting-review/material-
review run, 41 checkpoints, 37 attempts (8 text completed with no image budget;
29 image completed/consumed), 27 frames/image jobs, 29 assets and 571 gate-result
rows. The existing case asserts zero human facts/video jobs. Endpoint counts do
not establish cumulative rows or growth causes. `gates.py` already reuses an
exact immutable revision/gate-set evaluation and stores one row per gate; the
571 rows are not evidence of repeated append-on-read behavior.

The smallest evidence-backed next **investigation**, not an implemented or
approved optimization, is receipt-command closure construction in
`command_transactions.py:78`. Its pre-yield segment reads protected and full
projections over overlapping rows; the separate post-yield segment checks the
protected projection before constructing the full closure. A design review may
examine one row construction per individual contiguous segment while preserving
the exact full/protected hashes, protected-change refusal precedence, cancellation
and geometry inputs, and backend/error behavior. No row/proof may survive a
yield, mutation, commit, rollback, admission or fresh open. Preserve every
existing validation call and its freshness; a Session is not a snapshot guarantee.
ADR 0170 authorizes no broad material bypass. If these guarantees require a new
contract, obtain the owner's decision before implementation. No gate pruning,
cross-owner snapshot sharing, global/result cache or source change is selected.

Evidence root `.local/remaining-cost/complete-pack-current-930944ps/`, SHA-256:

- `main.prof`: `7ffca76f0b6c9cf024c5aa0ed2b552d98726eaa6fc37ce1071acc62062de411d`;
- `attribution.json`: `eb1b33754e6085e5899863ffcbe59b1fc9b10dd2762b3d1a30c02762458fc58f`;
- `cardinalities.json`: `60547e4b485ec4c2fd7b454b793c470ba732d6f2808d76e464eee5ba58d93ffc`;
- `profile.log`: `7007093a85bf95704c99f8f038241f26a0cea82e0dc8a8b887db4e53f24bc845`;
- `result.json`: `811c1eb116ad688f6ced30cd28bc2dd45200b62a740ca507edeabd3aeae3a9f7`;
- observer `.local/remaining-cost/complete_pack_current_profile.py`:
  `7b636035859c72e185c5cd700752589b6fcc4b7efddedc76f481cfdfd405f251`.

The manager independently accepted result/hash/probe/native-case/cleanup facts
and explicitly released the quiet allocation. All cost synthesis above was
read-only on retained files. No retry/new measurement/full/provider work or
production edit occurred. The existing warning remains. Whole-suite speed,
85-percent achievement and combined full/hosted qualification remain open.

### Receipt-command material projections — bounded implementation

After accepting the diagnostic receipt above, the owner authorized a bounded
design review and conditional implementation of receipt-command construction
reuse, with no further timing/profile/full allocation. The retained checkout
remains the sole source writer; the manager remains read-only, and CLI normal
work has priority. [ADR 0176](../adr/0176-receipt-command-local-material-projections.md)
records the separate decision; CLI reserved ADRs 0174/0175 are not used here.

Root cause: each receipt-command pre-yield and post-yield segment independently
selected, projected and sorted protected material twice to build protected and
full hashes. The command owner needs both identities in that segment. It does
not need another resolution of unchanged inputs inside that same uninterrupted
segment. This does not authorize sharing fresh admission, read or open results.

An independent read-only design review (existing GPT-6.1 Sol / High reviewer,
effective settings unverified) found no wider-authority blocker. The private
paired helper explicitly flushes, constructs/hashes protected rows, and checks
the post-command protected value **before** any managed-asset, geometry or
cancellation read/full hash. It then extends its local payload with the exact
existing extras and returns only two hash strings. Separate calls straddle the
yield; no row payload survives it. Public `material_closure` keeps its signature,
custom projection options, full columns, per-row datetime conversion/sorting,
original query order and hash keys through extracted unchanged helper bodies.
The paired receipt projection adds assets after protection; canonical JSON
already sorts keys, preserving the same full hash.

Unchanged boundaries: lifecycle lease/driver semantics, validation/admission,
controller claims, CAS, write/commit/rollback, other lifecycle owners,
ordinary-open corruption checks, inventory, current-versus-stale expected-
closure rebasing and run revision/time. This grants no new non-SQLite command
support; the existing driver `total_changes` assumption is untouched. No cache,
global/session/result state, row reduction or bypass was added.

New focused guards cover independent canonical payload expectations for empty
and populated projections, Unicode/nested JSON/null/datetime values, geometry
and all three cancellation lists, exact public custom projections, one table
projection per segment, pending-write flush even without autoflush, successive
call/rollback freshness, independent pre/post/subsequent command reads,
protected-refusal priority over extras/full hashing, ordinary-command exclusion,
receipt no-op revision behavior and flush/projection/hash-failure rollback with
context cleanup. Current/stale allowed-asset rebasing remains covered by the
existing authority tests. Stable-candidate independent review and focused
downstream results are recorded in the completion receipt for this slice.

Stopping condition: deliver this bounded source change with focused correctness
evidence and independent review. No benchmark/profile/full/provider work,
publication, moving CLI merge, default-worker change, creative acceptance or
speed claim is included. Combined full/hosted qualification and the original
85-percent target remain open.

Executable checkpoint: `a2436d78b18f3e6e05a380c85181208c920275aa`, based on
`04f6002a01d42660af5f7b174c0ef144bc9b90f0`. Independent stable code review by the
existing GPT-6.1 Sol / Medium reviewer (effective settings unverified) found no
actionable findings; the manager independently read the ADR, production diff,
all new guards, module-owner addition and actual 62-case exit-zero log without
an additional finding. Reviewers did not rerun tests or measure performance.

Executed tier: **focused**, 84 distinct cases passed:

- 62 passed: complete `tests/test_receipt_material_projections.py` (16),
  `tests/test_autopilot_authority.py` (20) and
  `tests/test_autopilot_claim_transactions.py` (26).
- 38 passed, including the same 16 guards: complete
  `tests/test_verification_module_ownership.py` (7),
  `tests/test_autopilot_late_receipts.py` (5), and explicit existing selectors
  `test_autopilot_images.py::test_complete_pack_selects_all_subjects_and_unique_route_frames_without_human_facts`
  (1), `test_autopilot_images.py::test_late_reference_retains_original_receipt_without_selection`
  (3), `test_autopilot_image_safety.py::test_direct_shot_cancellation_withdraws_automatic_authority_before_bundle`
  (2), and `test_autopilot_image_safety.py::test_stop_after_reference_ingestion_preserves_terminal_owner_and_prevents_selection`
  (4), all under `tests/`. These retain real stage/receipt/open/claim boundaries
  and fresh fake-host transport. The existing Starlette warning remains.
- `git diff --check` and F401 checks on both changed production modules and the
  new guard file passed. No full/module/hosted/provider run occurred.

Logs under `.local/remaining-cost/`, SHA-256:

- `receipt-projection-contracts.log`:
  `e79a3f1a662c438a866abb79fa71532cff87f5dd7c3692213887183e0d22f160`;
- `receipt-projection-downstream.log`:
  `d577b25bcfeef4accb9b7d4e2fa6db74b4132fb51ff210131ea8a739425dbcae`.

After correctness review, the manager requested preparation only of one
unprofiled pair for the unchanged complete-pack selector above: before
`04f6002a` versus executable `a2436d78`. The observer is the existing one-case
diagnostic/quiet-pair discipline adapted in ignored
`.local/remaining-cost/receipt_material_quiet_pair.py`; finished observers and
their pins stay immutable. It must start only after a separate quiet allocation,
use fresh native collection and completion-marker verification for exact case
fingerprint `4a5688a8f77a9eefd4132e4753046ad0532ff693c4c84d60c8905ead6e1d6e55`,
fresh absolute per-side roots, fixed dependency/interpreter/host probes, owned
process-group cleanup and finally restoration of its pinned clean main HEAD.
It times the established complete unprofiled command
`uv run --locked --no-sync python scripts/verify.py focused --pytest <CASE>`
plus immediate owned-group cleanup, including uv/wrapper startup, the wrapper's
selector collection and pytest import/collection/setup/call/teardown/reporting.
The separate native collection proof and probes are excluded. Ambient selectors,
plugin configuration, `PYTHONPATH` and pytest temporary-root overrides are
refused before the observer installs the existing timing plugin through its
child-owned `PYTEST_PLUGINS` and repository-root-only `PYTHONPATH`. The pytest
console entrypoint otherwise cannot import the repository's `scripts` package;
the direct `python -m pytest` diagnostic had included the working directory.
Both owned values are recorded and required equal across the pair; no ambient
or production configuration is changed. The wrapper's
collection-only marker (`complete=false`, no executed files) is checked
separately; only the execution block's successful exact-ID marker establishes
completion. Both wrapper steps and its final summary must succeed. The manager
caught and corrected the initially prepared direct-pytest timer path before any
launch; the production runner was not changed. No cProfile instrumentation or
alternative test path. At this preparation checkpoint no pair had run or
performance result was available; the separately allocated result follows.

### Receipt-command one-case matched measurement — completed

The manager explicitly allocated one quiet source-only pair after CLI ACK,
independently checking the observer and exact clean restore pin. Native session
15336 executed it once and exited zero. Both sides used the established focused
complete-command path above, unchanged exact fresh complete-pack case, existing
completion plugin and fresh per-side temporary roots. No profile, extra test,
full gate, provider work or retry ran in this allocation.

| Side | Exact revision | External complete-command seconds | Pytest seconds | Result |
| --- | --- | ---: | ---: | --- |
| before | `04f6002a01d42660af5f7b174c0ef144bc9b90f0` | 46.383018082997296 | 44.22 | 1 passed |
| after | `a2436d78b18f3e6e05a380c85181208c920275aa` | 46.415397459000815 | 44.25 | 1 passed |

Wall-time reduction was **-0.06980868719146383%**: this pair observed no speed
gain. Its approximately 0.032-second difference does not establish a statistical
regression. It does not establish whole-suite speed or the original 85-percent
target. The 84 distinct focused correctness checks and independent source review
remain separate evidence; combined full/hosted qualification is still pending.

Both actual execution markers proved native fingerprint
`4a5688a8f77a9eefd4132e4753046ad0532ff693c4c84d60c8905ead6e1d6e55`;
wrapper collection-only markers were checked separately. Source-input probes
remained fixed at `8d4e31819de9b4ea9b6473ff0691a43e0afa741148c3596d3c9e011af58b056f`
before and `042db77ea0d1c709cab7d75e7c64e7e4b5eb7b69a1b22655c6715e0c8b9b226d`
after; host `e157fcd2c8db7127845d443a20785aff48490f424fcbfe1eb56ec31bb040db92`,
interpreter/dependency identities and both observer-owned execution environment
values matched across sides. Ambient overrides were refused. The existing
Starlette warning appeared on both sides.

The observer restored exact clean `main` at
`463697dc37a515f4ccf0d4b0b8f4a12170fe0126`. Owned groups 9998, 10006, 10337 and
10360 were immediately settled absent; a post-terminal process-group inventory
also found none. `result.json` records `complete=true`. The terminal receipt was
sent promptly to the manager for CLI-window release. This subsequent docs-only
receipt does not retarget the now-completed observer or invalidate its runtime
inputs. All three completed observers retain their original bytes and pins.

Evidence root `.local/remaining-cost/receipt-material-quiet-0jasxfgm/`, SHA-256:

- `before/focused.log`:
  `92f46742f24be3cdb52b5292ba8092004f1314fce53ac9ee9e6d999b983a75ef`;
- `after/focused.log`:
  `204fcb62a7f58e540d2b5eefcfc56a2acd38732aedddff7af26a6722d63914a8`;
- `result.json`:
  `9144012689ee4dc3f6243c7abcebbb73b9c67f095564d9401ae0050b21866dea`;
- observer `.local/remaining-cost/receipt_material_quiet_pair.py`:
  `a1becc448d09ca4c7b00b9ad6bd5a2cf81ea1f70fd9fc4f5ddb8b5bfdd5ff878`.

### Current complete-Python capture failure and bounded repair

The manager allocated one current Python-only observation at clean
`bddb7cdf2d18ff924521dc6a3a14b4908e5ed83d` after CLI quiet ACK, using exactly
`uv run --locked --no-sync python scripts/testing/run_python_suite.py` with the
released default two workers. Native session 3882 ran once and exited one.
Current collection retained **2,239 cases / 211 files**, fingerprint
`cf44ff431a57ac8ab848124965921f73056fb33f7a1efe25d7dc0a9bf7340242`.
The workers reported 1 failed / 1,140 passed and 8 failed / 1,090 passed; both
completion markers correctly said `complete=false` and emitted no successful
phase-row inventory. External command time **524.1386793749989s** and runner
summary 518.081s are failed-run diagnostics, not qualified timing/coverage,
before/after savings or the original target's achievement.

The original manifest stayed byte-identical. Source/host probes stayed fixed,
exact clean main was preserved, all observed owned groups were confirmed absent
and the runner's temporary root was removed. The manager independently audited
terminal evidence and released CLI. No automatic retry occurred.

Read-only diagnosis identified two causes, then the owner approved only their
bounded test/observer repair:

- **Four observer-induced failures.** The failed observer placed child `TMPDIR`
  beneath repository `.local`. The Codex runtime fixture cloned complete source
  there; the extraction guard's repository filesystem scan found those copied
  prompt templates. Synthetic nested runner projects also inherited the ancestor
  repository `pyproject.toml`; installed pytest makes node IDs relative to that
  root, whereas the native runner accepts only `tests/...` IDs. All three nested
  failures reported no native case IDs. Their raw collector stdout was not
  retained, so the exact failed IDs remain unobserved. The unchanged extraction,
  four-worker isolation, fresh-ID success and old-ID refusal cases subsequently
  passed together under an external system temporary root. No extraction,
  native-ID, runner or fixture assertion was weakened.
- **Five stale routing assertions.** The stage-routing test still parsed a
  model-run shell block or expected adapter commands in model instructions.
  ADR 0165's current package-v4 contract makes trusted code own validation and
  report bytes. The repaired tests verify packages with
  `validation_plan_from_package`, expand fixed argv with
  `expand_validation_argv`, and execute real saved-Brief Cast/Art/Storyboard
  examples without parsing model shell. They assert candidate-only instructions,
  unchanged candidate bytes, exact host-captured report bytes and exact
  preset/neutral source resources. All five native case IDs remain unchanged.
  No production contract/runtime code changed or model execution was restored.

Executed **focused** correctness: first the five repaired cases passed; then
**37 distinct cases passed** in one union containing those five, complete
`test_codex_exec_validation.py` and `test_codex_exec_prompts.py`, selected neutral,
preset and mutated-contract resource guards, three current saved-Brief package
guards, and the four unchanged failing consumers named above. The fresh-ID test
asserts two successful native worker proofs; the old-ID test asserts refusal of
the mismatched worker fingerprint. `TMPDIR` was a fresh absolute `/private/tmp/`
child, removed after the command; its path/removal are retained in the log.
The manager independently read the routing diff and actual exit-zero union log,
finding no additional issue. F401 and whitespace checks passed. The untouched
production tree and unchanged four-consumer/runner diff were verified.
The tested executable-input fingerprint is
`18155d64c943e12b03766f50cb9b80be7b3e4e25ab93200ff2c66d0dce7dc6f0`;
the changed routing test's SHA-256 is
`7af3d68c4b8bdd71eeff784ef37fb7c8f31031f97334cd2cf85694f3150fe0be`.

Failed evidence root `.local/remaining-cost/python-current-two-i1jkshzz/`:

- failed observer `.local/remaining-cost/current_python_capture.py` SHA-256:
  `dfaa0c9a5d26908feb81d1bd3f25fa036023bef1ef158b673a3dce626894eb41`;
- `result.json`: `e078579aba8ab876bdc3f9912fc43fa442ce796adbc3507fabfa712d70e6794a`;
- `python-suite.log`: `592ec120f881f2dea2789b3092ff091026577eee2fceddbdb215c015b651f2a3`.

Correctness logs under `.local/remaining-cost/`:

- `stage-routing-current-contract-first.log`:
  `3610631818929db4eb96c49bc286048acece0c8db14f65af982a5b3cdcf8b8c0`;
- `stage-routing-external-focused.log`:
  `42dc84f9639d9bbdd1dcbb82818d54466a7e17b6a8aa73381d1bebb09871b865`.

A **new, unstarted** ignored `current_python_external_capture.py` preserves the
failed observer/result/full-log hashes alongside all earlier completed observers.
Measurement evidence stays repository-local; test execution uses a fresh
absolute external system temporary parent, with canonical containment checks
rejecting checkout-contained paths before any dispatch. After owned process
cleanup, only that identified disposable external root is removed. The native
runner, manifest, default worker count, exact worker proofs and phase-row checks
stay unchanged. Independent stable read-only review (existing GPT-6.1 Sol /
Medium reviewer; effective settings unverified) found no actionable findings in
the tests, record or new observer, and ran no checks. The observer's placeholder
HEAD is pinned only after the stable commit; root readiness review and a separate
quiet allocation still precede any new complete capture. No broad run/profile/
full/benchmark is allocated by this repair. Combined CLI/Python full
qualification remains required after integration.

### Current complete-Python observation and remaining-cost analysis

After the bounded repair above, root approved the new observer's exact source
pin/hash and allocated one separate quiet capture after fresh CLI ACK. Native
session 31862 executed once at clean main
`76389646780e2aadf92f1b8956d40f34073173f2`, using exactly
`uv run --locked --no-sync python scripts/testing/run_python_suite.py` and the
unchanged default **two** workers. It exited zero: **2,239 cases / 211 files**,
native fingerprint
`cf44ff431a57ac8ab848124965921f73056fb33f7a1efe25d7dc0a9bf7340242`.
External whole-command time was **524.1615562500083s**; native runner time was
518.212s. The timer includes immediate owned-group cleanup, excludes separate
inventory collection/probes/extraction and final external-parent removal, and
includes the observer's one-second process-tree observations.

| Worker | Files / cases | Setup / call / teardown seconds | Phase sum | Native elapsed |
| --- | ---: | ---: | ---: | ---: |
| 1 | 105 / 1,141 | 66.011886 / 428.434773 / 0.282617 | 494.729276 | 506.370s |
| 2 | 106 / 1,098 | 42.810008 / 463.794677 / 0.300258 | 506.904943 | 518.210s |

Root independently verified fresh collection, disjoint exact worker case-ID
proofs, all 211 positive-valid file rows against logs/report JSON, evidence
hashes and protected earlier pins. Before/after-collection/after source/input/
host probes agree; source remains clean and the manifest unchanged. Both owned
process trees settled; an independent immediate process-group check found no
owned survivors. External `/private/tmp/plotloom-python-current-zd8vzzy4` and
its nested native runner root were absent. Terminal/cleanup evidence reached
root before this receipt; root released CLI promptly. No retry occurred.

Aggregate phase work is **1001.634219379s**: setup **108.821894499s (10.8644%)**,
call **892.229449410s (89.0774%)**, teardown **0.582875470s (0.0582%)**. The
worker phase imbalance is 12.175667s; perfect redistribution of these observed
costs would reduce the larger phase sum by only 6.087833s. The ideal two-worker
floor at **fixed observed costs** is **500.817109690s**. Even eliminating both
imbalance and every other measured wall/phase gap leaves only 23.344447s
(4.4537% of observed external wall) for scheduling/startup/cleanup improvement.
This is a conditional packing bound, not an irreducible CPU cost or an absolute
future bound: faster production or fixture construction can change the costs.
Eliminating all recorded setup alone still leaves a 446.406162440s phase floor.

The largest current files are below; times are mutually exclusive pytest
phases, unlike nested profiler cumulative timings. All paths are under `tests/`.

| File | Cases | Total seconds | Setup | Call | Teardown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `test_autopilot_geometry.py` | 27 | 117.372771 | 9.565585 | 107.804944 | 0.002242 |
| `test_autopilot_images.py` | 10 | 112.018829 | 0.006270 | 112.010933 | 0.001627 |
| `test_autopilot_handoff.py` | 12 | 100.580598 | 11.391086 | 89.188458 | 0.001055 |
| `test_autopilot_creator_confirmation.py` | 16 | 74.457998 | 0.002879 | 74.454212 | 0.000907 |
| `test_autopilot_image_safety.py` | 11 | 64.676411 | 0.005754 | 64.669077 | 0.001580 |
| `test_specialist_terminal_reconciliation.py` | 62 | 45.425618 | 18.487480 | 26.875625 | 0.062513 |
| `test_autopilot_geometry_publication.py` | 3 | 28.357038 | 0.001486 | 28.355179 | 0.000373 |
| `test_autopilot_image_phase.py` | 3 | 25.929671 | 0.001337 | 25.928049 | 0.000285 |
| `test_native_bridge_intent.py` | 22 | 19.112112 | 13.991624 | 5.117918 | 0.002570 |
| `test_image_terminal_settlement.py` | 33 | 18.346540 | 0.021715 | 18.318181 | 0.006643 |

The top five total 469.106608s (46.8341%); the top ten 606.277587s (60.5288%).
Even deleting the entire top fifteen costs would leave a 157.314865s ideal
two-worker phase floor, above the original **151.73295s** reference
(151.733s rounded). This counterfactual is a scale check, never a proposal to
remove coverage. At perfect allocation, that target requires reducing current
phase work by at least **698.168s / 69.70%**, before accounting for remaining
wall overhead; the current external wall needs **71.05%** further reduction.

Inventory changed from the historical manifest's 1,911 cases / 185 files:
26 newly represented files contribute 333 current cases and 37.970836s of
current phase work; six retained files changed counts from 97 to 92 (net -5),
giving net +328 cases. No historical file disappeared. These are inventory
facts, not speed savings. In particular the eight retired schema2 receipt
variants and two replaced initial/final-admission variants retain the distinct
contract explanation in `inventory_distinctions`; file-level phase rows cannot
price removed individual cases. The manifest remains scheduling provenance
(`historical-duration`, retained 179 / scaled 6 / estimated 26), not a current
matched baseline. Neither the historical 578.639s / 1,911-case wall observation
nor its 1110.509s phase total establishes a matched gain against this capture.

**Next options, not implementation or measurement allocations:**

- First review four post-generation creator-confirmation cases for reuse of the
  existing closed six-frame `awaiting_handoff_seed`: the two variants of
  `test_exact_choices_succeed_without_a_name_and_store_no_invented_actor_or_comment`
  and the two of
  `test_ordinary_validation_refuses_unnamed_fact_without_its_receipt`. Their
  current bodies each call `handoff_image_environment(..., cuts_per_scene=2)`
  and `run_pack` before the behavior under test. That preparation is charged to
  **call**, not pytest setup. The seed already produces the same two-route /
  six-frame / two-reference state through eight fixture-backed text and eight
  fixture-backed image deliveries at real boundaries, then closes it. A bounded
  design must preserve isolated files/DB/assets, fresh ordinary-open checks, exact receipt and
  recovery assertions, native IDs and a fresh generation control. Do not resume
  a copied closed seed or replace dispatch/admission/lifecycle scenarios with
  snapshots. A seed is built per worker, so the net saving must include that
  cost; 74.457998s is the whole file, not an estimated recoverable amount. Leave
  the differently shaped retained-v1 control outside this first selection.
- For production attribution, the next causal question is duplicate immutable
  run/policy/attempt parsing and binding work **within one** ordinary-open
  validation. Source currently checks checkpoints, typed attempts, decisions and
  frames in separate passes, with checkpoint binding repeated for decisions.
  The earlier source-bound complete-pack profile supports investigating this
  path, but predates receipt projection and is not current attribution for
  these top files. Any new diagnostic needs an explicit allocation and exact
  integrated pin. Only a reviewed per-invocation construction context could fit
  the current operation-local authority; retain every check, diagnostic/error
  order, hash input, filesystem validation and direct standalone validator.
  Discard all facts at return; each new open/admission/write remains fresh.
  No cross-open cache, validation bypass or gate pruning is proposed.
- Scheduling weight refresh may improve packing but cannot close this gap at
  fixed observed costs. Further concurrency changes the resource comparison.
  Small remaining context projections have no evidence of the required scale;
  the last two scoped pairs observed no gain. Before another implementation,
  the owner must choose a bounded seed-extension/design or diagnostic brief,
  or explicitly fund a broader cost-reduction program / revise the target.
  Current evidence cannot promise that safe remaining gains approach 151.733s.

Evidence root `.local/remaining-cost/python-current-external-two-p3by4x5u/`:

- `result.json`: `9043dfaddf48023e207d6f0dde87714ff533aaad92a0e5fa43b7324b76ba2b5c`;
- `python-suite.log`: `bc7941773b2abb820d9050bc7848fbba41b13dac6be85909242917f4fb0c4369`;
- `native-reports-and-phase-rows.json`: `28f32e9c6791fd3082b85390289bff2d67f510068c1ee7f102a65a5b45af4933`;
- `native-cases.txt`: `e97b27cbf6417a7334ac6fa09cd1e732a229a001718ad3cf0bca33be96bbb003`;
- observer `.local/remaining-cost/current_python_external_capture.py`:
  `7ad3e54f17b18fb667db74c92a27e9a9202ee959bfa932be4eaaef54562e4658`.

Executable input is
`18155d64c943e12b03766f50cb9b80be7b3e4e25ab93200ff2c66d0dce7dc6f0`;
host is `e157fcd2c8db7127845d443a20785aff48490f424fcbfe1eb56ec31bb040db92`.
This single successful complete-Python observation is accepted scoped evidence,
not a matched speed gain, repeated result, final full gate, hosted CI or product
acceptance. Final combined CLI/Python full qualification remains required once
integrated inputs stabilize. This analysis used only retained rows and source
reads; no new test/profile/capture ran, no observer/result/log was edited, and
no runtime or workflow contract changed, so no new ADR is needed.

### Approved creator-confirmation seed extension — bounded implementation

Root authorized only the four post-generation cases proposed above, starting
from clean `245975b51840b388a3a08a59d6ff020de6a130e1`. The root cause is repeated
test arrangement: both exact-choice variants and both orphan-unnamed-fact
variants independently rebuild the same completed six-frame pack inside their
test bodies. Current file cost is 74.457998s, mostly call phase, but file rows
do not isolate the recoverable arrangement cost. The existing closed handoff
seed already builds that exact state through real boundaries with eight text /
eight image / sixteen successful typed terminal receipts and no human facts.
Reuse belongs in these test inputs, not production validation or dispatch.

Use a full isolated physical copy per case through `copy_awaiting_handoff_seed`;
retain fresh review/request construction and all handoff, CAS/hash, corruption,
transaction rollback, ordinary-open and snapshot/restore assertions. Retained
image job IDs describe the completed seed's evidence, never a new per-case
generation counter. No copied controller is constructed or resumed. Keep the
retained-v1 test and its fresh generation path unchanged. The existing seed
isolation/no-source-access guards and fresh handoff/recovery controls remain
in the focused selection. No helper or production contract changes are needed.

Before editing, native collection retained all **16** ordered case IDs in
`.local/remaining-cost/creator-confirmation-seed-before-native-cases.txt`, file
SHA-256 `e9d2689866e678ff3c4255264df633d25f807de1464e5478368ec399f85110cc`,
sorted native-ID SHA-256
`628c63d3757606ff9845972bc59cef9a5cdaa14c760a02fe1f1d6e31056e68c2`.
The proposed later measurement is exactly this whole file, including the real
session-seed construction and copies on the after side, unchanged retained-v1
fresh control, fresh external roots and full command wall time on both sides.
No benchmark/capture/profile/broad/full run or provider dispatch is allocated.
First complete focused correctness and existing independent stable review, then
return a pinned matched-pair proposal; no speed or 85-percent claim follows.

The bounded extension is implemented in
`tests/test_autopilot_creator_confirmation.py` only. The two selected functions
use existing closed-seed copies and label their evidence
`retained_image_job_ids`. Their handoff/recovery and corruption/rollback bodies
are AST-identical to baseline, as are every untouched function including the
retained-v1 fresh-generation control. No shared seed/helper, session-fixture,
production, CLI, dependency or timing-manifest code changed. After collection
retains the exact ordered 16 IDs in
`.local/remaining-cost/creator-confirmation-seed-after-native-cases.txt`, with
the same file and sorted-ID hashes above. The test file SHA-256 is
`3f1515dd74403967e5852032ce6f29746f2f0fa2427c57bf85454f945f6b5784`;
executable input is
`4109455dfab7da169c299c4e759d022c9f854d1ac42c80f922f02243106ea8f1`.

**38 distinct focused cases passed** in one native `verify.py focused` union:
the complete creator-confirmation file (16), handoff seed isolation/no-source-
access file (2), geometry seed safeguards (9), five invalid handoffs plus fresh
exact-handoff/withdrawal, mid-handoff rollback and takeover controls (8), and
three recovery cases: snapshot/closed-folder retained-file restore, portable
resume/claim/command refusal after acknowledgement, and active-autopilot snapshot
refusal until safe pause. The run used fresh absolute external
`/private/tmp/plotloom-creator-confirmation-focused-7qk8uryq`, removed after exit
zero. The existing Starlette/httpx warning remains. This concurrent correctness
run is not a performance comparison. Full selector argv and results are retained
in `.local/remaining-cost/creator-confirmation-seed-correctness.log`, SHA-256
`37b4b12c85e4367d492888fd8b6293860daaa7ba71d86e354f56fdb68fe6b419`.
Scoped Ruff F401 and whitespace checks passed.

The existing independent read-only reviewer (requested GPT-6.1 Sol / Medium;
effective settings unverified) found no actionable issue in the stable test /
plan diff and ran no checks. Root independently reviewed the complete test
diff and unchanged seed owner with no additional finding. The production
parsing-context hypothesis remains unallocated. No new fixture/runtime/workflow
contract was introduced; the existing closed-seed contract remains the owner.

Proposed observer for a separately approved **single matched whole-file pair**:
adapt the existing immutable receipt-pair method into a new ignored observer;
do not retarget any completed observer. Before is `245975b5` with input
`18155d64c943e12b03766f50cb9b80be7b3e4e25ab93200ff2c66d0dce7dc6f0`;
after is the scoped executable commit reported with this receipt and the input
above. On each exact clean pin, separately verify the same 16 ordered IDs and
native fingerprint, matching dependency/manifest/host identity, rejected ambient
filters/plugins and protected old evidence hashes. Then time the complete
`uv run --locked --no-sync python scripts/verify.py focused --pytest tests/test_autopilot_creator_confirmation.py`
command plus owned cleanup in a distinct fresh canonical external temporary
root, with no seed prewarming. The after-side session seed must be built inside
the timed command; both sides include the unchanged retained-v1 fresh control.
If using the existing observer-owned timing plugin, distinguish wrapper
collection from the actual 16-case execution and require exact successful
completion proof plus one valid 16-case file row. Preserve logs, source/host
probes, hashes and cleanup evidence; restore the original clean main pin and
report terminal/cleanup before docs. No retry on failure and no performance
dispatch until root reviews the concrete new observer and allocates CLI quiet.
No timing gain, final full qualification, hosted CI, push or product acceptance
is established by this implementation checkpoint.

### Creator-confirmation seed matched whole-file result

Root reviewed the concrete new 374-line observer, successful syntax/static/
canonical-path preflight and actual independent no-findings review, then gave
one START after fresh CLI quiet ACK. Native session 18844 ran once and exited
zero. Before was clean `245975b51840b388a3a08a59d6ff020de6a130e1`; after was
clean `8fef5a2f5db3ddf868025ce7e817f9a4754a9c96`. Each side ran the exact whole-
file focused command proposed above, with no seed prewarming. External complete
command time includes immediate owned cleanup, wrapper startup/selector
collection, imports, actual seed construction/copies, call/teardown/reporting
and the observer's one-second process observations. Separate native collection,
identity probes, extraction and final external-root removal are excluded.

| Side | External wall seconds | Setup | Call | Teardown | Phase sum |
| --- | ---: | ---: | ---: | ---: | ---: |
| before | 74.18319450000126 | 0.007142456 | 70.746272126 | 0.000872126 | 70.754286708 |
| after | 40.7252597080078 | 10.076479999 | 28.088784249 | 0.000685165 | 38.165949413 |

Phase seconds are rounded to nine decimal places here; full precision is in
`result.json`. Both actual executions passed **all 16 cases**. The after-side
10.076480s setup includes real session-seed construction, rather than removing
it from the comparison. Observed complete-command reduction is
**33.457934791993466s / 45.10177138838757%** in this single pair. This is scoped
file evidence, not a repeated/statistical result, whole-suite gain or an amount
to add to earlier pairs or subtract from the separate 524.161556s capture. The
unchanged fixed-resource **151.73295s** target and combined full qualification
remain open; no production parsing-context work is allocated by this result.

Both sides retained the same ordered 16 native IDs, file SHA-256
`e9d2689866e678ff3c4255264df633d25f807de1464e5478368ec399f85110cc` and
native fingerprint
`628c63d3757606ff9845972bc59cef9a5cdaa14c760a02fe1f1d6e31056e68c2`.
The wrapper's collection-only marker correctly reports `complete=false` /
zero files and is separated from the actual successful 16-case / one-file
completion proof. Each execution has exactly one valid 16-case phase row.
Before/after-collection/after probes agree within each pin, with the previously
recorded distinct executable inputs, matching dependency/manifest/host identity,
and unchanged protected completed observers/results/logs/phase/native-ID bytes.

Observed owned groups 64377, 64399, 65080 and 65102 settled; an immediate
independent process-group filter found no survivors. The fresh external roots
`/private/tmp/plotloom-creator-pair-before-652_ps3o` and
`/private/tmp/plotloom-creator-pair-after-38btfqu1` were removed after their
device/inode ownership checks. Exact clean main `8fef5a2f` was restored;
`result.json` records `complete=true`. Root independently confirmed terminal /
cleanup / restoration and released CLI before this documentation-only receipt.
No retry, extra pair, profile, broader/full capture, hosted CI or push occurred.

Evidence root `.local/remaining-cost/creator-confirmation-seed-quiet-0j8wvh0b/`:

- `result.json`: `21e50c843668203040fc345193e1dcf5119143dce584e74bfe1116c70ac88843`;
- `before/focused.log`: `efcf89a59b591ed7ebababecd1af5137b41c08fd6cb98c09fdf75a87bbfa3331`;
- `after/focused.log`: `49ed6f732cc60e6b185148653cab6bbcaa46d84f2563f20d60ea3168004f98d1`;
- observer `.local/remaining-cost/creator_confirmation_seed_quiet_pair.py`:
  `a5605b992d1e165868ffe76664aee3b572bb3107dbe35cd29ea1925ac17f7dc2`.

All retained pair artifact hashes still match. This receipt changes only the
plan, does not retarget the now-completed observer and establishes no new
runtime/workflow contract or product acceptance. No checks were rerun solely
for documentation; diff/command consistency and immutable hashes were reviewed.

### Historical material-closure attribution — read-only extraction

The manager extracted the existing main-thread complete-pack profile without
running new profiling or checks. Authoritative retained root:
`/Users/wjmao/projects/HU/plotloom-worktrees/python85-profiling/.local/remaining-cost/complete-pack-o_v35lkn/`.
The manager verified `call.prof` SHA-256
`0568761cd60476b78b42aa863676e969a53dc17ba9dd7a529a230df1e84fbee3`
and `attribution.json` SHA-256
`3be56242301e7077c8232ec8b513d8c08af300ac2a2765f9aa349f4bb511cb71`.
That profile binds source `3c3a025e` and a 55.536-second instrumented call.
This coordinator did not access the other checkout. At that attribution
checkpoint, local Git-object comparison independently confirmed then-current
`autopilot_closure.py` and `contract_hash.py` were byte-identical to that revision,
with SHA-256 respectively
`3345c6046c401af180f9c0ce362d733219216e255bc33a6b4bf3a30b7740fc4b`
and `2e779ab1b1f44bddf8ebebf975eb001f3bdf1f7bde8596075d5eb5305c773b77`.
Callers and counts changed afterward; attribution remains historical.

`material_closure`: 1,695 calls, 1.462100 seconds own / 20.708023 cumulative.
Its direct caller-to-callee edges were:

| Edge | Calls | Own seconds | Cumulative seconds |
| --- | ---: | ---: | ---: |
| result `iterrows` | 839,705 | 0.582317 | 5.275426 |
| `Session.execute` | 39,705 | 0.012568 | 4.115400 |
| `sorted` | 42,027 | 0.134032 | 4.032141 |
| final-closure `stable_hash` | 1,695 | 0.002136 | 2.302446 |
| `RowMapping.items` | 801,161 | 0.646190 | 1.171200 |
| operator equality | 46,671 | 0.022541 | 0.618996 |
| select construction | 43,188 | 0.012966 | 0.093166 |
| `Session.scalars` | 3,483 | — | 0.348339 |

Global profile edges, **not closure-exclusive**, included `Session._execute_internal`
(115,224 calls / 14.543607 cumulative seconds), engine execute (116,256 /
10.490219), `_compile_w_cache` (115,960 / 6.894215), `_compiler` (19,997 /
4.608755), select construction (115,224 / 0.424907), `_generative` (119,084 /
0.319015), `where` (79,314 / 0.148470), `Session._connection_for_bind`
(115,913 / 0.334061), SQLite cursor execute (118,915 / 1.005493 own/cumulative),
fetchone (978,278 / 1.171670 own/cumulative), and SQL type processing (1,988,466 /
5.032310 cumulative). These nested costs must not be summed or extrapolated
into current complete-suite savings.

This evidence does not identify query construction as the main remaining lever;
row processing, sorting/hashing and execution are larger historical edges. No
speculative plan cache or closure rewrite is selected. Keep exact hash inputs,
freshness and backend semantics. The next allocated observation remains the
prepared, unexecuted 37-case `598c21f0` → `5516f5a0` quiet pair. If its current
evidence leaves a material bottleneck uncertain, propose one source-bound
attribution run before choosing another change. No new product authority,
profiling/full/benchmark allocation or speed claim follows from this receipt.

## Residual-cost investigation — historical proposal, now separately scoped

One fresh main-thread profile ran the unchanged complete-pack control at clean
`3c3a025e` (the same executable inputs as the qualified/published candidate).
It passed with all eight text stages, 29 images and 27 unique route frames;
providers were fixture-backed. The profiled call took 55.536s, of which 54.982s
was process CPU. These instrumented costs are attribution, not a speed
benchmark or a comparison to the unprofiled full run.

The largest relevant cumulative costs were `material_closure` (1,695 calls,
20.708s), Bridge `get_state` (131 calls, 10.383s), and persisted-autopilot
validation on project open (499 calls, 9.235s). They overlap and must not be
added. Caller evidence assigns 308 closure calls / 4.396s to lifecycle
before/after checks; source shows `claim` uses that lease even when updating
only controller metadata. Other closure checks protect write admission,
receipt reconciliation, cancellation and current views. Bridge still repeats
upstream resolution inside its own read. These costs live in production
authority owners, not pytest scheduling.

Open questions for a separately scoped review are whether metadata-only claims
can preserve lifecycle/ownership guarantees without a full material comparison,
and which duplicate resolutions belong to one uninterrupted Bridge read.
Do not use a session/global closure cache, skip ordinary-open corruption
validation or reuse pre-write authority after mutation. Neither question is
implemented or promoted to an adopted contract, and neither is evidence that
85 percent is achievable. Broader production changes still need owner approval.

Evidence: `.local/remaining-cost/complete-pack-o_v35lkn/attribution.json` in
the profiling checkout, SHA-256
`3be56242301e7077c8232ec8b513d8c08af300ac2a2765f9aa349f4bb511cb71`;
`call.prof` SHA-256
`0568761cd60476b78b42aa863676e969a53dc17ba9dd7a529a230df1e84fbee3`.
Command: `uv run --locked --no-sync python .local/remaining-cost/profile_case.py complete-pack`;
observer SHA-256
`4fd3cb2fc79e81536e5746a68febc467de4a308e9984b6a782db6e7ef012885c`.
Source remained clean and input/host fingerprints matched after completion.

## Approved Bridge / controller-claim follow-up — October 14

The design review is collected and the CLI worker has explicitly released the
source/check window. The selected contract, exact measurement union and active
implementation status now live in the
[Bridge / claim plan](2026-10-14-bridge-claim-optimization.md).

The owner explicitly approved both pending follow-ups: the isolated CLI
runtime/import repair and a design-reviewed local production optimization of
Bridge reads and controller-claim transactions. This is not approval to remove
authority checks, change material hashes, reinterpret retained evidence or
increase default worker concurrency.

First obtain an independent read-only design review against main `b4f831da`
and the residual-cost evidence above. Requested model/effort: GPT-6.1 Sol /
High, effective settings unverified. Identify exact operation/transaction
boundaries, exception and return-value behavior, lifecycle/contention semantics,
stale/recovered/closed/handed-off cases and regression owners before editing.
Do not substitute the work-unit allocation lease simply because it also uses
`BEGIN IMMEDIATE`; its error contract and backend behavior differ.

The CLI worker holds the source/check window first. Python review may proceed
without writes, tests or profiling. After its findings are collected and the
CLI window is explicitly released, the manager records the selected design,
preselects matching timing and unaffected checks, and implements only the
reviewed local optimizations. Preserve fresh checks across separate operations,
writes, commits, rollback, cancellation, restoration and dispatch. No
session/global cache or ordinary-open corruption-validation bypass is allowed.

Use focused regressions and a stable independent code review before a final
full gate. Reconcile the exact integrated CLI/Python source before reusing
evidence or timing manifests. Actual whole-suite timing, publication and hosted
status remain separate; neither approval nor a local profile establishes 85
percent. Stop for a materially different authority or data-model change.

## Approved ordinary-open profile-construction candidate — October 14

After independently reviewing the accepted diagnostic and temporary design note,
the manager authorized precisely the lazy, private single-success slot described
in [ADR 0177](../adr/0177-invocation-local-autopilot-profile-construction.md).
The existing read-only architecture reader found no design blocker. The retained
checkout was clean main `b45f2a3f`; ancestry was verified and local main fast-
forwarded only to delivered CLI `8ab58839df652e21ec5eef51a63c925d33a1af58`.
This is development integration, not release/product acceptance. Preserve prior
evidence and its original revision claims; the CLI checkout remains untouched.

Deliverable: bounded source, ADR and focused regression candidate with explicit
module ownership, lightweight stdlib static inspection and the existing reader's
stable code review. Each profile site owns its fresh raw policy TEXT and decoded
extraction. Only direct ordinary checkpoint/decision passes share construction;
SQL, isolation, errors, receipts, hashes, files, public/nested and admission paths
retain their existing behavior. No plan reuse, generic memoizer or ambient cache.

Initial resource hold (historical design checkpoint): CLI's separate native
serial/parallel comparison had priority. Tests, collection, dependency tooling,
profiling, benchmarks, broad/full gates, provider calls, source commit, push and
activation were unallocated. The stopping condition was a stable reviewed diff
with selectors and proposed correctness/measurement commands. Those executions
needed separate scheduling; their later accepted results follow below. The
attribution remains diagnostic, not a timing baseline. The fixed-resource
151.73295-second / 85-percent target remains unmet.

The existing architecture reader's independent stable code review found no
actionable issue, including no fixture/API or predicted-count inconsistency.
Requested GPT-6.1 Sol / High; effective settings unverified. Review was source-
only: no imports, collection or execution. Stdlib AST parsing passed for all
eight changed/new Python files; the corrected one-off ownership JSON check and
`git diff --check` passed. Exact SQL-call ASTs and source-site order match the
integration base in both existing runtime files; the receipt contract file is
byte-identical. These static facts do not establish runtime correctness.

Initial focused command (unallocated at the design checkpoint; later executed):

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_autopilot_profile_construction.py \
  --pytest tests/test_autopilot_profile_bindings.py \
  --pytest tests/test_autopilot_profile_transactions.py \
  --pytest tests/test_autopilot_profile_receipts.py
```

Initially selected affected-consumer union, using one `--pytest` per selector:

- `tests/test_codex_exec_contracts.py`
- `tests/test_codex_exec_receipts.py`
- `tests/services/creator_workbench/test_codex_exec_pool_profile.py`
- `tests/test_autopilot_exec_pool.py`
- `tests/test_autopilot_early_references.py`
- `tests/test_autopilot_claim_transactions.py`
- `tests/test_autopilot_geometry.py::test_tampered_or_missing_lineage_refuses_ordinary_open`
- `tests/test_autopilot_creator_confirmation.py::test_ordinary_validation_refuses_unnamed_fact_without_its_receipt`
- `tests/test_autopilot_recovery.py::test_snapshot_and_closed_folder_restore_preserve_all_retained_creative_files`
- `tests/test_autopilot_recovery.py::test_portable_autopilot_cannot_resume_after_acknowledgement`
- `tests/test_autopilot_image_safety.py::test_retained_candidate_must_match_exact_manifest_output`

The last case exercises an existing direct public-binding caller affected by the
common-body extraction. This was a scoped correctness proposal, not full or
module qualification. No counts had been collected at that checkpoint; the
manager subsequently allocated external roots, execution and cleanup, with the
actual results below.

The initial proposal reserved a separately allocated matched observer for this
unchanged case, uninstrumented on both exact frozen inputs:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest 'tests/test_autopilot_early_references.py::test_complete_early_pack_reuses_original_jobs_and_budgets_once[mapped-consumer]'
```

At that proposal checkpoint, before was integrated `8ab58839` and the after
commit had not been created. Quiet matching resources, dependency/host and
native case proofs, fresh external roots, complete-command timing and owned
cleanup remained required. No old observer or diagnostic became the baseline.

### Ordinary-open profile correctness and matched result — October 15

Implementation was committed at `db0216999210616fa6020ef156b811abb735d55f`,
parent `8ab58839df652e21ec5eef51a63c925d33a1af58`. Its reviewed twelve-file
candidate digest was
`632b585b273ca193fb1db4eb3a0dcc9553d43fc891ce0bcd5038be6fe5e592b6`.
The exact candidate bytes passed **142 focused cases**: 51 in the four new
contract files above and 91 in the selected consumer union. This evidence was
captured before commit; committing changed no bytes. Independent stable code
review found no actionable issue. Correctness result
`.local/remaining-cost/profile-construction-correctness-htplzps2/result.json`
has SHA-256 `5ed960fef8a2d843ab0aa69c12692175d922e66d99a15d032ca3944c0bf589c4`.
The explicit eight-file Ruff F-family check passed; the earlier default Ruff
check remains failed with **ten non-F findings**. No quick/module/full success
or unfiltered hosted CI is implied by these focused/static records.

After attended independent observer reviews and root's separate setup/seal/
ONE START releases, the new quiet pair completed once. The requested reader
selection was GPT-6.1 Sol / High; host records confirmed that selection for the
later setup/observer review turns. Before was a separate clean detached control
at exact `8ab58839`; after was clean `db021699`. Frozen CLI `2a359171` remained
separate and untouched. Both arms used the same checked physical Python 3.12.13
and retained `.venv`, lock and case inputs. Root accepted setup-02's natural
nested runner/pytest/package/test/fixture/tool binding proof plus separate
per-arm import identities before measurement. The measured pair used only the
original timing plugin and arm `src:root` source paths, with fresh external
temporary/cache roots and unchanged fixture generation; no setup diagnostic,
collect-only override, prewarming or product instrumentation entered execution.

Both arms passed the exact mapped-consumer case in the command above, with
native fingerprint
`20a17f28cc1719827b02e22af90b923bbf436d1cf3d83d21a9b3e19f19c3bcd4`.
Each focused command's selector collection emitted `complete=false`; its
distinct actual execution emitted `complete=true`, one case/file and a valid
phase row. Both retained the same existing httpx deprecation warning.

| Side | Whole command | Setup | Call | Teardown | Case phase sum |
| --- | ---: | ---: | ---: | ---: | ---: |
| before | 50.113741375s | 0.000569792s | 47.094119167s | 0.000093583s | 47.094782542s |
| after | 45.048235292s | 0.000478542s | 42.661754000s | 0.000092750s | 42.662325292s |

Values here are rounded; full precision is in the result. Whole-command time
includes the focused runner's startup/selector collection, actual test phases,
reporting and immediate owned-group cleanup. Separate collection/import probes,
preservation checks and final external-root removal are excluded. This one pair
observed **5.065506083s / 10.108018%** less command time and
**4.432457250s / 9.411780%** less case phase time. It is not a repeated/statistical
result, a whole-suite saving or an amount to add to other scoped results or
subtract from the historical 524.161556s run. The **151.73295s / 85-percent**
target, current whole-Python measurement and combined full qualification remain
open. The human owner's CLI verification-authority choice is still pending;
provider, hosted CI, live
activation, publication and product acceptance remain held or unestablished.

Evidence root `.local/remaining-cost/ordinary-open-profile-isolated-jf3tfr7m/`:

- `result.json`: `7d20525429c5e829e52b04fc0bc1bebadecd624333d76f44b2adf7dcfda9b2fd`;
- `before/focused.log`: `aa55a4dd8c1fa4212347ce1c21be8c8b579096f53648c7494e109728a006d5b2`;
- `after/focused.log`: `2f1a4056e25483fcf0669a870400b3cfa83717b6953255e06785a1e7de5ce763`;
- observer `.local/remaining-cost/ordinary_open_profile_isolated_pair_20261015.py`:
  `8941b90e71be7e515890432b5460e0cd6a559e481991a475ab0806284257c9b4`;
- sealed plan: `9bf8ad66b531486cc3a9efce48681f9eaac7ce00f0701f0233de2dbd75753aca`.

Actual terminal, native proofs, source/environment/artifact preservation and
owned-group/exact-root cleanup passed root's independent audit. Setup-01 remains
a failed proof attempt; the older user-interrupted pair remains incomplete.
Neither supplied an arm or was relabeled as this successful pair. This receipt
changes only documentation after measurement: the measured source remains
`db021699` with the original digest above, not a later docs commit. No test was
rerun solely for these documentation edits. This receipt alone authorizes no
commit or push; publication still needs separate authorization/qualification.

### Proposed next checkpoint — one fresh current whole-Python observation

Prefer current whole-Python evidence before choosing another micro-optimization.
After review and a separately authorized local docs commit, pin that actual clean
HEAD (not yet known), executable inputs, environment/tool/host identity and the
unchanged timing manifest. Prepare a new ignored capture without retargeting
`.local/remaining-cost/current_python_external_capture.py` or any spent observer.
Reuse its inventory/scheduler/report extraction and native runner/completion
contracts; use the later reviewed latched stop, registration, early-cleaning and
reporting lifecycle, with exact owned groups and registered external-root inode/
device checks. Keep its whole-command timeout proposal at 3600 seconds, subject
to root review rather than inheriting the scoped pair's 900-second bound.

Proposed separate unfiltered native inventory command:

```sh
uv run --locked --no-sync python -m pytest --collect-only -q -p no:cacheprovider
```

Proposed timed command, retaining the released **default two workers**:

```sh
uv run --locked --no-sync python scripts/testing/run_python_suite.py
```

Use the existing checked environment and explicit retained source paths, offline/
no-sync children, fresh external temp/uv caches and the native runner's disabled
pytest cache. Refuse ambient filters/plugins/coverage startup; leave
`PYTEST_ADDOPTS` empty, as the runner requires. The runner itself selects the
timing plugin for workers. No setup diagnostic, fixture prewarming, manifest
rewrite, worker-count increase or new environment is proposed.

Deliver fresh native IDs/counts (currently uncollected, not predicted), scheduler
basis/history/fallback and exact whole-file assignments. Match the runner's own
fresh collector fingerprint to the separate inventory; require two disjoint
assigned native-ID fingerprints whose union is exact, both workers' true
completion markers and finite per-file phase rows. Preserve raw logs and report
hashes, whole-command wall including immediate owned cleanup, native worker/
parallel walls, per-file setup/call/teardown totals and pre/post source/env/
manifest/proof/cache identity. Phase sums are work totals, not parallel wall.
Retain all old evidence, including this pair, and verify terminal/group/root
cleanup before reporting. `verification-tooling` owns the native runner,
completion/scheduler/plugin and their existing regression selections; no tool or
test contract change is proposed.

Stopping condition: one current Python-only observation, then root review. This
proposal authorizes no capture authoring, collection or execution. The previous
524.1615562500083s at `7638964` / 2,239 cases / 211 files is different-input
history, not a matched baseline. A docs-only commit can retain executable
evidence while explicitly changing revision provenance; later CLI integration
that changes executable inputs/inventory invalidates current-source reuse and
needs fresh measurement/relevant qualification. Whole-Python success would
still leave combined full, hosted CI, CLI, publication and product acceptance
separate. No 85-percent promise follows from the scoped five-second observation.

### Current whole-Python observation failed — October 15

The separately allocated observation at clean
`bab6bc0809cc9b271e46a5a18e705340477b3fdd` genuinely terminated with exit 1.
Fresh native inventory contained **2,375 cases / 226 files**, fingerprint
`dca02467c486f4f961684426a3ed90c04ed7718d9d8c541adea8e8fa6716f713`.
Worker 1 reported 1,232 passed / 1 failed; worker 2 reported 1,141 passed /
1 failed: **2,373 passed / 2 failed** overall. Both actual timing markers were
incomplete, with zero per-file phase rows. External failed-command wall was
**701.227730750019s**; native coordinator wall was **694.223s**. This is failed
current-source evidence, not successful qualification, matched whole-suite gain,
or achievement of the 85-percent target. No phase bottleneck ranking is possible.

Evidence remains immutable under
`.local/remaining-cost/current-python-bab6bc08-ifyzlug_/`:

- Result: `f2513267cd33aa5cde0dfa800f5081cc484f044a33f82d11aeec74a845adb0e3`.
- Sealed plan: `fe170078f415fd08983ab6a851835914644778853c54af9a34ac3979869185c6`.
- Consumed START: `7099ca4ca997c5f8034d18043335f9deb5ac41a6ca6381b91fadfa50eb31bdd4`.

Initial/final source, environment and protected-artifact identities matched;
tracked source remained clean. All owned process groups and the exact external
parent/nested temporary roots were absent after cleanup. Root independently
accepted the failed-run closure and released its quiet window; that allocation
is spent and permits no retry.

Reviewed diagnosis traces both failures to the earlier `e71e537f` F5 timing
change, not the latest profile-construction optimization. The lifecycle test in
`test_project_storage_storyboard_review.py` retained an obsolete five-artifact
expectation. ADR 0173 requires the sixth timing artifact even for action-only
Script (`lines: []`), bound to accepted Script identity, saved language and the
canonical timing profile. The bounded repair updates that exact expectation and
checks the full timing payload/digest against its serialized candidate binding;
all lifecycle, cancellation, late-delivery and recovery assertions remain.

**Precision decision at failed-run closure — subsequently resolved below.** The other failure,
`test_raw_f5_accepts_submillisecond_time_but_production_conflicts_explicitly`,
exposes a contract conflict: ADR 0100 places exact integer-millisecond conversion
at Bridge/provenance and leaves raw F5 admission unchanged, whereas the new
receiving adapter rejects every fractional-millisecond cut before dialogue
assignment, including action-only Script. ADR 0173 authorizes canonical minima
and route checks without explicitly superseding that precision boundary.
Upstream-library versus receiving-adapter terminology does not resolve it.
The choices are to preserve raw precision with exact decimal comparisons against
minima/route ceilings while keeping Bridge conversion strict, or explicitly
authorize earlier precision rejection and reconcile the owning ADRs. Neither
rounding nor skipping empty-dialogue timing checks is an acceptable resolution.
No precision production code, owning ADR or second-test expectation is changed
by this first-failure repair. A precision repair, its affected qualification and
any fresh whole-Python run require the decision and a new allocation. The
separately authorized first-failure correctness window is recorded below;
combined full, hosted CI, CLI and product acceptance remain open.

The first-failure repair's separately allocated focused check executed once:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_project_storage_storyboard_review.py::test_f5a_freezes_current_f4_identity_blocks_lifecycle_and_refuses_late_delivery
```

Native session `76888` exited 0: **1 passed**, with the existing Starlette/httpx
deprecation warning. Native collection and true execution completion matched the
exact one-case fingerprint
`aa8cc6e7be4e089679beb7e123527baa0dc6cd57429223abe19e1c2b7e7e8382`.
The fixed existing environment ran offline/no-sync with cacheprovider disabled,
fresh external TMPDIR/uv cache and the established owned-group cleanup. Initial
and final candidate/environment/cache/protected-evidence probes matched; the
owned group and inode-bound temporary root were absent. Evidence is
`.local/remaining-cost/f5-artifact-lifecycle-correctness-li9lgi_j/`, result
`a76baeb96b57f973fdbc8bb5b065e1f76d7a6686bf50b2f5c62c8855e824d6f6`, log
`5a6b8c5a14b29a21ebe714a904dbb67ea6b1cdaa03bc3b5985de000ed97a0907`.
The measured whole-run revision remains `bab6bc08`; this later test-only repair
is not a relabelled whole-suite result. The subsequent receipt-only docs
update does not change the executed test bytes. No second precision case,
affected union, module, whole suite or full release check ran in this allocation.

### Approved raw F5 precision repair — October 15

The owner explicitly chose Option 1: preserve raw F5 decimal precision at review
admission, compare exactly against canonical minima and frozen timing ceilings,
and retain Bridge's strict integer-millisecond conversion. ADR 0173 now records
why integer-ms minima do not constrain cut precision and preserves ADR 0100's
boundary. The earlier failed whole-run receipt and its measured `bab6bc08`
revision remain unchanged evidence; the first artifact-expectation repair was
separately committed at `1b71883b`.

The shared receiving helper now uses decimal integer coefficients/scales for
comparisons and cut/segment/complete-route sums. Both receiving routes retain
their original upstream validators, complete frozen timing metadata and exact
dialogue ownership. The obsolete F5-only strict converter has no other callers
and is removed. Bridge/canonical conversion and the retained raw-F5-acceptance /
`cut_duration_invalid` integration expectation remain unchanged. There is no
new dependency or sandbox resource grant; the existing timing-helper identity
continues to be pinned by both routes and the Codex validation/resource owners.

The draft was preserved during the owner's CLI-priority checkpoint, with no
Python test live. Root subsequently released the bounded Python correctness
window after that CLI checkpoint finished. These are correctness checks, not
matched timing evidence. No new whole-Python, full release, sandbox handoff or
provider proof is authorized by this checkpoint.

Executed checks at retained HEAD `1b71883b` plus the uncommitted Option 1
candidate, with unchanged receiver SHA-256
`6b44c2c91a9339f5758cc44a536a6c69e737d5026086af0343480737a9357048`:

- Initial focused selection: the two previously failed node IDs and all six new
  exact-time test families, **56 passed / 4 failed** out of 60. Native session
  `35719` exited 1. The new cut-boundary fixture had 18-second episodes, violating
  the unchanged upstream 25-second target's ±15% gate before the precision check.
  The repair belongs to fixture construction: preserve the boundary segment but
  supply valid independent episode timing. No production gate or assertion was
  weakened. Evidence: `.local/remaining-cost/f5-option1-initial-640iu5x_/`, result
  `5fbe1871a0bd5848a18da23ccf876a71f7d6afad0618130b65318d7c3a4106f3`.
- Smallest affected family after that fixture correction: **14 passed**, session
  `73299` exited 0, native fingerprint
  `8f348b82c9de8a1a8ba37ca67a8ddca5cba8d745846663c3eab83a21be397b38`.
  Evidence: `.local/remaining-cost/f5-option1-boundary-1s4qspnk/`, result
  `96e802444198b49def122c273602e1c529818b216f16132629c351299c571cea`.
- Stable affected union below: **205 passed / 11 files**, session `64871` exited
  0, exact native fingerprint
  `1e43ce56a3de6555a77bc38ece2eae040c43c248b5f699fdd736f1350838509a`.
  Evidence: `.local/remaining-cost/f5-option1-affected-lpa1ekkd/`, result
  `4c097322b2e0f1fb4262e29a1b2975e57ec9f722d23c98bc55ed9390ea699568`, log
  `05fd88e7fff78b1a2ae256897b9fc86e1ec93e9ee55a7bc91c450fc2c8227350`.

The corrected test file at the successful checks was
`d6a7af8d4553a99f1178396229100cd6bfff896c68689252fa8b7dec07758de1`.
The successful native completion records match every collected ID with no
skips/xfails; the existing Starlette/httpx warning appeared in the affected
union. All three observations preserved their initial/final source, environment,
pytest-cache and protected-evidence identities. All owned groups and registered
inode-bound external roots were absent after cleanup. Source pytest caching was
disabled; children used the existing environment, offline/no-sync, explicit
retained src/root and fresh external TMPDIR/uv caches. The failed observation
remains failed and immutable. Later receipt-only documentation does not change
the tested executable inputs.

The affected union used exactly:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_f5_dialogue_timing.py \
  --pytest tests/test_project_storage_storyboard_review.py \
  --pytest tests/test_storyboard_review_timing.py \
  --pytest tests/test_storyboard_brief_style.py \
  --pytest tests/test_production_presentation.py \
  --pytest tests/test_production_presentation_integration.py \
  --pytest tests/test_production_bridge_voice_over.py \
  --pytest tests/test_codex_exec_validation.py \
  --pytest tests/test_codex_exec_resources.py \
  --pytest tests/test_codex_exec_stage_routing.py \
  --pytest tests/test_storyboard_operation_context.py
```

Both receiving routes have action-only submillisecond admission/render/acceptance
and unchanged Bridge refusal coverage, exact canonical-minimum and complete-route
comparisons, supported JSON exponent notation, frozen cut/segment boundaries,
missing timing metadata and malformed-number refusals. Existing source-binding,
ownership, multi-cue, install/reopen and currentness regressions remain in the
union. The existing `creative-production` owner already includes the changed
test file; there is no new file or allowlist expansion. Node syntax and scoped
Ruff F/I checks passed; AST/diff consistency was checked. These scoped results
leave a fresh whole-Python observation, combined full qualification, actual
changed-command sandbox qualification, hosted CI and product acceptance open.

### Successful current whole-Python observation — October 15

Measured clean revision **`b0ed49f3b81bd66fb090586e15f0530b217dd362`** passed
the unchanged default-two-worker native Python command: **2,433 cases / 226
files**, exact inventory fingerprint
`2c06e3d99bdb1d9433879631b9ef420d43518ebfb3a1123c1b91da92d5f44642`.
Both actual completion markers are true: worker 1 covers 1,286 cases / 112 files;
worker 2 covers 1,147 / 114, with disjoint exhaustive coverage and 226 finite
per-file phase rows. Native session `7173`, command execution
`exec-8208372a-3e53-4cef-b0aa-0b432f34b2e6`, genuinely terminated with exit 0.

External whole-command wall was **591.4420814999903s**, native coordinator wall
**584.771s**. Phase **work** totals were setup **174.38635409012204s**, call
**963.4108807064476s**, teardown **0.9395840348443016s**, aggregate
**1138.736818831414s**; these are not parallel wall or production-only time.
See the retained [result](../../.local/remaining-cost/current-python-b0ed49f3-tidx1h3k/result.json),
[raw log](../../.local/remaining-cost/current-python-b0ed49f3-tidx1h3k/python-suite.log)
and [phase ledger](../../.local/remaining-cost/current-python-b0ed49f3-tidx1h3k/native-reports-and-phase-rows.json).
Their SHA-256 pins are respectively
`90c1ea3823fe912613a82ea5c6cea494ba4da3644022c7ece2a224075e79908b`,
`93c946cfb40152f464232fadfa6e930cb4c1de0c6dfeb3f83419e370ca5395db`,
`dba4b90f9d17d2970273756c2f850cee36a0eab3db81bb15683e170cd3eef529`.

Source/environment/cache and all protected identities were preserved. All 14
owned groups, inode-bound parent root `151225105` and nested runner root were
absent; the quiet window was released and the allocation is spent. Root audit
`a51639` independently accepted raw coverage, exact canonical phase rows,
hashes and cleanup; `641b10` independently rechecked the fresh input/environment/
host/cache identity. Root's earlier extra auditor concatenated worker-grouped
rows against a path-sorted ledger; inspection `40047d` identified that ordering
assumption, and `a51639` verified exact canonical equality. No product failure,
weaker row check, changed input or rerun resulted from that auditor correction.

This is successful current whole-Python evidence, not `verify.py full`, hosted
CI, CLI/sandbox qualification, product acceptance or a matched speed comparison.
The original **151.73295s / 85%** target remains unmet. The failed `bab6bc08`
observation and all original pins/STARTs remain failed/immutable. This later
docs-only receipt does not relabel measured revision `b0ed49f3` or its inputs.
Unstable source-attribution candidates remain temporary pending Root review;
this receipt authorizes no implementation, profile or further execution.
