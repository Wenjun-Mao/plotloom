# MOSS-VoiceGenerator isolated Spark audition

**Status:** Technically generated. The owner and a Chinese-speaking friend
subsequently judged the MOSS group slightly better than the Qwen group;
individual candidate selection and product acceptance remain pending.
This is a specialist experiment, not a Voice Lab provider change, published Voice
ID, Plotloom handoff, or reason to retire Qwen3-TTS.

## Question and comparison boundary

The owner finds the current Qwen3-TTS VoiceDesign output unnatural. OpenMOSS
reports a preference advantage over Qwen VoiceDesign, but its published numbers
come from its own 160-sample evaluation. We tested whether its open checkpoint
can run on Spark and prepared matched Mandarin auditions for owner review.

The four A–D cases reuse the exact written directions, spoken line and numeric
seeds from the [earlier Qwen candidate manifest](2026-09-26-voice-candidate-handoff-draft.md).
Numerically equal seeds are useful for repeating *each* model's output; they do
not make different models' stochastic outputs equivalent. An additional urgent
MOSS sample uses the earlier Qwen Base-clone urgent line. That pair is **not** a
controlled VoiceDesign-to-VoiceDesign comparison.

## Spark setup and result

- Official source `OpenMOSS/MOSS-TTS` at Git commit
  `934d6826b084c46a0d033402174d5f8ac4ed2519` is isolated under
  `/home/wjmao/services/moss-voicegenerator-trial/source`.
- VoiceGenerator revision `97521ec2b6f3ec5026ac1f5751f8fc302d82c2d4`
  is under `/home/wjmao/models/moss-voicegenerator`; required MOSS audio
  tokenizer revision `3cd226ba2947efa357ef453bcad111b6eafba782` is under
  `/home/wjmao/models/moss-audio-tokenizer`.
- The official pinned `torch==2.9.1+cu128`/`torchaudio==2.9.1+cu128` install
  cannot resolve on Spark ARM64: the specified torchaudio wheel is x86-64/Windows
  only. The separate trial environment uses Spark's already-proven ARM64
  PyTorch `2.14.0+cu130`, Transformers `5.0.0`, and the pinned MOSS package.
  Triton also needs `Python.h`, absent from Spark's system Python; the trial
  runs with the locally bundled `uv` CPython 3.12.14 and its headers. Neither
  workaround changes the running Voice Lab, ComfyUI, Qwen Image, or other services.
- The [bounded runner](supporting/moss_voice_generator_trial.py) uses the
  model-card decoding values (`temperature=1.5`, `top_p=0.6`, `top_k=50`,
  repetition penalty `1.1`), BF16/CUDA, Torch SDPA and an offline, locally
  pinned model/codec load. Its outputs and hash receipt are on Spark under
  `/home/wjmao/services/moss-voicegenerator-trial/experiments/2026-09-28-qwen-comparison-float/`.
- Five 24-kHz mono float WAVs were generated. The preliminary PCM16 run is
  retained separately as diagnostic evidence: its urgent output exceeded
  full scale and would clip in PCM16. The final run preserves raw float samples;
  the Mac audition folder additionally has a gain-reduced urgent listening copy.

| Case | MOSS duration | Raw peak | Generation time after load | Comparison |
| --- | ---: | ---: | ---: | --- |
| A | 6.00 s | 0.769 | 5.5 s | Qwen VoiceDesign A, 5.04 s |
| B | 12.00 s | 0.615 | 6.5 s | Qwen VoiceDesign B, 5.44 s |
| C | 8.32 s | 0.663 | 3.6 s | Qwen VoiceDesign C, 5.52 s |
| D | 5.92 s | 0.577 | 2.7 s | Qwen VoiceDesign D, 7.52 s |
| A urgent | 8.08 s | 1.113 | 3.4 s | Qwen **Base clone** A urgent, 5.92 s |

All five final file hashes match the Spark receipt after copy to
`/Users/wjmao/Downloads/moss-vs-qwen-2026-09-28/`. The Qwen A–D copies match
the prior frozen manifest hashes. Spark's ComfyUI queue was empty after the
trial, and both Voice Lab and Qwen Image services remained active.

## Listening and decision gate

The owner listened to these clips with a Chinese-speaking friend; both felt
MOSS was **slightly better** than Qwen overall. They did not select an
individual MOSS A–D voice or separately accept wording, character fit, and
prosody for a reusable reference. Do not turn this group-level preference into
an automatic selection. B and C are noticeably longer than their Qwen
counterparts, so investigate pauses, repetition or extra words by listening.
The urgent pair can test acting direction, but it differs in generation mode.

For the later Stage-2 reference search, MOSS A is a **provisional test lead**:
it uses the same written voice direction as the previously preferred Qwen A,
lasts 6.00 seconds, and peaks below full scale. MOSS D is also technically
short enough to audition, but has a different older/deeper character direction.
Neither file has been judged individually more human-sounding; a local blind
audition page is retained at
`/Users/wjmao/Downloads/moss-vs-qwen-2026-09-28/stage1-reference-shortlist.html`.

Even if MOSS wins the short-line audition, VoiceGenerator alone does not prove
stable *same-person identity* across new lines. Before integration, test a
chosen MOSS recording as a frozen reference through an explicit reuse/clone
path, then the existing two-shot H3 voice-reference review. A selected MOSS
sample could only become a Voice ID through the normal provenance, H3-prep,
publication and review gates. Keep the current Qwen pipeline intact until
that evidence and a separate integration decision exist.

Primary references: [MOSS VoiceGenerator model card](https://github.com/OpenMOSS/MOSS-TTS/blob/main/docs/moss_voice_generator_model_card.md),
[MOSS setup guide](https://github.com/OpenMOSS/MOSS-TTS), and
[checkpoint license/release](https://huggingface.co/OpenMOSS-Team/MOSS-VoiceGenerator).
