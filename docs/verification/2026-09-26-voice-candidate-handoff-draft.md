# Synthetic voice candidates: specialist evidence and withheld Plotloom handoff

**Status:** Draft for later handoff. This is evidence and a question list, not an
approved Plotloom implementation plan or permission to contact its director.
The owner asked on 2026-09-26 to hold further director instructions until the
specialist-side choices are settled.

## What the specialist has established

- The gateway's accepted [Ref2VA contract](../adr/0090-h3-ref2va-per-job-voice-reference.md)
  consumes one frozen 32-kHz mono PCM16 WAV per image-and-voice job. It does not
  generate voices, manage Voice IDs, guarantee exact spoken words, or perform
  lip-sync measurement. Its admitted bounds are 1–10 seconds and at most 2 MiB
  for the reference, with 960×544 or 576×1024, 5–8-second video jobs.
- The earlier reference was an eight-second WAV extracted from a reviewed H3
  clip (SHA-256 `1982764d633299cb52d3dcf7c2cf1e068cfa511b68c7bbdf72665fdcaa55de4f`).
  It worked in the bounded two-shot and gateway canaries but is not a managed
  character voice asset.
- On Spark, an isolated `qwen-tts==0.1.1` trial generated four fictional
  Mandarin female voice candidates with the same audition text. Model:
  `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`, weights SHA-256
  `391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522`.
  Model files reside under `/home/wjmao/models/qwen3-tts/`; the environment and
  originals are under `/home/wjmao/services/qwen3-tts-trial/`. The original
  24-kHz float WAVs were preserved, with separate 32-kHz mono PCM16 derivatives.
  Full instructions, seeds, file hashes and measured audio properties are in
  `/home/wjmao/services/qwen3-tts-trial/experiments/2026-09-26/manifest.json`.
- The owner preferred candidate A among A–D, while explicitly noting possible
  first-listen bias, and said all four synthetic samples sounded cleaner than
  the extracted H3 reference. This is a subjective audition, not a controlled
  source-quality or model-quality measurement.
- Candidate A's H3-ready WAV is 5.04 seconds, SHA-256
  `a70bd1814953a7c9c9826368bd240408e4217b2f47e9d4cbc4e7da5c7b09e52f`.
  It was tested on the previously reviewed C1 visible-speaking and C2
  lighthouse shots, retaining their first frames, lines, seeds, prompt form,
  model and Base-20 recipe. Both eight-second outputs completed, decoded fully,
  and contain H.264 960×544 plus AAC 32-kHz audio. Output SHA-256 values are
  C1 `c11c0d6d545cbffaf5bda9f9d4aa7650f4da2ec46e2caeda2ba0a240450c7a05`
  and C2 `68bfc9f1f80c5481e4d724ecf00d660885f26bf074142e60e5bb7a8cd0869fa8`.
  The owner reviewed these two clips and replied “all good.” Preserve that as
  bounded acceptance of the pair, not separate numeric scores or broad
  reliability proof. Spark receipts and exact review wording are under
  `/home/wjmao/services/spark-comfyui/data/output/experiments/h3-ref2va-qwen-voice-a-2026-09-26/`.
- The Qwen Image service was stopped only for model setup/generation and then
  restored; its `/health` returned `ok`. No Plotloom product code or gateway
  contract changed during this voice-casting trial.
- A subsequent [Base-clone trial](2026-09-26-voice-reuse-trial.md) generated six
  technically valid Candidate A reuse samples across three new Mandarin lines
  and two seeds. The owner has not yet reviewed their speaker identity or
  performance, so this is not evidence of stable cross-line voice continuity.

## Likely Plotloom ownership when handoff is authorized

These are candidate responsibilities to resolve with the director, **not** an
instruction to begin implementation now.

1. Own a character-scoped Voice Candidate library: immutable audio bytes/hash,
   source kind, model/version/seed or import provenance, transcript/language,
   preparation lineage, duration and technical validity. Preserve source audio
   separately from the gateway-ready derivative. Imported human voices need a
   permission/provenance policy; the initial scope is synthetic voices.
2. Make audition and selection explicit. A stable Voice ID or selection record
   should point to an approved candidate revision; changing a descriptive
   prompt must not silently regenerate or replace that voice. Show comparison,
   approval, replacement/revocation and currentness in the character workflow.
3. Keep identity, performance and dialogue separate. The selected reference
   guides timbre; canonical Dialogue Cues and shot prompts own words and acting
   direction. Do not infer exact transcription or lip-sync from the reference.
4. Freeze the selected candidate ID, audio hash and prepared bytes into each
   video production snapshot. Upload that exact WAV per job through
   `POST /v1/video-jobs/from-image-with-voice`; the gateway deliberately has
   no reusable Voice ID resolver. Plotloom must retain its own selected audio
   independently of gateway input/output expiry and must not silently fall
   back to ordinary FL2VA or switch voices on retry.
5. Review generated dialogue as an audiovisual result: same-person voice
   across shots, intended words, visible mouth timing, extra speech and
   subtitles. A future ASR/alignment pass may supply evidence and timing, but
   must not automatically grant creative approval.
6. Cover stable selection, revision/currentness, exact audio handoff, restart,
   missing/stale reference, cancellation and unknown-dispatch behavior in
   tests. A technically successful job must remain reviewable, not
   auto-approved.

## Decisions still open on the specialist side

- Whether candidate generation becomes a Spark API/service, a bounded offline
  specialist workflow, or both; no Qwen3-TTS endpoint exists today.
- Candidate count, audition scripts, blind/level-matched comparison policy,
  and whether another voice engine is needed as a quality comparator.
- Whether a selected candidate should also feed a separate TTS/clone path for
  off-screen lines. The VoiceDesign-then-Base-clone mechanism now has a bounded
  technical trial, but its six outputs still need listening review. H3 Ref2VA
  currently uses only the frozen WAV.
- Plotloom-side retention and consent policy, and exact selection/currentness
  rules, must be decided before proposing a product schema.

**Handoff rule:** Do not send this draft to the Plotloom director, merge it to
main, or represent candidate A as a canonical Voice ID until the owner releases
the hold and the open decisions are reviewed.
