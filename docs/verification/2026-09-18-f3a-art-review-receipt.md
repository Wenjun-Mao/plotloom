# F3A novel-art review receipt

Date: 2026-09-18. This is technical workflow evidence, not human creative
acceptance, generated media, or F3B reference qualification.

## Delivered

- Source/map/graph/cast-bound F3A candidate, acceptance, reopen/save and cancel
  lifecycle owner; all records freeze revision/hash and reject stale/late work.
- Text-first production panel with handoff copy, refresh/cancel, raw `art.json`
  inspection/editing, sandboxed report, explicit acceptance, reopen/save, and
  an explicit no-image/no-selected-asset statement.
- The pinned `novel-art` validator and renderer remain the semantic/report
  tools; Plotloom validates identity, provenance, lifecycle and currentness.

## Historical attended isolated proof

The older F2A/F2B retained project roots at
`.local/relay/*/f2b-live-proof/` were read only and preserved. The current
runtime refuses their superseded video-selection schema, so an isolated current
project under `.local/relay/82991c84-9d63-4400-b30f-69fa23cd1099/live-proof/`
was re-entered from the retained source facts. It contains source r1, outline
r1, section map/installed graph r1, and cast r1.

In the production browser, the author prepared and copied art handoff
`ch_0a2f954fd14449f299b8b2de4a596152`; a Terra high-reasoning specialist
candidate produced two source-bound scenes (`S01`, `S02`) and one prop (`P01`).
Pinned `novel-art validate --cast` passed: `2 个场景 + 1 件道具全部通过校验`.
The generated HTML report and completion manifest preserve the package pin,
candidate hash `d3d732f9391142025b0811066eca5c65a3070e47a551946fa4fdb20a8dcfdb69`,
and no-media limitations. The UI refreshed and inspected the candidate,
explicitly accepted r1, reopened it, edited only text while preserving IDs, and
saved r2 (`2f91d782f818…`). Browser reload and backend restart still visibly
reported accepted art r2. No ImageGen, H3, video, or selected asset occurred.

This is historical attended evidence, not the missing committed regression for
the runtime corrected from `96557331537b22023fd4c80bb8bd32ca6d16cec4`.
The older F2B roots do not prove the current F3A browser path; their role here
is limited to explaining the isolated fixture's source facts.

## New production-browser regression

Source correction: `bfc2b57eb25a074236db37f82cb7ae2d2525e553`.

`frontend/e2e/art-review.spec.ts` starts the production FastAPI composition
against a test-owned file-SQLite project folder, with Vite and Playwright. It
uses a real accepted source, outline, section map, installed graph, and cast;
the only external seam is writing an upstream-valid `art.json` package into the
actual frozen delivery folder. It does not monkeypatch art ownership or fake an
acceptance response.

The four browser journeys prove:

- prepare → reload → re-copy of the same frozen package, ready rejection/cancel,
  and a distinct replacement job;
- author edit/explicit accept, current accepted JSON inspection without reopen,
  an original-report warning after the edit, reopen/save r2, reload, and backend
  restart;
- prepared-publication snapshot/close blocking, then cancellation, close, and
  explicit reopen; and
- a held old-project prepare response cannot alter the destination project's
  art panel.

The regression also asserts that only the established graph stage is populated:
no Story Bible, scene-beats, or storyboard is created. The accepted JSON is now
rendered read-only outside reopen; reopening changes edit authority only. This
fix implements ADR 0062's existing requirement that accepted art remains
readable, rather than changing art ownership or report provenance.

## Verification

- `node third_party/shuohao-skills/skills/novel-art/scripts/novel-art.mjs validate … --cast …` — passed.
- `uv run pytest tests/test_project_storage_art.py tests/test_project_storage_cast.py -q` — 4 passed.
- `npm run typecheck` and `npm run build` — passed; the pre-existing >500 kB
  chunk warning remains. Build refreshed `src/plotloom/static/`.
- `npm run typecheck:e2e` — passed.
- `npm exec -- playwright test e2e/art-review.spec.ts` — 4 passed. Raw output
  and the initial failure traces are retained under the ticket's ignored
  `.local/relay/3714b906-a6cc-4b23-ab32-1f1e28229598/` scratch directory.

## Remaining gaps

This regression is technical workflow evidence only. It does not establish
human creative acceptance, generated environment/prop references, media or
asset currentness, F3B qualification, or a live specialist candidate.

## F3B seam

The inherited cinematic-realism direction and upstream semi-realistic painterly
`realistic` preset are intentionally not equated. F3B must create and inspect
real environment/prop references, retain these IDs and section usages, then
make any compatible render-style decision explicitly. This receipt makes no
human creative approval or visual currentness claim.
