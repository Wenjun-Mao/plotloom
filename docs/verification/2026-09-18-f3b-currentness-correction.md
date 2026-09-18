# F3B currentness correction receipt

Date: 2026-09-18. Baseline: `2ec491d32634e7a2ce3d70256963b0309976917b`.

## Finding and correction

The original F3B technical proof changed accepted `art.json`, but did not prove
that F3B consulted the canonical art owner's complete currentness contract.
The F3B proposal owner had independently checked only `ArtHeadRow.status` and
revision. Consequently, a source, outline, map, graph, or cast change could
make `ProjectArtPersistence.get_state()` stale without changing the art head,
leaving an F3B proposal wrongly current.

The correction adds one session-local `ProjectArtPersistence` admission for a
current accepted scene/prop. It reuses the art owner's existing complete
binding comparison, and F3B calls it inside its own read/write transaction for
prepare, package-copy/export, list currentness, and delivery admission. No
nested session or duplicated binding logic was introduced. Delivered managed
assets remain historical evidence; a late pending delivery becomes
`inapplicable` and publishes no candidate.

The frontend now gives the F3B study component its own project/art epoch. A
response held for an earlier visit to project A cannot set assignment/error,
refresh, or busy state after A → B → A ownership changes. The user-facing F3A
copy now says that F3A itself is text-only while the visible F3B surface owns
reference bytes and their currentness.

## Unmount ownership addendum

The earlier project/art-epoch proof did not invalidate the parent or child
session token when the source-stage navigation unmounted `ArtPanel`. A held
copy response could therefore pass the old child's token check after unmount
and invoke its captured parent `refresh` callback. React discards its state
update, hiding the assignment/error symptom, but the stale refresh request was
still real. This is a frontend callback-ownership defect; it does not alter
the complete-current-art backend admission or either retained study.

The follow-up invalidates the exact active parent project token and child
project/art token in their effect cleanups. Identity checks make repeated
StrictMode cleanup/re-setup safe: cleanup only retires the session it captured,
and the subsequent setup uses the new epoch. The production A → B → A test now
waits for the held copy response and browser network-idle settlement before
asserting that no stale proposal refresh, assignment, or error appears. A
focused deferred-promise React test directly proves the unmounted callback
cannot refresh after its promise settles. This addendum does not reinterpret
the earlier proof or change the transition-policy disposition below.

## Transition policy disposition

`2ec491d` introduced the narrow F3A-to-F3B schema transition for exactly
format-9 project SQLite databases whose otherwise-current schema lacks only
`v2_art_reference_proposals`, `v2_art_reference_proposal_deliveries`, and
`v2_art_reference_proposal_candidates`. Its source roots are
`src/plotloom/project_storage/video_candidate_transition.py`, the project
open/recovery callers, and the three named tables. The only exercised case in
the retained test is a disposable fixture with those tables manually absent;
this correction did not run a transition against retained project data.

The exact one-time additive transition is retained unchanged pending director
disposition: it may be needed for valued F3A folders created immediately before
F3B, but current evidence does not establish that any retained folder needs
it. No retained data was deleted or migrated, and no broader compatibility
layer was added.

## Executed proof

- `uv run --locked pytest -q tests/test_project_storage_art.py` — passed: 5.
- `npm run typecheck && npm run typecheck:e2e` in `frontend/` — passed.
- `npm exec -- playwright test --config playwright.config.ts e2e/art-review.spec.ts --grep 'A-to-B-to-A'` in `frontend/` — passed: 1 production-browser regression.
- `npm exec -- playwright test --config playwright.config.ts e2e/art-review.spec.ts --grep 'F3B shows current' --repeat-each=2` in `frontend/` — passed: 2 production-browser lifecycle/currentness replays.
- `npm run build` in `frontend/`, followed by an out-of-tree production build and `diff -ru src/plotloom/static <out-dir>` — passed; checked-in static assets are fresh. Vite retained its existing >500 kB chunk warning.
- Independent Terra read-only review — no P0–P2 findings. It separately confirmed the current-subject transaction boundary, the A → B → A epoch guard, regression coverage, and the limited transition-policy caveat above.

### Unmount addendum verification

- `npm exec -- vitest run --config vitest.config.ts tests/art-panel-ownership.test.ts` in `frontend/` — pre-fix failed with an extra `getArt` call after the deferred copy settled; passed after cleanup invalidation.
- `npm run typecheck && npm run typecheck:e2e` in `frontend/` — passed.
- `npm exec -- playwright test --config playwright.config.ts e2e/art-review.spec.ts` in `frontend/` — passed: 6 production-browser journeys, including currentness/restart/cancellation, the existing lifecycle path, and A → B → A after held-copy response and continuation settlement. The lifecycle assertion now first waits for the mounted prepare callback's refresh, avoiding a direct-request race with its local writer; this is not a human creative approval.
- `npm run build` in `frontend/` — passed twice with identical checked-in static hashes (`workbench.js` `e80886d08775627ac2d99382db13c41c52f3026c7bb8763d074ab02f5b9bde37`, `workbench.css` `176bcb1bafd4a036ac058b788e2023fc23a4bcab9fd86a18304dcd892d35c8ef`, `index.html` `f9bd0c147d0cbef3d4c97a5aafaee1ac0b0d14e2ef7758561ec3e0746395cebe`). Vite retained its existing >500 kB chunk warning.
- Independent attended Terra read-only delta review — no P0–P2 findings. It confirmed the exact parent/child cleanup identity checks, StrictMode cleanup/re-setup, direct deferred-settlement proof, production response-settlement evidence, mounted copy/refresh coverage, and static hash above. The DOM assertions after unit unmount are secondary; the no-post-settlement API-call assertion is the direct guard.

No ImageGen/H3 calls or pilot mutations were made for this correction.
