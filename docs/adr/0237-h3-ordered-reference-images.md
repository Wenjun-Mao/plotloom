# ADR 0237 — Ordered timed images for native H3 Ref2VA

Accepted for the bounded gateway contract on November 6, 2026. Source review
is closed; activation and learned capacity are separate acceptance rows.

## Context

The independent Shuohao sample refers to five ordered pictures and cut times.
The existing FL2VA START/END route and ADR 0205 image-and-voice route cannot
represent that input. Pinned Comfy Ref2VA accepts up to nine encoder images,
and AddGuide independently anchors each still at a video frame.

## Decision

Add `/v1/video-jobs/from-reference-images` with ordered references and explicit
nonnegative integer-millisecond times (`atMs`). Accept 1–9 single images, first at zero, strictly
increasing, each before the requested end. Use the existing Ref2VA 960x544 and 576x1024 canvases and integer
`durationMs` from 5000–15000. Multipart uses one typed `request` JSON field
and an ordered repeated `images` field. JSON uses ordered `sourceUrl` entries. Snap guide times
to nearest 24 Hz frames with half ties upward and reject resulting collisions.
Snap total length upward to native 17k+5. Retain requested and resolved values.

Each image occupies its ordered Ref2VA text-encoder slot and exactly one timed
AddGuide. Use Ref2VA INT8 ConvRot, Base-20, `ref_image_size=match` and the adopted
VAE policy. The submitted prompt passes unchanged. Callers author prose, image
order and requested times. Trusted code owns validation, quantization and graph
binding. Exclude audio references, videos, arbitrary graphs and model overrides.

Store `h3_contract=ref2va` with a distinct versioned reference-images snapshot.
Extend only the exact known child frame-binding role schema losslessly. Reuse
atomic job/lane admission, status/download, queued cancellation and retention.
Snapshots bind every original and prepared image, timeline entry and prompt.
Originals are private. Prepared PNGs are readable by the Comfy input owner.
UNKNOWN holds protect active inputs and forbid resubmission.

Expose route-specific readiness and requested/resolved timeline readback.
Preserve existing FL2VA, voice and Qwen route contracts. Verify the generic
gateway with retained fixtures and one separately coordinated learned job for
the uncovered five-reference conditioning integration question. The later owner
authority prospectively substitutes the exact E01-01 story job for the generic
fixture; original prompt and final manager-frozen frames remain source-owned.
The owning plan is `docs/roadmap/2026-11-06-h3-reference-images.md`.

## Consequences

An 11.3-second request maps to 277 native frames, with its actual duration
reported separately. Caller-visible rounding makes fractional timing reviewable.
Reference blocks and timed guides add memory and compute. Node availability
alone does not establish runtime capacity, reliability or creative quality.

For this rollout, recovery uses a bounded gateway forward fix on the expanded
current schema. Retain the preceding gateway stopped/restart-disabled for audit;
no old-gateway restoration, schema reversal/reset/copy or compatibility layer is
authorized. Preserve admission and UNKNOWN evidence. Dashboard recovery remains
independent after fresh idle checks. This is a selected current-contract recovery
policy, not an assertion that the actual preceding binary rejects the new DDL.
