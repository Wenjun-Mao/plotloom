# Creator canonical read-only sidebar · 2026-10-22

> Only QA artifacts listed in the [2026-10-25 cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md)
> were retired. References to those artifacts describe historical
> runs, not available files or current launch/recovery instructions.
> Recorded outcomes and limits stand.

Status: qualified locally and activated at `21c6d6be`. Refresh the existing page
to load the changed frontend assets. Live Safari readback remains unavailable;
the browser evidence below comes from independent isolated fixtures. No provider
call, backend restart, source binding, push or GitHub CI run was performed.

## Why the agreed design disappeared

This was not an approved redesign or a missing design specification.
[ADR 0122](../adr/0122-creator-workspace-presentation.md), the original
[graph-centred plan](../roadmap/2026-10-06-graph-centred-creator-workbench.md),
the Chinese manual and the permanent acceptance checklist already distinguish
Creator's automatically ranked chart/right selected-node inspector from
Professional's technical graph view.

The defect originated in the frontend fallback introduced in `c8f59b77`:
`CreatorWorkbench` and `ProfessionalGraphWorkbench` both returned the same
`CanonicalGraphReader` when authoring was read-only. That shared reader displayed
all detail below the chart, bypassing Creator's layout and geometry. Write
authority incorrectly selected presentation. Source-unbound accepted stories
therefore lost the Creator shell even though they remained valid to read/play.

The earlier acceptance mapping exercised editable Creator's sidebar and
source-less Professional separately, not the mode × authority combination.
Component tests reinforced the shared-reader behavior without asserting mode
identity. The subsequent choice-label repair at `7fd015ba` preserved this bad
fallback. Manager review missed that existing-contract violation; a passing
label/layout check did not establish Creator presentation compliance.

The [durable amendment](../adr/0122-creator-workspace-presentation.md#workspace-presentation-is-independent-of-write-authority-2026-10-22)
now states the separation explicitly: mode chooses presentation; admitted source
and draft state choose mutation authority. The manual/checklist and browser
assertions now cover canonical read-only Creator as its own presentation case.

## Repair and boundaries

- Creator projects canonical nodes into its automatic chart plus bounded,
  resizable right inspector. Node title/type/footage mode/summary, incident choice
  text/effects and join rules are readable; IDs/full JSON stay folded.
- Selection and geometry reuse project-scoped private presentation state, with
  canonical start-node fallback and invalid/stored selection reconciliation.
  No authoring draft, source binding or graph store is fabricated.
- Selection reveal measures rendered node coordinates after React Flow's initial
  transform, not untransformed layout coordinates. The regression includes a
  translated-node case. Chart horizontal scrolling and page vertical scrolling
  retain their separate owners.
- Professional's technical read-only view and pan/zoom remain unchanged. Existing
  editable Creator and Professional behavior, canonical identity, read admission,
  autosave/CAS guards and authoring authority remain intact.

The actual source diff from retained `d68d5f07` and installed `7fd015ba` is
frontend presentation/private selection, tests, generated static assets and
documentation only. Backend Python, public API/schema/types, persistence,
provider/prompt behavior, dependencies/locks, service and build tooling did not
change. This is risk-scoped frontend qualification, not a full release run.

## Verification

One GPT-6 Luna / Max worker owned implementation, followed by GPT-6.1 Sol /
Medium independent review. Requested selectors were explicit; effective model
settings were not separately audited. Root reviewed the actual diff and owned
the final software/browser checks, pixel inspection and activation. Review found
no remaining concrete blocker and independently inspected the three supported
desktop screenshots and retained test/hash evidence.
Both idle workers were archived after their finals were collected and their
source/evidence reviewed; only their exact manager-scoped Relay routes were removed.

- Focused provider/presentation/autosave checks: 22 passed at the final worker
  checkpoint; frontend and E2E TypeScript checks passed.
- Unfiltered frontend unit suite: **168 files / 1,483 tests passed**.
- Two deterministic builds passed; the seven-file SHA-256 manifests are identical.
- The first parent browser invocation passed **20/20**: the entire Creator layout
  file (six canonical cases and three editable cases), shipped-static smoke
  (two cases), and graph-read recovery (nine cases). E2E TypeScript also passed.
- Canonical fixtures cover a valid four-node split and a six-node join/long-skip
  graph at 1280×768, 1280×460 and 1700×900. Assertions cover right-side geometry,
  selection/read-only fields, keyboard selection, resize/cancel, stored/invalid
  selection, mode switch/reload, label bounds/intersections/colors/scrolling,
  Professional native pan/wheel alignment and zero authoring writes. Full stage
  and graph-workbench payloads remain unchanged.
- Root directly inspected the three supported viewport images, then used an
  attended CLI browser on a new fixture origin to select the decision and ending.
  At 1280×768 and 1280×460, details changed with selection and remained beside
  the chart; an additional 1700×1200 bounds read confirmed the layout clamp.
  Console: zero messages/errors/warnings. No live-project browser surrogate was
  used. The owned browser and fixture server were closed; evidence is retained.
- `git diff --check`: passed.

Commands and retained evidence:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --vitest tests/graph-readonly-selection.test.ts \
  --vitest tests/graph-presentation.test.ts \
  --vitest tests/graph-read-autosave.test.ts
npm --prefix frontend run typecheck
npm --prefix frontend run typecheck:e2e
npm --prefix frontend test
npm --prefix frontend run build:deterministic  # twice; compare SHA-256 trees
uv run --locked --no-sync python scripts/verify.py focused \
  --playwright e2e/creator-workbench-layout.spec.ts \
  --playwright e2e/shipped-static.spec.ts \
  --playwright e2e/graph-read-recovery.spec.ts
```

Raw logs, manifests, preservation receipts and browser captures were retired,
including the inspected decision and short ending viewports.

## Retained findings, not hidden retries

Early focused harness failures exposed an excluded `.test.tsx` filename, a
project-switch test that had not rerendered its provider, and a mock-prop typing
error. These were corrected before the successful checkpoint, without weakening
production guards. Independent review also required rendered-coordinate
selection geometry and a reload expectation that respects the persisted
selected decision. Both landed before the first parent browser invocation.
Existing non-failing jsdom `window.scrollBy` warnings remain outside this repair.
An initial read-only job-state SQL used `status`; schema inspection established
the actual column is `state`, and the corrected diagnostic confirmed all 21 video
jobs are terminal `ingested`. No data write resulted from that diagnostic.

## Activation and preservation

P (`/Users/wjmao/projects/HU/plotloom`) was clean, detached at `7fd015ba`, with
zero active native attempts, enabled queue items or validators. Both historical
UNKNOWN identities were preserved. Before install and immediately before
activation, preservation snapshots were byte-identical. P switched to detached
`21c6d6be`; its read-only source mount exposes the qualified static assets
without restarting the backend, per the creator service contract.

All seven installed files match the second qualified build. Actual container
mount hashes are JS
`d6bd581173e502c6a9aee2f83a8219ab27c11b0d4a103f45de3bb0fccfdbd403`
and application CSS
`5d9126ffc19e3389c61d4d99d78938647edbc0cb08c9547ca9c099c2733699c3`.
Container `cd2edcb105d8` remains healthy with unchanged PID 172415; bridge PID
66847 and its start time remain unchanged.

The after-install preservation snapshot is byte-identical to the original:
all seven project identities, database-table fingerprints, media/selection files,
protected configuration, application/host accounting, queues and historical
UNKNOWN identities are unchanged, with no controller-claim differences.

Limits: isolated Chromium qualification is not a live Safari readback, owner
creative acceptance, new-generation qualification or full local/hosted release
qualification. No additional backend/media work follows from this repair.
