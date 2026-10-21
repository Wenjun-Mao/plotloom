# H3 console UI state corrections — 2026-10-21

Status: **BOTH DEFECTS CORRECTED, VERIFIED AND DEPLOYED.** Source `ef8417ba`.
Owner explicitly approved fixing/testing/deploying the two defects from the
[manual walkthrough](2026-10-21-h3-console-manual-walkthrough.md). Baseline5521b0fd.

## Root causes and correction boundary

- **UI-01**: click handlers mutated cursor history before a request completed.
  An existing stale-response guard protected fetched data but not the history.
  `DashboardPages` now owns one accepted page/query/cursor/history snapshot and one
  pending transition. Controls and handlers reject repeated navigation while pending;
  accepted responses commit it, failures leave the previous page/history intact.
  Filters reset through the same pending boundary; superseded responses cannot commit.
- **UI-02**: browser media failure and server file availability shared one text
  assignment. Polls replaced the native error even with the failed element retained.
  `DashboardPreview` now owns source-bound playback/load failure independently of
  backend availability. Polling keeps the element/error; successful video loadeddata
  or image load clears it, as does a new/expired source. Removed-source events cannot
  affect the new selection. Valid original downloads remain available.

These are client-state corrections, not database pagination/API/media/codec changes.
The state helpers are a cohesive108-line static module; main dashboard script387lines.
No new generation, queue actions, retention changes or production frontend edits.

## Verification

- Full locked gateway+extraction suite243passed; one existing Starlette/httpx
  deprecation warning. Node UI tests10passed; JavaScript syntax, targeted Ruff and
  patch whitespace checks passed. New tests cover duplicate Next/Previous, failed
  and superseded transitions, filter resets, persistent media errors, successful
  video/image recovery, removed-source events and preserved downloads. HTML script
  ordering and served-helper allowlisting are covered by the Python boundary test.
- Independent GPT-6.1 Sol/Medium review found no material findings and independently
  ran the then-current9Node tests; root's final10includes image recovery.
- Headed local Chrome used a copied disposable file-SQLite fixture with106records
  and retained video. Under500ms browser-only GET latency, double Next committed
  exactly page2; Previous restored page1/its original rows. A deliberately failed
  page GET retained page1/its rows; refreshing then navigating succeeded.
- Genuine browser media request abort produced an error; after6seconds/poll the
  warning remained, same video node remained and download was still available.
  Removing the test fault and reloading that element produced real loadeddata,
  cleared the warning and advanced playback. No fake error or completion event.
- Repeated the delayed double-Next/double-Previous and media-fault/recovery checks
  through actual private HTTPS after deployment, using the retained walkthrough
  canary `h3_cc23e43b2db24cdc8f2c0ac480b0cd79`. Recovery reached native ended normally;
  phone390x844 had no horizontal overflow. The intentionally aborted requests create
  expected console errors; they are test evidence, not unexplained service failures.
- Served `view-state.js` bytes exactly match committed source. Original MP4 download
  SHA256 still matches `8cb06bcfca59c1d0ea0ef1269293c38dade87dd3a511bb016671034155938841`.
- [Persistent HTTPS warning](supporting/h3-ui-fix-https-warning-20261021.png) and
  [recovered phone](supporting/h3-ui-fix-https-recovered-phone-20261021.png) inspected.
  Local fault/pagination evidence retained under `.local/h3-ui-fix-20261021/`;
  disposable data `/private/tmp/h3-ui-fix-qa.mYlWCK/data`, browser/fixture server stopped.

## Deployment and safety

At observed empty shared lane/Comfy queue, rebuilt and replaced **only** the
dashboard. Jobs147→147; no new generation, retry, deletion, migration or lane change.
Release `/home/wjmao/services/plotloom-h3-dashboard/releases/20261021-ui2.JFgusD`,
image `plotloom-h3-dashboard:20261021-ui2`, digest
`sha256:30f44564c1aadc6c64616a409b31cb7a2b15d983cfe14b242fa937ba56885147`.
Container `d3d742e6993a8c8cb93a9944864085bfc98cb9a71076a06f3cce63a7f435c599`,
healthy/unless-stopped. Existing read-only data/key mounts and locked dependencies
unchanged; no GPU access introduced. Tailscale Serve remains exactly the private
`/dashboard` handler, no Funnel or `/v1` publication and no admin reconfiguration.

Gateway `4020bc9e8dff13da68ca839f91e142f53e5104df60e8257f4cc22400520a42d6`
and Comfy `8542065d40cb5226eb50ecfbd838565e264fe8c2b02c0efe604d1af68b68354e`
retain their October6 start times/images. No generator or other service restart.
Rollback, if required, uses preceding dashboard release20261021.SN81Z5/image20261021;
do not alter gateway data or the private HTTPS handler to roll back this UI patch.

The original manual findings remain preserved, now resolved by this receipt. No
new creative/model-quality acceptance or claim about the earlier timeline report.
Broader specialist integration/director contact/merge/push remain held. Local commits
only; no CI triggered. Usage/cost telemetry unavailable.
