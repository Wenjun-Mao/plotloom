# ADR 0050: Unified H3 direct-generation contract

**Status:** Accepted

## Context

The first H3 gateway exposed a public asset upload route followed by a job
creation route. A newer one-step I2V route sat beside those routes. That left
three public ways to express the same intent, a public transient asset ID, and
an idempotency state which internal colleagues did not need. The H3 node also
supports no frame, a first frame, or both first and last frames, but the
gateway's durable record and renderer modelled only one image.

This is a contract mismatch, not an API ergonomics issue: extending the
one-frame job record would make cleanup, provenance, timing, and later T2V
behavior inconsistent by construction.

## Decision

Adopt gateway profile contract V4 with two direct creation routes:

- `POST /v1/video-jobs/from-image` accepts either JSON `sourceUrl` plus an
  optional `endSourceUrl`, or multipart `image` plus optional `endImage`. A
  start frame is required and URL/file channels cannot be mixed.
- `POST /v1/video-jobs/from-text` accepts only prompt, profile, optional seed,
  and optional requested duration. It is colleague-facing exploration, not a
  Plotloom authoring capability.

The legacy public `POST /v1/assets` and `POST /v1/video-jobs` creation routes
are removed without a shim. There is no public `assetId` or `idempotencyKey`.

Internally, `jobs` records `input_mode`, frozen requested duration, snapped
frame count, fps, and generation timestamps. Ordinary assets are connected by
immutable `job_frame_bindings` with `start` or `end` roles. Existing one-asset
jobs migrate to a `start` binding so their status and managed-output retention
remain readable.

Duration is a whole number in the reviewed 5–15 second range. The renderer
snaps it to MiniMax-H3's 24 fps `17k + 5` frame grid before dispatch; both the
requested duration and actual grid result are returned. `generationElapsedMs`
starts only after ComfyUI accepts the workflow and ends when completion is
observed. It intentionally excludes source downloading, image normalization,
and managed MP4 transfer; it is backend elapsed time, not a GPU-only metric.

Plotloom uses only the direct multipart I2V route, always with its existing
five-second frozen contract. Its adapter refuses a gateway whose V4 catalog
does not match. No Plotloom T2V UI or authoring route is introduced.

The runtime configuration marker for that reviewed catalog is
`VIDEO_MODEL=minimax_h3_gateway_catalog_v4`. Individual reviewed profile IDs
remain valid explicit runtime selections; no retired V3 catalog marker is
admitted. This configuration admission belongs to Plotloom's typed H3 adapter
contract and is checked before the gateway transport is constructed.

## Consequences

- Start and end frames follow identical decode, aspect, prepared-input,
  provenance, and retention policy. Failure while admitting either cleans up
  newly unbound frame assets.
- The renderer has an intentional zero/one/two-frame graph shape. It never
  leaves a `LoadImage` node disconnected from the H3 node.
- Colleagues get a smaller, direct API; a client timeout remains ambiguous and
  must not trigger an automatic duplicate retry.
- V3 data stays inspectable, but V3 creation endpoints cannot be called.

## Alternatives rejected

- **Keep upload and create routes as compatibility aliases.** It prolongs an
  unused public asset lifecycle and a second admission path.
- **Make end frame a special asset type.** Roles belong to the job-frame
  relationship; the same underlying asset policy must apply to either frame.
- **Expose gateway T2V in Plotloom now.** It would bypass the reviewed
  keyframe/identity workflow and is not part of current authoring scope.
