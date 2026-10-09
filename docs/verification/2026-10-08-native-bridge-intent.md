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
