# F1B reviewed outline-to-branch section-map receipt

Date: 2026-09-18. Scope: F1B's accepted-outline-to-explicit-section-map and
canonical-route-admission seam.
This is technical verification, not human creative approval or F1 acceptance.

## Delivered behavior

- The accepted F1A source and immutable upstream `outline.json` remain the sole
  upstream content record.  F1B adds a separate, compact author map that binds
  to its exact source revision, outline revision and outline hash.
- The editor exposes exactly three sections: one stable entry/choice section
  and two stable ending sections. Choice/outcome/routing IDs freeze after first
  save while text remains editable. No JSON editor or prose inference was added.
- Saving creates a map revision under CAS. Reload/reopen retains it. A source,
  accepted-outline, or map change retains historical input and marks only its
  installed graph and actual downstream consumers stale rather than replacing
  unrelated graph ownership.
- An explicit install atomically binds exact source/outline/map revisions and
  hashes plus canonical graph CAS. It compiles the current map into the existing
  `StoryGraphV2`: the entry is START, the two authored endings are ENDINGs, and
  the two author labels/consequences become CHOICE edges. The compact admission
  receipt points at this canonical graph revision; it stores no duplicate route
  state. Bible/entity effects and any provider/media work remain inapplicable.

## Production-browser proof

`frontend/e2e/source-outline-section-map.spec.ts` uses an isolated production
FastAPI/file-SQLite project and the F1A Tide Light pilot shape: weather-station
operator Lin Che chooses whether the cable powers the dock or beacon.  The test
uses the supported candidate package/delivery API to admit a clearly labelled
fixture candidate, explicitly accepts it in the production UI, enters both
outcomes/endings through form controls, saves, explicitly installs the canonical
graph, verifies both existing graph-derived route cards/choice labels, reloads,
restarts the backend, and verifies persistence. It performs no SQLite surgery,
provider, media, or creative-approval operation.

## Verification

| Check | Result |
| --- | --- |
| `uv run pytest -q tests/test_project_storage_source_outline.py tests/test_project_storage_source_outline_api.py` | 12 passed; one existing TestClient deprecation warning |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend run test` | 159 passed |
| `npm --prefix frontend run typecheck:e2e` | passed |
| `npm --prefix frontend run test:e2e -- e2e/source-outline-section-map.spec.ts` | 1 passed against production FastAPI/file-SQLite fixture; installs and verifies both canonical routes after backend restart |
| `npm --prefix frontend run build` | passed; refreshed `src/plotloom/static/` (existing Vite over-500 kB warning retained) |
| fresh out-of-tree static build + `diff -ru` | passed; checked-in `src/plotloom/static/` is current |
| `uv run --locked pytest -q` | 584 passed; one existing TestClient deprecation warning (log retained under the ignored Relay assignment scratch) |

## Independent technical review

An attended, independent read-only Terra review approved the stable candidate.
It verified the exact-three immutable-ID envelope; START/two-ENDING/two-labelled
CHOICE compilation with consequence traceability; atomic source/outline/map
hash-and-revision plus graph-CAS binding; unrelated-graph preservation; scoped
staleness; and route cards gated to the matching admitted canonical graph
revision. The reviewer did not independently rerun commands. Its scope is the
graph-admission contract, not F1 human creative approval.

## Follow-up seam

F2 may consume stable F1B section IDs for shared character/assets context. F1B
does not claim human creative approval or produced-media Play acceptance.
