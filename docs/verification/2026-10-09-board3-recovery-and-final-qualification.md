# Board3 recovery and final candidate qualification

Current continuation of the single [Create → Revise → Recover playbook](../creative-workflow/graph-workbench-acceptance.md)
and [run profile](../roadmap/2026-10-07-full-creator-e2e-repeat.md). Overall status:
**PARTIAL**, not whole-product or creative/media acceptance. This receipt closes
the bounded recovery, exploration and directory-feedback slices following the
[Board3 native-media receipt](2026-10-09-review-bound-bridge-and-board3-media.md).
Earlier results remain dated evidence, not new candidate PASS claims.

## Candidate and protected scope

- Executable `4bbf8c2`, branch `codex/one-current-story-rebuild`, worktree
  `/private/tmp/plotloom-one-story-rebuild.gfnqlc`.
- Checked and final-isolated-served JS SHA256:
  `f0c658027cb4e90ab8f3b9c60826ad55938721ba68e061db8dcd28a43cbc2d5e`.
  Matching4bbf8c2 idle reload and final preservation readback are recorded below.
- Owned native service8865/8866, same approved installation and settings.
  Final `/healthz`200; specialist busy=false/activeTasks=[] at21:48UTC.
- Normal8841 is unchanged at this checkpoint. Served JS SHA256 remains
  `3a8843193da3df6852f8b12731e33c90961dbe1339a9882b30fb2e03290555d5`.
  Both owner projects, managed assets and three protected configuration files
  match aggregate protection fingerprint
  `df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.
- Native media/lifecycle QA project `90c0f895-48de-4b57-8725-4b6f72797633`. Its source,
  accepted reviews, proposals, media and frozen job evidence are not rewritten.
  Twelve image jobs delivered, eleven H3 jobs ingested; four current selected
  clips and seven retained stale/unselected jobs. No generation for extra counts.
- Separate structural QA `fadc29a3-6a9b-4da3-b50e-cc51dd5c03a1` is used only for
  the authoring exploration and explicit changed-settings recovery below.
- Desktop matrix1280×768,1280×460,1700×900 only; no phone/1024px work.

## E21: actual source lifecycle, separate snapshot restore and restart

Native UI created snapshot `2ac66146-fd83-484b-8f51-bb20e76d420d` once,201 at
20:31:33UTC. It contains183 files including58 managed assets, projectFormat11,
snapshot format1; database SHA256
`d683ba03e8bb144797c00c4e0fb6eda5da5395c167a11e796c2909f2894ef0cd`.
Its exact retained location is:

`/Users/wjmao/projects/HU/plotloom/.local/current-story-native-2026-10-08/installation/outputs/.snapshots/90c0f895-48de-4b57-8725-4b6f72797633/20261009T203133160144Z__2ac66146-fd83-484b-8f51-bb20e76d420d`.

Operator CLI restore, not a UI restore claim: `uv run plotloom restore --source`
that exact snapshot `--outputs-dir /private/tmp/plotloom-board3-recover.ZwCCeE/outputs`
completed0. Fresh isolated8875/8876 uses the restored project and no H3. It did
not import application configuration or specialist runtime credentials.

Root sequentially read eight domain responses, freshly hashed all58 asset bytes
and compared the four selected job/request/output/segment/revision records. The
restored assets and selections match exactly. Seven non-bridge responses match.
Bridge differences concern installation-owned native-intent availability/task
state only: available/completed becomes unconfigured/prepared, with dispatch
chat identity omitted. Project intent ready state, response hash, report,
proposal and installed production remain unchanged. This is not a fresh native
delivery on the restore service.

Actual source UI also completed save-and-close/reopen, archive/restore and a final
idle service restart. Source project revision stays2; lifecycle ends9/active.
Eight domain response hashes, all58 assets and all four selections match both the
original baseline and before/after final restart at20:58:48.880UTC. No source,
outline, draft, review, selection or job mutation is inferred from lifecycle ACKs.

The last presentation-only candidate4bbf8c2 was reloaded while idle at21:48UTC,
after fresh busy=false/empty-task checks and baseline readback. Owned PID42291
shut down gracefully; new PID20399 loaded this worktree and identical launch
arguments/settings. Health and served JS match. Before/after JSON files
`recovery-{before,after}-4bbf8c2-idle-restart.json` again match all eight domain
responses,58 freshly hashed assets, four selections, revision2/lifecycle9/active.
This is actual paired-runtime preservation, not another generation or route replay.

Final read-only qualification at22:03:36UTC freshly rehashed all58 files and
compared all four selected records and eight domain responses to the paired
4bbf8c2 restart record: all equal, no different endpoint, revision2/lifecycle9/active.
Artifact `recovery-final-qualified-4bbf8c2.json` records this check. The normal
owner/protected fingerprint and both normal/isolated served JS hashes were also
freshly verified unchanged; no additional restart was needed.

Evidence root: `output/playwright/board3-r12-2026-10-09/` in this worktree:
`recovery-before.json`, `recovery-restored.json`, `recovery-after-close-open.json`,
`recovery-after-archive-restore.json`, `recovery-before-final-idle-restart.json`,
`recovery-after-final-idle-restart.json`. The read-only helper hashes bytes rather
than trusting stored asset names. Independent review verified all sixteen final
serialized response hashes and exact recorded parity; it did not rehash files.

## E17/E21: both restored native routes

Actual browser playback ran two shared opening clips → pause → East ending;
from-head restart cleared history, then two shared clips → pause → West ending.
Exactly six trusted native `ended` events, each5.000 seconds, unmuted, no media
error and zero dropped frames. No synthetic ended, time jumping or forced
controller advance. This proves restored multishot/branch operation, not image,
action, continuity or perceptual-audio quality. Each route remains15 seconds;
the four mutually exclusive entries total20 seconds.

Root inspected corrected shared-choice/East terminal/West terminal desktop pixels
and ordinary short-desktop scrolling to bottom controls. Independent review
inspected the corrected1700 choice,1700 East and1280×460 West frames. Retained
`restored-shared-choice-1700x900.png` was actually captured at1200×953: it is a
misnamed harness artifact, **not** supported-desktop qualification. Its replacement
is `restored-shared-choice-current-1700x900.png`. West terminal captures exist at
all three supported sizes; these are actual viewport captures, not stitched pages.

## Directory command feedback: diagnosis, repair and regression

An actual archive409 correctly refused concurrent root-owned API reads. Root
waited for them to finish and explicitly retried; archive200 succeeded, but the
previous busy banner remained. Concurrent reads explain admission refusal, not
the stale feedback. The owning lifecycle command never retired its prior error.

`useProjectLifecycle` now clears command feedback only when an admitted command
starts, including confirmed deletion. The close/open capability guard precedes
clearing. GET/filter reads, cancelled duplicate/delete consent and an unavailable
open command preserve feedback; no backend admission, CAS, dispatch, concurrency
or deletion rule changed. No automatic retry or downstream tolerance layer.

Before repair, all three initial new browser regressions failed on the retained
banner. Evidence `/private/tmp/plotloom-directory-error-red` remains red. The
initial repair passed15 adjacent lifecycle checks; independent review then found
capability no-op could clear feedback. Moving the guard and a fourth regression
closed that finding. Final four focused cases PASS11.7s in
`/private/tmp/plotloom-directory-error-final`:

- Archive and restore: failed command; filter GETs and cancelled confirmations
  retain error; a held explicit retry clears it before ACK and succeeds once.
- Disposable deletion: failed confirmed attempt and cancelled retry preserve
  data/feedback; confirmed retry erases only the precise disposable fixture.
- Unavailable folder-open: zero POSTs, unchanged navigation, prior error retained.

Final native presentation exercise injected one browser-only409, then allowed
actual archive200/lifecycle8 and restore200/lifecycle9. Three controlled-busy and
three retry-success viewports plus the restored short viewport were inspected by
root/reviewer. All necessary text/actions readable; no stale banner after success.
Injection proves presentation, not another genuine server busy event. The earlier
actual busy/refusal remains separately recorded. Lower directory rows use normal
modal body scrolling; screenshot absence is not a claim that those rows vanished.

## C/E22: structural stress and unscripted exploration

The stable graph slice passes nine browser cases in23 seconds: six siblings,
24 nodes/12 steps, centre/clamped tall inspector, graph pan and all three desktop
sizes; precise123→222→333 input/output changes, insertion, deletion variants,
Undo, drag, reload, node kinds, capacity/reuse and preview ownership. Root inspected
material captures and independent review all28 retained PNGs. These checks do not
turn synthetic focus events into actual OS-delivered blur.

Root also performed85.12 seconds of ad-hoc UI exploration on disposable graph
`fadc29a3-6a9b-4da3-b50e-cc51dd5c03a1`,1700×900: row-add parent/common-join
defaults, ending and decision conversion guards, precise incoming-edge options,
cancel and return to authored start. Captured requests show zero writes and
document-width overflow is absent; original title/long Chinese body remained.
The helper tried to select a disabled continuation for a fresh decision and timed
out. Inspection confirmed that fresh decisions own their pending choices; this
was a helper assumption, not a product defect or bypass. Root and reviewer directly
inspected decision-guard/mixed-input/return-to-start pixels. Exploration duration
is not a new30–90-second story/video requirement.

## Final directory-command and recovery coverage delta

Root additionally held Archive/Restore during the disposable directory exercise.
No progress was displayed and competing commands remained enabled. The owning
hook projected busy state only for Close/Delete/Snapshot; Archive's draft-saving
work also preceded admission. ADR0151 fixes this at command ownership, not the
server's writer boundary: one synchronous exact-token admission spans preparation,
request and directory refresh, with immutable target/action progress at both
directory entrances. No retry, CAS, idempotency or server exclusion is weakened.

Independent review found a superseded archive decision could retain project A
while a later Discard cleared project B's draft. A red unit regression established
the wrong target. Decisions now freeze operation and scope; a changed workspace
dismisses them before error clearing, saving or discarding. Six new lifecycle unit
cases and three adjacent dialog cases PASS; final scoped review has no finding.
The previous browser test's enabled New blank escape is retired by the new pending
contract; a genuine browser-history workspace escape retains the epoch guard and
proves the destination input is preserved. No safety assertion was relaxed.

Held confirmed Delete/Duplicate remain mounted and disabled; Archive/Restore
present target-specific status and disable competing commands. The final Delete
browser case scrolls the actual short-window modal to its action row and asserts
both buttons in viewport. Root and independent reviewer directly inspected
`delete-confirmed-held-actions-1280x460.png` in
`/private/tmp/plotloom-delete-confirmation-scroll-final/`'s exact test directory.
This closes action reachability, not unscrolled all-content fit. Earlier false
capture assumptions (ambiguous notice selector, absent retained Storyboard review)
were repaired in the test harness; their failed artifacts are retained.

Two previously unit-only recovery paths now have actual browser coverage:

- Manual Brief recovery overrides only the capability GET to false. Typed input
  survives session storage/reload/explicit restoration with zero automatic draft
  PUT or canonical PATCH; the explicit Save changes performs the canonical PATCH.
- Typed graph conflict uses two genuine tabs and an actual stale409. The recovery
  POST binds the latest revision/hash and preserves exact tab-B prose; formal
  source/outline and run inventory remain unchanged. Recovery does not restore old
  confirmation/install authority. The primary copy replaces “原始种子” with
  “最初的结构方案”; final graph browser case PASS6.1s.

Independent direct pixel review inspected18 held/refused/ACK/manual/graph captures
at1280×460 and1700×900, then the final scrolled Delete action frame and both changed
graph-copy frames. Root additionally inspected representative Cast/Script currentness,
archived Bible and recovery frames. These are fixtures, not specialist execution.
All three desktop captures exist; no claim that every captured PNG was inspected.
Evidence roots: `/private/tmp/plotloom-directory-command-final-r2`,
`/private/tmp/plotloom-graph-recovery-copy-final`,
`/private/tmp/plotloom-delete-confirmation-scroll-final`,
`/private/tmp/plotloom-currentness-capture-final`. The final stable sweep below owns
combined qualification; scoped red/green runs do not substitute for that sweep.

### Separate Creator provider stale-binding recovery

The two-tab conflict above does not exercise `GraphWorkbenchProvider.recover()`.
Root therefore used the existing disposable structural QA project, without
changing source/test/pin inputs during the sweep. Actual Brief UI changed the node
budget8→9 through the structure-impact confirmation; PATCH request92 returned200.
The Creator stale warning kept the authored opening title/body and disabled normal
editing. Its explicit “在当前版本恢复为新草稿” button sent request97 once, POST200:
`expectedDraftRevision:2`, current `expectedBindingHash:767324a0…`, `payload:null`.
There was no API setup mutation or synthetic recovery click.

Exact before/after readback compares the full authored graph payload, excluding
only changed bindingHash/topologyOrigin metadata. All eight nodes, connections,
text and field buffers remain unchanged; project revision is2, draft revision3,
node budget9. The new draft binds the current version, with topologyOrigin changed
from planner to author. Source and run inventory match exactly. This fixture's
Outline/map are missing, graphAdmission is null and runs are empty before/after;
it proves no authority was created, not preservation of populated installation
or accepted-map state. Normal editing becomes available; confirmation/install
authority is not granted by recovery. The helper is
`graph-recovery-readback.mjs`; evidence is `graph-{before,after}-settings-recovery.json`
under the Board3 evidence root. No extra generation or owner-project mutation.

Root directly inspected all six `graph-provider-{stale,recovered}-{desktop}.png`
viewport captures and the actual scrolled1280×460 recovered frame. At the initial
short-desktop top only the inspector header/footer fit; ordinary page scrolling
reveals the title/body while keeping its action row reachable. This is not an
unscrolled all-content-fit claim. The stale warning/recovery action is readable at
all three sizes; after recovery it is absent. Independent bounded review inspected
all seven pixels and the full JSON diff, with no remaining scoped finding. It
did not operate the browser or independently inspect the request trace. Its full
source-wrapper comparison is broader than the helper's source/Outline/map field
assertions. Neither this review nor before/after records alone establish absence
of automatic writes. This is separate from the two-tab conflict review.

## Software qualification checkpoints

Current4bbf8c2: fresh frontend1,025 PASS/124 files, application/E2E types,
deterministic build, lock, compile, archived Prompt Pipeline Lab verification and
diff hygiene PASS. Focused Python16 PASS.
Wheel/installed smoke PASS outside the checkout at
`/private/tmp/plotloom-4bbf8c2-wheel.AKpINB`. Required CI lint
`uv run ruff check src/plotloom/api --select F401` PASS. An accidental repo-wide
`src tests --select F401` probe failed420 existing findings, including intentional
facade reexports; no bulk fixes or claim of a whole-repo lint PASS. This delta
changes no Python file. Full Python **1,463 PASS in24m15s**, one existing Starlette
deprecation warning. The unfiltered274 browser sweep **PASS in15.3 minutes**,
with two workers to limit concurrent real-process stacks while Python was active. Output
`/private/tmp/plotloom-4bbf8c2-full-browser`, retained parent
`/private/tmp/plotloom-4bbf8c2-full-retained`. No executable/pin changes during gates.

Earlier stable8c79f48 qualification, not the new candidate's broad PASS:

- Fresh frontend1,019 PASS across123 files; application and E2E types,
  deterministic build, lock, scoped F401 lint, compile and diff hygiene PASS.
- Focused Python16 PASS: extraction boundary, static freshness and retained
  runtime inventory. Earlier full Python1,463 PASS at a452e27 remains historical;
  subsequent source deltas are frontend-only, not a fresh full Python claim.
- Serialized wheel/installed smoke PASS. Wheel root
  `/private/tmp/plotloom-final-wheel.N0K45r`, Plotloom0.1.0.
- Final unfiltered272 browser sweep at8c79f48 **PASS in8.8 minutes**; output
  `/private/tmp/plotloom-8c79f48-full-browser`, retained runtime parent
  `/private/tmp/plotloom-8c79f48-full-retained`. No source or pin changes during
  the stable sweep. Documentation reconciliation was separate from executable inputs.
- Existing Starlette deprecation/build chunk warnings remain nonblocking.
  Independent scoped source/test review and final recorded-readback/pixel review
  closed with no unresolved scoped finding; reviewer did not rerun these gates.

## Current fixture visual reconciliation

Independent review directly inspected24 further viewport PNGs from the final
`/private/tmp/plotloom-8c79f48-full-browser` sweep. Root directly inspected four
representative retained-Art/reader/Script frames. This is deterministic fixture
presentation, not native specialist execution or an all-state visual PASS:

| Exact test-output directory | Inspected filenames / desktop sizes |
| --- | --- |
| `source-review-currentness--adc1a--the-same-accepted-revision` | `art-retained-stale-{top,actions}-{1700x900,1280x768,1280x460}.png` |
| `story-prototype-missing-or-c2b39-ther-than-a-transport-retry` | `reader-missing-script-{1700x900,1280x768,1280x460}.png` |
| `story-prototype-optional-s-ac836--and-retries-only-that-read` | `reader-failed-storyboard-{1700x900,1280x768,1280x460}.png` |
| `story-prototype-shows-pend-3bee5-eader-errors-without-writes` | `reader-pending-storyboard-{1700x900,1280x768,1280x460}.png` |
| `sketch-visual-system-deskt-23de5-d-review-states-at-1700x900` | `dirty-source-1700x900.png`, `script-1700x900-viewport.png`, `storyboard-production-1700x900-viewport.png` |
| `sketch-visual-system-deskt-d4456-d-review-states-at-1280x768` | `dirty-source-1280x768.png`, `script-1280x768-viewport.png`, `storyboard-production-1280x768-viewport.png` |
| `sketch-visual-system-deskt-c3800-d-review-states-at-1280x460` | `dirty-source-1280x460-viewport.png`, `script-1280x460-viewport.png`, `storyboard-production-1280x460-viewport.png` |

The Art warning and disabled draft controls are readable; missing Script names
its preparation owner rather than suggesting transport retry. Held/injected
Storyboard reads remain visibly distinct and preserve route context. Accepted
Script guidance is readable. Storyboard production captures still say loading/
processing: they do **not** qualify a settled production-ready state. Short
viewports qualify only their visible slice, not all below-fold controls. No
blocking presentation defect was found in these observed states.

Later root inspection used six existing viewport PNGs from the frozen4bbf8c2
full-browser output, not a new browser run:

| Exact test-output directory | Root-inspected filenames |
| --- | --- |
| `source-review-currentness--01170-r-an-accepted-status-change` | `script-retained-dirty-status-1280x768.png`, `script-retained-dirty-actions-status-1280x460.png` |
| `source-review-currentness--43884-ch-but-permits-cancellation` | `storyboard-stale-ready-1700x900.png` |
| `source-review-currentness--b921e-ch-but-permits-cancellation` | `storyboard-stale-prepared-1280x460.png` |
| `source-review-currentness--f6e06-hority-until-explicit-retry` | `storyboard-post-mutation-read-failed-1280x460.png`, `storyboard-post-mutation-read-failed-1700x900.png` |

Dirty Script retains authored text and visibly disables saving until explicit
replacement. Stale-ready Storyboard distinguishes changed Script dependencies,
disabled confirmation and available rejection. Failed refresh exposes an explicit
retry and refusal to modify/produce. Root also read the complete owning test and
desktop capture helper: these are mocked deterministic review states, not native
specialist execution. Short captures qualify their visible slice only; lower
controls in stale-prepared/read-failed cases do not all fit. No new blocking
wording, alignment or overflow defect was observed in these six frames.

Independent review directly inspected12 existing4bbf8c2 viewport PNGs, with no
new tests or browser actions. Root additionally inspected the replacement-ready,
stale-ready Script and both updated accepted-Storyboard frames:

| Exact test-output directory | Independently inspected filenames |
| --- | --- |
| `source-review-currentness--6d06b-ch-but-permits-cancellation` | `script-{stale,retained-stale}-prepared-1280x460.png` |
| `source-review-currentness--d5388-ch-but-permits-cancellation` | `script-{stale,retained-stale}-ready-1280x460.png` |
| `source-review-currentness--b921e-ch-but-permits-cancellation` | `storyboard-stale-prepared-1280x460.png` |
| `source-review-currentness--43884-ch-but-permits-cancellation` | `storyboard-stale-ready-1280x460.png` |
| `source-review-currentness--f6e06-hority-until-explicit-retry` | `storyboard-post-mutation-read-failed-1280x460.png` |
| `source-review-currentness--c602e-ter-an-accepted-head-change` | `script-retained-dirty-{head,actions-head}-1280x460.png` |
| `review-seam-currentness-cu-7d33b-ver-stale-retained-evidence` | `script-replacement-ready-1280x460.png` |
| `sketch-visual-system-deskt-{d4456,23de5}-d-review-states-at-{1280x768,1700x900}` | `storyboard-production-{1280x768,1700x900}-viewport.png` respectively |

The replacement candidate is current while the old accepted Script is retained
and stale; enabled replacement confirmation does not grant old evidence authority.
The two updated Storyboard frames settle the accepted-review read only: their
production proposal still says loading/processing. No settled production-ready
or all-state qualification follows from those frames or their filenames.

## Earlier gap checkpoint — OS criterion superseded by settled run below

Actual current-candidate OS blur remains **NOT EXERCISED**. Two held-resize attempts
delivered no trusted blur; method reassessment and a third no-drag diagnostic also
delivered none after CDP focus emulation was disabled. The browser remained focused.
Finder/Chrome targeted actions did not establish a genuine foreground switch; a
later Dock inspection timed out. Fourth and fifth no-drag diagnostics used the
observed Finder window's Raise/menu actions, then a screenshot-grounded blank-area
click. Finder's selection changed, but the matched QA Chrome page still reported
`document.hasFocus() === true` and zero trusted window-blur events during the
continuous diagnostic. Focus emulation was restored and no held-drag assertion
was attempted from that result. `Browser.getBrowserCommandLine` also refused
metadata because `--enable-automation` was absent; that refusal is not evidence
that this page was headless. Returned width/text/caret and synthetic handler
checks are useful but cannot close this criterion. Historical genuine OS evidence
on5aff37e remains historical. No OS permission/settings change is authorized here.

Subsequent read-only transport diagnosis inspected cached CLI0.1.22/Playwright
1.64.0-alpha-1790635538000 implementation. Chromium page initialization enables
focus emulation; ordinary `ensureTab`, run-code completion and accessibility
snapshot paths do not re-enable it or call `bringToFront`. Explicit tab selection
and recording start do bring a page forward, but the retained diagnostic evidence
does not establish those intervening commands. Exact owned session metadata for
`native-routes-195` reports `attached:false`, Chromium/Chrome and `headless:false`.
This establishes a launched headed browser, not the matching OS window/target or
the cause of persistent focus. The root cause remains unknown. No sixth OS attempt,
browser invocation, settings change or synthetic acceptance followed this source
inspection; the trusted current OS-blur criterion remains unqualified.

A later read-only public `Browser.getVersion` diagnostic, guarded to the exact
owned structural QA page, identifies the active browser as Chrome154.0.8037.97,
revision `b510e9d7cd3a2fbd78d0ddc42234103206c5f78d`. Root and independent review
then inspected that exact Chromium source. The [renderer setter](https://chromium.googlesource.com/chromium/src/+/b510e9d7cd3a2fbd78d0ddc42234103206c5f78d/third_party/blink/renderer/core/inspector/inspector_emulation_agent.cc#603)
unconditionally forwards false to the shared FocusController; the browser-side
handler's equality guard returns FallThrough and does not block renderer dispatch.
This rules out the proposed fresh-secondary-session false no-op mechanism for
this revision. The owning agent can restore retained true, but no such intervening
restore is established. No sixth OS attempt, private-client access, emulation
change or product patch followed. Browser revision is proven; actual OS-window
identity and the cause of persistent focus remain unproven. A true/false toggle
would not improve this exact setter path and is not another acceptance method.

Further read-only target correlation obtains browser PID60986 through public
`SystemInfo.getProcessInfo`, matches it to LaunchServices' foreground PID, and
reads the exact owned QA URL in the native Chrome AX window. This strengthens
present-target identification only; it does not retroactively prove a foreground
switch or trusted blur in any earlier attempt. No OS permission changed.

E22's register still explicitly retains unobserved view/state permutations. Native
API model-inference E12 is unavailable by configuration, distinct from the built
and exercised Codex-native intent path. Scene/Prop downstream reference consumption
remains a capability gap; review/generation does not prove exact continuity.
The owned renderer pin4f9b2128 is qualified by pure/fixture/parent checks, but the
accepted native Storyboard remains frozen at266af294/report SHA8ac6996b. Do not
rewrite it or count it as native execution under the later evaluated-gate pin.

Normal-cutover preflight read both exact owner databases through the candidate's
read-only current-schema admission. Both are refused as unsupported SQL layouts;
no manifest, database row, asset or credential was rewritten. This is the intended
breaking admission boundary after removal of schema transitions, not a migration
defect to patch. The existing healthy normal runtime remains on its old matching
checkout. Updating that mounted checkout alone would expose new static bytes to
the old backend, so it is not a safe publication/deployment shortcut.

All frozen-candidate local release gates above are now settled. Independent scoped
source, recorded-readback/pixel and finite stopping-condition reviews are closed;
they do not expand the observed E22 slices to every state. No more media generation,
route replay or idle restart is required while executable/static inputs stay fixed.

Publication is a recoverable candidate-branch checkpoint, not normal activation
or an update to the mounted main checkout. Normal cutover still requires an
explicit choice for retained older demos, not a compatibility layer or implicit
reset. Current OS blur needs human/access or an explicit scope decision; another
blind transport attempt is not a demonstrated repair. CI/publication outcomes are
reported separately from these local gates. These boundaries prevent test totals
or a rough progress estimate becoming a100% acceptance claim.

Candidate checkpoint `e04e428` was pushed to `origin/codex/one-current-story-rebuild`
with clean worktree and0/0 divergence. Its delta from executable4bbf8c2 is seven
documentation files only. Exact-head [CI37997439888](https://github.com/Wenjun-Mao/plotloom/actions/runs/37997439888)
was dispatched once with unfiltered `browser_grep=.*`; observed in progress at
22:07UTC, not a remote PASS. Normal main stays7d79d18 and its mounted static bytes
remain unchanged. This later record-only reconciliation is not a source/pin change.

## Remote verification budget: observed failure and owning correction

Exact CI37997439888/e04e428 ended cancelled at22:38:07UTC. Verify job114046970043
exceeded its30-minute budget; browser never started. Its pytest log steadily
advanced from4% at22:09:18 through83% at22:37:58 before cancellation at22:38:04,
without reported failure/error markers. This is not a remote PASS or a demonstrated
stalled test. The local full suite's24m15s does not establish hosted-runner capacity.

The owning workflow now bounds Python at45 minutes inside a55-minute verification
job, preserving the full serial suite and adding only `--durations=20` reporting.
There is no filter, removed test, product timeout change or browser-shard change.
The new contract case failed against the old workflow (1FAIL/3PASS), then all four
CI contract cases passed after the repair; focused Ruff and diff checks also pass.
Independent read-only diff review agrees the layer and selection are correct;
its future-margin finding is closed by requiring a configured gap of at least10
minutes for setup/wheel/smoke, not guaranteeing10 minutes after pytest. Product
source, checked static and renderer
pin are unchanged from4bbf8c2; only CI configuration/test and this record change.
A fresh exact-head unfiltered CI run is required, not a retry claimed from the
cancelled run or automatic acceptance from the earlier local totals.

The scoped correction is published as `ef162100c8d7e2191908ee7a142ac2f4f6652646`.
[CI38000995714](https://github.com/Wenjun-Mao/plotloom/actions/runs/38000995714)
was dispatched once at22:46:17UTC with `browser_grep=.*` and that exact head.
It is in progress, not a remote PASS. Four focused CI cases, focused Ruff and
diff hygiene pass; the earlier1463 local Python total is not a new1464-suite run.

## Real OS blur pilot: criterion remains only partly exercised

With public focus emulation disabled on the exact owned QA page, CUA's observed
native `Hide Google Chrome` command changed the foreground from matched Chrome
PID60986 to ChatGPT PID2512 and produced a trusted document blur/hasFocus=false.
This resolves the earlier lack of an established OS blur method. It did not hold
a pointer or activate a resize gesture, so held-resize cancellation is not PASS.
Raise alone did not restore foreground. CmdTab produced a trusted document focus/
hasFocus=true, while the foreground PID read remained2512; OS return is unproven.
Listeners were removed, focus emulation restored and exact authored eight-line
text retained. No project command, provider dispatch or OS permission changed.
Root and independent read-only reviewer agree these evidence boundaries. The
ignored native receipt is `output/playwright/board3-r12-2026-10-09/
native-hide-focus-pilot-20261009.json` in the normal source checkout.

## Settled held OS-blur qualification

The current4bbf8c2 criterion now passes on owned structural QA at1280×460.
Explicit UI Save drained the clean authoring boundary; GET200 retained exact
draft3/updatedAt21:57:12.022579Z. Public focus emulation was disabled only on
that page. Twelve consecutive baseline frames proved caret0/textarea scroll0.
Real captured pointer movement changed width300→370; native-menu-open remained
370. CUA Hide Chrome changed LaunchServices foreground60986→2512 and produced
trusted element/window blur. Width rolled back to300 before lost pointer capture.
CLI tab-select13 restored foreground60986 and trusted focus. Continued buttons1
movement and release did not resume resizing or persist370. Exact text, caret,
active field, both internal scroll positions, automatic-width/null preference
and the complete server draft matched; zero mutation requests. Diagnostics were
removed, pointer released and focus emulation restored. No product patch needed.

Initial scroll comparison was confounded: macOS plain End started an animation
21→191.5→262. Idle End independently reproduced0→171→262 with width300 and caret0,
without resize/OS actions; settled resize/release retained scroll0. Evidence is
retained, not erased. The playbook now requires a stable scroll/caret baseline.
Ignored receipts in normal `output/playwright/board3-r12-2026-10-09/`:
`native-held-os-blur-20261009.json` (confounded scroll),
`textarea-scroll-setup-diagnosis-20261009.json`,
`native-held-os-blur-settled-20261009.json` and settled return viewport PNG.
Independent read-only review inspected all three JSON receipts and the return PNG:
no actionable finding. Server equality, zero writes and cleanup are retained
execution assertions, not a second server replay. This closes only the named
held-resize/OS-focus slice, not all dirty-input states or whole-product acceptance.
