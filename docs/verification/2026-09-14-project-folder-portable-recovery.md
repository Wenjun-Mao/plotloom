# Project-folder portable-recovery receipt

## Outcome

The direct format-6 composition now creates a self-contained, hash-verified
format-1 snapshot while a project is open. Capture holds the project-exclusive
operation lease, rejects nonterminal image/reference publication, backs up
SQLite at a committed point, and retains only the database-derived immutable
payload: project manifest, database, referenced content-addressed assets, and
complete terminal exchange evidence. It excludes links, locks, sidecars,
partials, nested snapshots, external file dependencies, credentials, application
data, and mutable broad-tree copies. A completed manifest hashes the exact
inventory; private staging and atomic publish ensure failure never advertises a
completed snapshot.

The direct workbench offers creation progress and the completed local location.
It drains known current-client draft writers before capture; an unacknowledged
edit in another client remains explicitly outside that promise. Its API has
project-scoped create/status operations and never accepts a browser filesystem
path.

The operator entrypoint is:

```sh
plotloom restore --source /absolute/path/to/snapshot-or-closed-project --outputs-dir /absolute/path/to/outputs
```

It accepts only a verified new-format snapshot or explicitly closed format-6
folder. It validates before a private, atomic destination publish, preserves
IDs, refuses identity/destination conflicts, and performs no provider lookup,
replay, account mutation, application-database read, or credential import.

## Checks

| Check | Result |
| --- | --- |
| `uv run --locked pytest -q` | 685 passed, 9 skipped; 278 pre-existing warnings |
| focused recovery/storage/API-contract tests | 23 passed; covers corrupt database/assets, missing referenced bytes, interruption cleanup, writer refusal, direct-folder state, identity conflicts, and CLI restore |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend test` | 149 passed |
| `npm --prefix frontend run build` | passed; refreshed `src/plotloom/static/workbench.js` (existing Vite chunk-size warning) |
| `npm --prefix frontend run test:e2e` | 38 passed against real FastAPI/file-SQLite fixtures; includes open snapshot → original loss → isolated restore → draft/reviewed-media recovery |
| `uv build --wheel` | built `plotloom-0.1.0-py3-none-any.whl` |
| `uv run python scripts/smoke_installed_wheel.py dist` | passed in a temporary isolated installation |
| installed wheel `plotloom restore --help` | passed; confirms the operator command is packaged without runtime configuration |

The final independent, read-only Terra safety review is recorded with the
delivery after it completes. The browser journey waits for the reviewed-keyframe
mutation and its local refresh to settle before capture; otherwise the snapshot
barrier correctly returns retryable `project_busy` instead of copying alongside
an active local writer.

## Remaining scope

The retained runtime, legacy import/migration, application accounting/profile
portability, video recovery, remote reconciliation, cloud sync, and live
provider execution remain out of scope. A local snapshot is recovery material,
not an off-device backup.
