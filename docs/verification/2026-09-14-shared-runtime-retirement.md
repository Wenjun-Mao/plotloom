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

## Historical coverage correction

The original receipt's statement that no current production test was removed
was too broad. The retirement diff deleted or materially rewrote 301 baseline
test functions (including 25 parameterized cases). Some were truly
shared-facade-only, but retained behavior also lost direct proof when its shared
fixture disappeared. This follow-up preserves the facade removal and records
the exact disposition in
`docs/verification/2026-09-14-retained-runtime-coverage-inventory.json`:
255 migrated current contracts, 11 named existing equivalents, and 35 approved
breaking-storage retirements. The inventory is deterministic from `e658057`,
checks replacement test identifiers, and is guarded by
`tests/test_retained_runtime_coverage_inventory.py`.

## Caller disposition

| Former caller/surface | Disposition | Current owner or evidence |
| --- | --- | --- |
| `persistence/legacy_repository.py`, root `SQLiteRepository` | Removed | `ProjectSQLiteRepository` is opened only by `ProjectStore` with a manifest-bound project ID. |
| `api/application.py`, `api/{projects,generation,image_jobs,managed_media,video}.py`, `create_app` | Removed together | `build_runtime_app` composes only `create_project_folder_authoring_app`; production browser journeys and project-folder runtime tests use this surface. |
| `conformance.py` | Migrated | Read-only current application-profile snapshots plus disposable `ProjectFolderStorage` samples; the normal project generation owner creates run, trace, evidence, and secret-safe receipt. |
| `alpha_acceptance.py` | Migrated | The same application-profile snapshot and disposable project homes preserve the 18-cell matrix, blinded review pack, atomic publication, provenance, and private mapping boundary. |
| `media_jobs.py`, `tests/media_jobs` | Retired | No production caller existed. Project image publication is covered through `ProjectMediaRepository`; direct-video ownership, accounting, unknown-outcome/no-replay, and playback remain in current project-folder/runtime/browser coverage. |
| Shared API/repository backend tests | Split by contract | Route/facade-only tests are retired; retained generation, repair, profile, media, lifecycle, and repository behavior is mapped to named project/application-owner tests in the coverage inventory. |
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
- `scripts/retained_runtime_coverage_inventory.py --check` derives the exact
  affected baseline function set and rejects missing classifications or current
  replacement test identifiers.
- `tests/test_project_storage_generation_contracts.py` directly exercises the
  retained project-generation recovery, lineage, correction, redaction, and
  tamper contracts without a shared facade.
- `tests/test_project_storage_route_contracts.py` proves initial-stage
  bootstrap is atomic, reserves idempotency outside project content, returns a
  retryable response during same-key initialization, and converges after an
  expired initializer lease.

## Verification

- Current coverage-preservation suite: `uv run --locked pytest
  tests/test_retained_runtime_coverage_inventory.py
  tests/test_project_storage_route_contracts.py
  tests/test_project_storage_generation_contracts.py
  tests/test_project_storage_work_unit_contracts.py tests/test_project_storage.py
  tests/test_production_project_folder_runtime.py
  tests/test_shared_runtime_retirement.py tests/backend_core/test_jobs.py -q`
  — 45 passed; one existing Starlette/httpx deprecation warning.
- Current locked Python suite: `uv run --locked pytest -q` — 452 passed; one
  existing Starlette/httpx deprecation warning.
- Focused ownership and boundary suite: `uv run --locked pytest
  tests/test_alpha_acceptance.py tests/test_conformance.py
  tests/test_shared_runtime_retirement.py tests/backend_core/test_jobs.py -q`
  — 22 passed.
- Historical locked Python suite at the original retirement candidate:
  `uv run --locked pytest -q` — 436 passed; one existing Starlette/httpx
  deprecation warning. This result is retained as historical evidence, not as
  proof that every retained behavioral contract survived the test deletion.
- Current frontend gates: `npm --prefix frontend test` — 149 passed across 16 files;
  `npm --prefix frontend run typecheck` and `npm --prefix frontend run build`
  passed; generated assets were fresh (`git diff --exit-code --
  src/plotloom/static`). The build retained its pre-existing chunk-size warning.
- Current browser gate: `npm --prefix frontend run test:e2e` — 39 production journeys
  passed.
- Current distribution gate: `uv build --wheel --out-dir <temporary-directory>` and
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
