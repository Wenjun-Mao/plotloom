# H3 ComfyUI 0.38 runtime qualification

**Result:** Bounded technical checks passed; **full qualification and production
promotion are not complete**. Five of five authorized generation calls used.
Original runtime restored; gateway, Voice Lab and Qwen Image healthy. No model,
recipe, gateway/API or Voice Lab production source change. No merge/push or
director contact.

Authority: [approved plan](../roadmap/2026-09-30-h3-comfy038-runtime-qualification.md).
Decision: [ADR 0095](../adr/0095-h3-runtime-qualification-and-catalog-isolation.md).
Starting source revision: `d953506` on `codex/h3-ref2va-gateway`.

## Root cause and runtime boundary

The installed baseline H3 VAE stores raw overlap tails before applying the
blend, whereas upstream [PR 16436](https://github.com/Comfy-Org/ComfyUI/pull/16436)
stores composited neighbours. The decoder internally tiles even with ordinary
`VAEDecode`; this belongs in Comfy's decoder, not prompts or gateway image policy.

| Identity | Baseline | Candidate |
| --- | --- | --- |
| ComfyUI | 0.35.0 | 0.38.0 |
| Commit | `d43a5fa20c8547ff42d13232f589a06536c42b97` | `6b747c0428c343e1417219641db93a4fb7cb69ae` |
| Docker image | `sha256:d45ca7983d4eda39cdd4df3bd03921b28754b2c15ce17f906032ef4dafd1cabc` | `sha256:db0010004575a508b5ac67fb36ea4ab83cf1964a84e70932019749f330c64110` |

Torch `2.14.0+cu130`, torchvision `0.29.0+cu130`, torchaudio `2.11.0+cu130`
and SageAttention `2.2.0` stayed exact. All non-Comfy installed package
versions stayed unchanged. BF16/VAE BF16, SageAttention, normal dynamic memory,
loopback port, cache/input/output/model mounts and GB10 `unified-memory-free`
source mod stayed unchanged. W6A8 was not installed or tested.

Only Comfy packages changed: aimdo 0.5.3→0.5.5, kitchen 0.2.33→0.2.36,
embedded docs 0.5.11→0.5.12, workflow-template core 0.3.339→0.3.361,
JSON 0.1.74→0.1.96, media-assets-01 0.1.44→0.1.48,
media-assets-02 added 0.1.6, frontend 1.52.7→1.53.6 and workflow templates
0.11.59→0.11.70. Full package inventories are retained privately on Spark.

Baseline already reported `nvidia-cusparselt-cu13 0.8.1 is not supported on
this platform` in `pip check`; no successful `pip check` or repair is claimed.
The initial candidate build needed corrected source ownership before startup
because Git rejected root-owned sources for the non-root user. That failed
startup made no generation call; the tested rebuilt image has correct ownership.

## Decoder-mechanism regression

The actual installed `MiniMaxH3VideoVAE.tiled_decode` ran **on CPU without GPU
access** in both images, with synthetic tile pixels and an independently
normalized separable overlap-add oracle. A 512×512, 3×3 tile grid with two-way
overlaps isolates the raw/composited-neighbour defect from weights/sampling.

| Measurement | Baseline | Candidate |
| --- | ---: | ---: |
| Maximum absolute composition error | 0.2834602 | 3.576279e-7 |
| Mean absolute composition error | 0.02657471 | 1.446870e-8 |

Both expected assertions passed: affected baseline, fixed candidate. This is
not proof for arbitrary triple-overlap configurations or all real videos.
The first harness launch needed `PYTHONPATH=/opt/ComfyUI`; it stopped at import,
not inference. [Machine-readable result](supporting/h3-runtime-038-2026-09-30/composition.json).

## Five-call generation evidence

Each matched I2V pair used quality 1 (V1.2 Turbo4, Euler, 6/3), seed `20260930`,
124 frames, identical frozen input/prompt/graph hashes; only output prefix
changed. First landscape then portrait on each freshly started runtime. The
sampler `105:14` was never cached. Ref2VA reused the reviewed 576×1024 case,
20 steps, native 12/3, seed `20260923`, exact first-frame/voice/model hashes.

| Case | Baseline elapsed | Candidate elapsed | Technical result |
| --- | ---: | ---: | --- |
| 1280×704 I2V | 195.179 s | 165.161 s | Passed |
| 704×1280 I2V | 196.697 s | 156.129 s | Passed |
| 576×1024 Ref2VA | Historical clip only, not matched timing | 474.433 s | Passed |

All five MP4s contain 124 H.264 frames at 24 fps, 32-kHz AAC and a 5.167-second
container duration. Both streams fully decoded without ffmpeg errors.
No rejected, failed, unknown or replayed submission occurred. Single pairs
were approximately 15% and 21% faster; these are observations, not a benchmark.
The voice case proves technical regression only, not dialogue/identity/lip-sync.

Exact IDs, graph/output hashes, cache lists, metadata and memory are in the
genuine [baseline receipt](supporting/h3-runtime-038-2026-09-30/baseline-receipt.json)
and [candidate receipt](supporting/h3-runtime-038-2026-09-30/candidate-receipt.json).
Raw graphs, prompt bodies and full histories remain private on Spark.

### Test-design defect caught in visual review

The presumed landscape still was actually a narrow doorway scene padded with
black bars, not the astronaut scene described by the frozen prompt. The runner
center-fit that whole image once from 832×480 to 1280×704; this did not remove
the embedded padding or establish semantic suitability. Both runtimes blend
the doorway image into the astronaut scene during the opening. This is visible
in retained baseline/candidate contact sheets, not an upgrade-specific defect.

Root cause: selecting the historical filename without reviewing its pixels
before freeze/submission. The landscape pair remains valid for equal-input
technical/timing comparison, but **not clean visual seam qualification**.
Do not silently change the input, weaken acceptance or spend a sixth call.
The next separately bounded visual qualification must first inspect prepared
image and prompt together, as recorded in ADR 0095.

Three sampled candidate portrait and Ref2VA frames show no obvious rectangular
brightness/color lattice; that limited inspection does not establish a full
video pass. Human whole-video visual/audio review is pending for those clips.

### Memory boundary

One-Hz observations are host `MemAvailable` and process RSS/HWM, **not Torch
allocation or exact GPU peak**. Process HWM is cumulative over that runtime's
lifetime and is not a fresh per-case maximum.

| Case | Baseline minimum host available | Candidate minimum host available |
| --- | ---: | ---: |
| Landscape | 27.76 GiB | 28.59 GiB |
| Portrait | 24.93 GiB | 25.57 GiB |
| Ref2VA | Not measured here | 27.18 GiB |

No OOM occurred in these cases. They do not qualify longer clips, concurrent
voice children, or all shared-memory states. Qwen Image and other previously
running services remained up; gateway and Voice Lab admission were paused idle.
The Comfy offload fix is not a demonstrated repair for the separate Voice Lab
CUDA primary-context failure.

## Catalog migration, restoration and preservation

Candidate startup migrated only a 19-MB copied user directory under
`experiments/h3-runtime-038-2026-09-30/candidate-user`, advancing its catalog
from migration 0006 to 0008. Comfy warned that manual tags/metadata, previews,
renames, API records, job links and deletion markers would be discarded/rebuilt.
Its generated `comfyui.db.bkp` and isolated copy remain retained. No production
catalog copy was migrated/reset. This prevents automatic promotion.

The original `spark-comfyui` container/image and `data/user` were preserved.
After known completion and an empty Comfy queue, candidate stopped; original
container name restored and started at exact baseline image/commit. Candidate
container `spark-comfyui-v038-qualified-20260930` is **stopped**; its historical
name does not imply full qualification or adoption.

Restoration checks: Comfy empty; gateway `ok`, zero queued/active, voice route
ready; Voice Lab `ok`, idle, all four engines available; Qwen Image `ok` and
`/v1/models` identifies Qwen-Image-2.1. Voice SQLite integrity is `ok`; creation
rows remain 5 completed/1 failed and reuse rows 9 completed/1 failed, matching
pre-pause counts. Both published Voice IDs' stored source and H3 hashes match
their files. No voice selection/regeneration, gateway data or model was changed.

The [separate mount proof](supporting/h3-runtime-038-2026-09-30/candidate-mount-proof.json)
was captured retrospectively while the candidate was running. Original runtime
inventories were not overwritten to imply that subsequently added guards ran
before the already completed submissions. The tool now enforces those mounts.

## Operator material, review and verification

Spark evidence root:
`/home/wjmao/services/spark-comfyui/experiments/h3-runtime-038-2026-09-30/`.
Output root: `data/output/experiments/h3-runtime-038-2026-09-30/`.
Local private review page: `/Users/wjmao/plotloom-canaries/2026-09-30-h3-runtime-038/index.html`.
Its package includes all five clips, prepared stills/contact sheets and one
clearly labelled historical voice clip. None is tracked or put in Downloads.

The independent read-only review found two guard gaps: mutable base-image
selection and unasserted user-dir isolation. The supported build wrapper now
checks the baseline ID and builds from that immutable ID; the experiment
asserts exact user/model mounts and preserves a separate later proof. Offline
tests cover both refusals and the exact accepted build argument. No GPU-stack
or tested decoder changes were made to implement these operator guards.

Executed focused checks: `uv run --locked pytest -q` on
`test_runtime_qualification.py`, `test_prompt_robustness_study.py` and
`test_voice_reference.py`: **40 passed**, one existing Starlette deprecation
warning. Scoped Ruff and shell syntax checks passed. Relative documentation
links, all five local media hashes, equal paired graph hashes, uncached sampler,
review-page media links, JSON parsing and final staged patch checks passed.
Full frontend/E2E/wheel gates were not rerun:
this changes operator tools/docs, not shipped gateway/frontend/package code.

**Next:** review the valid portrait/voice clips; separately authorize a corrected
landscape visual pair if required. Decide catalog preservation/reset explicitly
before any runtime promotion. No new dispatch or automatic adoption is authorized
by this receipt.
