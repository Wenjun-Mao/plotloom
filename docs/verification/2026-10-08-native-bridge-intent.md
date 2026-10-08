# Native Codex intent qualification

Status: implementation and focused software checks complete; broad gates and
real native acceptance remain in progress. Normal 8841 has not been changed.
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
  tests pass after this correction (100.98 seconds). Final full backend
  qualification remains pending.

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
