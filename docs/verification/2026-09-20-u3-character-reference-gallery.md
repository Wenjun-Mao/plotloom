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
- `npx playwright test --config playwright.config.ts e2e/cast-reference-studies.spec.ts`
  — 3 production FastAPI/file-SQLite browser journeys passed.
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

## Walkthrough availability

No persistent walkthrough URL is supplied. Read-only inspection found no
running retained Plotloom server or existing compatible retained project. The
only safe compatible proof available in this checkout is the supported
production FastAPI/file-SQLite fixture, whose roots are deliberately temporary
and whose retained raster is explicitly non-generated test evidence. Creating
a persistent project/output root merely to publish a URL would write outside
this assignment's approved scope and would not be a truthful existing-project
walkthrough. H3 remained disabled throughout; no provider or gateway call was
made.

## Product acceptance boundary

The browser and visual evidence verifies the presentation contract. It does not
constitute creative acceptance of any image, approval of any candidate, or an
attended user walkthrough of U3/U4.
