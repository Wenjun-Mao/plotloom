# Story-and-branch reader prototype verification

Date: 2026-09-18. Scope: the approved representative story-and-branch reader only.

## Contract checked

`?view=story-prototype&project=<project-id>` is an opt-in read-only frontend
surface. It requests the existing project, canonical `story_graph` stage, the
confirmed script, and optional accepted cast/art display names. Routes come
from the existing `deriveRoutes` owner; `sectionBindings` select the confirmed
episode for each graph node. The page has no mutation callback; all requests
made by this surface are GETs.

The browser proof creates a disposable current-contract project from the
retained beacon/dock screenplay fixture. It confirms the opening and both
ending branches, then selects the dock branch and verifies that the beacon
episode is absent from the route reader. It also verifies the compact creator
stage links, explicitly unavailable art/production labels, preserved scene
groups and accepted display names, and no non-GET `/api/v2/` request, including
after a navigation to the existing source workspace.

## Commands and results

From `frontend/`:

```text
npm run typecheck
# passed

npm test
# 18 files, 164 tests passed

npm exec playwright test -- --config playwright.config.ts e2e/story-prototype.spec.ts
# 1 test passed; browser interaction and no-write assertion

npm run build:deterministic
# passed; refreshed src/plotloom/static/
```

An initial `npm test -- --runInBand` attempt was rejected because Vitest does
not support Jest's `--runInBand` flag; it ran no tests. During the browser-test
update, two first attempts correctly exposed stale expectations: the retired
“已接受剧本 r1” label and an incorrect source-page heading. Both were corrected
in the test before the final passing run. No cleanup command was run. Command
evidence, including the preserved failures, is retained in
[`2026-09-18-story-branch-reader-prototype.log`](2026-09-18-story-branch-reader-prototype.log).

## Visual evidence

Headless Chromium screenshots were inspected after the passing browser run:

- `frontend/test-results/story-prototype-reads-orde-94cfd--screenplay-without-writing/story-prototype-1440.png`
  — 1440 × 4153, opening and beacon route.
- `frontend/test-results/story-prototype-reads-orde-94cfd--screenplay-without-writing/story-prototype-768.png`
  — 768 × 4588, dock route after selection.

At both retained widths the first viewport contains one compact creator-stage
navigation, the opening-to-two-ending map, current route focus, and a readable
screenplay column. The exact 768 px screenshot shows the branch canvas in its
two-column grid: the opening card is on the left and the two choice cards are
on the right. The CSS defines a one-column, stacked branch canvas only at
`max-width: 760px`; that below-760 px behavior is source-defined but was not
demonstrated by a retained screenshot. The English screenplay text was not
translated or edited.

## Read-only preview

The pre-existing F5 proof project on port 8776 was not used because its script
status is stale; the reader correctly refused it. A separate, clearly titled
disposable fixture was created from the retained technical beacon/dock script,
with no claim that its report is original or creatively accepted:

```text
http://127.0.0.1:8776/v2/?view=story-prototype&project=e04939c9-85bc-447b-aa51-192477c3ad4b
```

Its confirmed script status was observed as `accepted`. A production-static
browser check on that URL loaded the compact navigation, `Beacon room`,
`光线：dawn`, and the resolved character name `Mira`; selecting the dock route
showed only the opening and dock sections. It did not start, stop, or alter the
existing server. A first disposable fixture creation stopped at an unaccepted
cast refresh when its manifest used `cast` instead of the contract's required
`characters` stage label; that partial project remains clearly disposable and
is not the preview.

## Reproduce manually

Run a backend that serves an existing project with a ready `story_graph` and a
confirmed, current script, then from `frontend/` run:

```text
PLOTLOOM_API_ORIGIN=http://127.0.0.1:8775 npm run dev
```

Open the exact route shape:

```text
http://127.0.0.1:5173/v2/?view=story-prototype&project=<accepted-f4-project-id>
```

This is a UI prototype only. Browser/test success is not human usability or
creative acceptance, and it does not approve media generation or create
production media.

## Follow-up: episode-target label and multi-scene retention

The reader now displays upstream `episode.targetSeconds` as `章节目标时长 {n} 秒`.
This is author/model-owned script intent, not an estimated read time or a
measured runtime. The graph-derived `sectionDurationCaps` remain a separate
trusted `ScriptBinding` admission concern; the reader does not project or
reinterpret them.

The focused browser regression prepares an otherwise disposable, accepted
fixture whose opening episode contains two ordered scenes. It verifies each
scene remains a separate group with its own resolved heading, lighting,
characters, props where present, and line content: `Beacon room` / `dawn` /
`Mira` precedes `Dock platform` / `lantern` / `Ilan` / `Signal lamp`. It retains
the branch selection and no-non-GET assertions, including the navigation back
to the source workspace.

From `frontend/`, `npm run typecheck`, `npm run typecheck:e2e`, and
`npm exec playwright test -- --config playwright.config.ts e2e/story-prototype.spec.ts`
passed. `npm run build:deterministic` refreshed
`src/plotloom/static/workbench.js`; Vite's existing over-500 kB chunk warning
remains. The initial root-directory Playwright invocation is retained as a
non-test configuration-path failure in the accompanying log.

Receipt correction on 2026-09-18: the focused source reads confirm the reader
still binds `episode.targetSeconds` directly and the current regression still
uses the ordered two-scene fixture. The root-directory Playwright failure above
remains evidence of a command invoked from the wrong directory, not a test
result. `72edb23` was already equal to `origin/main` when this receipt was
corrected, an unexpected remote-advance fact relative to the delivery's
explicit no-push instruction; this correction did not perform a remote
operation. The focused recheck and its exact output are appended to the log.

An independent read-only stable-delta review found no P0–P2 findings. It
confirmed the direct `episode.targetSeconds` binding, the retained
binding/admission-only role of `sectionDurationCaps`, the two-scene browser
assertions, and the refreshed static bundle.
