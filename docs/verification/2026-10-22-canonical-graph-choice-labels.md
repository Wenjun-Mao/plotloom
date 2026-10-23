# Canonical graph choice labels · 2026-10-22

Status: frontend presentation repair qualified locally and activated at
`7fd015ba999a480c507e02feed4293652bf1de48`. Live Safari verification remains
unavailable; the screenshots below are isolated local fixtures, not the owner's
live project. No provider call, push or GitHub CI run was performed.

## Cause and durable contract

The accepted read-only reader used an index-based four-column grid, bypassing
Creator's topology layout. React Flow's top/bottom handles and midpoint labels
therefore placed same-row choices under intermediate cards. The built page also
loads library CSS after application CSS, overriding equal-specificity SVG label
colors. This was a frontend presentation defect, not missing choice content or
an authority/source-binding defect.

[ADR 0122](../adr/0122-creator-workspace-presentation.md#canonical-read-only-fallback-geometry-and-labels-2026-10-22)
records the remedy: reuse the topology-only ranked geometry, explicit downward
handles, separate incoming-label lanes and skip-edge gutters. Canonical source
order, IDs, text, effects, read-only status and authored data remain unchanged.
The shared authoring wrapper retains its prior row hints and algorithm. Scoped
HTML labels avoid the built CSS cascade conflict; long labels wrap and scroll
with keyboard access to their complete text. Natural graph height and horizontal
scroll preserve readability; page scrolling may be needed for lower ranks.

## Qualification scope and evidence

Trusted baseline: `fe2f245751007fb06f9f6db0e586d66cc335e393`; installed baseline:
`e74a3e86fb8ee3ccd3a775064a34b4c92b44afd0`. The actual diff changes frontend
geometry/presentation, tests, generated JS/CSS and documentation only. Direct
comparison confirmed unchanged backend Python, API/schema and request contracts,
persistence, admission/auth, provider/prompt behavior, service files, dependencies,
lockfiles, build tooling and shared `frontend/src/types.ts`. This qualifies for
the repository's risk-scoped local frontend policy, not a full local release run.

Delegation requested GPT-6 Luna / Max for the sole implementation owner and
GPT-6.1 Sol / Medium for independent review; native selectors were explicit,
while effective settings were not separately audited. Review found no actionable
core correctness issue. Its browser coverage findings
(bounds, pairwise label intersections, reachable scrolling and native pan/zoom)
were incorporated before execution. Both workers are now idle, archived and
unregistered from this assignment's Relay routes.

- Focused layout/presentation selection: 22 passed.
- Frontend TypeScript check: passed; final check also covers the updated test mock.
- E2E TypeScript check: passed, including the final browser invocation.
- Unfiltered frontend unit suite: **167 files, 1,479 tests passed**.
- Two `npm run build:deterministic` runs: all seven static-file SHA-256 entries
  matched exactly. Existing large-chunk warnings remain warnings.
- Browser scope: six checked-static canonical cases (two graphs × three desktop
  sizes), three existing editable Creator layout regressions and two shipped
  static smoke cases. Composite evidence is complete: the affected layout file
  passed **9/9** after the diagnosed test-coordinate correction; the unchanged
  static smoke file passed **2/2** in the first run. This is not a claim that the
  original combined invocation passed.
- Native CLI inspection of the retained four-node fixture at 1280×768, 1280×460
  and 1700×900: both Chinese choice labels readable and separate from cards.
  Browser console reported zero errors/warnings. Reviewed the join/skip and
  professional-mode screenshots, including the native pan/wheel result.
- `git diff --check`: passed.

The smallest journey uses an independent source-less start → decision → two
endings graph with “继续照向海面” and “照亮岸边石阶”. The separate six-node case
has two scene branches, a three-source join, a long skip choice and a terminal
ending. Brief counts match each graph. Each runs both creator/professional modes
and reloads, checks computed shipped theme colors, graph bounds, label/card and
label/label nonintersection, long-label keyboard scrolling and zero authoring
writes. Canonical stages and read-only reason are equal before/after. One case
performs native pan and wheel zoom and checks node/label transform alignment.
No fixture points at the live installation or uses a real provider transport.

Commands and retained evidence:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --vitest tests/creator-layout.test.ts --vitest tests/graph-presentation.test.ts
npm --prefix frontend run typecheck
npm --prefix frontend run typecheck:e2e
npm --prefix frontend test
npm --prefix frontend run build:deterministic  # twice; compare SHA-256 trees
uv run --locked --no-sync python scripts/verify.py focused \
  --playwright e2e/creator-workbench-layout.spec.ts \
  --playwright e2e/shipped-static.spec.ts
# After the diagnosed coordinate-only test repair:
uv run --locked --no-sync python scripts/verify.py focused \
  --playwright e2e/creator-workbench-layout.spec.ts
```

[Logs, manifests and preservation receipts](../../.local/canonical-graph-labels-20261022/)
and [retained browser artifacts](../../output/playwright/canonical-graph-labels-20261022/)
remain local. [Short desktop choice screenshot](../../output/playwright/canonical-graph-labels-20261022/choice-visible-1280x460.png)
shows the fixture, not a live Safari readback.

## Retained failures and corrections

- Initial worker type checks exposed a missing explicit React Flow node `type`
  and an untyped mock-call tuple (`TS2322`, `TS2352`, `TS2493`); these were fixed
  before successful type checks. A later E2E fixture typing error was also fixed
  before execution. Schema review corrected the proposed incomplete join fixture
  before its first browser run; no invalid fixture result is presented as E2E.
- The first unfiltered unit run was **1,477 passed / 2 failed**: the older
  validation-focus projection omitted React Flow's `Position` export. Its mock
  surface now includes the required exports without weakening focus assertions.
  The focused projection then passed 9/9 and the complete unit suite passed.
  Original log: `frontend-unit.log`; replacement: `frontend-unit-after-mock.log`.
  Existing non-failing jsdom `window.scrollBy` stderr was not broadened into this
  repair.
- The first browser run was **10 passed / 1 failed**. Focusing the long label
  scrolled the page; the test then dragged from the offscreen canvas origin
  (`y=-364.34375` in the retained trace), so no native pan occurred. The fix is
  confined to test coordinates: use the visible canvas intersection below sticky
  chrome. Production pan/zoom was not bypassed or patched. The affected file then
  passed 9/9 with the original transform assertions intact. `browser-1.log` and
  `browser-run-1/` retain the failure; `browser-2.log` and `browser-run-2/` retain
  the successful affected-file run. The final browser step took 33.570 seconds;
  other product/coordination time was not separately instrumented.

## Activation and preservation

P (`/Users/wjmao/projects/HU/plotloom`) was clean and detached at the installed
baseline. All video jobs were terminal `ingested`; native active attempts,
enabled queues and validators were zero. Historical UNKNOWN records were
preserved, not cleared. P switched to detached `7fd015ba`; its read-only source
mount exposes static assets without a backend restart, as documented in the
[creator service contract](../../services/creator_workbench/README.md).

All seven installed static files match the qualified second build. The actual
container mount also reports JS SHA-256
`acdb90bc035c72ed1e39ed3e87bd569b6fb550ed25b1b01c34f8dd98bca3c8cd`
and application CSS SHA-256
`45651ef8748293dde71398335590d13ec746dbe8f95c604123d55a1e75d53efa`.
Container `cd2edcb105d8` remains healthy with unchanged PID 172415; owned bridge
PID 66847 and its start time are unchanged. No service/gateway restart occurred.

The before/after preservation JSON files are byte-identical: all seven project
identities, every database-table fingerprint, media/selection files, protected
configuration, application/host accounting, queue state and historical UNKNOWN
identities are unchanged, with no controller-claim differences. The attended
CLI fixture server/browser were closed; disposable evidence roots are retained
for inspection. No live project was edited or copied into a test fixture.

Limits: no live Safari page readback, full local release qualification, hosted CI,
new generation/media acceptance or owner creative acceptance is claimed. Refresh
the owner's existing page to load the activated assets; Safari-specific visual
confirmation remains separate from the isolated Chromium evidence above.
