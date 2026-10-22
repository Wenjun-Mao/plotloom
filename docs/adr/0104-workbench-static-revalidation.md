# ADR 0104: Workbench static revalidation

Status: Accepted

## Context

The frontend build deliberately uses stable `workbench.js` and `workbench.css`
URLs. Default static responses supplied ETag and Last-Modified validators but
no cache policy. During verification of ADR 0103, the server returned the new
bundle while the browser's loaded resource still contained an older bundle.
Without an explicit policy, clients can reuse heuristically fresh cached bytes
without asking the server whether a deployment changed them.

## Decision

The `/v2` static response owner sends `Cache-Control: no-cache` on successful
and not-modified responses, including entry HTML and stable-name JS/CSS.
Cached bytes may be reused only after server revalidation. Existing ETag and
Last-Modified validators, byte serving and conditional 304 responses remain
owned by StaticFiles. This policy applies to the whole mounted frontend build
so HTML and its dependencies follow one freshness contract.

## Consequences and guardrails

- Ordinary document navigation can obtain the current build without heuristic
  reuse of stale bundles. Already executing JavaScript remains unchanged until
  document navigation; this is not automatic replacement of a running app.
- Previously cached responses lacking this policy can require one deliberate
  cache-bypassing navigation. Verification must compare the browser's actually
  loaded resource with deployed bytes, not merely the server's latest response.
- Runtime processes must restart to install the response owner. Normal and
  isolated-copy servers share the same contract; both need an explicit restart
  when this Python source changes.
- HTTP tests exercise HTML, JS and CSS through the real runtime mount: initial
  200, unchanged 304 by either validator, updated 200 and HEAD retain policy.
- Disabling caching with `no-store` was rejected because validator-backed 304
  reuse remains useful. Renaming build outputs was unnecessary for the existing
  stable-name deployment contract; caller-specific reload fixes would leave
  ordinary navigation exposed to the same missing policy.
