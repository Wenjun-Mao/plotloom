# Voice Lab audio pipeline: what exists and how to use it

**Scope:** The Spark specialist Voice Lab on `codex/h3-ref2va-gateway`.
This report distinguishes the running service from the intended Plotloom
handoff. It does not claim Plotloom can already consume a Voice ID.

## Purpose and flow

Voice Lab is a casting workspace: describe a character voice, hear alternatives
on one audition line, test whether a chosen voice survives new lines, and
publish the chosen recording as a durable reference.

```text
Project brief + common audition line + candidate direction
  → Qwen3-TTS 1.7B VoiceDesign → original 24-kHz WAV
  → validation/resampling → optional H3-ready 32-kHz WAV
  → blind listening, comparison, selection
  → optional 1.7B Base new-line clone test
  → explicit Publish → immutable Voice ID + independent WAV copies

Future: Plotloom imports Voice ID audio → freezes the audio in a video plan
  → uploads one reference WAV per H3 job → author reviews the resulting clip.
```

The specialist-side steps exist now at [Spark Voice Lab](http://100.64.35.71:8897/).
The Plotloom bridge is **not implemented**. A specialist can manually submit
published audio to the H3 gateway for an experiment, but there is no automatic
Voice-ID-to-video path.

## Author workflow today

1. Open `/` and create or choose a named project. The home page does not
   auto-open old recordings. A project has an editable name, shared voice
   brief, common audition line, candidate slots and lab-only selection.
2. Save the shared brief and audition line. Add candidates, each with a
   distinct written direction. Keeping the line constant helps isolate voice
   differences. The browser can hide directions, shuffle for blind listening,
   and compare two candidates side by side.
3. Generate candidates one at a time. Each request freezes the saved text,
   direction, seed and model revision into a new generation. The serial worker
   reports the number of design/clone jobs ahead, then observed phases and
   elapsed time. Qwen does not supply a trustworthy percent complete or ETA.
4. Listen and choose a current generation as the lab reference. Use **复用测试**
   to make a new-line sample with the Base model. It pins a copy of the
   selected source WAV before queuing. Judge voice identity, pronunciation and
   acting separately. A clone trial is evidence, not a published voice.
5. If the selection is H3-eligible, explicitly **Publish** it and copy the
   returned `voiceId`. Publication makes independent hash-checked copies of
   the original and H3-ready WAV. The read-only Voice ID endpoints resolve
   those exact bytes after refresh, restart, project deletion or later
   candidate regeneration.

Saving edited descriptions never alters previously generated audio. Changing
the brief, audition line or direction during an active generation makes its
result stale rather than current. Failed regeneration preserves the earlier
usable recording; successful regeneration switches only that candidate and
removes the older *unpublished* WAV. Published Voice IDs do not change.

## Identities and audio contracts

| ID | Meaning | Mutability |
| --- | --- | --- |
| `projectId` (`vp_…`) | Named casting workspace | Text and candidate list are editable. |
| `candidateId` (`vc_…`) | Stable slot for one voice direction | Current-generation pointer may change. |
| `generationId` (`vg_…`) | Frozen VoiceDesign attempt | Provenance stays; replaced unpublished files may be removed. |
| `trialId` (`vt_…`) | Base new-line experiment | Pinned input and output belong to this trial. |
| `voiceId` (`voice_…`) | Explicitly published voice | Independent audio and provenance are immutable. |

VoiceDesign produces mono 24-kHz float WAV. The Lab validates and hashes it,
then prepares a separate mono 32-kHz PCM16 reference by deterministic
resampling. H3 eligibility requires **1–10 seconds** and a prepared file of
**at most 2 MiB**. A longer valid original may remain auditionable but cannot
be published as an H3 reference. Retrieval verifies managed paths and hashes;
public API responses contain no server filesystem paths.

SQLite is `$VOICE_LAB_DATA_ROOT/voice_lab.sqlite3`. Unpublished audio lives
under `assets/<candidateId>/<generationId>/`, pinned clone material under
`clones/<trialId>/`, and published copies under `voices/<voiceId>/`. Deleting a
project requires its exact name and no active jobs; it does not delete its
published voices. There is no published-voice retirement API or automatic
Voice Lab media-retention timer yet.

## Models and operational boundary

The Lab uses **two** of Qwen3-TTS's variants:

| Task | Model | Call |
| --- | --- | --- |
| Design a new candidate | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | `generate_voice_design` with text and written instruction |
| Reuse a voice on a new line | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | `create_voice_clone_prompt` then `generate_voice_clone` |

Neither CustomVoice nor either 0.6B variant is used. Checkpoints are under
`/home/wjmao/models/qwen3-tts/` on Spark. The adapter checks weight hashes,
loads on demand with BF16/CUDA and Torch SDPA, then releases the model. One
worker serializes Lab design and clone jobs, **not** H3 or Qwen Image jobs.
After restart, unfinished Lab jobs become `interrupted` and are not silently
replayed. The service is private Tailnet, same-origin, and unauthenticated;
do not expose it publicly. See the [service README](../README.md) for the
systemd unit, configuration and API route list.

## H3 now, Plotloom later

The authenticated H3 Ref2VA gateway accepts one first-frame image and one
audio reference per `POST /v1/video-jobs/from-image-with-voice` job. Its
current admission bounds are 960×544 or 576×1024 video, 5–8 seconds
requested duration, and a 1–10-second mono 32-kHz PCM16 WAV of at most 2 MiB.
It does **not** resolve Voice IDs or maintain a voice library. For a manual
technical trial, retrieve `GET /api/voices/{voiceId}/audio?kind=h3` from the
Lab and submit those exact bytes as gateway `voiceAudio` with the image and
prompt. That is not yet a Plotloom workflow.

The intended Plotloom integration is to let an author bind a Voice ID to a
character, import and hash-pin its frozen WAV in Plotloom-owned storage, and
freeze that selection and exact audio into each production snapshot. The
gateway would still receive one audio upload per job. Canonical Dialogue Cues
and shot prompts would own intended words and acting; the reference guides
identity. Stale or missing references must fail visibly, never silently
switch voice or fall back to ordinary image-to-video. These product contracts
and the Plotloom director handoff remain pending.

The H3 reference is **not** an exact audio track or lip-sync guarantee. Review
each video for same-person timbre, intended words, pronunciation, emotional
delivery, visible mouth timing, extra speech and unwanted subtitles. The owner
heard consistent identity in six Base reuse samples, but both urgent samples
lacked urgency. Favorable two-shot H3 canaries do not establish broad
cross-shot reliability. Whether to use the published audition sample or a
dialogue-specific Base clone as each H3 reference is still an open design
choice.

## Evidence and source map

- [Voice Lab API](../src/plotloom_voice_lab/app.py),
  [model adapter](../src/plotloom_voice_lab/engine.py),
  [media preparation](../src/plotloom_voice_lab/media.py), and
  [published-voice store](../src/plotloom_voice_lab/voices.py).
- [Project/Voice ID decision](../../../docs/adr/0092-voice-lab-projects-and-published-voice-identity.md),
  [progress decision](../../../docs/adr/0093-voice-lab-observed-job-progress.md),
  and [H3 reference contract](../../../docs/adr/0090-h3-ref2va-per-job-voice-reference.md).
- [Spark Lab verification](../../../docs/verification/2026-09-26-spark-voice-lab-implementation.md),
  [project cutover](../../../docs/verification/2026-09-27-spark-voice-lab-project-cutover.md),
  [progress check](../../../docs/verification/2026-09-27-voice-lab-job-progress.md),
  and [Base reuse review](../../../docs/verification/2026-09-26-voice-reuse-trial.md).
