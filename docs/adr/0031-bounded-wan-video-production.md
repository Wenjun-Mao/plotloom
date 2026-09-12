# ADR 0031: Bounded Wan video production

Status: approved implementation contract, 2026-09-12. Provider/model and the
100-second pilot allowance are user-approved; the detailed
[P2 plan](../roadmap/p2-wan-audiovisual-pilot-plan.md) is prepared for review.

## Problem

P1 freezes image production inputs, but a remote paid video request introduces
submission uncertainty, temporary output URLs, duration-based allowance and
audio review. Re-enabling historical raw-Shot MediaTask execution would bypass
current Approval/reference ownership and cannot safely establish these properties.

## Decision

- One approved selected keyframe and current canonical audiovisual context form
  an immutable video snapshot. Canonical data owns story truth; the adapter owns
  Wan request syntax; output metadata owns observed duration, not authored timing.
- Start with AtlasCloud Wan 3.0 only, 5 seconds/720p/audio enabled. Keep explicit
  versioned capabilities outside canonical story data. Grok and smart duration
  are excluded. Reuse Plotloom server credentials, never V1 runtime configuration.
- Enforce a shared durable 100-second requested-duration ledger. Reserve and
  claim transactionally before dispatch; after dispatch conservatively retain
  the charge for failures and unknown outcomes. Only proven pre-dispatch failures
  release reservations. No automatic resets, allowance refunds or blind POST retry.
- Separate remote execution, local ingestion, cancellation intent and creative
  approval. A timeout is not failure, a remote URL is not a stored artifact, and
  an audio track is not evidence of correct dialogue. Candidate selection and
  review bind precise revisions/hashes and become stale on dependency edits.
- Upload approved bytes without exposing local/Tailscale services. Confine and
  validate public-provider downloads, preserve managed bytes, and retry retrieval
  without regenerating. Existing legacy provider-production hard stops remain.

## Alternatives and consequences

Reject generic V1 payload reuse (Wan uses a different input field), automatic
fallback/retry (uncertain duplicate spending), and account balance as a local
allowance mechanism (not a concurrency-safe pilot limit). Reject building a
general video editor before one usable clip. Conservative seconds accounting can
stop earlier than actual billing requires; this is intentional and not a dollar
cap. User approval is required to enlarge it.

P1.5 identity/framing evidence permits planning this pilot, not approval of the
known glove-side-defective profile output. Input review excludes that candidate.
The first clip and adjoining-shot experiment must earn separate real audiovisual
receipts before P3. Regression/restart/budget tests and attributed listening/viewing
in the linked plan guard these boundaries. No live video was made for this ADR.
