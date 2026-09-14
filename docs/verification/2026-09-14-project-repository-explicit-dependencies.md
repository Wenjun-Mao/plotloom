# Project repository explicit-dependency receipt

## Outcome

`ProjectAuthoringRepository`, `ProjectGenerationRepository`, and
`ProjectMediaRepository` no longer accept or retain the full
`SQLiteRepository` composition root. Each receives only its named typed
capabilities. Generation-only admission (frozen-provider identity and recovery
callbacks) is now owned by `generation_admission.py`, rather than being exposed
through the retained facade.

The root cause was an incomplete earlier extraction: public methods had moved
to the three facades, but each facade still accepted an `Any`-typed root and
reached through it dynamically. This kept the actual dependency boundary at the
retained facade. The correction belongs in composition and constructor contracts:
it makes authority visible to callers while retaining the existing transaction,
hash, compare-and-swap, recovery, and media semantics. ADR 0042 and the
modularization roadmap record that correction.

The direct project-folder API, pipeline, image, video, snapshot, and
qualification paths now import narrow project capabilities. A legacy-import
blocker regression runs real direct project flows and the installed-wheel probe
does the same without loading `legacy_repository`.

## Verification

- `uv run --locked python -m compileall -q src/plotloom scripts/smoke_installed_wheel.py`:
  passed.
- Focused regression suite covering alpha fixture reuse, retained qualification,
  project persistence, and the explicit-composition contract: **64 passed**.
- `uv run --locked pytest -q`: **712 passed, 9 skipped**. The existing
  FastAPI/SQLite/Pydantic warnings remain; no new failures were masked.
- Frontend `npm --prefix frontend test`: **149 passed**; `typecheck`,
  `typecheck:e2e`, and production build passed. The Vite large-bundle warning
  is pre-existing; generated files under `src/plotloom/static/` remained clean.
- Browser `npm --prefix frontend run test:e2e`: **39 passed**.
- Fresh `uv build --wheel` followed by
  `uv run --locked python scripts/smoke_installed_wheel.py <wheel-directory>`:
  passed. The fresh environment installs the wheel, blocks the retained facade,
  constructs the direct project authoring surface, creates a snapshot, and
  upgrades a fresh SQLite database to the Alembic head.
- `git diff --check`: passed.

One Terra read-only review identified two integration issues before final gates:
the conformance qualification seam had to preserve its injectable retained
repository factory, and direct project tests had copied the alpha fixture. The
factory is now lazy/injectable, and the deterministic fixture has one shared
legacy-free home used by both test groups. A final review pass also found a
missing V3 provider-profile test import; it was restored before the 64-test and
full-suite runs above.

No provider calls, migrations against user data, or generated frontend assets
were changed during this checkpoint.
