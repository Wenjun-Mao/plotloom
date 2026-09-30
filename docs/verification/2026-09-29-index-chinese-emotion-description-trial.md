# IndexTTS2 · Chinese emotion-description trial with original MOSS D

**Status:** Both Chinese-description takes passed the owner's listening review
for firm, decisive, time-critical delivery. Identity, exact wording, and
distortion have not received a separate verdict for these new takes.
This tests the real `use_emo_text=True` route; it does not
choose a production engine, publish a Voice ID, or change Voice Lab/H3/Plotloom.
Plotloom-director handoff and merge/push remain on hold.

## Question and controls

The [previous comparison](2026-09-29-moss-d-stage2-reuse-comparison.md) used a
numeric vector specifying fear `0.6` and surprise `0.3`. Its file label
“urgent” was experiment metadata, not a written instruction sent to Index.
The owner heard anxiety/fear, not the intended decisive urgency. Therefore
this trial tests a different control route rather than a translation of an
earlier English prompt: **there was no earlier English emotion description**.

Hold the original MOSS D reference, spoken line, seeds, Index source/checkpoint,
native Linux normalizer, precision, and `emo_alpha=1.0` fixed. Send this separate
Chinese emotion description:

> 情况紧迫，果断地制止对方。语气坚定，立即行动，不恐慌、不害怕。

Spoken dialogue remains:

> 等等，别打开那扇门！控制台还在报警，先把电源切断！

Seeds: `20260930`, `20261001`. Equal seed numbers do not guarantee paired random
draws against the previous vector route: this route additionally runs the
emotion classifier. No prompt search, extra intensity variants, or manual
changes to the resulting vector were performed.

## Actual text interpretation

The installed `QwenEmotion` helper first received the direction alone. Its
preview output, and the outputs observed during **both actual synthesis calls**,
were identical:

| happy | angry | sad | afraid | disgusted | melancholic | surprised | calm |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.85 | 0 | 0.05 | 0.05 | 0 | 0.05 | 0 |

Preview classification took 2.51 seconds. These are classifier strengths, not
probabilities or a listening verdict. With alpha 1, no alpha attenuation was
requested. The speech model receives the eight-dimensional interpretation,
**not the free-form Chinese description**. There is no urgency category.
The description was therefore compressed mainly to anger. The owner subsequently
heard the desired urgency in both takes, as recorded below; the classifier's
category name did not itself establish the perceived delivery. Chinese input
alone does not make this a general acting-direction interface.

## Owner listening review · 2026-09-29

The owner reported that both clips labelled **试听 B** sounded
“坚定、果断、时间紧迫”. Because the page randomizes A/B/C, the agent requested
source reveal without a refresh or reshuffle. The owner then confirmed the
displayed source was **Index · 中文描述 → 自动情绪分类（本次生成）**.
This binds the delivery judgment to the new Chinese-description takes at both
retained seeds, not to the old uncontrolled or fear-vector takes.

This is a successful small trial for this reference, line, description, alpha,
and two seeds. It does not establish general emotion control, a naturalness
advantage over Qwen, or a separate identity/wording/distortion acceptance for
these new clips. The earlier anxious/scared judgment for the fear-vector takes
is unchanged.

The reusable lesson is to judge **audible performance against the author's
delivery target**, rather than equating fear with urgency or treating an
internal emotion label as the final performance verdict. Chinese descriptions
are a promising author-facing control to validate further, not a direct
free-form instruction to the speech model. Do not hardcode this anger-heavy
vector as a universal urgency preset.

## Execution and technical evidence

- [Bounded runner](supporting/index_chinese_emotion_trial.py), copied to Spark
  with matching SHA-256
  `d62610602e999671bf0191f63e599506e5a65cae070b150ac5733efb4cf2d90a`.
  Its inspection phase runs only the helper; its generation phase loads Index
  with `use_qwen_emo=True` and uses `use_emo_text=True`, the exact direction,
  and `use_random=False`. A trial-only observer records the helper's actual
  return values without changing them, the source, or RNG behavior.
- Original reference SHA-256:
  `da061210b3e8360c20be8546089d42382f36a8ada64d953b0c151c64fd6088ae`.
- Index source revision: `ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c`;
  installed `infer_v2.py` SHA-256:
  `d954a50f7704a02c4c4fc213492de976f31f984180f77c6998ad29fe9238fbe1`.
- Index checkpoint revision: `740dcaff396282ffb241903d150ac011cd4b1ede`;
  existing `qwen0.6bemo4-merge/model.safetensors` SHA-256:
  `11293257a8df593c154a8ecd5fc039f3076de35411e35f06d41b471e136f6641`.
  No model download was required. Speech-model options remained FP32,
  `use_cuda_kernel=False`, `use_deepspeed=False`; the helper loads FP16.
- Both outputs are finite, mono, 22.05-kHz PCM16 WAVs:

  | Seed | Audio duration | Synthesis-call elapsed | Full-scale samples |
  |---:|---:|---:|---:|
  | 20260930 | 5.283 s | 8.33 s | 78 / 116480 |
  | 20261001 | 4.830 s | 5.86 s | 42 / 106496 |

  Elapsed times include the helper and synthesis, but exclude model loading.
  Both peaks reach 1.0. Full-scale counts are a technical caution for distortion
  review, not proof of audible clipping. Audio was not attenuated or normalized.
  Peak Torch allocation was 8.86 GiB, not whole-system or total GPU memory.
- Manifest SHA-256:
  `be764d5506789447306446161812ae5a54d669780ec9f1d60f36c7a41c8b7f90`.
  Interpretation SHA-256:
  `b9e6a407a452041c221b106baa59a7b7a7904659bd9421868ae45dc4dfba5ad6`.

Spark evidence lives under
`/home/wjmao/services/index-chinese-emotion-trial/`: runner, failed initial
inspection log, successful header-qualified inspection log, synthesis log, and
`2026-09-29/` outputs/manifest/interpretation. The local listening package is
`/Users/wjmao/Downloads/moss-d-chinese-emotion-2026-09-29/`.
It contains the original reference, four unchanged previous Index controls,
and two new takes. All seven local WAV hashes match their retained source
evidence. The page shuffles method order, keeps the same order across the two
seeds, and reveals sources without recreating audio elements.

## Setup issue and scope

The first inspection failed before classifying or synthesizing: PyTorch's
Qwen3 rotary-position matrix multiplication invoked a Triton native kernel,
whose compiler could not find system Python 3.12's `Python.h`. Matching 3.12
headers already existed under the qualified native-normalizer prefix.
Setting trial-process
`C_INCLUDE_PATH=/home/wjmao/services/index-tts2-trial/linux-normalizer/include/python3.12`
resolved compilation. No package installation, source patch, model change, or
normalizer fallback was made. The failed log is retained; it produced no clip.

ComfyUI was empty and GPU utilization was zero before work. Idle Qwen Image was
temporarily stopped for headroom; Voice Lab and ComfyUI remained intact. Service
restoration was checked after generation: Qwen Image restarted and `/v1/models`
returned `Qwen/Qwen-Image-2.1`; Voice Lab was active and ComfyUI's queue was
empty. These checks do not claim an end-to-end concurrent generation test.

## Verification and remaining gate

Executed: runner syntax compilation, both actual inference calls with observed
classifier outputs, audio shape/finite-value checks, all seven copy-hash checks,
audition JavaScript syntax check, and patch whitespace check. There was no
product source change, so the full product suite was not rerun. The local
audition page was not browser-verified by the agent; the owner opens it for
listening. No ASR or video lip-sync check was performed.

The desired urgency delivery is accepted for both new takes. Separate review of
same-person identity, exact words, and distortion, plus validation across other
lines and delivery targets, remains open before integration. Production engine
selection and the Index license gate remain unchanged.

The bounded [three-line delivery follow-up](2026-09-29-index-chinese-delivery-followup.md)
retains two seeds each for new urgency, reassurance, and restrained-frustration
lines. It is a separate listening gate and does not broaden this acceptance.
