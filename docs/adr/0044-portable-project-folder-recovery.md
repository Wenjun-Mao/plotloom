# ADR 0044: Verified portable project-folder recovery

## Status

Accepted, 2026-09-14. This advances the direct, format-6 project-folder
composition from [ADR 0040, project-folder storage boundary](0040-project-folder-storage-boundary.md).
It does not cut over the retained runtime, import legacy folders, or change
provider/accounting ownership.

## Context

An ordinary folder copy cannot prove it captured a committed SQLite point, the
exact asset set referenced at that point, or a complete specialist exchange.
Conversely, an incoming folder is untrusted input: copying it broadly could
preserve path indirection, credentials, mutable operational debris, or a
corrupt project that becomes discoverable before validation completes.

## Decision

The direct composition creates a format-1 snapshot only while it owns the
project's exclusive local operation lease and no image/reference publication is
nonterminal. It uses SQLite's backup API, derives the retained files from the
backup database, and includes only `project.json`, `project.sqlite3`, referenced
immutable assets, complete terminal exchange evidence, and a generated
`recovery.json` control record. The control lists any captured nonterminal text
or media operation as known, unknown, or not submitted; it contains no
credentials and does not rewrite historical attempts. Snapshot input is an
exact tree: the declared regular files plus their required directories and
`snapshot.json`. Extra root, nested, hidden, linked, hard-linked, or special
entries are rejected deterministically.

A versioned `snapshot.json` records project and snapshot identity, database
hash, and the complete payload inventory. Validation rejects views, triggers,
unexpected indexes/tables, or an altered SQLite schema shape before any normal
project handle can execute against imported data. Owned asset paths come only
from their typed managed-asset storage columns, never by matching authored
story prose. The snapshot builds in a private directory, validates its schema,
foreign keys, hashes, recovery control, and exact inventory, then atomically
publishes below the application's `.snapshots/<project-id>/` root.

The browser may request a snapshot but cannot choose its path. Its own known
draft writers are drained before the request; unacknowledged edits in another
client are intentionally outside that boundary. Create/status responses return
the operation ID, complete manifest, and copyable local location.

`plotloom restore --source <snapshot-or-closed-folder> --outputs-dir <root>` is
the operator-only restore entrypoint. It accepts either a verified snapshot or
an explicitly closed format-6 folder. It validates before copying a declared
payload set into a private directory, preserves the stored project identity,
and atomically publishes only if no discovered project or destination already
uses that identity. Restore does not read application storage, browser state,
credentials, provider profiles, or remote systems; it never dispatches,
replays, reconciles, or changes historical job state. A snapshot's hashes
become a frozen source inventory. Every copied file is compared with that
inventory and the private destination is rehashed before publication, so
same-size source mutation cannot publish a substitute. A closed live-folder
restore holds that folder's existing exclusive operation lease through
validation and copying. It permits only its regular local lock, SQLite
sidecars, and empty managed roots as operational exclusions; a snapshot
permits none.

On restored open, `recovery.json` blocks startup reconciliation and both known
and unknown historic run IDs from explicit resume. The direct composition's
recovery-control acknowledgement can record operator acknowledgement without
submitting, reconciling, or relabelling an historic attempt as succeeded.
Acknowledgement does not make those stored IDs resumable; known-ID retrieval
and video/accounting reconciliation remain later work.

## Consequences

Snapshots may be taken while a project is open and retain that operational
state; a direct folder must be explicitly closed before restore. The mechanism
is a local recovery copy, not multi-host coordination, cloud sync, or an
off-machine backup. Restored drafts, lineage, selections, and owned media remain
readable while unfinished external work remains recovery-required.

## Rejected alternatives

- A generic recursive copy: it has no committed database boundary or exact
  inventory and can include mutable/unsafe entries.
- HTTP paths or browser-selected output destinations: they turn a local UI into
  arbitrary filesystem authority.
- Copying application storage, provider configuration, or dispatch leases:
  those are installation-scoped and can expose credentials or duplicate remote
  work/accounting semantics.
