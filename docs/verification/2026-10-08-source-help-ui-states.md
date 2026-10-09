# Source and structural-help UI audit — 2026-10-08

Status: **PUBLISHED / REMOTE CI PASSED**. This E22 checkpoint extends
the [whole-product visual/text audit](2026-10-08-whole-product-ui-audit.md).
It is not completion of Create → Revise → Recover or native-media acceptance.

## Root causes and repairs

- Source's first failed read displayed an error and a generic “正在处理” spinner.
  Missing `state` was treated as a request in progress, even after the request
  failed. Spinner visibility now follows the actual checking phase and names
  the read. Retained content still does not imply verified authority.
- An archived Source view invited the author to prepare/send an Outline despite
  disabled controls. The StageGuide now follows owner read-only admission after
  failed/checking precedence. It says “项目当前只读，可查看已有内容；不能修改来源或
  准备、发送新任务。” It does not infer archive from the generic read-only flag,
  which also covers Close/snapshot admission. No handlers or eligibility changed.
- Root pixel inspection of171 found the short desktop's help icon partly under
  the sticky toolbar. Centre hit testing did not establish a fully visible control.
  The setting group plus shared dock footprint exceeded available hover-reading
  height. Structural settings now use the established compact grid, and the
  adjacent dock uses the same8px separation. The dock remains normal-flow with
  reserved100px height; no floating overlay or short-height-only special case.
  Tests require the entire28px desktop control and explanation inside the
  viewport below the measured toolbar. Hover is not waived by focus or pinning.

These are reading/composition repairs under
[ADR0132](../adr/0132-creator-ui-reading-boundaries.md), not generation, schema,
confirmation or dispatch changes. Frozen source/settings and creative prose are
not rewritten for cosmetic consistency.

## Executed evidence and exclusions

Artifacts: `output/playwright/full-lifecycle-2026-10-07/`.

- 168: six new Source cases failed because the fault fixture used `detail`, while
  the actual transport reads `message`. Correct the fixture, not production
  transport. Root inspected the genuine failed-read/generic-spinner pixels.
- 169: six Source cases pass; help failed its fixed-position full-tip criterion.
  Ordinary scrolling must target the setting/explanation rather than require
  every setting plus help at a single fixed offset. Initial TypeScript failure
  from a nonexistent bounding-box `right` property was not a browser execution.
- 170/171: seven cases pass. Independent source review found no contract defect;
  the pixel reviewer inspected all84 final171 PNGs. However, root subsequently
  found the first short help trigger clipped. Those centre-only captures do not
  qualify full-control visibility; the discrepancy is retained, not called PASS.
- 172 repeated the unchanged help test because a patch used an incorrect working
  path and did not apply; its PASS is not tightened-criterion qualification.
- 173: the tightened text-bound diagnostic failed at55.515625px vs toolbar58px.
  Range bounds are font layout bounds, not exact ink; the durable gate uses the
  stronger full button rectangle, with direct pixels as well.
- 174: compact settings restored first control space, but fractional `scrollBy`
  left tooltip bottom460.28125px. Capture rounds measured overflow up, retaining
  exact viewport bounds and no numeric tolerance.
- 175: first short explanation passes; second control would start55.4375px under
  toolbar58px. Reassessment identifies remaining12px dock gap beside the8px
  compact grid. Use consistent compact separation rather than repeat the broad
  assignment or weaken hover/full-control requirements.
- 176: final focused candidate passes all7 cases21.9s. Root directly inspected
  short hover0/hover1/focus0, wide hover2 and archived Source top. The full controls
  and explanations are genuinely visible. Independent GPT-6 Luna/Max directly
  inspected all84 current176 PNGs, with no remaining concrete visual/copy finding.

Source cases use isolated disposable real FastAPI/file-SQLite projects. Only GET
reads are held/faulted; initial successful reads and explicit retry are real.
Dirty text is retained exactly through pending/failure/retry, mutation controls
stay disabled until reverification, and canonical/project source objects remain
identical. Archive uses a separate QA project, not a shortcut around dirty Close.
All those browser reads/retries send zero API writes. Setup source confirmation
and archive are explicit API fixture construction, not native generation evidence.

The final packet has36 Source viewport PNGs: initial pending/failed/empty top and
prerequisite, dirty pending/failed/reverified status and separate editor frames,
then archived top/prerequisite, at1700×900,1280×768,1280×460. Help adds45 viewport
frames: five explanations ×pure hover/focus/Escape ×three sizes. Three full-page
help frames supplement hierarchy, not viewport reachability. Pin retention,
adjacent-field editing and Escape remain separately exercised.

Prepared/sent/waiting task states, stale Outline, other Creator/Pro permutations,
immutable original Outline's fractional-minute rendering, native media/all-route
acceptance and post-install revision/rebuild remain outside this checkpoint.

## Qualification

Final source/test review GPT-6.1 Sol/Medium is clean. Complete frontend713/96files,
application/E2E types, deterministic build, lock/API F401, archived prompt reader
and diff checks pass. Build chunk/color-env warnings remain visible. Python1245
qualification is reused from unchanged backend source/tests, not newly executed.
Final installed-wheel smoke passes for `/private/tmp/plotloom-source-help-wheel.ShmpjD/`,
SHA256 `9c50bb9c794067aae5f16367599efa1abc2dfd33f5d413d7b89066bb1551a791`.

Unfiltered177 passes all230 browser tests6.5m on875 frozen source/test/config/static
inputs. Before/after SHA256 is identical:
`7cc3dec21a00f72f29537f7776d0606fad90793723f0c5fd325dfeda3561e715`.
Default4 workers/zero local retries remain unchanged. Final pixel inspection and
local gates are complete.

Owner/protected-setting readback is exact before and after qualification:
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`
(Wind17/Rain67 managed files and three protected settings). No native dispatch or
owner-project mutation; prior browser gates cannot qualify this changed candidate.

Normal 8841 returns HTTP 200 and serves the qualified checkout assets byte-for-byte:

- `workbench.js`: `5eb01d798c50a907ff4aec544c1018f6e25bcd7872364a7673ab7ffe7165e00a`.
- `workbench.css`: `000aac5623f5ce4cf63f007979f7e7d1e09f9aa3698a1da3556fe400dbec3b7c`.
- Unchanged `workbench2.css`: `42beb639a4681beb6bea3a3b04916ee1eb63481a821eb42994f152de7e2d6850`.

No backend source, service restart or credential/settings write is required.

Executable `210c33c604055916d35251ed8af1a5318251910d` is pushed to `origin/main`.
The full unfiltered [CI37773930608](https://github.com/Wenjun-Mao/plotloom/actions/runs/37773930608)
has completed success at that exact head: verify and both browser shards passed.
Commit-ref dispatch requests were explicitly refused
with HTTP 422 and created no runs. A fresh remote-main read established the same
SHA; one branch-ref dispatch then returned the matching run. No duplicate run was
created. This remote result qualifies only that published Source/help candidate.

## October9 continuation — Outline task presentation (isolated, not published)

On the one-current-story candidate based on `38f55b8`, the full unfiltered browser
suite finished **248 PASS in7.8m** before this copy delta. That result qualifies
the settings/recovery candidate, not the subsequently changed Source wording.

The actual8865 browser created disposable project
`fadc29a3-6a9b-4da3-b50e-cc51dd5c03a1` (QA E22 来源任务状态 · 可删除), saved its Brief,
confirmed source r1 and prepared Outline `ch_b6dcce69b1a04c9c868870c228d90321`.
No generation was sent. Its header said “等待助手交付” while the durable task
read “任务已准备，尚未发送”. The candidate's prepared lifecycle was incorrectly
presented as evidence of dispatch. The header now says “任务尚未交付”; the shared
task component remains the owner of prepared/queued/uncertain dispatch wording.
The same component's initial read catch used `String(error)`, exposing `Error:`
to the creator. It now presents the error message, with a Chinese fallback for
non-Error failures. No API, dispatch, retry, acceptance or cancellation rules changed.

The before/after browser pass overrode only the exact task status GET to show
prepared, queued, outcome_unknown and409 read failure. All API writes were guarded;
none were attempted during either pass. A queued automatic check would have been
intercepted too. The real task JSON was identical before/after, still prepared.
The named failed-read retry recovered through GET only. These are controlled
presentation states, **not native queued execution or delivery proof**.

Root inspected all16 final viewport images in
`output/playwright/native-intent-2026-10-08/source-status-final-{prepared,queued,outcome_unknown,failed}-{1700x900,1280x768,1280x460,1280x460-end}.png`
under the canonical repository. Short-height top and scrolled-end captures jointly
show the full candidate, error, controls and guidance. Earlier `source-task-prepared-*`
captures put the header under the sticky toolbar; they are superseded by these
properly positioned captures, not used as complete-header evidence.

After removing the overrides, real UI cancellation made exactly one POST to that
candidate's `/cancel`; source JSON was unchanged and status became cancelled.
All3 `source-status-final-cancelled-{size}.png` were directly inspected. The visible
reprepare action does not imply another task was prepared. Project and task records
are retained for evidence; no data or media was deleted.

Four regression assertions failed before repair. After repair,14 focused tests,
types, E2E types, deterministic build, diff check and9 focused real-server Source
browser tests passed (23.2s). The first typecheck caught a missing `readOnly` prop
in the new test setup; corrected without changing product behavior or assertions.
The retained independent reviewer inspected the source/test delta and all19 final
captures and found no material issue. Review is scoped to this delta, with no
additional tests run by the reviewer. Normal8841 is unchanged.
At that checkpoint stale accepted Outline, broader Creator/Pro permutations,
revised media/routes and the remaining whole-product audit were still open.

### October9 — retained Outline after source revision

On candidate `551fbd4`, a fresh real-server browser fixture accepted an Outline,
saved/applied its branch map and restarted the backend. Opening a revision without
changing source correctly allowed returning to the retained Outline. Saving source
r2 then disabled that return, retained the exact accepted Outline/map and marked
graph admission stale, but the stage guide still offered a valid old-version return.
The SectionMap save hint repeated that unavailable option; its warning exposed
raw English stale reasons as the main guidance.

Both operations share `outlineStatus=reopened`; their source revision binding
distinguishes return eligibility. The presentation now uses that binding, matching
the existing backend/button guard. Ready/prepared candidates take guidance priority
over the revision-open message. Branch warnings give actionable Chinese guidance
and retain original reasons under technical details. No backend contract, safety
gate, report bytes or accepted content was changed; this is not a compatibility layer.

Regression evidence: an initial run failed on a test locator that incorrectly used
an exact label despite the required marker; its corrected run reproduced the actual
wrong guide after all retention assertions passed. Both failure artifacts remain in
`frontend/test-results/stale-outline-before` and `stale-outline-reproduction`.
The final expanded journey passes in7.6s, including real source revision, valid
return, stale refusal, report reopen, new task frozen at r2 and cancellation without
dispatch. The report/delivery are explicit synthetic fixtures, **not native generation
or rich report-content qualification**.

The final27 screenshots (nine states × three supported desktop sizes) are retained
under canonical `output/playwright/native-intent-2026-10-08/stale-outline-final/`.
Root directly inspected the nine guide, report and bottom-action screenshots;
the retained independent reviewer directly inspected the remaining18, reviewed the
source/test/generated-bundle delta and found no material issue. The bottom controls are readable
at1280×460, report close remains visible, and stale guidance matches disabled actions.
The full frontend suite passes888 tests/109files;15 focused tests, application/E2E
types, deterministic build and diff check pass. Rebuilding produces identical
`workbench.js` Git blob `a4008c383ec30fb6cf4693229fe5fac0bccc6dc8`.
The wider Source/currentness browser suite passes23 tests in1.3m, including stale
Script/Storyboard candidates, failed refresh authority and retained dirty content.
The review reused the retained worker; its inherited model/effort was not verified.
No full unfiltered browser rerun is claimed for this newest delta;248 PASS remains
the earlier `38f55b8` baseline. Existing chunk-size/color-environment warnings remain.
No normal8841 update, native generation or owner-project mutation occurred.
