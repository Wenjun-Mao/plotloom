# ADR 0095: H3 runtime qualification and catalog isolation

**Status:** Accepted for specialist qualification; production promotion pending.

## Context

ComfyUI 0.35.0's H3 VAE stores raw tile tails before blending. Upstream
[PR 16436](https://github.com/Comfy-Org/ComfyUI/pull/16436), released in
[0.38.0](https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.38.0), uses
composited neighbours. Ordinary `VAEDecode` still invokes H3's internally
tiled decoder: prompts, image padding and gateway changes cannot fix this
decoder composition defect.

The runtime upgrade also applies a catalog migration that discards manual
asset metadata, previews, API-managed records and deletion markers. A model
inference pass does not establish safe production metadata migration.

## Decision

- Qualify the exact upstream commit in a separate image derived from the
  preserved live image. The supported build wrapper verifies its exact image
  ID and passes that immutable ID to the build; freeze non-Comfy packages,
  retaining Torch/CUDA/SageAttention and the existing GB10 source mod.
- Use a copied, isolated Comfy user directory. Keep the original container,
  image and user directory available for rollback. Assert user/model mounts
  before running; retain genuine inventory and do not overwrite evidence
  when adding later guards.
- Keep models, recipes, gateway contract and Voice Lab data unchanged. Bound
  generation calls and persist uncertainty before each sole POST; never
  replay an existing receipt.
- Separate decoder-mechanism regression, technical media checks, whole-video
  creative review and production adoption. Synthetic two-way overlap-add
  establishes the tested composition mechanism, not all geometry/quality.
- Review actual prepared input pixels against the prompt **before submission**,
  not just filenames, dimensions and hashes. An input–prompt mismatch is a
  test-design failure; retain and label that pair, never silently replace it.

## Consequences and rejected alternatives

Unpinned runner `update --keep` changes runner and Comfy master together;
it is not the controlled upgrade path. A prompt workaround or automatic
padding/cropping change fixes the wrong layer. W6A8 is deferred to a separate
model comparison. Candidate startup must not migrate the production catalog
just because inference tests pass.

The five-call trial passed its bounded technical checks, but its landscape
input was contaminated and human review is pending. Baseline was restored.
Production promotion requires an explicit catalog disposition and adequate
visual/audio evidence; no automatic reset or deletion is authorized.

See the [qualification receipt](../verification/2026-09-30-h3-comfy038-runtime-qualification.md).
