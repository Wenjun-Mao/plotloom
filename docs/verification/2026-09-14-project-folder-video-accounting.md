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

## Dispatch-boundary correction

The direct H3 contract now freezes an adapter ID/version plus a secret-free
fingerprint of the configured transport instance. It excludes endpoint bytes,
credentials, userinfo, query/signed URLs, and authorization data from the
portable project snapshot. Each current transport binding is checked before
preflight, upload, submit, poll, and download; an otherwise matching adapter
at another endpoint fails closed, including known-ID restore reconciliation.

Direct project video is composed with the ledger-free lifecycle owner and
admits only the exact `local_capacity_v1` policy. A missing, unknown, or paid
policy cannot create an allowance or touch the retained Wan ledger tables.
The application dispatch owner was extracted from profile storage. Its tests
prove durable application reservation → project claim → application claim event
→ provider-call order, conservative claim-event fault recovery, cancellation
between reservation/claim, no provider call after pre-transport failure, and
no replay after restart.

## Checks

| Check | Result |
| --- | --- |
| focused direct video/API/transport tests | 27 passed; includes instance mismatch/missing-binding refusal, signed-URL rejection, exact policy admission, durable dispatch ordering/fault/cancel/no-replay, retained-ledger isolation, and H3 prepare/reconcile/playback |
| `npm --prefix frontend test` | 16 files, 149 tests passed |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend run build` | passed; refreshed `src/plotloom/static/workbench.js` (existing Vite chunk-size warning) |
| focused browser H3 journey | 1 passed through real FastAPI and file SQLite: H3 fixture lifecycle, snapshot, original removal, isolated restore, selection, and playback |
| `uv run --locked pytest -q` | 707 passed, 9 skipped; 278 warnings |
| `npm --prefix frontend run test:e2e` | 39 passed against real FastAPI/file-SQLite fixtures |
| `uv build --wheel` and installed-wheel smoke | built `plotloom-0.1.0-py3-none-any.whl`; isolated install smoke passed; SHA-256 `bdfcdeb76d9d9ad57bcafb842841e03bed58cd77e62390b8ad9b0bc61992e3ba` |
| independent Terra review | one read-only review found non-HTTP signed URL acceptance in backend identity configuration; the URL-root validator and regression coverage were corrected before the final gates |

The locked test environment still reports the pre-existing FastAPI TestClient,
SQLite datetime-adapter, and selected Pydantic serialization warnings. No new
test failures or static-asset freshness gaps remain.
