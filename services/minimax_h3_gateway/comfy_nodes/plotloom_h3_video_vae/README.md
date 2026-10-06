# Maintained H3 video-only VAE loader

`PlotloomH3VideoVAELoader` is the one repository-owned Comfy node in the
production H3 runtime. [ADR 0098](../../../../docs/adr/0098-h3-video-only-vae-precision.md)
defines the split: reviewed INT8 ConvRot **video at FP16**, stock FP32 audio
checkpoint **at BF16**, global `--bf16-vae`, and `--fast fp16_accumulation`.
It accepts only the checkpoint/hash and policy constants in `loader.py`.
No external dependencies, requirements file, global monkeypatch or sampler
changes are introduced.

Mount this directory at `/opt/ComfyUI/custom_nodes/plotloom_h3_video_vae`, read-only,
from a stable release. Models are read-only too. The frozen gateway snapshot
records policy, node version, checkpoint/hash, audio dtype and fast policy.
Absent flags/node/assets fail readiness; wrong checkpoint bytes fail loading.

The custom disk factory preserves device and explicit dtype. For the pinned
dynamic runtime, a non-dynamic clone materializes freshly loaded pristine VAE
parameters before core constructs its delegate. The original patcher owns the
factory; do not assign a recursive factory to every fresh delegate or pass
dtype in Comfy's device argument. Quantized/offloaded parameter storage is not
the same as FP16 encoder/decoder computation.

Verification:

- Offline tests: `uv run --locked pytest -q tests/services/minimax_h3_gateway/test_vae_policy.py`
  from the Plotloom repository root.
- Actual pinned GPU lifecycle: [operator harness](../../tools/vae_adoption/README.md)
  exercises initial load, non-dynamic clone, same-device deepclone, offload/reload,
  disk reload, then stock audio. It proves CUDA activation dtype and finite
  output, not multi-GPU compatibility or general memory reliability.

Requalify for a new Comfy/Torch runtime. Keep the historical experiment loader
isolated; it is evidence, not the production implementation.
