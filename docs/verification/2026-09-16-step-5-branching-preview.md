# Step 5 branching-preview receipt

## Scope and implementation

Implemented the authorized minimal structural author preview. It uses the
canonical StoryGraph start node, scene/shot ordering, and only current,
explicitly selected, ingested video jobs. Node-local media plays in order,
ordinary one-successor nodes may continue automatically, decision nodes retain
their final frame and require a click on a canonical outgoing edge, and endings
retain their final frame with an explicit restart. Missing selected media and a
media load/corruption error are blocking gaps; neither is skipped or generated.

The session is browser-local and never writes canonical state. Its graph/order/
selected-media identity is a reset boundary; stale ended events and repeated
choice clicks are ignored, and replaced/unmounted media is paused. The preview
does not execute edge effects or join reconciliation prose/JSON. A reached
shared node is structural reuse only, not stateful published-runtime behavior.

## Evidence

- `npm --prefix frontend run test -- --run tests/video-pilot.test.ts` — 13
  focused tests pass: both branch choices, one-choice decisions, final hold and
  restart, missing/corrupt media, duplicate ended/click events, and reset/pause
  boundaries.
- `npm --prefix frontend run typecheck` and `npm --prefix frontend run
  typecheck:e2e` pass; `npm --prefix frontend run build:deterministic` refreshed
  `src/plotloom/static/`.
- Existing FastAPI/browser production regression `frontend/e2e/video-pilot.spec.ts`
  retains its local-H3 downloaded-MP4 native-ended selected-pair playback proof;
  it now also confirms the Step 5 player and its honest missing-media state on
  that page. The retained two-clip pilot still lacks four route clips.
- Independent Terra read-only review found and the implementation repaired: a
  one-edge decision auto-advance, session media cleanup, and corrupt-media
  gap reporting. The re-review reported no material remaining finding.
- `uv build --wheel --out-dir .local/relay/1e5693db-0798-42ef-ad16-d7328950fc44/wheel-BpCrM4`
  plus `uv run --locked python scripts/smoke_installed_wheel.py <wheel-dir>`
  passed in a fresh isolated installation.

## Browser-evidence boundary

An attempted standalone four-job branching FastAPI/browser fixture was not
retained: the local H3 browser media element loaded but did not advance under
that synthetic multi-job setup, including when `play()` was invoked directly.
It therefore cannot honestly evidence a full native-ended branching journey.
The focused DOM tests use test-only fixture jobs and native-style events; they
are implementation verification, not produced-story acceptance. No provider,
upload, dispatch, paid call, or retained-pilot mutation was used for Step 5.

## Acceptance status

This receipt establishes the bounded implementation and fixture verification,
not full live branching audiovisual acceptance. The retained pilot has missing
route footage, and a complete produced branching story needs a separately
authorized media/creative review once that footage exists.
