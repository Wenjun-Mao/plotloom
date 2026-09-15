# MiniMax-H3 catalog V3 clean-cutover verification

**Commit:** `8f51a31`  
**Date:** 2026-09-15  
**Scope:** retire the 864 × 480 compatibility profile and implicit H3 profile
fallbacks without changing Spark's protected configuration or managed data.

## Root cause and repair

The original one-profile H3 prototype remained a non-selectable catalog row,
but also remained the gateway HTTP default, template identity, and adapter
fallback for incomplete frozen requests. This was runtime compatibility debt,
not merely historical documentation.

V3 removes the retired profile from both independently versioned catalogs,
requires `profileId` for every new gateway request, rejects missing/unknown
profiles before creating a job or fetching a source URL, and replaces the
old-profile-named graph asset with a profile-neutral Turbo template. Plotloom's
adapter and frontend no longer filter a mixed current/historical catalog or
infer an old profile for a frozen request, response, or output.

The decision and deployment boundary are recorded in
[ADR 0049](../adr/0049-h3-catalog-clean-cutover.md).

## Verification

- `uv run --locked pytest -q` — **497 passed**; one pre-existing Starlette
  TestClient deprecation warning.
- `npm --prefix frontend test` — **149 passed**.
- `npm --prefix frontend run typecheck` — passed.
- `npm --prefix frontend run build` — passed; generated static bundle updated.
- `npm --prefix frontend run test:e2e` — **39 passed**.
- `docker build -f services/minimax_h3_gateway/Dockerfile -t
  plotloom-h3-gateway:catalog-v3-clean-cutover .` — passed.
- `uv build`, wheel content inspection, and isolated installed-wheel import —
  passed.
- `git diff --check` — passed.

## Spark deployment check

Only the deployed gateway source package was synchronized with `rsync
--delete`; protected `.env`, SQLite state, input assets, and managed outputs
were not replaced. The gateway container was rebuilt and recreated from its
existing source-only deployment directory.

`GET http://100.64.35.71:8090/health` returned `status: ok`,
`profileContractVersion: 3`, exactly the six current profiles, and fixed
`dispatchConcurrency: 1`. The retired ID was absent. Before deployment, there
were no non-terminal jobs using the retired profile. A post-deployment active
job, if any, was verified to use a current catalog profile; no new H3 job was
submitted for this verification.
