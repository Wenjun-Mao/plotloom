# ADR 0040: Project-folder storage boundary

## Status

Accepted, 2026-09-13. Checkpoint 2A replaces the rejected `460ff56`
construction result with a direct project-owned text-generation repository. It
remains deliberately unwired from the retained runtime and pilot data; this is
not a storage cutover or migration.

## Context

The retained runtime uses one `SQLiteRepository` for canonical project content,
provider profiles, installation preferences, and paid-provider accounting. Its
artifact and exchange roots also live beside that shared database. A copied
project therefore cannot recover its complete state independently, and a future
runtime could too easily make a project record depend on installation-specific
configuration or credentials.

The approved storage plan requires one authoritative database and owned bytes
per project directory, with provider-profile selection and global accounting
remaining installation-owned. The original 2A attempt ran `PipelineEngine` in
a temporary mixed `SQLiteRepository`, rewrote its allocated project ID, and
copied only a successful result into a second project schema. That made the
temporary database—not `project.sqlite3`—the lifecycle authority. Failed,
cancelled, quarantined, crash-interrupted, and outcome-unknown evidence could
therefore disappear at the projection boundary.

## Decision

Introduce an unwired composition seam in `plotloom.project_storage`:

- `ProjectDirectoryRegistry` creates exclusively allocated UTC-and-UUID project
  homes below an explicit outputs root. It discovers live projects only through
  validated immutable `project.json` manifests; hidden operational directories
  are not projects.
- Each `ProjectStore` owns one `project.sqlite3` and immutable
  content-addressed files under `assets/<hash-prefix>/<hash>`. Its bound
  `ProjectSQLiteRepository` uses the existing canonical `PipelineEngine` and
  `LifecycleJobRunner` directly. Admission, plans, work units, attempts,
  response/candidate artifacts, seals, repair scopes, bindings, canonical
  heads, and every terminal disposition are written to this database as they
  occur. Stored artifact references are confined relative paths and
  hash-verified on read.
- The project schema is a named canonical-text subset, not a clone of the
  mixed application repository. It contains canonical/review-gate state and
  text-run/recovery/repair tables (plus the project-local media-task rows read
  by conservative startup recovery). It excludes provider settings/profiles,
  profile selection, global ledger tables, and unrelated image/video/review
  surfaces until their project-owned ports are separately delivered.
- `ApplicationStore` owns only reusable public provider profiles, their selected
  preference, and global accounting reservations in a separately located
  `application.sqlite3`. It rejects credential-shaped configuration. It has no
  project content table or project database reference.
- `ProjectFolderStorage` is the explicit composition root requiring separate
  outputs and application roots. This format has no old/new selection flag and
  does not modify `PlotloomSettings`, `build_runtime_app`, or the current shared
  `SQLiteRepository` callers.

The manifest contains only storage format version, immutable project ID,
creation time, and the fixed relative database location. Mutable title, status,
canonical content, provider configuration, credentials, and absolute file paths
are prohibited from it. The project database records only the selected public
profile snapshot frozen on each run, never mutable profile selection,
credentials, or accounting state. A process-local profile admission scope and
`RunSecretBroker` support both bearer and none authentication modes; raw
artifact persistence rejects recognizable secret-shaped values after adapter
redaction.

## Consequences

Two independently reopenable project homes can run the actual deterministic
four-stage fixture without the former shared project database. A successful
run still commits its complete canonical stage range atomically from sealed
aggregates. Unlike the rejected result, a failed, cancelled, quarantined, or
outcome-unknown run is retained in the same project home without partial
canonical heads. Exact repair reopens the quarantined parent directly from
project-owned scope, binding, and artifact evidence; stale scope/hash/artifact
checks fail closed and no automatic repair/replay occurs.

The remainder of checkpoint 2 must route the complete existing project workflow
(authoring, image/video handoff, reviews, lifecycle, drafts, close, and all
delayed-work lookups) through project handles and coordinate globally unique
accounting reservations without placing credentials in either database. It must
not route a production operation through the old narrow fake-provider helper.

Checkpoint 3 remains responsible for snapshot, restore, integrity and failure
recovery. Checkpoint 4 alone may archive the retained data and perform
the breaking runtime cutover after writer quiescence and verified inventory.

## Rejected alternatives

- Add a legacy/new storage switch or dual writes: this would ship an unsupported
  compatibility runtime and obscure cutover ownership.
- Reuse the old shared repository once per project: it would keep application
  profiles and accounting schema in project folders, contradicting the intended
  ownership boundary.
- Execute in a disposable mixed repository and project a success afterward:
  it loses terminal/crash evidence and requires identity rebinding, so it
  cannot be the durable lifecycle authority.
- Put profiles, credentials, or accounting reservations in `project.json`: a
  copied project would leak secrets or duplicate installation-global state.

## Verification

See the [direct 2A receipt](../verification/2026-09-13-project-folder-storage-checkpoint-2a-direct.md)
and the historical [checkpoint 1 receipt](../verification/2026-09-13-project-folder-storage-checkpoint-1.md).
