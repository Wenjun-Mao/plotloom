# Video candidate review — verification receipt

Candidate: `2925fddc84cea4c6da88db97ac74b4280c2d8f9b` following ADR 0052.
This receipt covers only the approved shot-scoped candidate correction and
disposable fixtures; no existing pilot media was generated, replaced, or
removed.

## Ownership map

- `VideoJobPersistence` owns frozen attempts, immutable review history,
  revisioned shot selection, and disposal state.
- `ProjectVideoRepository` owns the project-file deletion boundary and its
  shared-blob recheck.
- `ProjectArtifactStore` owns confined, content-addressed byte removal.
- `VideoPilotPanel` owns fresh intentional client idempotency keys, comparison,
  explicit selection, irreversible confirmation, and route-safe refresh.

## Executed evidence

- The production-path pre-change folder regression proves an exact format-8
  schema is read-only/restore non-mutating, refuses a shared-lease mutation,
  then receives one exclusive transactional transition and reopens with its
  selected review/job preserved. Bulk IDs exclude a later candidate; stale
  selection rejects; and an after-byte-removal interruption reopens/retries
  without damaging selected/shared bytes.
- `uv run --locked pytest -q` passed: **556 passed, 1 warning**, exit 0.
- `npm --prefix frontend test` passed: **158 tests in 16 files**; application
  and E2E TypeScript checks passed. The native candidate peer-pause regression
  is included.
- Deterministic frontend build passed and left `src/plotloom/static/` fresh.
  Vite reported its existing over-500 kB chunk advisory only.
- The full **42-test** Playwright suite passed. Its real production
  FastAPI/file-SQLite candidate journey generated two offline H3 alternatives,
  selected the second, restored into a separate installation, and irreversibly
  discarded the unselected first. The selected route media remained readable.
  The independent H3 profile, route, and branching-player journeys passed in
  that suite.
- Fresh wheel build/install/import smoke passed from Relay scratch for
  `plotloom-0.1.0-py3-none-any.whl`, SHA-256
  `8c2bd29363f35a5180ff30a7837bcfb88b5c6ffda30da43906d522459c87a5ee`.

## Review and gaps

An attended independent Terra read-only delta review found one P1: the
transition was reachable under a shared project lease. The final candidate
routes the known legacy case through a short exclusive transition before
returning a normal shared handle; the regression proves the shared-lease
refusal. The review also caught wording that could misstate the historical
latest-review projection; ADR 0052 now states that only a latest `select`
review becomes the transitioned selection. No unresolved review findings
remain. Actual command logs are retained in the assignment Relay scratch.
