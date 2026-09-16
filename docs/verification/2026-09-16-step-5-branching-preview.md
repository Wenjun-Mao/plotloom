# Step 5 branching-preview receipt

## Scope and implementation

The authorized minimal structural author preview has source-level implementation
work. It uses the intended
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

## Source and focused-check evidence

- `npm --prefix frontend run test -- --run tests/video-pilot.test.ts` — 14
  focused tests pass for both branch choices, one-choice decisions, final hold,
  new-episode restart, missing/corrupt media, duplicate events, and reset/pause
  boundaries. These tests use DOM events and do not establish native playback.
- `npm --prefix frontend run typecheck` and `npm --prefix frontend run
  typecheck:e2e` passed for the candidate before browser work began.
- Existing FastAPI/browser production regression `frontend/e2e/video-pilot.spec.ts`
  retains its local-H3 downloaded-MP4 native-ended selected-pair playback proof;
  it now also confirms the Step 5 player and its honest missing-media state on
  that page. The retained two-clip pilot still lacks four route clips.
- The existing selected-pair browser test remains a separate Step 4 proof only;
  it does not exercise a complete branching journey.

## Native branching failure preserved

`frontend/e2e/branching-video-preview.spec.ts` is retained as the production
FastAPI offline fixture. It creates a canonical four-node graph, obtains four
selected H3 fixture clips through the normal project routes, confirms a ranged
media response, and requires native start → decision → both selected endings
across a restart. It does not inject `ended` events.

The fixture's canonical-admission and response-identity mistakes were corrected
before native playback was assessed. The first genuine browser journey showed
the start clip reach its native end and the decision media mount, but the decision
remained at `currentTime = 0`. A second bounded lifecycle attempt preserved a
more direct diagnostic: after the explicit start-button click, the served clip
reported `readyState: 4`, `duration: 5.166667`, `networkState: 1`, `error: null`,
`paused: true`, and `currentTime: 0` after nine seconds. This establishes a
browser lifecycle capability boundary rather than absent, corrupt, or unserved
fixture media. The fixture currently records no `play`/`playing`/`pause` event
trace and no direct play-promise outcome, so it cannot distinguish browser/
fixture policy from an external DOM owner; it must not be described as a proven
player-ref defect. The failing test and Playwright error context remain the
executable diagnostic; no successful final-frame screenshot exists to retain.

One attended independent Terra read-only review examined the exact media ref,
identity cleanup, and click path. It found no remaining scoped frontend
lifecycle cause: cleanup captures the superseded committed element, and the
initial click does not change media identity. It recommended no further source
mutation under the stop condition; a future authorized investigation needs
browser event/promise telemetry or parent/DOM-owner inspection.

Per the bounded-delivery stop condition, no third native-playback attempt was
made. No provider, upload, paid call, retained-pilot mutation, or deployment was
used for this work.

## Acceptance status

This receipt does **not** establish fixture verification or Step 5 acceptance.
The retained pilot has missing route footage, and the player also needs a newly
authorized lifecycle correction followed by fresh browser proof before any
creative-media review can be considered.
