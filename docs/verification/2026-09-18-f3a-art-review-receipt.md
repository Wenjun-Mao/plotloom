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

## Attended isolated proof

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

## Verification

- `node third_party/shuohao-skills/skills/novel-art/scripts/novel-art.mjs validate … --cast …` — passed.
- `uv run pytest tests/test_project_storage_art.py tests/test_project_storage_cast.py -q` — 4 passed.
- `npm run typecheck` and `npm run build` — passed; the pre-existing >500 kB
  chunk warning remains. Build refreshed `src/plotloom/static/`.

## F3B seam

The inherited cinematic-realism direction and upstream semi-realistic painterly
`realistic` preset are intentionally not equated. F3B must create and inspect
real environment/prop references, retain these IDs and section usages, then
make any compatible render-style decision explicitly. This receipt makes no
human creative approval or visual currentness claim.
