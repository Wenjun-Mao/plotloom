# ADR 0081: Narrow source-static browser and API import checks

Status: Accepted for bounded verification, 2026-09-22.

## Context

The manual CI workflow already builds and drift-checks the checked frontend
bundle and smoke-tests the installed wheel. Its shared Playwright fixture
serves Vite, however, so it does not execute the checked bundle through
FastAPI. The wheel smoke verifies packaging and startup but does not run the
wheel's JavaScript or CSS in a browser. Separately, Ruff 0.16.8 reports two
F401 unused imports in `src/plotloom/api`; a whole `src/plotloom` check reports
396 and is outside this gate.

## Decision

Add an opt-in checked-static mode to the shared E2E fixture. It reuses the
disposable FastAPI and fake-provider stack, serves `src/plotloom/static/` from
FastAPI, and starts no Vite process. Existing E2E specs continue using their
current Vite fixture. A dedicated smoke observes same-origin `/v2/`
JavaScript/CSS responses, request failures and page errors, saves a Brief from
the sample project, and verifies it after reload. Isolated route-interception
cases return 404 for the JavaScript and CSS entry assets and prove the smoke
gate rejects both.

Pin Ruff 0.16.8 in the development dependency group. Remove only the two
imports confirmed unused in their own API modules and run
`uv run ruff check src/plotloom/api --select F401` in the existing manual CI
workflow. Do not add a whole-source Ruff gate, autofix, formatter, ESLint,
automatic CI triggers or a build-system change in this slice.

The source-static browser smoke and installed-wheel smoke are separate
evidence: the former executes the source checkout's checked bundle through
FastAPI; the latter checks installed package contents and startup outside the
source tree and does not execute browser assets.

## Rejected alternatives

- Replacing the Vite fixture for all E2E specs would remove existing dev-server
  coverage; the static mode stays opt-in.
- Running Ruff over all of `src/plotloom` would surface 396 existing F401
  findings instead of the two confirmed API imports in this slice.
- Treating wheel package/startup checks as browser evidence would leave the
  browser's source-static path untested.
- Changing automatic CI triggers, adding autofix/formatting, or replacing the
  build system is outside this bounded verification decision.

## Consequences

The static fixture uses the same disposable storage and provider fakes as the
existing E2E mode. Browser and persistence coverage now exercises the checked
source bundle, while installed-wheel browser coverage remains open. The CI
workflow remains `workflow_dispatch` only. The scope does not imply product or
creative acceptance.
