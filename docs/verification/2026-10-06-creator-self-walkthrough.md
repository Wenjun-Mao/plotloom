# Creator coverage audit and self-walkthrough

Date: 2026-10-06. Status: local software gates and independent review passed;
owner walkthrough and real creative/media acceptance remain separate.

## Publication and next walkthrough

Runtime repairs are pushed at `02fcc306763c2015911189d570c00dcf33ac1477`;
final test-contract corrections at `a7922931f90f43775386b27661b0f510d97586c3`.
Normal8841 serves the qualified JS/CSS below; the backend still runs unchanged
from `c8f59b7`. Final test/doc changes do not alter those runtime bytes.

The [new unfiltered CI](https://github.com/Wenjun-Mao/plotloom/actions/runs/37561866807)
is running against exact head `a792293`, with `browser_grep=.*`. It is not yet a
remote pass. The earlier `02fcc30` run37560739179 was explicitly cancelled as
superseded after the two remote-trace test-contract corrections, not counted
as successful qualification. Older G5 run37495692517 remains red as recorded below.

The owner can start from the
[clean disposable nine-node demo](http://127.0.0.1:8841/v2/?project=8204819e-da63-46b7-b2ca-0ce64f6e1ef0&stage=creator).
Use a desktop browser window at least **1280px wide**. Owner acceptance is still
pending; remaining coverage boundaries are explicit in the ledger and closing note.

## Scope and evidence boundaries

Expanded the permanent [acceptance checklist](../creative-workflow/graph-workbench-acceptance.md),
not a competing checklist. C01–C47/P01–P06 remain active; C48–C55 add the current
node-role, join/effect, recovery, navigation, consent, entry and help controls.
Every future workbench tuning pass must use the checklist and record its actual
subcase coverage. Missing hands-on evidence cannot be inferred from test counts.

Started from clean `main` at `8e29c8a050fb82f9142fbe20f0d20c32db795afe`.
Only this task's two clearly named demos were edited on normal 8841:

- `8204819e-da63-46b7-b2ca-0ce64f6e1ef0`: **QA 图覆盖 2026-10-06 · 自用可删除**,
  created from blank Brief through the UI, not an API-established entry fixture.
- `a2bef822-9069-4d47-b966-aae6f2a9160f`: **QA 覆盖演练 2026-10-06 · 自用可删除**,
  saved from the UI sample entry, used for source-less canonical read-only and
  A–B–A navigation checks.

No writes to Rain/Wind, their source/outline/media, provider settings or credentials.
No live provider dispatch. The ordinary backend was not restarted or changed.
Early headed Chromium work used Vite 8844 proxying the normal API; final smoke
and the original cycle refusal were repeated through the checked 8841 bundle.
Private selection/geometry preferences are origin-scoped: 8844 preferences do
not imply identical 8841 selection. Same-origin reload preservation was verified.

Evidence codes below: **L** = this pass's headed live UI clicks, typing, pointer
dragging, scroll and keyboard with exact readback; **E** = current isolated real
browser/API tests with explicit fixtures/fake transports; **U** = current unit
or Python contract checks; **V** = directly inspected screenshots; **R** =
independent read-only review. API/file-created E initial states do not count as
their creation/generation/approval steps having been exercised through the UI.
An E or U-only subcase is **NOT EXERCISED live**, not waived.

## Root causes repaired and rechecked

1. **Hidden asynchronous refusal:** cycle validation failed correctly, but the
   edit dialog closed before the awaited result and the error was above a long
   graph. Preview preparation now returns actual admission success; refusal
   retains dialog/values/local alert. Cancel/Escape cannot dismiss pending work.
   Rechecked cycle, capacity and direct node-role refusal without mutation.
2. **Inspector error ownership:** direct controls showed refusal off-screen.
   Their alert now stays in the bounded inspector header. Modal operations keep
   their own alert. The visible error is not mistaken for successful admission.
3. **Selection restoration:** add/remove join used a receipt's old selection,
   jumping away from 333. Ordinary commands preserve the selected surviving
   node; creation/reuse keep intentional selection and removal uses safe fallback.
   Replayed exact add/remove join and Undo, plus deferred-selection unit tests.
4. **Project/session lifetime:** a flush begun in A could dispatch a command
   after switching to B. The common acknowledgement boundary now checks its
   owner after flush; disable/unmount invalidate it. Unique busy tokens prevent
   an old completion unlocking a newer session. Held-flush/request and
   disable/re-enable/unmount regressions pass; live A–B–A keeps the exact map.
5. **Native controls:** edit/discard dialogs missed current surface styling;
   checkbox inherited 40px text-input geometry. Dialog surfaces now share the
   presentation contract, checkbox/radio use explicit 16px geometry. Rechecked
   actual pixels, checked/unchecked footage readback and both OS colour preferences.

Decisions and rejected workarounds are recorded in
[ADR 0121](../adr/0121-current-source-graph-authoring.md) and
[ADR 0122](../adr/0122-creator-workspace-presentation.md). No compatibility
writer, schema adapter, stale-receipt tolerance or second graph was added.
An obsolete development-guide compatibility-endpoint claim was removed.

## Diagnostic failures, not qualification

- First full browser run: **190 passed / 1 failed**, exit1, 5.9m. New detail-control
  test reloaded during a second save. Trace adjudication: unfinished-buffer PUT
  acknowledged revision11 at71835ms; PUT(expected11) began71854ms; reload71868ms
  aborted its browser response while the server committed12. Retained input then
  retried11 and correctly received409. Its conflict modal intercepted the next
  Save. A buffer-presence poll was not final-save acknowledgement. The test now
  waits for the Save owner's readiness before reload; it does not dismiss the
  protection modal, force-click, extend timeout or silently retry. The independent
  reviewer reconstructed these exact events; this note retains the adjudication
  after Playwright replaced the first run's transient results directory.
- First wheel smoke: exit1, packaged JS missing because the wheel was built while
  the frontend output directory was being replaced. No packaging fallback was
  added. Sequential final build → wheel → isolated smoke passes. The failed wheel
  remains `/tmp/plotloom-walkthrough-wheel-20261006/`; it is not a release candidate.
- Harness-only expectations were corrected after readback: post-Close creates a
  fresh unsaved workspace (not absence of all Creator headings); injected503
  retained a generic HTTP failure rather than the fixture's unsupported error
  object text. Neither was treated as a product fix or hidden with forced clicks.
- Late inspection of the earlier [G5 remote run](https://github.com/Wenjun-Mao/plotloom/actions/runs/37495692517)
  (`c8f59b7`) found a failed required-mark assertion and one retried Close test.
  The required-mark check compared an inline text box with the enclosing label's
  line-box top (`3px` on Linux versus a strict `<3px` assertion). Current markup
  and trace use an inline baseline. The replacement checks that baseline, inline
  display, same-line containment and placement after the text; runtime CSS and
  the adjacent-control alignment assertion are unchanged.
  Close trace proves both final draft PUT and Close returned200; Close returned
  `closed`, revision2. Directory GET started1308153.136ms and never settled while
  the final route was removed1308152.475–1308169.373ms. Chromium's global Fetch
  interception teardown is a strongly supported cause, not a conclusive CDP
  reconstruction. Successful cases now await the refreshed closed row and
  enabled Open before removing interception; failed Close awaits rendered
  refusal and enabled editor. Persistence assertions/deadlines stay unchanged.
  These test-only corrections are recorded in [ADR0081](../adr/0081-narrow-source-static-and-api-lint-checks.md).
  Diagnostic downloads remain `/tmp/plotloom-cast-ci-diagnostic.9FayL5` and
  `/tmp/plotloom-close-ci-audit.ZBYuYY`; the older red result is not relabelled green.
  The first focused Close rerun had7pass/1fail: its new refusal assertion expected
  the fixture's FastAPI-style `detail` text, while the current client accepts
  top-level `message` and correctly rendered its generic503 failure. The check
  now asserts that actual rendered503; no parser adapter or product change was added.

## Current checklist evidence ledger

All listed software assertions passed on this candidate. Scope codes preserve
which states were hands-on, simulated/fixture-established or contract-only.
Within a broad row, evidence does not promote unvisited adjacent states to L.

| Item | Expected and observed result / current evidence |
|---|---|
| C01 | L/E: normal checked JS/CSS match disk hashes; no page/resource error; build/wheel pass. Known warnings below. |
| C02 | L: blank Brief → Source → editable seed; sample source-less canonical explicitly read-only; clean opening matches inspector. E: admission requires current source. |
| C03 | L/E/V: top/middle/bottom inspector centre alignment or viewport clamp at all three desktop sizes. |
| C04 | L/E/V: document scroll reaches long graph; inspector body scroll and footer remain reachable. |
| C05 | L: row-added third/fourth/sixth siblings have equal y; E/V: 24-node long graph, no wrapping, horizontal pan. |
| C06 | L/E/V: insertion, reconnect, delete/Undo, skip and converging edges retain direction and do not cross cards. |
| C07 | L/E/V: Chinese/special characters/blank placeholders/selected cards; E/V both OS preferences keep readable dark theme. |
| C08 | L: keyboard divider, separate Escape/Tab cancellation, help focus; E: row-add Enter/preview Escape and Shot Enter handoff. |
| C09 | L/E: one + per actual row; 123/222 additions do not insert another row. |
| C10 | L/E/U: shared parent defaults correctly; mixed/detached row requires explicit parent. |
| C11 | L/E/U: shared merge default commits the shown output; changed/pending/no-shared targets remain explicit. |
| C12 | L: illegal ending/decision conversion refuses and preserves content; E/U: fresh decision scaffold, ending no-output and capacity. |
| C13 | E/U: detached reuse retains identity/body/type/outputs; duplicate output refuses. NOT EXERCISED live. |
| C14 | L/E/U: exact-edge insertion retains option identity/prose/effects and original downstream target. |
| C15 | L/E/V: preview describes actual nodes and edge option; arrows and real-node counts remain accurate. |
| C16 | L/E/V: literal Chinese, spaces and HTML characters save without topology changes; E confirms no HTML execution. |
| C17 | L: edit Cancel and preview Cancel/Escape unchanged; E/U: exact one transaction and stale preview refusal. |
| C18 | L/E/V: independent click and actual pointer connection dragging; displaced target/downstream retained. |
| C19 | L: cycle, protected opening input and out-degree refusal unchanged; E/U: self-link/ending/merge safety and legal skip links. |
| C20 | L/E: 222 and 333 independently choose an exact incoming output; parents are not restricted to nearest visual row. |
| C21 | L/E/U: previous input remains pending with original identity/prose; other edges unaffected. |
| C22 | L: seventh option refused at current Brief max6; E/U: identical retarget refused and unique identities preserved. |
| C23 | L: scene/pending-edge deletion and opening protection; E/V: decision/join/ending/detached deletion, retained installed records. |
| C24 | L/E/U: safe bypass and only-delete separately preview/commit; no cascade; old input becomes pending. |
| C25 | L: safe bypass of333; E/U: unique no-effect rule and ambiguous merge/decision refusal. |
| C26 | L/E/U: Cancel/Undo restore exact map; surviving current selection/fallback and late selection regressions pass. |
| C27 | L: node summary survives Story/Production/Pro/Creator; E: scoped script dirty ownership across selection/modes/reload/save. |
| C28 | L/E: both modes read the same Root; Pro position-only drag moves geometry without topology writes. |
| C29 | L: all five structural hover/focus explanations inspected; E/U: current shot/target settings and preview. |
| C30 | L: node budget30→31 explicitly previewed, Cancel unchanged, Confirm marks stale; E/U: range/integer/shot rules and frozen-proposal refusal. |
| C31 | L/E/U: incomplete/target-mismatch states distinct; target change never reshapes graph; confirmation gates remain strict. |
| C32 | L: unfinished saves and atomic capacity refusal; E/U: no-worse safety and current128-node/6-option contracts. |
| C33 | L/E/U: repeated Undo restores exact structure/prose/metadata; newer authored input prevents lossy Undo. |
| C34 | L: stale recovery and local refusal; injected discard503 retains dialog/map. E/U: unknown outcomes and save conflict fail closed. |
| C35 | L: acknowledged draft survives reload/Close/Open without confirmation; E/U: failed-save retained input. |
| C36 | E/U: held ACK, fast selections, double/stale submission and switched/unmounted owners; L: A–B–A. |
| C37 | R: GPT‑6.1 Sol/Medium read-only code/contract and21-pixel-view review, no blockers; acceptance not inferred. |
| C38 | L: fresh reset then UI-authored9-node/9-edge demo, opening/Story, ACK23, base0, no accepted map or runs; E: independent clean checked-bundle fixture. |
| C39 | L/R: exact baseline/static/wheel identities retained; no owner reset/data upgrade; only named QA demos mutated. |
| C40 | L: Production prerequisite gate; E/V: all repeated scene actions/dialogue and ordered production cuts at exact coordinates. |
| C41 | E/U: explicit prepare/check/cancel/report/accept/content-confirm/install remain separate. No live assistant dispatch or generation claimed. |
| C42 | L: Brief change preserves draft with stale/recovery; E/U: prose/footage/script/board drift pauses old handoff, retains media. |
| C43 | E/V/U: exact Shot owner, approval/keyframe/video/select/play commands with fake transport. NOT EXERCISED with real media/providers. |
| C44 | L/E: explicit checkbox opt-in/out saves footage mode; route-only controls expose no invented production footage. |
| C45 | L/E/V/R: natural graph height, side inspector near85% visible space; no500px cap or inner vertical chart scroll. |
| C46 | L/E/V: actual divider drag/keyboard/Home/Shift-arrow/double-click; separate Escape/Tab cancel; E: clamp/persistence and delivered-blur regression. Actual OS blur NOT EXERCISED. |
| C47 | L/E/V/R: visible/documented1280px minimum; only1280×768,1280×460,1700×900 qualification. No phone/1024 authoring tests. |
| C48 | L/E/U: compatible/illegal roles, new start+Undo, protected start; actual Pro geometry drag does not alter story. |
| C49 | L/E/U: add/remove join stays selected; required keys, differences, reconciliation/notes save; generic unfinished-buffer retention checked separately. |
| C50 | L/E/U: target clear+Undo, input replacement, pending-edge delete; option/fact/entity effects and incomplete JSON save/reload/complete exactly. All endpoint safety variations additionally contract-tested. |
| C51 | L: discard Cancel unchanged; injected503 keeps map/dialog, retry resets only QA draft; actual Brief-stale recovery preserves authored map. |
| C52 | L: Story/Production/Creator/Pro/Brief/Close/Open/A–B–A ownership; E: Source/readers/history/currentness. |
| C53 | L/E/U: edit and preview Cancel separately, immutable preview, local refusal/values and exact confirmation; late/double/stale coverage. |
| C54 | L: visible source/cast/art/settings entrances and missing production prerequisites; E/V: accepted/candidate reports, script/whole package, Shot/read/play owners. Source/media initial fixture establishment is not L. |
| C55 | L: all five structure help hover and keyboard focus match meaning; E/U: remaining setting/help/focus contracts. |
| P01 | L/E: Brief remains reachable; explicit target save preserves old content and requires review. |
| P02 | L/E/U: current Brief capacity; frozen task context/multi-option suggestion and infeasible targets refuse without parameter edits. |
| P03 | E: automatic check0send0accept, completion/failure/cancel/leave/reopen and polling ownership. NOT EXERCISED against a live assistant. |
| P04 | E/V: reports/reopen/save/cancel/confirm/apply preserve accepted content, not a regenerate-only shortcut. NOT EXERCISED with a live generated outline. |
| P05 | E/U: suggestion enters shared draft; explicit confirm/apply required, no planner-equality bypass. NOT EXERCISED with a live generated suggestion. |
| P06 | L/E/V/U: selected node, occurrences, exact shots/read/play match owners; diagnostic technical details are not creative acceptance. |

E uses `creator-workbench-{operations,layout,delivery,text,story,production,cancellation}.spec.ts`,
current Source/branch/settings/currentness/close/navigation and production/media
journeys. U uses provider/dialog/geometry tests and current graph command/API/
production validators. All ran in the final unfiltered suites. The expanded
controls test separately exercises role refusal, selection-safe join fields,
unfinished/complete JSON and checkbox opt-in/out.

## Direct visual review and retained artifacts

Permanent captures: [supporting directory](supporting/graph-workbench-walkthrough-20261006/).
They contain ten live captures (preview, four/six siblings, original unstyled
in-place refusal, styled refusal, capacity, discard failure, clean8841 and final
8841 cycle), plus21 current fixture viewport images independently inspected:
top/middle/bottom/six-sibling views and light/dark Production/Shot-owner views
at each supported size. `screenshots.json` binds each image to its source/hash.
Main separately inspected live and fixture states; full-page Story is supplemental
content evidence, not sticky geometry proof. Side inspector stays beside graph,
short-window footer remains visible, labels/arrows avoid cards, and siblings pan
rather than wrap. No blocking visual finding was reported.

## Executed gates and current identity

- Python: **1182 passed**, exit0, 398.43s.
- Frontend: **546 passed /77 files**, exit0; app/E2E types pass.
- Final full unfiltered browser rerun after both remote-trace test repairs:
  **191 passed**, exit0, 5.9m. Earlier runtime qualification also passed191/5.5m.
- Focused provider/dialog17 and operations5 passed before full qualification.
- Focused required-mark/cast session1 and Close8 passed after remote-trace
  diagnosis. Final full-browser qualification was rerun after these test-only
  corrections, which do not change the qualified runtime bytes.
- Lock, configured API F401 lint, archived prompt-reader verify and compileall pass.
- Deterministic build passes; final rebuild yields identical JS/CSS hashes.
- Sequential fresh wheel/isolated installed smoke pass. Wheel retained at
  `/tmp/plotloom-walkthrough-wheel.Sg90kS/plotloom-0.1.0-py3-none-any.whl`.
- Independent code/contract and direct21-image review: no unresolved blocker.

Normal8841 returned200 and matched the checked files exactly:

| Artifact | SHA-256 |
|---|---|
| `workbench.js` | `0038474b6d0148b6d29ff4d350a7461e13f5e1e57db2e413ad5c56ac2fe86ac8` |
| `workbench2.css` | `c36e30d7fdcc5e1f0b349d3fbb71dd459b0ece7201523d65125484dfa9278fcb` |
| wheel | `28caa8862cbcc0c17f6078c66b8f9aa4b01a7a5e6b9b375f5a18162f1841f086` |

Existing nonblocking warnings: Starlette/httpx deprecation, Node colour-env warning,
Vite large bundle warning and the existing SettingsDialog number-key warning.
No new unexplained browser resource or page error.

Final normal QA map:9 nodes/9 edges, draft23, canonical base0, opening selected,
Story active, no open modal/structure check, no pending unsent Root record,
accepted section map null and runs0. The prior16-node exercise was explicitly
discarded only in this QA project; it can no longer be Undo-restored there.
Owner projects were not reset. The other named QA sample is intentionally read-only.

Remaining acceptance limits: no blanket claim of every subcase manually replayed
on normal8841; E/U-only states are marked above. Real provider/creative/video
quality, actual OS-delivered focus loss and owner intuition remain unverified.
These limits do not authorize weakening software gates or resetting owner work.
The task-owned 8844 development server and headed QA browser were stopped after
readback; the healthy normal8841 service remains online for the owner's walkthrough.
