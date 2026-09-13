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
