# ADR 0095 — Persistent local creator workbench

Status: accepted, 2026-10-01.

## Problem

The creator walkthrough ran in a foreground Codex terminal without a service
manager. A Mac reboot stopped it; no owner restarted it. Project data was
durable, but server availability depended on an interactive session.

## Decision

Run the existing walkthrough composition in Docker Compose, detached with
`restart: unless-stopped`, a readiness check and bounded logs. Bind port 8841
only to localhost. Mount the source checkout read-only and the existing outputs
and application directories writable at their original absolute paths. Keep
SQLite, assets, packages, specialist bindings and dispatch leases outside the
container; do not relocate/rewrite requests or start with a fresh project store.
The image contains locked Python dependencies plus Node and Git, which current
art validation and upstream execution pins require.

### Playback tooling and activation clarification (2026-10-03)

The exact playback path in ADR 0082 requires FFmpeg and ffprobe in the server's
execution environment. The retained container lacked both, even though the Mac
isolated runtime supplied them. The image now installs the distribution's
FFmpeg package and checks both executables during build; enabling a provider
remains a separate explicit configuration decision. Relying on host PATH or
moving derivation to a provider would hide a missing deployment dependency.
Read-only mounted Python source is not hot reload: explicit `start` now forces
container recreation even when mounted-only changes leave the built image and
Compose configuration unchanged. A regression asserts build → bridge → forced
recreate → health order. Static bundle bytes are served from the mount and
can become visible earlier. Activation therefore requires a quiet dispatch
checkpoint and deliberate admission of any changed project schema; frontend
visibility alone does not prove an upgraded backend.

Native Codex queueing must remain on macOS. A separate login-started launchd
bridge runs only the existing `codex queue` command, authenticated with a local
token, and permits only the configured specialist task IDs. A container CLI shim
keeps the existing dispatcher and its reservations authoritative. Neither bridge
nor shim retries; lost acknowledgement still means outcome unknown. Credentials
remain outside project/application state and image layers. Health checks do not
queue tasks. This applies equally to text and image specialists.

### Repository service ownership clarification (2026-10-02)

The tracked `services/creator_workbench` deployment is the second explicit
service owner alongside `services/minimax_h3_gateway`. The extraction guard
had retained its older gateway-only allowlist despite this decision and the
committed workbench, causing the broad Python suite to fail. The guard now
names exactly these two real directories and still rejects unknown children,
foreign tracked paths, untracked files and missing tracked files. Credentials,
generated deployment configuration and runtime data remain outside both source
subtrees. Adding another service requires an explicit ownership decision, not
a general `services/*` exception. Focused tests exercise both admitted owners.

### Explicit private H3 composition (2026-10-11)

The owner E2E walkthrough reached an approved keyframe, but the persistent
server still hardcoded `video_provider=None` and `video_adapter=None`. Host
provider configuration and installed FFmpeg could not change that composition.
The fix belongs in the deployment owner, not the UI or generation contracts.

`manage.py start --h3-config <protected-file>` is an explicit retained opt-in.
Validate an owned, non-symlink, owner-only file before Docker/bridge changes;
retain only its path in ignored deployment state. A selected Compose override
mounts it as a read-only secret. Parse only provider fields without dotenv
interpolation or environment mutation; specialist subprocesses never receive
these values. Keep installation outputs/application paths authoritative and
require the existing trusted catalog, bearer credential and private gateway
root. Invalid configuration fails closed with a sanitized error. Default
composition ignores ambient enable flags and credentials.

An existing protected checkout `.env` is permitted as an operator-selected
server file outside service source and installation state; a dedicated private
file is preferred for narrower contents. Neither is copied into the image or
project payload. Mandatory gateway preflight remains at generation preparation
and submission, not deployment startup. `start --disable-h3` removes the opt-in
without deleting credentials, leases, approvals, media or job evidence. No
startup path dispatches or retries jobs. Native regression discovery now
covers default-off, private configuration, redaction, storage ownership,
persistence, disable and fail-before-Docker behavior.

### Owner-approved private tailnet access (2026-10-11)

The owner needs colleagues on the Tailscale network to use the same workbench.
Retain Docker's localhost-only publication and add a separate Tailscale Serve
HTTPS 8443 root proxy to `http://127.0.0.1:8841`; preserve the existing HTTPS
443 proxy to port 8000. Use background Serve, not public Funnel or a wildcard
Docker port. No backend restart, project migration or direct bridge-listener
publication is needed.
The exact host URL, verification and endpoint-scoped disable command live in
the [service operations guide](../../services/creator_workbench/README.md#private-colleague-access-over-tailscale).

Tailnet membership and policy are the intended trusted-operator boundary, not
a new multi-user authentication or role model. Every permitted colleague has
the current workbench's full project, settings and native generation authority.
The bridge's credential does not provide separate authorization for those
web users: its configured task allowlist is itself editable through the app.
This deployment is unsuitable for untrusted or read-only users without a
separately designed access layer. A future API text-provider activation also
requires credential-boundary review: editable provider destinations plus
server-key probes give co-admins authority over that key's destination.
The current shared composition has the API text pipeline disabled.

Changing Docker to a wildcard host publication would expose unrelated LAN
interfaces. Mounting Plotloom under the existing proxy's subpath would couple
its root-relative API/static routes to that service. A separate private HTTPS
port preserves both contracts. Qualification checks config preservation,
absence of Funnel, TLS, frontend/API reachability and loopback publication;
same-machine success does not prove another client's policy or connectivity.

### Wake-up boundary clarification (2026-10-01)

The later [ADR 0096](0096-native-specialist-deep-link-wake.md) qualifies the
documented external desktop-open path; the investigation below remains the
evidence at this earlier boundary, not a claim that desktop wake is impossible.

The bridge acknowledges queue admission, not specialist startup. The approved
wake-up follow-on requires native atomic admission and the specialist's existing
tool executor. A process-local `thread/read` status is not a concurrency guard;
do not substitute a standalone app-server execution surface merely because its
`thread/resume`/`thread/queue/start` schemas exist. Native writer exclusion and
busy-start rejection are useful guards, but do not establish desktop tool
execution or ownership transfer. Keep the current transport until that complete
path is verified. A lost acknowledgement still cannot authorize another queue
submission. See the [investigation receipt](../verification/2026-10-01-specialist-wake-up-gap.md).

## Alternatives and consequences

A container-only native CLI cannot run the Mac app's executable. Disabling image
handoff would break the creator's next step; proxying the whole backend would
leave the actual server outside Docker. Broad remote execution or a new queue
store is unnecessary. The small host bridge is the intentional Mac-specific
deployment boundary; product generation and admission contracts are unchanged.

The Docker runtime must run after login (OrbStack on the current host), and the
Mac must be awake. The browser
server can stay available while Codex is closed, but native tasks still require
the Codex app. Tests cover authentication, task binding and ambiguous transport;
restart/recreate checks must retain the existing accepted-art hash and prepared
image request. Never clear an inflight lease as part of deployment or restart.
