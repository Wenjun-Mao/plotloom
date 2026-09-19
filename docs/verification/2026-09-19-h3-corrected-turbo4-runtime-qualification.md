# H3 corrected Turbo 4-step runtime qualification

**Date:** 2026-09-19  
**Source checkpoint:** `10a9131` (`fix: version H3 sampling recipes`)  
**Scope:** one controlled corrected-recipe baseline and an isolated
`fp8_matrix_mult` runtime experiment on Spark. This is not a production
promotion or a broad creative-quality evaluation.

## Fixed conditions

- H3 geometry: `832 × 480` landscape, 24 fps, 124 frames (a five-second
  request, delivered as approximately 5.167 seconds).
- Profile: `minimax_h3_fp8_turbo4_landscape_832x480_v2`.
- Recipe: `lightx2v_fl2va_turbo4_v1_768p` — v1.0 768p LoRA, strength `1.0`,
  four steps, video/audio sigma shifts `6 / 3`, `res_multistep` / `simple`,
  denoise `1.0`.
- A single non-sensitive generated conditioning still, fixed prompt, and fixed
  seed were held constant for all runs. They are intentionally not retained in
  this repository.
- Gateway source was deployed with profile contract version 5; the gateway
  health projection reported `ok` before submissions.

## Technical observations

| Runtime | Observation | Generation elapsed time |
| --- | --- | ---: |
| normal service | corrected baseline | 65.559 s |
| `--fast fp8_matrix_mult` | cold run; includes first-use kernel compilation | 77.217 s |
| `--fast fp8_matrix_mult` | warmed repeat | 69.416 s |
| normal service | first post-restart run | 76.863 s |
| normal service | warmed repeat | 69.721 s |

All retained outputs inspected with `ffprobe` were H.264 video plus AAC
audio, `832 × 480`, 24 fps, and 5.167 seconds. Mid-clip frame inspection found
no black padding or obvious geometry break in either warmed comparison clip.
Different samples should not be expected to be pixel-identical merely because
the seed and conditions are frozen.

## Result and operational decision

The warmed runs differ by 0.305 seconds (less than one half of one percent),
which is not evidence of a useful speed improvement. `--fast
fp8_matrix_mult` remains an unpromoted experiment and is not part of the
restart-safe Spark service.

The service was restored with the required H3 model mount configuration and
verified healthy without `--fast`. An initial restart attempt without the
H3-specific mount made ComfyUI healthy while hiding the H3 files; the gateway
correctly refused new work as `comfy_profile_unavailable`. The reproducibility
guide now records that `spark-h3-mounts.conf` is mandatory.

Host `ffprobe` version 6.1.1 is installed and verified. It is an optional
operator diagnostic, not a gateway runtime dependency.

## Eight-step source-conflict probe

The verified LightX2V 8-step 768p ComfyUI LoRA was installed under the
dedicated Spark model root. Its 1,956,193,000 bytes match SHA-256
`08cfe946033af7d27719b964b6e0a0e50c32138daabbd6ce4137e23df6bf9980`.

Two direct, non-gateway ComfyUI experiments used the same fixed controls as
the baseline, eight steps, Euler/simple, and shifts `6 / 3` or `12 / 3`:

| Candidate | Elapsed time | Technical result | Audio level |
| --- | ---: | --- | --- |
| README `8 / 6 / 3` | 109.092 s | H.264/AAC, 832 × 480, 24 fps, 5.167 s | mean -37.0 dB |
| example graph `8 / 12 / 3` | 98.132 s | H.264/AAC, 832 × 480, 24 fps, 5.167 s | mean -45.2 dB |

These clips are deliberately outside the gateway job lifecycle: the gateway
has no experimental-profile admission route, and a temporary catalog entry
would make an unreviewed recipe selectable. The direct output is private
operator evaluation material in ComfyUI's `output/experiments/` area, not a
gateway-managed delivery and not covered by the gateway's retention worker.
Remove it manually after the recorded review; do not copy it into managed
gateway output storage without a corresponding gateway job record.

Mid-clip still inspection found coherent images for both candidates, but a
single still and level measurement cannot assess temporal consistency,
dialogue intelligibility, or creative quality. Human playback review is still
required.

## Four-step v1.2 probe

LightX2V's v1.2 release note supplies a complete four-step 768p recipe: four
steps, shifts `6 / 3`, Euler/simple, and a stated aim of improved audio quality
relative to v1.1. The installed 1,956,193,000-byte ComfyUI LoRA matches
SHA-256 `c8168ebc17bbacc4296103dda2fec1ba85b24392fa08cf2bfbcef0cff0dc3cc8`.

Its first fixed-control render delivered H.264/AAC, `832 × 480`, 24 fps, and
5.167 seconds in 76.902 seconds after the ComfyUI restart. Its audio
`volumedetect` result was mean -29.5 dB and max -10.1 dB. That is a signal
measurement, not an intelligibility or quality score.

An identical re-submission was fully served from ComfyUI's execution cache in
1.04 seconds and is excluded from every timing conclusion. A distinct-seed,
uncached warmed timing run completed in 66.103 seconds, also with the required
technical media contract. The source manifest records its exact recipe and
vendor source. As with the 8-step probes, these are private direct-ComfyUI
evaluation artifacts, not gateway-managed deliveries; a human must review the
matched-control clip before any profile is proposed for admission.

## What this does not establish

- It does not declare the corrected v2 profiles production-quality for all
  scenes, motion levels, dialogue, or character-continuity cases.
- It does not rank the v1.0 four-step LoRA against a newer four-step adapter
  or the eight-step quality adapter.
- The current LightX2V 8-step material has an upstream contract conflict: its
  model-spec README says `8 / 6 / 3`, while its downloadable I2VA ComfyUI
  graph serializes `8 / 12 / 3`. A later eight-step experiment must record the
  selected complete recipe and cannot silently treat either value as an
  admitted default.
- It does not make an automatic visual or product selection. Those candidates
  need their own complete recipe records and human review under the comparison
  policy in the H3 rationale manual.
