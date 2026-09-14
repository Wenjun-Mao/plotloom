# Persistence package extraction receipt

## Checkpoint

- **Baseline:** `8b6f444c35626316ccf84bfc5ca0d49ef64932c4`, with a clean
  worktree at start.
- **Observable outcome:** replace `src/plotloom/persistence.py` with an
  explicit package while retaining the public repository, mapped-row, schema,
  metadata, hash, migration, session, and contention contracts.
- **Owned scope:** persistence package, regression test, modularization plan,
  and this receipt. No frontend, provider, configuration, data, or migration
  file changed.
- **Stopping condition:** stable behavioral candidate with complete locked
  Python, unchanged-frontend, browser, Alembic, and installed-wheel evidence.

## Ownership result

`schema/` owns the base and cohesive authoring, generation, project-media, and
application-control mapped rows. `codec.py` owns canonical stored values and
`stable_hash`; `database.py` owns engine/session construction; and
`transactions.py` owns distinct read, ordinary-write, bootstrap-immediate,
lifecycle-immediate, and work-unit-claim-immediate leases. The public façade
exports the existing named types deliberately; it uses no wildcard forwarding.

`legacy_repository.py` remains a deliberately temporary retained-runtime
composition. Its remaining seams are authoring/lifecycle/gates/approvals,
generation/recovery/repair/commit, project-media facts, and application
profiles/settings/video-pilot accounting. Moving those operations is deferred
to capability-owned slices with caller migration and transaction evidence.

## Baseline versus candidate characterization

The baseline module was 10,120 lines and registered 44 metadata tables. The
candidate also registers 44 tables, and its project table selection remains the
same 35-name `PROJECT_TEXT_PIPELINE_TABLE_NAMES` subset. The regression test
freezes the baseline table names, public constructor parameter order for both
repository classes, `stable_hash` output, project table selection, and the five
named lease entry points.

The preserved import matrix is `plotloom`, `plotloom.persistence`,
`plotloom.project_storage`, `plotloom.api`, and `plotloom.runtime`; Alembic is
characterized through `SchemaMigrator.upgrade()` because importing `alembic/env.py`
outside Alembic deliberately has no configured context. Existing lifecycle and
work-unit tests exercise distinct repository instances and retain their
contention translations for lifecycle and claim leases.

## Verification

| Command | Result |
| --- | --- |
| `uv run pytest -q tests/test_project_storage.py tests/test_project_storage_image_workflow.py tests/backend_core/test_api_modularization_contract.py tests/backend_core/test_project_lifecycle.py tests/backend_core/test_work_unit_persistence.py` | 66 passed |
| `uv run pytest -q tests/backend_core/test_persistence_modularization_contract.py` | 2 passed |
| `uv run --locked pytest -q` | 667 passed, 9 skipped |
| `cd frontend && npm run typecheck && npm test && npm run build` | typecheck passed; 132 unit tests passed; build passed |
| `git diff --quiet -- src/plotloom/static` | passed after the frontend build; generated static assets unchanged |
| `cd frontend && npm run test:e2e` | 30 passed |
| isolated `SchemaMigrator(...).upgrade()` | passed against a fresh SQLite database |
| `uv build --wheel --out-dir <temporary directory>` plus `uv run --locked python scripts/smoke_installed_wheel.py <temporary directory>` | passed; installed wheel performed Alembic upgrade; SHA-256 `9731752c5d6d9ce5b2c0da1b404967f7882665c5531acdff688ae4efa3ef0931` |

Expected existing warnings remained: SQLAlchemy's Python 3.12 SQLite datetime
adapter deprecation, selected Pydantic serializer warnings for historical
fixtures, the TestClient deprecation, and Vite's pre-existing large-chunk
advisory. No new runtime failure is accepted by this receipt.

## Independent review

A read-only Terra review compared the candidate to `8b6f444`. It confirmed all
45 ORM class ASTs, 44 metadata tables, the focused repository/lifecycle/claim
tests, and Alembic compatibility. It found one P1 public-surface omission:
`PROJECT_TEXT_PIPELINE_TABLE_NAMES` was baseline-public but initially only
available from `persistence.schema`. The façade now deliberately re-exports it,
and the regression test imports it from `plotloom.persistence`; the post-review
focused contract/lifecycle/work-unit run passed 56 tests. The corrected stable
candidate then repeated the locked Python suite (667 passed, 9 skipped),
frontend typecheck/unit/build/static check (132 passed), browser suite (30
passed), fresh Alembic upgrade, and installed-wheel smoke. Its wheel SHA-256 is
`80758212df92f91f05e56c1be203d2c72730d87016c6114e9f334651c299113b`.

## Remaining work

This is not persistence completion or a project-folder runtime cutover. The
next owner must take one named capability seam, migrate its exact callers, and
delete the corresponding legacy implementation only after focused regression
and transaction evidence. Frontend modularization remains a separate pending
phase.
