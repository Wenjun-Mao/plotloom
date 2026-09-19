# H3 dialogue visual-text robustness study

Date: 2026-09-19
Status: technical execution and initial human creative review complete; broader qualification pending

## Question

A corrected LightX2V v1.0 four-step baseline rendered imperfect visible
subtitle-like text while prompting a Mandarin spoken line. This study separates
two plausible causes without altering a public H3 profile:

1. an undifferentiated prompt that presents literal dialogue as visual prompt
   text; and
2. the declared four-step sampling recipe.

It does **not** establish that any recipe is better overall, and it does not
promote v1.2 or alter Plotloom's production prompt compiler.

## Fixed controls

- one 832×480 astronaut start frame without visible writing;
- 124 frames at 24 fps (5.167 seconds);
- the normal, documented Spark runtime;
- video/audio sigma shifts `6 / 3`, `simple` scheduler and denoise `1.0`;
- seeds `130117`, `41398272`, and `20260919`.

The two four-step recipes differ only in their explicitly declared LoRA and
sampler: corrected v1.0 uses `res_multistep`; experimental v1.2 uses `euler`.
Each recipe was rendered with both prompt contracts:

- `inline_dialogue_v1`: mirrors the current general Plotloom projection, which
  places visual/action/dialogue/sound in one text stream.
- `audio_only_visual_no_text_v1`: explicitly splits visual and audio meaning,
  states that the Mandarin line belongs only to the audio track, and forbids
  visible writing, captions, subtitles, titles, signage, UI text and
  typography.

The full reusable experiment declaration is
[h3-prompt-robustness-study.v1.yaml](../../services/minimax_h3_gateway/h3-prompt-robustness-study.v1.yaml).

## Execution evidence

All 12 direct ComfyUI renders completed successfully. `ffprobe` confirmed each
one is 832×480 H.264 video with an AAC audio stream and a 5.167-second
container duration. No gateway job, active profile, runtime flag, or Plotloom
prompt compiler was changed.

| Recipe | Prompt contract | Seeds | Median elapsed |
| --- | --- | --- | ---: |
| v1.0 `res_multistep` | inline dialogue | 3 | 68.1 s |
| v1.0 `res_multistep` | audio-only / no-text | 3 | 68.1 s |
| v1.2 `euler` | inline dialogue | 3 | 68.1 s |
| v1.2 `euler` | audio-only / no-text | 3 | 68.1 s |

The first use of each recipe was modestly slower because of warm-up; those
values must not be treated as a sampling-quality or performance ranking.

The secret-free receipt, with prompt hashes, Comfy prompt IDs, descriptors and
timings, is retained at
[h3-prompt-robustness-study-2026-09-19.json](supporting/h3-prompt-robustness-study-2026-09-19.json).
The MP4s remain on Spark at:

```text
/home/wjmao/services/spark-comfyui/data/output/experiments/h3-prompt-robustness-2026-09-19/
```

They are direct ComfyUI experiment outputs, not gateway-managed assets; delete
them manually after review rather than expecting gateway retention to apply.

## Initial human review

The reviewer inspected all twelve clips and recorded the following observed
issues. An unlisted clip had no issue recorded in this pass; that means only
that it passed this narrow single-shot review, not that it is globally
qualified.

| Complete recipe | Prompt contract | Seed | Observation |
| --- | --- | ---: | --- |
| v1.0 `res_multistep` | audio-only / no-text | 41398272 | Face/teeth defect. |
| v1.0 `res_multistep` | inline dialogue | 20260919 | Visible subtitle artifact. |
| v1.0 `res_multistep` | inline dialogue | 41398272 | Face/teeth defect, less obvious than its audio-only counterpart. |
| v1.2 `euler` | inline dialogue | 130117 | Face/teeth defect, less obvious. |
| v1.2 `euler` | audio-only / no-text | all three | No issue reported; all three judged good. |

No subtitle was reported for either audio-only condition or for v1.2 inline
dialogue. The evidence supports treating the visual/audio separation as a
useful H3 prompt-contract candidate, but does **not** prove that it alone
eliminates text artifacts: the sample is three seeds from one source image and
the complete v1.2 recipe also changed the LoRA and sampler.

The complete v1.2/Euler plus audio-only contract is the strongest result in
this bounded study. It is a qualification candidate, not a promotion: its
quality must still be checked across more than one shot type, geometry and
frame-conditioning mode before it can replace the current public v1.0
profiles.

## Next decision rule

For every clip, score visible writing (none/minor/material), text legibility,
Mandarin audibility and intelligibility, lip synchronization, continuity,
motion and framing.

- Define and test a named H3-only audiovisual prompt renderer at the adapter
  boundary; do not alter Plotloom's provider-neutral frozen prompt projection.
- Admit v1.2/Euler only as a distinct, opt-in candidate profile, never as an
  in-place reinterpretation of the existing v1.0 profile IDs.
- Before any default change, test that pair on dialogue and non-dialogue shots,
  both landscape and portrait geometry, and start-only plus start/end-frame
  conditioning. Score text artifacts, speech, facial integrity, continuity,
  motion and framing.
