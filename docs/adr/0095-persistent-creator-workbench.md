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

Native Codex queueing must remain on macOS. A separate login-started launchd
bridge runs only the existing `codex queue` command, authenticated with a local
token, and permits only the configured specialist task IDs. A container CLI shim
keeps the existing dispatcher and its reservations authoritative. Neither bridge
nor shim retries; lost acknowledgement still means outcome unknown. Credentials
remain outside project/application state and image layers. Health checks do not
queue tasks. This applies equally to text and image specialists.

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
