# H3 dashboard output actions — 2026-10-22

Status: local candidate verified; deployment evidence follows below.
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

Pending: deploy the final history/layout correction at another idle checkpoint
and repeat private-HTTPS history/geometry checks. Existing data, gateway/Comfy
container identities, secret mounts and Serve handler remain unchanged.
No merge, push, CI trigger or director message is authorized here.
