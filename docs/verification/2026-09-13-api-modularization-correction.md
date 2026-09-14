# API modularization correction receipt

## Checkpoint

- **Verified baseline:** clean
  `28c4a2a73ec03b2e44ab796802c66463cd979cf7`.
- **Original contract authority:** isolated source export of monolith
  `5ec8ef83fc3fa6efdd9b3b41f5e76a7a8c2e1daf`, created with `git archive` in a
  temporary directory. No checkout reset, worktree change, `.env`, user data,
  provider, or frontend state was touched.
- **Owned scope:** `src/plotloom/api/`, tests, the modularization roadmap,
  ADR 0041, and this receipt.
- **Stopping condition:** preserve both public factory contracts while moving
  text admission and project-folder media to their cohesive owners.

## Contract characterization

The isolated original export instantiated both factories with a temporary
static directory, explicit injected lifespan, observer-capable scheduler, and
separate temporary direct-storage roots. The canonical record includes every
route registration, full OpenAPI schemas and selected operation declarations
(including operation IDs, request bodies, responses, aliases, headers, and
defaults), factory signatures, state-key sets, static mounts, lifespan identity,
and completion-observer registration.

The record is 206,297 JSON bytes with SHA-256
`1d33b23c3809d63654c780d7ac07ecd2bd6acfe7a8fdb6b18a8a15b98feaa72e`:

| Factory | Routes | OpenAPI paths | Schemas |
| --- | ---: | ---: | ---: |
| `create_app` | 72 | 55 | 125 |
| `create_project_folder_authoring_app` | 40 | 26 | 78 |

`tests/backend_core/test_api_modularization_contract.py` retains this
provenance-bound expectation. Its expected hash is a baseline artifact, not a
candidate-generated snapshot; it normalizes only JSON key ordering.

## Implementation and focused evidence

- `api/application.py` is now 123 lines of composition.
- `api/text_admission.py` is a 420-line typed application-lifetime service;
  readiness state and observer ownership do not escape into persistence.
- `api/project_folder_media.py` is 282 lines and owns direct-storage asset,
  visual-intent, keyframe, preview, and workbench routes.
- `api/project_folder_image_jobs.py` is 443 lines and retains package/delivery
  responsibilities.
- `uv run --locked pytest -q tests/backend_core/test_api_modularization_contract.py tests/backend_core/test_m15_profile_repository.py tests/test_project_storage_image_workflow.py`
  — 8 passed.
- Focused API/storage suite — 153 passed:
  `tests/backend_core/test_api.py`, `test_frontend_contract.py`,
  `test_project_lifecycle.py`, `test_storyboard_review.py`, `test_pipeline.py`,
  `test_exact_work_unit_repair_integration.py`, `test_m15_profile_repository.py`,
  `test_managed_still_media.py`, `test_image_jobs.py`,
  `tests/test_project_storage.py`, and
  `tests/test_project_storage_image_workflow.py`.

## Full stable-candidate gates

| Gate | Result |
| --- | --- |
| `uv run --locked pytest -q` | 665 passed, 9 skipped |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend run typecheck:e2e` | passed |
| `npm --prefix frontend test` | 132 passed across 14 files |
| `npm --prefix frontend run build` | passed; the tracked static bundle was unchanged |
| `git diff --exit-code -- src/plotloom/static` | passed after build |
| `npm --prefix frontend run test:e2e` | 30 passed |
| `uv build --wheel --out-dir <temporary directory>` + installed-wheel smoke | passed |
| `git diff --check` | passed |

The frontend build emitted only its existing bundle-size advisory. Python's
passing suite retained existing deprecation and Pydantic serializer warnings.
There is no configured Python linter in the locked environment (`ruff` is not
an installed project command), so no substitute lint result is claimed.
