# ADR 0098 — Isolated workbench transport composition

Status: accepted for the bounded test-installation launcher, 2026-10-02.

## Problem and evidence

Two manually assembled launchers derived server storage, bridge allowlist and
outbound `codex` routing independently. One isolated image send reached the
normal installation's allowlist; a copied bridge in the next attempt still read
the first copy's settings. Both sends remain outcome unknown with their original
leases and receipts. Health checks and matching server folders did not exercise
the outbound dispatch path. The unattended roadmap retains those failed attempts.

## Decision

One isolated runtime owner derives storage, the exact specialist settings path,
both loopback ports, a private ephemeral shim, and its subprocess URL/credential
environment. The authoring composition accepts an explicit native executable
and environment applied to both text and image bindings, including future UI
rebindings. Transport configuration stays out of persisted specialist settings.
The existing direct/default transport remains available to normal compositions.

Bind both ports before serving. Reject foreign specialist dispatch roots,
symlinked installation application state, unavailable executables, and credentials
inside installation state or without owner-only permissions. Use an existing
external credential; never copy credentials into project data. A single context
owns socket, bridge thread and ephemeral shim cleanup on startup failure or exit.
The normal Docker workbench and LaunchAgent are separate owners and are untouched.

The isolated CLI installs a Python SIGTERM exit handler around the composition.
Uvicorn replays captured signals after shutting down its server; the native
default SIGTERM action would otherwise bypass the outer context's cleanup.
Python exit unwinds that context before termination and restores the prior
handler. Qualification includes a real CLI subprocess termination test, not
only calling a context manager's cleanup directly.

Qualification must exercise registry dispatch → actual shim subprocess → HTTP
authentication/allowlist → fake native executable, for both roles. A foreign
installation ID and health probe must produce zero native queue calls. Tests
also retain original settings/leases and prove owned-resource cleanup.

## Alternatives and consequences

Copied launcher scripts and search/replace configuration retain multiple path
authorities. Global environment/PATH mutation allows one composition to affect
another. In-process transport mocks cannot qualify the missing outbound wire.
Explicit per-dispatch subprocess configuration addresses this at composition
rather than changing generation field ownership or package contracts.

No automatic retry, lease release, historical assignment replay or new receipt
protocol is introduced. Typed prequeue refusal is an unresolved follow-up: safe
owner release would require trusted transport, strict attempt identity, a typed
prequeue exception/tombstone and a durable receipt before release. An HTTP 400
alone does not prove an old unknown attempt was never queued.
