# ADR 0039: H3 gateway-managed output retention

## Context

ComfyUI's output directory is a renderer workspace, not a dependable handoff
location. Serving completed clips from its `/view` route tied Plotloom's known
gateway jobs to ComfyUI's local retention and made ownership ambiguous.

Anonymous UUID-only filenames also made the gateway's private asset, prepared
input, and output directories needlessly hard for an operator to inspect.

## Decision

The gateway owns completed H3 MP4s under its persistent data directory. It
receives a single validated ComfyUI output descriptor, copies that exact file
into gateway storage atomically, hashes it, and removes the source from the
mounted ComfyUI output directory. Only after source removal succeeds does the
job become `succeeded` and downloadable through the gateway.

Every newly stored gateway file begins with its UTC allocation timestamp in
the portable form `YYYY-MM-DDTHH-MM-SSZ_`, followed by its immutable API ID:
`…_asset_<uuid>.png` for uploads, `…_h3_<uuid>.png` for prepared ComfyUI
inputs, and `…_h3_<uuid>.mp4` for managed outputs. The ID remains the
collision-safe owner and public API reference; the timestamp is operational
metadata only. A managed-output name is persisted when the job first enters
`transfer_pending`, before a copy begins, so restart recovery always resumes
the same destination. This is a clean state cutover: operators reset prior
gateway SQLite and managed files before deploying it rather than retaining a
second filename contract.

If a process stops during the handoff, the durable job remains
`transfer_pending`. A later gateway pass resumes only the frozen descriptor
and gateway-owned destination; it does not submit new H3 work. A missing or
unsafe source/destination fails closed.

Each managed output is retained for exactly 72 hours from successful gateway
handoff. The worker deletes only a named, database-owned managed file whose
deadline has passed, then changes its job to `output_expired`. Job metadata,
digest, expiry evidence, and error code remain; the gateway never performs a
broad directory cleanup or deletes arbitrary ComfyUI files.

An `output_expired` row remains as a short audit record for 30 further days.
It then becomes eligible for conditional deletion from the gateway's `jobs`
table, removing its stored prompt and control-plane history. At that point the
MP4 is already absent. At MP4 expiry—not at this later row cleanup—the gateway
also removes that job's per-job prepared ComfyUI input and may release its
keyframe earlier. Independently, no uploaded gateway keyframe survives beyond
30 days after allocation, whether or not a job used it or a managed MP4 remains
retained. These are gateway-owned transfer copies only; this policy never
deletes Plotloom's canonical project stills or character references. SQLite
marks the due keyframe metadata `purge_pending` before filesystem deletion, so
it cannot enter another job. If a job still has a foreign-key reference, that
small metadata row remains inaccessible until the final job audit record is
removed.

## Consequences

- Plotloom retrieves MP4 bytes only from gateway-managed storage, never a
  ComfyUI endpoint or provider URL.
- The gateway deployment needs a writable mount of ComfyUI's output directory
  as well as its existing input mount.
- After 72 hours, a delayed retrieval is reported as
  `h3_gateway_output_expired`; it is not silently treated as a new generation
  or a valid candidate.
- Output retention is distinct from Plotloom's longer-term selected-candidate
  artifact policy and from input-asset retention.

## Guardrails

Regression coverage proves copy-then-remove handoff, restart-safe pending
transfer, secret-free status, targeted 72-hour expiry, preservation of
unrelated files, client handling of the expired-output state, 30-day job-record purge, and
age-based keyframe cleanup, including a keyframe linked to an existing job. It
also proves that new asset, prepared-input, and managed-output names carry the
readable UTC prefix.
