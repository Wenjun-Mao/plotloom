# Plotloom's dedicated Tailscale name

Status: owner-authenticated deployment is live at
`https://plotloom.tail6040ad.ts.net/v2/`. TLS, frontend/API access from the Mac
peer, recreation persistence and existing-service preservation passed. A real
colleague-device check remains separate; no whole-product acceptance or hosted
CI result is claimed by these operational checks.

## Approved scope and decision

The owner requested that exact app-specific address, Tailscale-only, without
renaming the Mac or changing its existing endpoint. See the dedicated-node
clarification in [ADR 0095](../adr/0095-persistent-creator-workbench.md) and
the [operator guide](../../services/creator_workbench/tailnet/README.md).

The existing Mac is an untagged, user-owned Tailscale node named
`wenjuns-macbook-pro.tail6040ad.ts.net`. A named Tailscale Service requires a
tag-owned host, so reusing it would change the Mac's access identity. Instead,
one new userspace Tailscale container has its own network and persistent state
volume, with no published ports, privileged mode, TUN device, added
capabilities, route/exit-node advertisement or SSH. Serve proxies HTTPS 443
to the unchanged workbench through `http://host.docker.internal:8841`.
Its config contains no public `AllowFunnel` entry.

There are no application, API, schema, provider, generation, project-storage,
Python dependency or existing service changes. The new optional deployment
does not own or mount any valued project directories. No project or provider
action was performed; no workbench restart, full suite or hosted CI was run.

## Verification executed before authentication

- The checkout was clean at `3f38cf0b1cb3c9fa486fd79aaec45a5698116649`.
- Host Tailscale version was 1.104.1. Neither spelling of that Docker tag was
  available; Docker Hub's official registry identified stable as v1.102.5.
  The verified index digest is
  `sha256:c507f3a2a6ab1cabd8d809b98edeb41edbd5c3fb6ad9632ffd098b4c7d0b4065`.
- Pulled the explicit official version/digest. Its isolated `tailscale version`
  command reported 1.102.5. Released source confirms ordinary Serve accepts
  explicit HTTP hostname targets and uses a system dialer, despite the older
  documentation's localhost-only wording. The operator guide links the exact
  released CLI regression, target validator and daemon transport.
- `docker compose -f services/creator_workbench/tailnet/compose.yaml config --quiet`
  and `git diff --check` passed. An attended GPT-6.1 Sol / Medium read-only
  design and stable-candidate review found no actionable issues.
- The exact pinned image, first in an isolated one-shot container and then in
  the started node, read the existing upstream `/healthz` successfully.
- `docker compose -f services/creator_workbench/tailnet/compose.yaml up -d`
  started only `plotloom-tailnet-tailscale-1`, creating its dedicated network
  `plotloom-tailnet_default` and volume `plotloom-tailnet_tailscale-state`.
  Inspect confirmed no port bindings, privileged mode, added capabilities or
  devices. Only its private state volume and read-only config directory are
  mounted.
- At that staging checkpoint the node reported `NeedsLogin`, with no assigned
  DNS name or Tailscale IP.
  Its one-time authentication page was opened for the owner; no credential or
  approval was submitted. Authentication URLs are deliberately omitted here.

## Preservation and remaining gates

The valued workbench remains container
`6ad4a274a4cee2bb4531e3174e9d4f38b8d254c04465a5411f4802aa5b22a8e3`,
started at `2026-10-11T14:10:16.088160382Z`, with host publication limited to
`127.0.0.1:8841`. The Mac's Serve config still has exactly its HTTPS 443 ->
localhost:8000 and HTTPS 8443 -> localhost:8841 mappings, with no Funnel.
No existing endpoint was removed or repointed.

## Completed authentication and peer qualification

The owner subsequently completed the interactive login. The node reported
`Running`, `Online: true`, the intended MagicDNS suffix `tail6040ad.ts.net`
and exactly `plotloom.tail6040ad.ts.net` (no suffix), with IPv4 `100.122.10.97`.
Its Serve config contained only HTTPS 443 -> `http://host.docker.internal:8841`,
with no Funnel. The existing Mac is a distinct Tailscale peer, not this node.

From that Mac, normal hostname resolution and certificate validation returned
HTTP 200 for `/healthz` with `TLS verification 0`, the Plotloom HTML title at
`/v2/`, and the same-origin `/api/v2/runtime-capabilities` JSON. The active
instance still has `apiTextPipeline: false`. The HTTPS-served `/v2/workbench.js`
matched the checked local static asset exactly at SHA-256
`5c0e0a7d43ad4eb68d17ed324a8fdba3923ffa223ab5fe17ffdd32cae807deac`.
The real in-app browser also rendered the Plotloom start page with the
`创建空白项目`, `打开示例项目` and `打开项目目录` controls at this URL; no
project action was taken.

Recreated only the new proxy with
`docker compose -f services/creator_workbench/tailnet/compose.yaml up -d --force-recreate --no-deps tailscale`.
Its retained Tailscale node ID, exact hostname, IPv4/IPv6 addresses and Serve
configuration matched before/after. HTTPS health and API reads passed again
after recreation, without another login or an auth key. The original workbench
container ID, start time and loopback publication remained exactly as recorded
above; the Mac retained its name, untagged identity, IP addresses and both
unchanged Serve mappings. No existing proxy was removed or repointed.

## Remaining operational limits

The configured URL is available to tailnet clients allowed by the existing
policy; no policy, device-expiry or per-user role change was made. A real
colleague-device test remains separate from the verified Mac peer. The Mac,
Docker and workbench must remain running; user-owned node key expiry and the
existing shared-admin trust boundary still apply. Workbench-replacement
recovery was not exercised by restarting valued work; its deliberate downtime
test belongs in a future authorized maintenance window.
