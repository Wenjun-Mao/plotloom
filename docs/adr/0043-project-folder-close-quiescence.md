# ADR 0043: Explicit project-folder close and quiescence

## Status

Accepted, 2026-09-14. This is a bounded continuation of ADR 0040's unwired
project-folder composition; it is not retained-runtime cutover, snapshot, or
restore delivery.

## Context

`ProjectStore.close()` only disposed the request's SQLite engine. A later
request could rediscover the manifest and open another handle, while an active
sibling could still publish a manual image package outside SQLite. Therefore a
successful handle disposal did not establish a folder safe to copy.

## Decision

Format 6 adds one project-owned operational-state row (`open` or `closed`) to
`project.sqlite3`, distinct from the author-controlled Archive lifecycle and
its revision. The row is the durable admission authority; it does not duplicate
canonical content or lifecycle state.

All direct-composition registry handles hold a shared advisory lease on the
project-local operation lock. Explicit Close obtains the exclusive lease,
refuses nonterminal text/media work and any image or reference package whose
external publication ownership cannot prove terminal, writes `closed`, WAL
checkpoints, disposes SQLite, and releases the lease. The close does not cancel
remote work, force a stale lock away, replay a job, or infer external-idle state.
Explicit Open also takes the exclusive lease and changes only admission state;
it never dispatches or replays work. Ordinary registry opens reject a closed
project, so delayed requests cannot silently reopen it.

The direct workbench owns one project-scoped draft-quiescence contract. It admits
Close before any disposition or drain and holds that admission through the Close
response. The requesting client freezes edits, save/dispatch actions, and route
changes for that project during the interval; media hooks also refuse a late
programmatic update. Close drains the current authoring draft and every known
visual-intent or image-direction queue, including a dirty queue retained after
its form unmounts on shot/target navigation. A CAS/network failure retains the
durable or local buffer and leaves the project open. A visible Close-time
Discard first obtains the exact current draft receipt, CAS-discards that one
scope, and only then removes its local record; it cannot erase another scope.
Clearing a server-backed image direction similarly remains dirty until its exact
discard receipt succeeds. A retained media writer keeps its own entity-keyed
CAS revision, acknowledgement, save flight, timer, and conflict state; mounting
another shot or target cannot reset the receipt needed to drain the old writer.
A durable draft receipt does not canonically save or approve author content.
Explicit Open closes the directory view and routes to the reopened project; it
never replays a job.

## Consequences

The direct storage factory exposes close/open only through its capability flag;
the retained runtime does not show a control it cannot honor. A filesystem
advisory lease coordinates local
processes and external publication paths, but is not a claim of safety across
hosts or unsupported filesystems.

Failed Close restores the requesting client's editability and preserves the
same route and canonical projection. The close admission is client-local and
supplements, rather than replaces, the project-folder operational-state row and
cross-process lease.

## Rejected alternatives

- Reuse Archive: it changes author lifecycle rather than local copy admission.
- Treat per-request engine disposal as close: delayed requests reopen immediately.
- Use a process-local flag: independent local processes can still race writes.
- Automatically cancel/replay or remove stale locks: neither proves remote or
  specialist work stopped.
