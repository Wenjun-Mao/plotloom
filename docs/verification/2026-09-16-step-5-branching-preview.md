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

## Gated browser evidence

The earlier production failure reported media readiness but not the imperative
`play()` promise, native events, or committed-element lifetime. The current
bounded proof therefore tested those layers in order, with the same established
offline H3 fixture bytes. The fixture gateway writes only to its own temporary
directory; no new footage or retained pilot media was created or changed.

1. `frontend/e2e/native-video-probe.spec.ts` first serves those bytes from the
   Vite origin through a test-local route and mounts one plain `<video>` plus
   one `Play` button with `page.setContent`. It neither creates a project nor
   mounts Plotloom's React player. A real click produces `play`, `playing`, a
   resolved `play()` promise, progressing `currentTime`, and a native `ended`
   event on the same connected element.
2. Its second test stays isolated and proves the smallest reusable sequence:
   one video reaches its final hold, an explicit A/B click alone selects the
   next playback, restart resets to time zero, and both endings reach native
   end. It does not synthesize media events or introduce a graph/runtime model.
3. `frontend/e2e/branching-video-preview.spec.ts` then exercises the real
   FastAPI project route, canonical four-node graph, four selected offline-H3
   jobs, and the committed structural player. Browser-side test telemetry
   records attachment/removal, `play()` call/result, and native media events.
   The verified journey is explicit start → native-ended ordinary successor →
   decision hold → A ending → restart with a new media identity → B ending.
   All six real `play()` calls resolved and all six distinct session identities
   reached native `ended`; no play rejection occurred. The test retains the
   old-element handles and proves each superseded start, successor, and ending
   is paused and disconnected. Its telemetry records the six distinct identities
   that actually play and end, while also observing the mounted and removed
   lifecycle identities (development StrictMode may remount an identity). The
   test retains its final screenshot.

## Checks run on this candidate

- `npm --prefix frontend run test -- --run tests/video-pilot.test.ts` — 14
  focused structural-player tests passed.
- `npm --prefix frontend run typecheck` and `npm --prefix frontend run
  typecheck:e2e` — passed.
- `npm --prefix frontend run test:e2e -- --grep 'plain same-origin offline H3
  video plays|isolated native video choice sequence'` — both isolated browser
  rungs passed.
- `npm --prefix frontend run test:e2e -- --grep 'production FastAPI fixture
  plays both native-ended branches and resets an episode'` — passed with the
  lifecycle telemetry above.
- `npm --prefix frontend run build:deterministic` — passed; generated static
  assets were already current.

The separate Step 4 selected-pair browser test remains a retained regression
only; it does not replace this complete four-node fixture. No provider, upload,
paid call, retained-pilot mutation, deployment, or creative-media work was used.

## Acceptance status

This receipt establishes the bounded structural-player implementation and native
browser proof. It does not claim a complete produced story, retained-pilot
coverage, creative/media qualification, Alpha readiness, or release. Step 5
remains pending director acceptance of this evidence.
