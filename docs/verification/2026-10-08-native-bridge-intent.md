# Native Codex intent qualification

Status: implementation and full local software qualification complete;
real native acceptance remains in progress. Normal 8841 has not been changed.
This checkpoint extends the existing Create → Revise → Recover run, not its scope.

## Implemented contract

Candidate `33b3b7a`, followed by dispatch repair `ecfdd30`, implements
[ADR0140](../adr/0140-native-bridge-intent-candidates.md). Native intent uses the
existing specialist registry with explicit native provenance, frozen proposal
and replacement-target identities, strict complete suggestions and an inert,
deterministically derived report. It neither fabricates an API profile nor
falls back to an API provider. Historical pre-pin recovery code was removed;
current stored pins and terminal reconciliation remain.

Generated suggestions remain unreviewed. Qualification exposed a shared API
and native review bypass: installation rejected only pending intent, allowing
model-suggested intent. Both transports now require explicit whole-package
author saving before installation, independently of presentation review.

Independent review found one P2: a package prepared on an earlier source
revision could still be sent after the checkout changed. The specialist would
correctly stop, leaving its reservation unresolved. Send now checks clean
current execution authority against the stored pin before package publication,
reservation or dispatch marking. It never replaces the frozen pin. The reviewer
confirmed the repair. Regression snapshots recursively cover nested input files;
an initial directory-as-file test error was corrected before the passing rerun.

## Executed checks

- 139 focused backend tests passed on the initial implementation.
- 21 native tests passed after the dispatch repair, including dirty source and
  revision, contract and skill drift; no queue or reservation on refusal.
- 74 focused frontend tests and both typechecks passed. The full frontend suite
  then passed all 819 tests. Existing React test warnings remain visible.
- Real clean-source pin preflight passed after each native implementation commit.
- Two deterministic builds matched before the subsequent page-neutral copy edit.
- Independent review found no other blocking issue in currentness, review,
  late delivery, report binding or transport isolation. This is not a native send.
- Final unfiltered browser qualification on `0ce6806` passed all 240 tests in
  6.7 minutes. The final frontend suite passed all 819 tests after the copy edit.
- The initial full backend run passed 1,363 tests and failed one strict API
  response assertion that omitted the two newly implemented native capability
  fields. That assertion now checks both fields explicitly; no production
  response or guard was changed. Seven unchanged F5A tests moved out of the
  oversized Art module into a 200-line storyboard-review module. Independent
  review found no lost coverage. All 38 Art, storyboard-review and native-intent
  tests pass after this correction (100.98 seconds). The final full backend
  rerun passed all 1,368 tests in 634.06 seconds, with one existing Starlette
  deprecation warning. Its complete output is retained in
  `output/playwright/native-intent-2026-10-08/final-backend-gate.log`.

## Browser lifecycle test correction

The first unfiltered browser pass finished with 239 passes and one failure.
The Art test cancelled a prepared publication, then used a separate API client
to close the project while the browser's specialist-status GET still held a
shared lease. The trace shows that read spanning 23:26:21.395–.496 UTC and the
exclusive close arriving at .492. The server correctly refused with
`project_busy: another local writer is active`.

The test now uses visible Save-and-close and directory Reopen, exercising the
requesting client's read barrier from ADR0124. No lease, timeout or refusal was
weakened. The exact test passed three consecutive runs. Its unchanged fixture
helpers moved into a cohesive module, reducing the 628-line test file below
500 lines; all nine tests in the Art file also pass. The initial failure trace is
retained under `output/playwright/native-intent-2026-10-08/initial-art-close-race`.

The current wheel built and passed installed smoke outside the source checkout.
Both typechecks, lock check and API F401 lint also pass. A fresh deterministic
build on `3409c03` leaves checked static unchanged, including JavaScript SHA256
`b598c9a273550e72ac192ea93b4e1b87dd60c6049687da190d61daa61da086d5`.
All 47 creator-workbench service tests pass using the documented
`uv run --locked python -m pytest` invocation (11.42 seconds). An initial direct
`pytest` invocation could not import the root `tests` package during collection;
the documented invocation resolves the path without a code or environment patch.

## Bible read and wording audit

Artifact `204-bible-read-recovery.json` in
`output/playwright/full-lifecycle-2026-10-07/` records browser-only initial Bible
503 and named Retry on retained native project
`b3a933f7-b6fc-40e3-826f-5162f95a119a`. All six failure/recovery frames were
inspected at 1700×900, 1280×768 and 1280×460. The exact URL and 16,237-character
stages response were preserved with zero non-read requests. Interception was
removed after the check. This covers initial read/recovery, not every Bible state.

The shared unavailable panel incorrectly mentioned a shot position on this
non-shot page. It now says “当前链接与页面位置仍保留”, with unchanged read-only
Retry semantics. All ten availability tests pass; the updated bundle was rebuilt.
The final-candidate recheck below qualifies the corrected copy separately.

On `3409c03`, the fresh disposable project below now supplies six directly
inspected failure/recovery viewports at all three supported sizes. A browser-only
503 affects only its initial stages GET; removing the fault and clicking
“重新读取项目” restores the same Bible URL and exact stages response, with zero
non-read requests. The corrected page-neutral explanation and both actions are
readable. Independent screenshot review found no blocker. The short failure
frame retains prior scroll, so it qualifies the visible banner, explanation and
actions, not the offscreen heading. Recovered fields are genuinely empty because
this new project has no installed Bible; content preservation rests on exact
readback, not the blank screenshot.

The six files are `bible-read-{failure,recovered}-{1700x900,1280x768,1280x460}.png`
under `output/playwright/native-intent-2026-10-08/`. The two earlier
`source-confirmed-1700.png` and `source-ready-1700.png` instead show the saved
specialist-settings dialog, not the Source page. A backdrop-centre click was
intercepted by that dialog; its actual visible Close button worked normally.
`source-visible-1700.png` then records the Source page at its retained lower
scroll. Those naming/method limits are not relabelled as Source-top coverage.

## Remaining acceptance

Use a fresh current-schema disposable project and a clean committed execution
checkout. Complete actual native intent prepare/send/check/report/review, then
the remaining within-node media and same-completed-project revision journey.
Do not copy historical approvals into a new baseline or equate fixture playback
with native delivery. The whole-product state matrix and artistic-quality
exclusion remain as defined by the current run profile.

## Fresh native walkthrough setup

The isolated service on 8865/8866 loads the `0ce6806` implementation with its
matching checked UI; normal 8841 remains unchanged. The UI-created disposable
project `90c0f895-48de-4b57-8725-4b6f72797633`, “QA 原生重建·渡口信号”, has
a saved Brief and confirmed source. It uses one visible character, one location,
one two-way signal prop, two endings and a two-shot opening: four planned
five-second shots and a fifteen-second complete route. This deliberately covers
within-node advancement as well as route selection; the requested durations are
targets to verify against later delivery, not delivered-media claims.

The isolated installation's settings now point to the existing text and image
specialist chats. No model, normal-service setting or protected credential was
changed. No generation was sent during setup. Complete broad qualification and
verify clean execution authority before preparing and sending native jobs.

The last normal-service check had no active specialist tasks. Wind's 17 managed
files, Rain's 67 and three protected configuration files still match aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.

## Second keyframe and opening preview

At02:23 UTC on October9 the same image-specialist turn completed job
`ij_5c53936182fd4f6bbcbad469b50d568e`; automatic ingestion exposed candidate
`4b231ff7-2f73-4d15-b570-11cc66c40c8a`. Root inspected the full1672×941 image
and frozen C01 reference, saved intent `f1f9127f-a0ab-469d-a0fe-defe84298abb` r1,
selected keyframe `fbe3a07d-62fd-4e68-93fe-1f0e1869c816`, and recorded Codex-only
review `de43812d-f4e1-4351-996e-fda2a61c5e35`. No owner creative approval is implied.

The opening's two reviewed keyframes created preview
`8c7aeccc-d8a1-496b-808e-1f4e448dd6e3`. Previous/next and play/pause worked;
root inspected first/second images in the1700×900 browser. Both have5000ms
timing and remain current. Captures `two-shot-still-preview.png` and
`two-shot-still-preview-second.png` are in the evidence directory above.
This verifies a same-node multishot static preview, not complete video playback.

After reading all current sources and the complete compiled prompt, root prepared
and submitted the second H3 job once at02:29:49 UTC:
`vj_bb2e716216f84abeacb3505263f68a1d`, provider
`h3_b97a971fa5e540f1afb8b6f6a0d8cb1d`, request hash
`91f8cef4abdaba18b30a986734ff23741fc97c642b36141f99c20ee05458ed38`.
It requests quality8,960×544,5seconds/124frames,contain-pad,seed2664258457478185,
without an endframe. This checkpoint records submission only.

## Image task status repair

Both delivered image cards still enabled Send and retained stale waiting feedback.
The server already requires `prepared` at native dispatch, so this was a frontend
state mismatch, not missing dispatch safety. The UI now enables sending only for
a current prepared job with known media state; terminal persisted states supersede
transient action notices. Refresh and cancellation semantics remain unchanged.
In particular, cancellation is not proof that a specialist stopped and must not
clear its reservation. Candidate delivery does not imply selection.

Focused9 and full829 frontend tests, typecheck, deterministic build and independent
read-only review passed. Review found no issues. Normal8841 and protected data are
unchanged; full E2E qualification, revised playback and remaining visual/copy checks
are still outstanding.

## Opening completion and ending media

The second opening H3 result was ingested and explicitly trimmed to frames0–120
as segment `9f476f00-9c07-4cc8-922f-0c52ad46e42c`. Browser playback ended at5seconds,
120 rendered frames,zero drops and no media error, with audio enabled. Technical
QA selection retains the content defect: both red lights activate although the
source says neither route is activated. This is not creative approval.

East image `ij_f4340a885f4b4f74a0b3cb84fe29f6be` delivered asset
`e52f3c17-ec59-43a5-8da8-7593d8db1d84`, original SHA256
`eff6e69c86d476bc9e7c15ed5b81bd5d4d2bee559beb3fc11cb721ae52ce8a94`.
Root viewed the complete image and frozen C01 portrait, then explicitly saved
intent, keyframe selection and Codex identity review. Warm lamp tint and uncertain
prop continuity remain declared limitations. H3 job
`vj_0e0bbcfbe8c543a6bbb1fc4c37f861c9` was submitted once at02:43:15 UTC October9,
provider `h3_dba5533df48247d6a18320126e9328c0`, request hash
`279e98277f175b7bed83b32197fe6ef46ca4439dcacbd2d96c7468ba689322b7`.
Its H.264/AAC960×544 original has124frames at24fps and5.167seconds. Segment
`18b4f21b-9575-4f0d-b860-618c9d6cbc06` played to actual ended at5seconds,
120frames,zero drops,no media error and audio enabled before explicit technical
selection. Early/late pixels show left lamp on,right off and leftward confirmation.
A metrics serializer initially called unsupported `VideoPlaybackQuality.toJSON`;
direct field readback then verified the already-completed playback, without replay.

West image `ij_1dfc7f700d7748e29eb486bd5c6cc3d0` completed and ingested asset
`f82f92b1-dd6b-43e0-baf1-50f4c888f591`, original SHA256
`179a42ce914ae4f33d2cb873f586b6b8282a3aca0f930e727faf42d1f1f9d8b9`.
Full image inspection,explicit intent/keyframe and Codex reference review passed
for functional testing, retaining warm tint and prop-continuity limitations.
After reading each source and the complete compiled prompt, root submitted once
at02:52:49 UTC H3 job `vj_c7001760815844ca9887c134c7355e7f`, provider
`h3_65448b6752d744a8b78b72d667be170c`, request hash
`135ab62e504687e8b09d8385008e1591fad40cd5a5dcc52eaf2cf0f82a4e35ba`.
Both ending requests use quality8,960×544,5seconds/124frames,contain-pad and no
endframe. A subsequent UI result check ingested West without a second submission.
Segment `948f8c41-b014-4d8a-a0d2-575354a67d96` retains frames0–120,
SHA256 `b8e0a9d5bc953ba7ed6a3c0cde3dd6d9e3986b42612c68500473476cdd9b9bf8`,
120frames at24fps and160000 audio samples at32000Hz without padding.
Actual browser playback reached ended at5seconds with120 rendered frames,
zero drops and no media error. First/last pixels show right lamp on,left off
and rightward confirmation. Root entered a technical-only review and explicitly
selected the segment; UI ACK and independent job readback both confirm selection.
Artistic quality, prop continuity and audio semantics remain unaccepted.

All four shots are now technically selected. Through the normal Play story link,
the opening advanced from shot1/2 to2/2, then paused at the route-only choice.
Choosing East played its selected segment to actual ended; Start over reset the
story and a second complete opening traversal led to West, also ended. Both
ending videos reported5seconds,120frames and zero drops. This proves both current
15second media routes, including same-node multishot, not revised production.
The initial new-tab viewport was2400×1906; opening screenshots are supplementary.
Choice and both ending viewport screenshots were directly inspected at1700×900.
Evidence: `west-video-early/late.png`, `route-opening-shot1/2.png`,
`route-choice-1700.png`, `route-east-ended-1700.png`, `route-west-ended-1700.png`.
The playback copy “单一路径完成后继续” is still awkward: it describes advancing
after the current segment's shots, not completing an entire story route. The
generic ending instruction “等待明确操作” also fails to name replay/restart.
These remain E22 wording findings, not a functional playback failure.
Same-project Revise and remaining recovery/audit coverage are still outstanding.

## Review evidence and request wording repairs

Native UI inspection found two owning defaults that misrepresented evidence:
`visibleJobs.length` was labelled generated original candidates even when jobs
were only prepared/submitted, and new identity comparisons prefilled positive
English observations. The header now counts video request records; new comparisons
require actual reviewer-entered identity/state notes, with Chinese placeholders.
Existing review validation and stored evidence are unchanged. Specialist check
timestamps now use the shared Chinese24-hour local-time formatter.

Focused24/full834 frontend tests,typecheck and deterministic build passed;
independent read-only review returned no findings. Live8865 pixels confirm the
request wording and the new empty observations/disabled review submission before
West review. The waiting-image card was directly inspected at1700×900,1280×768
and1280×460, with resend disabled and no document horizontal overflow at1280.
Evidence names include `west-image-waiting-*`, `video-request-wording-1700.png`,
`review-blank-observations-1700.png` and `east-video-early/late.png` in the native
evidence directory. These scoped checks are not a fresh full browser suite.
Protected data again matches aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.
Normal8841 remains unchanged; no active specialist checkpoint was edited.

## Native execution started

After the complete software gate, clean checkpoint `1b07652` passed fresh Outline
and native-intent pin preflight. The owned runtime's executable files remain
identical to its loaded `0ce6806` implementation. Both registries were idle before
dispatch; the text task's previous turn was completed. Its model and effort were
left unchanged and are not independently identified by this run.

The UI prepared and sent Outline `ch_442ef84357df48248fb96ac23da5b289` once.
The native task actually executed and completed in 107 seconds. Automatic
checking loaded its candidate, and the visible report opened successfully.
Source, topology, one-character/location/prop scope and the 10-second opening
plus alternative 5-second endings were reviewed before explicit QA confirmation
of Outline r1. This is functional test admission, not artistic acceptance.
Manifest SHA256 is
`c7874031ffa7d22a6e371a5a01c0a7e74945a2f76657f9ca80681559478644c2`.

The original Outline report still displays the long fractional-minute scalar.
Its unequal-section limitation is disclosed in the candidate and report; the
existing formatter defect remains open. `outline-report-native-top.png` records
the inspected original, without rewriting its bytes or treating it as a visual
pass. All images here are under `output/playwright/native-intent-2026-10-08/`.

Three `outline-waiting-{1700x900,1280x768,1280x460}.png` frames were inspected by
root and independently reviewed. Waiting status, timestamp, named Check and
queue/cancellation explanations are readable without page-width overflow. The
short viewport is intentionally scrolled to the task region; it does not qualify
the offscreen heading. The 768-high view requires scrolling to cancellation and
manual instructions, which the short scrolled capture shows. No cancellation or
duplicate send was used for these reading checks.

The UI then prepared and sent branch job
`ch_ba8c9bfc32244a5392535236752d2d44` once, using the same text specialist and
confirmed Outline. The task completed in 68 seconds. After reading its candidate,
the UI brought it into the editable draft, confirmed map r1 and applied graph r1.
Map hash is `3962785214e80c682eb0871be41547fd9d21d3f0a7265e9b95fa167142f151c1`;
graph hash is `71b25820f0ee119c47525c82d519915a1330864bb1441dd8be774c0096156239`.
The four-node graph preserves the opening, choice and two alternative endings.
`creator-admitted-baseline.png` qualifies the visible top, not offscreen endings.

The accepted Outline report reopened during branch execution at all three desktop
sizes. The `outline-accepted-reopen-*` frames show accessible report and Close
controls, but retain the fractional-minute defect. `outline-accepted-risks.png`
captured the report top rather than the intended risk region; it does not prove
risk-region pixels. Candidate risk text was separately read in full.

Branch summaries and consequences contain `continuation`, `route_only`,
`authored footage` and frozen node IDs. Independent read-only review traced this
to missing prose-purpose guidance in the schema, brief and specialist contract,
not the renderer: routing already has dedicated exact-ID fields. This is an open
wording defect. Its bounded repair belongs in those generation contracts, with
exact-identity leakage regression coverage and a fresh delivery; never sanitize
or rewrite retained candidate evidence. Structural admission is not wording PASS.

## Character delivery and explicit style correction

Native Cast `ch_4bbc112b931a437db9351b1f78cc6579` completed in 111 seconds.
Its one-character candidate preserves C01, source evidence and all four section
contexts. Candidate SHA256 is
`8fb14bf4633771e7ca92e54b91ee2ad04b7c98029e6062b1f5adf97c6310ed11`.
The specialist correctly disclosed that its pinned `realistic` preset mandates
painterly directions despite this project's live-action setting. This repeats
the explicitly retained Cast limitation in ADR0061, not an image-rendering error.

For this disposable functional test, the visible Cast editor changed image style,
positive/local/sheet prompts, negative prompt and tags to live-action photography,
then appended the exact correction and QA boundary to source notes. Identity,
appearance, evidence and performance constraints were untouched. Explicit UI
confirmation saved Cast r1, hash
`2d5f9b303fddccfc95e4f8562d491dd39916679f3df20904a7f23994e10a51ca`,
with C01 mapped to C01. Original candidate/report/manifest remain unchanged.
This exercises the supported author-edit path; it does not close the generation
preset mismatch or establish artistic acceptance. Before any generation-contract
repair, revise ADR0061's retained preset decision and align request, schema,
specialist and admission ownership; do not defer contradiction to an image overlay.

`cast-original-report-top.png` shows the original static report heading and summary
below technical details, not its complete body. Sandbox script-block console
messages come from this intentionally inert report; confirmation itself succeeded.

## Native reference images and route timing repair

Character job `ij_caafe18ccc244a729b997111e0b0e5cd` delivered and was explicitly
selected through the UI. A second candidate, `ij_01462fa06c4447ebb6628eaefabde564`,
was ingested and added to the comparison without replacing the first selection.
`character-pair-1700x900.png` records the visible comparison, not the complete
offscreen image height. Native Art `ch_7684f4aba6e24d04b65d63375b2730d3` was
confirmed as r1 with one environment and one prop.

Environment `ij_db7e9b0172b640b5a64949fcfc1a0e77` and prop
`ij_9fadb361a12d4d4a97f18c3f33fca42d` both executed in the image specialist,
were ingested with the named Check control, enlarged, closed and explicitly
selected in their respective UI subjects. Root inspected
`environment-reference-zoom.png` and `prop-reference-zoom.png`: image and Close
control fit the 1700×900 viewport. Prop asset
`1ab2b9e1-4a55-4164-bc16-7baab0ba2ae0` has hash
`d1d3d78f84ad6d870e50df4ed3e61a61fc09f180205a75900703096632b8dbfc`.
Its expanded provenance shows `art_reference_proposal` and rights `unknown`.
These are functional reference-review checks, not artistic acceptance or proof
that environment/prop references feed shot production; the UI explicitly says
they do not. Refused cleanup of non-private ImageGen staging preserved files.

Script `ch_5d705d357d554294bafcdd676874cb46` stopped without delivery: the frozen
package imposed 7.5-second section caps while accepted author content required
a 10-second opening and either five-second ending. The target route is 15
seconds, so the author request is feasible. Root cause was reuse of Scene Beats'
equal-depth generation allocation as a universal authored-scene admission cap;
canonical installation repeated the same restriction.

ADR0018/0064 now distinguish generation allocation from authored route budgets.
F4/F5 bind a versioned route hash, ordered section mapping, route-only membership
and complete routes, with no section-cap compatibility reader. F4 validates
targets and estimates; F5 validates cuts; canonical installation uses longest
DAG-route duration. A real fixture admission test carries unequal 10/5/5-second
episodes through pinned upstream validation, F5, intent/presentation review and
canonical installation, while overlong routes remain rejected atomically.

Independent review found and closed one additional gap: identical SQL layouts
could hide obsolete review JSON. Read-only folder and recovery admission now
validate all retained F4/F5 candidate/revision bindings before mutation. Eight
open/closed cases prove current contracts admit and obsolete bindings refuse
open, inspect, reopen and recovery with unchanged database/manifest bytes.

The repair passed 1,382 backend tests, 819 frontend tests and all 240 browser
tests, plus types, deterministic build, lock, focused F401 lint and installed-wheel
smoke. Logs are `route-budget-{backend,frontend,browser}-gate.log` under the same
evidence directory. A removed unused import was the only lint correction.
Independent review found no remaining concrete timing/admission blocker.

The old Script request was cancelled through the UI; no Script revision exists.
Its specialist turn is independently confirmed completed, but the application
reservation remains held because no delivery was produced. Exact terminal
settlement and the disposable obsolete-row reset remain cutover work; no frozen
package has been rewritten. A pending poll returned 404 after cancellation;
this is retained recovery evidence, not a claim of a clean cancellation console.
Native Script on the repaired runtime and all downstream same-project production
remain unverified. Normal 8841 is unchanged; the owner/protected aggregate still
matches `df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.

## Qualified isolated cutover and fresh Script

Timing repair is committed at `c032320`. Preflight also found that ordinary
creative dispatch named only a relative specialist skill, although the reused
chat belongs to an older checkout. `e7bb564` names the runtime's absolute checkout
and skill for every creative stage, matching native intent's existing behavior.
All 42 focused specialist/isolated-launcher tests and independent review passed;
the broader results above belong to the preceding timing candidate.

Both native tasks were rechecked as idle with their exact completed turns.
The isolated service was stopped before an explicit disposable reset. Existing
registry completion settled only the cancelled Script job, matching retained
task/project/stage identity and independently observed terminal turn
`01a11e09-2c35-7b41-81bd-fd0bda495990`. The transaction removed only that cancelled
candidate row after checking missing head/revision0 and no accepted Script.
All other database rows and all 79 retained project files were unchanged;
frozen package and execution pin remain. This operator reset is not a pass for
product-side recovery from a text task that returns no delivery.

The supported isolated launcher now serves executable `e7bb564` on 8865/8866
with its checked static assets and existing specialist bindings. Initial startup
refused the older configured H3 catalog v5; selecting current catalog v7 in this
process's environment enabled the existing trusted backend, without changing
the saved settings, gateway endpoint or credential. Health and empty specialist
reservations passed before dispatch. Normal 8841 remains unchanged.

At 21:27 Toronto the UI prepared and sent fresh Script
`ch_2675e62e41354f3590e38db251207f72` once. Its target is 15 seconds and frozen
route hash is `a1c1742c9d313c092a55c9df8e9b4d1741015b6c94c9cb0a2bbc48db7bfbc1b4`.
The UI shows queued/waiting; generation, delivery and downstream acceptance are
not established by that acknowledgement. Owner/protected hashes still match.

## Native Script accepted and storyboard dispatched

The fresh Script specialist turn `01a11e46-3533-7d61-b465-0ce6a1d8d607`
completed in 171 seconds. Plotloom ingested the delivery into a pending review;
root read the exact candidate and manifest, opened its JSON and static report,
then explicitly confirmed Script r1 through the UI at 21:40 Toronto. The visible
accepted hash begins `0d683c4b52d3`; original candidate SHA256 is
`3cc624183194deb111ff5994645ace84fc75aa26e4c7ca739f500cb8152a0999`.
The three footage sections retain targets and estimated durations 10/5/5 seconds,
C01/S01/P01, the opening's two actions and distinct left/east and right/west
endings. The route-only choice has no authored episode. This is provisional
functional QA acceptance, not generated-media timing or artistic acceptance.

Root inspected `script-report-top.png`, `script-report-content.png` and
`script-report-tail.png` at 1700×900. They show the archive heading, portions of
the chapter content and scene table after inner scrolling; they do not establish
complete middle/bottom pixel coverage. The report remains sandboxed. Its English
episodic labels and 20-second sum of mutually exclusive endings are retained
upstream output, not the actual 15-second playback route. The generation brief
says the UI explains these inapplicable metrics, but `StaticReportReader` only
explains disabled controls and original/current content: this disclosure gap
remains open. Do not rewrite the delivered report to hide it.

At 21:41–21:42 Toronto the named UI controls prepared and sent storyboard
`ch_84ff5f7d4ecc4ebbb8029b53672cec34` once, with the default 8-second cut ceiling.
The same specialist is executing turn `01a11e53-5492-7f50-9c95-b02e90e5e47f`;
it confirmed two opening cuts plus one per ending, each five seconds. Delivery,
admission and acceptance remain pending at this checkpoint.

The waiting panel also displayed `9:41:53 PM`. Root traced this to two remaining
`toLocaleTimeString()` calls in `SpecialistTaskActions`, unlike the explicit
Chinese 24-hour formatting elsewhere. This is an open E22 wording inconsistency,
not a task-clock or generation failure. No active package or runtime code was
changed during these observations.

## Native intent and production installation

Storyboard job `ch_84ff5f7d4ecc4ebbb8029b53672cec34` completed in 157 seconds,
was ingested and explicitly accepted through the UI at 21:45 Toronto. Its four
five-second cuts preserve the two opening actions and one cut for each ending.
Root inspected the JSON, report content and top viewport; artistic approval is
excluded. The accepted hash begins `88997139b329`.

Proposal r1 froze hash
`5cbcffbdb4c534f1b16c0c93cf336255924f327312f63815f198985d75e69510`.
Native Codex intent job `ch_21cda76dbf06423694413a85f3dc8ac4`, pinned to
`3493828`, completed turn `01a11e57-4c31-7bc0-ad2b-952481cef12b` in 69 seconds.
All seven source-bound suggestions were ingested into proposal r2 and read by
root. Explicit UI saving without text changes created r3; delivery alone did not
approve installation. Waiting-panel pixels were checked at 1700×900, 1280×768
and 1280×460. The original intent report has an overly narrow frame and technical
UUID headings; that visual/copy gap remains open.

At 21:53 root reviewed all eight presentation sources. The final “本路线结束。”
in each ending was split into a review-only fragment; the remaining action and
composition text stayed physical with its full limitations retained. Keyboard
selection did not move the caret in this session; exact DOM text selection plus
the normal split button exercised the product operation, not keyboard usability.
Explicit confirmation and save created proposal r4, followed by installation
through “确认投产提案”: three scenes, four shots, no generated or selected media.
Four primary beat mappings and the required quality checks were present before
the separate functional-only storyboard approval. The native intent task's
“尚未由作者确认” status persists after acceptance and needs correction.

## Production reference readiness repair

The first image preparation failed twice with HTTP422 `identity_reference_missing`;
the second attempt captured the response after the first exposed no visible
error at the scrolled form. No image job was created. The UI claimed C01's
reference was current, but that selection belonged to accepted Cast rather than
the installed Story Bible. ADR0061 deliberately separates these authorities;
server refusal was correct. The frontend incorrectly treated any current decision
as production-ready.

The shared production-reference selector now requires `story_bible` authority,
current decision/state and exact active-decision identity. Both the preparation
summary and image prerequisite consume it. Copy explains that an existing image
can be explicitly selected for production without generating another. No server
guard, context hash or reference decision is automatically changed.

Independent read-only review found no issues. Focused tests, typecheck, all 823
frontend tests and paired deterministic build passed. On isolated8865, reload
retained the image-direction draft and showed the Cast-only reference as not yet
selected for production; preparation was disabled. Root inspected
`production-reference-required.png` at 1700×900. Explicit UI selection of the
same asset `20bd88c5-8ed3-4205-805d-ce41637fac11` created reference r2 and changed
the summary to ready. Native preparation and delivery remain the next check.
Normal8841 is unchanged; this is not full E2E or narrow-screen acceptance.

## First keyframe and H3 submission

Image job `ij_00c0e50a39f34e4186f1118df492f9e7` completed and was automatically
ingested as candidate `6285d0b7-869b-46f4-8c60-826ed0c82b2c`. Root inspected the
complete 1672×941 image and its frozen character reference, then saved visual
intent r1, explicitly selected the keyframe and recorded Codex-only consistency
review `fbf80a9f-b54f-427b-ab7f-dee63ad34d77`. These are disposable functional
decisions, not owner artistic approval. The candidate was not automatically selected.

The H3 form correctly refused an aspect mismatch. Root explicitly chose quality8,
960×544 landscape, five seconds and contain-pad to preserve the full composition.
After reading each source, root entered English directions and reviewed the full
compiled prompt. Job `vj_35ea30f75dd344e5a055646de4b379bc` was prepared and submitted
once at 02:12:21 UTC on October9, with provider handle
`h3_d75954f59e3149bc9eca29be2fdd4f9f`. Its request hash is
`b6f0fa83c087e892b888e01be76c49c4a7ed075569e6a4a9b9339421e0187234`;
no endframe is used. At this checkpoint it is submitted, not delivered or selected.
The other three shots and both complete routes still require media.

## Report state and width repairs

The intent task's `ready` transport state incorrectly claimed the author had not
confirmed it, even after package saving and installation. It now states delivery
only and points to the current package review state; it does not infer approval
from transport completion. The report's grid used start alignment, shrinking the
details element. A scoped full-width rule repairs that container without changing
the retained report, URL or sandbox. App-owned Script and Storyboard guidance now
distinguishes sums across all branches from one complete playback route.

Focused10 and full825 frontend tests, types, deterministic build and diff checks
passed. Independent read-only review found no issues. Root viewed the live report
at1700×900 and1280×460: iframe widths1304 and884 respectively, matching their
containers; the short desktop document remained1280px wide. A1280×768 capture
and visible Script guidance were also collected. Evidence is under
`output/playwright/native-intent-2026-10-08/` in the main checkout. The changes are
isolated; no service restart or normal8841 deployment occurred.

Still open: technical report headings and English limitation text, mixed12-hour
task clocks, delivered image cards retaining a send control, and native media,
same-project Revise and remaining full-product coverage. No full E2E PASS is claimed.

At02:18–02:19 UTC the first H3 result was ingested: H.264/AAC,960×544,124frames
at24fps,5.167seconds. UI preparation created segment
`eb56d0bd-af21-4e0a-b5ce-0fc3ecba41b6`, frames0–120, with exactly5seconds and
160000 decoded audio samples at32000Hz. Actual browser playback reached its end
with120 rendered frames,zero dropped frames,no media error and audio enabled.
Root viewed early/late frames, then explicitly selected it for functional QA.
The review records the visible extra wiping cloth as a model fidelity defect;
audio semantics and artistic quality are not approved. Three shots still lack
selected media. Protected-owner/config aggregate remains
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.
