# H3 console manual walkthrough — 2026-10-21

Result: **core workflow passed; two reproducible UI defects remain open.**
Source baseline `81baa43c`, deployed dashboard image
`sha256:eef52ef944757d8143de5ebd20c08475bd2c147531e07dbe119ee43a251f39ca`.
Real headed Chrome through normal-TLS Tailscale URL
`https://gx10-1523.tail6040ad.ts.net/dashboard/`, desktop1440x900 and phone390x844.
Owner requested manual UI testing. Gateway development/test generation is already
authorized; this pass was explicitly bounded to **one** Q1 five-second live canary.
No product-source edits, deployment, restart, merge, push or director contact.

## Walkthrough results

| Area | Observed result |
|---|---|
| Defaults/options | Q1,576x1024,5seconds,blank seed; four qualities and six resolutions present |
| Native form validation | Empty form, duration4 and negative seed blocked without any POST |
| Input-mode switching | Only chosen upload/URL inputs enabled; optional end frame supported |
| Rejected URL | Missing local image URL returned `source_url_fetch_failed`; form draft preserved, no job admitted |
| Successful creation | UI multipart uploaded retained first/end frames,202accepted, selected new ID, running status and elapsed time displayed |
| Search/filter | Exact ID, no-match/literal-markup search, Qwen-only and failed-H3 views exercised |
| Draft/navigation | Unsaved prompt survived selection, browser Back and polling; copy-ID button confirmed success |
| Explicit reuse | Prompt/scalars copied, both file and URL inputs cleared, seed preserved, no submission |
| Expired output | `h3_197d7081b30d46af835377a4da4ce294` showed expiry with no preview/download |
| Natural playback | Live canary reached native ended=true at5.167seconds, no media error, unmuted |
| Download/refresh | Actual MP4 download; bytes/hash equal database; selected ID restored after refresh |
| Phone | No horizontal overflow; preview/details/download reachable |

The two defects below were found with controlled browser-only failure/latency
conditions, not by damaging output files or production data. Read-only GPT-6.1
Sol/Medium review suggested these interaction checks; root independently reproduced
them through the browser. Initial negative requests and intentional media abort
produced expected console errors. A fresh successful-canary page reported zero
console errors/warnings. This is not a complete browser/device compatibility matrix.

## One real canary

- Job: `h3_cc23e43b2db24cdc8f2c0ac480b0cd79`; Comfy ID
  `f71a0cdd-defc-4588-a89d-cbf00bf0cb98`.
- Q1,576x1024,5seconds,seed20261021,`reject_mismatch`; actual124frames at24fps.
- Both start and end bindings admitted. Source is the retained exact-ratio input
  `experiments/h3-cross-geometry-2026-09-20/dialogue_portrait_v1_576x1024.png`,
  SHA256 `36d6534d670d477ea24e642a3cd12ca6c1e80e1d4c55d8cdb97917e34b9f90c1`.
  No new source image was generated. Same retained image supplied for both frames.
- Backend elapsed86253ms; submitted18:05:15.112Z, completion18:06:41.365Z.
- ffprobe: H.264,576x1024,124video frames,5.167seconds; AAC32000Hz/stereo.
- Managed output `2026-10-21T18-06-41Z_h3_cc23e43b2db24cdc8f2c0ac480b0cd79.mp4`,
  456698bytes, SHA256 `8cb06bcfca59c1d0ea0ef1269293c38dade87dd3a511bb016671034155938841`.
- Live jobs146→147, exactly one new job. No retry, duplicate, cancellation or cleanup.
  Output remains under ordinary72-hour retention; no special retention override.
- [Open canary](https://gx10-1523.tail6040ad.ts.net/dashboard/?job=h3_cc23e43b2db24cdc8f2c0ac480b0cd79).
  This proves the bounded UI→gateway→H3→retained-output journey, not acceptance of
  voice identity, dialogue accuracy, lip sync, all quality/resolution combinations,
  or a fix for the colleague's earlier15-second timeline report.

## Open defects and owning layer

### UI-01 — repeated Next while a page is loading duplicates pagination history

With50-row pages and500ms browser-only delay on the jobs GET, double-click Next.
The UI displays page3 but shows the same cursor/page2 rows; Previous changes the
counter to2 without changing those rows. Source:
`dashboard/static/dashboard.js:356–360` pushes cursor history using the old
`nextCursor` before the pending page resolves. Request epochs discard stale data
but do not make navigation/history atomic.

Fix belongs in client pagination state: admit only one pending cursor transition
and synchronize history/counter with accepted navigation. Do not change database
pagination, add sleeps or weaken stale-request guards. Proposed regression:
rapid repeated Next/Previous under delayed responses must not duplicate history
or mislabel rows. **Not implemented in this testing assignment.**

### UI-02 — a poll erases a native playback error message

On retained job `h3_7975b0fcecc14cdf9ce9c6bcd41ebe55`, abort only the browser media
request and reload its video source. The genuine media element reports error4 and
the UI initially says「浏览器无法读取或播放此输出；可下载原始文件检查。」.
After one poll it instead says「可查看」although the same failed video remains.
Source:`dashboard/static/dashboard.js:276–282`: local error callback updates text,
then each detail render replaces it with backend file availability.

Fix belongs in presentation state: retain a source-bound playback failure independently
of backend file availability until media recovery/replacement. Do not mark the H3
job failed, remove a valid download, transcode, or force-recreate media on every poll.
Proposed regression: native media error remains visible across polls for that source,
and clears on deliberate recovery/new source. **Not implemented here.**

## Evidence and final state

[Desktop success](supporting/h3-walkthrough-success-desktop-20261021.png) and
[phone detail](supporting/h3-walkthrough-success-phone-20261021.png) inspected.
Additional validation/admission/fault screenshots and CLI snapshots remain local
under `.local/h3-walkthrough-20261021/` and `.playwright-cli/`; no MP4 committed.
Gateway and Comfy retain their original container IDs/October6 start times; the
shared lane and Comfy queue were empty after the canary. Browser session closed.
No automated suites rerun for this documentation-only walkthrough record.
Usage/cost telemetry unavailable. Both defects are concrete follow-ups, not a
reason to claim the otherwise successful UI walkthrough entirely passed.
