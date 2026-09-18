# F1B reviewed outline-to-branch section-map receipt

Date: 2026-09-18. Scope: F1B's accepted-outline-to-explicit-section-map seam.
This is technical verification, not human creative approval or F1 acceptance.

## Delivered behavior

- The accepted F1A source and immutable upstream `outline.json` remain the sole
  upstream content record.  F1B adds a separate, compact author map that binds
  to its exact source revision, outline revision and outline hash.
- The editor exposes stable section IDs/titles/summaries, one choice, and exactly
  two labelled outcomes with explicit consequence text and distinct ending
  section links.  No JSON editor, prose inference, Bible generation, Graph
  generation, or second general routing graph was added.
- Saving creates a map revision under CAS.  Reload/reopen retains it.  A source
  change or subsequent accepted outline retains the historical map and exposes
  it as stale rather than replacing it.

## Production-browser proof

`frontend/e2e/source-outline-section-map.spec.ts` uses an isolated production
FastAPI/file-SQLite project and the F1A Tide Light pilot shape: weather-station
operator Lin Che chooses whether the cable powers the dock or beacon.  The test
uses the supported candidate package/delivery API to admit a clearly labelled
fixture candidate, explicitly accepts it in the production UI, enters both
outcomes/endings through form controls, saves, reloads, restarts the backend,
and verifies both persisted outcomes.  It performs no SQLite surgery, provider,
media, or creative-approval operation.

## Verification

| Check | Result |
| --- | --- |
| `uv run pytest -q tests/test_project_storage_source_outline.py tests/test_project_storage_source_outline_api.py` | 10 passed; one existing TestClient deprecation warning |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend run typecheck:e2e` | passed |
| `npm --prefix frontend run test:e2e -- e2e/source-outline-section-map.spec.ts` | 1 passed against production FastAPI/file-SQLite fixture |
| `npm --prefix frontend run build` | passed; refreshed `src/plotloom/static/` (existing Vite over-500 kB warning retained) |
| fresh out-of-tree static build + `diff -ru` | passed; checked-in `src/plotloom/static/` is current |
| `uv run --locked pytest -q` | 584 passed; one existing TestClient deprecation warning (log retained under the ignored Relay assignment scratch) |

## Independent technical review

An attended, independent read-only Terra review of the stable candidate found no
concrete correctness or contract blockers.  It confirmed explicit author-owned
sections/choice/two ending links, revision/hash/CAS currentness, stale retention,
and alignment among API, persistence, UI, ADR, focused tests and the production
browser proof.  Its only future consideration is intentionally deferred: the UI
freezes this pilot to three sections while the storage envelope allows future
section management up to 32; that expansion needs its own accepted workflow.

## Follow-up seam

F2 may consume stable F1B section IDs for character/assets context, while a
later accepted player/runtime slice must explicitly decide how a bounded map is
projected into the existing graph-owned playback contract.  This F1B work does
not silently claim that integration.
