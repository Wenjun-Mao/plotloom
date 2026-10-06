# H3 D adoption · 2026-10-06

**Status: D adopted and serving; both managed canaries and idle restart passed.**
Owner approved video-only precision, durable reload/clone behavior, focused
verification and deployment. Specialist source baseline: `e422b4e`.
[ADR 0098](../adr/0098-h3-video-only-vae-precision.md) and the
[bounded plan](../roadmap/2026-10-06-h3-vae-adoption.md) are the authority.
Plotloom integration/director contact, merge and push remain held.

## Exact change

| Layer | Before | D |
| --- | --- | --- |
| Comfy/Torch/CUDA/Sage | Pinned 0.38.0 image | Same exact image and packages |
| Global VAE policy | `--bf16-vae` | Unchanged |
| Video checkpoint | FP16-storage video VAE | Official INT8 ConvRot video VAE |
| Video compute | BF16 | Explicit FP16 through maintained loader/factory |
| Audio | FP32 checkpoint, stock loader, BF16 compute | Unchanged |
| Fast policy | No FP16 accumulation flag | `--fast fp16_accumulation` |
| Sampling and public contracts | Reviewed qualities 1/2/3/8, Ref2VA; API 6/1 | Unchanged |
| Frozen private renderer | Ordinary 3 / voice 1 | Ordinary 4 / voice 2, includes exact VAE policy |

Current image/container/node/checkpoint/template identities and the immediate
rollback pair are in [the D manifest](../../services/minimax_h3_gateway/h3-vae-d-adoption.v1.yaml).
The old FP16 VAE, earlier containers/images, original user directories, model
assets and experiment evidence were retained. Gateway overlay replaced source
only; dependencies were not reinstalled. Production mounts node/models read-only.
Original gateway/Lab SQLite and artifact directories are unchanged.

## Root causes and corrections

1. **Experimental reload callback:** Comfy's third `load_vae_patcher` argument is
   device, not dtype. The historical callback could fail or lose FP16 on clone.
   The maintained node uses its own typed factory, materializes freshly loaded
   dynamic parameters before core's non-dynamic delegate, and leaves globals
   and the stock audio loader alone. The experiment code/evidence are preserved
   and labelled historical-only, not silently repaired into production proof.
2. **Initial GPU harness:** importing only `model_management` left the patcher
   static, unlike live Comfy's bootstrap. Initial FP16 compute passed but the
   distinct-clone assertion failed. The corrected harness imports pinned `main`
   without starting its server, asserts DynamicVRAM, then tests real delegates.
   Both failed `lifecycle.json` and passed `lifecycle-dynamic.json` are retained.
3. **Source-overlay build:** two attempts failed before container renaming.
   BuildKit interpreted a raw local `sha256:<id>` in `FROM` as a registry image
   named `sha256`, not the existing local image ID. The durable operator fix
   creates a unique local tag, verifies its exact ID, disables pulls and builds
   before replacing anything. Conflict/identity regressions and independent
   review pass. No Comfy image or installed dependency changed.
4. **Canary observer:** it incorrectly waited for `completed`; the real gateway
   terminal state is `succeeded`. First generation succeeded normally. Its
   original source/receipt were retained, then a tested GET-only reconciliation
   verified the same job ID and consumed only the still-unused second claim.
5. **One voice status GET disconnected:** the observer stopped with
   `ConnectionError` after both POSTs were acknowledged. Exact connection-close
   cause is not established. Fresh health/status checks found both original
   serving IDs healthy, zero restarts/OOM kills and the voice job continuing.
   No runtime fix or generation replay is claimed. A stopped observer can be
   reconciled only with both IDs acknowledged and the second server-proven
   succeeded; it has no POST remaining. The prior stopped receipt is retained.

## Pinned GPU lifecycle proof

Same Comfy image, no server/network/diffusion; 128px video and 0.1s stereo audio.
Actual encoder/decoder inputs were checked on CUDA, with finite decoded output:

| Check | Compute |
| --- | --- |
| Initial video load | FP16 |
| Non-dynamic clone, distinct model | FP16 |
| Same-device deepclone, distinct model | FP16 |
| Offload/reload | FP16 |
| Pristine disk factory | FP16 |
| Stock audio after the entire video lifecycle | BF16 |

Factory bindings survived clone/deepclone. FP16 accumulation was enabled.
Live canary logs separately record the video checkpoint immediately followed
by `dtype: torch.float16`, and audio checkpoint by `dtype: torch.bfloat16`.
This is storage-vs-compute evidence, not a claim that all raw parameters are FP16
or that other GPUs/Comfy revisions are compatible.

## Managed canaries and final serving proof

Exactly two acknowledged managed POSTs; same retained frozen cases hash
`b5971616b3a8edd89e4360000e617c10938ef9675fd5e0923c8e888f3430257b`.
No voice synthesis, uncertain replay, new comparison sweep or approval occurred.

| Case | Job | Verification |
| --- | --- | --- |
| Ordinary quality 1, 704×1280 | `h3_57767740e75a48768f96c6b852189534` | Passed; 124 frames, H.264/AAC, 32kHz audio, full decode and frozen D policy |
| Ref2VA, 576×1024 | `h3_14de80bdf1ed4c07b4fb055348b07153` | Passed; 124 frames, H.264/AAC, 32kHz audio, full decode and frozen D policy |

Backend elapsed time was 146,984ms (ordinary) and 445,649ms (voice). These are
deployment smoke observations, not a new matched speed comparison. Media hashes,
exact snapshots' hashes/VAE policy, CUDA dtype evidence, source hashes and
private-receipt hashes are in the
[secret-free supporting proof](supporting/h3-vae-d-adoption-20261006.json).

After proving all managed/Comfy jobs and Voice Lab grants idle, the same D
containers and Voice Lab were stopped and restarted once. Gateway versions 6/1,
four qualities, six ordinary resolutions and Ref2VA readiness returned unchanged;
both known jobs remained succeeded/output-ready. Qwen-Image/Lab health passed.
All three published voice records, two takes and their WAV bytes match the
before-maintenance hashes. Immediate rollback containers remain stopped; no
unexpected restart or container OOM kill occurred. Spark itself was not rebooted.

Private operator receipts and proof media:
`/home/wjmao/services/spark-comfyui/experiments/h3-vae-d-adoption-20261006/`.
Raw prompts, input/audio bodies, endpoint and key are not in this tracked receipt.
The existing retained performance-reference clipping warning is unchanged.

## Verification and boundaries

- Final unfiltered `uv run --locked pytest -q`: **857 passed**, 152.13 seconds.
  Existing Starlette deprecation warning only; no deselection or skips.
- Final observer/extraction checks: 19 passed, then 8 observer regressions after
  the stopped-read-only recovery guard. Focused gateway suite: 133 passed.
- Scoped Ruff and patch whitespace passed.
- Wheel build and isolated installed-wheel smoke passed. Gateway/custom node
  are independently deployed service source, not wheel contents.
- One monitored GPT-5.6 Terra reviewer checked loader/renderer/deployment and
  concrete follow-ups including stopped read-only reconciliation; no remaining
  material finding at those checkpoints.
- No frontend, browser, general memory or new human-quality acceptance claim.

The earlier owner A/D review and single-case timing measurements remain bounded
evidence, not an all-quality speed, memory-reliability or voice guarantee.
The historical CUDA cause stays parked. Reboot behavior relies on preserved
restart policies; this assignment does not reboot Spark. No cleanup/reset,
director message, merge or push occurred.
