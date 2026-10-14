# Python context reuse and bounded worker experiment

Status: owner-approved slice implemented, independently reviewed, locally
full-qualified and integrated on October 14, 2026. This continues the
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

## Residual-cost investigation — not an approved implementation

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
