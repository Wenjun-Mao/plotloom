# Project-folder close/quiescence receipt

## Outcome

The direct project-folder composition now has explicit Close and Open operations
separate from Archive. Format 6 persists operational admission state in each
project database. Shared project-local advisory leases protect normal handles;
Close takes the exclusive lease, refuses admitted siblings and nonterminal work
or unproven manual-publication ownership, checkpoints SQLite WAL, then releases
the handle. Delayed normal requests receive `project_closed` until explicit Open.

The workbench admits Close before any disposition or drain and holds that
project-scoped admission through the server response. It freezes editing,
saving, dispatch, and project/stage navigation for the requesting client. The
drain includes the current authoring draft and every known visual-intent or
image-direction writer, including a dirty writer retained across a shot or
target unmount. Each retained writer owns entity-keyed CAS, acknowledgement,
flight, timer, and conflict state; a newly mounted form cannot reset an older
writer's receipt. Queue changes during a drain, or a CAS/network failure, reject
Close without dropping its buffer. Close-time Discard persists the current
authoring draft, CAS-discards that exact receipt, and only then removes local
state. A durable receipt is deliberately not a canonical Save or Approval.
Reopen routes to editing rather than only changing backend state.

The retained runtime remains unchanged. No provider call, remote cancellation,
automatic replay, snapshot/restore, video dispatch/accounting change, old-data
mutation, or runtime cutover was performed. Offline fixtures establish this
evidence only.

## Checks

| Check | Result |
| --- | --- |
| `npm --prefix frontend test -- --run tests/visual-intent-drafts.test.ts tests/project-draft-quiescence.test.ts` | 19 passed; retains an acknowledged visual intent and image direction across a switch, then drains with their original CAS revision |
| `npm --prefix frontend run test:e2e -- --grep 'project-folder Close'` | 7 passed; exercises held admission, durable discard, close failure, visual and image-direction recovery, including acknowledged direction after switching away |
| `uv run pytest -q` | 678 passed, 9 skipped; 278 warnings |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend test` | 148 passed |
| `npm --prefix frontend run build` | passed; refreshed `src/plotloom/static/workbench.js` |
| `npm --prefix frontend run test:e2e` | 37 passed against the real FastAPI/file-SQLite factory and offline fixtures |
| `uv build --wheel` | built `plotloom-0.1.0-py3-none-any.whl` |
| `uv run python scripts/smoke_installed_wheel.py dist` | passed in an isolated temporary environment |

The Vite build retained its existing chunk-size warning. Python emitted existing
SQLite/Pydantic warnings; neither introduced a test failure.

The prior close-race review found unchecked WAL checkpoint results, unleased
discovery validation, bounded media-task busy detection, and the missing media
drain. The candidate checks checkpoint completion (reverting a newly attempted
close on failure), leases discovery validation, uses unbounded SQL existence
checks, and replaces independent media timers with the shared drain described
above. The focused browser checks use the real FastAPI/file-SQLite factory and
offline fixtures only; they make no live-provider claim.

The attended read-only Terra review found that a retained media writer was
reading the CAS state of the currently mounted shot/target. The candidate now
keeps that state per writer entity and has focused visual/image hook regressions
plus a browser journey that acknowledges an image direction, switches away,
closes, reopens after a backend restart, and recovers the direction. The review
found no other code-backed issue in the requested scope.

## Remaining scope

Snapshot/restore, video cutover/accounting, retained-runtime cutover, and old
data archive/migration remain outside this close slice.
