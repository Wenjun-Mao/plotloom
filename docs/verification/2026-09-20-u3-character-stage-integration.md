# U3 Characters-stage integration — technical verification receipt

Date: 2026-09-20. Scope: accepted cast text review and F2B image-reference
review only. This is technical evidence, not creative approval or the pending
attended creator-usability acceptance.

## Root cause and delivered boundary

The standalone gallery made image comparison readable but gave the creator no
coherent task because its selection/refinement decisions were elsewhere. The
new `stage=characters` workspace entry keeps F2A cast review and the reused
image-first F2B view in one hierarchy. It retires the standalone gallery route,
its duplicate creator navigation and `CastReferenceStudiesPanel`; it does not
change the API, schema, asset, proposal, decision, Art, screenplay, storyboard
or Play owners.

Viewing calls only GET owners. Explicit image-adjacent controls retain existing
selection CAS/reviewer/notes and prepare/copy/refresh/cancel requests. Prepare
is a manual handoff, not provider dispatch. Stale/reopened cast disables new
work while retaining evidence, and selected/current candidate/historical/missing
and failed states remain differentiated.

## Executed checks

- `npm test` — 19 files / 169 tests passed.
- `npm run typecheck` and `npm run typecheck:e2e` — passed.
- `npx playwright test e2e/cast-reference-studies.spec.ts --config playwright.config.ts`
  — 4 production FastAPI/file-SQLite scenarios passed: original → refinement →
  selection across reload/restart; prepare/export/cancel and late inapplicable
  delivery; stale cast and held operation ownership; delayed project-read
  invalidation.
- `npm run build:deterministic` and `git diff --exit-code -- src/plotloom/static`
  — passed; built frontend assets are fresh.

## Walkthrough environment

A separate H3-disabled production service is retained at
`http://127.0.0.1:49072/v2/`, using only
`.local/relay/ef469f97-f8f0-4cf0-8d63-6b67e4c9638a/characters-walkthrough/`
for application data and outputs. Fixture project
`e31b1149-edb6-4611-b76c-accd4210fc22` was created through the production API,
then uses a labelled retained P0 raster as its selected technical reference and
a prepared-then-cancelled refinement. It visibly demonstrates current selected,
failed delivery, cancelled handoff and recognizable parent lineage. No provider
or ImageGen call was made. The previously director-owned preview and its
persisted roots were not modified.
