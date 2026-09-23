# Batch B assessment: narrow verification proposal

Status: assessment at local `main` `cb6fa27`, 2026-09-23. No tooling, workflow,
dependency, product, or fixture code has been changed. This is an
implementation-ready proposal, **not** approval to turn on CI triggers or
execute Batch C. The [tracker](2026-09-23-repo-simplification.md) remains the
scope boundary.

## What current source establishes

- F1: [CI](../../.github/workflows/ci.yml) is `workflow_dispatch` only. It
  already runs Python, frontend unit/type/E2E, builds the production frontend,
  checks `src/plotloom/static` for drift, builds a wheel, and runs the
  [installed-wheel smoke](../../scripts/smoke_installed_wheel.py). The wheel
  smoke checks packaged static files and production composition, but does not
  execute the JavaScript in a browser. An earlier [one-off production-static
  browser receipt](../verification/2026-09-18-story-branch-reader-prototype.md)
  exists; it is not a repeatable CI regression.
- [Shared Playwright fixture](../../frontend/e2e/fixture.ts) starts the real
  project-folder backend and a local fake provider in disposable roots, but
  serves all current specs through `npm run dev`/Vite. The production app
  already mounts `settings.static_dir` at `/v2` in
  `src/plotloom/api/project_folder.py`; its default is the checked bundle in
  `src/plotloom/static`. No new static server is needed.
- F21: [`build`](../../frontend/package.json) uses `vite build` and
  `build:deterministic` uses the same config through `frontend/build.mjs`.
  Existing CI gates `build`; these are two entrypoints, not evidence of a
  missing build. Keep the gated entrypoint in this small slice; evaluate
  deleting the wrapper only after an independently scoped parity check.
- F20: no Ruff or ESLint is declared in checked manifests. An isolated,
  read-only Ruff **0.16.8** diagnostic found **2 F401 unused imports** in
  `src/plotloom/api`: `CreativeHandoffError` in
  `project_folder_source_outline.py:11` and `TextProviderProfileSnapshot` in
  `text_admission.py:21`. The same rule reports **396** across all
  `src/plotloom` (318 marked fixable), so a whole-tree gate or autofix would
  be a separate, much larger cleanup. Existing TypeScript typecheck stays.

## Smallest later implementation, if approved

1. Extend only `frontend/e2e/fixture.ts` to expose a static mode that reuses
   its disposable backend/fake-provider stack but does **not** spawn Vite; set
   `frontendOrigin = apiOrigin`. Do not switch the existing E2E specs. Add one
   `frontend/e2e/shipped-static.spec.ts` that loads `/v2/`, requires the
   backend to serve `/v2/workbench.js`, opens the sample workbench, performs
   one explicit Brief save, reloads, and verifies authoritative content.
   Register response, request-failure, and page-error observers *before*
   navigation: every same-origin `/v2/` JS/CSS request must complete with 2xx
   (or a valid cache 304 on reload),
   including modulepreloads, and the test must require at least one script and
   stylesheet from the index. This catches a missing CSS file even if the UI
   remains interactive. The smoke tests the checked production bundle through
   the shipped FastAPI static mount.
2. Reuse CI's existing build/bundle-diff and Playwright step; the new spec is
   discovered by the existing `test:e2e` command. Focused local command:
   `npm --prefix frontend run build && git diff --exit-code -- src/plotloom/static && npm --prefix frontend run test:e2e -- --workers=1 e2e/shipped-static.spec.ts`.
   The wheel smoke remains a separate packaging check; this source-bundle
   browser smoke does not claim to launch an installed wheel.
3. Pin Ruff `0.16.8` in the `pyproject.toml` dev group and checked `uv.lock`, remove
   only the two verified API imports after caller review, then gate only
   `uv run ruff check src/plotloom/api --select F401` in the existing manual
   CI job. Before edits, reproduce with
   `uvx ruff check src/plotloom/api --select F401 --statistics` (baseline: 2).
   No ESLint addition, whole-tree Ruff gate, formatter, or `--fix` run belongs
   to this slice.

One worker means at most one disposable FastAPI/fake-provider stack for the
focused browser run; Playwright's current per-test timeout is 45 seconds and
fixture readiness waits are bounded. There are no external provider calls, retained
projects, or existing services in the proposed smoke. Stop and investigate if
the built bundle changes unexpectedly, the static request is not served from
the backend, or the test is flaky; after two unsuccessful attempts, preserve
evidence and reassess rather than widen the fixture. Automatic `push`/PR CI
triggers require a separate director decision and are unchanged here.
