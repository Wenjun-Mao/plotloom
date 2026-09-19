# ADR 0068: H3 reproducibility inventory and qualified sampling recipes

**Status:** Accepted

## Context

The Spark MiniMax-H3 path combines a host/container runtime, large model
assets, a ComfyUI graph, and a gateway profile catalog. Existing gateway
operations documentation explains deployment and API behavior, but did not
bind exact runtime/asset facts to a complete sampling recipe.

That gap allowed the installed LightX2V four-step LoRA to inherit ComfyUI's
base H3 `12 / 3` shifts instead of declaring its published `6 / 3` contract.
The graph still rendered, so an apparently healthy output could conceal the
mismatch.

## Decision

Maintain a secret-free, versioned H3 installation manifest beside the gateway
source and two linked manuals:

- a clean-room reproducible setup guide;
- a rationale and operations manual;
- a machine-readable current-installation inventory.

The manifest records exact asset hashes, runner/ComfyUI/runtime pins, launch
policy, rendered workflow hash, observed profile behavior, and qualification
status. It never records endpoint addresses, bearer secrets, customer prompts,
input media, or generated media.

Sampling settings are profile-owned atomic fields: H3 family, LoRA identity
and strength, steps, video/audio shifts, sampler, scheduler, and denoise.
Runtime controls such as Torch/CUDA, attention backend, memory policy, and
`fp8_matrix_mult` remain worker-level settings.

A profile moves from observed to candidate, qualified, production, or retired
only through evidence that names both its recipe and runtime manifest.

## Consequences

- Future reproduction has an inspectable starting point without exposing
  secrets or user content.
- A renderer test can prevent implicit defaults from substituting for a
  declared sampling contract.
- Runtime A/B tests do not multiply the creative profile catalog.
- The presently observed four-step installation remains explicitly
  unqualified until the `6 / 3` sigma-shift repair and re-baseline complete.
