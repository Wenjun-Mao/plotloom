# Python context reuse and bounded worker experiment

Status: owner-approved slice implemented, independently reviewed and locally
full-qualified on October 14, 2026; publication pending. This continues the [testing-health plan](2026-10-10-testing-health-cleanup.md),
not a redefinition of its 85-percent complete-suite wall-time target.

## Authority and baseline

The owner approved operation-local production Script/Storyboard context reuse
and experimentation with four Python workers. Eight workers are permitted only
after measured memory/isolation headroom. The released default remains two.
Broader Production Bridge reuse, cross-operation caching and coverage reduction
are excluded. [ADR 0167](../adr/0167-operation-local-storyboard-context.md)
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
