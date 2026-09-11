# P1 self-contained copied-brief correction — verification receipt

Date: 2026-09-11  
Scope: the P1 copied-job acceptance gap only. This is a local implementation
candidate, not director acceptance, a production release, or a new ImageGen run.

## Root cause and contract correction

The initial P1 pilot proved manual image-job transport and one actual original /
refinement pair, but its copied refinement package did not contain the creator's
facial-clarity/practical-lighting direction or the resolved authored facts needed
to act on the Shot. The specialist received those points outside the package.
That violated the intended copied-brief boundary rather than being a missing UI
label.

The correction moves the contract to trusted preparation:

- the creator must enter a nonblank presentation/refinement change before
  preparation; it is hashed in the frozen snapshot without granting authority to
  alter canonical narrative facts;
- a refinement derives the current reviewed-keyframe binding and its exact,
  role-specific VisualIntent ID/revision from trusted storage, then freezes both
  that identity and the intent payload;
- the package includes only the Shot's resolved scene/beat/cue,
  character/location/prop and required-state records, plus required reference
  roles/bytes—never unrelated project data or secrets;
- v2 packages include and revalidate `completion-manifest.example.json`, and the
  copied assignment names it explicitly; historical v1 packages remain readable
  and recheckable without migration;
- a newer role-specific VisualIntent revision after Copy makes that refinement
  inapplicable. Refresh preserves its late receipt but publishes no candidate.

[ADR 0028](../adr/0028-agent-operated-image-jobs.md) now records this ownership
and currentness contract. The [P1 plan](../roadmap/p1-image-generation-plan.md)
remains **Approved — revision 2** with implementation and acceptance kept
separate.

## Browser and package regression

`frontend/e2e/image-jobs.spec.ts` runs against a real FastAPI process, a
file-backed SQLite database and a test-owned same-host exchange root. It:

1. prepares and Copies an original brief through the browser;
2. asserts the v2 request contains the explicit creator direction, resolved
   character/location/prop/cue context, and completion-manifest template;
3. writes the retained P0 evidence image
   `docs/verification/supporting/p0-generated/01-arrival.png` as a declared
   specialist delivery, then uses browser Refresh and explicit intent/selection;
4. prepares, Copies and Refreshes a valid refinement, asserting the frozen
   reviewed VisualIntent binding/revision and required parent-output role; and
5. Copies a second refinement, changes that intent through the normal browser
   editor, then Refreshes its retained-asset delivery and observes an
   `inapplicable` receipt with no candidate.

The retained bytes are deliberate regression input only. No new ImageGen call,
batch, provider bridge, credential, remote request, or creative-quality claim
was made for this correction.

## Focused verification

- `uv run pytest tests/backend_core/test_image_jobs.py -q` — `8 passed`.
  The fixture uses admitted canonical cue timing and verifies package integrity,
  resolved context, v2 template, exact refinement binding and post-Copy intent
  invalidation alongside existing delivery safety cases.
- `npm run typecheck` and `npm run typecheck:e2e` in `frontend/` — passed.
- `npm run test:e2e -- image-jobs.spec.ts` in `frontend/` — `1 passed`.

## Stable-candidate gates

- `uv run --locked pytest -q` — `542 passed, 9 skipped, 272 warnings`.
- `npm test`, `npm run typecheck`, and `npm run typecheck:e2e` in `frontend/`
  — `120` unit tests and both TypeScript checks passed.
- `npm run build` in `frontend/` — passed and regenerated the checked-in
  `src/plotloom/static/workbench.js` bundle. Vite emitted its pre-existing
  >500 kB chunk-size advisory only.
- `npm run test:e2e` in `frontend/` — `25 passed`, including the new P1 journey.
- `uv build --wheel` and `uv run python scripts/smoke_installed_wheel.py dist`
  — passed from an isolated installed wheel.

Director acceptance is intentionally not claimed here.
