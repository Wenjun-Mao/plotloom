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
- Atlas's hosted upload reference is the adopted upload-response authority: a
  successful upload is a JSON object containing a top-level HTTPS `url`. The
  adapter sends multipart field `file` to `POST /api/v1/model/uploadMedia` and
  rejects every other 2xx response shape. In particular, `data.url` is not a
  compatibility path; an Atlas-maintained skills repository currently shows the
  conflicting `data.download_url` shape, which requires an explicit future
  contract decision rather than permissive parsing.
- After the durable dispatch claim, persist only allowlisted diagnostic evidence:
  phase, a safe code, and (when received) an HTTP status. Provider bodies,
  signed URLs, credentials, and exception text are never diagnostic evidence.
  This does not make a failed upload or malformed submission response replayable:
  every post-claim diagnosis remains `outcome_unknown` and retains its requested
  seconds. Historical unknown outcomes remain unchanged.

## Alternatives and consequences

Reject generic V1 payload reuse (Wan uses a different input field), automatic
fallback/retry (uncertain duplicate spending), and account balance as a local
allowance mechanism (not a concurrency-safe pilot limit). Reject building a
general video editor before one usable clip. Conservative seconds accounting can
stop earlier than actual billing requires; this is intentional and not a dollar
cap. User approval is required to enlarge it.

Reject accepting every plausible nested upload URL: it would make an application
error response indistinguishable from a successful upload and would conceal a
provider contract conflict. A separately authorized, evidence-preserving
qualification is required before extending the strict response allowlist.

P1.5 identity/framing evidence permits planning this pilot, not approval of the
known glove-side-defective profile output. Input review excludes that candidate.
The first clip and adjoining-shot experiment must earn separate real audiovisual
receipts before P3. Regression/restart/budget tests and attributed listening/viewing
in the linked plan guard these boundaries. No live video was made for this ADR.
