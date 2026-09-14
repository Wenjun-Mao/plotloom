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

## Consequences

The direct storage factory exposes close/open only through its capability flag;
the retained runtime does not show a control it cannot honor. Browser draft
flush remains client-owned and CAS-protected before the command; a failed flush
keeps the buffer and folder open. A filesystem advisory lease coordinates local
processes and external publication paths, but is not a claim of safety across
hosts or unsupported filesystems.

## Rejected alternatives

- Reuse Archive: it changes author lifecycle rather than local copy admission.
- Treat per-request engine disposal as close: delayed requests reopen immediately.
- Use a process-local flag: independent local processes can still race writes.
- Automatically cancel/replay or remove stale locks: neither proves remote or
  specialist work stopped.
