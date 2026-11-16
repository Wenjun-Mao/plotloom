# ADR 0241 — Workbench request source IP attribution

Accepted: 2026-11-16.

## Context

Repeated failed colleague polling reached the Mac workbench through Tailscale
Serve and Docker. Uvicorn's default loopback-only proxy trust logged the Docker
gateway, losing the peer address needed to identify the originating machine.

## Decision

Use Uvicorn's existing access logging and proxy-header handling. The workbench
manager accepts `start --trusted-proxy-ips` as comma-separated exact IPs,
persists the normalized selection in installation-local deployment configuration,
and explicitly supplies `FORWARDED_ALLOW_IPS` through Compose. The unchanged
default is `127.0.0.1`; an empty selection disables forwarded trust. Reject
wildcards, networks and hostnames. Never infer trust for all Docker networks.

The operator verifies the current transport gateway before configuring it and
rechecks after a Docker network recreation. This setting changes only the
existing proxy/client metadata handling; it does not enable Tailnet, change
project schemas, add analytics, or dispatch providers. No new header/body/token
logging or project persistence is introduced.

Tailscale Serve [v1.102.5 replaces inbound X-Forwarded-For with its peer IP](https://github.com/tailscale/tailscale/blob/v1.102.5/ipn/ipnlocal/serve.go#L1068-L1075).
[Uvicorn 0.52.4 applies forwarded headers only for a trusted transport peer](https://github.com/Kludex/uvicorn/blob/0.52.4/uvicorn/middleware/proxy_headers.py#L28-L78).
The result identifies the Tailscale source node, not its public/LAN address.
Processes able to reach the Mac loopback publication share the Docker gateway
and can supply forwarded headers. Therefore this is operational attribution,
never authentication or authorization. No application policy may rely on this
IP as proof of machine identity. Historical gateway-only logs remain unattributed.

## Verification

Provider-free checks cover finite selection, persistence and Compose/Uvicorn
wiring, direct callers, forwarded callers and an untrusted transport peer.
Activation reuses the exact deployed image and retained runtime, preserves all
data/credential/H3 mounts and settings, and leaves the owner's stopped Tailnet
container stopped. A synthetic read-only request proves access-log attribution;
a future real colleague request is required to establish that caller's identity.
