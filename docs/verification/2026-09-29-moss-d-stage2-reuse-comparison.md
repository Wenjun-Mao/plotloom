# Original MOSS D → Stage-2 voice reuse comparison

**Status:** Technically generated and reviewed by the owner. Both reuse engines
performed well on perceived same-person identity in this small listening set;
the explicit Index urgency takes sounded anxious/scared rather than urgent.
Exact wording, pronunciation, and broader reliability remain **unverified**.
No Voice Lab engine, published Voice ID, H3 workflow, or
Plotloom integration changed. The owner has paused Plotloom-director handoff.

## Question and controlled boundary

The owner preferred the unchanged MOSS D Stage-1 recording over four new D
variants, while still finding it imperfect. This trial holds that exact raw
recording (SHA-256
`da061210b3e8360c20be8546089d42382f36a8ada64d953b0c151c64fd6088ae`)
and its transcript fixed, then asks Qwen3-TTS Base and IndexTTS2 to speak the
same three *new-to-this-reference* Mandarin lines. They are the same neutral,
urgent, and gentle lines used in the earlier Candidate A comparison, enabling
review of how the changed Stage-1 reference affects the existing test.

Both engines used seeds `20260930` and `20261001` per line, but equal numbers
do not equate their random streams. Index additionally produced two urgent
takes with its previously tested emotion vector
`[0, 0, 0, 0.6, 0, 0, 0.3, 0]`; these are a performance-control contrast, not
matched Qwen modes.

## Execution and retained evidence

- [Bounded serial runner](supporting/moss_d_stage2_reuse_trial.py): validates
  the original reference hash and the pinned Index source commit before
  loading a model. Each completed clip is hash-recorded; unrecorded files and
  changed prior outputs block resumption.
- Qwen Base: existing `Qwen/Qwen3-TTS-12Hz-1.7B-Base` checkpoint revision
  `fd4b254389122332181a7c3db7f27e918eec64e3`, BF16/SDPA, in-context
  voice clone with `x_vector_only_mode=False`. Six 24-kHz mono **float** WAVs,
  4.72–6.64 seconds. The first clip ran alone, followed by the remaining five.
- IndexTTS2: source commit `ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c`,
  checkpoint revision `740dcaff396282ffb241903d150ac011cd4b1ede`;
  FP32 with native Linux WeTextProcessing normalizer qualified in the
  [separate normalizer trial](2026-09-29-indextts2-normalizer-qualification.md).
  Eight 22.05-kHz mono WAVs, 4.528–6.026 seconds. The first clip ran alone,
  followed by the remaining seven. One controlled urgent clip reached a
  reported peak of 1.0; this alone is not an audible-clipping verdict.
- Both engines accepted the same original MOSS float WAV without conversion.
  Their output sample formats and loudness were not equalized, so listening
  volume should not be mistaken for naturalness or identity.
- Spark trial root:
  `/home/wjmao/services/voice-stage2-moss-d-trial/`, with `run_trial.py`,
  `qwen/`, `index/`, and run logs. The script copy hash matched the repository
  source before execution.
- Local audition:
  `/Users/wjmao/Downloads/moss-d-stage2-comparison-2026-09-29/listen.html`.
  It groups clips by line, offers the second seed on demand, has a fixed
  source-reveal mapping, and does not recreate audio elements on reveal.
  All 14 local generated WAVs match their Spark manifest hashes; the copied
  original reference matches its earlier hash. Both local manifests are
  secret-free. Their SHA-256 values are:
  - Qwen: `61099b1f4f7d8893da2eb885a3a83b3733a01bc8efa8d60453688bf47d23568c`
  - Index: `9210f642b5e2e6c7f122c1edc6a96c490e256765502d0aec816836be076b673c`

Qwen Image was idle and temporarily stopped to provide Index's memory
headroom. After Index completed, it was restarted and `/v1/models` returned
`Qwen/Qwen-Image-2.1`. Voice Lab remained active, and ComfyUI's queue was
empty at the final check. These are service-restoration checks, not an
end-to-end load/concurrency claim.

## Owner listening review · 2026-09-29

The owner reported that **all clips performed fairly well at sounding like the
same person** and could not distinguish a reliable identity advantage for
IndexTTS2 versus Qwen Base. N2 (Qwen neutral, seed `20260930`) sounded perhaps
slightly younger than the original MOSS D, but the owner explicitly regarded
that impression as too subjective to rely on. This is encouraging for these
lines and seeds, not a general same-speaker guarantee or an engine ranking.

The owner reported that U3 and U5—the two Index clips using the explicit
emotion vector—**did not sound urgent**; they sounded anxious and scared.
The vector specified `afraid=0.6` and `surprised=0.3`, so the result is
consistent with the control signal we gave it. That is an inference about
this trial's direction, not proof that IndexTTS2 cannot deliver urgency.
In particular, fear/anxiety and decisive, time-critical urgency should not
be treated as the same performance target. The controlled takes fail the
intended urgency review despite the earlier finding that the vector has a
material audible effect.

The owner did not provide a separate judgment of exact spoken words,
pronunciation, or which engine sounds more human. Do not infer acceptance of
those dimensions from the positive identity report. The original MOSS D
remains a provisional Stage-1 reference; this comparison does not choose a
Stage-2 engine or publish a Voice ID.

## Remaining review gate

Before integration, review exact words and pronunciation and decide whether
either engine is noticeably more natural after accounting for loudness. Treat
performance direction as a separate workstream: if urgency is retried, define
the desired delivery as firm, quick, and time-critical **without fear**, then
change only that control while holding reference, line, and seeds fixed.
Do not relabel the fear-heavy U3/U5 results as successful urgency.

Technical audio validation alone does not answer the remaining questions. There was no ASR
transcript check, video lip-sync check, or product-level Voice ID decision.
Do not infer general model ranking or select a production engine from these
files alone. The Index model's nonstandard license remains a separate
integration gate.
