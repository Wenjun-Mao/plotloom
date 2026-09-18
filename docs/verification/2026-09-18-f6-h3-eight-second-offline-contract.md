# F6 H3 eight-second offline contract verification

Date: 2026-09-18. Tested source revision is recorded with the delivery commit.

## Scope and result

This is the bounded offline adapter and product-contract change identified by
the [F6 readiness receipt](2026-09-18-f6-h3-audiovisual-readiness.md). It does
not contact H3, create a retained project, upload an image, generate media,
change gateway/deployed configuration, or make an audiovisual/creative
acceptance claim.

Plotloom now accepts exactly five seconds (the existing default: 124 frames at
24 fps, about 5.167 seconds) and eight seconds (192 frames at 24 fps, exactly
eight seconds) for a new catalog-backed H3 I2V job. Every other duration is
rejected before transport. The persisted job snapshot freezes requested
duration, frames, fps, geometry, native audio, input aspect policy, seed,
adapter/version, and configured backend binding. Submit and poll responses
must match its frozen profile, aspect policy, seed, requested duration, and
frame count. Ingestion separately requires H.264/AAC plus exact geometry, fps,
frame count, and the established one-frame duration tolerance.

The public profile timing remains its five-second default. The capability
projection and focused workbench control expose only the qualified `5` and `8`
choices rather than the gateway's broader 5--15 parser range. The direct H3
dispatch lease records the frozen requested seconds without touching the Wan
paid-pilot ledger.

## Automated evidence

- `uv run --locked pytest -q tests/video_backends/minimax_h3/test_transport.py tests/test_project_storage_video.py tests/test_production_project_folder_runtime.py`
  - passed: 41 tests. Covers default and eight-second compilation/snapshots,
    restart, submit/poll duration-frame-seed mismatch refusal, observed-output
    mismatch refusal, hash/currentness, backend binding, and dispatch lease
    units.
- `uv run --locked pytest -q --maxfail=2`
  - stopped after 379 passing tests at two pre-existing extraction-contract
    hygiene failures: a root-level `output` directory and earlier ignored Relay
    clones under `.local/relay/` are discovered as undeclared roots/copies.
    They were preserved as required; no source test was relaxed or allowlisted.
- `cd frontend && npm run typecheck && npm run test -- --run`
  - passed: TypeScript check; 18 files / 162 tests.
- `cd frontend && npm run build:deterministic`
  - passed. Regenerated `src/plotloom/static/` deterministically; Vite reports
    its existing single-chunk size warning.
- `cd frontend && npm run test:e2e -- --grep "H3 browser path freezes"`
  - passed: one offline production-browser journey. It keeps five seconds as
    the initial choice, selects eight explicitly, freezes 192/24 in the
    request, and ingests the matching fixture through a backend restart.

## Boundaries retained

This is not a live F6 qualification, a selected media candidate, a native
audio verdict, an F5 projection, a TTS/lip-sync decision, or authorization for
a third duration. The later attended assignment remains limited to at most two
unselected eight-second clips and must use the normal production admission
path.
