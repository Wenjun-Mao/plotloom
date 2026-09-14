# Project-folder close/quiescence receipt

## Outcome

The direct project-folder composition now has explicit Close and Open operations
separate from Archive. Format 6 persists operational admission state in each
project database. Shared project-local advisory leases protect normal handles;
Close takes the exclusive lease, refuses admitted siblings and nonterminal work
or unproven manual-publication ownership, checkpoints SQLite WAL, then releases
the handle. Delayed normal requests receive `project_closed` until explicit Open.

The retained runtime remains unchanged. No provider call, remote cancellation,
automatic replay, snapshot/restore, video dispatch/accounting change, old-data
mutation, or runtime cutover was performed. Offline fixtures establish this
evidence only.

## Checks

| Check | Result |
| --- | --- |
| `uv run pytest tests/test_project_storage.py tests/test_project_storage_image_workflow.py -q` | 13 passed |
| Targeted API/frontend/persistence characterization plus storage tests | 24 passed |
| `uv run pytest -q` | 676 passed, 9 skipped (existing warnings) |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend test -- --run` | 139 passed |
| `npm --prefix frontend run build` | passed; refreshed `src/plotloom/static/workbench.js` |
| `npm --prefix frontend run test:e2e` | 30 passed |
| `uv build && uv run python scripts/smoke_installed_wheel.py` | passed |

The Vite build retained its existing chunk-size warning. Python emitted existing
SQLite/Pydantic warnings; neither introduced a test failure.

An independent read-only close-race review found unchecked WAL checkpoint
results, unleased discovery validation, and bounded media-task busy detection.
The candidate now checks checkpoint completion (reverting a newly attempted
close on failure), leases discovery validation, and uses unbounded SQL
existence checks for nonterminal runs/media tasks. Media-draft close flushing
remains an explicit follow-up gap: the current direct workbench's independent
media-draft timers require a dedicated shared flush coordinator before its Close
control can claim that guarantee.

## Remaining scope

Snapshot/restore, video cutover/accounting, retained-runtime cutover, and old
data archive/migration remain outside this close slice.
