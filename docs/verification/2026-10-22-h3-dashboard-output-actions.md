# H3 dashboard output actions — 2026-10-22

Status: **IMPLEMENTED, VERIFIED AND DEPLOYED.** Final source `91346e08`.
Baseline `cc30ce58`; owner requested improving the reported output-access failure.

## Root cause and scope

Job selection already fetched the right record and updated the URL. At widths
at or below1050px, CSS placed the detail panel after the entire50-record list;
selection did not scroll or focus it. The output column's「可查看」was status text,
not an action. This was a navigation/discoverability defect, not missing media
or failed generation. Correction belongs in the dashboard interaction/layout.

- Explicit「预览 / 下载」on available outputs;「详情」for other records.
  Downloads remain native links to the existing checked original-media route.
- Selection reveals/focuses the detail heading;「返回任务列表」returns to that
  job, or the list heading if filtering/pagination removed it. Same-job selection
  does not reset playback. History/deep links retain selected identity.
- Bounded list with sticky table headings; phone-width cards keep actions visible
  without horizontal scrolling. Original download is above the portrait player.
- A cohesive keyed job-list module retains same-page buttons through polling,
  preserving keyboard focus. Polls never scroll/focus the detail panel.
- No generation, API/schema/retention changes or model-runtime changes.

## Local verification

- Locked gateway plus extraction tests:243passed (one existing Starlette/httpx
  deprecation warning); final Node UI tests:14passed; targeted Ruff and patch checks pass.
  Coverage includes served assets, available/unavailable actions, expiry updates,
  selection-only reveal, return fallback, stable controls and prior pagination/
  preview regressions. Authoring frontend and wheel gates are not applicable to
  this service-only static UI/asset-allowlist change.
- Independent GPT-6.1 Sol/Medium review found no material findings. Its minor
  delayed-highlight observation was resolved by immediate selection highlighting.
- Headed Chrome against disposable file-SQLite106-record fixture, with retained
  video (no inference):1440×900,800×900,390×844; no document overflow. At800px both
  row actions fit the visible list width. At390px card actions fit within viewport.
- Preview click revealed details and focused its heading; download above player
  completed as an attachment. Playback advanced across a5-second poll without
  resetting; keyboard focus/button identity survived polling. Last-row return,
  Back navigation, page2 transition and absent-row return fallback passed.
- Local screenshots inspected; scratch evidence retained under `.local/` after
  closeout. The fixture's copied media/data are not production evidence or new jobs.
- Final private-HTTPS history check found a second interaction cause: native Back
  restored scroll after the immediate reveal, and a short loading placeholder
  could clamp scrolling before content arrived. The correction makes SPA history
  scrolling explicit and finishes each navigation's reveal once after accepted
  detail rendering. Return-to-list and fetch failure cancel that pending reveal;
  ordinary polls do not renew it. Local phone initial click, Back, Forward and
  reload now each place the panel16px from the top. A second independent review
  found no material issue and independently passed all14UI tests.

## Deployment

Initial source `c9daabfa` deployed at13:22:20Z after the colleague's active render
finished. Job count168→168. Private HTTPS checks passed native playback/seek,
same-element polling, row download and phone actions using the reported job
`h3_aa2856b70b544113a8f23924b093a2d3`. Download SHA256 matches the stored original:
`1d8a4a7055e16c34ec61f139220d4cdd942a84607b6c309d9a515a93ac7db898`.
Two in-flight read polls received502during dashboard cutover and recovered;
no generation was sent. A colleague started another job after the idle cutover.

Final history/layout correction deployed at13:27:22Z at a new observed empty
shared lane and Comfy queue. Job count169→169; both colleague renders were left
to finish normally before either dashboard replacement. No generation submitted
by this work. Gateway and Comfy container IDs/images/start times remain exactly
as before, with their October6start times. Data/key read-only mounts and Tailscale
Serve `/dashboard` handler remain unchanged. Dashboard is healthy/unless-stopped.

- Release `/home/wjmao/services/plotloom-h3-dashboard/releases/20261022-output-actions2.zLJ3ON`.
- Image `plotloom-h3-dashboard:20261022-output-actions-2`, digest
  `sha256:dbae86250c22faa321625ff39b7e1efef60e635702424ab1c7d3418e6029aa4d`.
- Container `ae9dd77c03e6281c0950157a5650995537ecb923c06af460af75fa7afe6c24e5`.
- Final served dashboard.js SHA256
  `6fafeeb0e6b0db2358a6cd47a104a8893fe35757f98f17f35feaceab34a2faff`
  exactly matches committed source; new helper/CSS/HTML hashes matched as well.

Repeated genuine private HTTPS phone click/Back/Forward/reload: each placed the
detail panel16px from the viewport top; return focused the correct current row.
Desktop layout inspected, no overflow. Playback retained the exact element and
reached native end across polling. Original download of
`h3_17237b55a4094be992436e63c314f721` matched its recorded SHA256
`28f9720fd4a9c2dab78bcc1337f0ea46cb7f2e8282f8194331e797817e524a91`.
Expired rows/detail offered no download. A local browser-only600ms detail-GET
delay also proved return-to-list cancels a pending reveal (focus/scroll unchanged
after response); no production request was delayed or altered.

Inspected final screenshots: [desktop](supporting/h3-output-actions-https-desktop-20261022.png),
[phone list](supporting/h3-output-actions-https-phone-list-20261022.png),
[phone preview](supporting/h3-output-actions-https-phone-preview-20261022.png).
Scratch screenshots/downloads retained under `.local/h3-output-actions-20261022/`;
owned local fixture server and Chrome test session stopped. Existing rollback
release/image retained. Work is local to the specialist branch: no merge, push,
CI trigger or director message.
