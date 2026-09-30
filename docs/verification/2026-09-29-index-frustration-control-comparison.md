# IndexTTS2 · Fixed-line frustration control comparison

**Status:** Four new takes generated and copied with matching hashes. Owner
review rejected P1/P2 as too angry and accepted V1/V2 for the intended
restrained-frustration delivery. Voice Lab/H3/Plotloom remain unchanged;
director handoff and merge/push remain on hold.

## Root-cause question and approved boundary

The [three-line follow-up](2026-09-29-index-chinese-delivery-followup.md) passed
urgency and reassurance review, but the owner could not hear frustration in
F1/F2. Their direction had been reduced to `calm=0.94`, `angry=0.01` before
synthesis. That identifies encoding as the first layer to investigate, not
proof that the speech model lacks the capability.

The owner approved one focused comparison: two positively phrased Chinese-text
takes and two modest explicit-anger-vector takes, keeping original MOSS D,
the F line, seeds `20260930` / `20261001`, alpha `1.0`, pinned source/checkpoint,
native Linux normalizer, and model precision unchanged. Previous F1/F2 remain
unchanged controls. Stop after four new valid clips and service restoration;
no extra prompt search, intensity sweep, or production integration is included.

Spoken text:

> 这已经是第三次了。我不是责怪你，但我们不能再把同一个问题留到明天。

Positive direction:

> 对问题反复出现感到不满和挫败，带一点恼火把要求说清楚。语气严肃、坚定，情绪力度适中，表达克制而有分量。

Explicit vector, in the pinned eight-category order:
`[0, 0.25, 0, 0, 0, 0, 0, 0]`. Only anger is nonzero. This is an exploratory
strength, not a calibrated frustration preset.

## Actual routes and preview

The [runner](supporting/index_frustration_control_trial.py) uses the actual
`use_emo_text=True` path for P1/P2. It observes the helper's return without
altering its values. V1/V2 use `use_emo_text=False` and the explicit vector;
the observer asserts zero classifier calls for that arm. Speech inference is
FP32; the existing helper is FP16. One shared model is loaded and all four calls
run serially. The shared provenance-check runner is not edited.

| Arm | happy | angry | sad | afraid | disgusted | melancholic | surprised | calm |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Positive text preview | 0 | 0.85 | 0.02 | 0.05 | 0.05 | 0.03 | 0 | 0 |
| Explicit vector | 0 | 0.25 | 0 | 0 | 0 | 0 | 0 | 0 |

The preview took 2.09 seconds. The text arm is stronger and contains other
components; this is **not an equal-vector route ablation**. Holding alpha at
1 does not equalize emotion intensity. Equal seed numbers also do not guarantee
identical speech-model random draws across a route that runs a classifier and
one that bypasses it. Do not attribute any difference solely to the route.

Both text synthesis calls matched the preview. Both vector calls bypassed the
classifier and used the specified vector unchanged. This verifies dispatch,
not the perceived emotion.

## Technical results

All four new WAVs are finite, mono, 22.05-kHz PCM16, retained without loudness
normalization or speed changes.

| ID | Duration | Call elapsed | Peak | Full-scale samples |
|---|---:|---:|---:|---:|
| P1 | 5.689 s | 8.80 s | 1.0 | 80 |
| P2 | 5.561 s | 6.74 s | 1.0 | 30 |
| V1 | 6.687 s | 6.99 s | 0.8654 | 0 |
| V2 | 7.825 s | 8.23 s | 0.7705 | 0 |

Elapsed time includes synthesis and output checks, plus classification in the
text arm; it excludes model loading. Full-scale samples warrant listening for
distortion but are not an audible-clipping verdict. Peak Torch allocation was
9.19 GiB, not whole-system or total GPU memory.

Executed: runner syntax check, preview classification, four real inference calls,
waveform finite/shape checks, and local copy-hash checks for all four new takes,
two previous controls, and the original reference. Audition JavaScript syntax
and all seven audio targets were checked. No agent browser/audio perceptual
review, ASR, video lip-sync test, or full product-suite run was performed.
Only experiment support and documentation changed.

## Evidence and audition mapping

- Spark root: `/home/wjmao/services/index-frustration-control-trial/`, with
  both runners, inspect/generation logs, and `2026-09-29/` evidence.
- Local package: `/Users/wjmao/Downloads/moss-d-frustration-controls-2026-09-29/`.
- Fixed audition IDs: **P1/P2** = new positive-text route; **V1/V2** = new
  explicit-vector route; **F1/F2** = unchanged previous failed-target takes.
  Suffix 1 uses seed `20260930`, suffix 2 uses `20261001`. Shuffling changes
  display order only, never those bindings; source reveal preserves audio nodes.
- Runner SHA-256:
  `bd4c89f898572dfad7573a7ad6b72b328558309f3bfd4b71630b0eb8e4a54e10`.
  Shared runner SHA-256:
  `d62610602e999671bf0191f63e599506e5a65cae070b150ac5733efb4cf2d90a`.
- Manifest SHA-256:
  `3cdffbcdd118b5f67a8f0ca287f0eb9da13b108dd9b3b76b74c8ca17da1b334d`.
- Interpretation SHA-256:
  `697596eab68ba91812464c627c4ff51f80221d8edee56ddc741851dbb979a193`.

Before work, Voice Lab was idle, ComfyUI's queue was empty, and GPU utilization
was zero. Qwen Image was temporarily stopped for headroom. The trial uses the
previously qualified Python 3.12 include-directory environment setting; no
packages/models are downloaded and no installed Index source is changed.

After the generation process exited successfully, Qwen Image was restarted.
Its final `/health` returned `ok`, and `/v1/models` identified
`Qwen/Qwen-Image-2.1`. Voice Lab still reported an idle worker, and ComfyUI's
queue was empty at the post-generation check. No concurrent-load test is claimed.

## Owner listening review · 2026-09-29

The owner reported: **P1/P2 are too angry, not 保持克制; V1/V2 are good.**
This accepts the intended delivery in the explicit-vector pair and rejects the
restraint criterion in the positive-text pair. It does not supply a separate
new verdict for identity, exact words, or distortion. The previous F1/F2 remain
failed-target evidence rather than being reclassified through this result.

## Interpretation and bounded stopping decision

The retained sequence now spans calm-heavy F1/F2 (frustration not heard),
anger-heavy P1/P2 (too angry), and modest anger-only V1/V2 (accepted restraint).
Together with observed control signals, this makes direction encoding and
intensity a demonstrated integration concern: Chinese descriptions containing
“克制” or “情绪力度适中” do not reliably produce mild numeric strengths.
Index can produce the requested delivery in this case; the failed text output
is not evidence that its speech model lacks restrained expression.

This is not proof that anger `0.25` is a universal frustration preset or that
one route is intrinsically better. The arms have different vectors, and evidence
is limited to one reference, line, listener, and two seeds per arm.

There is enough evidence to stop this audition series and propose a bounded
Voice Lab integration, not to claim general performance qualification:

- Prior MOSS D reuse review found no reliable same-person advantage between
  Qwen Base and Index in that small set.
- Chinese-description urgency passed on two lines with two seeds each;
  reassurance passed on one line with two seeds.
- Restrained frustration passed here on one line with two seeds only after
  using a modest explicit vector; text interpretation remains fallible.

Recommended integration guardrail: keep voice identity separate from delivery,
make interpreted emotion strengths reviewable and adjustable, and retain an
audition before reuse. Do not silently turn this trial's vector into a fixed
mapping for all frustration requests. The next evidence should exercise actual
project/candidate/reuse operations and serial model loading/unloading, rather
than repeat broad prompt searches. Exact wording, distortion, the Index license,
and downstream video/lip-sync behavior remain separate checks at their relevant
integration boundaries. This recommendation does not authorize implementation,
publish a Voice ID, or lift the director-handoff/merge/push hold.
