# Plotloom MiniMax-H3 gateway

This is the private, typed API in front of Spark's loopback-only ComfyUI
service. It is deliberately **not** a ComfyUI proxy: callers cannot submit
workflows, select model files, or reach ComfyUI directly.

Plotloom is now wired to this gateway through the versioned
`minimax_h3_gateway.v2` adapter. Use the complete
[H3 gateway operator and maintainer manual](../../docs/operations/minimax-h3-gateway-manual.md)
for deployment, security, Plotloom configuration, lifecycle, recovery, and
the exact limits of verified behavior.

The local service contract has six bearer-authenticated client operations plus
one unauthenticated health route:

1. `POST /v1/assets` stores one PNG, JPEG, or WebP reference frame from a
   multipart file or a private/public `http(s)` `sourceUrl` JSON body.
2. `POST /v1/video-jobs` prepares and durably queues one reviewed,
   allowlisted-profile job. It returns `202` and a job ID without waiting for
   H3; `idempotencyKey` is optional but required for caller retry deduplication.
3. `POST /v1/video-jobs/from-image` combines image ingestion and job admission
   for a multipart file or `sourceUrl`; it returns the ordinary queued-job
   response but deliberately has no idempotency-key contract.
4. `GET /v1/video-jobs/{id}` reports a known job.
5. `GET /v1/video-jobs/{id}/output` serves its gateway-managed completed MP4.
6. `POST /v1/video-jobs/{id}/cancel` cancels only a still-queued job.
7. `GET /health` exposes safe readiness and queue counts without a bearer key.

For a colleague-facing, copy-paste client guide—including Spark's current
Tailnet base URL and a test image—see
[`docs/operations/minimax-h3-gateway-client-guide.md`](../../docs/operations/minimax-h3-gateway-client-guide.md).

The gateway owns one FIFO dispatch worker. Its queue is intentionally not
length-capped: H3 receives one job at a time, while any further jobs remain
durably queued. This is a concurrency guarantee, not a retention policy; see
[ADR 0038](../../docs/adr/0038-h3-gateway-durable-fifo-dispatch.md).

After completion, the gateway atomically hands off its one expected MP4 from
the mounted ComfyUI output directory into gateway-managed storage, then
removes the ComfyUI source. It retains that managed copy for 72 hours; see
[ADR 0039](../../docs/adr/0039-h3-gateway-managed-output-retention.md).
The corresponding SQLite job record is removed 30 days after that handoff,
rather than 30 days after the MP4 expires.
No gateway-owned uploaded keyframe remains beyond 30 days, whether or not it
was used by a job. A completed job can release its keyframe earlier when its
last managed MP4 expires. This does not affect Plotloom's canonical project
assets.

New gateway-owned keyframes, prepared inputs, and completed clips use a
portable UTC timestamp prefix (`YYYY-MM-DDTHH-MM-SSZ_`) before their stable
`asset_…` or `h3_…` ID. The ID remains the API identifier; the timestamp is
there for on-host inspection. Deploy the naming contract with a clean gateway
state rather than preserving UUID-only files.

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

## Runtime layout

The gateway package keeps one responsibility per module:

- `api.py` owns FastAPI routing and authentication;
- `gateway.py` coordinates durable jobs without owning transport or files;
- `comfy.py` owns the narrow ComfyUI readiness/history/submission transport;
- `media.py` owns uploaded keyframes, prepared inputs, MP4 handoff and cleanup;
- `store.py` owns the SQLite control plane;
- `workflow.py`, `naming.py`, and `contracts.py` own the frozen workflow,
  timestamped naming, and public settings/contracts respectively.

`app.py` is intentionally only a compatibility export surface. Keep new logic
in the responsible module rather than growing that façade.

For new H3 work, Plotloom normally sends an aspect-matched keyframe with
`reject_mismatch`. An explicit author-owned `allowLetterbox` mode instead
freezes gateway `contain_pad`; this gateway receives the documented
`aspectPolicy` only and does not infer author intent.
