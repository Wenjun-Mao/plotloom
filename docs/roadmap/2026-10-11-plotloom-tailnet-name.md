# Dedicated Plotloom tailnet name

Status: owner-approved setup implemented and operationally qualified.

## Authority and outcome

The owner requested `plotloom.tail6040ad.ts.net` for colleagues, Tailscale-only,
without renaming the Mac or changing its other endpoint. Provide the existing
workbench at `https://plotloom.tail6040ad.ts.net/v2/`, preserving both existing
Mac Serve mappings, the workbench runtime, valued projects and credentials.

## Bounded implementation

Use the [independent node deployment](../../services/creator_workbench/tailnet/README.md)
and [ADR 0095](../adr/0095-persistent-creator-workbench.md): one pinned official
userspace Tailscale container, private persistent state, separate network,
interactive owner authentication and HTTPS Serve to the existing host gateway.
Do not retag/rename the Mac, restart or replace the workbench, add host ports,
enable Funnel, alter access/expiry policy, expose the bridge directly, copy
projects, dispatch providers or save an auth key/login URL in source.

## Evidence and stopping condition

Complete after the exact tailnet/hostname is confirmed, normal TLS and
frontend/assets/API access pass from an authorized peer, only the new container
is recreated with stable identity/config, original endpoints/runtime remain
unchanged, and the reviewed configuration/documentation are published.
The [dated receipt](../verification/2026-10-11-plotloom-tailnet-name.md) records
those executed checks and the no-actionable-findings independent review.

This is an operational deployment qualification, not whole-product or hosted
CI qualification. No CI dispatch is authorized by this setup. Real colleague
device access, ongoing key-expiry operations and a future authorized workbench
replacement/downtime exercise remain explicit operational follow-ups.
