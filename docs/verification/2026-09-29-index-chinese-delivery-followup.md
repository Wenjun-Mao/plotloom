# IndexTTS2 · Chinese delivery directions across three new lines

**Status:** All six takes generated and copied with matching hashes. Owner
listening acceptance is pending. No production integration,
Voice ID publication, Plotloom-director message, merge, or push is authorized here.

## Approved slice and stopping condition

Following the owner's acceptance of both Chinese-description takes in the
[urgency trial](2026-09-29-index-chinese-emotion-description-trial.md), the owner
approved testing a few new lines and delivery directions before integration.
This slice generates exactly three new Mandarin lines × two retained seeds,
using original MOSS D and the actual Index `use_emo_text=True` path. Stop after
six valid outputs and service restoration; listening review is a separate gate.
No prompt fishing, intensity sweep, new engine, video generation, or production
API/UI change is included.

## Frozen cases

The [runner](supporting/index_chinese_delivery_followup.py) contains the exact
spoken text and separate Chinese direction. U1/G1/F1 use seed `20260930`;
U2/G2/F2 use `20261001`. These audition identifiers are stable, unlike the
randomized A/B/C labels in the previous comparison.

| Audition | Intended delivery | Spoken line |
|---|---|---|
| U1 / U2 | Firm, decisive urgency; not fear/panic | 先停下来，别碰那个开关！把人带到出口，我马上切断主电源。 |
| G1 / G2 | Gentle, patient reassurance; not exaggerated soothing | 别着急，我在这里。先慢慢呼吸，等你准备好了，我们再一起往前走。 |
| F1 / F2 | Restrained frustration; not scolding, sarcasm, or self-pity | 这已经是第三次了。我不是责怪你，但我们不能再把同一个问题留到明天。 |

The urgency direction is unchanged from the accepted trial, testing a new line.
The other two directions are new. Original MOSS D's reference hash, Index
source/checkpoint, native Linux normalizer, FP32 speech inference, FP16 helper,
alpha `1.0`, and `use_random=False` are unchanged. The runner reuses the previous
runner's provenance checks and records both scripts' hashes; retained evidence
and the shared runner are not edited.

There is no same-line uncontrolled arm in this batch. It tests whether these
outputs meet the target, not whether the description alone causally produces
each performance. Different lines can themselves influence delivery.

## Preview interpretation

The helper receives each direction, not its spoken line. Scores are classifier
strengths, not probabilities or audible-performance judgments:

| Direction | happy | angry | sad | afraid | disgusted | melancholic | surprised | calm |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Urgency | 0 | 0.85 | 0 | 0.05 | 0.05 | 0 | 0.05 | 0 |
| Reassurance | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1.0 |
| Frustration | 0 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.94 |

The calm-heavy frustration interpretation is retained without a manual vector
override or rewritten prompt. Actual scores during every synthesis call are
observed and checked against these previews in the manifest. The speech model
does not directly read the descriptive instructions.

All six synthesis-call interpretations matched their previews. That establishes
repeatable classification in this batch, not successful audible delivery.

## Generated audio and checks

Every clip is finite, mono, 22.05-kHz PCM16. Outputs were not normalized or
attenuated for audition.

| Audition | Duration | Call elapsed | Peak | Full-scale samples |
|---|---:|---:|---:|---:|
| U1 | 5.608 s | 8.69 s | 1.0 | 46 |
| U2 | 6.060 s | 7.18 s | 1.0 | 223 |
| G1 | 5.747 s | 6.90 s | 0.4848 | 0 |
| G2 | 5.700 s | 6.78 s | 0.5854 | 0 |
| F1 | 5.492 s | 6.63 s | 0.6692 | 0 |
| F2 | 5.747 s | 6.87 s | 0.5686 | 0 |

Call elapsed includes the helper, synthesis, and file checks, but excludes model
loading. The full-scale counts are a reason to listen for distortion, not a
claim of audible clipping. Peak Torch allocation was 8.99 GiB; this is not total
GPU or whole-system memory.

Executed: runner syntax compilation, three preview classifications, six actual
speech-inference calls with classifier observation, waveform shape/finite-value
checks, and hash checks for the six local copies plus original reference.
All seven HTML audio links point to existing files; inline JavaScript passes
syntax checking. The audition page was not agent-browser-verified. No ASR,
video/lip-sync, or full product-suite run was performed: this slice changes
experiment support and documentation only, not product runtime code.

## Evidence locations and runtime boundary

- Spark: `/home/wjmao/services/index-chinese-delivery-followup/`, containing the
  two script copies, inspection/generation logs, and `2026-09-29/` artifacts.
- Local audition: `/Users/wjmao/Downloads/moss-d-delivery-followup-2026-09-29/listen.html`.
- Follow-up runner SHA-256:
  `3166bec88ee630f46e137ffdabd64074fc24e6315e62c9208370cf8bc255d6a2`.
- Unchanged shared runner SHA-256:
  `d62610602e999671bf0191f63e599506e5a65cae070b150ac5733efb4cf2d90a`.
- Manifest SHA-256:
  `400e6d2f2095a8cb4b9113b82b02644a00de698046aa70406d21e602d28b6dba`.
- Interpretation SHA-256:
  `c005fc4b72893a91800fc81406fe3d2e55e9be3fd0b9757940105972f80864e2`.

Before work, Voice Lab reported `workerActive=false`, ComfyUI's queue was empty,
and GPU utilization was zero. Idle Qwen Image was temporarily stopped for memory
headroom. The trial uses the existing Python 3.12 include-directory setting
qualified previously; no models or packages are downloaded, no installed Index
source is changed, and Voice Lab/ComfyUI remain intact.

After all six calls exited successfully, Qwen Image was restarted. Its `/health`
returned `ok` and `/v1/models` returned `Qwen/Qwen-Image-2.1`. Voice Lab's health
check still reported `workerActive=false`; ComfyUI remained empty at the
post-generation check. No concurrent-load claim is made.

## Pending review

For each fixed audition ID, review same-person identity, exact spoken words,
target delivery, and any distortion. Do not infer general instruction following,
naturalness superiority, or production readiness from six outputs. Preserve the
earlier accepted urgency finding separately. Index's license gate is unchanged.
