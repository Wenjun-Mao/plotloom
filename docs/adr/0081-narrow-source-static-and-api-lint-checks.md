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

## Current-control browser journeys · 2026-10-03

Browser setup must exercise the current creator UI rather than retain removed
sidebar/button labels or depend on disclosure positions. The shared
`frontend/e2e/workbench-controls.ts` names secondary navigation and media panels;
candidate toggles retain their asset-bound test identity while their visible
labels distinguish pending review. Hydration tests verify withdrawn controls,
then normal navigation after load. Persistence, source/identity ownership,
selection and natural playback assertions remain required. This updates test
setup for current UI contracts; it does not restore retired UI or widen product
acceptance. ADR0109 owns the independent CI budget/evidence boundary.

The sample shot seed emits the already-defined canonical `visibleTexts: []`
default explicitly. Its omission made exact first-save roundtrip checks differ
after backend serialization; the seed, not a permissive comparator, owns the
repair. Serialized-bootstrap regression coverage retains the exact stage
payload assertion and introduces no authored text or ownership change.

H3 media journeys must use the same source read, faithful English direction
review, complete prompt preview and explicit freeze as the current H3 UI. The
non-H3 direct-freeze button is not an H3 setup shortcut. Synthetic fixtures
share the reviewed-direction helper without changing source text, admission,
selection, persistence or native playback assertions.

The shared page fixture owns route-handler teardown: after the test body, it
removes routes and awaits pending handlers before Playwright disposes the
request context. Use [`unrouteAll({ behavior: "wait" })`](https://playwright.dev/docs/api/class-page#page-unroute-all),
not error suppression; held-response cases must release their owned gates.
Lifecycle regressions cover waiting, test failure and drain failure. Reload
persistency first establishes a hydrated owner. Prepared and ready/accepted
stale-review journeys are separate cases with unchanged assertions/deadlines,
so repeated hydration does not consume another state transition's entire
assertion budget.

When a test must remove an interceptor before its body ends, first await the
operation's rendered outcome and any dependent projection read. Backend Close
acknowledgement is earlier than the refreshed closed-directory row; removing
Chromium's last route during that read changes global Fetch interception and
can strand the test's own request. Failed Close instead awaits its rendered
refusal and restored enabled editor. This is harness sequencing, not a product
retry, longer timeout or permissive persistence assertion. Required-mark layout
checks likewise assert inline baseline and containment in the label line rather
than comparing inline-text and enclosing-line-box top pixels across OS fonts.

Shot changes intentionally clear retained-image draft ownership (ADR0103).
Multi-shot fixtures must retain their chosen asset again and explicitly review
compatibility, not inherit another shot's temporary retention. Approved-board
reloads use the named review control before checking collapsed detail. Query
identity assertions compare parsed parameters, not parameter order; textareas
use their accessible textbox names rather than wrapper-label text that includes
the initial textarea contents.

The active image journey follows the native specialist `/send` receipt and
immutable package/delivery checks. Removed clipboard controls and an already
skipped retired Story-Bible proposal test are not current product contracts.
Original/refinement delivery, frozen context/reference/provenance, stale-intent
inapplicability, tamper rejection and historic reference ownership remain tested.
The tampered terminal error retains its dispatch reservation as production
requires; fixture cleanup does not pretend that rejection released it.
