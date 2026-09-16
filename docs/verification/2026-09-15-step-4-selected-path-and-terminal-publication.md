# Step 4 selected-path and terminal-publication receipt

## Scope and outcome

This source-only slice projects selected current ingested clips onto one explicit
valid graph route, reports missing route clips, preserves native cut/final-hold
behavior, and removes the deprecated whole-run repair contract. It also treats
the existing durable `cancelled` image-job state as terminal for close and
snapshot while retaining late delivery as inapplicable evidence. No retained
project, candidate, provider, upload, dispatch, cancellation, or configuration
was changed.

## Verification

| Command | Result |
| --- | --- |
| `uv run pytest tests/test_project_storage_image_delivery_contracts.py tests/test_production_project_folder_runtime_boundaries.py tests/test_retained_runtime_coverage_inventory.py` | 17 passed; one existing TestClient deprecation warning |
| `uv run python scripts/retained_runtime_coverage_inventory.py --check` | passed |
| `uv run pytest -q` | 551 passed; one existing TestClient deprecation warning |
| `npm run test` | 150 tests in 16 files passed; focused API/video tests: 24 passed |
| `npm run typecheck` and `npm run typecheck:e2e` | passed |
| `npm run build:deterministic` | passed; regenerated `src/plotloom/static/` (existing Vite over-500 kB chunk warning) |
| `npm run test:e2e -- --grep "P2 H3 selected pair plays in order and survives file-SQLite restart"` | passed: real local H3 fixture playback crossed route scenes, cut on native end, held the final frame, reset/reselected the explicit route after restart, and retained bytes |
| `uv build --wheel --out-dir .local/relay/lean-step4-fix/wheel-final` plus `uv run --locked python scripts/smoke_installed_wheel.py .local/relay/lean-step4-fix/wheel-final` | passed in a fresh isolated installation; final wheel SHA-256 `293edef338832aaaa55ad517f30c93dc91923d6103dba409fb866b53975bae72` |

Unit coverage also asserts that an equally selected clip on an exclusive sibling
branch is excluded from the selected route. The browser proof is a local
fixture, not retained-media or human creative acceptance.

## Independent review

An attended independent Terra review found that the frontend still exposed the
removed whole-run repair endpoint. The client method and its API test were
removed, generated static assets were rebuilt, and the focused API/video,
frontend unit, typecheck, and static-build gates were rerun successfully.
