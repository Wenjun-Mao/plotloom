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
only canonical mutation and, in the same SQLite transaction, consumes only a
receipt whose scope/entity/revision, base canonical revision, and normalized
payload match the requested canonical content; a newer or different draft
cannot be silently deleted.

The existing workbench, not a second UI, detects this test-only capability.
It autosaves after 750 ms idle and flushes on blur or project/stage navigation.
It reports Saving, Saved, Failed, and Conflict. Browser session storage holds
only unacknowledged safety data; a recovered server draft comes from
`project.sqlite3` and is offered for reconciliation. The first edit after a
server recovery seeds its CAS from that durable receipt, and typing during an
in-flight save queues a later save rather than remaining only in the session.

## Focused evidence

- `uv run pytest tests/test_project_storage.py -q` — `10 passed`.
  This includes two-project isolation, direct four-stage payload allowlisting,
  draft CAS, exact canonical consumption, secret rejection, and reopening a
  file-backed project store after process reconstruction.
- `npm run typecheck` and `npm test -- --run` — passed (`130` frontend tests).
- `npx playwright test e2e/project-folder-authoring-drafts.spec.ts` — passed.
  The real FastAPI/file-SQLite journey proves autosave does not mutate canon,
  two-tab conflict keeps the losing input, a held in-flight autosave retries
  newer typing, explicit Save mutates canon and consumes the matching draft,
  and a restarted backend restores an editable durable draft.

## Full verification

- `uv run --locked pytest -q` — `663 passed, 9 skipped` in 71.78 seconds.
  The retained TestClient, SQLite datetime-adapter, and existing Pydantic
  serialization warnings remain visible (278 total warnings).
- `npm run typecheck`, `npm test -- --run`, and `npm run build` — passed.
  The production build regenerated `src/plotloom/static/workbench.js` from the
  current frontend source; the expected existing bundle-size warning remains.
- `npm run test:e2e` — `29 passed`, including the project-folder browser
  journey and its E2E TypeScript check.
- `uv build --wheel --out-dir /tmp/plotloom-project-storage-wheel-Df0hsU` and
  `uv run --locked python scripts/smoke_installed_wheel.py
  /tmp/plotloom-project-storage-wheel-Df0hsU` — passed. The wheel SHA-256 is
  `8780f63dee7a1397c1faaa98f47e23d72d9bc46fe1da5779c939f1270bca6bd4`.

## Independent review

The attended read-only Terra review of `ac340c1` found three P1s: server-only
recovery seeded its next local CAS at zero, typing during an in-flight save was
not queued, and canonical consumption did not prove the receipt's payload/base
matched the requested canonical mutation. The scoped remediation adds those
three contracts and their focused regression coverage. The same reviewer then
rechecked only those findings against this candidate, ran
`uv run pytest tests/test_project_storage.py -q` (`10 passed`), and approved
the result with no remaining P1/P2 findings.

## Deliberately deferred

This is not a retained-data cutover. The default runtime, provider/gateway
paths, profiles, keys, visual-intent/media-direction drafts, close/quiescence,
snapshot/restore, and live storage routing are unchanged. No provider calls,
gateway changes, `.env` changes, retained database/artifact mutation, or
deletion occurred.

No retained-data cutover is implied by this evidence.
