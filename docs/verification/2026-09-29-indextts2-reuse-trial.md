# IndexTTS2 Candidate A reuse trial on Spark

**Status:** Eight valid IndexTTS2 audio files generated and technically verified.
Human listening, text accuracy, identity, and acting acceptance are **pending**.
This is an isolated specialist experiment, not a Voice Lab engine, Plotloom feature,
or selected voice. Do not hand implementation instructions to the Plotloom director
yet; the owner has paused that handoff.

## Question and comparison

Can IndexTTS2 reuse a selected candidate voice more naturally, and express an
urgent Mandarin line more convincingly, than the current Qwen3-TTS 1.7B Base
reuse stage? The previous Qwen Base experiment kept Candidate A's identity in
six samples, but the owner found both urgent performances flat.

The six comparable Index clips use the **same Candidate A reference WAV, three
Chinese lines, and numeric seed labels** as the retained Qwen Base experiment.
The additional two Index clips repeat the urgent line with an explicit emotion
vector. Equal numeric seeds do not imply equivalent random streams across
engines. Listen for naturalness, speaker identity, exact words/pronunciation,
and acting separately; this trial does not establish any of those by itself.

- Original Qwen Base evidence: [Candidate A voice reuse](2026-09-26-voice-reuse-trial.md).
- Index runner: [index_tts2_reuse_trial.py](supporting/index_tts2_reuse_trial.py).
- Secret-free per-output receipt: [Index manifest](supporting/index_tts2_reuse_manifest.json).
- Spark Index files: `/home/wjmao/services/index-tts2-trial/experiments/2026-09-28-candidate-a-reuse`.
- Matched local listening copies: `/Users/wjmao/Downloads/plotloom-index-tts2-comparison-2026-09-28/` (`index-tts2/`, `qwen-base/`, and the reference).

## Frozen setup and ARM64 adaptation

- Source: `index-tts/index-tts` commit `ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c`,
  using **IndexTTS2**, not 2.5. Source checkout:
  `/home/wjmao/services/index-tts2-trial/source`; upstream source remains clean.
- Main checkpoint: `IndexTeam/IndexTTS-2` revision
  `740dcaff396282ffb241903d150ac011cd4b1ede`, stored at
  `/home/wjmao/models/index-tts2/2.0`. Main and auxiliary assets occupy about
  11 GiB on Spark. The copied, isolated Python environment is at
  `/home/wjmao/services/index-tts2-trial/.venv` (about 6.6 GiB).
- The official upstream `uv sync` cannot install its CUDA 12.8 PyTorch 2.8 wheel
  on Linux ARM64. The isolated environment instead started from Spark's working
  Python 3.12 / PyTorch `2.14.0+cu130` environment; trial dependencies were
  installed only into that copy. TorchAudio's WAV writer additionally required
  `torchcodec==0.16.0` in this environment.
- Upstream Linux normalization requires `WeTextProcessing` → Pynini; PyPI has no
  ARM64 wheel, and its source build requires unavailable development libraries.
  The runner explicitly selects **upstream's alternative `wetext` normalizer**
  through a trial-local adapter. This changes the text-front-end implementation;
  it is a known comparison limit and **not an approved production workaround**.
- Model inference used FP32, no DeepSpeed, no custom CUDA kernel, and disabled
  the optional Qwen emotion-text model. Uncontrolled clips used no explicit
  emotion vector. Two controlled urgent clips used
  `[0, 0, 0, 0.6, 0, 0, 0.3, 0]` in Index's documented order
  `[happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]`.
- The Candidate A reference SHA-256 was
  `97f1d02937cc70b1dc7a1972333234afbfc7afddeac513b277fd961e9d171dfe`.
  Its original file and the six Qwen comparison files were not modified.

The source API and emotion controls follow the [official IndexTTS repository](https://github.com/index-tts/index-tts#python-api).
The model carries the project's [bilibili Model Use License Agreement](https://github.com/index-tts/index-tts/blob/main/LICENSE),
not a standard permissive code/model license; review its terms before any
product or colleague deployment.

## Execution and observations

The first sample was admitted alone, then the remaining seven ran serially in
one process. All eight final WAVs are nonempty PCM 16-bit mono at 22,050 Hz,
3.924–5.782 seconds. Per-sample inference after model load took 4.43–5.95
seconds. Every local copy matches its Spark `manifest.json` SHA-256; the six
Qwen comparison copies also match their original manifest. One controlled
sample reaches full-scale amplitude for one sample; this is not by itself
evidence of audible clipping.

This is a **technical generation result**, not a creative quality verdict.
Qwen's retained WAVs are 24 kHz, Index's are 22.05 kHz; no resampling or
post-processing was applied to conceal that distinction. There was no ASR or
independent transcript check in this run.

## Memory and service safety

At preflight, Spark had about 29 GiB available unified memory and 11 GiB swap
in use. ComfyUI, the Qwen Image service, an embedding service, and Voice Lab
already held GPU allocations. After confirming an empty ComfyUI queue and
idle GPU, the Qwen Image user service was **temporarily stopped** for the trial;
available memory rose to about 64 GiB. Index's process-reported peak PyTorch
allocation was 7.80 GiB; this is not total system/GPU peak. The Index process
exited after the batch. Qwen Image was restarted and its `/v1/models` response
confirmed the model ready. Voice Lab and ComfyUI were left running.

This does **not** prove that four voice models—or H3, Qwen Image, and Index
generation simultaneously—fit safely. The product direction should keep
checkpoints on disk, use one serial voice worker with a short-lived process
for only the chosen engine, and coordinate active generation across the wider
Spark GPU services before promising concurrent service use. Process exit
releases model/CUDA state more reliably than relying solely on `empty_cache`.

## Decision pending

The owner should compare the matched neutral, urgent, and gentle pairs, then
compare each uncontrolled Index urgent clip with its controlled counterpart.
Record separate judgments for naturalness, identity, wording, and urgency.
Only then decide whether Index deserves a Stage-2 engine option. Stage-1 MOSS
versus Qwen candidate design is a separate decision. No Voice ID or production
engine selection changes result from this experiment.
