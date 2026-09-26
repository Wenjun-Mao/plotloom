# U4 longer continuous opening H3 trial · 2026-09-25

## Scope and source authority

This is one isolated production-shaped experiment, not a change to the original
`暴风灯塔` project or creative acceptance. The director confirmed both lines and
coherent voice/pose in the retained two-shot assembly, but rejected its
unnatural six-second cut. This trial uses one continuous authored 12-second
opening cut for the first four beats: the keeper places the single brass fuse
between two empty parallel sockets without inserting it into either route;
she says `一枚，只够一边。`; rain slides down the thick lantern-room glass; she says
`主灯，或者码头。`. The 12-second choice follows that pacing problem; it is not
the H3 maximum or a claim that longer always works better.

The fresh isolated project is retained at
`.local/relay/h3-longer-shot/outputs`. Before supported writable opening, it
was byte-identical to `.local/relay/bridge-intent-live-u4-source-trial/outputs`;
the historical root and original U4 project were not edited. The source trial
already had real reviewed intent wording, an accepted F5 package, and no
canonical bridge heads or video candidates. Its earlier schema required the
normal storage-open migration in the isolated copy; no database row or head was
fabricated. The copied 57 dramatic-intent entries were matched to the
historical reviewed entries by target, source coordinates/hash/excerpt, and
saved/accepted through the supported bridge path without a new model call.

The isolated Brief's shot-count policy became advisory to permit the existing
reviewed storyboard's 8/9/9-shot source scenes without changing their contents.
The new F5 candidate used the explicit frozen editorial `maxCutSeconds=12`
policy and passed specialist validation/render. The accepted F5 is review r3,
content hash `5fcda26c85e909499818542d956fceff77307ad18ff77f0f9cedb8c63c0fb9c5`;
only the first two six-second E01-01 cuts were replaced by one 12-second cut,
while the other segments/cuts and their durations remained unchanged. The
bridge was explicitly accepted as proposal r5, hash
`4e64cdcbcccb2b3f229d39a8081f3c3b69936707b85ab246d8faef5df74fa9c8`,
then installed StoryBible, SceneBeats and Storyboard revision 1. Canonical
`opening-s1-c1` is 12,000 duration units, with cue IDs
`opening-s1-b2-d1` and `opening-s1-b4-d1`. Storyboard Approval
`41737265-ea6b-4b0e-bbcf-1a4e57558fa6` and reviewed keyframe revision 1
were created only in this development copy; director creative review remains
pending.

## Frozen image, prompt, and single dispatch

The first frame is the retained 1672×941 PNG
`.local/relay/real-shot-trial/opening-s1-c1-keyframe.png`, SHA-256
`7c4c375db892b1b1cbc02136df59ab7fb627affbaf9437e2202b9fb939627d48`.
Its bytes match managed asset `a379fb5d-3c62-4bbc-8f31-f93efc68cfbc` in the
isolated project. Visually, the keeper holds the brass/white-ceramic fuse left
of a green board whose empty sockets are vertically stacked to her right;
rain glass is behind. No end image was bound (end-frame revision 0), and no
new image was generated. The reviewed English directions are source-bound by
hash `4444936058c6fa5d773af247a6fd593c9ff9edaa53057b36e77f5ba1225d8789`.
The complete compiled prompt SHA-256 is
`9629dd4ba213e41ca93785f67a6a52460a8716172527f6a4a88e1cd30493d8a4`:

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] <Picture 1> establishes the opening visual style, composition, subjects, objects, and spatial relationships; preserve them as the action develops in one continuous shot. A steady cinematic medium shot frames the female lighthouse keeper holding the brass and white-ceramic fuse beside the deep-green switchboard. Two empty parallel sockets are vertically stacked to her right. Faded circuit labels and thick rain-streaked lantern-room glass remain behind her in cold storm-blue and amber light; rainwater slides down the glass, 16:9. She carefully places the brass fuse in the space between the two parallel empty sockets without inserting it into either one. The camera remains in one static medium shot throughout the exchange. The visible speaker established by <Picture 1> (S1) speaks with a cool, firm mezzo-soprano voice with steady chest support. She studies the circuit labels. The visible speaker established by <Picture 1> (S1) says once with natural, measured delivery: <d>[Chinese] 一枚，只够一边。</d> The visible speaker established by <Picture 1> (S1) speaks with a cool, firm mezzo-soprano voice with steady chest support. After a brief breath, she confirms the circuit diagram. The visible speaker established by <Picture 1> (S1) says once with natural delivery: <d>[Chinese] 主灯，或者码头。</d> Do not add text overlays or words absent from the reviewed pictures and authored shot.

overall_soundscape: Rain patters softly on the thick lantern-room window glass.

non_diegetic_music: N/A
```

The manager reviewed the complete prompt and frozen snapshot before one
provider POST. Prepared job `vj_1b0ace353c084f9394178f5d23ea98cb` froze
request hash `3d2bc20843b4755e91588884f429a0a3074ebc547be3efab4a4cc92e4619b9b5`
and snapshot hash `9f9ecf7bf753d285caaa93efc0d4fa9ad400e488d6395345c6d992d91b2e82f3`.
It requested quality 8 with profile
`minimax_h3_quality8_landscape_960x544_v2`, 960×544, 12 seconds / 294 expected
frames at 24 fps, native audio, explicit seed `20260923`, and reviewed
`cover_center_crop`. The request uses `segment_required` because the canonical
12-second shot is 288 nominal source frames and requested playback length is
not exact. Neither a trim nor selected playback was authorized.

Gateway health immediately before dispatch was `ok` with zero queued and
active jobs. Exactly one approved submit returned prediction
`h3_2052b9946f934fb5a1e68c87fc1eeead` at
`2026-09-26T01:39:58.807135+00:00`; there was no retry. The ignored
`.local/relay/h3-longer-shot/pre-dispatch.md` preserves the pre-POST record.

## Output and review boundary

The first coarse reconciliation of that exact prediction at approximately
02:00 UTC ingested one current, unselected original. Its stored bytes match
output SHA-256 `35f8d1b4444651055d9b2493d7654b6065e172903441aabb5bedda08eceb6a02`.
The gateway reported generation from `2026-09-26T01:40:00.211Z` to
`01:54:17.340Z` (`857129` ms, about 14 minutes 17 seconds); it did not report
token/cost usage.
Trusted probe and independent `ffprobe` agree on 12.250 seconds, 294 frames at
24 fps, 960×544 H.264 video and 12.250 seconds of stereo 32-kHz AAC audio.
Full `ffmpeg -xerror` audio/video decode returned without error. The exact
[original media](http://127.0.0.1:8840/api/v2/projects/fbb913c8-534b-4439-ba68-211e70ec743d/video-jobs/vj_1b0ace353c084f9394178f5d23ea98cb/media)
loaded in a browser with duration 12.25, readyState 4, and no media error;
its byte-range route returned HTTP 206. This is technical integrity, not
audiovisual acceptance.

Browser screenshots sampled the original at approximately 1, 6, and 11
seconds, retained as `.local/relay/h3-longer-shot/original-1440-t1.png`,
`original-1440-t6.png`, and `original-1920-t11.png`. At 1 second the keeper
holds the fuse free. At 6 and 11 seconds it appears inserted into or pressed
against the *upper* socket while the lower socket remains empty. This is a
material visual source-fidelity concern: the authored action keeps the fuse
between the two sockets without choosing either route. The samples do not
substitute for a whole-take director review or establish the cause of the
model behavior. The agent did not listen to or transcribe the Mandarin audio.
The manager was notified before any editorial action. No segment was prepared,
no media was selected, and no creative approval is implied. The full original
remains available for director listening and visual review.

After ingestion, the credentialed generation server was stopped and a
credential-free, loopback-only process now serves the same isolated project on
port 8840 for this session. Its video backend is disabled; after restart the
job remains ingested/current/unselected and the original media route still
returns HTTP 206. No login-startup service was installed. The director owns
any sound-model/TTS research and the next small, editable end-to-end creator
walkthrough.

## Subsequent director feedback and trial closeout

The director reported that this take was free of intrinsic video defects and
also observed the fuse appearing to enter the upper socket. They explicitly
withheld a story-fidelity judgment until seeing the intended prompt. The manager
then explained that the frozen prompt requires placement between the two empty
sockets without insertion; the director agreed to record positive video-quality
feedback separately from this action-fidelity mismatch and move to the hands-on
creator walkthrough. This is not creative approval, media selection, or general
qualification of quality 8. No additional generation is authorized by closeout.

The result was already ingested when the director asked about the idle gateway;
the manager recovered the worker's final through a bounded task-status read.
Completion was not surfaced promptly to the director. The temporary hourly
reporting watchdog was paused after result recovery. Do not label this as a
successful automatic completion notification.

The full original and frozen prompt remain available as evidence for the
director's H3 specialist. No prompt or model-mechanism conclusion is established
by this single output. No trim, retry, or selection followed the feedback.

## Product verification results

The F5 timing-control correction keeps the existing eight-second default but
freezes each candidate's chosen 2–15-second editorial maximum in its source
review binding; accept/currentness use that frozen policy without loosening
F4 source authority. The UI exposes the curated 8/10/12/15-second choices and
resets the draft to 8 when switching projects. Independent contract review
approved this bounded policy after the project-switch guard. Focused Python
tests passed (37), full Python suite passed (762, one existing Starlette/httpx
deprecation warning), frontend unit tests passed (221), and frontend typecheck
and deterministic build passed (existing large-chunk warning). A read-only
browser walkthrough of the isolated project showed accepted F5 r3, the
12-second Beats 1–4 opening cut and both lines, with the curated timing control.
