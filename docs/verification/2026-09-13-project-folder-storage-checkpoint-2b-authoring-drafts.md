# Project-folder storage checkpoint 2B: durable authoring drafts

## Scope and outcome

Baseline: `1a025c8466b3b7681a87c10778fd49788bf98557` on clean `main`.

Checkpoint 2B extends 2A's direct `ProjectSQLiteRepository`; it does not add a
temporary database, a result projection, or a runtime storage switch. New
format-4 project homes contain `v2_authoring_drafts`, keyed by project/editor
scope/entity ID. Each draft stores an allowlisted canonical Brief or one of the
four canonical stage payloads, its base canonical revision, draft CAS revision,
and update time. Credential-shaped values and non-canonical UI/session objects
are rejected.

`create_project_folder_authoring_app` is an explicit test-only composition.
It opens the one manifest-discovered project handle named by the route and
leaves the retained runtime's shared repository composition untouched. Its
draft PUT requires both current canonical and draft revisions. A stale tab
receives 409 and retains its losing local buffer. Canonical PATCH remains the
only canonical mutation and consumes only an exact acknowledged draft receipt;
a newer draft cannot be silently deleted.

The existing workbench, not a second UI, detects this test-only capability.
It autosaves after 750 ms idle and flushes on blur or project/stage navigation.
It reports Saving, Saved, Failed, and Conflict. Browser session storage holds
only unacknowledged safety data; a recovered server draft comes from
`project.sqlite3` and is offered for reconciliation.

## Focused evidence

- `uv run pytest tests/test_project_storage.py -q` — `10 passed`.
  This includes two-project isolation, direct four-stage payload allowlisting,
  draft CAS, exact canonical consumption, secret rejection, and reopening a
  file-backed project store after process reconstruction.
- `npm run typecheck` and `npm test -- --run` — passed (`130` frontend tests).
- `npx playwright test e2e/project-folder-authoring-drafts.spec.ts` — passed.
  The real FastAPI/file-SQLite journey proves autosave does not mutate canon,
  two-tab conflict keeps the losing input, explicit Save mutates canon and
  consumes the draft, and a restarted backend restores the durable draft.

## Deliberately deferred

This is not a retained-data cutover. The default runtime, provider/gateway
paths, profiles, keys, visual-intent/media-direction drafts, close/quiescence,
snapshot/restore, and live storage routing are unchanged. No provider calls,
gateway changes, `.env` changes, retained database/artifact mutation, or
deletion occurred.

The final locked-suite, build/static freshness, full browser gate, wheel smoke,
and attended independent review are recorded only after they complete.
