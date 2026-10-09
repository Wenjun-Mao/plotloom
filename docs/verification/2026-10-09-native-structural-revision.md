# Native structural revision and graph label layout

This is the Revise round of the approved full creator E2E run, on the same
completed native project `90c0f895-48de-4b57-8725-4b6f72797633` at isolated8865.
Revised production and playback remain pending. No native job was dispatched
during these structural operations; normal8841 and protected projects were not edited.

## Authoring actions and saved state

After explicitly changing Brief nodeBudget4→8, the UI recovered the existing
draft against the current binding. An exact East-choice-edge insertion created
scene `graph-3d5df4ce8b4141e19bdc13e7` and continuation
`graph-b9c9410be53e4696ac3d48dd`. Draft r3 contained the insertion, r6 the final
title and prose. A value-matched save ACK and independent readback preceded reload;
the text and identities survived. This avoids confusing an earlier title-blur ACK
with a later full-prose save.

Safe bypass removed that scene at r7 and restored the original East edge. Undo
restored its identity, prose and connections at r8. Undo uses authoring-drafts PUT;
an automation wait incorrectly expected graph apply POST and timed out, but the
readback established the applied r8 and no duplicate action was issued.

Deleting the old East ending with “仅删除，保留待连接” produced r9 and a pending
continuation endpoint. Changing the new scene to an ending correctly refused
while that output remained. Explicitly deleting the pending continuation produced
r10; the subsequent ending conversion succeeded at r11. Final East title, summary
and choice consequence were acknowledged at r13 and independently read back.

The final topology has four nodes and three edges: original opening, original
route-only choice, unchanged West ending and the new East ending. Original East
choice edge `edge-ab8a8b8d-dfa8-5fc2-895b-13d1ead701d4` now targets the new ending.
The new East summary retains a five-second left-lamp/left-turn ending and the
ten-second opening, without new characters, settings or props.

Normal UI confirmation returned200 at03:27:45UTC; graph application returned200
at03:28:06UTC on October9. Confirmed map r3 hash:
`dae2b0721c9833baaa1403b3bbc5eda97e136dca0232a050c87ab88b5a338c89`.
Applied graph r3 hash:
`30a0f7257cffed8454838d81ddb0e397b8f827e5db3ddaf89f561d346d7fc894`.
The graph admission is current. All four baseline H3 jobs remain ingested with
one retained segment each, current=false and selected=false. Old media is retained,
not admitted as revised production.

## Label layout root cause and repair

Insertion appended a node identity while the visible row put West before the
new East scene. Label lanes still followed historical edge creation order, so
the outgoing option curves crossed. This was a presentation-layer ordering bug,
not a wrong story connection. `creatorLayout` now sorts each copied label lane by
visible target position, then source position at joins. It does not reorder or
rewrite the story topology or edge identities.

A regression reproduces the appended-middle-node case and asserts label order
and unchanged edge output. The existing six-sibling/converging-label check now
tests geometric separation independently of original edge creation order.
Independent read-only review found no concrete defects. The previous stable
checkpoint passed840 frontend tests, types and the isolated frontend build;
this continuation reran all three layout tests and diff checks successfully.
Full browser and publication gates remain separate.

Directly inspected evidence under the main checkout's
`output/playwright/native-intent-2026-10-08/`:

- `revise-inserted-middle-1700.png`: original crossing defect.
- `revise-inserted-fixed-1700x900.png`, `revise-inserted-fixed-1280x768.png`,
  `revise-inserted-fixed-1280x460.png`: repaired routing and retained side editor.
- `revise-delete-bypass-preview-1280x460.png`: initial short-height preview;
  its lower controls were outside that captured viewport.
- `revise-delete-ending-controls-1280x460.png`: scrolled preview with confirmation
  controls visible and subsequently used successfully.

C06 now permanently includes insertion-induced label ordering. This checkpoint
does not close character/reference revision, production rebuild, fresh media,
all revised routes or the remaining whole-product E22 audit.

## Stale cast editing defect found during revision

After graph r3, Cast correctly became stale and retained its old descriptions and
two identity-reference images. However, “编辑角色设定” remained enabled. Clicking
it wrote a reopened head, while the state projection continued to return stale
and therefore never displayed an editor. Saving that binding could not succeed.
The next-step guide also directed the author back to already-current source
content rather than preparing the replacement review.

The repair validates the accepted binding inside the reopen transaction before
head mutation, returning the existing typed context diagnostic on staleness.
The UI only enables accepted-cast editing for current accepted state; it explains
the new-task path and keeps retained content readable. Changed-binding guidance
uses the current review's recovery instruction, while genuinely missing upstream
prerequisites still link to their owning stage. ADR0076 records this distinction;
no stale content is rebound, accepted automatically or deleted.

Independent review found no actionable defects. Focused16 Python and27 frontend
checks pass, including unchanged head status/time/revision on refusal. All845
frontend tests, application types and the isolated build pass. Root directly
viewed `revise-stale-cast-guidance-{1700x900,1280x768,1280x460}.png`: the disabled
edit action, retained text, recovery explanation and preparation control are
readable; preparation remains available. Nine focused browser checks and browser
types also pass, covering current edit/cancel/save, reference session ownership,
stale reads and cancellation. Lock, production F401 and diff checks pass. A wider
F401 invocation also found five pre-existing unused imports in the touched Cast
test module; cleanup is deferred until the running full Python gate finishes so
its inputs remain stable. Full Python verification and loading the backend repair
are pending at this checkpoint. No replacement generation has yet been dispatched.
Protection readback still matches aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`:
Wind17 files, Rain67 files and three protected settings/credential files unchanged.

## Character render contract — subsequent continuation

The preceding pending Python gate completed:1,382 PASS in628.95s on the
stale-Cast repair checkpoint `16b058a`. That matching backend was loaded on
isolated8865. The five unused test imports were then removed. These results
are not the qualification of the subsequent style-contract changes.

One replacement Cast task, `ch_39ba9445a043441ab2c289934e5fb441`, was prepared
at03:39:13UTC and sent once at03:39:37UTC on October9. It completed in142.868s
and reached candidate-ready, but was NOT accepted. Its report explicitly
disclosed that the upstream painterly `realistic` preset conflicted with the
author's live-action direction. Candidate and report remain immutable evidence.
Correcting prompts downstream would repeat the baseline's contract failure.

[ADR0141](../adr/0141-character-render-direction.md) defines explicit author
style selection, frozen direction and shared delivery/accept/save validation.
The candidate implementation also corrects Art's prerequisite check: it must
validate the actual accepted Cast binding, not a freshly generated context
against itself. No vendor rewrite, compatibility execution or evidence patch
is introduced. A ready proposal can be abandoned through the UI before a
replacement is prepared; cancellation does not delete its delivery files.

Independent source review found no concrete defects and requested persisted
staleness coverage. The added tests prove missing/changed contracts prevent Art
preparation without mutation. A Brief edit fails at the earlier installed-graph
prerequisite; the test initially expected the later style diagnostic and was
corrected after inspecting the context evaluation order. Focused21 Python
checks now pass. The prior broader focused106 checks,845 frontend tests and15
Cast/reference/currentness browser tests also pass. Application/browser types,
the updated frontend build, focused F401 and diff checks pass.

The new explicit-style browser flow passes: abandon a ready proposal, retain
its exact candidate bytes, require a selection, prepare a distinct live-action
package, compare the frozen contract with its binding and reload. Root directly
inspected `output/playwright/cast-render-contract-2026-10-09/` screenshots at
1700×900,1280×768,1280×460; the selector and preparation control remain readable.
Wheel build/installed smoke and protected-owner aggregate verification also pass.
An additional in-memory integration check used one character from the pinned
`渡口` example and its actual source text: all three current presets passed
the composed style/upstream validator and rendered a report containing the
character. Substituting a fabricated evidence quotation was rejected for each.
No retained native candidate or vendor file was changed for this check.

The first unfiltered241-test browser run exposed six static-Cast-report setup
failures: two fixtures still omitted the now-required preparation body. The
API's422 refusal was correct. Those callers now explicitly choose `realistic`;
all six report regressions pass in29.4s, preserving their original-report and
no-write assertions. The unfiltered run remains diagnostic, not a green gate.
Full Python qualification of ADR0141 and broader browser discovery are still
running. The implementation remains uncommitted and is not activated
on normal8841. No new native style-corrected task has been dispatched. Revised
production, fresh media, all revised routes and remaining Recover/E22 checks
remain open.

## Qualification follow-up: fixture contracts and specialist read settlement

The first full browser run completed with233 passes and8 failures. Six were the
missing explicit Cast style bodies noted above. One was a fixture-byte regression:
the common delivery helper unnecessarily reserialized non-Cast JSON. Non-Cast
fixtures now retain their original bytes, and the original Storyboard hash
assertion passes. No retained native delivery was rewritten.

The eighth failure initially appeared on an immediate API snapshot after UI
cancellation. The trace showed two in-flight specialist status GETs overlapping
the exclusive snapshot. Replacing that direct call with the real snapshot button
reproduced the refusal: specialist fetches were outside the main API client's
read barrier. The repair enrolls all browser specialist GET bodies in the same
project read admission. A second regression distinguished completed domain
refusals from interrupted reads: a fully received409 after cancellation settles
the read even though the caller still receives its domain error. Transport/body
interruptions remain fail-closed. ADR0124 records the boundary; no sleep, retry,
lease relaxation, reservation clearing or dispatch changes were added.

Independent review of both lifecycle deltas found no concrete issues. Full849
frontend checks, application types and build pass. The stricter full-body check
also exposed a unit fixture reusing a consumed Response; it now returns a fresh
response for each subsequent call. One intermediate browser run was invalidated
by an implementation edit causing Vite hot updates (visible in its retained
trace); stable-source repetition and the fresh unfiltered gate remain required.
Evidence lives under `output/playwright/cast-render-contract-2026-10-09/` in
separately named regression directories, preserving the initial failure traces.

Full Python completed with1,393 passes and5 failures in1,446.78s. All five were
old preparation callers omitting explicit style in the context/currentness test
fixtures; both affected modules now pass all19 checks. A new unfiltered Python
run is in progress. This is not yet a qualified native execution checkpoint.

The stable-source cancel-to-snapshot journey then passed three consecutive
fresh-fixture executions in21.4s, without retries or timing sleeps. Wheel and
installed smoke pass. Protected aggregate remains
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.
Fresh unfiltered241-browser qualification is now running in `full-browser-final`;
do not interpret the focused repetition as full-suite completion.

While the stable full gate ran, root directly viewed six of its current viewport
captures: Art enlarged-report top1700×900, inline-report bottom1280×768,
enlarged-report bottom1280×460, Character long-rights details1280×768,
explicit-style empty selection1280×460 and Cast long-synopsis end1700×900.
The report scope/read-only guidance and close controls are readable; the report
bottom and synopsis final line are visible, and long rights text wraps without
covering identifiers. The short-height style selector and disabled preparation
control remain beside their guidance rather than clipped by the toolbar.
English report prose is explicit fixture content, not a native Chinese-delivery
claim. The scrolled Character image is only partially in that viewport; this
capture proves rights-layout readability, not whole-image comparison. No new
visual defect was observed in these six states. Their paths remain in
`full-browser-final/{art-static-report-*,cast-reference-studies-*,cast-render-choice-*,cast-static-report-*}`;
they do not close the remaining whole-product state permutations.

Four further current-gate captures were directly inspected: the six-sibling
graph's middle three siblings and resized/reopened editor at1280×460,
node-kind refusal at1700×900, and pending-cancellation Inspector actions
at1280×460. Parallel siblings share a row, the editor remains at the right with
its footer visible, and the geometrically drawn plus is centered. The reopened
graph retains deliberate horizontal pan (part of the ending is outside the
viewport); that capture does not prove automatic recentering. Refusal guidance
is visible above the editing fields, and the cancellation action is reachable.

The refusal capture also demonstrates an E22 wording defect: node selectors
render internal `scene`/`decision` values. Source inspection locates this in
GraphEdgeDetails, GraphNodeDetails and CreatorEditDialog, while CreatorChart
already has Chinese node-kind labels. This is presentation ownership, not an
invalid graph or a reason to translate stored enums. A shared Chinese label
mapping and regression checks belong in the subsequent bounded copy pass,
alongside the previously noted playback continuation wording. Product/test
inputs remain unchanged during the current full qualification suites.

The same current run's1280×768 conflict, failed reload and verified-retry
captures were also directly viewed under
`current-contract-recovery--be4ce-ilure-and-retry-at-1280x768/`. The conflict
dialog distinguishes reload/copy/discard; the failed-read dialog retains
readable, scrollable draft JSON with copy/export/retry controls and explicitly
withholds writes before project verification. After successful verification,
the unresolved version conflict is shown again instead of silently overwriting
it. Buttons and explanations fit their dialogs. These are product-shaped
fixture observations, not a newly induced native service failure.

Three further current captures were directly reviewed: stale rebuild guidance
at1280×460, complete selected-reference sources at1280×768 and expanded frozen
direction at1280×460. The rebuild notice distinguishes preserved media from
paused playback and asks for a new reviewed proposal. Both selected-reference
images use full-image containment rather than thumbnail cropping; the second
is deliberately an imported screenshot fixture, not a generated character-quality
claim. The long direction wraps and its technical identifiers remain readable.
That last element capture includes the fixed header and does not by itself prove
every scroll position is unobscured. Original English fixture prose and raw
technical provenance values are retained evidence, unlike the editable node-kind
selector wording defect recorded above.

The fresh unfiltered browser gate completed: **241 PASS in14.7minutes**
(`full-browser-final`, two workers). It includes the real UI cancel-to-snapshot
regression, explicit Cast render selection/discard and currentness flows,
same-project rebuild, recovery, report reading and media controls. The Python
gate is still running; no native activation or replacement dispatch has occurred.

Pre-activation readback again confirms protected aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`,
Wind17/Rain67 files and three protected settings files. The isolated specialist
registry is idle. Old Cast proposal `ch_39ba9445a043441ab2c289934e5fb441` remains
ready and unaccepted over accepted Cast r1; its original delivery hashes are:

- cast.json: `82bc7f25b4294d9bc0b7bae48730986a82444d4055dffca70252f8dd65779da2`
- report.html: `7e33a7213e8a25a77e19287653961f824de3d89cc054a62761874476e0655453`
- completion.json: `cf4d0fa3428a073607d23a75ad2c7528cb1e68003f8a404b75eafbebe47c18e7`

Final Python qualification completed: **1,398 PASS in1,457.74seconds** with
one dependency deprecation warning. Combined with849 frontend PASS,241 browser
PASS, application/browser types, build, lock, F401, diff, wheel/installed smoke,
prompt-reader verification and independent source review, this qualifies the
Cast-style/shared-read repair checkpoint for isolated native execution. The
known node-kind/playback copy follow-ups and full native Revise/Recover/E22 scope
remain open; normal8841 is not activated by this local checkpoint.

## Native Cast revision and retained-image refinement repair

The committed `0923311` checkpoint was activated only on owned8865/8866.
Native Cast job `ch_83c99e97726b475e83a07d14926091ae` was prepared/sent once
with explicit live-action direction, current graph/map r3 and unchanged source.
Its original Cast/report hashes are respectively
`909c15de60a78999d0a1658a63a5f2308420c42dbe3b1abd134e541f4eefce48` and
`f1e75a667b90f5c3600762a5fdf288fd261026fa62b1a3ef5674aea91c990394`.
UI confirmation established Cast r2; reopening and saving the QA low-bun design
established r3 after the successful save ACK. Subsequent GET readback confirms
accepted r3, no stale reasons and content hash
`5b1a8d604aaa024e39bb7078a067b8ee8a4826525d51bb8e9e84349770e653a4`.
The old delivery remains original, with the edited head explicitly different.
Native evidence is under normal-repo `output/playwright/native-intent-2026-10-08/`
(`revise-cast-*`). The capture named `revise-cast-original-bottom.png` shows the
voice/prompt sidebar, not proof of reaching the complete report's bottom.

The next real UI action selected an older same-character image as an explicit
editing input. Preparation failed409: `proposal refinement must name a current
candidate for the same character`. The failure is retained in
`revise-historical-refinement-refused.png`; no new proposal or dispatch resulted.
Backend admission incorrectly equated the parent proposal's currentness with
its eligibility as an image input. New-proposal authority must instead come
from the current accepted Cast, with the accepted retained image bound by hash.

The scoped repair in ADR0061 preserves current-Cast admission, requires a
same-project/same-character delivered parent with accepted matching delivery and
exact asset hash, and freezes the old image only as `parent_output`. Package
instructions now name the accepted Cast, require viewing the parent and state
that current design supersedes the older design. Gallery eligibility/copy agree.
Old proposals and selections remain stale; nothing is automatically selected.
The permanently hidden duplicate proposal form and its unused requests/actions
were removed from the production-media panel; reference selection/review remain.

Verification so far: ten new persistence regressions PASS; seventeen focused
related Python checks PASS;849 frontend checks, application types, deterministic
build, lock, F401, diff, prompt-reader verification and installed-wheel smoke PASS.
The new browser revision journey PASS includes acknowledged Cast edit/reload,
retained-image prepare/send through fake transport, current-input verification,
delivery/reload and unchanged old proposal/decision/manifest bytes. Its initial
diagnostic failures were harness assumptions (retired copy endpoint, required
field accessible name and request envelope); corrected tests retain all guards.
Their first/second/third/focused evidence directories remain, not counted as PASS.

Root directly inspected all three fresh full-gate refinement viewports at
1700×900,1280×768,1280×460. The old-design explanation, selected refinement mode,
author text and create control are readable below the toolbar. Files are under
worktree `output/playwright/reference-revision-2026-10-09/full-browser/`
`cast-reference-revision-re-fa38a-s-old-proposal-or-selection/`.
English authored text and existing images are fixtures, not native delivery or
quality approval. Independent GPT-6.1 Sol/Medium review reported no findings,
with ten focused Python checks and diff check independently passing; effective
host model settings were not independently verified. Full Python/browser gates
are still running. No revised native image has been prepared or dispatched yet.

Protection readback still matches
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`,
Wind17/Rain67 files and three protected settings. Specialist registry is idle,
with exactly two delivered/noncurrent old Character proposals and no new one.

Separate E22 report diagnosis: retained Cast report line307 still explains
inline inference markers, but the current writing contract moves inference
disclosures into `reviewNotes.sourceNotes` and acting constraints into
`performanceGuidance`. This report embeds those notes only in the JSON-copy
payload and script data, not a readable review section; the static reader hides
the copy control and disables scripts. This is a generation/reader contract gap,
not missing notes in accepted Cast data. Preserve original bytes; qualify a
current-contract report fix alongside the pending Outline duration-rendering
repair. Neither issue is repaired by the refinement change.

## Project import ACK race found by the full gate

The first unfiltered browser run finished **241 PASS / 1 FAIL**. At1280×460,
the end-frame journey imported an asset successfully but could not find its
candidate control. Trace timing shows the approval201 at05:22:09.959UTC,
import POST at10.089, new-context reads at10.094, and import201 only at10.855.
Those reads were empty; no post-import read followed. The import handler held
the preceding approval context's refresh callback, which correctly refused
that obsolete context but consequently never refreshed the current gallery.
This was a product ownership race, not a viewport or provider failure.

A deferred-import/shot-change integration test first reproduced the missing
third read. ADR0130's project-write ACK helper now refreshes the latest context
within the same project visit/mount. Old A→B→A visits and unmounted owners are
ignored; the existing read sequence supersedes pre-ACK reads. No optimistic
injection, generation retry or test-only approval serialization was introduced.

Fresh qualification: **852 frontend PASS**, application/browser types and
deterministic build PASS; the affected browser journey passed **nine checks**
(three repetitions at each supported desktop size). Independent read-only
GPT-6.1 Sol/Medium review found no issues and independently passed21 affected
frontend checks. Effective host model settings remain unverified. A new full
browser gate is running in `full-browser-ack-fixed`; full Python is still live.
The first red trace/screenshot/video remain under `full-browser`, and the nine
passing regression checks under `import-ack-regression`, in the same dated
worktree evidence directory. Native runtime activation is still pending.

Fresh direct pixel inspection of the repaired refinement form passed all three
desktop sizes from `full-browser-ack-fixed`. Native original-Cast reading was
also checked without reloading the old runtime: `revise-cast-report-document-end-`
captures show the final Chinese prompt text and true document boundary at all
three sizes (remaining scroll0). The earlier `actual-bottom` capture, despite
its name, only shows the shorter voice column and is not bottom evidence.
The current-head/original-delivery distinction is visible; the separate missing
source/performance disclosure and obsolete inference-marker wording remain open.
Wheel/installed smoke, lock/F401/diff and archived prompt-reader checks PASS after
the final frontend build. Owner/protected-file fingerprint remains unchanged.

Final checkpoint qualification: **1,408 Python PASS in1,522.62seconds** (one
dependency deprecation warning), **852 frontend PASS**, **242 unfiltered browser
PASS in8.1minutes**, types/build/compile/lock/F401/diff/prompt-reader/wheel/smoke
PASS. Independent source reviews and direct three-viewport refinement pixel
review closed without findings. Checked JS SHA256 is
`65af915186ccdb1e516560c62c9fded9961e25c25f82b9fe1c53a3053f8f17bb`.
Root approves this stable checkpoint for isolated activation/native refinement,
not normal8841 publication or completion of the remaining Revise/Recover/E22 run.
