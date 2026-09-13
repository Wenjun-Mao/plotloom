# Project-folder storage checkpoint 2A: direct repository correction

## Scope and disposition

Baseline: `460ff5685e0f25168d30f20f38fbf060c99bb0c7` on clean `main`.

The baseline's temporary mixed `SQLiteRepository`, `_rebind_staging_project_id`,
and success-only `ProjectGenerationEvidence` projection are rejected. They
made a disposable harness authoritative and dropped non-success lifecycle
evidence before it reached `project.sqlite3`.

This correction introduces a direct, bound `ProjectSQLiteRepository` for the
canonical text pipeline. It reuses `PipelineEngine`, `LifecycleJobRunner`, and
their normal atomic sealed-stage commit. `project.sqlite3` now records run
admission, plans, work units, attempts, artifacts, seals, repair lineage, and
all terminal outcomes at their real lifecycle boundaries.

The new project format is version 3 and deliberately has no importer or
compatibility reader for the rejected construction schema. The retained runtime,
pilot data, application database, provider/gateway behavior, frontend, and
media wiring are unchanged and unwired.

## Ownership and guardrails

- The project schema is a bounded canonical-text subset, not a copy of the
  mixed application schema. It excludes provider settings/profiles/selection,
  global ledger tables, and unrelated image/video/review tables.
- Application storage retains public profile selection and accounting. A
  process-local admission scope freezes the selected public profile on a run;
  `RunSecretBroker` remains the only bearer-key path, and none mode receives no
  lease.
- Artifact persistence rejects recognizable secret-shaped values after the
  existing response-redaction boundary. Credentials do not enter project DB
  rows, traces, or artifact records.
- Exact repair uses the durable parent work-unit scope, binding hashes, and
  referenced evidence directly. A stale parent is rejected; no repair or
  replay is implicit.

## Focused evidence

`uv run pytest tests/test_project_storage.py -q`

Result: `8 passed`.

The fixture coverage proves two separate project homes execute and reopen the
actual four-stage deterministic pipeline; direct failed, cancelled,
quarantined, and interrupted/outcome-unknown records survive; a restart marks
the ambiguous dispatch unreplayable; stale repair and foreign routes fail;
bearer and none profiles remain secret-free; and successful runs have complete
canonical heads only.

`uv run python -m compileall -q src tests` and `git diff --check`

Result: passed.

## Full verification

- `uv run --locked pytest -q` — `661 passed, 9 skipped` in 60.46 seconds.
  Existing dependency/runtime warnings were retained: FastAPI's TestClient
  deprecation, SQLite datetime-adapter deprecations, and two pre-existing
  Pydantic serialization warnings in work-unit persistence tests.
- `uv build --wheel --out-dir /tmp/plotloom-project-storage-wheel-vDC1EJ` —
  built `plotloom-0.1.0-py3-none-any.whl`.
- `uv run --locked python scripts/smoke_installed_wheel.py
  /tmp/plotloom-project-storage-wheel-vDC1EJ` — passed from a fresh isolated
  environment. Wheel SHA-256:
  `ac3d3e6853f0e8e75ad34cfbea89e0c22a250e70ab1c0b4401f79610cf550d84`.

One attended read-only Terra review remains required before release. Its result
and any remediation will be appended before the source receipt is finalized.
