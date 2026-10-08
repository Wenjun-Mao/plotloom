# Whole-product visual and text audit — 2026-10-08

Status: **EXECUTED / PARTIAL COVERAGE**. Included in the current full E2E run,
with scoped repairs verified; unqualified states remain listed below. This is
not full lifecycle acceptance. Artistic image/video quality remains owner/H3 scope.
Baseline: [full lifecycle ledger](2026-10-07-full-creator-e2e-repeat.md);
reusable entry: [E22.1–E22.7](../creative-workflow/graph-workbench-acceptance.md#e22-全产品视觉与文案专门检查).

## Scope and evidence discipline

Audit primary and Professional views, settings, readers and recovery messages for
spacing, alignment, scrolling, actionable states, terminology and **weird wording**:
unnatural translations, unexplained jargon, awkward sentences and labels that
misstate what a handler does. Use 1700×900,1280×768,1280×460 only; narrow/phone
support remains retired. Screenshots exist under
`output/playwright/full-lifecycle-2026-10-07/`; capture alone is not a visual PASS.

Native read-only sweep uses the disposable project
`b3a933f7-b6fc-40e3-826f-5162f95a119a` on isolated8861, with structural QA in a
separate tab. No settings saved, directory mutations or provider dispatches during
this sweep. Loaded content is awaited; initial Source loading and Pro timing
captures are excluded from qualification. Original creative prose and immutable
report evidence are not rewritten for cosmetic consistency.

## Current view/state coverage

| Surface | Actual evidence / inspection | Remaining scope |
|---|---|---|
| Brief, Creator, source, Pro |82–85 native/QA;109 loaded review captures, long graph and all18 Pro viewports; root/independent direct pixels | All applicable state permutations not yet pixel-qualified |
| Cast/reference gallery |80b/86 expanded image/details;115 final native confirmed-label/expanded-provenance/top-and-bottom captures across desktop sizes, root short-pixel inspection and independent direct review of all nine files | Empty/failed-state final pixels not yet qualified; guard/state regressions remain required |
| Bible |88: native populated premise field, all three sizes directly inspected | Additional selected entity forms and failure/read-only pixels |
| Art, Script, Storyboard/production review |87–89 native top/middle/bottom;94 saved/selected;109 loaded heads;112 repaired Art/production viewport pixels at all three sizes;113 actual native optional-Art-task scrolling at all three sizes, zero writes | Deeper selected/failed/stale state permutations not yet pixel-qualified |
| Script/Storyboard readers |90: both native East/West routes opened, matching screenplay/storyboard, top/bottom ×three sizes; root and independent subset review | Remaining captured pixels and failed/stale-reader states |
| Play |90/95 native incomplete media;109 missing installed production exposed a misframed request error;112 typed prerequisite state directly inspected at all three sizes with exact owner link and no transport alert | Native playable/all-route progression not established; initial request failure/retry tested separately |
| Specialist/provider settings, Home/directory |91 native top/bottom;93 repaired overlay hit/scroll/Close;109 desktop views;112 initial top, text-ID scroll and image-ID scroll pixels directly inspected at all three sizes; readable directory times rechecked | Other operational states not yet pixel-qualified |
| Trace, repair, Beats |97 native idle/populated;109 all18 Pro and three enabled exact-repair viewports;112 one-line Add Scene control directly inspected at all three sizes | Additional retained-failure and unknown-state pixels |
| Shot/media details |83 QA;110 current native pending/loaded at three sizes, initial failure at short desktop and successful named retry; root inspected all seven frames, zero POSTs | Native preview/selection/playback quality and remaining subcontrols remain separate/incomplete |

No page-width overflow observed in the measured native89–91 cases. This does not
prove every view or state. Captured larger frames not explicitly inspected remain
unqualified. Sandbox-blocked scripts in immutable static reports are an intentional
reading boundary, not permission failures to solve by enabling report scripts.

## Findings, root causes and bounded repairs

| Finding | Root cause / repair boundary | Verification so far |
|---|---|---|
| Prepare actions read like immediate generation | Copy did not follow prepare-only handlers; say准备任务/片段预览 | First repair gate208PASS; no dispatch semantics changed |
| Brief/Creator/Pro/Bible/Beats/Trace/repair guidance exposed jargon or unclear next actions | Primary guidance borrowed implementation terms; natural action/object wording, retaining exact diagnostics | Representative native captures; whole state matrix remains partial |
| Bible premise query also matched Logline | Shared wrapping label included help containing“故事前提”; direct native control gets sibling label and help description; Logline help usesField hint |611 frontendPASS and208 browserPASS; native88 at all three sizes |
| Trace with a retained failed/current run said to start a run | Empty event list treated as no run; guidance now distinguishes running/existing/true idle | Focused state tests in611 gate; native failed-state pixels still pending |
| Art confirmation drift and reference action said“替换为用作…” | Manual approval and reference decision handlers confused with technical acceptance/asset replacement |626 frontend/full209 intermediate gate; native94/96 plain reference boundary and112 Art pixels |
| Confirmed production showed“确认后，将建立…” | Help ignored accepted state; conditional past/future tense | Bridge tests, intermediate full209 gate and112 production pixels |
| Saved presentation review said media“尚未因此获得接受” | Literal technical-acceptance phrasing; plain independent media审核/选用 boundary | Presentation tests and native94 saved-state rendered recheck |
| Specialist heading hidden under topbar | Dialog mounted inside sticky sidebar stacking context; native rect within viewport but heading-center hit returnedHEADER.topbar |92before direct pixels/hit test; move to workspace overlay boundary, three-size hit/scroll/close regression added |
| Missing-video links indistinguishable / long comma-chain notice | Shot prose reused as display identity and deduplicated in prose; use node+scene/shot context and concise count, preserve exact-ID links and structural gaps |38 focused label/playback testsPASS; identical-prose/24-link desktop regression. Independent review found generated qualifier could collide with authored node title; node position now unconditional, with explicit three-node regression |
| Brief and frame-input helpers absent from descriptions | Some callers kept helpers inline instead of using the sharedField hint contract; move text verbatim into hints, retain exact constraints and fields | Brief five-control rendered-description assertions, frame-input regression and626 frontend/full209 intermediate gate PASS |
| Media candidate called“Imported” even for a native generated image | CandidateCard display assumed one ingestion source; neutral“候选图片” label leaves persisted provenance authoritative | Exact import/snapshot selectors updated; no provenance or asset identity rewritten |
| Unknown video reads appeared empty | Initial job array was empty before owned budget/backend/job reads settled; gate production guidance on successful owned read | Six pending/failure/stale-project unit regressions;110 native transport exercise, zero writes |
| Short Brief help could not be scrolled into view | Unbounded form column was sticky; put it in document flow rather than repositioning help downstream | Focused loaded six-browser PASS; direct109 short help pixels |
| Missing playback preparation said“请求未完成” | Successful missing-stage reads used the transport-error branch; typed missing-production state with preparation-owner link | Unit retry→prerequisite check, exact browser state assertion and112 three-size direct pixels PASS |
|“＋ 添加场景” stacked into three lines | Scene-card 30px number-column grid styled every button, including the generic action | Restrict card grid to non-generic buttons; one-line browser geometry at all three sizes |
| Accepted Art appeared to require an unselected style | Accepted revision and optional NEW task shared hierarchy, although the existing note distinguished their semantics | Explicit optional-new-candidate section, preserved head, focused Art PASS,112 independent pixels and113 real native scroll/read-only proof |
| Generic errors/directory times mixed English into primary UI | Default transport fallback and host-locale AM/PM formatting, not server evidence | Chinese fallback preserves HTTP status/raw details and explicit server messages; Chinese24h `<time>` retains source timestamp |
|“分镜评审确认/确认评审” was awkward | Technical noun phrase in creator guidance |“确认分镜方案与建立正式镜头内容”; no review/production/media handler change |
| Gallery said“已接受角色” while the editor said“已确认角色设定” | Manual creator confirmation used a technical accepted-state label in the adjoining gallery | Current badge/nav say已确认; stale says角色设定需重新确认;13 focused session/selection guards PASS;115 actual native scroll/read-only evidence at all three sizes. Frozen creative prose remains unchanged |

New stable reading invariants are recorded in
[ADR0132](../adr/0132-creator-ui-reading-boundaries.md). Copy-only changes do not
relax approval, overwrite creative source or select a candidate automatically.

## Gates and qualification limits

Latest stable intermediate candidate:626 frontendPASS, application/E2E types,
build/deterministic buildPASS,1245 PythonPASS (one existing Starlette warning),
lock/API-import lint and wheel smokePASS. Full209 browserPASS6.1m with849
source/test/config/static files unchanged before/after:
`fc8e31d277e8385974082fb2c06e05fa04b2340b0355ace84e3fc4aa222bb962`.
The later bounded Play/Art/scene/date/error-copy refinements are not qualified
by that gate:628 frontendPASS, types/buildPASS, focused Art/visual/repair
14PASS/1FAIL52s. The failure was the capture's assumption that the first chat-ID
field must be visible at scrollTop0 on a460px desktop. Root directly inspected
the failure: the initial explanation and first assistant card were visible;
the ID field was correctly below the fold. Corrected capture waits for the first
card legend at the top, then explicitly scrolls to both ID fields and checks
their viewport intersection. Art capability/guards remain unchanged. Corrected
focused14PASS42.3s is retained in112; an independent reviewer directly inspected
30 repaired viewport/full-page captures, with no remaining concrete finding.
Full-page captures establish copy/hierarchy only, not viewport reachability.
Native113 directly inspected all three optional-Art-task viewports after actual
scrolling, with no page overflow or API writes. Latest wheel/installed smokePASS.

Latest frozen full gate:207PASS/2FAIL6.1m,849 files unchanged before/after:
`9a5834de241d632e234e76251501f7cf976da4999643195c065621594e4064a3`.
Evidence retained in114-final-gate-failures. One failure was an old exact
Storyboard wording assertion, corrected to the reviewed wording without weakening
the source-owner navigation check. The other was the recurring plain native
Chromium clock stall; the unchanged multi-ending native sequence and application
branching-video preview passed in the same gate. That recurrence is unresolved,
not classified as a harmless retry. No clean final-gate/release claim is made.
Corrected navigation suite6PASS24.4s retains the exact preparation-owner and
stale-state checks. The later Cast wording-only candidate again passes628 frontend
tests, application/E2E types and deterministic build. Its final full browser gate
passes209 tests in5.9m with849 files unchanged before/after:
`138820796c744b2a4994781d2a6d837ef5c376999a226c8973e4f75b70cd1c95`.
Evidence is retained in116-qualified-final-gate. Both unchanged native probes
pass in this gate; prior stalls remain unresolved historical observations, not
claimed fixes. Final wheel/installed smokePASS from
`/private/tmp/plotloom-ui-audit-cast-wheel.zVCzW7/`.

The114-native-clock-diagnosis paired experiment used the identical retained MP4
and a video-only remux with a byte-identical H.264 stream. Both advanced and
ended at5.166667 seconds under the existing Chromium/default headless contract.
CDP reported FFmpeg decoders and no player errors. It did not reproduce the
stall, so the cause remains unproven: this is not a fix or a qualifying retry.
Playback-quality fields serialized as `{}`; no numeric frame-count claim is made.
No mute, timeout, worker-count or original-fixture workaround was introduced.

Evidence exclusions and false positives are retained rather than silently counted:

- 104 Art/Script/Storyboard/Player captures that only awaited headings were
  premature;109 replaces them with exact loaded-owner or prerequisite checks.
 104 exact-repair capture was layout-only before eligibility;109 requires the
  enabled exact repair control before capturing.
- 105 retains the207PASS/2FAIL native-video-probe run: loaded bytes decoded but
  Chromium's media clock stayed at0 before application choice handling. The
  unchanged probes passed alone and in the later209 gate. Cause is not proven;
  no timeout, clock assertion, mute or worker-count workaround was added.
- 106/108 native-video capture attempts are excluded for incomplete readiness or
  incorrect route-release timing;110 explicitly settles the held GET before
  removing the route and distinguishes pending, known-job loaded and failed reads.
 110 wide loaded video pixels caught initial decoding and are not media-ready
  frame evidence; medium/short show a native frame, not playback/artistic acceptance.
- 107 retains the wrong accepted-review fixture Play assumption and unreachable
  sticky Brief help failure;109 follows the real fixture's missing-production state.
- 111 retains focused14PASS/1FAIL and the erroneous initial chat-ID viewport
  assumption. Initial top, text-ID scroll and image-ID scroll are separate states.
- A previously reported report-toolbar clipping concern was retracted after fresh
  pixels showed readable labels and margins. The assistant-settings short capture
  was scrolled to image settings, not missing text settings. The Brief's reserved
 100px help dock intentionally avoids layout shift; it is not a spacing repair.

Independent GPT-6 Luna/Max pixel reviewers directly inspected42 and17 distinct
109 viewport files; targeted source review found no blockers in the new typed
state/copy/layout changes. Screenshots still do not qualify unexercised handlers.
The repaired112 set has30 independently inspected files;115 adds nine native
Cast files and a source/test diff review with no concrete defect. Main images
retain `object-fit: contain`; thumbnail crops and ordinary viewport folds are
not mistaken for loss of the full reference image. The reusable coverage/copy
documentation also received a separate read-only truthfulness check.

### Earlier gates and preserved repair history

First batch:611 frontend testsPASS, application/E2E typesPASS, buildPASS;6 focused
browser testsPASS. Initial full gate206PASS/2FAIL exposed the accessible-label
root cause; failures retained, not removed. Repaired full gate208PASS(6.2m), with
the same846-file fingerprint before/after:
`830a68ba16b886871c2e99a7e8cfd6689140be01e0c8c2cdf444764647a81645`.

Subsequent copy/modal/recovery-label changes are **not qualified by that gate**.
An intermediate focused Art run32PASS/1FAIL was an old button-name assertion;
its deferred-unmount behavioral assertion remains required. Rebuild, focused
checks followed:613 then616 frontendPASS, types/buildPASS. Focused browser19:
18PASS/1FAIL exposed a strict summary selector; focused14:13PASS/1FAIL exposed
an exact label-text query including the decorative required marker. Corrected
selectors still assert the actual accessible name and description; the final
first-save/presentation6PASS(26s). Both failures and artifacts are retained.

The next frozen full browser gate208PASS(6.7m),846 files unchanged before/after:
`de0e7c7655f0ed79fe89b069eb368519317862a59ba8767ee9ef0b99a97eca1d`.
Independent review then found the authored-title qualifier collision; its durable
fix and further copy/description refinements were **not qualified by that gate**.
Their later build/browser and direct-pixel checkpoints are recorded above; these
earlier gate receipts do not qualify subsequent changes.

Native93 confirms repaired Specialist painting/scrolling/Close at all sizes.
Native94/95 confirms saved/selected Art and presentation states and readable exact
missing-media links. Native96 directly inspected all three sizes shows the final
plain reference boundary. A capture attempt waited for an obsolete Source heading
and timed out without producing qualification; the actual Art panel/text was then
bound and captured successfully. Frozen English prompt and Chinese attribution
notes in94 are original reviewed content, not interface copy: they are retained,
not rewritten to disguise mixed-language source evidence.

Fresh owner-protection recapture matches the exact aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`:
Wind17/Rain67 managed files, both complete DB row/schema sets and three protected
configurations. Scoped source qualification is complete; source/push/CI identity
is reported separately at delivery. The lifecycle run still remains PARTIAL: opening H3 is
ingested but not selected/playback-qualified; other route media, native multishot
preview, same-project post-install revision/rebuild and remaining recovery checks
are not completed by a visual audit.
