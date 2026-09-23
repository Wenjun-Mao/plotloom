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

## Acceptance correction (same day, after initial receipt)

The first receipt above records the original run and its then-excluded stale
bridge assertion; it is not a claim that the exclusion remains necessary.
On the actual parent revision `ca49a09a`, with the same locked environment and
submodule revision, that assertion failed because the bridge already returned
`installedStoryboardCurrent: false`. The test expectation now names that
existing response field, and the complete backend suite passes without
deselection: **728 passed**, one Starlette/httpx deprecation warning. A first
full rerun also found temporary parent-baseline copies inside the repository
via the prompt-template uniqueness check; those diagnostic copies were moved
outside the repository, preserving the evidence, before the clean rerun.

The shot-readiness summary now distinguishes an authored six-second shot from
the qualified eight-second H3 original request. It states the conditional
144-frame derivative path, source/approval/keyframe prerequisites, original
ingest, explicit human segment choice, and disabled dispatch separately. The
segment-review inputs now exist without a prepared proposal, so an ingested
take can be rejected before derivation; the zero-proposal dispatch regression
passes. Full frontend verification: **212 tests passed**, TypeScript passed,
and the deterministic static build was refreshed (existing large-chunk
warning). The marked offline H3 browser journey and the complete native-ended
branching journey each passed against the production FastAPI composition.

For inspection, the task-owned `127.0.0.1:8824` read-only preview now points
to a **new** isolated synthetic fixture at
`.local/relay/reviewed-playback-segment-marked/plotloom-e2e-M2b3Ba/`, project
`b90164f8-ac99-4c81-a20b-8f042bb4327e`:

`http://127.0.0.1:8824/v2/?project=b90164f8-ac99-4c81-a20b-8f042bb4327e&view=play`

The preview injects an unmistakable synthetic/read-only banner, disables
common write controls, refuses all non-GET/HEAD/OPTIONS requests (POST probe
405), and keeps provider dispatch disabled. Its media carries visible frame
number and time labels plus second-varying tones; it is **not** real H3 or
creative acceptance. The previous black-frame fixture and partial marked
fixture remain untouched. The play view was inspected at 1440×900 and
1920×1080; captures are under
`output/playwright/reviewed-segment-marked-{play,controls}-{1440,1920}.png`.
The read-only copy cannot exercise write actions; those were exercised in the
isolated browser test fixture. No live provider was called and no protected
project data was mutated.
Focused independent re-review found one fixture portability issue: a
macOS-only font path. The marker generator now uses Pillow's bundled default
font; the marked H3 browser journey passed again after that correction. No
other scoped correctness finding remained.

## Interactive isolated walkthrough (2026-09-23)

A separate writable technical walkthrough runs through the normal project-folder
API and shipped static UI, but only against the fixture root
`.local/relay/reviewed-playback-interactive/plotloom-e2e-tKXLLu/`. Its
LaunchAgent `com.plotloom.reviewed-playback-segment-interactive` listens only
on `127.0.0.1:8831`, clears text/image/video provider credentials, and has no
provider or generation dispatcher. It does not use or mutate the earlier
read-only 8824 preview, protected U4/F6 evidence, or production projects.

The untouched ready project is `bf515ad1-fbdc-4c8e-beec-066a99fa62a9`;
its opening H3 original remains current but unselected and has no segment, while
the ending segment remains selected. The directly linked opening controls are:

`http://127.0.0.1:8831/v2/?project=bf515ad1-fbdc-4c8e-beec-066a99fa62a9&stage=storyboard&entity=shot%3Ashot_01#video-segment-review-vj_626ad6e39cb544d6ba7908a5a298e28a`

The separate repeatable exercise project is
`a82afa85-3bbd-4bc9-b9af-e3a1cd9c36f4`. In its opening shot, the browser UI
created a new `[48,192)` proposal (144 frames), played the complete six-second
preview with synchronized audio, and explicitly selected it with a technical-
only synthetic note. The segment POST and selection POST both returned 201;
preview/media range requests returned 206. After a LaunchAgent restart, the
selected segment ID, revision, and hashes persisted. The original remained
eight seconds/192 frames with SHA-256
`6523f9a21db4a4ab7756bb179355fe26821189b20f610de455e32b472d994655`; the
selected six-second derivative SHA-256 was
`3c1b8f222ba298310b81dab6c32ab447de6d156baa13bb33ebe7c887bd64957f`. Full
`/media` and `/playback` response hashes matched the original and selected
derivative respectively. The route player completed on the exercise project.
The public backend remained `enabled: false`; attempting the existing-job
submit endpoint returned 503 `h3_video_not_configured`.

The first manual prepare returned 422 because launchd's PATH omitted the
installed `/opt/homebrew/bin/ffmpeg`; the typed segment contract correctly
refused derivation. The LaunchAgent now explicitly includes `/opt/homebrew/bin`
in PATH so launchd has the same media tooling as the interactive shell. No
validation was weakened. After reloading the plist, the same UI action returned
201, and a second restart preserved the selection. Setup, exact links, and
start/status/restart/stop commands are in
`.local/relay/reviewed-playback-interactive/README.md`.

The static frontend adds a fragment target for the segment controls.
The focused E2E walkthrough passed (1 test), including the ready project's
unselected opening state and direct-link placement. The persistent ready link
was visually checked at 1440×900 and 1920×1080 with the safety banner pinned
above the controls; captures are
`output/playwright/interactive-segment-review-anchored-1440.png` and
`output/playwright/interactive-segment-review-anchored-1920.png`. This is a
synthetic technical exercise only, not real H3 output or creative/media
acceptance. The persistent service has provider dispatch disabled; the focused
E2E uses its offline fake gateway, and no external or paid provider was called.
No protected data was changed, and nothing was pushed.
