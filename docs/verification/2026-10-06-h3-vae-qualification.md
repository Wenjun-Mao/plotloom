# H3 VAE qualification — execution ledger

**Status: stopped after one baseline component smoke; baseline restored.**
No full clip was submitted. This is not passed qualification, adoption or creative
acceptance. The harness correction below was verified offline against retained
observations, not by another GPU workload.
The owner approved the [four-arm plan](../roadmap/2026-10-06-h3-vae-qualification.md)
on October 6. Twelve full-generation attempts maximum; one small component smoke
per arm. No production API, recipe, Comfy version or model-installation reset.
Integration, director contact, merge and push remain held.

## Frozen controls and implementation

- Exact Comfy 0.38 image/commit remain fixed, with the baseline global BF16
  flags. B changes video-only precision; C adds FP16 accumulation; D changes
  only the video checkpoint relative to C.
- Official INT8 asset pinned to upstream revision
  `e5eb578a89295337b8ff433a035929ce0279e0b6`; downloaded SHA256 matches
  `52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e`.
  The existing FP16 video and FP32-storage audio files are retained.
- Frozen three-case document hash:
  `b5971616b3a8edd89e4360000e617c10938ef9675fd5e0923c8e888f3430257b`.
  Exact-size reviewed landscape/portrait references and a retained lighthouse
  image/performance reference; no new image/voice or resize/crop/pad.
- The retained Ref2VA performance reference is 4.551 seconds; all clips request
  124 frames at 24 fps. Its existing possible-source-clipping warning remains;
  no gain or voice adjustment is part of this trial.
- Operator module: `services/minimax_h3_gateway/tools/vae_qualification/`.
  Isolated custom video loader, compute pre-hooks, successful kernel counters,
  synchronized stage/outer timings, scoped model-load timings, memory trace,
  full-stream decode and exclusive uncertainty-first no-replay runner.

## Pre-generation review and checks

One monitored, read-only GPT-5.6 Terra review found four material harness issues:
CPU staging mistaken for GPU compute, missing pre-smoke stopped-state guard,
missing exclusive receipt lock, and incomplete timing/parameter proof. All four
were corrected, with focused regressions. The same reviewer verified those
specific corrections and found no residual blocker; no second general review.

| Check | Result |
| --- | --- |
| Locked focused experiment tests | 20 passed |
| Locked affected gateway suite | 107 passed; existing Starlette deprecation warning |
| Scoped Ruff | Passed |
| Patch whitespace | Passed |

Two CPU environments lacked different preparation dependencies. Freeze used the
existing gateway image with no GPU or network, avoiding environment changes.
A missing separately deployed memory helper was supplied and hashed before any
GPU request. A Docker `top` PID-field requirement was corrected before services
were paused. None of these preparation failures consumed generation attempts.

## Maintenance and execution

Live control/API and persistent SQLite checks proved zero managed work and zero
unreleased voice grants. Gateway/Lab admission was paused; the original Comfy
container, image and production user directory are preserved. A post-pause
check confirmed idle state and captured hashes of three published voices and
two performance takes. Qwen-Image and the other resident services stay unchanged
across all arms. Experiment API uses a separate loopback-only port.

Arm A ran one static 128px-frame/0.1s-audio component workload in an isolated
container/user/output root. The Comfy history records successful execution.
Actual video and audio encoder/decoder inputs were BF16 on CUDA; FP16 accumulation
was off. Observed video dispatch included fused normalization and RMS/rotary
kernels. Finite decoded video and audio returned. These small-component timings
are not full-clip performance evidence or a speedup claim.

### Why the runner stopped, and the durable correction

The original harness incorrectly required every raw model parameter dtype to
equal compute precision. Dynamic VRAM loading preserves checkpoint-storage
weights and casts them on demand:

| Baseline model | Raw parameter dtypes observed | Actual compute activation |
| --- | --- | --- |
| Video | 486 FP16 / 73 BF16 | BF16 CUDA |
| Audio | 368 FP32 / 292 BF16 | BF16 CUDA |

Thus the parameter guard failed after a successful component workload; this
was a measurement-contract bug, **not a CUDA/OOM or model failure**. The corrected
contract distinguishes known immutable checkpoint storage from strict compute
dtype/device, still rejects unrecognized storage, and has regression coverage.
The retained observations pass offline reassessment. The original stopped
receipt is unchanged; no stop guard was bypassed and no cell replayed.

Restoration initially caught a second observer-level mismatch: Docker returned
the same mounts in a different order. Canonical comparison now sorts only by
destination, preserving every binding/mode field, with a tamper regression.

### Restoration proof

The isolated A container is stopped and retained. The original baseline
container is running, with identical image, Comfy commit, launch flags, mount
bindings, ports and restart policy. The production user root is unchanged.
Comfy queue, gateway lane and Voice Lab are idle/healthy; Qwen-Image health and
its service are healthy. All three published voices and both takes match their
pre-maintenance record/file hashes. Other containers were not stopped.

Private evidence root on Spark:
`/home/wjmao/services/spark-comfyui/experiments/h3-vae-qualification-2026-10-06/`.
Raw graphs, prompt/audio bodies and media stay outside Git. Local mirrored
component evidence:
`/Users/wjmao/plotloom-canaries/2026-10-06-h3-vae-qualification/`.
There is no twelve-video comparison page yet because no full clip was generated.

## Remaining gates

- Resume approval and a fresh cold-boundary A smoke: restarting its process
  requires one additional small workload beyond the original one-per-arm cap.
  The original smoke is retained, not replaced or erased. No extra full clips
  are proposed; the twelve-attempt ceiling remains entirely unused.
- Successful remaining component proofs and twelve attributable clips.
- Actual dtype/kernel, timing, memory and full decode observations.
- Repeat baseline restoration and unchanged voice/take proof after comparison.
- Owner visual/audio review, then a separate adoption decision if justified.

No production promotion, Plotloom edits, director message, merge or push.
