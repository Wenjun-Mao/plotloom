# Conflict and retained-draft recovery audit — 2026-10-08

Status: **PUBLISHED / SCOPED QUALIFICATION COMPLETE**. This bounded E22 checkpoint is part
of the [whole-product visual/text audit](2026-10-08-whole-product-ui-audit.md),
not completion of Create → Revise → Recover, all visual states or native media.
Artistic image/video acceptance remains owner/H3 scope.

## Root causes and bounded repairs

- The actual normal8841 disposable two-tab journey155 displayed both “已加载服务器版本”
  and an authority failure after a GET-only503. Conflict reload acknowledged before
  the aggregate read, whose void result conflated admission, failure and supersession.
  The loader now returns those outcomes separately; only an owned admitted read
  acknowledges reload and remounts the editor. Pending disables reload/copy/discard.
- Route epochs did not distinguish two same-route reads or late Resume callbacks.
  Exact unaborted read ownership now guards admission and continuation publication.
  Replacing a read invalidates its callbacks, not an already-sent execution request.
- Unknown authority could mount a second dialog over retained recovery/conflict.
  One authority dialog now takes precedence without dropping the conflict buffer;
  explicit successful retry reveals the retained workflow again.
- The157 journey measured an extra blur-triggered draft PUT409 during conflict
  reload. Every autosave entry now requires the current connected project and no
  known conflict;409 closes admission synchronously. No CAS relaxation or error
  suppression is added. Reload performs no writes or implicit draft merge.
- Unsafe discard removed storage but retained copyable conflict state. A regression
  reproduced resurrection before repair. Discard now invalidates the selected local
  record and its same-binding superseded workflow/editor references. Newer or
  unrelated records and acknowledged server drafts remain protected.
- Independent review found typing during a held save could produce an older conflict
  snapshot. Both failing unit cases were reproduced before repair. A409 now retains
  newest local typing; discard invalidates older snapshots of that selected lineage,
  while a changed selected record requires a fresh decision.
- Copy guidance exposed “连续阶段前缀” jargon and could imply confirmed content had
  changed when only a draft changed. It now names project content **or draft version**,
  explains required earlier content, and excludes original tasks, review decisions
  and media. Graph recovery remains a distinct same-project action.
- Final161 pixel review found discard-after lacked a clear acknowledgement of what
  was removed. A project-scoped status now names the selected tab-local buffer and
  preserved saved drafts/confirmed content without clearing the accurate read error.
  The165 short-desktop replay found this normal-flow status above the retained page
  scroll. Successful discard now reveals that status once; rerenders do not repeatedly
  scroll. Dismissal/navigation clear it, and a changed selected record cannot show success.

The durable contract is [ADR0133](../adr/0133-owned-project-read-acknowledgement.md).
The reusable E22 checklist now requires these recovery/admission/lineage checks.

## Executed evidence and exclusions

Artifacts are retained under `output/playwright/full-lifecycle-2026-10-07/`.

- 155: normal8841 real disposable conflict and GET-only failed reload; retained
  snapshot/YAML and root-inspected failed PNG establish the premature ACK/overlap.
- 156: added browser cases failed from an early creation-URL read and secondary-tab
  default viewport. Correct exact project/viewport setup; do not count those frames.
- 157: all three desktop cases reproduced the repeated blur PUT409. The write guard
  was retained, not weakened. Exact retained buffers passed before the guard failed.
- 158: five journeys passed; discard revalidation failed on a test-only incorrect
  dialog name. Fix to the actual “发现可恢复草稿”, not a product title change.
- 159: six journeys pass33.6s;160: six pass31.0s with held-save/newer typing.
- 161: wording candidate six pass31.5s. Conflict, pending, failed, retry-verified
  and loaded at1700×900,1280×768,1280×460 plus three short-desktop discard frames
  give18 PNGs. Independent GPT-6 Luna/Max directly inspected all18; root inspected
  eight final frames, including short pending/loaded/failed and discard sequence.
  Titles, explanations, controls and JSON scroll region fit; pending actions are
  disabled and loaded/copy remain distinct. The missing discard feedback above is
  a real text-state gap, not a visual PASS. Reverified recovery is the unchanged
  winning project draft, not the discarded losing buffer or unrelated local record.
- 162: intermediate full gate221PASS/3FAIL6.9m,872 inputs unchanged. Two failures
  stopped in Vite readiness before navigation. Trace identifies an unbounded HTTP
  fetch bypassing the nominal25s readiness deadline; outer45s fixture timeout lost
  process-output diagnostics. The helper now aborts each fetch at its remaining
  deadline and preserves last HTTP/error/process output. Budgets/workers/retries
  are unchanged; **actual Vite non-readiness cause remains unknown**.
  The third failure was a lifecycle test race: Delete exists before archive completes;
  visibility was not an archive receipt. Actual click landed during disabled directory
  refresh. Test now awaits exact archive response and settled archived projection.
- 163: fivePASS/oneFAIL; test wrongly expected the fault text alone instead of the
  full contextual read-error banner.165: fivePASS/oneFAIL; genuine off-screen feedback
  above the retained scroll, established from the actual second-tab trace pixels.
  The fixture's default failure screenshot belongs to the first tab, not that state.
- 164: exact archive/restore/permanent-delete journeyPASS3.9s,5.8s overall.
- 166: final sixPASS30.6s;18 PNGs independently directly inspected by GPT-6 Luna/Max,
  root inspected all three changed discard frames. Feedback and retained read error
  are both genuinely visible at1280×460 **without test-side scrolling**. All five
  recovery states remain readable at all three sizes; no remaining bounded copy/pixel
  finding. Winning durable draft remains distinct after reverification.

Genuine browser editing generates the conflict; only reads are faulted503. All
three reload cases measure zero writes and preserve original canonical content,
durable drafts and exact local input; deliberate Copy makes one POST with the
retained Brief title and no `initialStages`. Discard holds a real losing PUT while
newer text is entered, releases409, fails reload503, discards only that exact local
lineage, revalidates and preserves the winning durable draft/canonical objects.
An explicitly isolated unrelated local record remains unchanged. Those read/discard
operations send no API writes. No native provider generation or owner-data mutation.

## Qualification and next action

Final source review GPT-6.1 Sol/Medium is clean for loader, autosave, lineage,
feedback/reveal and diagnostic/test changes. Complete frontend713/96files,
application/E2E types, deterministic build, lock/API F401, archived prompt reader
and diff checks pass. Build chunk and color-env warnings remain visible.

Unfiltered167 passes all224 browser tests in6.5m on875 frozen
source/test/config/static inputs. The before/after SHA256 is identical:
`46bdd9f7834e72dd042316790624960f5d6bf3d5c1f1a0ebb46aefdcc34c1d45`.
Default4 workers and zero local retries are unchanged. Python1245 qualification is reused from
unchanged backend source/tests, not newly executed. The final installed-wheel smoke
passes for `/private/tmp/plotloom-recovery-qualification.GFBgWK/wheel-final/`, SHA256
`52059f7d2f66369aafb7a3615b7b98ff4625f34d942800d7fc9abb3bf50fd2cb`.
An intermediate unit run failed because jsdom lacks native scrolling; the explicit
test-only DOM harness observes the requested scroll while real-browser tests qualify
the viewport. A diagnostic status unit used a100ms real-network assumption; fake
clock/response observation now owns that status assertion, while the real stalled-socket
test still proves deadline abort. No production fallback or tolerance layer is added.

Before and after this gate, both owners and all three protected settings are exact:
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`
(Wind17/Rain67 files). Only the audit-owned creator-ui-recovery browser was closed;
QA evidence and user browsers remain. No service restart or settings write.

Normal8841 serves the final checked JavaScript bytes, SHA256
`c19cca37d6e26e2b6a000f1d6ea7947fe4060eb6b82460002945c1830398c08e`.
Base CSS remains `3b0c81ad3f5e2d92a455826ba114d269fedb3ddbf192ffed70c5381bbe1ea35d`;
product CSS remains `42beb639a4681beb6bea3a3b04916ee1eb63481a821eb42994f152de7e2d6850`.

Executable `8ea291aae6cc2089566c6cb49640e3afe225cb12` is pushed to `origin/main`;
normal8841 serves the exact checked assets without a service restart. The single
unfiltered [exact-head CI37769739148](https://github.com/Wenjun-Mao/plotloom/actions/runs/37769739148)
is running; remote success is not claimed. The prior published35cc75b CI37763010686
is successful; it is not this candidate's qualification.

Next: remaining Source/help/review-state pixels and native-media/lifecycle gaps in
the full audit register. This receipt closes only the bounded recovery slice.
Do not inherit final qualification from an earlier candidate or relabel failed runs.
