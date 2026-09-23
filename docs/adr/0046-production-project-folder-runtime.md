# ADR 0046: Production project-folder runtime composition

## Status

Accepted, 2026-09-14.

## Context

[ADR 0040, project-folder storage boundary](0040-project-folder-storage-boundary.md)
deliberately introduced project-folder storage without wiring it into the
shipped runtime. `build_runtime_app` consequently continued to construct
the retained `SQLiteRepository`, shared artifact root, and shared image
exchange root. The direct factory proved individual project capabilities but
did not own application profile admission, run dispatch, or run-to-project
routing, so promoting it unchanged would drop supported authoring and text
workflow behavior.

## Decision

The production factory is the project-folder composition. `PLOTLOOM_OUTPUTS_DIR`
and `PLOTLOOM_APPLICATION_DATA_DIR` name its two separate roots; defaults are
anchored to the explicit application root. The old shared database, artifact,
exchange, and legacy-artifact-root configuration names are rejected before any
storage is opened.

`application.sqlite3` owns secret-free reusable text profiles, selected profile,
run-to-project index, and dispatch/accounting control. The index is rebuilt from
validated project manifests and their project-local run records at startup, then
all run-ID routes resolve one exact project. Project databases remain the only
authority for canonical content, drafts, runs, media, lifecycle, snapshots, and
recovery facts.

Text admission freezes the selected application profile into each new project
run. Server and browser-session keys stay process-local in `RunSecretBroker`.
Startup reads every discovered project to rebuild the disposable route index, but
reconciles only projects admitted OPEN; a CLOSED database is never rewritten at
startup. Every mutation-capable run route obtains an admitted OPEN project
handle before profile admission, route reservation, or provider work. Read-only
run inspection uses a separate inspection handle and cannot reopen a project.

The application index reserves a run route and frozen-profile reference before
the project database creates a run, then confirms the durable run status after
creation. That ordering means an index write failure cannot leave an unrouteable
canonical run, and the application-side profile deletion guard atomically
rejects deletion while any queued, running, cancel-requested, or pending frozen
run references the profile. Startup rebuilds both disposable route and frozen
profile reference records from project-local evidence.

RunContext uses the project-owned relative artifact adapter. Production run
bytes therefore live under the owning project and are addressed by confined
relative content-addressed paths; no production text dispatcher may emit an
absolute `file://` URI or rely on a relocation bridge. Snapshot inventory is
derived from typed project storage records and its ordinary integrity checks.
That typed inventory adds `v2_run_artifact_blobs`, so this runtime writes
project storage format 8. Older format-7 project folders are rejected at the
manifest boundary; there is intentionally no in-place migration in this
cutover.

The trusted H3 adapter is composed only when its frozen configured
backend identity is present; absent H3 configuration exposes an explicit
unavailable capability and never falls back to Atlas/Wan.

## Consequences

This is the breaking runtime cutover, not retained-data migration. Existing
project data and `.env` contents are untouched. Archiving old working sets,
exporting approved settings/accounting, and switching an operator's local
configuration remain separately controlled operational work recorded in the
storage roadmap and development entrypoint.

## Rejected alternatives

- Retain the shared repository behind a compatibility flag or dual-write path.
- Discover a run by searching every project database for each request.
- Persist browser-session keys, provider credentials, or H3 endpoint secrets in
  an application or project database.
- Treat inspection as permission to mutate a closed project, or rewrite closed
  run history during startup reconciliation.
- Rewrite old absolute artifact URIs while restoring a project. New-format
  storage rejects those paths instead.
