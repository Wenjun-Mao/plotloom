# Candidate A VoiceDesign → Base clone trial

**Status:** Six outputs generated and technically checked; speaker continuity,
delivery, and text accuracy await listening review. This is an isolated Spark
experiment, not a gateway feature or a Plotloom Voice ID.

## Question and boundary

The owner preferred synthetic VoiceDesign candidate A and approved its two-shot
H3 reference-video trial. The remaining question is whether that one audio
sample can anchor a reusable character voice across *new* Mandarin lines.
Qwen's documented VoiceDesign → Base-clone route is the mechanism tested here.
No Plotloom or gateway product endpoint was added, and the Plotloom director
handoff remains on hold.

## Reproducible setup

- Spark host `gx10-1523`; isolated environment
  `/home/wjmao/services/qwen3-tts-trial/.venv`, `qwen-tts==0.1.1`,
  BF16 and Torch SDPA. No other service was stopped.
- Base checkpoint `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, immutable Hugging Face
  revision `fd4b254389122332181a7c3db7f27e918eec64e3`, downloaded to
  `/home/wjmao/models/qwen3-tts/base-1.7b` (4.3 GiB on disk).
- Reference: original mono 24-kHz Candidate A WAV, SHA-256
  `97f1d02937cc70b1dc7a1972333234afbfc7afddeac513b277fd961e9d171dfe`;
  exact reference transcript is in the runner. In-context clone mode uses
  `x_vector_only_mode=False` and one reusable prompt, not a new VoiceDesign
  generation per line.
- Runner: [voice_reuse_trial.py](supporting/voice_reuse_trial.py). It freezes
  three lines (neutral, urgent, gentle) and two seeds per line. The first
  sample ran alone before the remaining five; previously completed WAVs were
  hash-checked and skipped. Example invocation on Spark:

```sh
/home/wjmao/services/qwen3-tts-trial/.venv/bin/python \
  /home/wjmao/services/qwen3-tts-trial/experiments/2026-09-26-voice-reuse/run_trial.py \
  --model-dir /home/wjmao/models/qwen3-tts/base-1.7b \
  --reference-audio /home/wjmao/services/qwen3-tts-trial/experiments/2026-09-26/candidate_a_original.wav \
  --output-dir /home/wjmao/services/qwen3-tts-trial/experiments/2026-09-26-voice-reuse
```

## Result and limits

Six WAVs completed at 24 kHz mono with durations 4.88–6.64 seconds and
nonzero signal. All six files copied to
`/Users/wjmao/Downloads/plotloom-voice-reuse-2026-09-26/` and verified against
the per-file SHA-256 values in Spark's `manifest.json`; the copied original
reference also matches its frozen hash. `ffprobe` independently confirmed
sample rate, channel count, and duration. Per-sample generation measured
3.81–4.90 seconds after model load, not a service latency benchmark.

Technical completion does **not** establish same-person identity, good
performance for each emotional context, exact words, or H3 lip-sync. The owner
should compare each clone with A and with the other five outputs, listening for
identity drift, pronunciation, unnatural prosody, and seed sensitivity.
Candidate A remains a preference, not a canonical selected Voice ID. No
automatic speaker score or creative acceptance is inferred from file validity.

## Next decision

If the six samples sound sufficiently like one person, define the minimal
candidate-generation and Voice ID contracts before connecting the Voice Lab's
Generate control. If they do not, preserve these files as negative evidence and
test a different reference length/source or clone engine before productizing.

Official API reference: [Qwen3-TTS Voice Design then Clone](https://github.com/QwenLM/Qwen3-TTS/blob/main/README.md#voice-design-then-clone).
