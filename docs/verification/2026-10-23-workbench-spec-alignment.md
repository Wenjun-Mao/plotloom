# Workbench specification alignment · 2026-10-23

Status: implemented source candidate, focused verification in progress; independent
review and final frontend qualification pending. Activation and owner acceptance
remain separate. The approved [plan](../roadmap/2026-10-23-workbench-spec-alignment.md)
binds this receipt. Source baseline is clean retained R at `d029e536`; no work was
performed in installed P or the default Narrative-Forge checkout.

## Root causes and implemented boundaries

| Contract | Cause and repair layer |
| --- | --- |
| Editable labels | Fixed lanes had unbounded button height. Bound the full-text button to 80px with native internal scrolling, complete accessible text and keyboard exact-edge editing. No story truncation or schema change. |
| Pro selection | Controlled nodes omitted shared selected state; native Enter/Space never reached the owner. Project shared selection and route keyboard activation to the existing owner. |
| Brief counts | Display wrongly required write-capable draft data. Share topology-only counting with draft completeness kept in its authoring wrapper. Snapshot the named draft/canonical/unknown basis together with before/after targets when opening preview. |
| Global action status | Creator and Pro independently composed prerequisites. Share read-derived availability/currentness from existing graph, Source/Outline and production owners; actual commands and write guards remain unchanged. |
| Pro navigation | Inherited wheel policy consumed document navigation. Explicit Pro props allow native page wheel, deliberate pinch/controls and background pan in both authority states. Canonical Pro gets a bounded technical viewport; Creator retains its natural-height shell. |
| Pro lifetime | Page-local positions and uncontrolled viewport vanished on mode unmount. A workspace-scoped in-memory session holds visual context only; project replacement/provider exit resets it. Pro's project key resets its own local projection, never the graph provider. Old callbacks retain only the retired session object. |

Expanded native testing exposed a second canonical wheel cause: `overflow:auto`
on the node shell included the default handles protruding beyond its boundary.
The retained trace shows a short decision node consuming wheel into `scrollTop=3`
while page/transform remain unchanged. Keep the shell non-scrolling and confine
intentional long-text scrolling to an inner label. This repairs the presentation
contract rather than forwarding wheel events or adding a global listener.

The canonical unknown-read preview journey also exposed a recovered-Brief ownership
defect: workspace `value` contained recovered author input, and `rememberDraft`
updated that recovered payload on each edit. Comparing Save's proposed targets
against `value` therefore compared the working draft with itself and skipped the
preview; retained DOM shows formal Save at 41 without consent. Supply saved
canonical Brief separately for before/target comparison, saved visual-direction
display and launch dirty comparison. Only editable hydration uses recovered
`value`. This repairs the existing preview/currentness contract at view wiring;
it changes no persistence, generation code, payload or approval mechanism.

Actual diff boundary: frontend projections, view wiring, CSS, frontend tests and
checked generated assets only, plus these existing-spec records. API clients and
request construction, backend/schema, persistence/admission/auth, provider/prompts,
dependency/lockfiles, package contracts and build tooling are unchanged. The new
projection can disable already-refused actions; it cannot admit backend writes.
Independent review must confirm this boundary before reduced final qualification.

## Executed focused evidence

Private evidence root in R: `.local/workbench-alignment-20261023-worker/`.
Fixture setup uses isolated API/file delivery with blank provider credentials;
it is not a claimed creator setup operation or provider generation.

- First whole-file operations run: **8 passed**. `first-slice/` retains the first
  native short-desktop Pro screenshot. Accepted-source `createScriptProject(...,
  {}, [])` readback proves current admission, null persisted draft and matching
  initial payload. Explicit Save precedes presentation checks. Ordinary wheel,
  Ctrl-wheel pinch emulation, background pan, Enter selection/details and actual
  Creator→Pro retention passed with exact graph/stage readbacks and zero author
  writes. Ctrl-wheel is Chromium emulation, not physical Mac-trackpad acceptance.
- Focused existing graph contract checks: **76 passed in 7 files**. Added
  alignment plus Creator presentation checks: **36 passed in 2 files**. Type
  checks passed during development. These precede the final unfiltered unit run.
- First integrated browser run: **17 passed / 2 failed**, retained unchanged in
  `first-integrated-failures/`. One existing resize fixture measured coordinates
  during focus-induced document movement (trace pointer y=172, divider y=310).
  It now waits for stable native geometry and checks the actual hit before drag;
  the cancellation assertion remains. The new lifecycle fixture's locator used
  `zoom in` instead of actual `Zoom In`; corrected without product changes.
- Corrected selection: **19 passed**, log `second-focused-browser.log` and pixels
  in `second-focused-browser/`. Native node-position retention, A→B→A, reload
  and close/reopen were exercised, alongside exact 300-character Chinese option
  Save/readback, unchanged topology, no label intersections and keyboard reading/
  exact-edge editing across all three desktop sizes.
- Expanded checks: **16 passed / 4 failed**, `expanded-focused-browser.log` and
  `expanded-failures/`. Three viewport manifestations exposed the node-shell 3px
  scroll cause above. The new canonical Brief failure was its real form-draft
  recovery modal after reload, not missing canonical content.
- Reassessed selection: **20 passed / 1 failed**,
  `reassessed-focused-browser.log` and `reassessed-failures/`. All canonical
  pane/node/edge wheel checks, controls and non-draggable-node checks passed;
  both modes withdraw Confirm/Apply on source/production read failure and recover
  after successful reads. The remaining Brief fixture conditionally checked for
  a recovery dialog before hydration published it; its next run explicitly waits
  for and restores that existing test-owned form draft. First failures remain.
- Explicit recovery selection: **11 passed / 1 failed**, log
  `preview-recovery-focused.log`, evidence `preview-contract-failure/`. Waiting
  for recovery removed the earlier fixture race and exposed the real recovered-
  versus-canonical comparison defect described above. No further browser retry
  preceded source/DOM diagnosis and manager confirmation of that cause.
- After the canonical-baseline repair, focused Creator/alignment units pass
  **38 cases in 2 files**, including restored-target Cancel and saved visual/
  launch-dirty ownership. The native whole operations file exercises the same
  explicit recovery/unknown-read journey; its current result is retained in
  `canonical-baseline-fix-focused.log`: **12 passed**. Final candidate results
  follow below; the newly extended workbench journeys use checked-static fixtures
  for final qualification, retaining the earlier development-server evidence.

Generated build checks so far succeeded with the existing large-chunk warning.
They are development builds, not final deterministic comparison/qualification.
The test fixtures own process/root cleanup. Evidence copies preserve pixels and
traces before later runs replace `frontend/test-results`.

## Remaining qualification and limits

Freeze a stable source/static checkpoint for independent read-only review, then
run the plan's unfiltered frontend unit suite, both type checks, two deterministic
builds with sorted SHA-256 tree comparison, and native whole-file affected browser
selection including checked-static workbench cases. Direct pixel inspection is
separate from assertion success. Record final revisions/results here.

No backend/full-suite or hosted-CI pass is claimed. No GitHub Actions, workflow
changes, push, provider call, real-project mutation, restart, runtime activation
or live Safari access occurred. Root owns preservation-checked P activation.
Isolated Chromium proof is not owner usability/creative acceptance.
