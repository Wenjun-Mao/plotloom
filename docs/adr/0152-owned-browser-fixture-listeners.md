# ADR 0152: Browser-fixture listener ownership

Status: adopted for the E2E fixture, 2026-10-09; final focused checks, independent
code review and the full zero-retry local browser gate pass. Exact-input hosted
qualification is pending.

## Problem and evidence

Hosted run38009336409, browser shard2, first attempted the Source dirty-refresh
test with both provider and backend at127.0.0.1:35937. Its trace records successful
provider readiness followed by backend bind refusal before the test body. The
retry passed, so the job is green with one flaky test, not clean first-pass.
The fixture's `reserveLoopbackPort` closed each probe before returning its number;
sequential probes could receive the same address. Production exact-port refusal
was correct. No UI, lingering-process or TIME_WAIT cause is established.

## Decision

Each test-owned service binds its own loopback socket using OS allocation and
keeps it open through serving. A role/host/positive-port stdout receipt reports
that already-bound address; the parent uses it for ordinary bounded HTTP readiness
and Vite's exact backend proxy. A receipt is not HTTP readiness or test acceptance.
Reject incomplete, malformed, duplicate or wrong-role receipts and exited owners.

The Python fixture hands its open socket directly to Uvicorn, setting production
configuration only after the OS returns a positive port. Backend restarts bind
the original exact address, preserve roots and refuse collision without fallback.
The external provider binds directly. The Vite fixture first binds its parent
HTTP server, then loads the ordinary Vite config through its public middleware
API with the actual positive port. `middlewareMode.server` supplies the parent
for proxy upgrade handling; `hmr.server` separately attaches Vite's HMR listener
to it, with the actual `clientPort`. Both settings are required. The same owned
server handles HTTP/proxy and HMR. Locked Vite7 `listen(0)` substitutes the default
port; initializing with0
and directly binding Vite's HTTP server also freezes0 into its HMR fallback.
Binding before initialization avoids both defects. No private Vite/socket fields
or alternate application/HTML routing is used.
Child processes and test roots remain owned by the existing fixture cleanup.

## Alternatives and guardrails

Holding three probes until allocation completes would prevent duplicate numbers
but retain a release-before-child-bind race. Retries, added sleeps, production
fallback and readiness tolerance hide the ownership defect. They are rejected.
Normal runtime/PORT rules, provider behavior, deadlines and retry policy stay
unchanged; no compatibility path is added.

Deterministic tests demonstrate the old release gap, exclusive live ownership,
distinct service roles, startup-failure cleanup and exact restart. Browser tests
exercise actual Vite proxy/HMR and checked-static composition with persisted data.
Re-run the failing Source tests, relevant restart cases, then the full browser gate
with zero local retries. Preserve original flaky evidence separately from repair
qualification; re-run exact committed hosted inputs once, without duplicating a
still-active prior run.
