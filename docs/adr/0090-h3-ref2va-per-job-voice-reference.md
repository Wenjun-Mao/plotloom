# ADR 0090: Ref2VA as a per-job image-and-voice H3 route

**Status:** Accepted for the bounded Spark gateway checkpoint, 2026-09-26.

## Context

The gateway's `quality` values select FL2VA sampling recipes. Ref2VA uses a
different diffusion checkpoint and graph: a first-frame guide and standalone
audio reference feed `MiniMaxH3ReferenceToVideo`. Calling it another quality
would conflate model family, audio provenance and rendering behavior. Direct
ComfyUI trials were reviewed at 960×544/8 s and genuine 576×1024/5 and 8 s;
they establish only this narrow capability, not general voice-cloning or
lip-sync reliability.

## Decision

- Add authenticated `POST /v1/video-jobs/from-image-with-voice`. JSON requires
  `sourceUrl` and `voiceSourceUrl`; multipart requires `image` and `voiceAudio`.
  Both require `prompt`, `resolution`, and `aspectPolicy`; `seed` and
  `durationSeconds` are optional. Mixed input styles, end frames, `quality`,
  `profileId` and arbitrary workflow/model controls are rejected.
- Admit only 960×544 or 576×1024 and whole-second duration 5–8 (default 5).
  This is a technical bound, not an assertion that every intermediate
  duration or authored line is creatively qualified. Existing FL2VA routes,
  four quality values and 5–15 s duration contract remain unchanged.
- Require a 1–10 s, at-most-2-MiB decodable PCM16 mono 32 kHz WAV. Rebuild a
  canonical WAV header without trimming/resampling, preserve the submitted
  bytes privately, and return their SHA-256 only in the 202 admission receipt.
  The prepared WAV has its own frozen digest. Ordinary status omits audio
  hashes, bytes, source URLs and paths. Other audio forms are explicit
  rejections until separately qualified.
- Freeze a versioned Ref2VA snapshot at admission: INT8 ConvRot model identity
  and known checksum, Base-20 recipe with no LoRA or sigma override, first
  frame and prepared voice names/digests, prompt digest, seed, resolution,
  requested duration, 17k+5 frame count, and renderer version. The worker
  validates it and the files before dispatch. It never resolves a voice from
  the mutable FL2VA quality catalog.
- Retain the existing SQLite `input_mode=image|text` column for already
  queued jobs; add `h3_contract=fl2va|ref2va` with default `fl2va` and a
  private one-to-one `job_voice_bindings` table. Public status projects the
  Ref2VA combination as `inputMode=image_voice` and `quality=8` without
  relabeling old jobs. Existing snapshots and jobs are not rewritten.
- Reuse the single H3/Qwen FIFO, unknown-dispatch rule, queued cancellation,
  status/output and 72-hour MP4 retention. Ref2VA audio and prepared inputs
  are released after successful output expiry, or after 30 days for terminal
  unsuccessful jobs; active queued/running inputs are protected. The record
  may be purged at day 30 only after its audio files are released. Gateway
  retention does not define Plotloom's character/Voice Candidate retention.

## Rejected alternatives and consequences

We reject a gateway-wide reusable Voice ID library, a `quality=9` alias,
arbitrary audio transcoding, implicit FL2VA fallback and synchronous video
generation. Plotloom, not the gateway, will own stable Voice IDs and candidate
selection revisions. This route consumes one frozen audio upload per job.
Speech text remains in the prompt; a reference guides perceived timbre and
delivery but is not an exact waveform, transcript or lip-sync guarantee.

The gateway requires its Ref2VA checkpoint and Comfy nodes to be visible at
admission. `/health` reports `voiceReferenceReady` separately so the optional
voice path cannot be mistaken for ordinary FL2VA readiness. Tests guard the
strict route, graph, frozen/restart behavior, non-voice paths, tamper failures
and file/record cleanup.

The private source WAV remains gateway-owned mode `0600`. Its separate Comfy
input copy is also mode `0600`, but owned by the shared input directory owner
so Comfy can read it even when the gateway container runs under another UID.
Failure to establish that ownership rejects admission and rolls back files.
Comfy history `execution_error` is terminal even when its `completed` flag is
false; the public job receives only a stable error code, not a backend traceback.
