# Python context reuse and bounded worker experiment

Status: the first owner-approved slice was independently reviewed, locally
full-qualified and integrated on October 14, 2026. The later historical-scheduler
and geometry-fixture continuation is implemented with focused checks and
independent review; scoped geometry measurement passed, while whole-suite
measurement and combined full qualification remain open. This continues the
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
