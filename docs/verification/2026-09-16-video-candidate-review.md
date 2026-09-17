# Video candidate review — verification receipt

Candidate: local working tree following ADR 0052.  This receipt covers only
the approved shot-scoped candidate slice and disposable fixtures; no existing
pilot media was generated, replaced, or removed.

## Ownership map

- `VideoJobPersistence` owns frozen attempts, immutable review history,
  revisioned shot selection, and disposal state.
- `ProjectVideoRepository` owns the project-file deletion boundary and its
  shared-blob recheck.
- `ProjectArtifactStore` owns confined, content-addressed byte removal.
- `VideoPilotPanel` owns fresh intentional client idempotency keys, comparison,
  explicit selection, irreversible confirmation, and route-safe refresh.

## Executed evidence

- Focused Python candidate regressions passed: two alternatives, preserved
  initial selection, stale selection conflict, selected/shared-blob safety,
  disposal/reopen, and cross-kind managed-asset sharing (2 passed).
- Existing direct-folder runtime checks passed (8 passed), and frontend unit
  tests passed (157 passed); TypeScript app and E2E typechecks passed.
- Deterministic frontend build completed and refreshed
  `src/plotloom/static/workbench.js`.
- The full 42-test Playwright suite passed. Its real production
  FastAPI/file-SQLite candidate journey generated two offline H3 alternatives,
  selected the second, restored into a separate installation, and irreversibly
  discarded the unselected first. The selected route media remained readable.
  The independent H3 profile, route, and branching-player journeys passed in
  that suite.
- Fresh wheel build/install/import smoke passed from the Relay scratch
  directory.

## Review and gaps

An independent read-only review found two P1 issues before final checks:
discarded rows left a half-addressed hash that broke reopen validation, and the
blob guard omitted managed/runtime artifact owners.  Both are fixed and the
new regressions above cover the corrected contracts.

The attempted complete locked Python suite did not provide a clean candidate
gate: its existing last-failed cache records 16 failures outside this slice
(generation/provider, pipeline, gateway and legacy repository tests).  No
failure was attributed to the candidate changes, but the full-suite gate needs
a clean director-owned baseline rerun before release acceptance.
