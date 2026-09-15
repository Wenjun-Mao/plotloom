# H3 direct-image intake verification — 2026-09-14

## Candidate

- Source implementation: `c3de055` (`feat: add direct H3 image job intake`)
- Documentation clarification: `f5c1b5c`
- Deployment host: Spark private Tailnet gateway at `http://100.64.35.71:8090`
- Scope: URL/raw image admission and the stateless one-step HTTP contract.
  No H3 generation was submitted for this verification.

## Automated evidence

- `uv run --locked pytest -q`: **494 passed** (one existing Starlette
  deprecation warning).
- Gateway-focused FastAPI tests: **28 passed**.
- Local gateway Docker build completed successfully.
- `git diff --check` passed before release.

## Spark verification

The service was rebuilt with Docker Compose while retaining its existing
gateway `.env` and data directory. `GET /health` reported `status: ok`, the
seven reviewed profile descriptors, `queuedJobs: 0`,
`activeDispatches: 0`, and `dispatchConcurrency: 1`. Its OpenAPI document
contains `POST /v1/video-jobs/from-image`.

The client-guide source image was fetched through the deployed
`POST /v1/assets` JSON URL path:

- source: `https://raw.githubusercontent.com/Wenjun-Mao/plotloom/main/docs/storyboard-handbook/assets/storyboards/moon-control-room-finished-frame.png`
- result: PNG, `1672 × 941`, SHA-256
  `77cf18cb266d740de77ac9e0a6f29ba0e7b2fa4e9521579a662981fb8bb56a5e`
- result asset: `asset_8a52907742aa4c8fa084d3714a78f28a`

That ordinary unreferenced gateway asset is intentionally governed by the
existing 30-day keyframe retention policy. The test did not create an H3 job,
reach ComfyUI, or consume video-generation time.
