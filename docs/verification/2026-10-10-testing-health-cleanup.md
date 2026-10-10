# Testing health cleanup

Status: implemented, independently reviewed and locally qualified; exact hosted
qualification is pending. This receipt retains the baseline and failed attempts
separately from the corrected combined gate. Normal cutover is not authorized here.

## Baseline and scope

- Candidate: `codex/one-current-story-rebuild`; worktree:
  `/private/tmp/plotloom-one-story-rebuild.gfnqlc`.
- Before restructuring, `uv run pytest --collect-only -q` collected **1,469**
  cases in 1.41 seconds.
- Named-family baseline: 70 Python case IDs: 43 from
  `tests/generation/test_work_unit_contracts.py` (34 functions before parameter
  expansion) and 27 from `tests/test_project_storage_video.py` (23 functions
  before parameter expansion); frontend static tests expanded to 42 app-state
  cases and 34 video-pilot cases (32 registration expressions, including two
  two-row `it.each` registrations), 76 total.
- Production setup baseline was captured serially on this host in
  `/private/tmp/plotloom-test-health-baseline-20261010.pstats` using the exact
  two-test command described in the approved roadmap: 2 PASS in 53.06 seconds
  (freshness rebuild 28.16s; runtime HTTP intent 23.77s). Profiling attributed
  45.08s cumulative to 1,551 primitive / 1,579 total `subprocess.run` calls,
  mostly real currentness work in `cast_style._run` (30.34s cumulative) and
  `art_style._run` (14.77s cumulative). Runtime HTTP cleanup accounted
  for 23.60s in Starlette `TestClient`/AnyIO shutdown; this lifecycle remains
  real and will not be bypassed.
- Browser baseline from hosted CI38009336409: 276 selected cases, shard 1
  143 PASS / 34.6 minutes and shard 2 132 PASS / 17.9 minutes, with one flaky
  overall. The exact prior workflow used Playwright file sharding with
  `BROWSER_GREP` passed unchanged as `--grep`.
- No collected behavior is approved for deletion. The audit established no
  safe duplicate/retired-contract target; no tests are being removed.
- Current existing changed/untracked Python SHA-256 aggregate (70 files):
  `5fca2793a89c3d796bb2a39acff79ce68c9281b1e30f32c08048bb3df5d5b90d`.
  `tests/test_ci_browser_contract.py` is
  `e92d9a9fd843c7c18b5cd9cc38037633b55d3fc27eeb1e80b2921acc0d181556`;
  `frontend/e2e/fixtures/bridge_handoff_project.py` is
  `4470309fbf6667492c5eb263c58daae7b04c449694fdeaa897bfa17139dbe344`;
  `tests/test_native_bridge_intent.py` remains
  `92c3bdc7d5c728e6420403b06178c6e1b074573006acff46924530990950a781`.
  No Python product or dependency lock files changed.

## Pre-change behavior-to-module map

- `tests/generation/test_work_unit_contracts.py` (43 case IDs): scene facts
  and timing 269-654 -> `test_work_unit_scene_facts.py`; prompt contracts
  655-1005 -> `test_work_unit_prompts.py`; scene-fragment contracts
  1006-1328 -> `test_scene_fragment_contracts.py`; storyboard-fragment
  contracts 1329-1573 -> `test_storyboard_fragment_contracts.py`;
  continuity contracts 1574-1883 -> `test_storyboard_continuity_contracts.py`.
  Pure builders move to a non-collected fixture module; assertions and
  parameter cases remain intact.
- `tests/test_project_storage_video.py` (27 case IDs): review/predispatch
  contracts 41-379 -> `test_project_storage_video_review.py`; retained review
  recovery 380-523 -> `test_project_storage_video_recovery.py`; disposal
  524-785 -> `test_project_storage_video_disposal.py`; submission
  786-1019 -> `test_project_storage_video_submission.py`; reconciliation
  1020-1246 -> `test_project_storage_video_reconciliation.py`; dispatch
  faults/safety 1247-1551 -> `test_project_storage_video_dispatch.py`.
  Fake gateway and video fixture builders move to
  `tests/video_storage_fixtures.py`; image identity setup moves out of its
  collected test module to a non-collected fixture module. Existing external
  consumers in video review, retained evidence, and presentation integration
  now import fixtures, not collected test modules.
- `frontend/tests/app-state.test.ts` (42 registered cases): opening/drafts
  140-359 -> `app-state-opening.test.ts`; save lifecycle 360-607 ->
  `app-state-save.test.ts`; navigation/history 608-898 ->
  `app-state-navigation.test.ts`; generation/trace ownership 899-1204 ->
  `app-state-generation.test.ts`. Each module retains independent hooks,
  roots, mocks, and awaited unmount.
- `frontend/tests/video-pilot.test.ts` (34 expanded cases across 32 registration
  expressions): base candidates
  50-295 -> `video-pilot-candidates.test.ts`; route/branch playback 296-459
  -> `video-pilot-routes.test.ts`; review lifecycle 460-642 ->
  `video-pilot-review.test.ts`; session playback 643-874 ->
  `video-pilot-playback.test.ts`. Each module retains its own DOM/media/dialog
  isolation and cleanup. The disabled rejected-take reopening two-row case
  remains in the review module; bridge-history's stale/foreign-current two-row
  case remains in playback.
- The creator-confirmation spec uses only a static HTML fixture and validates
  DOM confirmation, keyboard focus, cancel/reload, and no native dialogs. It
  now uses the Vite-only fixture; API-backed creator specs remain on the full
  workbench.
- `test_production_bridge_intent._pending_project` uses a 9-cut/3-scene
  review board to test bridge semantics; preserve it. The setup helper
  `_accepted_f4_script` currently calls `_prepare_art_context`, which prepares
  then cancels a dummy Art candidate immediately before preparing the actual
  Art candidate. The accepted-source/outline/map/Cast prefix now has a
  purpose-specific helper for callers that immediately prepare Art, retaining
  the cancel-history helper for tests that exercise that history.

## Collected-case reconciliation

- A full `uv run pytest --collect-only -q` after the split temporarily reported
  **1,466**, not the 1,469 baseline. The three-case reduction was real coverage
  loss, not duplicate test-function collection: the `test_exact_ms` extraction
  omitted its attached four-row `@pytest.mark.parametrize("seconds,units", …)`
  decorator. Without it pytest collected one unresolved-fixture node instead
  of four valid cases. The body remained present, so searching only test
  definitions did not expose the omission.
- Restored the original parameter rows from the pre-change test at HEAD
  `bd04778` (`tests/test_production_presentation.py`, original lines 22–24).
  The expected baseline IDs and restored current IDs are exactly:

  ```text
  tests/test_production_presentation.py::test_exact_ms[2.5-2500]
  tests/test_production_presentation.py::test_exact_ms[1.001-1001]
  tests/test_production_presentation.py::test_exact_ms[5-5000]
  tests/test_production_presentation.py::test_exact_ms[100000000000000000000000000000000001-100000000000000000000000000000000001000]
  ```

- Verification after restoration: `uv run pytest --collect-only -q
  tests/test_production_presentation.py` collected 28 cases; `uv run pytest -q
  tests/test_production_presentation.py -k test_exact_ms` passed all four rows
  (24 deselected), exit 0. The full `uv run pytest --collect-only -q` then
  returned **1,469** cases in 1.19 seconds, exit 0. The intermediate 1,466
  result is retained here as a failed reconciliation observation, not a
  passing result.
- Independent source comparison at HEAD `bd04778` confirmed no other missing
  top-level test definitions or imported `test_*` bindings in the relevant
  source; a complete moved-test body and decorator/parameter-row comparison is
  now complete. The reviewer matched all 895 original top-level tests, found
  all 77 moved functions exactly once (75 AST-identical; two presentation
  integration bodies differ only in fixture import redirection), and found no
  missing definitions or imported `test_*` duplicates. Moved-case map:
  work-unit 34; video storage 23; Art-to-script 5; review reopen 2;
  bridge-intent HTTP 1; presentation-to-rebuild 1 plus integration 5; rebuild
  to dependencies 2 plus guards 4. The reviewer executed no tests and made no
  edits. This reconciliation demonstrates why AST/test collection equivalence
  must include decorators and parameter IDs, not just function bodies or
  aggregate counts.
- In the corrective review, all 32 original video-pilot registration
  expressions matched HEAD exactly once, including both two-row `it.each`
  chains. The E2E fixture's function bodies/main AST are unchanged apart from
  fixture import redirection; 214 moved-helper bindings across 58 Python
  consumer modules resolve, with no retired collected-owner import or
  compatibility re-export remaining.

## Browser allocation evidence

- Hosted attempt-level duration evidence contains 276 rows (143 on shard 1,
  133 on shard 2 including the flaky retry), totaling 1,633.000 and 781.534
  test-seconds respectively. Rows are attributed to their whole spec file;
  they are not shard wall times and omit runner/setup overhead.
- Current unfiltered Playwright collection reports 278 cases in 84 spec files.
  A longest-processing-time greedy bin pack assigns whole files into 42 specs
  per group. It estimates 1,212.434 seconds and 1,212.900 seconds of historical
  case time, with 122 and 156 cases respectively. The two newly added listener
  cases have no hosted timing and are imputed at the 5.4-second historical
  median per case (10.8 seconds total). These are estimates, not measured new
  hosted durations; global fixture/setup overhead and new-case behavior remain
  unknown, so this does not claim a hosted wall-time speedup.
- `frontend/e2e/browser-shard-manifest.json` is the explicit two-group file
  allocation. Playwright's supported `testMatch` file patterns select a group
  only when CI sets `BROWSER_SHARD=1` or `2`; local runs without that variable
  still select the complete suite. `fullyParallel: false` preserves default
  within-file order, while CI keeps `--workers=1`, so each runner owns at most
  one service stack at a time. Built-in `--shard` is removed to avoid a second
  partition.
- `frontend/scripts/check_browser_shard_manifest.mjs` fails closed if current
  spec files are missing, unexpected, or assigned more than once. It also runs
  Playwright `--list` for the unsharded suite and both manifest groups using
  the same `BROWSER_GREP`, then requires exact set union and zero overlap.
  With `BROWSER_GREP='.*'` it passed: 84 specs, 278 cases, 122/156, zero
  overlap or missing; the full-suite guard also explicitly requires both groups
  to be nonempty. With diagnostic `BROWSER_GREP='currentness'` it passed: 20
  cases, 14/6 across groups, zero overlap or missing. A one-case diagnostic
  passed as 1/0. The corresponding empty-group Playwright command exited 1
  without `--pass-with-no-tests`, then exited 0 with that public option and ran
  no test body. The guard independently refused a globally empty grep with
  exit 1. CI now uses that option only after the guard proves global nonempty
  selection and exact disjoint group union; the default `.*` guard additionally
  requires each group populated. These are local checks, not hosted runtime
  qualification.
- The creator-confirmation spec is the only reviewed API-in-memory journey
  using the Vite-only fixture; API-backed creator journeys remain on the
  provider/backend fixture. Its focused no-retry run passed once and left no
  Vite child process. No hosted rerun has been dispatched.

- Before the corrective restoration, the split-family Vitest run reported 72
  passes across eight files and the full frontend run reported 1,043 passes
  across 132 files. Both exited successfully but omitted the two `it.each`
  registrations/four expanded cases from HEAD, so neither is accepted as
  complete coverage. The restored expressions match HEAD exactly; independent
  review confirmed all 32 video-pilot registration expressions exactly once,
  including both chains and all four rows.
- The owner's attempted full browser run was interrupted after 8.8 minutes:
  179 passed, 9 failed, 2 interrupted, and 88 not run (exit 130). All nine
  failures stopped during fixture import on the same missing
  `_review_fixture_presentation` export from collected
  `tests.test_production_bridge`; no product assertion failed before setup.
  The consumer search also found stale imports from
  `tests.test_project_storage_art`. The two interrupted tests were caused by
  the intentional SIGINT. This
  is a red, unqualified full browser result, not a pass. The fixture now imports
  directly from `tests.production_bridge_fixtures` and
  `tests.creative_delivery_fixtures`.
- Corrected verification: the eight split Vitest files passed 76/76; the full
  frontend suite passed 1,047/1,047 in 132 files; `npm --prefix frontend run
  typecheck` and `npm --prefix frontend run typecheck:e2e` both passed. The six
  affected Playwright files were observed by the worker to pass 11/11 with
  `--workers=1 --retries=0` in 5.0 minutes. The retained
  `/tmp/plotloom-corrected-affected-e2e/.last-run.json` records `passed` and
  no failed IDs, but no complete console log was retained; that artifact alone
  does not prove the case count, duration or execution settings.
  `bridge_handoff_project.py --help` imports successfully, and a
  repository search found no remaining imports from the two retired collected
  fixture modules. The corrected frontend and focused browser results do not
  substitute for the owner's fresh combined browser/package qualification below.
- Frozen corrective source hashes: `frontend/tests/video-pilot-review.test.ts`
  `744ed8a152938c594be9a9ef006f309cedb6b8a144d2ff240bd2ef659239dfd4`;
  `frontend/tests/video-pilot-playback.test.ts`
  `926b3ac8cdd8f27f4eeabfb4c46a5bd59beaf87e332b024838027156f8ee7a60`;
  `frontend/e2e/fixtures/bridge_handoff_project.py`
  `4470309fbf6667492c5eb263c58daae7b04c449694fdeaa897bfa17139dbe344`.
- The only Python source changed in this corrective turn is the E2E seed helper
  `frontend/e2e/fixtures/bridge_handoff_project.py`, whose setup-function
  imports now point at non-collected fixture owners; its function bodies/main
  AST are otherwise unchanged. It is not a pytest test module. The serial full
  1,469-case Python gate is reused only within its verified input boundary;
  this helper's `--help` import smoke and the affected browser cases provide
  direct coverage of the changed import path. The later full browser gate also
  qualifies all current consumers.

## Production setup measurement

- The exact approved serial cProfile pair was rerun with the same command and
  method, writing `/private/tmp/plotloom-test-health-after-20261010.pstats`:
  2 passed in 55.76 seconds (freshness rebuild 29.57s; runtime HTTP intent
  25.10s), compared with the pre-change 2 passed in 53.06 seconds
  (28.16s; 23.77s). This does not demonstrate a latency improvement. The
  profile had 8 fewer `subprocess.run` calls, and `_accepted_f4_script` no
  longer performs a dummy Art prepare/cancel before preparing the actual Art
  candidate. Cumulative `subprocess.run` time nevertheless increased
  45.08s -> 47.31s; the evidence does not establish why.
- The real accepted-source/outline/map/Cast preparation, actual Art validation,
  freshness/currentness checks, TestClient lifespan, rollback/CAS and dispatch
  behavior are retained. The change removes only redundant setup in the
  accepted-script path; paths that verify canceled-Art history continue to use
  the history-building helper.

## Scoped local checks and evidence limits

- `npm --prefix frontend test -- tests/app-state-opening.test.ts
  tests/app-state-save.test.ts tests/app-state-navigation.test.ts
  tests/app-state-generation.test.ts tests/video-pilot-candidates.test.ts
  tests/video-pilot-routes.test.ts tests/video-pilot-review.test.ts
  tests/video-pilot-playback.test.ts`: the initial split reported 72 passed but
  was incomplete against HEAD; after restoring the four expanded parameter
  rows, the same eight files passed 76/76, exit 0.
- E2E typecheck passed with `npm run typecheck:e2e`; the focused
  `creator-confirmation.spec.ts` run passed once with `--workers=1
  --retries=0`, and `pgrep` found no remaining `vite-runtime.mjs` process.
- `BROWSER_GREP='.*' node scripts/check_browser_shard_manifest.mjs` passed:
  84 specs and 278 selected cases, 122/156, zero overlap or missing. The same
  guard passed with `BROWSER_GREP='currentness'`: 20 selected cases, 14/6,
  zero overlap or missing. The later interrupted full browser attempt and the
  corrected 11-case affected-spec run are recorded above; the owner retains
  the fresh combined browser qualification.
- `uv run pytest tests/test_ci_browser_contract.py -q`: 4 passed, exit 0. The
  updated contract asserts matrix-to-`BROWSER_SHARD` selection, absence of a
  second CLI shard, guarded `--pass-with-no-tests`, default-full nonempty shard
  checks, pre-run manifest guard and unchanged grep wiring, along with the
  original one-worker, artifact-upload, and deadline checks.
- The focused Python batch
  `uv run pytest tests/test_project_storage_art.py
  tests/test_project_storage_script.py tests/test_production_bridge.py
  tests/test_production_bridge_intent.py
  tests/test_production_bridge_runtime_http.py
  tests/test_production_rebuild_freshness.py
  tests/test_production_rebuild.py -q` used exec session19676. The last
  recorded poll showed continued dots; the process later disappeared and the
  session returned an unknown process ID without final output or a persisted
  log. This run is unqualified, not counted as pass or failure, and was not
  repeated. The subsequent full manager Python gate covers these modules; its
  terminal result and unchanged-input reuse boundary are recorded below.
- `git diff --check` passed after the reviewed browser adjustment. Ruff `check
  --select I,F401,F821` passed on the
  previously scoped changed Python modules. At that scoped checkpoint, combined
  gates and owner-controlled exact hosted qualification remained pending; the
  subsequent local closure is below. Ruff
  `check --select I,F401,F821` passed for the restored native-intent test and
  updated browser workflow contract. `python
  scripts/retained_runtime_coverage_inventory.py --check` passed after updating
  references and the source hash; original baseline/disposition/review/rationale
  were preserved. The focused multi-module Python session19676 remains
  unqualified because final output was lost; it was not repeated. The manager's
  later full gate and bounded reuse supersede that missing focused result without
  converting it into a pass.

## Manager combined qualification

The corrected frozen candidate is based on published branch HEAD
`bd04778af90c958dc630aa9f5d0e9db8dac26eb9`; the final executable/test commit and
hosted run identity will be recorded after publication. All 19 checks in
`/private/tmp/plotloom-corrected-qualification.WIAV60` ended with explicit
`QUALIFICATION_EXIT_CODE=0` markers. Complete logs remain in that directory.

- Python: **1,469 PASS /one existing Starlette warning in1,407.58s**. The original
  serial gate is `/private/tmp/plotloom-combined-qualification.EfhrzC/python.log`,
  terminal exit0. Independent review and the manager compare the original/current
  **515** input records under `src/`, `tests/`, `scripts/`, `manage.py`,
  `pyproject.toml`, `uv.lock`, `.github/` and `.gitmodules`: exact equality.
  No product, pytest, dependency or workflow input changed after that gate. The
  E2E seed-helper import correction is outside that Python reuse boundary and
  covered directly by the fresh full browser gate, not silently inherited.
- Frontend: **1,047 PASS /132 files in4.38s**; application and E2E typechecks PASS.
- Browser: **278 PASS in14.7m**, two workers, zero retries, unfiltered `--grep=.*`,
  exit0. No skipped, failed or flaky cases are reported. The command/header and
  terminal result are retained in `browser.log`. The allocation guard separately
  verifies all84 specs, disjoint122/156 hosted case groups and exact complete union.
  Local two-worker wall time is not a measurement of the hosted one-worker shards.
- Lock, scoped API F401 lint, compile, retained-runtime inventory, deterministic
  frontend build, checked static parity and archived prompt-reader verify PASS.
- Wheel build and installed-wheel smoke PASS using the external
  `wheel/plotloom-0.1.0-py3-none-any.whl`; no wheel artifact was added to the source
  root. The build retains the existing large-chunk warning, not a new failure.
- The1002-file executable/test input manifests before/after are byte-identical;
  both aggregate SHA256 values are
  `3c012e632927893b38c47a6bd3d7ce2695ba8c1440b215a1e308b46d38589c81`.
  Diff hygiene PASS; the pinned renderer submodule remains clean.

Source equivalence and evidence review are closed. The worker's missing four
frontend parameter cases and stale E2E helper imports were real cleanup regressions;
their red attempts above remain visible. The corrected full result does not erase
them or claim a measured setup speedup.

The native Create → Revise → Recover and finite E22 evidence remains separately
qualified by the Board3/presentation receipts. A fresh read-only native comparison
at `2026-10-10T03:59:25.903Z` again found eight equal endpoint projections,58 equal
asset hashes, four equal selected records and no differing endpoints;
`/private/tmp/plotloom-post-cleanup-readback.iHCqCu/readback.json` records r2 /
lifecycle9 active. Cleanup changed no application bytes, generation, reviews or
selection. Normal checkout remains clean and its checked JS is still
`3a8843193da3df6852f8b12731e33c90961dbe1339a9882b30fb2e03290555d5`;
the candidate JS remains
`0a4fd0e721b819da4ffec7d946e0af8f7c9ae3a90e9c4d473972951ac3ace160`.
Exact hosted qualification remains pending; normal/main cutover still requires
the separately requested retained-demo choice. No schema adapter or owner reset.

### Publication hygiene delta

The first staged `git diff --cached --check` refused95 whitespace-only blank lines
in the four newly split `app-state-*.test.ts` files. The earlier unstaged diff check
did not include untracked files; its PASS is not complete new-file hygiene proof.
The worker removed only blank-line whitespace. Manager and independent review
compare staged/worktree lines:95 changes, unchanged line counts, no non-whitespace
or other source delta; `git diff --ignore-space-at-eol --exit-code` PASS.

After formatting, all **1,047 frontend tests /132 files PASS in4.81s**, and both
typechecks PASS with explicit exit0 markers. Logs and before/after hashes are in
`/tmp/plotloom-final-hygiene.qMZDrK`. The original Python/browser/package gates are
reused only because application, E2E, package and Python inputs remain exact and
the four unit-test deltas are proved semantically unchanged. The final1002-input
publication manifest differs from the full-gate manifest only at those four files:
`/tmp/plotloom-final-hygiene.qMZDrK/publish-inputs.sha256`, SHA256
`880a19c371bfafea6644dda771bff4fb95869b1f932056580ee09f83fc68911e`.
This is the formatted-tree fingerprint, not a claim that the original whole-tree
hash stayed identical through formatting. The final staged hygiene check is
required before commit; no gate is bypassed.

A further read-only native comparison at `2026-10-10T04:28:39.188Z` again matches
all eight projections,58 asset hashes and four selected records with zero differing
endpoints, r2/lifecycle9 active. Artifact:
`/private/tmp/plotloom-prepublish-readback.OB7m17/readback.json`.
