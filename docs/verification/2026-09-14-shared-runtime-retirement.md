# Shared-runtime retirement receipt

Captured 2026-09-14 from accepted main `e658057`.

## Scope and root cause

The production browser parity receipt's one-time caller inventory identified an
already-unreachable shared runtime: its `SQLiteRepository` facade still
composed project and application state, while its old FastAPI factory/routes,
root aliases, qualification tools, and generic media worker still exposed or
called it. Production `build_runtime_app` had already proved the correct owner:
one project folder per project plus a separate application control store.

ADR 0048 removes the second composition rather than adding a compatibility
layer. There is no source retained-project importer, selectable storage mode,
or `.env`/retained-data cutover in this change.

## Caller disposition

| Former caller/surface | Disposition | Current owner or evidence |
| --- | --- | --- |
| `persistence/legacy_repository.py`, root `SQLiteRepository` | Removed | `ProjectSQLiteRepository` is opened only by `ProjectStore` with a manifest-bound project ID. |
| `api/application.py`, `api/{projects,generation,image_jobs,managed_media,video}.py`, `create_app` | Removed together | `build_runtime_app` composes only `create_project_folder_authoring_app`; production browser journeys and project-folder runtime tests use this surface. |
| `conformance.py` | Migrated | Read-only current application-profile snapshots plus disposable `ProjectFolderStorage` samples; the normal project generation owner creates run, trace, evidence, and secret-safe receipt. |
| `alpha_acceptance.py` | Migrated | The same application-profile snapshot and disposable project homes preserve the 18-cell matrix, blinded review pack, atomic publication, provenance, and private mapping boundary. |
| `media_jobs.py`, `tests/media_jobs` | Retired | No production caller existed. Project image publication is covered through `ProjectMediaRepository`; direct-video ownership, accounting, unknown-outcome/no-replay, and playback remain in current project-folder/runtime/browser coverage. |
| Shared API/repository backend tests | Retired as obsolete-mode tests | They exercised the removed shared route/facade rather than a current project-folder owner. Current runtime/recovery/media/video/browser and generation contract tests remain; no current production test was removed to mask a failure. |
| Legacy Alembic/shared-store migration tests | Retired as historical serialization tests | The authorized breaking cutover has no retained database importer. Historical documents stay immutable; current format/recovery tests validate supported project-folder serialization. |

## Regression guards

- `tests/test_shared_runtime_retirement.py` asserts all retired modules and
  public aliases are absent.
- `scripts/smoke_installed_wheel.py` rejects retired files in the wheel and
  installs under an import blocker during production startup and snapshot
  recovery.
- The qualification/Alpha tests assert read-only profile loading, explicit
  application/project ownership, cleanup of temporary evidence, and secret-free
  receipts/review material.

## Verification

- Focused ownership and boundary suite: `uv run --locked pytest
  tests/test_alpha_acceptance.py tests/test_conformance.py
  tests/test_shared_runtime_retirement.py tests/backend_core/test_jobs.py -q`
  — 22 passed.
- Locked Python suite: `uv run --locked pytest -q` — 436 passed; one existing
  Starlette/httpx deprecation warning.
- Frontend gates: `npm --prefix frontend test` — 149 passed across 16 files;
  `npm --prefix frontend run typecheck` and `npm --prefix frontend run build`
  passed; generated assets were fresh (`git diff --exit-code --
  src/plotloom/static`). The build retained its pre-existing chunk-size warning.
- Browser gate: `npm --prefix frontend run test:e2e` — 39 production journeys
  passed.
- Distribution gate: `uv build --wheel --out-dir <temporary-directory>` and
  `uv run --locked python scripts/smoke_installed_wheel.py
  <temporary-directory>` passed. The isolated installed-wheel probe runs
  `plotloom restore --help`, migrates a fresh project schema, exercises
  startup/snapshot recovery, and rejects every retired module.
- CLI contract: `scripts/conformance.py --help` and
  `scripts/alpha_acceptance.py --help` expose no shared-database option.
- Independent read-only review found the Alpha external-review boundary had
  lost focused tests for malformed/prose-bearing sheets, strict score types,
  frozen identity, quality thresholds, partial manifests, receipt filtering,
  and private-map completeness. The boundary implementation was already
  correct; regression tests now cover those contracts and are included in the
  focused and full Python results above.
