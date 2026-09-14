# ADR 0046: Production project-folder runtime composition

## Status

Accepted, 2026-09-14.

## Context

ADR 0040 deliberately introduced project-folder storage without wiring it into
the shipped runtime. `build_runtime_app` consequently continued to construct
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
Startup reconciles each known project conservatively and does not submit or
replay a run. The trusted H3 adapter is composed only when its frozen configured
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
