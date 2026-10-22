# Frozen configuration reading and diagnostics — 2026-10-08

Status: **SCOPED QUALIFIED AND PUBLISHED**. This extends
the [whole-product UI audit](2026-10-08-whole-product-ui-audit.md) within the
current full E2E run. It does not close Create → Revise → Recover, all visual
states, native playback or image/video artistic acceptance.

## Root causes and bounded repairs

- The settings selector said “活动 Profile” even when a frozen run's different
  configuration was selected while the server still used `default`. Presentation
  conflated the editor selection with server activation. It now says “当前编辑的
  模型配置”; only the server-owned active option says “当前使用”, with an explicit
  “设为当前使用” action. The sidebar/dialog both say “供应商与会话密钥”.
  Callbacks, selection, activation, credential and dispatch contracts are unchanged.
- Configuration-read guidance said “没有继续运行” while the retained run was
  still running. The shared repair/continuation boundary now describes only the
  withheld **new execution request**, without claiming existing work stopped.
  Missing configuration and read failure stay distinct from missing credentials.
  Independent final pixels caught a further “请重试读取” instruction without a
  visible retry control. Copy now names the available recovery: refresh the page
  to re-read. The existing journey restores the real catalog and reloads before
  key entry, asserting zero API writes and no automatic Resume during that read.
- Directory dates used Chinese24-hour formatting, while run/configuration dates
  inherited browser locale. One UI formatter now gives the same Chinese24-hour
  presentation in the reader's local timezone. Stored values, raw trace times and
  the directory's exact `<time dateTime>` are not rewritten.

## Actual desktop exercise

Existing frozen-bearer journey uses a disposable project, explicit fake-provider
hold and a separately seeded run; the tab initially has no session key. The server
current-use profile remains `default`; the frozen job remains `frozen_bearer`.
The case reads the running job and then exercises GET-only browser catalog faults:
remove that exact profile from the read response, then fail the catalog GET503.
It reloads the real catalog before entering the fixture key and explicitly resuming
the same job. No fault response changes server configuration.

All browser API writes are zero through reading, fault captures and opening the
frozen Settings. The settings save intentionally PUTs public profile settings;
only its secret is session-only. That save does not resume the job. The explicit
later Resume uses exactly that frozen configuration's key, and
the completed job/active-profile/server-key readbacks retain their original guards.

Final153 captures: missing key, Inspector, missing profile, failed read, settings
top and scrolled blank-key field ×1700×900,1280×768,1280×460 =18 PNGs. Artifacts:
`output/playwright/full-lifecycle-2026-10-07/153-final-frozen-recovery-wording/`.
The earlier150 set was directly inspected in full by independent GPT-6 Luna/Max;
root inspected the short settings top/key field and wide failure/sidebar frames.
All18 final152 files were independently inspected; only the read-failure recovery
instruction needed revision. Independent Luna/Max directly inspected all three
changed153 read-failure frames, and root inspected the final1280×460 frame:
refresh-to-re-read is explicit; full guidance and HTTP503 evidence wrap without
clipping or overlap. The remaining15 frames have the same reviewed presentation.
The modal remains scrollable: a below-fold field is not clipping, and its lower
field/footer are actually reached before capture. Frozen fixture display names and
professional readiness/protocol identifiers remain evidence, not translated prose.

## Acceptance observability, not a media fix

The earlier146 unfiltered gate retained218PASS/2FAIL; plain native clocks stalled
before application choice handling. Both served the same complete104192-byte MP4
as the later passing147 probe. Their final decoder/buffer state was absent because
the plain probe lacked the collector used by application playback. Each caller now
supplies its exact endpoint filter and trace-reader identity. Collection remains
read-only/bounded, and playback, ended assertions, timeouts, workers and local
zero-retry policy are unchanged. Six unit cases retain exact bytes/range identity,
bounded stalled reads/detach and cleanup, plus explicit native filtering.

The first complete unit/type check after that API change failed five unit cases and
TS2554: the unit harness still supplied two arguments. Supplying its exact original
branching source fixes that caller contract; no production default/fallback is added.
The subsequent complete check passes688 frontend tests/92files, app/E2E types and
deterministic build. Build chunk warnings remain visible.

The H3 read-only advisory is preserved verbatim at
`147-h3-artifact-contract-advisory-verbatim.txt` in the same artifact root. It found
no established output-contract violation in the separate ingested native clip:
strict software decode and container checks pass, while headed Chromium reported a
VideoToolbox disconnect. Root's inference remains **cause unknown**, not hardware,
artifact, browser or lifecycle adjudication. No generation/model/settings change
was requested or performed. That clip is not the plain probe's104192-byte fixture.

## Final gates and publication

Final152 focused13PASS25.2s; final153 focused1PASS8.2s and changed-pixel review PASS.
The stable unfiltered154 browser gate passes220 tests6.4m, default4 workers and
zero local retries. Its868 source/test/config/static inputs are unchanged before/
after, SHA256 `19ab284635776f3404ad85429e5c4ce4d784337a46243909ad739c05edf4e02a`.
Both unchanged native acceptance probes pass; prior stalls remain unexplained,
not repaired by this gate. Final688 frontend/92files, application/E2E types and
deterministic build pass after the last recovery-copy change. Lock/API F401,
archived prompt-reader verification, diff check and latest installed-wheel smoke
pass. Wheel: `/private/tmp/plotloom-whole-ui-audit.Pw78Ff/wheel/`, SHA256
`e6d8a1c49743cf4dc684daa432518ab9084390073a48e3ef887a4a2783859d37`.
Python1245 qualification is reused from unchanged qualified backend source/tests,
not newly executed. Build chunk, color-env and Starlette warnings remain visible.

Owner/config protection before/after that gate is exact
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`
(Wind17/Rain67 files and three protected settings). Normal8841 returns200 and
serves exact checked JS `2098d0968924e96988d7806c21fb556b856322c5ae775be16d195a41ee76c55b`,
base CSS `3b0c81ad3f5e2d92a455826ba114d269fedb3ddbf192ffed70c5381bbe1ea35d`
and product CSS `42beb639a4681beb6bea3a3b04916ee1eb63481a821eb42994f152de7e2d6850`.
No service restart or protected-setting write was needed. Independent Sol/Medium
source/receipt review and Luna/Max pixel review are closed. Root approved and
published executable `35cc75ba022f7bec1bac9723cd156efc81a17f1f`; origin/main identity
is exact. Its unfiltered exact-head
[CI37763010686](https://github.com/Wenjun-Mao/plotloom/actions/runs/37763010686)
is in progress, not claimed successful. The earlier published baseline's
CI37753998839 completed success and is not a substitute for this candidate.
Post-publication owner/config protection remains exact. Only the owned read-only
report audit browser was closed; evidence, QA objects and user browsers remain.
Documentation-only closeout does not change the qualified executable fingerprint.
Do not inherit qualification from
the earlier145/146 failed gates or treat a passing focused native run as their fix.

The next bounded recovery slice remains open: actual tab/project reconciliation,
busy/failure pixels and conflict reload success must be checked. Source inspection
found `serverReloaded` set before the loader establishes success; this is a separate
state-contract defect, not covered or repaired by the current settings/report batch.
