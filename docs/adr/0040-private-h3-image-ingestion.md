# ADR 0040: Private H3 image ingestion and stateless one-step admission

> **Historical creation boundary (2026-09-23):** This is the H3-ingestion
> `0040`, not the [project-folder storage `0040`](0040-project-folder-storage-boundary.md).
> [ADR 0050](0050-unified-h3-generation-contract.md) removed the standalone
> `/v1/assets` step and public asset ID. The current `from-image` route still
> accepts a private `sourceUrl` form; do not infer that URL ingestion vanished.

## Context

The gateway previously accepted only multipart uploads followed by a separate
job request. That is dependable for Plotloom, but inconvenient for trusted
colleagues who commonly have a downloadable image URL and want one short H3
request. URL hosts also frequently omit or mislabel `Content-Type`, making a
header-based image contract unreliable.

Creating an endpoint-specific submission/deduplication mapping would make the
convenience route stateful in a second, unnecessary way and would introduce a
separate retention/cleanup policy.

## Decision

The private, bearer-authenticated gateway has six client operations. Existing
`POST /v1/assets` accepts either its multipart image or JSON
`{"sourceUrl": "http(s)://…"}`. New
`POST /v1/video-jobs/from-image` accepts a multipart image plus job choices,
or the equivalent JSON `sourceUrl` form. It persists an ordinary gateway asset
and ordinary queued job, then returns the existing closed job envelope. It
does not return a second asset response shape and rejects `idempotencyKey`.
Callers that need a reusable asset ID or retry-deduplication use the existing
two-step contract.

Both paths inspect decoded bytes, not the caller/host `Content-Type`, and
store only detected JPEG, PNG, or WebP metadata. URL fetching uses a dedicated
client, never ComfyUI transport, with three redirects, 5-second connect,
20-second read, and existing byte/pixel limits. A URL exists only during that
fetch: no URL, query string, or source-response body is stored in SQLite or
logs beyond the resulting normal gateway asset.

This is a private Tailnet MVP. `http` and `https`, including internal
addresses, are allowed. It intentionally does not implement host allowlists,
DNS/IP filtering, or public-service SSRF policy. Those controls are required
before the gateway is exposed beyond trusted internal callers.

Known profile and image-aspect preconditions are validated before a job is
reserved. A one-step request that fails after it created an otherwise
unreferenced asset removes that temporary asset immediately; the existing
asset-retention worker remains the crash-safe fallback.

## Consequences and guardrails

- The convenience route performs no H3/ComfyUI call; it only creates durable
  local work for the serial dispatcher.
- A client timeout after one-step submission is `outcome_unknown` to that
  client. It must not automatically retry, because a new request can create a
  second normal job. The two-step route retains its existing idempotency key.
- The response remains secret-free and URL-free. Job, output, keyframe, and
  SQLite retention remain governed by ADR 0039.
- Tests cover both content types, actual-byte detection, bounded URL fetches,
  URL non-persistence, ordinary response shape, aspect preflight, and rollback
  of an unreferenced one-step asset.
