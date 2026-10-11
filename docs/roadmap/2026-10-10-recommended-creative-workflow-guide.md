# Recommended creative workflow guide

Status: guide and concrete branch-control correction published on main. The
one-graph/two-views refinement is published as `7da7b6e`; its required unfiltered
hosted run 38101824564 remains in progress. Hosted CI is separate: original run
38098197412 on 4955bbf completed with verify passed and both browser shards failed;
correction run 38101073289 on 63b25f4 is in progress at this check. The isolated
modular-verification task owns completion follow-up. This status-only update
does not change the qualified executable inputs or require another dispatch.

## Owner walkthrough correction — one graph, two views

Status: published as `7da7b6e` after local qualification (2026-10-10); hosted CI pending.
Trusted baseline: `63b25f461367b5732e08e6aac5eef3c429721f75`.

The workbench switch exposes two presentations of the existing shared graph
draft, but route classification labels professional graph editing as step 3
and creator graph editing as step 4. The switch also incorrectly marks every
non-creator page as the professional view. This makes view navigation look
like lost progress and hides the shared-graph relationship.

Deliverable: label the switch as two views of one graph; mark only the actual
graph view active; classify both graph routes as step 4, `剧情图编辑`, with a
separate view label. Source-page branch preparation remains step 3. The step
number describes the current activity, not a completed percentage. Preserve
the existing shared draft owner, guarded navigation and independent save,
confirm and apply operations. No persisted progress or alternate graph copies.

Evidence: focused workflow mapping and guard regressions; disposable browser
switches in both directions, shared unsaved draft/selection and unchanged
canonical readback; supported desktop pixel inspection; unfiltered frontend
tests, both type checks, repeat deterministic builds and independent review.
Actual dependency review must confirm this is a bounded frontend change before
using risk-scoped local qualification. Suite tooling stays with the isolated
M0–M5 task. Exclude owner project/state, Safari operations, generation and live
service restarts. Stop after scoped main publication and one required
unfiltered hosted-CI dispatch, reported separately from local qualification.

Local qualification evidence against that baseline:

- Actual executable diff changes guide classification/copy and layout, graph
  page descriptions and the existing sidebar switch presentation. Its extracted
  component invokes the same guarded navigation with the same route arguments
  and disabled conditions. No backend/API schema or request payload, graph/draft
  ownership, persistence, admission, auth, provider/prompt, dependency, build or
  package contract changes. Internal view labels do not introduce server state.
- `uv run --locked --no-sync python scripts/verify.py quick`: 1,074 tests across
  133 frontend files, both TypeScript checks, lock and API unused-import checks
  passed (12.606s). These source/type inputs remain unchanged by the subsequent
  expanded-guide CSS repair.
- `verify.py focused --vitest tests/recommended-workflow.test.ts --playwright
  e2e/recommended-workflow-guide.spec.ts --playwright
  e2e/creator-workbench-story.spec.ts`: 25 model cases and all 5 browser cases
  passed (17.480s). Both graph views remain step 4 for applied, mismatched,
  failed-read and read-only states, without weakening exact identity checks.
  The disposable branch journey switches in both directions at all three
  approved sizes, retains the selected node and unsaved graph title, and leaves
  source/accepted-map/admission readback unchanged. The existing script-draft
  mode-switch, failed-read recovery and unsaved navigation cases also pass.
- The first browser attempt exposed an expanded-layout overflow at 1280px:
  the non-shrinking details flex item used its longer paragraph's intrinsic
  width and squeezed the current-step label. Expanded details now take a
  full-width row with a bounded minimum width. The same width/height checks
  pass after repair; no assertion or supported viewport was removed.
- Directly inspected creator/professional screenshots at 1280×768, 1280×460
  and 1700×900, plus the expanded guide at 1280×460. The shared-graph switch and
  compact step/view label fit; sticky placement and no page overflow pass.
- Two deterministic builds match sorted static-tree manifest SHA-256
  `3f05eceef0408a37a3b69578420cdfb4fde351ef35f35272b46e16211819686f`.
  No-cache normal8841 reads match local `/v2/workbench.js` SHA-256
  `182d45787330dd264c737b69669819633b03df12b4a18c3c7de317c80b7cc2cc`
  and `/v2/workbench2.css` SHA-256
  `0a9066ec0305d9a56414bc6ad66c54c94716c6fe957e286a9b1f9d90df570ed0`.
  `/healthz` is healthy; no service restart or owner-project read/write occurred.
- Independent GPT-6 Luna / Max stable-candidate review found no findings and
  confirmed the existing guarded navigation, shared graph owner and unchanged
  API/persistence boundary. Required unfiltered hosted CI was dispatched once
  with `browser_grep=.*` on executable SHA
  `7da7b6efa20e43a3b2d692eeac7defe6838a1e1c`:
  [run 38101824564](https://github.com/Wenjun-Mao/plotloom/actions/runs/38101824564)
  is in progress, not counted as passed before terminal success.
  Local frontend qualification is not full
  local release qualification or owner product/creative acceptance.

## Earlier correction — concrete branch next controls

Status: implemented and locally qualified (2026-10-10); hosted CI pending.

The owner found that a delivered branch suggestion was described generically
instead of naming `带入可编辑草稿`. Root cause: task-specific advice lived under
the outline step, which route classification no longer selected after outline
acceptance. Correct the branch step and observe the existing graph-draft owner
to distinguish delivery, import, incomplete draft, confirmation and application.
The guide remains advisory, and the owning controls retain all mutation guards.
This correction does not change source/server contracts, dependencies, providers,
project settings or the owner's story. ADR 0155 records the refined invariant.

Independent review found two adjacent availability gaps: manual `刷新` did not
retry the graph owner, and a successful shared source read could hide a failed
page-local stage read. Manual refresh now retries both owners; project/basis-
scoped branch observations report the owning panel's actual edit restrictions.
The reviewer confirmed both causes repaired with no additional production-code
findings. Its assertion-wording finding was also corrected.

Qualification against trusted baseline `b8dc2aff312fab6e4df1a52d58268848f61d13da`:

- Actual diff: frontend guidance/owner observations, a shared existing dirty
  check, explicit manual read retry, tests, ADR/receipt and generated JS only.
  Backend/API schemas and request payloads, persistence, admission, auth,
  providers/prompts, dependencies, build tooling and packaging are unchanged.
  No second draft owner or compatibility path was introduced.
- `verify.py quick`: 1,072 tests across 133 frontend files and both type checks
  passed (12.371s), plus the runner's lock and API-unused-import checks.
- Focused model/source/project-read checks: 39 tests passed using
  `tests/recommended-workflow.test.ts`,
  `tests/project-directory-read-recovery.test.ts` and
  `tests/outline-cancel-reprepare.test.ts`.
- `verify.py focused --playwright e2e/recommended-workflow-guide.spec.ts`:
  both browser cases passed (11.395s). The real disposable project traverses
  prepared task → deterministic delivery → import → incomplete/complete draft
  → confirmation → application → later unsaved revision. Injected graph and
  partial stage GET failures verify named retry and action suppression/recovery.
  Guide inspection preserves source readback; no specialist was dispatched.
  Two earlier browser attempts stopped on mismatched test error wording, not
  product failure; assertions were aligned with the observed guide/API transport.
- Imported-suggestion screenshots inspected at 1280×768, 1280×460 and 1700×900;
  compact advice and the actual import control fit. Expanded/sticky geometry and
  the existing unsaved-draft navigation protection also pass.
- Two deterministic builds match sorted static-tree manifest SHA-256
  `1cfeade34c909798479f22d17f3afbede90fcfc434f7b948ff30b685dc2bb75c`.
  No-cache GETs of `/v2/workbench.js` and `/v2/workbench2.css` from normal8841
  match local bytes: JS
  `9a71f57f6673d18d9e9759deb1abb4e559250c10d7a80838fc0525b13b7deffd`,
  CSS `3a9232c1494593f281de68e182649bd955f690abad74f1f9d42e7d588917b9ae`.
  `/healthz` is healthy. No service restart or owner-project operation occurred.

Required unfiltered hosted CI must be dispatched on the published correction
SHA and reported separately; this local evidence is not a full local release
gate, hosted success or owner creative acceptance. No broad local suite rerun
for this unchanged-backend frontend correction.

## Original guide delivery

Prepared October 10, 2026.
Authority: owner-approved follow-up coordinated through manager
<code>01a04525-e907-7630-9640-78790d69e8ae</code>; retained <code>main</code>, one source owner.
Baseline: <code>bc4d6ec98a20dec3962c6d40724a05898e637ae8</code>.

## Approved outcome

Add a compact, always-visible recommended process guide beneath the workspace
toolbar for Brief, source/outline and branch work, Creator, production/review,
and storyboard routes. The sequence is 项目简报 → 来源与大纲 → 剧情分支 → 创作工作台 → 制作与审阅 → 播放. Show a route-aware current step, authoritative status,
one next action and an expandable six-step view. Keep the guide advisory and
preserve manual graph authoring, return navigation, draft protections and the
distinction between interactive playback and static reading.

## Scope and exclusions

Use existing workspace routes and state owners. Do not create, generate or
accept product content; modify owner project <code>a46790f2-981d-4454-a9f4-8679d70e65e5</code>,
jobs, settings or drafts; restart normal8841; or change backend behavior. Support
the approved desktop viewports 1280×768, 1280×460 and 1700×900.

## Candidate evidence

- The shared guide and project/revision-scoped source-review owner are
  implemented in the workspace shell. Concurrent source reads are coalesced;
  mutations invalidate older replies. Branch-task status is tied to the exact
  accepted outline/map and Brief basis.
- Route/status/currentness tests cover source revision mismatch, branch map
  identity and graph content hash, production subroutes, read failure,
  read-only state, and player versus static report wording.
- Independent implementation review found an unsaved-source navigation gap
  and a false “reading” status for blank workspaces. Both were fixed at the
  workflow model/state boundary; a follow-up read-only review found no further
  findings. Regression coverage checks draft action suppression, blank versus
  pending project status, and source-editor dirty-state reporting.
- The owner approved risk-scoped local frontend qualification on October 10.
  <code>ADR 0156</code>, <code>AGENTS.md</code> and <code>docs/development.md</code> record the evidence boundary and exact
  commands. Review against baseline
  <code>bc4d6ec98a20dec3962c6d40724a05898e637ae8</code> found changes only in frontend
  UI/state wiring, tests, documentation and generated static assets. Backend
  APIs, API request/response types, persistence, schema, admission,
  authentication, provider/prompt behavior, package manifests, lockfiles and
  build tooling were unchanged; frontend file paths alone were not used to
  establish the boundary.
- <code>uv run --locked --no-sync python scripts/verify.py quick</code> passed: 133 Vitest files /
  1,058 tests, application types and browser-fixture types.
- Focused verification passed with selectors
  <code>tests/recommended-workflow.test.ts</code>,
  <code>tests/project-directory-read-recovery.test.ts</code>,
  <code>tests/outline-cancel-reprepare.test.ts</code> (25 tests total),
  <code>tests/test_ci_browser_contract.py</code> (5 tests), and
  <code>e2e/recommended-workflow-guide.spec.ts</code> (1 Playwright test).
- The browser case exercised the source-editor dirty indicator and save, the
  existing unsaved-Brief navigation dialog, the expanded guide and sticky
  placement at 1280×768, 1280×460 and 1700×900. Screenshots were inspected;
  the expanded guide fits at 1280×460.
- Two deterministic builds produced identical sorted static-tree hash
  manifests (manifest SHA-256
  <code>4ca73cd31cf938c6a10d46e8c5530d8853ce503713a8ffb2da0f5ece3d12e6bf</code>).
  No-cache GETs from normal8841 matched the local generated bytes exactly:
  <code>workbench.js</code> SHA-256
  <code>49810a6db245a1154e8f59b1dfcb7c3751932255c6d444d22f4316f207e84f26</code> and
  <code>workbench2.css</code> SHA-256
  <code>3a9232c1494593f281de68e182649bd955f690abad74f1f9d42e7d588917b9ae</code>.
  The service was not restarted.
- One initial <code>full</code> run passed the frontend suite and all 1,492 Python tests,
  built the candidate assets, then stopped at the Git-baseline parity check
  because those generated assets differed from the checked-in baseline. The
  assets were retained and rebuilt deterministically. After the owner approved
  the risk-scoped policy, the redundant second <code>full</code> run was stopped during
  its Python step at about 48%; it is not counted as a result. These observations
  and the reason not to repeat unaffected suites are documented in
  <code>ADR 0156</code>.
- Independent read-only policy review found the local frontend gates concrete
  and current, confirmed that the policy reviews actual dependencies rather
  than inferring safety from file paths, and found no new verification tier or
  infrastructure implied. It identified one hosted-CI evidence boundary:
  <code>.github/workflows/ci.yml</code> runs only through <code>workflow_dispatch</code> and accepts a
  <code>browser_grep</code> input (default <code>.*</code>). The workflow file does not enforce required
  unfiltered status. The owner-required gate will therefore be explicitly
  dispatched with <code>browser_grep=.*</code> after publication and its actual result
  reported separately; no workflow filter or waiver was added.

## Approved verification-policy correction

The owner approved a durable risk-scoped local qualification policy on October
10, after the observed bundle-parity failure. It permits bounded UI guidance
changes using unchanged contracts to qualify through unfiltered frontend tests,
both type checks, repeat-build hash comparison and affected browser/pixel
checks. Cross-layer, contract, dependency/build-tool and uncertain changes
still require unfiltered <code>full</code>; hosted CI remains mandatory and separate.
This is policy documentation, not a new verification runner tier. The separate
modular-suite follow-up is owner-approved for M0–M5 in an isolated worktree;
it is recorded at
<code>docs/roadmap/2026-10-10-testing-health-cleanup.md</code>.

## Remaining acceptance and stopping condition

Scoped publication is complete: guide/policy commit <code>e6ca2d1</code> and separate
planning-note commit <code>4955bbf</code> are on main. Required unfiltered hosted CI
run <code>38098197412</code> (<code>workflow_dispatch</code>, <code>browser_grep=.*</code>) was dispatched on
<code>4955bbf1d64edbc2d432dc99bfc88b8faaeb3e8c</code>; at the last original-delivery
check, verify passed in 15m26s and both browser shards were in progress.
This historical run does not qualify the correction above. Local frontend qualification does
not imply hosted CI completion, full local release qualification, owner
walkthrough acceptance or creative acceptance. Do not restart normal8841.
Owner refresh guidance is <code>⌘R</code>, then <code>⌘⇧R</code> if the open browser tab still shows
the previous bundle.

## Applied-route next-control refinement — approved

The owner requested that the compact guide itself show both application success
and a concrete next production instruction. Root cause: its graph-view branch
already verified exact applied admission, but returned generic editing advice
and did not give pending graph edits precedence. The owning frontend projection
now checks the existing graph read/draft state, then shows a distinct applied
status and names the first reachable footage section and Creator `制作` tab for
step 5/6. Professional view first names its return-to-Creator control. Titles
come from the exact accepted map, not this owner's story or current selection;
route-only and unconnected nodes are skipped. Pending field buffers count as
unconfirmed edits. No reachable footage is not a production-completion claim.
Independent review identified two advisory edge cases: pending JSON fields must
name field submission rather than unrelated structural edits, and editable
titles can repeat. Both are handled explicitly; ambiguous titles fall back to
selecting a filming node on the current route, without adding selection state.

Scope against trusted `aca29bc`: advisory projection/rendering, shared graph-draft
observation, styles, regression coverage, documentation and generated assets.
Backend/API schemas and payloads, persistence, admission, auth, providers/prompts,
dependencies, build tooling and package contracts remain unchanged. No new read,
selection action, confirmation/application authority or production dispatch is
introduced. Preserve the current graph-page step index and existing navigation
guards. ADR 0155 records the contract; ADR 0156 supplies bounded frontend
qualification. Earlier release failures still prohibit push. Tests and pixel
checks must prove both-view state transitions, native writes without reload,
pending/unavailable-state suppression and no owner-project mutation.

### Executed local qualification

The stable refinement diff is based on `aca29bc987e7dec13db7f2ccc75cf6223ee554c0`.
Its actual dependency surface remains within ADR 0156's bounded frontend policy;
the review corrections do not change requests, persisted drafts or admission.

- Focused Vitest: `recommended-workflow.test.ts`,
  `workspace-workflow-guide.test.ts`, `graph-confirmation-read.test.ts`:
  **53 passed** (3 files).
- `verify.py quick`: unfiltered frontend **1,115 passed** (135 files), both
  frontend/browser-fixture type checks, locked-dependency check and API F401
  lint passed; 10.637 seconds total. No full Python integration rerun.
- Explicit Playwright selection: `recommended-workflow-guide.spec.ts`,
  `creator-workbench-production.spec.ts`, `creator-workbench-delivery.spec.ts`,
  `production-rebuild.spec.ts`, one worker, grep
  `applied graph status|real next branch control|workflow visible|graph confirmation and application|creator Production|checked bundle|checked production controls|same project recovers`:
  **11 passed**, about one minute. Includes native Confirm/Apply without reload,
  dirty/incomplete/pending-field recovery, retained selection/media, manual
  production-tab entry and source branch progression. Disposable fixtures only.
- Inspected both applied views at 1280×768, 1280×460 and 1700×900, plus the
  pending-field short viewport, expanded short guide and checked clean entry.
  Status/instruction rows are readable without clipping or horizontal overflow.
  Evidence: `/tmp/plotloom-applied-guide-review-20261010/`.
- Two deterministic builds matched all seven static files. SHA-256 of the
  sorted path/hash manifest JSON:
  `7e22d1b53cd4308e1b5e8fff4e78e9120f48611ea80059fe9724f556e8b7c904`.
  No-cache normal8841 static GETs returned HTTP 200 and exactly matched local
  JS `d30499ee4bb869a1b21b391b135cec3c1023b5ac2c00c92f367a3dc11a8b6566`
  and CSS `6d9ed4e83d49b4ee0d4a35516929085f69cbd7f1f644880ddc9813a71ed1bb87`.
  The existing large-chunk warning remains unchanged.
- Browser shard manifest: 85 specs, 285 selected cases split 124/161, no overlap
  or omissions. `git diff --check` passed.
- Independent read-only review requested GPT-6 Luna / Max; effective host model
  settings were not independently verified. Both concrete findings were fixed
  and re-reviewed as resolved, with no related defect. Reviewer ran no checks.

This is local frontend qualification, not full release or hosted-CI success.
The earlier `e923b58` full gate's six browser failures and unrun downstream
package gates remain outstanding; do not push or waive them. No owner project,
normal8841 runtime or creative content was mutated; only its served static UI
assets changed. Owner refresh/walkthrough acceptance remains pending, and any
pending user edits must be preserved before refreshing.
