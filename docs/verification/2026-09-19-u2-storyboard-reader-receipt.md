# U2 route-focused storyboard reader — verification receipt

Date: 2026-09-19

## Scope and authority

This is the approved read-only U2 usability slice only: a Chinese reader over the
current accepted F4 script, F5A storyboard-review evidence, and canonical graph.
It is not creative/media/M2 approval and does not introduce production shots,
SceneBeats/Bible projection, provider work, or source-data mutation.

## Root-cause and contract change

The retained story reader admitted F4 script plus graph but did not consume F5A;
therefore it could not present storyboard evidence and could not prove the two
surfaces belonged to one current binding. The fix belongs at the reader admission
contract, not in a downstream display fallback: it rejects absent/stale/reopened or
binding-mismatched F4/F5A/graph state before rendering, while the canonical graph
continues to own route order and F4 continues to own script facts.

## Verification

- `npm run typecheck` — passed.
- `npm test -- --run tests/model.test.ts` — passed: 13 tests.
- `npm run typecheck:e2e` — passed.
- `npx playwright test --config playwright.config.ts e2e/story-prototype.spec.ts` —
  passed: 2 tests. It uses the production FastAPI browser surface and a clearly
  disposable deterministic fixture; the reader made no non-GET API request.
- `npm run build:deterministic` — passed; refreshed
  `src/plotloom/static/workbench.{js,css}`.
- Wide (1440 px) and narrow (768 px) screenshots were captured by the focused
  browser proof and visually inspected. The narrow layout collapses cut metadata
  without clipping; generation instructions are closed by default.

## Independent review

An independent Terra read-only stable-delta review found no runtime-blocking issue:
currentness admission, graph-owned order, prompt disclosure, missing-media honesty,
and sandboxed upstream-report isolation are all present. It identified two coverage
gaps (graph/section binding mismatch and F5A sibling-route exclusion); both were
added to the focused model/browser proof and rerun successfully. It also noted that
ADR 0067 describes the preceding F4-only reader. This bounded U2 prototype change
is recorded here and in its approved roadmap receipt; the broader ADR/rearchitecture
is outside this slice rather than silently expanded here.
