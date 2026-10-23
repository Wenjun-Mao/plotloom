# Workbench specification alignment · 2026-10-23

Status: implemented, independently reviewed and locally frontend-qualified at
clean executable revision `dd71f0794938fab607c189283d2b3cbe25e384c9`.
Root-owned activation and owner acceptance remain separate and pending at this
handoff. The approved [plan](../roadmap/2026-10-23-workbench-spec-alignment.md)
binds this receipt. Source baseline is clean retained R at `d029e536`; no work was
performed in installed P or the default Narrative-Forge checkout.

## Root causes and implemented boundaries

| Contract | Cause and repair layer |
| --- | --- |
| Editable labels | Fixed lanes had unbounded button height. Bound the full-text button to its editable 48px lane with native internal scrolling, complete accessible text and keyboard exact-edge editing. Its focus outline clears row insertion controls. No story truncation or schema change. |
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

## Stable-candidate review and bounded corrections

First reviewed source/static checkpoint: `9c07f670`. Independent read-only review
found one currentness blocker: retained Source/Outline object presence is not
proof of a current accepted outline. Root also directly observed the long editable
label's lower-right corner overlapping the row insertion chip in all three pixels.
Original candidate/observations remain retained, not retroactively passed.

- Share the existing accepted-current predicate between the workflow guide and
  action projection: status must be `accepted`, with the accepted outline's
  source revision matching current Source. Both modes disable Confirm/Apply for
  reopened or mismatched retained content while preserving ordinary draft Save.
  Unit regressions cover both states; supported isolated API setup and recovery
  prepare current complete drafts so stale-draft refusal cannot mask the check.
- Editable labels share a row gap with insertion controls; canonical labels do
  not. The earlier 80px cap ended 10px into the insertion lane. Use a named 48px
  editable cap, accounting for the 3px outline plus 2px offset, without moving
  topology or truncating content. Native checks now include focused-label versus
  insertion/add controls and actual insertion hit/cancel at all three desktops.
- Successful body-only attachments did not survive the list reporter. Write
  structured JSON into the existing `testInfo.outputPath`, then attach that path.
  Preserve fixture IDs, current receipts/readbacks, zero-write arrays, source
  revision/working-tree status and static hashes alongside PNGs before replacing
  test outputs. This is test-artifact retention, not new runtime machinery.

Focused review-fix units: **94 passed in 3 files** (alignment, layout and existing
workflow-guide owner). E2E type check and refreshed deterministic build pass.
The whole affected browser selection is `review-fixes-focused-browser.log`.
That invocation retained **20 passed / 2 failed** in `review-fix-first-failures/`:
the built-static lifecycle test compared incidental whole inline style and caught
React Flow's temporary `visibility:hidden` despite an identical retained node
transform; it now asserts exact position plus visible state at each checkpoint.
Source replacement also sets `outlineStatus=reopened`, so reason projection must
prioritize the mismatched source revision. Both controls were already disabled;
the revision mismatch now has the specific accurate explanation.

After those causal corrections, **14 focused units and all 13 operations browser
cases pass**, including checked-static review-fix journeys. See
`review-fixes-corrected-focused.log` and `review-fixes-corrected/` for preserved
JSON/readbacks and pixels. Direct inspection of all three new 48px-label desktop
screens confirms the focus outline clears insertion text and target cards. Final
selection also strengthens Enter and Space checks to change away from the opening
node, rather than merely reselect it; that final case passes below.

## Final local frontend qualification

Independent focused re-review closed both findings with no remaining blocker.
Root separately reviewed the installed `21c6d6be` → candidate `dd71f079` actual
diff and confirmed the frontend-only boundary above. One worker owned execution;
root/reviewer did not duplicate software qualification. Inputs stayed clean and
unchanged throughout these final runs.

| Check | Result / retained log |
| --- | --- |
| `npm --prefix frontend test` | **1,490 passed in 169 files**, unfiltered; `final-unit.log` |
| `npm --prefix frontend run typecheck` | PASS; `final-typecheck.log` |
| `npm --prefix frontend run typecheck:e2e` | PASS; `final-typecheck-e2e.log` |
| Two `build:deterministic` runs | PASS; `final-build-first.log`, `final-build-second.log` |
| Sorted full static SHA-256 tree comparison | All **7 files identical**; `final-static-first.sha256`, `final-static-second.sha256` |
| Native whole-file browser selection | **46 passed**, 65.509s; `final-browser-seven-files.log` |

Browser selectors are exactly `creator-workbench-layout`,
`creator-workbench-operations`, `graph-interactions`, `graph-read-recovery`,
`project-folder-close`, `recommended-workflow-guide` and `shipped-static`, each
as its whole `e2e/*.spec.ts` file through `verify.py focused`, without test-name or
line filters. Affected new workbench journeys and canonical layout cases exercise
the fresh checked-static assets; retained development-server evidence is separate.

Both static manifests have SHA-256
`7e23c2ddd53318954dc469eb802f899bb46fea3b16367dfc505396eb6b02a8c9`.
Key qualified assets:

- `workbench.js`: `ea3a782af33f69ab7f04bcb287e2fd3f5f0a4ba690f151c2cd551cda1f7ba53c`
- `workbench2.css`: `624e3c8ffa554f49d06ad64877a862918fd1be78aff3fd79f40ddd2ee4b6f880`

`final-browser/` preserves the complete final test outputs. Its 13 top-level
structured evidence files all name clean `dd71f079` and the matching static hashes.
Eleven explicitly scoped presentation/read-refusal segments record empty write
arrays and complete graph readbacks; relevant canonical stage readbacks are
retained with the navigation/recovery evidence. The long-label journey intentionally
saves author text; Brief Cancel may retain ordinary form-draft autosave. Neither
is described as zero writes across its whole journey. Fixture setup is API/file
delivery and supported recovery, not a claimed creator setup action.

| Scoped outcome | Fresh evidence |
| --- | --- |
| C06/C07/C15 labels | Exact 300-character Chinese option after UI Save/readback; unchanged topology; label/card/label/control bounds, focused reading and exact-edge editing; native insertion hit/Cancel at all three desktops. `editable-label-readback.json` and `editable-long-label-*.png`. |
| C02/C07/C08/C28 selection | Native Enter and Space each change to a non-opening node and update shared details; actual mode switches retain selection. Existing pointer, Undo, dirty-buffer and late-ACK unit/browser regressions pass. `pro-fixture-readback.json`, first-slice and operations pixels. |
| C29/C30 counts | Shared draft and canonical counting, named snapshot basis, explicit failed/stale reads, recovered-versus-canonical before targets and Cancel preserving formal Brief/graph. `canonical-preview-readback.json`, canonical preview pixel and focused unit contracts. |
| ADR 0155 global actions | Missing prerequisites, incomplete/mismatch, current graph, source/production read failures, reopened outlines and source-revision mismatch share status/availability in both views; Save remains independent. `action-read-uncertainty.json`, both `noncurrent-*.json` and action-help pixels. |
| C56 Pro navigation | Both authority states: native wheel over pane/node/edge moves the document without transform change; working zoom/fit, Ctrl-wheel pinch emulation and background pan; canonical nodes do not drag. Canonical full readbacks/writes and Pro slice JSON remain unchanged. |
| C57 Pro lifetime | Native editable node movement and viewport survive actual mode switches; A→B→A, reload and close/reopen reset visuals. Canonical Pro mode retention/reload and common session/late-callback isolation are covered. Shared selection/content/Creator geometry owners remain intact. `pro-position-readback.json` plus existing layout/recovery tests. |

Direct final pixel inspection covered the three `editable-long-label-*.png`,
three desktop `expanded-guide-inspector.png`, canonical short-desktop view,
1280×768 canonical controls/reload and join/skip pan/pinch views, Pro selection/
position context, and canonical Brief preview. The editable focus outline clears
insertion text and target cards. Expanded sticky guidance leaves the inspector
header reachable with its body internally scrollable; the accepted height formula
and cancellation checks pass. Pro position-context pixels do not alone establish
simultaneous inspector visibility; the final short-desktop slice also shows the
selected ending and matching chapter field with reachable controls.

Existing nonfailing jsdom `window.scrollBy` notices from unchanged completion/
media-navigation tests and the existing large-bundle build warning remain in logs.
Isolated fixture teardown completed, settling its child processes and removing
only test-owned temporary roots. No real projects were cleaned or reset. Product
implementation/coordination time was not separately instrumented; the final
browser runner duration is reported above without invented cost/time percentages.

No backend/full-suite or hosted-CI pass is claimed. No GitHub Actions, workflow
changes, push, provider call, real-project mutation, installed-service restart,
runtime activation or live Safari access occurred. Root owns preservation-checked
P activation. Safari/physical-trackpad input and owner usability/creative acceptance
remain unperformed; Ctrl-wheel is Chromium pinch emulation. The final documentation
checkpoint changes no qualified executable/static bytes.
