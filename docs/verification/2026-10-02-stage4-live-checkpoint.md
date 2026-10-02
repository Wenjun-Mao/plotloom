# Stage 4 live checkpoint: real media, acceptance still open

Status at 12:40 UTC / 08:40 Toronto, 2026-10-02: **partial, not complete**.
The Mac locked during review; computer-use inventory reports that automatic
unlock failed and requires manual unlock. Dependent UI work is stopped, with
no pending image/video generation. The owner has been asked to unlock the Mac.
The approved stop-new-work boundary remains 13:04:18 UTC and hard cutoff
13:34:18 UTC. This receipt does not extend either boundary.

This follows the [source gate](2026-10-02-stage4-source-gate.md) and
[stages 2–3 live completion](2026-10-02-stage23-live-completion.md) under the
[approved walkthrough](../roadmap/2026-10-02-unattended-creator-walkthrough.md).
All content approvals, identity reviews and keyframe choices below are
provisional agent decisions in the isolated copy, not owner creative acceptance.

## Committed deployment and preservation

Implementation `bd3ffd9d255f9b66502ca003da6a6ef95d166daa` is pushed to `main`.
It includes the post-install common-provenance repair. After an idle checkpoint,
the manager cleanly stopped only its previous isolated process and started
the same installation through the committed launcher. Current owner is this
manager chat; PID **89547**, exec session **18618**, ports **8851/8852**.
The copy has explicit H3 opt-in and the process-only current v7 catalog override.
Credentials and dotenv were not rewritten. Both source and copy served static
trees are identical; this repair required no new static promotion.

Only normal container `plotloom-creator-workbench-1` was restarted for the
repair; the normal native bridge was untouched. Normal H3 remains disabled.
Fresh checks at approximately 12:37 UTC confirm both workbench health endpoints,
the healthy normal container, the owned copy process, and matching static.
The earlier isolated online gap remains unexplained; uninterrupted availability
is not claimed. The current copy process is deliberately retained for review.

Copy URL: <http://127.0.0.1:8851/v2/?project=ee271b49-f384-414c-9711-452ee6333b84>.
Data root: `.local/unattended-2026-10-02/final-installation`.
Normal workbench: <http://127.0.0.1:8841/v2/>.

Original-project verification after deployment and again at 12:43 UTC shows
**all 73 database tables and 67 file hashes exactly equal the launch baseline**.
The only API projection delta is the common-provenance repair exposing
`rightsNote: null` and `declaredAdditions: []` on three retained art assets.
Those defaults do not rewrite their stored declarations, acquire rights, or
prove that no additions were made. Other original source/state facts are
unchanged. The latest API capture exactly equals the post-deployment capture;
the original launch baseline was not rewritten.

Evidence: `evidence/manager-provenance-after-deploy-original.json`,
`evidence/manager-real-media-midrun-original.json` and
`evidence/manager-stage4-lock-checkpoint-original.json`, beneath the workflow root
`.local/unattended-2026-10-02/`.

## Actual creator UI milestones

- Whole presentation ownership was explicitly reviewed and saved; 15 manual
  dramatic intents were labelled as provisional test content. Proposal r3,
  hash `b5834e09e75fb21e2bb8c130e39a55f31b9edfa6db1777f1374b703a0779aacc`,
  was explicitly installed. Canonical story-bible, scene-beats and storyboard
  heads are current at revision 1. Raw F4/F5 evidence remains retained.
- The formerly blank storyboard workbench recovered after the provenance
  deployment and displayed all nine pre-production assets. A new explicit
  Storyboard Approval `35028ac8-e016-4340-a136-6f5af4365f1d` was created.
- Preparation correctly refused the old cast-owned C01 reference decision.
  ADR 0061 requires an explicit story-bible-owned review, not implicit fallback.
  The UI re-reviewed the same retained photo as reference r3,
  `fafa8b50-7309-4e07-8c5f-5d40c7e06dc7`, against the installed bible and
  accepted Cast r3. Old decision/history and image bytes remain preserved.
- A fresh image worker was explicitly bound in Settings: GPT-6 Luna / Max,
  chat `01a0fc5f-7712-76c2-b407-99e9c38e6658`. Four packages were individually
  prepared, exported and sent. All four have current, technically accepted
  delivery receipts pinned to `bd3ffd9` and the current image skill.
- Only the first two images were explicitly reviewed and selected as keyframes,
  with source-bound VisualIntents and same-person review records. Two English
  H3 packages were previewed, frozen and dispatched once each through the UI.
  The first take was played in the actual workbench and a continuous 60-frame
  proposal was prepared. **No video or derivative was selected for the story.**

The exact post-opening question remains “林遥要如何回应这条消息？” with
“去咖啡馆赴约” and “今晚先回家” as runtime choices, not generated image text.
The manager independently read the first complete frozen H3 prompt and its
source chain; raw F5 multi-shot/runtime-choice instructions did not enter it.

## Real-media results

| Shot | Image job | Result |
| --- | --- | --- |
| opening-s1-c1 | `ij_811a4b2e690b4b1babdc5a957d63fcab` | Single character/phone/porch; selected provisionally. First frame already has a faint screen glow, which the reviewed video directions preserve and brighten. |
| opening-s1-c2 | `ij_a47a38ff10f54152a52156047124a438` | Exact “我还在老地方。” visibly readable in the still; selected provisionally. This does not certify the generated video's text. |
| opening-s1-c3 | `ij_c4558e0c8a794acbb29bc64e8939d407` | Technically admitted but unselected: rural valley, misty hills and changed porch conflict with the first two town-street shots. No H3 dispatch. |
| opening-s1-c4 | `ij_30d0e38c56c04c7fbd4893d050855f7e` | Technically admitted but unselected: plausible close-up, but gaze is already raised. First-frame alignment with the authored lifting action remains unresolved. No H3 dispatch. |

Stills 1, 2 and 4 are 1672×941; still 3 is 1672×940.
Current image preparation supplies C01 identity
images, not selected S01/S02/P01 art images. Scene/prop continuity is therefore
text-guided, not image-conditioned. No cross-shot reference was silently added
to a frozen package. The third still's mismatch is observed; absence of scene
conditioning is a relevant current limitation, not proof of a unique model cause.

Each specialist attempted its prescribed staging cleanup once. The first
attempt refused a task-root mismatch; later attempts refused the
tool-owned 0755 directory against the private-directory contract. All exact
staged outputs remain preserved. No chmod, broad search/deletion, repeated
cleanup attempt or helper-contract weakening was used to force success.

Both H3 jobs use quality 8, landscape 832×480, native audio, an explicit
center-crop decision, five-second requested capacity and no end frame.
Canonical shot duration remains **2500 ms** with `segment_required`, never
silently retimed to the request. Both ingested originals measure **124 frames
at 24 fps / 5.167 seconds**, H.264 video and AAC audio.

| Shot | Video job | Review state |
| --- | --- | --- |
| opening-s1-c1 | `vj_4d259d91e0c049f985aedcfbd12ac469` | Visually plausible screen brightening and stable composition. A current `[0,60)` derivative exists, but remains unselected pending genuine sound review. |
| opening-s1-c2 | `vj_20d20f212c9f4ba5a33b4d81befd98eb` | Generated message glyphs are blurred/deformed; exact readable text is not verified. Visually unsuitable, ingested and unselected. The intended UI rejection did **not** persist: server `reviews` is still empty. |

The first derivative is `7b204194-18a8-4758-bcb3-b7eb714f6ea1`, SHA-256
`16b38b978c90e1034c683f21059eedf77c9f7796ab368aa20017f3ab391052db`.
Independent hash/probe checks confirm 60 frames at 24 fps and 2.500-second
video/audio/container duration. Stored decoded audio evidence is 80,000
samples at 32 kHz. Arithmetic and successful decoding do not establish
audible boundaries or creative acceptance.

## Acceptance gaps and reusable observations

1. **Sound cannot be auditioned in this session.** Tool audio input explicitly
   reported unsupported. Unmuted browser playback and AAC presence are not
   evidence that an agent heard the track. ADR 0082/0083 require final-segment
   sound review; the manager kept all real derivatives unselected. No claim
   of absent speech, appropriate ambience or sound continuity is made.
2. **Readable still text did not survive this video trial.** Both independent
   reviewers inspected native frames and found the incoming sentence could
   not be reliably certified. Source phone/text pixel size at 832×480 versus
   generative reconstruction is an open causal question. A later controlled
   tighter-phone/native-resolution legibility test is reasonable; blind repeat
   dispatch or a general claim that H3 cannot render Chinese is not supported.
3. **A nice still is not necessarily a faithful first frame.** The fourth image
   already depicts raised eyes. Do not manufacture a down/up loop or claim the
   full authored lifting action from a stationary raised-gaze video. Preserve
   the candidate and review initial-state/action alignment before dispatch.
4. **Cross-shot setting consistency is not implied by identity consistency.**
   The third still's new rural geography is not accepted as a camera-angle
   variation. A planned, observed-scene-grounded requirements revision was not
   dispatched before the lock. Any future scene-reference consumption changes
   need their own durable input contract, not package tampering.
5. **Host lock, not a proven product mutation failure, stopped interaction.**
   The rejection click stalled and subsequent inputs did not act. A pending
   JavaScript confirmation was initially suspected from the control source,
   but is unproven. Computer-use inventory subsequently reported the locked
   Mac and failed automatic unlock. No API-write fallback or security bypass
   was used; inspect dialogs and read server state after manual unlock before
   retrying the intended review.

No reply typing/send/retention media was generated, including ending-b cut 3's
indirect reference to the previous reply. Its literal-text authority remains
an open source-input review item; no freeform text override was invented.
The remaining eight shot keyframes and ten shot videos are absent. All twelve
shots lack a selected reviewed playback segment, so **neither real-media route
is playable**. Both actual job playback GETs correctly return 404/no reviewed
playback segment. The prior actual Storyboard reader and synthetic both-route
browser tests remain separate evidence, not real-video completion.

## Verification and evidence index

The final production-presentation implementation passed 964 Python tests,
46 service checks, 294 frontend tests and both typechecks. The subsequent
small provenance repair passed the independent affected 111-test backend gate,
46 service checks, 295 frontend tests, both typechecks and focused real-component
mixed-asset checks; 16 committed recovery/pin checks then passed. These are
different, overlapping checkpoints: the full 964-test suite was not rerun after
the small repair. Source-gate browser playback uses synthetic media.

Manager live verification includes frozen request/receipt/pin review, actual
still inspection, output hash checks, H3 original/derivative probes, sampled
frame review, unselected playback refusal, original preservation, static
equality and normal/copy health. Repository CI is manual-dispatch only; no CI
run exists for `bd3ffd9`, and no CI success is claimed. No measured cost or
usage delta is available. Private Tailscale presence was inspected earlier;
no Serve route or remote viewer was configured/qualified because the retained
review path is local.

A separate GPT-6 Luna / Max read-only checkpoint review confirmed the live
state, preservation comparison and resume boundaries. Its delivery-versus-selection
wording finding was corrected: four still deliveries are not four selected
keyframes. The manager also verified the distinct third-image height, all four
image output hashes/pins and all three retained video-copy hashes.

Evidence directory: `.local/unattended-2026-10-02/stage4-live/`.

- `stable-live-checkpoint.json`, `manual-review-notes.json` and refreshed
  `live-{bridge,image,video,visual}-state.json` contain exact job, request,
  output, currentness, approval and selection facts.
- `recovered-approval.jpg`, `c1-h3-actual-playback.jpg`,
  `c1-h3-submitted.json`, `c2-h3-prepared.json` document actual live milestones.
- `c1-h3-raw.mp4`, `c2-h3-raw.mp4`, `c1-h3-segment-0-60.mp4` are verified
  copies of the retained managed originals/derivative, not fixture media.
- `c1-all60frames.png`, `c2-boundaries.png`, `c2-text-pixel-detail.png` and
  `manager-c*-*.png` record visual review. Contact sheets are sampled or
  downscaled views, never audio evidence or proof of continuous legibility.

The image worker and coordinator are idle; the image worker remains available
for a possible owner-authorized continuation before cutoff. No provider dispatch
is pending or uncertain at this checkpoint. The manager retains the copy server
and owns final documentation/runtime/monitor cleanup.

## Exact continuation

Manually unlock the Mac and report that it is unlocked. Before any new action,
verify the remaining run boundary, inspect the actual browser/dialog state and
refresh current source/review state. Record the intended second-video rejection
only through an explicit supported control, without assuming the earlier click
succeeded. The owner must listen to the first original and final 2.5-second
proposal before choosing it. Source-critical reply media, third-shot scene
continuity and fourth-shot first-frame alignment then need bounded review;
do not submit fresh work after the stop-new boundary or count this receipt as
permission to extend the run. No existing generation needs replay.
