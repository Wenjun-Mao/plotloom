# ADR 0040: Project-folder storage boundary

## Status

Accepted, 2026-09-13. Checkpoint 1 construction is implemented but deliberately
not wired into the retained runtime or pilot data.

## Context

The retained runtime uses one `SQLiteRepository` for canonical project content,
provider profiles, installation preferences, and paid-provider accounting. Its
artifact and exchange roots also live beside that shared database. A copied
project therefore cannot recover its complete state independently, and a future
runtime could too easily make a project record depend on installation-specific
configuration or credentials.

The approved storage plan requires one authoritative database and owned bytes
per project directory, with provider-profile selection and global accounting
remaining installation-owned. This first checkpoint must prove that boundary
without mutating retained pilot data or adding a selectable legacy/new runtime.

## Decision

Introduce an unwired construction seam in `plotloom.project_storage`:

- `ProjectDirectoryRegistry` creates exclusively allocated UTC-and-UUID project
  homes below an explicit outputs root. It discovers live projects only through
  validated immutable `project.json` manifests; hidden operational directories
  are not projects.
- Each `ProjectStore` owns one `project.sqlite3` and immutable
  content-addressed files under `assets/<hash-prefix>/<hash>`. Stored artifact
  references are confined relative paths and are hash-verified on read. The
  initial vertical slice persists project creation, optimistic brief editing,
  and an offline deterministic-provider result. It has no credential, queue,
  HTTP, gateway, or provider-accounting path.
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
are prohibited from it. The project database records no provider profile or
accounting state in this checkpoint.

## Consequences

The construction seam demonstrates two independently reopenable project homes
without the former shared project database. It also gives later routing work an
ownership-safe target rather than a second runtime mode.

Checkpoint 2 starts by replacing the construction-only fake run with an
isolated execution of the existing four-stage text pipeline. Its project schema
owns canonical revisions and heads plus the complete secret-free run evidence:
run snapshots, plans, work units, attempts, artifacts, seals, and exact repair
scope/reuse lineage. A complete child run is installed in one project-database
transaction only after every canonical stage is sealed. A stale project revision,
failed/quarantined run, incomplete seal set, or mismatched project/run identity
therefore cannot partially install canonical output. The application-owned
selected public text profile (including adapter identity/version where supplied)
is frozen verbatim in each actual run; credentials are resolved only by the
ephemeral secret broker and are never projected into either store.

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
- Put profiles, credentials, or accounting reservations in `project.json`: a
  copied project would leak secrets or duplicate installation-global state.

## Verification

See the [checkpoint 1 receipt](../verification/2026-09-13-project-folder-storage-checkpoint-1.md).
