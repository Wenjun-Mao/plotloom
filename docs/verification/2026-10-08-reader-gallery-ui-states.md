# Reader, gallery, Bible and run reading states — 2026-10-08

Status: **SCOPED LOCAL QUALIFICATION PASSED; PUBLICATION PENDING**. Part of the
[whole-product visual/text audit](2026-10-08-whole-product-ui-audit.md) and current
full E2E run. It is not complete lifecycle, native generation or artistic acceptance.
Stable guardrails are in [ADR0132](../adr/0132-creator-ui-reading-boundaries.md)
and [E22](../creative-workflow/graph-workbench-acceptance.md#e22-全产品视觉与文案专门检查).

## Scope and root causes

Only disposable public-API fixtures and owned read failures were constructed.
No owner project/settings or native provider task was changed for these captures.
Actual server creative prose, exact errors and immutable reports remain intact.

| Failure | Root cause / durable repair |
|---|---|
| Missing reader Script/route looked like a failed request | Domain prerequisites shared a transport-error path. Typed prerequisite guidance links to the Creator/Script owner; actual read failures retain retry. |
| Optional Storyboard failure made reading unnecessarily dependent on it | Separate optional read state/effect; keep qualified Script and selected route, retry only Storyboard. Currentness, section mapping, hashes and sandbox remain strict. |
| Initial gallery read failure had no local recovery | Add named owned read-only retry; do not classify failed reads as empty images. |
| Failed gallery refresh discarded the visible draft/content | Retain the same subject component and local inputs; error disables mutations until a successful latest/session-owned read. |
| An overlapping read stranded retry disabled | Data-read ownership incorrectly owned manual pending state. Independent review found it; held observation → retry → newer failed read regression reproduced it. Separate retry-operation ownership releases pending without allowing stale data/error commits. |
| Empty gallery said 当前身份参考 beside 未选择 | Hero fallback assumed a selected reference. Use 尚无参考图片 only when no candidate/selection exists; real selected fallback stays unchanged. |
| Archived guidance invited prepare/send/selection | Gallery and adjacent Cast helper ignored read-only authority. Explain restrictions; no control/handler authority is relaxed and no new observation starts in read-only/error states. |
| Cast status/cancellation and Bible guidance exposed awkward abstractions | Say 角色设定需重新确认 / 正在编辑角色设定, explain cancellation's unchanged-binding condition, name人物/地点/道具 and type-specific unnamed cards. Creative content is not rewritten. |
| Run/attempt labels exposed enums and called an uncertain result a failure | One presentation map names each public status. Unknown attempt results remain uncertain even when their persisted status is failed; original payload/status/code remain inspectable. |
| Pending cancellation looked like a first cancellation | The server deliberately permits a repeat cancellation signal. Preserve that eligibility and say 再次请求取消 / 已请求取消，等待运行结束; this is not a retry or cancellation-contract change. |
| Failed-run explanation squeezed its badge and ID into fragmented text | Trace's stage selection, status and explanation incorrectly competed in one flex row. Give them separate owned rows, preserve wrapping evidence and test single-line status geometry. |
| Zero events still invited selecting an event | Detail-pane and progress helper independently ignored availability. Both now follow actual event count and retain truthful idle/retained/waiting guidance. |
| Repair guidance used technical abstractions or invented an execution source | Human explanations distinguish changed inputs from uncertain results. Keep exact refusal/outcome codes; no attempt means 执行来源未记录, not 首次执行. |
| An uncertain attempt still carried a 失败记录 tag | Event-kind classification checked failed status before outcome uncertainty. Classify it as a request/warning while preserving the original failed payload and outcome evidence. |
| Full timestamps overlapped stage/title | A fixed60px time column assumed short clock strings. Give the complete ISO timestamp its own row; assert timestamp-bottom ≤ content-top at all three desktop sizes. |
| Current repair lists retained a retired trace adapter | Current progress owns eligibility; remove the unused trace-to-quarantine adapter, historical test and deprecated raw fields. Do not invent demo repair eligibility or rewrite original evidence. |

## Direct viewport/state checks

Only 1700×900,1280×768,1280×460. Viewport capture waits for the intended state,
centers its complete target below fixed chrome, and requires12px bottom margin.
Ordinary scrolling is exercised; full-page capture alone is not evidence.

- Final137 reader21 PNGs: no-project, missing Script, reopened Script, stale Storyboard,
  initial fatal read, pending Storyboard, failed optional Storyboard at all sizes.
  Independent direct review of all21 finds readable guidance/actions.
- Final137 gallery12 PNGs: initial failed read, successfully confirmed Cast with no images,
  archived guidance at all sizes. Independent review found the empty-heading
  contradiction; final corrected hero and archived-helper pixels are recaptured.
- Final137 Bible21 PNGs: character/location/prop top and bottom at each size, plus archived
  character deep link. All independently inspected; root inspected representative
  short-desktop top/bottom/archived frames. Retained values, aligned labels and
  lower fields are readable. English state/prose values are authored fixture data.
- Trace/repair42 PNGs in137: idle, retained failure, zero-detail, pending cancel,
  separate cancellation action and Professional Inspector; changed-input refusal
  and uncertain-result list/explanation/rebuild. Independent direct review of all42
  found no clipping, overflow or inaccessible captured controls but caught the
  residual zero-event progress helper. It was corrected, along with pending-event
  tone and the unknown-result rebuild warning. All45 recaptured frames in140
  were independently inspected; the new running/key-blocked state exposed the
  timestamp collision. Final141 re-captures all45; independent direct review of
  the three changed running-event pixels finds full dates and titles separated.
  Root also inspected the short-desktop frame. The other42 states were unchanged
  and directly inspected in140; do not imply45 new final-review inspections.

Archive checks qualify retained values, truthful guidance and disabled mutations,
not fully interactive comparison or retry: the outer archived fieldset disables
controls. Initial gallery fault is its references API read, not failed image bytes.
Fixtures are not native generation or complete Create/Revise/Recover acceptance.

## Regression and preserved failures

- Focused reader/gallery/Bible/review-seam journeys16PASS32.5s in129, then
 16PASS33.3s in130 after the retry-owner and empty-heading corrections.
- Reader failure123 was an incorrect test error field (`detail` instead of the
  API's `message`); parser was not widened. Failure124 assumed one Script GET,
  but StrictMode made two initial reads; the retry made no new Script read.
  Assert against the pre-retry baseline; retain zero writes and route/Script checks.
-126 short reader retry screenshot cropped its lower border. Direct review
  identified capture framing, not inaccessible controls.129 leaves the margin;
  all21 re-reviewed, crop resolved without changing reader layout.
-127 gallery/Bible initial run2FAIL/1PASS demonstrates missing retry and misleading
  archived guidance. Bible forms already passed; those failures remain retained.
- New overlapping-read unit initially4PASS/1FAIL: pending remained true after the
  superseding error. After independent ownership repair5PASS; latest full frontend
  and final browser gates below must qualify subsequent copy changes.
- Gallery tests retain local input/DOM identity on refresh failure, suppress new
  read-only observation, ignore invalidated sessions and keep the newer error
  authoritative when manual reads settle later. Reader tests preserve nine routes,
  shared joins/endings, exact section/Script/Storyboard currentness and no writes.
- Final reading/run focused journeys18PASS33.4s in137. Frontend664PASS87 files,
  application/E2E types and deterministic buildPASS. A new diagnostic-test suite
  initially failed to load because its Node filesystem mock omitted the default
  export; a partial mock corrected that harness, with no product/parser tolerance.
- Intermediate frozen full gate133:214PASS/1FAIL5.8m.853 source/test/config/static
  files stayed unchanged, hash `292880d19236f7a25402fa9b2435657566efba06dc15db57a6dadc18c16a49203c`.
  The native branching clip stayed at currentTime0 despite readyState4 and no media
  error. Exact HTTP206 body119093 bytes has SHA256
  `9db2ca070c77bec620130338cb4494bb1a7058aa99c66d8e708349b11810eb49`;
  H.264/AAC timestamps and complete local FFmpeg decoding passed. Neither proves
  native browser ended. Cause remains unproven; the later isolated native PASS134
  is diagnostic evidence, not a fix or replacement gate.
- Browser teardown now retains CDP events/properties/errors, renderer snapshot,
  response metadata/hash and available exact failed media bytes. Snapshot/body/
  detach each have a diagnostic-only budget; pending reads are explicit. Five
  unit regressions cover exact bytes, never-settling reads, persistence failure
  cleanup, partial-range attachment typing and passing-run detach stall.
  Gameplay assertions/settings are unchanged.
-135 Trace/repair capture initially targeted a stretched list panel, partly outside
  the short viewport. The actual item is the reading target; its complete bounds
  are asserted. Direct review then caught the cramped failure badge and technical
  refusal text that passing browser assertions had missed;137 re-captures those
  repairs, including the six previously unreviewed Inspector frames.
- Intermediate138 full gate217PASS6.1m,858 files unchanged:
  `2c0eb8586e5da293403ade94b02c5f14e57b635137daf482072f7d70948a2a18`.
  This precedes the last review repairs and does not qualify them or explain133.
-139 new active-run reading fixture failed its zero-write assertion: the normal
  loader automatically resumed the same owned no-auth run. The read-only route
  aborted that request. Use the real missing-frozen-bearer-key refusal rather than
  disabling product execution or providing credentials.140 then2PASS8.7s;141
  adds timestamp non-overlap checks and passes2 tests8.5s. Focused model/status
  regressions39PASS. The unknown kind, pending tone, helper, warning and adapter
  cleanup received independent source review with no remaining concrete finding.

## Final qualification and remaining work

- Final frontend666PASS87 files; application/E2E types and deterministic buildPASS.
  Build retains the existing large-chunk warning; it is not silenced or a new
  chunk-splitting acceptance claim.
- Final142 unfiltered browser217PASS6.1m, default4 workers and0 local retries.
  All858 source/test/config/static inputs stayed identical before/after:
  `17e70e9f60d38d8a3438e2407ceba3b69382c9d08b58d61d0d748607bab2c999`.
  Prior stalled probes remain unexplained historical failures, not fixed by this
  later PASS. The diagnostics keep future failures inspectable without weakening
  native playback/ended assertions.
- Lockfile and API-unused-import checksPASS; final wheel/installed smokePASS:
  `/private/tmp/plotloom-reading-state-qualified-wheel.xAc9G4/`.
- Normal8841 serves matching JS SHA256
  `a30c005e8f0767cfe85584c603d46895af2a4d6d525a51cda90b67486aa88277`
  and CSS SHA256
  `42beb639a4681beb6bea3a3b04916ee1eb63481a821eb42994f152de7e2d6850`.
  No restart or protected-setting changes were required.
- Fresh preservation readback is exact:
  `df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`;
  Wind17/Rain67 files, both full database row/schema sets and three protected files.

Publication/remote-CI identity follows commit/push. Earlier PASS counts do not qualify later changes.
Full backend1245PASS was already run during this same E2E audit chain; this
frontend-only checkpoint does not claim a second backend run.

Remaining UI state slices are explicit in the whole-product register:
review failures/stale/dirty, dialogs/help/report expansion, archived interactive
controls and native report/route pixels. Actual H3 opening remains ingested but
unselected and decoder-ended acceptance is unresolved. Other route videos,
native multishot/model-intent generation and post-install revision/rebuild are
not completed by these reading-state fixes. Overall E2E remains **PARTIAL**.

Next source-only findings, not pixel-qualified or repaired here: the dirty Archive
consent inherits navigation's “保存并切换” wording despite archiving, and frozen-key
guidance puts Profile/Key terminology into the primary creator message. Exercise
the actual disposable branches before changing the shared intent/presentation
contract; keep cancellation, credential refusal and model ownership unchanged.
