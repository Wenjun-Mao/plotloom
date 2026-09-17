# F1A live source-to-outline proof receipt

Date: 2026-09-17. Scope: one disposable F1A production-UI proof; this is not
F1/F1B completion, human creative approval, source clearance, or media work.

## Live proof

- Created the isolated project `潮汐灯` (`a555b63e-13e2-455b-a49b-77a1bf4ce661`)
  through the production UI, using an original declared synopsis. Its frozen
  scope is cinematic realism, about 120 seconds, one cable decision, and two
  mutually exclusive endings with no reconvergence.
- Saved the source with verbatim attribution, rights declaration, adaptation
  intent, and bounded allowed additions. The UI prepared
  `ch_2873bf8153f04560bc3af633e49c3657` at source r1 / expected outline r0.
- An attended Terra specialist read only the frozen package and delivered the
  upstream-shaped candidate/report/receipt. It used pinned Shuohao revision
  `4322897e6d2bdaf66365534fd40194360c75a85f`; beats and full validation plus
  all 14 deterministic gates passed. No provider, Qwen, or media call occurred.
- Production UI refresh admitted the delivery, then explicitly installed outline
  r1. This was a technical lifecycle exercise only. It was reopened without
  replacement, then the project was closed and reopened; source r1 and accepted
  outline r1 remained visible with the reopened review state.

The ignored package, delivery, runtime logs, and test logs are under
`.local/relay/3340e35f-3d3d-499e-8699-1e1e40c328b0/`. Real ready and reopened
UI screenshots were captured in this task's proof record.

## Technical review and correction

Independent read-only Terra review confirmed package/manifest identity and
source faithfulness, but found that the raw upstream report's fixed “signed off”
heading could imply human approval. F1A now presents it as an explicitly
unreviewed, collapsed upstream artifact rather than rewriting its hash-bound
bytes. ADR 0058 records that ownership boundary; a React Strict Mode late-load
race that could erase unsaved source input was also fixed with regression
coverage. E2E selectors now use stable stage labels rather than shifted stage
numbers.

## F1B handoff inputs, not implementation

Accepted source r1 and outline r1 provide S01 weather station, S02 distant
beacon/dock view, C01 Lin Che, C02 stranded sailor, cable and beacon-lamp props,
and the B02 cable choice with dock-power/beacon-dark versus beacon-power/dock
self-evacuation endings. The accepted upstream outline remains linear: it has
no machine-readable option IDs/text, branch nodes, per-branch duration split, or
section mapping. F1B must own that mapping without inventing a second graph.

## Verification

- `uv run pytest -q`: 583 passed; one existing Starlette deprecation warning.
- `npm --prefix frontend test`: 17 files, 159 tests passed before the
  scope-excluded unit-test removal; the allowed production E2E journey covers
  the same late-load regression in the final candidate.
- Frontend and E2E TypeScript checks passed; Vite production build refreshed
  `src/plotloom/static/` (existing over-500 kB warning retained).
- Serial production E2E suite: 48 passed. The initial parallel run exposed stale
  stage-number selectors; the corrected label-based selectors and final source
  race fix were verified by the serial final run.

## Tracker and CI policy

The roadmap now records that GitHub CI is a deliberate manual-trigger check.
The director separately owns the pending workflow-only removal of `push` and
`pull_request` triggers while retaining `workflow_dispatch` and existing jobs.
