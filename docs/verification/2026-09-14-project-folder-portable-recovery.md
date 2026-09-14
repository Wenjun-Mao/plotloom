# Project-folder portable-recovery receipt

## Outcome

The direct format-6 composition now creates a self-contained, hash-verified
format-1 snapshot while a project is open. Capture holds the project-exclusive
operation lease, rejects nonterminal image/reference publication, backs up
SQLite at a committed point, and retains only the database-derived immutable
payload: project manifest, database, referenced content-addressed assets,
complete terminal exchange evidence, and a secret-free recovery control for any
unfinished text/media operation. Snapshot input is an exact tree: declared
regular bytes plus only their needed directories and `snapshot.json`; extra
root/nested/hidden files, links, hard links, and special entries are rejected.
Typed managed-asset URI columns—not authored prose—define retained bytes.

Validation rejects views, triggers, unexpected SQLite objects, and altered
schema shapes before any normal project handle can see imported data. Restore
freezes the input hash inventory, compares every copied byte, and rehashes its
private destination before atomic publication; same-size source mutation cannot
substitute data. A closed-folder restore holds the existing exclusive local
lease through validation and copying. It admits only its named local lock,
SQLite sidecars, and empty managed roots as source exclusions; snapshots admit
none.

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
Restored known/unknown unfinished operation IDs are recovery-required: startup
reconciliation and explicit resume remain blocked while historical attempts are
preserved. Acknowledgement cannot replay, reconcile, or label them succeeded.

## Checks

| Check | Result |
| --- | --- |
| `uv run --locked pytest -q` | 697 passed, 9 skipped; 278 warnings |
| focused recovery/storage/API-contract tests | 34 passed; covers exact tree inventory, links/special entries, same-size source mutation, closed-folder lease contention, hostile SQLite views/triggers/schema shape, prose asset lookalikes, known/unknown restored work, private-root confinement, corrupt bytes, interruption cleanup, identity conflicts, and CLI restore |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend test` | 149 passed |
| `npm --prefix frontend run build` | passed; static assets were already fresh (existing Vite chunk-size warning) |
| `npm --prefix frontend run test:e2e` | 38 passed against real FastAPI/file-SQLite fixtures; includes open snapshot → original loss → isolated restore → draft/reviewed-media recovery |
| `uv build --wheel` | built `plotloom-0.1.0-py3-none-any.whl` |
| `uv run python scripts/smoke_installed_wheel.py dist` | passed in a temporary isolated installation |
| installed wheel `plotloom restore --help` | passed in a fresh temporary environment; confirms the operator command is packaged without runtime configuration |
| independent Terra safety review | attended, read-only, no findings; reviewed exact inventory/hash/source race/schema/recovery and confinement paths |

The browser journey waits for the reviewed-keyframe mutation and its local
refresh to settle before capture; otherwise the snapshot barrier correctly
returns retryable `project_busy` instead of copying alongside an active local
writer. The optional `ruff` executable is not installed in the locked runtime;
the full Python, frontend, browser, wheel, and installed-CLI gates above passed.

## Remaining scope

The retained runtime, legacy import/migration, application accounting/profile
portability, video recovery, remote reconciliation, cloud sync, and live
provider execution remain out of scope. A local snapshot is recovery material,
not an off-device backup.
