# Plotloom MiniMax-H3 gateway

This is the private, typed API in front of Spark's loopback-only ComfyUI
service. It is deliberately **not** a ComfyUI proxy: callers cannot submit
workflows, select model files, or reach ComfyUI directly.

Plotloom is now wired to this gateway through the versioned
`minimax_h3_gateway.v2` adapter. Use the complete
[H3 gateway operator and maintainer manual](../../docs/operations/minimax-h3-gateway-manual.md)
for deployment, security, Plotloom configuration, lifecycle, recovery, and
the exact limits of verified behavior.

The local service contract is intentionally small:

1. `POST /v1/assets` uploads one PNG, JPEG, or WebP reference frame.
2. `POST /v1/video-jobs` creates an asynchronous job using one reviewed,
   allowlisted profile and mandatory `cover_center_crop`, `contain_pad`, or
   `reject_mismatch` policy.
3. `GET /v1/video-jobs/{id}` reports a known job; `GET .../output` proxies its
   completed MP4.

Keep ComfyUI on `127.0.0.1:8188`, bind this gateway only to Spark's Tailscale
address, and keep its bearer key server-side. Do not replace the documented
profile catalog with an SSH-only edit: profile changes require a new versioned
gateway/Plotloom contract and verification.

## Module boundary and future extraction

This directory is the git-tracked source module for the gateway: its container
definition, environment template, typed HTTP service, and profile catalog stay
together under `services/minimax_h3_gateway/`. Plotloom's adapter deliberately
lives elsewhere under `src/plotloom/video_backends/minimax_h3/`; it consumes
the versioned HTTP contract and must not import gateway runtime code.

That boundary keeps the current same-repository deployment reproducible while
allowing a later extraction into its own repository without changing the
Plotloom production contract. Until such an extraction is explicitly approved,
gateway source changes, profile changes, and their operator documentation are
reviewed and versioned here with Plotloom.

For new H3 work, Plotloom normally sends an aspect-matched keyframe with
`reject_mismatch`. An explicit author-owned `allowLetterbox` mode instead
freezes gateway `contain_pad`; this gateway receives the documented
`aspectPolicy` only and does not infer author intent.
