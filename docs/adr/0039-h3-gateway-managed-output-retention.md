# ADR 0039: H3 gateway-managed output retention

## Context

ComfyUI's output directory is a renderer workspace, not a dependable handoff
location. Serving completed clips from its `/view` route tied Plotloom's known
gateway jobs to ComfyUI's local retention and made ownership ambiguous.

## Decision

The gateway owns completed H3 MP4s under its persistent data directory. It
receives a single validated ComfyUI output descriptor, copies that exact file
into gateway storage atomically, hashes it, and removes the source from the
mounted ComfyUI output directory. Only after source removal succeeds does the
job become `succeeded` and downloadable through the gateway.

If a process stops during the handoff, the durable job remains
`transfer_pending`. A later gateway pass resumes only the frozen descriptor
and gateway-owned destination; it does not submit new H3 work. A missing or
unsafe source/destination fails closed.

Each managed output is retained for exactly 72 hours from successful gateway
handoff. The worker deletes only a named, database-owned managed file whose
deadline has passed, then changes its job to `output_expired`. Job metadata,
digest, expiry evidence, and error code remain; the gateway never performs a
broad directory cleanup or deletes arbitrary ComfyUI files.

At the first upgrade to this contract, the worker adopts each pre-retention
`succeeded` job whose frozen ComfyUI output descriptor still identifies a
regular source file. It uses the same copy/verify/remove handoff and never
submits H3 again. If an older source was already removed before the upgrade,
the record becomes explicitly unavailable with
`gateway_legacy_output_unavailable`; it is not misrepresented as a file this
gateway retained and later cleaned up.

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
unrelated files, additive database migration and legacy-output adoption, and
client handling of the expired-output state.
