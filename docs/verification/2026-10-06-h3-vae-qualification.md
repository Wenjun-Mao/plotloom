# H3 VAE qualification — execution ledger

**Status: technical screen passed; owner visual/audio review pending.**
All twelve planned full clips passed compute/dispatch, geometry, audio-stream
and complete decode checks. The exact baseline services are restored and the
three published voices/two takes are unchanged. No production adoption or
creative acceptance is claimed. Both stopped precursor receipts are preserved.
The owner approved the [four-arm plan](../roadmap/2026-10-06-h3-vae-qualification.md)
on October 6. Exactly twelve full-generation attempts, no replay, and six small
component workloads including the two additional authorized cold smokes.
No production API, recipe, Comfy version or model-installation reset.
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
| Locked focused experiment tests | 24 passed |
| Locked affected gateway suite | 111 passed; existing Starlette deprecation warning |
| Scoped Ruff | Passed |
| Patch whitespace | Passed |
| Copied media/input/graph hashes and twelve-cell accounting | Passed |
| Restoration proof, redacted receipt and documentation links | Passed |

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

### Precursor restoration proof

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
No full clip had been generated at this precursor checkpoint.

## Authorized resumption

The owner authorized the extra A component smoke and testing/downtime on October
6. Exactly one fresh execution root was initialized at
`/home/wjmao/services/spark-comfyui/experiments/h3-vae-qualification-2026-10-06-resumed/`.
It records the stopped precursor receipt's path/SHA256 and zero full attempts.
`cases.json` is byte-copied, retaining the same `b597…0257b` canonical hash;
the original input root remains read-only mounted and all model hashes remain
unchanged. The extra A smoke passed; A/B/C subsequently completed nine full cells.
No second freeze, altered precursor, skipped stopped guard or replacement cell.
Managed admission is paused under a fresh persisted idle and voice/take proof.
The twelve full-attempt ceiling applies to the resumed comparison as a whole.

### INT8 storage correction and three-cell continuation

ABC completed all nine cells with valid observations/full decode. The first D
component also executed successfully but its raw parameter-storage check failed:
the pinned official INT8 header contains 527 F32, 35 F16, 144 I8 and 144 U8
tensors, including FP32 biases, normalization and weight scales. Observed video
parameters are 252 FP16 / 307 FP32, while encoder/decoder inputs are FP16 CUDA.
Actual `int8_linear`, `int8_attention` and `fp16_conv3d` dispatch returned
successfully; audio remains BF16 CUDA. This is another checkpoint-storage
assumption in the measurement contract, not a failed INT8 compute path.

The correction admits FP32 storage **only for D**, without weakening its FP16
CUDA activation guard or BF16 audio invariant. A regression explicitly rejects
FP32 compute with those same valid storage counts. A narrow independent Terra
follow-up found no residual issue; focused tests pass (24).

The stopped resumed receipt and first D evidence remain unchanged. Exactly one
continuation root at
`/home/wjmao/services/spark-comfyui/experiments/h3-vae-qualification-2026-10-06-int8-continuation/`
inherits all nine ABC claims and their successful smokes, records the stopped
parent's SHA256, and keeps the same cases/input/observer hashes. It leaves only
three D full claims, never a fresh twelve-call allowance. The owner's general
testing/downtime permission covers the additional cold D component (six small
components total across the three roots). Its fresh smoke and all three D full
cells passed. No full cell was replayed; total full attempts remain twelve.

## Measured results

A = current BF16; B = video FP16; C = FP16 + fast accumulation;
D = official INT8 + FP16 floating operations + fast accumulation.
Audio compute remained BF16 in all arms (unchanged FP32-storage checkpoint).

| Arm / case | Total seconds | Video encode seconds | Video decode seconds | Minimum host available GiB |
| --- | ---: | ---: | ---: | ---: |
| A / landscape | 162.150 | 0.44 | 44.54 | 30.50 |
| A / portrait | 150.149 | 0.35 | 40.30 | 27.74 |
| A / Ref2VA | 466.800 | 0.38 | 28.29 | 29.02 |
| B / landscape | 159.314 | 0.56 | 43.18 | 29.39 |
| B / portrait | 147.159 | 0.34 | 39.58 | 26.65 |
| B / Ref2VA | 455.040 | 0.38 | 23.50 | 29.03 |
| C / landscape | 180.158 | 0.43 | 61.88 | 30.24 |
| C / portrait | 177.250 | 0.34 | 63.39 | 27.50 |
| C / Ref2VA | 463.787 | 0.38 | 29.15 | 28.19 |
| D / landscape | 144.129 | 0.56 | 28.04 | 31.48 |
| D / portrait | 138.151 | 0.34 | 28.37 | 29.74 |
| D / Ref2VA | 452.817 | 0.38 | 14.83 | 31.25 |

Total means submit-to-observed completion, with three-second polling granularity;
it includes model/graph work and MP4 creation, not post-completion validation.
VAE columns are synchronized outer wall time, including model management.
Inner CUDA-event timings and scoped model-management timings remain separately
retained; they must not be added to the outer values. Successful video dispatch
in C includes FP16 Conv3D/linear; D includes FP16 Conv3D and INT8 linear/attention.
Symbols alone were not used as proof.

Each arm starts a fresh isolated process, runs its component smoke, then unloads
component models before the three full clips. Landscape is first; portrait and
Ref2VA follow. Shared disk/library caches remain intact. This is one observation
per cell, not randomized/repeated throughput qualification. Sampling precision
can change results even with identical seeds; MP4 differences are not a decoder-
only quantization error measurement.

The CPU-only observer samples host memory at approximately 1 Hz from before
submission through full-stream decode. All twelve traces passed. Minimum
available memory above is not exact GPU peak headroom; process RSS/HWM and host
available memory overlap on UMA and are never added. Existing swap usage peaked
at about 6.10 GiB; no CUDA/OOM failure occurred. This does not diagnose the parked
historical CUDA incident.

**Interpretation:** B provides little whole-render benefit in this screen.
C's FL2VA decode is materially slower despite real fast-kernel dispatch, so
the fast flag alone is not recommended. D reduces total time versus A by 11.1%
(landscape), 8.0% (portrait), and 3.0% (Ref2VA). Its decode is faster and sampled
host availability is higher; neither proves universal throughput or exact peak
VRAM savings. Prefer D for owner review, while retaining A pending acceptance.

## Final restoration and retained review

The final receipt is completed with exactly twelve passed claims. Both stopped
parent receipt hashes were checked unchanged. All experiment containers are
stopped and retained; the unchanged original Comfy container was restarted.
Image, commit, launch flags, mount bindings, ports, restart policy and production
user root match the pre-maintenance authority. Comfy, managed gateway, Voice
Lab and Qwen-Image are healthy with idle jobs/grants. Embedding/comment services
were not stopped. Three published voices and two takes match their before/after
record and file hashes. INT8 is installed but not selected in production.

The local twelve-video review package is
`/Users/wjmao/plotloom-canaries/2026-10-06-h3-vae-qualification-resumed/index.html`.
It includes frozen inputs, three fixed-frame samples per clip, and separated
timing/kernel/memory data. All copied clip/input hashes and graph hashes were
verified offline. Local mirrored raw evidence is under its `evidence/resumed/`
and `evidence/int8-continuation/` directories; the latter includes
`restoration.json`. Raw graphs, prompts, voice media and locators remain private.
The browser tool refused automatic file-URL navigation; no automated browser
playback or human-equivalent visual/audio acceptance is claimed. Open this local
HTML manually for review. Limited frame inspection is not motion acceptance.

Durable secret-free measurements and hashes:
[result receipt](supporting/2026-10-06-h3-vae-qualification-results.json).
Operator source baseline was `f1864cd`; this record accompanies the final local
tools/tests/docs commit. No shipped backend/frontend code changed; scoped checks
replace unrelated full frontend/E2E/wheel gates as approved. Usage/cost deltas
are unavailable from existing records.

## Remaining decision

Owner comparison of A versus D for intended words, identity/emotion, lip-sync,
extra speech/subtitles, drift/shaking and tile seams. If acceptable, authorize
a separate maintainable video-only precision/INT8 adoption—not promotion of
this experiment shim. Do not change baseline automatically or run a new sweep.

No production promotion, Plotloom edits, director message, merge or push.
