# ADR 0105: H3 review during media read withdrawal

Status: Accepted

## Context

An unrelated image delivery triggered a media refresh while a creator was
reviewing A1's H3 sources. The fail-closed reader projected no binding and
selection revision zero during loading. H3 treated those unknown values as a
source change, erased its English buffer and regenerated its seed when the
same authoritative A1 binding returned.

## Decision

Media availability is separate from authoritative H3 source identity. The
editor retains the last ready binding, exact intent, identity-review and asset
identity for comparison only; it does not project retained media as current.
Project-wide selection revision remains the current request CAS token, not
the source identity of an unchanged Shot.

Loading or error suspends source read, preview and freeze, cancels late read
and preview callbacks, and withdraws consent and compiled authorization.
The creator's seed, English buffer and prior source hash remain visible as
unverified work. Recovery requires an explicit fresh source read using the
same seed and current CAS token. Only an exactly matching server source hash
preserves English; a different hash initializes blank fields. Consent and
compiled preview must then be obtained again.

Authoritative binding, intent, identity-review, project, Shot, request settings
or end-frame changes still invalidate the old package. Explicit seed edits
keep ADR 0102's invalidation semantics. No request is automatically frozen,
submitted or retried, and server source-hash/currentness checks are unchanged.

## Consequences and guardrails

- Unknown reads no longer discard creator work or silently change a comparison
  seed. A restored read alone never restores permission to freeze.
- Integrated workbench/video tests exercise unrelated image polling, deferred
  success, error/retry, exact versus different source hashes, late read/preview
  callbacks, current CAS use and genuine binding/intent/review changes.
- Existing project/Shot, seed, settings, end-frame and source-ownership tests
  remain required. Scope changes do not inherit another scope's review.
- Keeping stale media current or disabling polling was rejected: freshness
  withdrawal is intentional and must not become a caller-specific exception.
