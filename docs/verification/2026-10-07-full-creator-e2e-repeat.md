# Fresh full creator E2E run ledger

Scope: [approved repeat](../roadmap/2026-10-07-full-creator-e2e-repeat.md).
Inventory: permanent C01–C55/P01–P06/E01–E22, with meaningful subcontrols and
states recorded separately here. Current status is IN PROGRESS, not acceptance.

## Preservation and runtime

Baseline `8782dab`, clean main. Manager independently captured protected owner
rows, 67+17 files and three protected configurations: aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.
New isolated8861/8862 `.local/full-creator-2026-10-07/installation`, initially
process7211 then idle-restarted13666 before first send,23408 before branch dispatch,
30338 after branch completion (zero inflight/two completed receipts). Prior8851 projects and evidence
remain retained. This ledger never records credentials.

## Inventory and root causes

| Contract | Controls/states and required evidence | Status |
|---|---|---|
| E01–E04/P01–P05 | Fresh Brief/source/outline/branch UI, frozen tasks, reports/cancel/reopen, independent Save/Confirm/Apply | PARTIAL: Brief/source/Outline r1 and native branch Confirm/Apply PASS; richer native structure pending |
| E05–E06/C01–C55 | Permanent structural/detail/settings inventory, required123→222→333 sequence, richer joins/choices, dirty/authority recovery | PARTIAL: separate fresh structural QA; actual123/222/333 reconnections, bypass/delete/Undo and decision/join/ending cancel/delete/Undo PASS; unconnected deletion, save/reopen and remaining detail/visual inventory pending |
| E07–E09/P04/P06 | Cast/art native delivery, distinct image subjects, pair comparison/zoom/selection/refinement/reopen, exact provenance | PARTIAL: original Art provenance/static reader/gallery zoom PASS; native Cast static reader/review/confirmation r1 PASS with offscreen style boundary; fresh images pending failed execution-preflight recovery |
| E10–E13 | Script/static archived report/full scenes, storyboard review, intents/presentation/install, exact canonical handoff | PARTIAL: original Script/Storyboard static readers PASS after retained FAIL; fresh Script/Storyboard/intents/presentation/install workflow pending |
| E14–E18 | Native keyframes, managed endframe/dirty guards, one-send H3, original/segment decisions, all media routes, downstream staleness | NOT EXERCISED |
| E19–E21 | Rapid project/node/mode/history, queued/hidden/reopened tasks, unknown refusal, snapshot/restore/typed deletion/idle restart | NOT EXERCISED |
| E22/C37–C39 | Three viewport sizes × color preference, separate pixels,30–90s exploration, clean seed, full gates/independent review/preservation | NOT EXERCISED |

Provenance failure: persisted declaration exists, while candidate.asset embeds
metadata only. Shared art/character/shot candidate serializers have the same
defect. Correct layer is public persistence projection, not gallery fallback.
ADR0125 records the fix and null/history semantics. Original runtime/gallery retest
passed independently; fresh native gallery coverage remains pending.

Outstanding provenance UI gaps at the reviewed execution checkpoint: the shared
API now projects persisted declarations, but Character ProposalDetails passes
only origin, and shot MediaCandidates omits rights. Art shows both. These are
disclosure-owner gaps, not a persistence/schema defect; E08/E14 are not fully
qualified. Manager authorized a LOCAL checkpoint commit of current tested source
only, not push/normal activation or full E2E completion. Follow-up Character/shot
UI must display persisted source/rights/optional note and absent declarations as
unavailable, never infer approval. Pinned image API/persistence source stays frozen
while the same request/reservation is outstanding; native continuation still
needs separately confirmed human authority.

Archived Script failure: pinned report Show-all handlers require JavaScript,
while iframe and endpoint CSP intentionally prohibit it. Long scene blocks may
be clipped. Owning reader presentation must preserve stored report evidence and
the security boundary. ADR0126 defines named static Script/Art/Storyboard/Cast
presentation after actual neighboring failures. Original Script/Art live reader
retests passed. Corrected original Storyboard full prompts/segments and fresh
native Cast static disclosures also passed; wide Cast height repair independently
corroborated. Final hidden relationship hint is fixture-proven and awaits live
activation after native reservation resolves. Pinned multi-role/long-content
fixtures passed separately; no scripts enabled. Fresh Script/Storyboard provider
milestones remain pending.

## Live ledger

API fixtures and historical observations never fill fresh UI milestone rows.
Expected failures, exact identities, separate visible/pixel evidence, focused
checks and remaining subcontrols are appended as exercised below.

### First current checkpoints

| Subcase | Action → visible observation / identity | Qualification |
|---|---|---|
| E01 Brief/new project | Actual Create blank/title/synopsis/drama/live-action/10s/one choice/two endings/four nodes/two options/zero joins/one shot, Save→Source. New project `b3a933f7-b6fc-40e3-826f-5162f95a119a`; offscreen adult Lin, one room/one copper signal lamp, three5s pictures, two10s routes. | LIVE_UI_ISOLATED PASS for named inputs, other preset/custom states pending |
| E02 source/settings/prepare | Actual source Confirm→r1; QA-local text/image chat fields saved/Close; Outline Prepare→`ch_c1ced9e72a55423995ad84a821dfb3eb`, source1/outline0 frozen. Modal Save did not close by contract; premature underlying click was correctly intercepted, then explicit Close. | LIVE_UI_ISOLATED PASS, no normal settings mutation |
| E02 dispatch/admission/report/accept | Send once14:17:27UTC; native turn `01a116b9-f6ca-7d33-b925-595d40ec43b9` completed168855ms. Existing automatic checks admitted actual delivery; full report read before explicit Confirm14:24:26. Three organization records, one offscreenrole/room/prop,14/14; east/west mutually exclusive and no new quality/same-person claims. | LIVE_UI_ISOLATED/LIVE_PROVIDER PASS; screenshot04 directly inspected1700×900 |
| E21 fresh idle restart | Prepared unsent Outline/source retained across owned8861 restart before send; reload recovered same project/candidate, no duplicate. | LIVE_UI_ISOLATED/READBACK PASS for this idle restart only |
| E09 provenance original repair | Old8851 exact process20595 stopped only after zero inflight/all12receipts completed; same root/backend/static restarted13855. Original S01 asset `684e1485-a8e5-4344-ac6a-74ab31856c54`, candidate `a6e48087-1a8c-4a73-880f-943f1b9bf968`, originalij69ef…/hash e7d084… now visible source `art_reference_proposal`, rights `unknown`,1672×941. Actual existing Check retained unselected Use button/same image. | LIVE_UI_ISOLATED PASS for original action; screenshots02/03 directly reviewed1700×900/1280×768, manager independently corroborated; fresh native galleries still pending |
| E09 neighboring archived Art Copy | Ordinary original report first Copy click left label复制/data-done null; expected sandbox script-block error, no write/selection. Pinned renderer requires JS for copy/export/inner zoom, native prompt details work. | LIVE_UI_ISOLATED FAIL before repair; subsequent corrected original PASS below |
| E02 revision/cancel/retained Outline | After accepting r1, ordinary reopen/Close and reopen/Escape, Start revision→Prepare `ch_27e1387d11484596b1ddc9298a4c6fa8` unsent→Cancel→Return retained accepted Outline r1. | LIVE_UI_ISOLATED PASS; timeline/detail/export subcontrols still pending |
| E03 native branch task | Prepare `ch_c2912042416b4c3d9c2e344717b6722f`→Send once; visible sent/automatic delivery checks. | LIVE_UI_ISOLATED PASS for dispatch, actual admission/review pending |
| E03 branch review/adopt/Confirm/Apply | Actual returned four-node/two-ending candidate fully read, then Bring into editable draft→Confirm saved→separate Apply. UI shows story route r1/current and two complete east/west routes. Native branch task receipt completed normally. | LIVE_UI_ISOLATED/LIVE_PROVIDER PASS for named actions; richer structure pending |
| E09 corrected original static Art | Corrected owned8851 runtime27688 activated only while zero inflight/all12 receipts completed. Six prompt details initially open; actual first summary closes then reopens. Copy/export hidden; old report has no embedded image/zoom (NOT EXERCISED there). Modal Close→reopen, Escape→opener focus. | LIVE_UI_ISOLATED PASS;05/06 directly inspected1280×768/1700×900 and manager independently inspected. Gallery-owned zoom remains separate/pending |
| E09 immutable Art report | Default API exactly equals stored HTML; static view distinct. Stored SHA256 `437b31ad3fc0155da6133b9d9acb65e7d631881a1316c1467c0f3e83a5e79885` retained before/after actual reading. | READBACK PASS, no evidence rewrite |
| E02 Outline subcontrols | Retained accepted report ordinary 明细表 shows table, 时间轴 hides it. Export JSON click produces no download; actual browser warning identifies absent allow-downloads grant. ADR0086 explicitly keeps downloads restricted while allowing original export control visible. | LIVE_UI_ISOLATED PASS for tabs; export BLOCKED_BY_DESIGN, no download success or permission relaxation claimed |
| E07 cast dispatch hidden/reopened | Create character proposal→Send once→navigate to retained Outline→return Characters while native task continues. | LIVE_UI_ISOLATED PASS for dispatch/navigation; delivery/review pending |

Current exact browser screenshots: `output/playwright/full-creator-2026-10-07/`.
Screenshot01 records first Outline sent;04 loaded candidate report.02/03 repaired
original details inspected for readability, no horizontal overflow or occlusion.
All current media/creative-quality acceptance remains excluded.

### Subsequent partial checkpoints

- Cast `ch_e4e2200ffa35409e8896beae762992ff`: initial native turn
  `01a116cb-82fc-77b2-966b-24286e2aa589` failed at capacity after16.8s, with no
  delivery. UI Check truthfully retained queued/waiting-delivery; it does not
  project native execution failure. Independent read-only assessment confirms an
  external visibility boundary: receipts own queue/package/delivery state and
  text UI warns acknowledgment is not execution. No failed app transition or
  running/healthy claim is demonstrated; no reconciliation feature is introduced.
  Human explicitly authorized
  one same-frozen-job continuation; manager sent it without model/settings/job or
  lease changes. Turn `01a116d6-6dec-7cd1-bcf7-10dc488d849a` completed148729ms;
  ordinary automatic checks admitted the same Cast candidate. All fields reviewed,
  acceptance still pending corrected static-reader retest.
- Cast style boundary: F2 pinned realistic means half-painted, unlike Brief
  live-action. Explicit functional QA acknowledges this offscreen independent
  character-design proposal only, not same appearance, Brief-style or creative
  acceptance. F3's frozen live-action art-style contract must own actual film Art
  and keyframes; no inherited Cast default, silent mapping or frozen-job rewrite.
- Original Script `ch_ff461edee55e430c8a95205348f65b72`: static host/all five
  sections visible; stored/default HTML SHA256
  `0007445bc8968ff5b4b1d826e1b93552365ca35ec4d3ea6548b73ee18bf20d62`
  unchanged. Screenshot07 is1700×900 top/summary pixels, not long-scene pixel proof.
- Original Storyboard `ch_94df04816baf423c9bfc80e66da749eb`: actual Show-all
  stayed max-height760px, Copy inert. Screenshot08 preserves pre-repair failure.
  Fresh Cast Copy/Expand/Search inert under empty sandbox; screenshot09 filename
  says1280 but measured pixels are1700×900. Manager directly reviewed07/08/09.
- Structural QA project `0eabd058-b8a6-4ad1-8764-d2bbf11155be`: actual fresh
  Brief two choices/three endings/max-three-options/one join, nine-node planner
  seed, all nine titles/summaries edited. Added123 `graph-96dc7984a15d401eaeb54322`
  with first-choice→123→join; added222 `graph-d67bfb0c52f64816885650b7`
  explicitly unconnected; inserted333 `graph-509b1cdcda1540a5aa8343ef` after123,
  preserving original edge identity. Actual reconnection previews exercised;
  required bypass/delete/undo sequence remains in progress, not full E05 PASS.
- Original gallery-owned image zoom opens1672×941 asset, Escape closes and
  restores opener focus. Separate from report-inner zoom, which is disabled.
- Outline export warning is expected C01 sandbox policy evidence, not successful
  download. C08 actual OS blur is NOT EXERCISED; DOM focus cannot qualify OS focus.

Latest focused checks: provenance34PASS/8.72s includes deterministic earliest
created-at/ID tie regressions; manager independently34PASS/7.33s. Static parser/API
16PASS/0.71s, genuine pinned Storyboard1PASS/10.1s and Cast four-role1PASS/4.4s,
e2e typecheck PASS. Manager independently combined parser/API/provenance50PASS/7.89s.
These do not qualify native multi-role delivery or fresh images. Storyboard fixture
first image-branch attempt failed because close/reopen does not remount the frame;
reload established the intended intercepted image transport. No product contract
or CSP was weakened.

Independent Cast review found a desktop static-layout omission: pinned `.side`
retained a viewport-fixed height after switching the shell to linear reading,
allowing long synopsis overflow into main content. Static CSS now resets owned
height to auto. The first guard checked sidebar-box bottom but did not measure
overflowed content and was insufficient. The final genuine pinned long-synopsis
fixture at an iframe wider than1080px measures actual synopsis/footer content
bottom against main top: the old fixed-height counterfactual must overlap, and
the restored static auto-height must not. This is presentation
ownership, not a host-viewport workaround. Earlier broad snapshot gates require
rerun against this repaired candidate.
Corrected live wide-frame height is183.289px, sidebar bottom243.289 before
main top254.289 (1360px iframe), independently corroborated. Reviewer then
observed pinned graph's residual hover/click instruction despite inert canvas:
static visibility contract must suppress exact `.graph-h .hint`, not leave a
scripted-action promise. Fixture asserts hidden; archived text remains retained.

Execution-prerequisite sequencing failure: Character image native turn
`01a116e9-924d-7e41-af31-9ad80d13a5ab` stopped at pin preflight because
`src/plotloom/api/project_folder_art.py` was uncommitted. No image/completion/pin
was created. The local exported/waiting state is not execution evidence. Preserve
`ij_5be49304cccb4b1bbbc215f08b2f75cd` and its frozen request/reservation; no
resend, replacement or bypass. Obtain stable independent review/full gates and
explicit local-commit-only authorization, then separately authorized same-task
continuation. Art live-action task is prepared but remains unsent. This is run
sequencing, not a product bug; permanent checklist now carries the pre-native
committed-checkpoint prerequisite.

Current executable checkpoint gates (not full fresh E2E acceptance): final Cast
content-overflow/hint fixture1PASS/4.7s, parser/API16PASS/0.65s, lock check/API F401
lint/compileall/diff check exit0, deterministic build PASS (existing chunk warning),
wheel build and installed-wheel smoke PASS. Wheel SHA256
`0c26b842d7468cd2e1804bf1e2e77695cf1521514ac276e99c7adb92f39ea3c5`;
static JS `cfa42149a62261642ad534c0856e04f9f9065ac3e97c50f4edc5ea1b4b695cce`.
Independent initial 1,214 Python/552 frontend passed, but executable source changed
during that run: diagnostic only. Independent final frozen-v2 rerun: 1,214 Python
tests PASS in 415.45s; 552 frontend tests across 77 files PASS; both typechecks,
lock/API F401/diff checks PASS. Source fingerprint before/after
`b997431e4172ee12343485013799859a293d2b4adf6e53e72a1f63f2980a3d61`,
tracked diff fingerprint `7a9b211820ccf9d15b7098ffad726a975974b85f3c3a4f00a444fc5e87e5ec17`.
Independent source review closed and protected owner checkpoint matches baseline.
Full 202 fixture browser suite PASS in20.6m, exit0. No local commit yet. Saved
gate receipt: `output/playwright/full-creator-2026-10-07/execution-checkpoint-receipt.md`;
stdout was terminal session17682, not a separate full transcript. Playwright
artifacts are `frontend/test-results/`. Real QA browser writes were paused during
suite; these fixture gates do not fill fresh native E01–E22 rows.

Live structural additions: decision/join/ending only-delete previews enumerate
exact affected endpoints, ordinary Cancel preserves node, Confirm detaches it,
Undo restores node and downstream content. Required333 bypass and only-delete
both confirmed/undone with original edge IDs restored; draft explicitly saved.
Unconnected-node deletion and full save/reopen/visual inventory remain pending.
Original Storyboard corrected live three blocks967/970/998px and full H3 prompts
623/644/687px have no max-height or inner overflow; controls hidden. Host ordinary
close/reopen retains named static frame. Screenshot13 directly inspected final
prompt/soundscape/music lines1700×900;12 is mid-prompt, not final-line proof.
Stored report SHA256 `c231d3e49f98401c905b746b46415cdba09d76aab442d2f91da59e8168b6c440`.
Fresh native Cast r1 explicitly confirmed only after static reader retest and
functional offscreen style acknowledgment. Its retained HTML current SHA256
`f9cab6fa8ab0f6f65d41b6bfe3bee60e00b15142c33f6eb9a128dfe25b1ef5e4`.
Multi-role/all-role/long-synopsis proof remains genuine pinned fixture, not this
one-role native delivery. Fresh Art explicitly prepared live-action and unsent.

Focused provenance31PASS/8.10s includes12 shared consumer tests for known/unknown/
absent/invalid declarations and absent assets. Script static endpoint1PASS;
strengthened actual-pinned long scene/cast/all-five-sections/independent script/
parent/network/onclick/edited-warning/archive-hash browser1PASS/5.1s. Adjacent
Script/owned HTML/JSON close/current Story7PASS/18.9s. Art parser/API2PASS/0.80s,
actual-pinned Art static browser PASS; corrected adjacent accepted-report copy/URL
assertions plus static test2PASS/9.3s. These are fixture checks, not fresh live Art/
Script acceptance or final gates. Fixture failed attempts are retained in terminal
outputs: confined delivery rejected an extra report-source fixture file; moving
the fixture outside the inbox fixed setup. A wrong expected final cast line was
corrected after inspecting actual orderedE03 last line. No validator was weakened.

Independent manager provenance corroboration: same31 tests PASS/7.14s; existing
Starlette/httpx deprecation warning only. Independent static review found a source
preservation defect: `splitlines` recognized CR/Unicode separators that HTMLParser
does not count, shifting start-tag offsets. Corrected to LF-only offsets with exact
source-slice assertion, preserving unrelated text rather than tolerating mismatch.
Six CR/CRLF/U+2028/U+2029/VT/FF regressions plus parser/API8PASS/0.74s; actual-pinned
Art browser rerun1PASS/4.1s. Live Art will be retested only after corrected activation.
The subsequent corrected original live retest is recorded above. Independent manager
parser/API8PASS/0.59s and independent presentation review closed the offset blocker;
no source/security blocker remains for this component. Browser fixtures and live
pixel/control evidence remain distinct from the not-yet-complete full journey.
