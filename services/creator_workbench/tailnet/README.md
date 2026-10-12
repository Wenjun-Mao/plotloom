# Dedicated private Plotloom hostname

This optional Mac + Docker deployment gives the existing workbench a separate
Tailscale node named `plotloom`. The configured owner URL is
**https://plotloom.tail6040ad.ts.net/v2/**. Owner authentication, exact-name
checks, HTTPS/frontend/API access from the Mac peer, and new-container
recreation were verified on 2026-10-11; see the
[deployment receipt](../../../docs/verification/2026-10-11-plotloom-tailnet-name.md).
For a fresh installation, authenticate its new node and verify the assigned
tailnet/name before claiming that address as available.

It does not rename or retag the Mac, modify its Serve endpoints, restart the
workbench, or copy project data. The existing Mac's HTTPS 443 -> localhost:8000
and HTTPS 8443 -> localhost:8841 mappings remain separate.

## Start and authenticate

Run from the Plotloom checkout, with the existing workbench already healthy:

```sh
docker compose -f services/creator_workbench/tailnet/compose.yaml config --quiet
docker compose -f services/creator_workbench/tailnet/compose.yaml up -d
docker compose -f services/creator_workbench/tailnet/compose.yaml exec tailscale tailscale status --json
```

The first start uses interactive Tailscale authentication, not an auth key in
Compose, a command, or the repository. Follow its one-time login URL and approve
only this `plotloom` device using the intended tailnet account. Device approval
may also be required by the tailnet policy. Do not put that login URL into Git,
verification receipts, screenshots or shared reports. The node is not an
ephemeral CI device. Its private state stays in the dedicated Docker volume
`plotloom-tailnet_tailscale-state`, outside application/project storage.

`TS_AUTH_ONCE` retains that identity across restarts. Its user-owned key expiry
policy still applies; reauthenticate the same retained node when needed. Do not
clear its state or silently register replacement nodes to bypass expiry.

## Access and preservation boundary

Userspace networking needs no published host ports, TUN device, privileged
mode, added capabilities, subnet routes, exit-node advertisement or Tailscale
SSH. Serve terminates HTTPS 443 only on this node's tailnet interface. The
configuration contains no `AllowFunnel` entries; no public Funnel is enabled.
The optional health endpoint is loopback-only inside the container.

The proxy target is the existing managed workbench through Docker's host
gateway, `http://host.docker.internal:8841`. The deployment owns its own Docker
network; it neither shares the workbench's namespace nor attaches to the
workbench's Compose network. A workbench replacement does not require changing
the target or recreating this proxy. During workbench downtime requests can
fail; a healthy Tailscale node alone is not application readiness.

This remains the same shared-admin workbench, not a read-only player or a
multi-user permission model. Permitted colleagues can use its project,
settings and native production controls. Only grant access to trusted operators.
See the [existing access boundary](../README.md#private-colleague-access-over-tailscale)
and [ADR 0095](../../../docs/adr/0095-persistent-creator-workbench.md).

## Verify before sharing

Check the new node's `BackendState`, `Self.DNSName`, tailnet and certificate
domain. A suffixed name such as `plotloom-1` is not the requested address; stop
and resolve ownership rather than rename another device. Then inspect only
this node's Serve config:

```sh
docker compose -f services/creator_workbench/tailnet/compose.yaml exec tailscale tailscale serve status --json
curl --fail https://plotloom.tail6040ad.ts.net/healthz
curl --fail https://plotloom.tail6040ad.ts.net/api/v2/runtime-capabilities
```

Validate `/v2/` and its assets with normal certificate verification from an
authorized peer, including the Mac. Recreate only this new container and verify
its identity, configuration and URL survive. Recheck the Mac's original name
and both Serve mappings, the workbench's container identity and loopback port,
and absence of Funnel before declaring setup complete. Do not restart the
valued workbench just to exercise proxy recovery; that belongs in an authorized
maintenance window.

The image is pinned to official release `v1.102.5` and its OCI index digest.
Although the Serve reference still describes loopback-only targets, this
release's [CLI regression](https://github.com/tailscale/tailscale/blob/v1.102.5/cmd/tailscale/cli/serve_v2_test.go#L225),
[target validator](https://github.com/tailscale/tailscale/blob/v1.102.5/ipn/serve.go#L807)
and [daemon system dialer](https://github.com/tailscale/tailscale/blob/v1.102.5/ipn/ipnlocal/serve.go#L1000)
support explicit HTTP hostname targets. The chosen image must be verified
against the live host-gateway route; do not substitute an unverified moving
tag or silently add relay containers. [Official Docker parameters](https://tailscale.com/docs/features/containers/docker/docker-params)
define the persistent state and `${TS_CERT_DOMAIN}` Serve setup.

## Stop without losing identity

```sh
docker compose -f services/creator_workbench/tailnet/compose.yaml stop
```

`start` resumes it; `up -d` can recreate it with the same retained volume. To
remove just these deployment containers and network while preserving identity,
use this exact Compose file's `down` without `--volumes`. Never delete the
state volume, remove the tailnet device, call the Mac's `serve reset`, or change
the Mac's identity as routine cleanup.
