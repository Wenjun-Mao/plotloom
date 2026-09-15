# ADR 0038: H3 gateway durable FIFO dispatch

## Context

MiniMax-H3 has one usable generation lane on Spark. The original gateway
created a durable job record but synchronously posted that job to ComfyUI in
the request handler. Its apparent queue limit was a small admission shortcut
that mixed gateway jobs with ComfyUI's own backlog. A slow or unavailable
ComfyUI therefore held the caller open, and the gateway itself did not own a
durable order for multiple Plotloom requests.

## Decision

The gateway keeps six bearer-authenticated client operations plus a narrow
unauthenticated health route:

1. `POST /v1/assets` stores one validated reference asset from a multipart
   image or private `sourceUrl` retrieval.
2. `POST /v1/video-jobs` validates/prepares that asset, creates a durable job,
   and returns `202` with `queued` status without posting to ComfyUI. Admission
   is gateway-local, so a temporarily unavailable or busy ComfyUI leaves new
   valid work queued rather than rejecting it.
3. `POST /v1/video-jobs/from-image` is a stateless convenience admission that
   stores one supplied image and queues one ordinary job. Its input and retry
   boundary are recorded in ADR 0040.
4. `GET /v1/video-jobs/{id}` returns the known state.
5. `GET /v1/video-jobs/{id}/output` serves only the completed known MP4 owned
   by the gateway.
6. `POST /v1/video-jobs/{id}/cancel` cancels only a still-queued job.
7. `GET /health` returns safe H3 readiness, catalog and queue counts without
   a bearer key.

The gateway owns one FIFO dispatch worker. It submits at most one of its jobs
to ComfyUI at a time and waits while trusted external ComfyUI work is already
queued. Queue length is intentionally **not** capped: ten or more accepted
jobs may wait durably. The distinct completed-output ownership and retention
contract is recorded in [ADR 0039](0039-h3-gateway-managed-output-retention.md),
not hidden in a generation-concurrency limit.

`idempotencyKey` is an optional, request-bound job field. A repeated matching
request returns the original job; a changed request using the same key returns
`idempotency_conflict`. Plotloom supplies its durable local video-job ID when
using a gateway transport. Existing trusted direct callers remain compatible
but cannot receive retry deduplication unless they send a key.

`queued` and `submitting` are additive job states. A worker atomically claims
the oldest queued job as `submitting` immediately before the outbound POST.
On restart, historical `reserved` or `submitting` jobs become
`outcome_unknown`, never a replay candidate. A queued job alone may be
cancelled; no endpoint claims it can safely cancel a job that may be in
ComfyUI.

## Consequences

- A gateway request is short and independent of H3 render duration.
- Gateway SQLite is now the authority for queue order and restart recovery;
  one gateway process must own each gateway data directory.
- ComfyUI remains loopback-only and is still not a caller-facing queue API.
- Health exposes `queuedJobs`, `activeDispatches`, and fixed
  `dispatchConcurrency: 1`, but no prompt, path, asset, secret or ComfyUI
  graph.
- Output handoff/retention and any future parallel hardware are distinct
  decisions. They must not silently change this one-lane contract.

## Guardrails

Regression tests prove unlimited FIFO admission, one dispatch at a time,
external-ComfyUI waiting, queued cancellation, idempotency conflict, restart
recovery without replay, real worker lifecycle, strict secret-free health, and
Plotloom transport acceptance of the additive queued states.
