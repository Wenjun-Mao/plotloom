# M1 playable story view receipt

Date: 2026-09-16. Scope: checkpoint 1 only from
[Playable MVP milestones](../roadmap/playable-mvp-milestones.md). This receipt
records implementation and verification, not director acceptance, push, M2
readiness, new generation, or a new audio judgment.

Director acceptance: `6941f2e` accepted after source, retained visual evidence and
Relay verification review. Recorded final checks include 557 Python tests and
158 frontend tests passing. The bounded M1 viewing outcome is accepted, not M2;
the departure defect and prior user-attributed audio approval remain unchanged.

## Gap map and decision

Before this slice, `BranchingVideoPreview` already projected canonical graph,
storyboard, scene beats and selected current video jobs, including native media
ended/error handling, explicit branch choices and restart. It was mounted only
inside the storyboard media workbench. The gap was therefore a discoverable,
reopenable viewing surface rather than another player, graph, manifest, or media
API.

`?project=<id>&view=play` now selects a small Play composition before the
workspace mounts. It reads only the existing project, stage and video-job APIs;
it owns no persisted playback data and creates no authoring draft or media
authority. The workbench top bar exposes **播放故事**. Loading, request failures,
missing stage content and the player's existing missing-media/native-media error
states stay visible in this surface. The player gained only display labels so
the workbench keeps its existing preview wording. ADR 0052 records the related
one-time selected-media transition admission correction.

The retained project's immediately preceding selection schema exposed a startup
ordering fault: startup recovery inspected it read-only before the approved
writable transition could run. `ProjectRunDispatcher` now uses the normal
admitted active-project open before recovery or index inspection; a closed
legacy folder stays excluded until explicit Open. This changes neither selected
bytes nor historical reviews and is covered by a production-runtime regression.

## Retained-pilot proof

Project: `4d7d4856-e407-4467-9432-3d9187b9edf8` — **末班车的银色吊坠**.
The production server served the freshly built static workbench at the direct
Play URL. An attended native Google Chrome session opened that URL despite the
browser-provider inventory omitting Chrome, displayed the clean Play view, and
progressed opening → decision → return branch. Its transient AX text “Unable to
play media” was not treated as media failure.

Passive native-video state from the headed browser session established the
decision, return and departure clips at `currentTime: 5.167`, `ended: true`,
`paused: true`, `error: null`, with the expected current media URL. Both choice
buttons appeared only after the decision completed, and both endings showed the
restart control. After normal `POST /close` then `POST /open` (operational
revisions 4 then 5), all four selected/current job IDs and their retained hashes
were unchanged. A reload of the same direct Play URL then completed both return
and departure paths again with the same terminal native state.

The retained audiovisual approval remains the user's prior approval. In
particular, this work makes no fresh audio judgment and does not revise the
known intermittent departure-face limitation.

![Retained departure ending in Play view](assets/m1-play-retained-departure-ending.png)

Screenshot SHA-256:
`1e7c36a75c3619638a4530f8f7bac0483c2d56a09df0793cb28429b36ee0db01`.

## Automated evidence

- `npm run typecheck` — passed.
- `npm test` — 16 files, 158 tests passed.
- `npx playwright test --config playwright.config.ts e2e/branching-video-preview.spec.ts`
  — passed. The production FastAPI/file-SQLite fixture enters the shipped
  FastAPI `/v2` static Play URL directly (not Vite), asserts no workspace shell,
  validates real `currentTime`/`ended` media state, both endings and restart,
  then normal close/open, reload and repeats both paths.
- `uv run --locked pytest tests/test_production_project_folder_runtime.py -q`
  — 7 passed. This includes the startup transition regression.
- `npm run build` — passed; generated `src/plotloom/static/workbench.js` and
  `workbench.css` are current. Vite reported its existing >500 kB bundle warning.

An independent Terra review found and corrected the production-static browser
coverage gap; it found no other concrete issue. The full browser suite, locked
Python suite and installed-wheel smoke are recorded from the final candidate
before handoff.
