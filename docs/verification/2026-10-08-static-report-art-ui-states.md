# Original reports and stale Art reading — 2026-10-08

Status: **SCOPED QUALIFIED BY LATER154 GATE**. This is part of
the [whole-product visual/text audit](2026-10-08-whole-product-ui-audit.md), not
full Create → Revise → Recover or media-quality acceptance.

## Root cause and bounded repair

The Script reader described disabled report JavaScript as “上游脚本”, easily
confused with the story's 剧本. Script/Storyboard review and the Story reader
also used inconsistent report summaries and English frame names. The owning
defect is app presentation, not the frozen creative report or its sandbox.

One shared reader now says “阅读原始剧本报告（只读）” / “阅读原始分镜报告（只读）”.
Its helper explicitly identifies a read-only presentation, explains which
report controls are disabled, and distinguishes the retained original from
current edits. Script's confirmed-version helper makes that difference explicit.
The Chinese iframe names match their report subject. URLs, read admission,
empty sandbox, no-referrer, static projection and original archive remain intact.
The Story reader's existing540px iframe geometry remains unchanged.

## Actual desktop evidence

All captures are in `output/playwright/full-lifecycle-2026-10-07/`; the three
supported viewports are1700×900,1280×768,1280×460. An independent GPT-6 Luna/Max
reviewer directly inspected all72 captures; root additionally inspected
representative native/fixture viewports and the corrected short-desktop footer:

-144-outline-{top,table,middle,bottom}-*:12 captures. Actual Timeline/Table
  switching, lower asset section, last content, Close/reopen and exact report
  identity on disposable8861. Modal/close bounds and hit tests pass at all sizes.
-145-script-{disclosure,top,middle,bottom}-*:12 captures. Original native report
  job `ch_8c225c8ce2ef4a68b01775b7eb598e2a`,22479 bytes.
-145-storyboard-{disclosure,top,middle,bottom}-*:12 captures;145-board-west-
  {anchor,prompt-top,prompt-bottom}-*:9. Original native report job
  `ch_e700ff3bd4224c1db467860ea9045a6e`,42131 bytes. The actual E03-01 anchor
  navigates to the West segment; its full prompt has no internal height clipping.
-145-native-west-{route,episode,instructions-top,instructions-bottom,
  report-disclosure,report-segment,report-bottom}-*:21. Actual West selection
  keeps E01/E03, excludes East E02, expands the exact instruction, opens/reopens
  the original report and reaches its true last content with normal scrolling.
  At460px, the540px iframe requires both document and frame scrolling; the final
  bottom capture shows the footer, not a centered partial frame.
-145-reader-art-focused/source-review-currentness--adc1a--the-same-accepted-revision/
  art-retained-stale-{top,actions}-*:6 explicit-fixture captures. Reopened Art
  becomes stale after an upstream Cast change; the exact local JSON draft remains,
  Save is disabled, discard/replace are readable, and the entire accepted-Art
  object equals its pre-change value before discard. This is not native generation.

The native project is `b3a933f7-b6fc-40e3-826f-5162f95a119a` on isolated8861.
All three native exercises assert exact canonical preservation and zero project
API writes. Script/Storyboard also compare original archive bytes before/after,
check static CSP and permissions, and preserve source identity on reopen.
No page/frame horizontal overflow was observed. The West original report covers
all three episodes; its route-filtered reader intentionally covers only E01/E03.
The disclosure labels these as different reading scopes, not conflicting routes.

Capture corrections are retained as non-qualification: the first Outline probe
assumed a `.modal-card` rather than the actual dialog; the first Script pass did
not open its collapsed disclosure and timed out. Corrected captures use observed
owners, assert report visibility and repeat the full guarded exercise. No failed
capture is counted as a visual PASS. Sandbox-blocked report JavaScript remains
intentional; frozen English creative prose is not translated or rewritten.

## Remaining original-report defect

The original Outline duration tile prints `0.083333333333333333 分钟`, splitting
“分钟” across lines at1280px. Independent source diagnosis locates direct numeric
interpolation in the pinned upstream renderer, not host CSS. ADR0086 preserves
the interactive original bytes; ADR0126's static projection is not an Outline
presentation contract. This is **UNRESOLVED**, not repaired by a no-wrap patch,
archive rewrite or hidden response transform. A future renderer correction or an
explicit derived-Outline presentation contract needs its own scope and regression.

## Gates and startup evidence

- Focused report/Art3PASS11.9s; frontend685PASS/91files; application/E2E types,
  deterministic build, lock, API-unused-import lint, wheel/installed smoke PASS.
  Wheel: `/private/tmp/plotloom-report-art-audit.ZUPU3w/wheel/`.
- First stable unfiltered gate:216PASS/4FAIL6.8m. All four are45s workbench
  setup failures before navigation/test assertions, with empty browser network
  traces.866 source/test/config/static files unchanged before/after:
  `d3b9f7fe2b40f1421a252ed3fd8e85adf76fe0c9f937ba0e8899264d8ad1e96e`.
  Retain145-qualified-report-art-gate as failed evidence; a focused replay of
  the four unchanged cases passes9.5s, but does not diagnose startup causation.
- The earlier121 failure had the same missing inner-phase evidence. The proven
  observability defect is repaired only with named root/port/readiness trace
  steps. Polling, process ownership, environment,45s/25s limits, retries and
  workers are unchanged. Independent GPT-6.1 Sol/Medium review finds no drift.
  Four146-startup-trace-focused cases PASS9.1s; all traces now identify their
  nested root, port, provider, FastAPI and Vite phases/timings. Pending-step
  evidence on an actual timeout is not yet empirically observed.
- Unfiltered146-qualified-report-art-gate finished218PASS/2FAIL6.1m, with its
 866-file fingerprint unchanged before/after:
  `792115f3f469e83af9d3cbe6c7d85a0ca112e63e703c1f16f4eedf5d2da80005`.
  Both failures are plain native probes before choice handling: click/play/playing/
  play-resolved occur while the connected video clock remains0. The served full
  MP4 is104192 bytes, SHA256
  `0db6507870ee4003ac27b13013dde1c795b583f4eee3aacb878456c19e47fd8b`,
  with no console/media error in the then-available evidence. No startup timeout
  occurred in that gate. Final decoder/buffer state was missing because these
  probes had not installed the diagnostic collector; that observability gap is
  corrected with an explicit native fixture filter/trace reader, not a playback fix.
  Focused147 probes2PASS35.7s retain complete media state and CDP decoder events;
  identical bytes, native ended and FFmpeg decoders pass in that focused run.
  They do not diagnose the prior stall or substitute for an unfiltered gate.
  Underlying startup cause, unbounded in-flight fetch and cumulative readiness
  budgets remain named limitations; this instrumentation is not a startup fix.

Fresh owner/config protection is exact:
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`;
Wind17/Rain67 managed files and three protected files preserved. At this checkpoint normal8841 served
HTTP200 exact JS `61f3a611638681197e5a0a11c3a41eb07780b2c33e1baf757cef74fd6b63345d`;
backend source remains qualified e941780, no restart or settings changes.
The later [frozen-configuration checkpoint](2026-10-08-frozen-profile-ui-states.md)
owns the next candidate, gate and serving identity; the hash above is historical.
The later154 stable unfiltered gate passes220 tests6.4m on unchanged868 inputs;
the linked checkpoint owns latest688 frontend, package/protection and serving
readbacks. Earlier145/146 failures remain retained and their causes unresolved.
Publication is pending closeout. Other visual-state permutations,
native successful/all-route playback and the broader lifecycle remain PARTIAL.
