# Reviewed playback segment — bounded technical receipt (2026-09-23)

## Outcome and boundary

The approved first [ADR 0082](../adr/0082-proposed-production-playback-timing.md)
slice now has a separate authored shot duration, qualified H3 request, decoded
original take, and explicitly selected playback derivative. The creator can
choose any contiguous, frame-aligned 144-frame window from a qualified
eight-second take for a six-second shot, or the full 192-frame window for an
eight-second shot. The original bytes and hash remain retained. A proposal is
not a selection: the UI presents the final derivative with sound and requires
reviewer/note plus an explicit confirmation. This technical control cannot
prove a human watched or creatively approved a clip.

Root cause: route playback previously treated a selected whole job as a
playable shot. Its nominal provider request could disagree with both the
authored duration and decoded media, and ordered playback could mount a
partial path. The fix lives at the timing/source, segment-selection, and
shared playback projection boundaries, not in browser-only seek/stop logic.
Frozen jobs now bind current canonical or accepted F5 source timing; a narrow
8-to-6 `segment_required` request does not retime source or waive the original
H3 ingest checks. The local derivative is H.264/AAC with validated 24-fps
decoded frames, PTS, audio coverage and digest. Segment proposals bind the
  original hash, exact window, source lineage, probe evidence and selection
  revision. Selection CAS and media serving recheck currentness and hashes.
  Portable snapshots include both proposed and selected derivatives; a take
  with retained proposals cannot be discarded. The legacy review endpoint
  cannot select an H3 whole take. A later explicit rejection clears the
  shared selection revision and blocks playback without erasing evidence.
Both ordered and branching players consume only a current selected derivative
and block incomplete routes. Old whole-job selections are not automatically
playable. No new nominal-six provider catalog entry was added.

## Executed verification

- Broad backend: 727 tests passed with one unrelated, unchanged bridge
  expectation deselected; one existing Starlette/httpx deprecation warning.
  The single excluded test expects a bridge response without
  `installedStoryboardCurrent`, a field already present before this slice.
  Its full-suite run failed at that exact assertion after 726 passes; no
  bridge response or that test was changed here. Focused timing/video/runtime
  suites also passed (40). Synthetic API proof covered a
  24–168-frame six-second segment and 0–192-frame eight-second segment,
  no playback before selection, whole-take H3 selection refusal, CAS
  rejection, proposed/selected derivative snapshot restore, disposal refusal,
  post-selection rejection, hash changes, reopening, and Storyboard drift.
  The decoded-media tests also covered two arbitrary in-points with distinct
  picture/audio markers, nonzero PTS, short audio, variable cadence, corrupt
  bytes and invalid windows.
- Frontend TypeScript and E2E TypeScript checks passed; focused video UI
  tests passed (20); the full frontend suite passed (211). The deterministic
  build refreshed the checked-in
  `src/plotloom/static/` bundle; Vite reported its existing large-chunk
  warning.
- Production FastAPI + typed offline H3 fixture browser tests passed:
  two-shot proposal/confirmation and partial-route suppression (2 tests),
  plus the complete four-node native-ended branching journey through both
  choices, reset and project close/reopen (1 test). These are synthetic
  fixture actions, not actual creator or F6 media acceptance.
- The retained read-only walkthrough was opened through the shipped static
  mount at 1440×900 and 1920×1080. Its play view exposed a six-second
  derivative and branch controls; its workbench showed the six-second
  24–168-frame selected proposal with original/request/measured/segment
  labels. A disabled dispatch backend initially hid old H3 review evidence;
  frozen job identity now owns that review mode, with a regression test.
  Screen captures: `output/playwright/reviewed-segment-play-{1440,1920}.png`
  and `output/playwright/reviewed-segment-controls-{1440,1920}.png`.
- Independent read-only review identified the missing snapshot bytes,
  proposal/original disposal link, and legacy H3 selection bypass. After
  fixes and regressions, its closure pass found all three resolved and no
  new correctness issue in that delta.

## Retained isolated inspection copy

The fixture lives only under
`.local/relay/reviewed-playback-segment/plotloom-e2e-Wztf5A/`, not in a
production project or committed source. It was created by the typed offline
H3 browser journey; no real provider call or paid fallback occurred. Project
`2e9c35f3-f200-4154-aac5-4b6e84023ec3` is served read-only at:

`http://127.0.0.1:8824/v2/?project=2e9c35f3-f200-4154-aac5-4b6e84023ec3&view=play`

For the segment controls, use the same URL with `stage=storyboard` instead
of `view=play`, then select the first shot. The local LaunchAgent
`com.plotloom.reviewed-playback-segment-preview` owns the loopback listener,
using `.local/relay/reviewed-playback-segment/serve_preview.py` and
`~/Library/LaunchAgents/com.plotloom.reviewed-playback-segment-preview.plist`.
That preview disables H3 dispatch, clears provider keys before constructing
the app, and rejects all non-GET/HEAD/OPTIONS requests; a POST probe returned
405. After restart on the final code, PID 77361 listened only on
`127.0.0.1:8824` and returned 200 for the play view and 405 for POST.
Inspect with
`launchctl print gui/$(id -u)/com.plotloom.reviewed-playback-segment-preview`.
Stop only this preview with
`launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.plotloom.reviewed-playback-segment-preview.plist`;
the matching `bootstrap` command starts it again. Stopping it does not delete
its isolated evidence. The ignored local README repeats these controls.

## Product acceptance and exclusions

No human creative or audiovisual acceptance is claimed. The source in this
fixture is a synthetic test tone and black frames, not the U4 story or the
rejected/unselected F6 clips. Real H3 output, actual dialogue/lipsync,
editorial window choice and any live canary still require separately scoped
review. No original U4 data or F6 selection was changed; no asset was
deleted, no provider was called, and no Batch C or push was performed.
