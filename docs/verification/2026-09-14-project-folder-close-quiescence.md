# Project-folder close/quiescence receipt

## Outcome

The direct project-folder composition now has explicit Close and Open operations
separate from Archive. Format 6 persists operational admission state in each
project database. Shared project-local advisory leases protect normal handles;
Close takes the exclusive lease, refuses admitted siblings and nonterminal work
or unproven manual-publication ownership, checkpoints SQLite WAL, then releases
the handle. Delayed normal requests receive `project_closed` until explicit Open.

The workbench now drains one project-scoped queue before Close: the current
authoring draft plus all mounted visual-intent and image-direction writers.
Each writer owns its timer and CAS flight; queue changes during a drain, or a
CAS/network failure, reject Close without dropping its session buffer. A
durable receipt is deliberately not a canonical Save or Approval. Reopen
routes to editing rather than only changing backend state.

The retained runtime remains unchanged. No provider call, remote cancellation,
automatic replay, snapshot/restore, video dispatch/accounting change, old-data
mutation, or runtime cutover was performed. Offline fixtures establish this
evidence only.

## Checks

| Check | Result |
| --- | --- |
| `uv run pytest tests/test_project_storage.py tests/test_project_storage_image_workflow.py -q` | 14 passed |
| `npm --prefix frontend test -- --run tests/visual-intent-drafts.test.ts tests/project-draft-quiescence.test.ts tests/workspace-owner-contracts.test.ts` | 14 passed |
| `uv run pytest -q` | passed (existing warnings/skips retained) |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend test -- --run` | 142 passed |
| `npm --prefix frontend run build` | passed; refreshed `src/plotloom/static/workbench.js` |
| `npm --prefix frontend run test:e2e` | passed |
| `uv build && uv run python scripts/smoke_installed_wheel.py` | passed |

The Vite build retained its existing chunk-size warning. Python emitted existing
SQLite/Pydantic warnings; neither introduced a test failure.

The prior close-race review found unchecked WAL checkpoint results, unleased
discovery validation, bounded media-task busy detection, and the missing media
drain. The candidate checks checkpoint completion (reverting a newly attempted
close on failure), leases discovery validation, uses unbounded SQL existence
checks, and replaces independent media timers with the shared drain described
above. The focused browser checks use the real FastAPI/file-SQLite factory and
offline fixtures only; they make no live-provider claim.

The attended read-only Terra review then found a concrete authoring race: Close
could join an older in-flight authoring save while a newer local revision waited
behind it. The authoring saver now drains through the newest local revision and
is registered in the same project contract as media. The review also found that
a dirty visual draft with empty provenance could falsely report success; that
state now blocks Close. Browser regression evidence holds the first authoring
PUT, types a newer value, then proves Close waits for the final receipt; the
media counterpart holds a visual-intent PUT. Storage fixtures also prove an
independent process lease, a nonterminal-run refusal, and a copied closed
directory reopening only after explicit Open.

## Remaining scope

Snapshot/restore, video cutover/accounting, retained-runtime cutover, and old
data archive/migration remain outside this close slice.
