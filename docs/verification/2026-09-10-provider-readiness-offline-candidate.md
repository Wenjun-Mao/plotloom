# Provider-readiness offline candidate

Date: 2026-09-10

## Outcome

This offline candidate separates application service reachability from the
selected text backend's readiness. New pipeline, rebuild, and exact-repair
admissions obtain a V3 frozen snapshot with a trusted adapter ID/version, then
reject only a definite non-generative preflight failure. V1/V2 snapshots retain
their historical hash and resolver paths.

Readiness observations are application-memory-only, profile/revision scoped,
timestamped, and secret-free. They are cleared after a material profile or
availability edit and return as `unverified` after restart. The workbench shows
the service plane separately from backend state, profile, reason, observed
time, and remediation.

## Offline evidence

- `uv run pytest -q tests/generation/test_provider_profiles.py tests/generation/test_providers.py tests/backend_core/test_api.py` — 55 passed.
- `npm --prefix frontend run typecheck` — passed.
- `npm --prefix frontend test -- --run` — 115 passed.
- `npm --prefix frontend run build` — passed; generated workbench assets were
  refreshed.
- `npx playwright test --config playwright.config.ts` from `frontend/` — 23
  passed, including the external OpenAI-compatible fake-provider paths. Its
  readiness route serves `GET /v1/models`; it never sends a completion merely
  to assess readiness.
- A local, keyless `TEXT_AUTH_MODE=none` server was viewed at 1440×900 with
  Playwright. The disconnected workbench baseline showed all three columns and
  distinct badges: `Plotloom 服务：未连接` and `文本后端：unverified · default ·
  readiness.not_checked · 未检测`. The temporary screenshot directory was sent
  to Trash after inspection because the repository's extraction boundary gate
  intentionally forbids undeclared top-level artifact directories.
- `uv build --wheel` — built `plotloom-0.1.0-py3-none-any.whl`.
- `uv run python scripts/smoke_installed_wheel.py dist` — passed.

## Full-suite qualification

The unfiltered `uv run pytest -q` result was 518 passed, 9 skipped, 3 failed.
One failure was the temporary `output/` directory created for visual inspection
and disappeared once that generated directory was removed. The two remaining
failures are outside this change and predate it:

- `tests/backend_core/test_pipeline.py::test_graph_join_missing_convergent_null_uses_exact_expected_value_and_installs`
  expects a different repair-fact ordering; the assertion was last changed in
  `01107cbd`, while this candidate does not alter join repair code.
- `tests/backend_core/test_repository.py::test_file_sqlite_uses_alembic_foreign_keys_and_wal`
  expects migration `0010_v2_schema_approvals`, but the current unmodified
  repository migrates to `0011_text_profile_availability`.

With only those two known unrelated tests deselected, the full offline suite
passed: 519 passed, 9 skipped, 2 deselected. No live backend was contacted;
the default-backend retry remains an operator-owned pending gate.

## Secret boundary

The candidate persists only public profile configuration, V3 adapter identity,
and safe readiness state/reason/time. Browser and server credentials are leased
only for the probe or dispatch and are never included in a profile, snapshot
observation, trace, log, UI response, or this ledger.
