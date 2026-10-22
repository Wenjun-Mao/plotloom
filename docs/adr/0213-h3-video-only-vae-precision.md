# ADR 0213: H3 video-only VAE precision

Original specialist identifier: ADR 0098; renumbered during main integration on 2026-10-22.


Status: accepted by owner on 2026-10-06; deployment requires its separate receipt.

## Problem and evidence

Global `--fp16-vae` would also change the audio VAE. The twelve-cell pinned
ComfyUI 0.38.0 qualification instead retained global `--bf16-vae`, explicitly
selected video FP16, and verified video FP16/audio BF16 compute. The owner saw
no quality difference in the three A/D pairs. This is bounded evidence, not a
universal perceptual or memory guarantee.

The experiment's cached factory incorrectly supplied dtype as the third argument
of `load_vae_patcher`, which is **device**. Fresh clones could fail or fall back
to global BF16. Single-GPU qualification did not exercise that dormant path.
The fix belongs in the loader, not in sampler or caller workarounds.

## Decision

- Maintain a small repository-owned Comfy node loading only the reviewed INT8
  ConvRot video checkpoint at explicit FP16. Preserve the stock audio loader,
  its FP32 checkpoint, and global BF16 policy. Add `--fast fp16_accumulation`.
- Register our own disk reload factory, preserving device and dtype. The pinned
  VAE constructor lacks `disable_dynamic`; materialize the pristine model at its
  selected dtype before core's outer clone constructs the ordinary delegate.
  Do not replace Comfy globals or create a redundant temporary patcher. Test
  actual clone, deepclone, offload/reload and compute.
- Freeze checkpoint, hash, loader/policy version and audio/fast policy in new
  ordinary and Ref2VA execution snapshots. Reject earlier execution versions
  before submission; do not reinterpret them. Deployment requires drained queues.
  Historical terminal records and media remain readable, unchanged.
- All four qualities and Ref2VA share this video binding. Sampling, public API,
  resolutions, duration, voice identity, FIFO and retention do not change.
  Public health/creation versions stay 6 (ordinary) and 1 (voice); only private
  frozen renderer versions advance to 4 and 2 respectively.
- Preserve the prior container/image for rollback. No new tuning sweep, Plotloom
  integration, director messaging, merge or push is authorized by this decision.

## Alternatives and consequences

Global FP16 was rejected because it changes audio. Reusing the experimental
callback was rejected because its factory contract is wrong. Copying Comfy's
whole VAE class or monkeypatching its globals was rejected as maintenance debt.
The small node is pinned-runtime integration code: future runtime upgrades must
rerun the focused lifecycle tests. Frozen old contracts need not remain executable.
Adoption adds one component lifecycle proof and at most two managed full clips
(quality-1 portrait and Ref2VA); unknown submissions are never replayed.

See [qualification evidence](../verification/2026-10-06-h3-vae-qualification.md)
and [adoption plan](../roadmap/2026-10-06-h3-vae-adoption.md).
