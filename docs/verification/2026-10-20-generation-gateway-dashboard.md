# Generation gateway dashboard — 2026-10-20

Status: **HISTORICAL LOOPBACK VERIFICATION; HTTPS GATE RESOLVED 2026-10-21.**
See [private HTTPS closeout](2026-10-21-h3-dashboard-generation.md#private-https-closeout--2026-10-21).
The initial refusal and pending checks below are preserved as original evidence,
not current blockers. H3 creation is the separately approved ADR 0215 extension.

Owner approved the [plan](../roadmap/2026-10-20-generation-gateway-dashboard-plan.md)
and selected Tailscale-only access. Source owner is the retained H3 specialist
checkout, baseline `fa56e775`; no broader specialist integration/merge/push is implied.

## Local checks so far

- Full locked gateway suite: 168 passed; one existing Starlette deprecation warning.
- Dashboard subset: 27 passed; Node UI regression tests: 2 passed.
- Targeted Ruff, JavaScript syntax and patch whitespace checks passed.
- Independent GPT-6.1 Sol / Medium review found two concrete P2 issues: recorded
  MIME was not checked, and switching to a failed job retained old detail fields.
  Both corrected, with regression tests; correction review reports no material finding.
- Image dependency installation changed from direct pins to checked `uv.lock`;
  only the dashboard's required package modules are copied into its image.
- Headed local Chrome used a real FastAPI/file-SQLite disposable fixture and
  unchanged retained MP4. Native play/seek and polling video-node preservation passed.
  That fixture is not a production job or a new generation/quality acceptance.
- Initial browser command used the older CLI snippet shape and was rejected before
  execution; the current CLI requires an async function. Corrected invocation passed.
  Initial data-URL favicon was blocked by CSP; replaced with an allowlisted same-origin
  static SVG. Final browser/static qualification is recorded below when available.

## Deployment evidence

- Implementation checkpoint: `0124ca59`; locked image build passed on Spark ARM64.
  Dashboard image: `sha256:e6675b1fb5d13c01e349539c90f249bfaac9d3fa590b1383295eecf037ba06cc`.
- Release root: `/home/wjmao/services/plotloom-h3-dashboard/releases/20261020.phi6au`.
  Independent container `plotloom-h3-dashboard`, ID
  `89cef929eec6f5256535f5fe819dae6b40ff38e8e13c8c1f5daba30962e9a690`.
  Loopback page/assets/overview/list returned200; generation `/v1` path returned404.
- Activation of the container was preceded by an observed empty shared lane/queue
  and empty Comfy queue. Container is healthy, unless-stopped, UID1000, no GPU/key/
  environment-secret mount; the only bind mount is gateway data `/data`, RW=false.
  Actual mounted SQLite uses DELETE journaling; live rows read and write attempt
  refused. No initializer, migration, reconciliation or dispatch worker ran.
- Spark loopback original output GET and HEAD Range both returned206 with exact
  Content-Range. Full original-byte download matched its recorded hash and
  4,080,043-byte size. Only the dashboard was restarted; reads recovered and the
  job count remained152. This is not a whole-host reboot test.
- Generation gateway ID remained
  `4020bc9e8dff13da68ca839f91e142f53e5104df60e8257f4cc22400520a42d6`, image
  `sha256:f833c3469ea62c94c428ea5d98e0e8236fc317dd6a6721a8a4f7c7d51e6ad692`;
  Comfy ID remained
  `8542065d40cb5226eb50ecfbd838565e264fe8c2b02c0efe604d1af68b68354e`, image
  `sha256:db0010004575a508b5ac67fb36ea4ab83cf1964a84e70932019749f330c64110`.
  Both retain October6 start times; neither was restarted or replaced.
- Additional extraction/source-admission regression:13passed after source commit.
- Headed local browser also passed identity withdrawal after injected detail-read
  failure, PNG preview, prompt text-only handling, selected-job reload and phone
  page-width check. The first fault check waited on a role absent from the existing
  detail notice and timed out; the corrected exact notice locator passed. Injected
  request failures are retained as test errors, not unexplained application errors.
  Screenshots are [desktop](supporting/h3-dashboard-local-desktop-20261020.png),
  [phone overview](supporting/h3-dashboard-local-phone-20261020.png) and
  [phone detail](supporting/h3-dashboard-local-phone-detail-20261020.png).

## Native HTTPS gate — owner action required

The supported Tailscale CLI refused the attempted exact handler with exit1:
`sending serve config: Access denied: serve config denied`. Its configuration
remains `{}`; no handler or Funnel was created. Noninteractive sudo is unavailable.
Do not claim the proposed HTTPS URL is live. No permission/ACL/operator change or
alternative publication mechanism was attempted.

On Spark, an administrator can run the exact scoped command:

```sh
sudo tailscale serve --bg --https=443 --set-path=/dashboard http://127.0.0.1:8091/dashboard
```

The target path deliberately restores the app-owned prefix: installed Tailscale
[v1.102.4 strips the mount prefix before proxying and joins the target path](https://github.com/tailscale/tailscale/blob/v1.102.4/ipn/ipnlocal/serve.go).
This source analysis is not a substitute for the pending live HTTPS routing test.
Do not use a global reset or grant general operator privileges merely for this step.

After owner activation, verify Serve configuration, normal TLS validation, the
actual `/dashboard`→`/dashboard/` redirect, resources/JSON/media paths, native
play/seek and full-download hash through HTTPS from the Mac. Confirm no Funnel
and no `/v1` publication. These remain pending, so the approved slice is not yet
reported complete. Local fixture server/browser are stopped; the read-only Spark
dashboard remains healthy on loopback, ready for the native gate.

Rollback only this handler, if it was actually added:

```sh
sudo tailscale serve --https=443 --set-path=/dashboard off
```

Stop the dashboard with the dedicated Compose file if rollback is requested;
never delete gateway data or restart the generation services as part of rollback.
