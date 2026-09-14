# Project-folder video/accounting receipt

## Outcome

The direct format-7 project-folder composition supports the frozen MiniMax H3
lifecycle through its existing typed provider and adapter contracts: prepare,
submit, reconcile/download, review/select, cancellation, status, and byte-range
playback. A configured transport is required for network work; there is no
Atlas/Wan fallback. The browser-facing direct-folder workflow now exposes the
video panel independently of retained-runtime media-draft capability flags.

Project SQLite owns H3 request evidence, job/provider identity, review and
selection, and the content-addressed local video output. The separate
application database owns immutable dispatch identities, reservations, and
append-only event history. Dispatch reserves first, persists the local claim
before network admission, is idempotent by dispatch identity, and keeps an
uncertain cross-database reservation conservative. Paid admission requires an
explicit accounting bootstrap; H3 does not change historical Wan/Atlas
allowances.

Recovery captures real nonterminal video rows. A restored known remote H3 job
can only explicitly reconcile through a matching configured adapter; unknown or
pre-dispatch work cannot replay. Close refuses a nonterminal video job. Once
bytes are downloaded, listing, review, selection, and range playback operate
from the project folder without the original application database or H3
configuration.

The retained runtime, legacy import/migration, gateway deployment, live provider
execution, and historical Wan ledger remain unchanged.

## Checks

| Check | Result |
| --- | --- |
| focused direct video/recovery/API/persistence tests | 32 passed; includes fake H3 prepare/duplicate-submit/reconcile/review/select/range playback/snapshot/restore, an air-gapped restored API, accounting idempotency/cap contention, known matching-adapter recovery, and unknown replay refusal |
| `npm --prefix frontend test` | 16 files, 149 tests passed |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend run build` | passed; refreshed `src/plotloom/static/workbench.js` (existing Vite chunk-size warning) |
| focused browser H3 journey | 1 passed through real FastAPI and file SQLite: H3 fixture lifecycle, snapshot, original removal, isolated restore, selection, and playback |
| `uv run --locked pytest -q` | 700 passed, 9 skipped; 278 warnings |
| `npm --prefix frontend run test:e2e` | 39 passed against real FastAPI/file-SQLite fixtures |
| `uv build --wheel` and installed-wheel smoke | built `plotloom-0.1.0-py3-none-any.whl`; isolated install smoke passed |
| independent Terra review | one read-only review identified local access incorrectly gated on H3 configuration; routes and air-gapped restore coverage were corrected, then all listed gates passed |

The locked test environment still reports the pre-existing FastAPI TestClient,
SQLite datetime-adapter, and selected Pydantic serialization warnings. No new
test failures or static-asset freshness gaps remain.
