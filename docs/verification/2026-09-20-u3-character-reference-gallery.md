# U3 character-reference gallery verification — 2026-09-20

## Scope and contract

This is the first approved, bounded U3 surface only: the read-only
`?view=character-reference-review&project=<id>` character gallery. It composes
the existing accepted-cast, character-reference decision, proposal/delivery,
and managed-asset read owners. No server API, persistence schema, selection,
generation, import, refresh, disposal, provider, H3, script, storyboard, or
Story Bible contract changed.

The root cause was a presentation gap: F2B already retained the selected
reference, candidate, currentness, delivery and refinement facts, but only in
an authoring surface. The gallery makes those owners readable without adding a
projection or write path. ADR 0071 records the durable view boundary.

## Executed evidence

- `npm run typecheck` — passed.
- `npm run typecheck:e2e` — passed.
- `npm test` — 18 files / 165 tests passed.
- `npx vitest run --config src/pages/CharacterReferenceGalleryPage.vitest.config.ts`
  — 1 focused in-scope gallery test passed. It fails a selected hero, changes
  the preserved gallery component to a second subject with the same asset, and
  verifies the image presentation recovers under the new identity.
- `npx playwright test --config playwright.config.ts e2e/cast-reference-studies.spec.ts`
  — 4 production FastAPI/file-SQLite browser journeys passed, including held
  gallery response invalidation, selected-image HTTP failure, and parent-link
  hash/focus behavior.
- `npx playwright test --config playwright.config.ts e2e/story-prototype.spec.ts`
  — 3 production browser journeys passed (multi-scene screenplay admission,
  focused screenplay/storyboard route switching, and stale storyboard refusal).
- `npm run build:deterministic` — passed; refreshed
  `src/plotloom/static/workbench.css` and `workbench.js`.
- `git diff --check` — passed.

The focused browser journey uses the existing F2B supported cast-only fixture
and retained test-only raster bytes. It verifies no-selection/no-image,
selected versus merely-current candidate, refinement parent, collapsed stored
frozen direction, separate technical details, failed/inapplicable delivery,
stale cast presentation, navigation to and from the screenplay route, backend
restart persistence, and that gallery network requests are all GET. It asserts
the fixture's canonical stage set remains only `story_graph`, proving the view
does not require or create script, storyboard, or Bible state.

Wide (1440 px) and narrow (768 px) captures were inspected from the successful
Playwright output. The first narrow capture exposed that the 760 px gallery
breakpoint left its desktop subject rail active at 768 px. The corrected 820 px
gallery breakpoint collapses that rail before image cards become constrained;
the rerun capture shows full-width readable cards and preserved image aspect.

An independent read-only Terra review of the stable delta initially found four
concrete gaps: no-delivery proposal states were omitted, stale selected assets
were text-only, historical proposals widened admitted subjects, and candidate
provenance did not join to the managed-asset owner. The final delta retains
prepared/exported/cancelled no-delivery evidence, renders historical selected
assets or missing cards, derives subjects only from accepted cast mappings, and
joins each candidate to the provenance-bearing managed-asset record. The
focused suite above was rerun after those corrections.

## Superseded walkthrough statement

The prior statement that a persistent walkthrough was outside scope was
incorrect: the approved acceptance correction expressly authorizes a separate,
disposable persistent technical fixture. That prior walkthrough was unattempted,
not blocked. Its independent review was also pre-fix only and cannot establish
acceptance of the corrected image and lifecycle contract. This receipt is
updated with the actual post-fix walkthrough and review evidence below.

## Post-fix persistent production walkthrough

Executed after the correction against the normal production entrypoint, not
`OfflineH3GatewayFake`: `PLOTLOOM_ENABLE_H3_GATEWAY=false PLOTLOOM_HOST=127.0.0.1
PLOTLOOM_PORT=49071 PORT=49071 PLOTLOOM_OUTPUTS_DIR=<ignored persistent
outputs root> PLOTLOOM_APPLICATION_DATA_DIR=<ignored persistent application
root> uv run --locked plotloom`. The process remains available at
`http://127.0.0.1:49071` (PID 4006). Its disposable, ignored roots are
`.local/relay/4f01b0c1-25e6-4447-bcd4-695fe58f8859/persistent-u3/outputs` and
`.local/relay/4f01b0c1-25e6-4447-bcd4-695fe58f8859/persistent-u3/application`.

The separate project is `35271279-3269-431b-8088-165c1705bc2e`, visibly titled
“U3 persistent technical fixture — non-generated raster.” Its setup reused the
supported cast-only creation and proposal-delivery package-validation flow to
write two labelled retained P0 test rasters (original and refinement); no
ImageGen, H3 gateway, or other provider was called. The fixture setup writes
are separate from the following gallery viewing evidence.

At `http://127.0.0.1:49071/v2/?view=character-reference-review&project=35271279-3269-431b-8088-165c1705bc2e`, both served gallery assets decoded as
`image/png` at 1672 × 941. The view showed selected r2, the explicit
unselected original alternative, historical r1, and a recognizable original
parent thumbnail/link under the selected refinement. Browser snapshots and
inspected screenshots at wide and 768 × 900 narrow viewports confirmed readable
layout. The script navigation reached the intentional cast-only unavailable
state rather than fabricating screenplay data. Browser gallery viewing was
GET-only; no project revision or gallery-owned state changed after fixture
setup.

## Independent post-fix review

An independent Terra/high, read-only review was performed after all final code
and regression evidence changes. Exact final report: “Final scoped review:
**approved — no findings.** The receipt now distinguishes the dedicated passing
identity-recovery test from `npm test`; the current candidate satisfies the
requested corrections and remains read-only/GET-only.” Earlier review findings
on the identity-reset proof, parent-link focus, and receipt wording were
corrected before this final review; those prior reviews are not acceptance
evidence.

## Same-document gallery ownership regression closure

The prior Playwright case named `invalidates held gallery reads after a project
change` remains useful browser evidence, but its two `page.goto(...)` calls
destroy the first document. It therefore cannot by itself prove cleanup and
owner invalidation when this gallery component changes projects while a React
root remains mounted.

The focused identity-reset test was moved from `src/pages/` to the standard
`frontend/tests/` convention, and its bespoke page-only Vitest configuration
was removed. `npm --prefix frontend test` now discovers it together with the
actual-component delayed-response regressions in
`tests/character-reference-gallery.test.ts`. The tests mount one root, change
the project through `window.history` plus a supported React rerender, and use
controllable API promises that deliberately ignore `AbortSignal`. They settle
the new project first, explicitly flush React work, then settle the old
project's complete success or reject its old project read. In both cases the
new title remains visible and the old data/error cannot replace it. The tests
also assert that every old gallery request signal was aborted. The existing
same-asset subject identity-reset proof remains there, alongside a
selected-primary-missing-metadata assertion that ensures a selected hero is
not silently replaced by an available candidate.

Regression sensitivity was demonstrated locally without retaining a runtime
change: the component's success and error owner guards were temporarily
disabled, then only the two same-document tests were run. Both failed: late
old success replaced “New project” with “Old project”, and late old rejection
replaced the gallery with “old request failed”. The guards were restored before
the passing focused and full standard-suite checks below. This is evidence that
the tests exercise the actual gallery lifecycle contract, not an isolated
helper.

Final tests-only closure checks:

- `npm --prefix frontend test -- character-reference-gallery` — 1 file / 4
  tests passed under the standard `vitest.config.ts` discovery configuration.
- `npm --prefix frontend run typecheck` — passed.
- `npm --prefix frontend test` — passed after the final independent review.
- `git diff --check` — passed.

An independent Terra/high read-only review of this latest test/docs delta found
no issues. It inspected the mounted-root/history transition, deliberate
AbortSignal-ignoring deferred promises, explicit post-settlement React flushes,
success and rejection assertions, cleanup signal checks, and the absence of a
production-source delta.

The persistent production preview (PID 4006 on port 49071) and its existing
project `35271279-3269-431b-8088-165c1705bc2e` were not restarted, written, or
otherwise used by this tests-only closure.

## Product acceptance boundary

The browser and visual evidence verifies the presentation contract. It does not
constitute creative acceptance of any image, approval of any candidate, or an
attended user walkthrough of U3/U4.
