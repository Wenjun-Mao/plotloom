# ADR 0033: Private MiniMax-H3 gateway on Spark

## Context

The validated Spark H3 workflow runs in ComfyUI, whose graph API exposes
arbitrary node execution and has no authentication. Direct application access
would couple Plotloom to transient node IDs, model filenames, and output paths.
The first UI smoke also proved that forwarding a portrait keyframe directly to
a 16:9 canvas silently distorts the character.

## Decision

Run ComfyUI only on `127.0.0.1:8188`. A separate single-process FastAPI
gateway binds only to Spark's Tailnet address and requires a bearer key.

The initial public contract is deliberately narrow:

- upload a PNG, JPEG, or WebP reference frame;
- create a job using the frozen `minimax_h3_fp8_turbo4_480p` profile;
- choose an explicit `cover_center_crop`, `contain_pad`, or
  `reject_mismatch` input-aspect policy;
- poll a durable gateway job and retrieve its MP4 through the gateway.

The profile freezes the observed FP8 FL2VA, NVFP4 Qwen encoder, video/audio
VAEs, four-step Turbo LoRA, 864×480 output, 124-frame / 24fps timing and
native-audio path. The gateway does not accept arbitrary ComfyUI JSON, model
paths, dimensions, durations, steps, or custom nodes. It records an ambiguous
submit as `outcome_unknown` and never automatically replays it.

## Consequences

Plotloom integration remains a later adapter task: it must compile a frozen
production snapshot into this contract and preserve known-job recovery. It
must not reuse the Atlas-specific upload/HTTPS/prediction parser as a generic
H3 adapter.

H3's native-audio capability does not imply speech. Dialogue must be present
in the frozen video prompt; audiovisual quality remains a human review gate.

The current Tailnet-only HTTP deployment intentionally has no public HTTPS or
reverse proxy. Internet exposure would require a separate authentication and
TLS decision.
