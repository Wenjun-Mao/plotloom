# Batch-video implementation qualification, 2026-10-18

Status: initial integrated source checkpoint; local qualification combines full-run
evidence with an exact test-contract rerun and downstream package checks.
Publication and activation are held for manager review. Technical evidence does
not establish human creative acceptance.

The [manager correction checkpoint](2026-10-18-batch-video-corrections.md) records
source `20e3c65b`, its affected regressions and evidence reuse after this checkpoint.

## Source and authority

- Retained checkout: `/Users/wjmao/.codex/worktrees/b30f/plotloom`, `main`.
- Baseline: `c5aabe252a83c6aa6708fbbbcf4fe704a771eaa3`.
- Initial product candidate: `575907e7`; qualified test-contract revision:
  `52ad5889` (only the navigation regression assertion changed). Subsequent
  checkpoint documentation does not alter executable inputs.
- Owning plan: `docs/roadmap/2026-10-18-batch-video-production.md`.
- Contracts: ADR 0192 inspection/authority and ADR 0193 frozen video batches.
- One source writer. Independent read-only reviews found and verified corrections
  for dispatch inventory races, native draft retention, control CAS, immutable
  confirmation versus mutable selection revisions, proposal rebinding, retained
  prediction observation, late acknowledgment focus and the existing story player.
  The final progress-only review found no actionable findings.

## Root causes and changes

Each raw image formerly repeated full retained-evidence admission. Raw reads now
use exact inspection with lifecycle/confinement and requested-byte hashes;
authoritative metadata, writes, dispatch and approval keep full validation.
Geometry/handoff proof reuse ends with the request. Repeated SQL gate decoding
and whole production-closure construction caused the remaining material commit
latency; immutable scalars now share only the same request/connection/mutation,
data-version and outer/nested transaction snapshot. Rollback and external writes
invalidate that reuse; file bytes are outside this SQL cache. Outside a proof
scope, the scalar helper computes directly and preserves the ordinary session
protocol rather than requiring a SQL connection.

Batch production inventories all unique route shots, preserves good selections
and observes existing known work, then freezes complete assistant English drafts,
compiled prompts, profiles, seeds and bounded workload at explicit Start. Existing
native video owners perform preparation, claim-before-transport, reconciliation,
ingestion and unselected segment proposals. UNKNOWN is never resent. One final
explicit audiovisual confirmation selects all proposals in one transaction.
Manual window preparation updates the unconfirmed proposal pointer/review CAS.
A superseding setup does not stop reconciliation of earlier known predictions.

Completion intent starts at an explicit command, before asynchronous work.
Visibility/navigation invalidation survives a late response. Material approval's
HTTP acknowledgment and polled handoff share one pending completion owner, so
either ordering refreshes exactly once. Successful video approval refreshes the
existing player without recreating or discarding unrelated editors.

A settled batch no longer triggers repeated full background admission scans.
Progress reads count exact linked job states without rebuilding the complete
video gallery; final review retains full authority and byte validation. These
changes address measured work at its owning layers, rather than weakening review.

## Executed qualification

Logs are retained under `.local/batch-video/` in the source checkout.

### Final full candidate

Command: `uv run --locked --no-sync python scripts/verify.py full`.
Product candidate: `575907e7`; log: `full-final.log`.

| Gate | Result |
| --- | --- |
| Locked dependencies; FFmpeg/FFprobe; API F401; archived prompt reader | Passed |
| Unfiltered frontend unit suite | 1,409 passed, 161 files |
| Application type contracts; browser fixture type contracts | Passed |
| Native Python suite | 3,257 passed across 280 files, workers 1,795/1,462 |
| Deterministic production build and checked-asset parity | Passed |
| Unfiltered browser shard manifest | 335 cases, 95 specs; zero missing/overlap |
| Complete browser execution | 334 passed; one obsolete URL assertion failed |
| Corrected navigation spec at `52ad5889` | All six cases passed, including the failed case |
| Wheel build and isolated installed-wheel smoke | Passed |

The full invocation exited one solely because the existing navigation journey
expected `stage=storyboard` without the approved `#video-batch-production` target.
The trace showed the correct destination. The exact assertion now requires that
hash and additionally requires the batch heading to be in the viewport. This
changes only the test, not product behavior. `navigation-contract-final.log`
records the six-case focused rerun and E2E type check, both passing. The 334 other
browser cases and all backend/build evidence retain unchanged inputs; those
results are reused under the repository's evidence policy. The final local
qualification is composite, not a claim that this full invocation exited zero.

The Python native runner completed in 976.968 seconds. The full invocation took
1,553.339 seconds through its browser failure; it stopped before wheel gates.
The exact downstream commands are `uv build --wheel --out-dir
.local/batch-video/wheel-final` and `uv run --locked --no-sync python
scripts/smoke_installed_wheel.py .local/batch-video/wheel-final`; their retained
output is `wheel-final.log`. The prior navigation failure screenshot, trace and
video remain under `full-browser-navigation-failure/`. No release gate was
filtered, waived or removed.

The first full attempt (`full-candidate.log`) completed all 3,256 Python cases:
3,250 passed and six failed. All six exposed the same scalar helper protocol
regression outside a proof scope. The fix restores uncached calculation at that
boundary; no assertions or coverage were weakened. The final full rerun is
necessary because that fix, the idle controller predicate and progress-read
changes alter executable inputs. Both attempts remain retained.

### Scoped evidence and assets

- `quick-source-final.log`: quick tier passed, 1,409 frontend unit cases across
  161 files and both application/E2E type checks. This is feedback, not release
  acceptance.
- `module-contract.log`: four-owner contract union initially failed 17 of 1,254
  Python cases. Root causes: prior-layout fixture construction retained new
  tables; nested lifespan ownership; a closed/no-work startup open; raw corrupt
  video diagnostics. `module-failure-regressions.log`: 47 explicit failed/affected
  cases passed after correction. No assertions were weakened.
- `projection-contract-fix.log`: 24 cases passed, including receipt projection,
  proof scope, realistic 42-shot and native review cases.
- `idle-controller-regressions.log`: 38 material-byte, proof-scope, recovery and
  review cases passed. `progress-read-regressions.log`: 18 API, recovery, review
  and inspection cases passed, including progress linked-job state coverage.
- `proof-cache-regression.log`: request/write/rollback/nested rollback/external
  commit regression passed; independent review also checked an external commit
  with unchanged SessionTransaction.
- `final-native-browser.log`: 21 explicit batch/autopilot journeys passed.
  `material-confirm-ordering.log`: 19 autopilot journeys passed, including polling
  before a delayed 6.5-second acknowledgment and exactly one handoff refresh.
  Native batch journeys cover actual StoryboardPage approval-to-playback, process
  restart while paused, unrelated edit/focus preservation, stale approval response
  visibility and six real decoded audiovisual clips. Complete 42-image material
  review uses native APIs/storage/approval with fake provider transport.
- Deterministic frontend build twice: seven-file SHA-256 tree matched, receipt
  `3547147c28931063e22f124199a40c61bbfe1bd6253a291e86d91673887ef87c`
  in `static-tree-final.json`. Backend-only candidate changes preserve those assets.
- Desktop pixel inspection: saved playback action visible below sticky chrome
  at 1280×460, 1280×768 and 1700×900. Final native batch screenshots were inspected
  and retained under `desktop-final/` before the focused rerun cleared outputs.

## Performance measurements

Controlled local fixture: 42 distinct production shots, five reference sets,
genuine retained image/native evidence and one geometry preparation. Provider and
Codex supervisor transport are fake; API, schema, approval, storage, selection,
FFmpeg media and native artifact validators are real. Test data and fake profiles
are isolated from the running installation. These local measurements are not
owner media acceptance or internet-wide latency promises.

The first material confirmation response measured 13.05 seconds. A profile found
267 repeated image-authority checks and approximately 379k canonical gate decodes.
After exact SQL snapshot reuse, unprofiled measurements were:

| Read/action | Seconds |
| --- | ---: |
| Awaiting material review, first/repeat | 0.676 / 0.453 |
| Material confirmation response (includes commit) | 4.876 |
| Post-handoff consolidated metadata refresh | 0.329 |

Source: `projection-contract-fix.log`. An earlier six-case native qualification
recorded 4.356 seconds for confirmation and 0.363 seconds for refresh
(`scalar-cache-qualification.log`). These are response timings, not isolated SQL
commit times or browser readiness.

Browser readiness below waits for loaded material pixels, no media error and an
enabled review confirmation action. Video review waits for the enabled whole-pack
action and all 42 video elements; clips use `preload=none` and are not downloaded
eagerly. Neither material nor video confirmation was clicked in this measurement.

| Fixture state | Cold seconds | Warm seconds | Requests | Transferred bytes | Encoded body bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Awaiting 42-image review | 1.935 | 1.830 | 49 | 809,675 | 794,975 |
| Completed v3 handoff material review | 2.361 | 1.821 | 49 | 809,633 | 794,933 |
| Prepared 42-video review | 3.855 | 3.830 | 2 | 1,538,950 | 1,538,350 |

Sources: `gallery-qualified.json` and `gallery-qualified.log`. Each material page
loads 47 images including five reference sets. Synthetic PNG payloads are small;
owner photographic payload/network behavior remains unmeasured. Earlier prepared
review measurements of 10.90–11.37 seconds, an intermediate 5.84–5.87 seconds and
a 7.38-second warm sample under concurrent full-suite load remain retained in the
benchmark logs. Profiling identified settled background scans and repeated full
job-gallery construction; the final controller/progress changes address both.
The final controlled samples meet the planned cold ten-second/warm five-second
limits, without claiming those limits for all environments.

The isolated native runner completed 42 jobs, 210 requested source seconds and 42
unselected proposals; selected segments and final receipts both remain zero
(`native42-facts.json`). Real FFmpeg source clips contain native AAC audio. Only
transport is fake; no paid/live provider generation occurred. Benchmark servers
were stopped after those jobs settled.

## Deliberately separate delivery state

No owner creative approvals or owner-story generation were performed. No deployment
checkout, container, owner assets or project data were changed. The deployment
checkout remains detached at `7b90bbc70d69aeb7a1bfda2c4af1b6e25759560f`.
The new exact current schema is incompatible with the previous current schema;
activation needs an explicit manager-directed preservation/quiescence assessment
under the approved targeted development-data policy. The owner's old-schema
42-shot project remains untouched. No compatibility migration or broad cleanup
was added. Do not activate this schema over valued media or unsettled work by
assuming it is disposable.

Bounded live provider/supervisor smoke needs a still-current, already owner-reviewed
fixture; one was unavailable, so live smoke remains a disclosed gap. Post-activation
and owner-payload performance also remain unmeasured. No push, hosted CI success,
installation activation or product acceptance is claimed. Publication and
activation await the manager's review of this checkpoint.
