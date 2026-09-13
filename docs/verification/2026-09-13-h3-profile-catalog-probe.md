# MiniMax-H3 v2 profile catalog — Spark probe receipt

Date: 2026-09-13

Scope: direct, serial verification of the six new selectable MiniMax-H3
profiles implemented in `47a0dc5`. This is an operational media-contract
probe, not a creative-quality or production-readiness evaluation.

## Why this probe was needed

The catalog deliberately forbids callers from supplying arbitrary dimensions.
It freezes one reviewed profile ID in every new job, but that source contract
is useful only if the independently deployed Spark gateway produces the exact
claimed media for every selectable profile.

## Method

- The deployed gateway reported profile contract version 2 and the expected
  seven safe descriptors (six selectable plus the historical-only 864×480
  descriptor).
- One existing non-user test keyframe was uploaded once. Each selectable
  profile ran serially with `contain_pad`, a fixed seed, and the same neutral
  test prompt. Serial submission avoided GPU contention between profiles.
- Each successful MP4 was downloaded from the gateway and inspected locally
  with `ffprobe`. Spark itself does not include `ffprobe`; moving the
  inspection to the control machine fixed that tooling gap without changing
  the gateway or weakening its output contract.

## Results

| Profile | Delivered geometry | Video | Audio |
| --- | --- | --- | --- |
| `minimax_h3_fp8_turbo4_portrait_576x1024_v1` | 576×1024 | H.264, 124 frames, 24 fps | AAC, 32 kHz stereo |
| `minimax_h3_fp8_turbo4_portrait_608x1088_v1` | 608×1088 | H.264, 124 frames, 24 fps | AAC, 32 kHz stereo |
| `minimax_h3_fp8_turbo4_portrait_704x1280_v1` | 704×1280 | H.264, 124 frames, 24 fps | AAC, 32 kHz stereo |
| `minimax_h3_fp8_turbo4_landscape_832x480_v1` | 832×480 | H.264, 124 frames, 24 fps | AAC, 32 kHz stereo |
| `minimax_h3_fp8_turbo4_landscape_960x544_v1` | 960×544 | H.264, 124 frames, 24 fps | AAC, 32 kHz stereo |
| `minimax_h3_fp8_turbo4_landscape_1280x704_v1` | 1280×704 | H.264, 124 frames, 24 fps | AAC, 32 kHz stereo |

All six outputs matched their frozen profile geometries exactly. No job was
resized, retried through a different profile, or accepted through a fallback.
The temporary input and downloaded probe outputs were removed after
inspection; this receipt intentionally contains no keys, private endpoint,
job ID, prompt text, model path, or media file.

## What this establishes—and what it does not

The catalog is now an operationally evidenced output contract: the default
576×1024 portrait profile and the five other selectable profiles can deliver
their declared codec, frame, audio, and geometry shape through the deployed
gateway.

It does **not** establish comparative creative quality, no-stretch visual
quality beyond the configured `contain_pad` policy, dialogue quality,
character identity continuity, cross-shot continuity, throughput, or general
production readiness. Those require the next retained, human-reviewed
adjoining-shot evaluation with a scoped character reference.

See [ADR 0036](../adr/0036-minimax-h3-profile-catalog.md) for the frozen
catalog contract and the [H3 gateway manual](../operations/minimax-h3-gateway-manual.md)
for deployment and operating boundaries.
