# Identify the machine sending workbench requests

## Current status

Updated: 2026-11-16. Source/qualification owner: this chat. Baseline: main
`e9fb9c2d`, with unrelated H3 specialist changes preserved. Existing access logs
record only the Docker gateway `192.168.156.1`; the original historical caller
cannot be recovered from them. The owner stopped the dedicated Tailnet node;
it stays stopped. Finite trusted-proxy configuration is implemented and tested;
an isolated real HTTP request recorded its synthetic forwarded IP. Activation
is held because `/api/v2/specialists` reports an active outline task. Next:
at a native idle checkpoint, activate only the proxy configuration on the exact
existing workbench image/runtime; do not clear the task or its reservation to
obtain idleness. Stop when live read-only log attribution and deployment/data
identity are verified, with Tailnet still stopped.

## Acceptance

| Claim | Required evidence | Fresh media | Status |
|---|---|---|---|
| Future proxied requests show the originating IP | Existing Uvicorn access logging, with only explicitly configured proxy addresses trusted | No | Passed in isolated actual HTTP server; live workbench activation pending |
| Trust is bounded and durable | Managed configuration rejects wildcard/network/hostname trust, persists exact IPs, and passes them to Compose; untrusted peers cannot replace the client address | No | Passed: 14 focused proxy tests; actual Compose compilation also passed |
| Activation preserves the installation | Same image, source mount, writable data mounts, credentials and H3 settings; healthy read-only API; Tailnet remains stopped | No | Held: workbench busy with an outline task; no live configuration/runtime change made |

## Scope and method

Own only creator-workbench proxy configuration, focused tests and documentation.
Use the deployed Uvicorn middleware and access log, without adding an analytics
store, logging request bodies/credentials, or making IP an authentication signal.
The fixture is an isolated HTTP server plus synthetic trusted/untrusted proxy
requests; the real journey is a read-only workbench health/API request. No
provider dispatch, project schema upgrade, project mutation, frontend change,
Spark change, CI or publication. Root owns temporary test cleanup. Keep the
dedicated Tailnet container stopped throughout.

The current deployment runs image `sha256:5bbf544dcd28116fa64eff1066ce085ce1478945b9933e61ff05f3060fa3ba60`
with a separate retained runtime checkout at revision `543df21cf9ed61c0ee6ebfa440432ecc342f6af2`.
Do not replace that checkout or rebuild it from current main for this change.
Trusting the Docker gateway also trusts processes able to reach the Mac's
loopback publication. These operators already share administration; log IPs
remain operational attribution, not authenticated device identity.

## Verification and operational findings

- `verify.py focused --pytest tests/services/creator_workbench/test_proxy_configuration.py --pytest tests/services/creator_workbench/test_h3_runtime.py`: 41 passed. The latter selection preserves the existing H3 opt-in and credential boundaries without provider contact.
- `verify.py quick`: passed; this is scoped development feedback, not complete release qualification. Existing jsdom `window.scrollBy` diagnostics and the Starlette TestClient deprecation warning were non-failing.
- Independent GPT-6 Luna/Max source review found no concrete defect. It confirmed the activation constraint: avoid `manage.py start`, which also rebuilds and may reload the bridge. Review reused the parent test evidence.
- Compiled the actual Compose configuration with the retained runtime path and proposed exact allow-list `127.0.0.1,192.168.156.1`; checked forwarded-IP environment, loopback publication and retained working directory without applying it.
- A temporary loopback HTTP server using locked Uvicorn 0.52.4 logged the controlled `203.0.113.42:0` forwarded client and returned HTTP 200. The server was terminated; no provider or project was touched. This was synthetic attribution, not a real colleague request or an end-to-end Serve test.
- Temporary receipts: `/private/tmp/plotloom-api-traffic-review-20261116/proxy-configuration-verification.json` and `ip-attribution-observation.json`.
- Host Tailscale peer lookup: deyang7 = `100.124.174.97`, deyang6 = `100.96.187.4`. This mapping does not identify the historical caller. Existing logs only show `192.168.156.1`.
- The final observed recurring HTTP 422 was 2026-11-16 15:32:50 Toronto; the dedicated Tailnet container stopped at 15:32:55. No recurring polling was observed afterward. Keep the separate Mac Serve mappings unchanged.

## Activation boundary

Do not run current-main `manage.py start` against the retained deployment: it
would rebuild an unrelated runtime. Its deployed `manage.py`, `compose.yaml`
and `compose.h3.yaml` match the source baseline for these files. Once idle,
apply only the scoped manager/Compose patch to that retained runtime, persist
the exact verified proxy allow-list, and use the native Compose path with
`up -d --no-build --pull never --wait --wait-timeout 90 workbench` after checking
the image tag still resolves to the pinned current image. Compare all other
service settings and mounts before applying. Read back health/API and a
controlled source-IP log entry; ensure the dedicated Tailnet container remains
stopped. No schema upgrade or stale-task clearing is part of this assignment.
