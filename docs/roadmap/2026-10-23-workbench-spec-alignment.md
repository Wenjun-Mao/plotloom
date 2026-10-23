# Creator and Professional workbench specification alignment

Status: implementation plan for owner review, 2026-10-23. Planning is authorized;
implementation and activation have not been approved or started. The product
choices are settled; no additional design decision is needed before approval.

Source baseline: clean retained checkout R
`/Users/wjmao/.codex/worktrees/b30f/plotloom`, `8040ec5e`, local `main` ahead of
`origin/main` by 12 commits. Its executable diff from audit baseline `8d3b259a`
is empty. Installed checkout P `/Users/wjmao/projects/HU/plotloom` was inspected
clean at detached `21c6d6be`; current runtime/quiescence must be checked at delivery.

## Outcome and boundaries

Make both workbenches follow the [agreed product specification](../specs/workbenches-product.md):
readable editable choice labels, shared selection and action status, truthful
Brief target previews, and the adopted Professional navigation/session behavior.
Keep Creator's automatic chart/right inspector distinct from Pro's technical
canvas, including canonical read-only states. One graph/draft/selection authority
continues to own both views.

The [audit](../verification/2026-10-22-workbench-spec-audit.md) owns the four
observed deviations and their evidence limits. [ADR 0122](../adr/0122-creator-workspace-presentation.md)
owns the accepted height formula and C56/C57 Pro decisions. The
[review register](../specs/conflicts.md) has no remaining intent question for this
bounded scope. Other product domains, native completion/media quality, narrow
screens, new source binding, schema/persistence/API changes, durable Pro layouts,
new read-only node dragging and unrelated refactors are excluded.

Sidebar height is a retained regression requirement, not a new redesign:
`min(0.85 × full viewport height, usable visible workspace)`, centred/clamped,
with reachable header/actions and internal body scrolling.

## Root causes and repair scope

| Work | Cause and correct layer | Required result |
| --- | --- | --- |
| Editable long labels — audit 1 | Absolute full-text label has bounded width but unbounded height against fixed layout lanes | Bound the visible label to its lane without data truncation; retain full keyboard-accessible text and exact-edge editing. |
| Pro selection — audit 2 | Controlled nodes omit shared selected state and only mouse clicks reach the shared owner | Project shared selection and route native keyboard selection to that owner; canvas, details and mode navigation agree. |
| Canonical Brief counts — audit 3 | Count display requires an authoring draft, incorrectly coupling reading to write authority | One topology-only count kernel accepts current draft or canonical topology, names its basis and preserves unknown-read handling. |
| Pro action status — audit 4 | Creator alone composes prerequisites/currentness; shared action bar receives no Pro status | Share derived action availability/status from existing reads, not copied strings or a new permission owner. |
| Pro page/canvas navigation — C56 | Both Pro paths inherit wheel zoom and scroll prevention; callback presence currently chooses canvas policy | Explicit Pro presentation policy: ordinary wheel scrolls the page, deliberate pinch/visible controls zoom, background drag pans; retain intentional inner scrolling. |
| Pro session lifetime — C57 | Pro-local positions and uncontrolled viewport vanish when mode pages unmount | In-memory active-project presentation owner survives mode switches, then resets on project change/reload/close-reopen without resetting shared selection or authored work. |

Keep these repairs in frontend projection, interaction and presentation ownership.
Do not fabricate a draft, duplicate graph state, tighten the 300-character schema,
relax read/CAS/currentness guards or modify backend admission to accommodate UI.

Primary source entrypoints are `frontend/src/features/graph/`:
`ProfessionalGraphWorkbench.tsx`, `CanonicalGraphCanvas.tsx`,
`CanonicalGraphReader.tsx`, `CreatorChart.tsx`, `creator-workbench.css`,
`creatorStructure.ts`, `creatorAdmission.ts` and `GraphWorkflowActions.tsx`.
The stable session boundary is `frontend/src/app/workspace/WorkspaceController.tsx`;
Brief count composition is in `frontend/src/pages/BriefPage.tsx` and
`features/graph/BriefTargetPreview.tsx`. The existing graph provider/context and
`useCreatorGeometry.ts` are preservation boundaries, not replacement targets.

## First observable UI outcome and prerequisites

The first vertical slice is a short desktop session at 1280×460: enter Pro, wheel
over its background and a node, and see the document move without graph zoom or
pan. Deliberately zoom/pan, reposition a supported editable node, select by
keyboard, switch Creator→Pro through the in-app view controls, and retain the Pro
view plus shared selection/details. Follow immediately with canonical-only Pro
page scrolling, deliberate navigation and non-draggable read-only nodes.

Use existing isolated `frontend/e2e/fixture.ts` infrastructure with blank provider
keys and test-owned roots. There is no paid/native generation in this milestone.

- Positive editable fixture: `createScriptProject(request, origin, label, {}, [])`
  from `frontend/e2e/f5a-fixture.ts`. It prepares a deterministic accepted outline
  and installs a current four-node source graph, skipping cast/art/script setup.
  Verify current source/outline/admission, `draft=null` after installation and
  `initialPayload` matching the accepted map before exercise. That seeds the
  frontend's initial editable map; it is not a recovered/persisted server draft.
  If a checkpoint needs a server ACK, explicitly Save and read back its receipt.
  API/file delivery is labelled fixture setup, not a claimed creator UI operation.
- Canonical fixture: reuse `canonicalFourNodeSplit()` and `initialStages` setup
  in `creator-workbench-layout.spec.ts`; verify `readOnlyReason` and `draft=null`.
- Missing-prerequisite fixture: `createCreatorGraph` has a graph draft but no
  accepted source/outline. Retain it for refusal/status parity, not positive
  confirmation or production-readiness claims.
- A second test-owned project in the same browser/runtime establishes project
  change and A→B→A visual reset. Reuse existing close/reopen lifecycle controls.
- Retain join/long-skip and 3–6 sibling fixtures for label/layout regression.

Record project identities, source/static identity, initial ACK/currentness and
GET payloads before presentation actions. A fresh root and owned browser/server
have one execution/cleanup owner. Preserve useful evidence; do not reset real
projects or replace a denied live URL with another browser/port or a data copy.

## Implementation approach

Use one small Pro presentation-session owner at the stable workspace boundary
that survives Creator/Pro page replacement. Keep it separate from authored graph
commands and shared selection. Reset on active project/lifecycle exit, not on
ordinary reads, reconnects, acknowledgements or mode unmount. Reload naturally
starts empty; do not introduce a project cache or browser/server layout storage.
Discard removed-node position entries without erasing surviving context. Restore
a retained viewport without running initial fit over it; first entry/reset may
use the existing fit behavior. Do not remount the graph provider to clear visuals.

Give canonical canvas callers an explicit presentation contract. Creator remains
passive, natural-height and page-vertical/chart-horizontal. Pro uses its technical
viewport, visible zoom/fit controls and deliberate pan/zoom. If canonical Pro needs
the existing bounded Pro viewport rather than Creator's full-layout scroll shell,
split that shell only, retaining shared topology/label geometry and fields.
This avoids competing nested horizontal navigation, not a new layout algorithm.
Canonical Pro nodes remain non-draggable. No global wheel listener is introduced.

Prefer the existing bounded canonical-label accessibility pattern over expanding
every row dynamically. Preserve complete text and an exact editing action; a
tooltip or clipped/ellipsized text alone is insufficient. Trade-off: long labels
need internal reading/expansion rather than making the whole story much taller.
Implementer chooses cohesive markup without nested interactive controls.

Factor topology counting from `creatorStructure` without turning canonical data
into an authoring draft. Preserve route guards, enumeration limits/truncation,
join/degree/count semantics and unfinished-draft checks in their current layers.
Select a current draft/canonical basis using owned read status; failed or stale
reads cannot silently become current canonical counts or a false zero. Snapshot
the preview basis consistently and identify it in the disclosure.
The shared initial/unsaved editable payload is a draft basis even before a server
draft row exists; a null persisted draft alone must not force canonical counts.

Share prerequisite/action projection from `creatorStructure`, `creatorAdmission`,
source/outline and production reads. Keep actual provider/backend write guards
and request payloads unchanged; view-specific layout/desktop controls stay separate.
Show missing prerequisites, read uncertainty and currentness beside global actions
while preserving Save / Confirm / Apply as separate operations.

## Ordered delivery

1. **Preflight and Pro vertical slice.** Reconfirm the diff boundary, installed
   dependency/input behavior and the fixtures above. Implement Pro presentation
   lifetime, explicit wheel policy/controls and shared selection projection with
   focused state/prop tests. Exercise the first native UI slice before broad
   qualification. Ordinary wheel needs both wheel-zoom disabled and native page
   scrolling allowed; disabling zoom alone still consumes wheel in this library.
   Do not assume Meta-wheel emulates pinch; use the installed supported gesture.
2. **Contain editable labels.** Reuse lane geometry and complete-text reading.
   Through the actual editable UI enter/save a valid 300-character Chinese option,
   read back its exact bytes/topology, inspect card/label intersections and reach
   both full-text reading and exact-edge editing by keyboard.
3. **Complete counts and action parity.** Implement topology-only count projection
   and shared prerequisite/status projection. Exercise draft/canonical previews,
   incomplete/missing-prerequisite states and read-failure recovery in both views.
   Cancel a target preview and prove no formal Brief or canonical mutation.
4. **Integrated regression and stable review.** Cover all six rows below with the
   same candidate, preserving dirty text, shared selection, Creator preferences,
   structural Undo and late-ACK behavior. Independently review a stable diff and
   retained source/browser/pixel evidence; repair concrete findings with focused
   checks. Update affected specification/manual guidance and ADR ownership details
   only where the actual implementation warrants them. Do not create a second log.
5. **Qualify once and deliver.** Complete the applicable final local qualification,
   commit a coherent `main` checkpoint with generated assets, then perform the
   proposed preservation-checked frontend activation and readback below. Report
   local qualification, isolated UI proof, activation and owner acceptance separately.

One source writer works serially in R. One verification owner coordinates costly
runs and cleanup. Read-only independent review does not trigger duplicate full
suites. Keep new modules cohesive; do not add Pro presentation responsibilities
to the already large graph draft provider or rewrite the workspace controller.

## Acceptance and verification

| Contract | Required fresh evidence |
| --- | --- |
| Labels, C06/C07/C15 | Editable 300-character option is exact after Save/readback; no label/card or label/label overlap, accessible complete reading/editing, retained canonical join/skip lanes and 3–6 siblings. |
| Shared selection, C02/C07/C08/C28 | Mode entry and native Enter/Space selection update the visible canvas and inspector together; pointer, structural Undo and newer-selection/late-ACK guards remain correct. |
| Brief counts, C29/C30 | Draft-backed and canonical-only previews show correct counts and named current basis; equivalent topologies agree, unknown reads stay explicit, Cancel preserves formal targets/graph. |
| Global actions, ADR 0155 | Both views show prerequisite/currentness status beside whole-graph controls with matching domain availability. Missing Outline, incomplete/mismatched graph and failed production/source reads do not invite known-refused writes. |
| Pro navigation, C56 | Both authority states: ordinary native wheel over pane/node/edge moves the document without graph-transform change; visible zoom/fit controls are present and work in editable and canonical-only Pro. Deliberate pinch and background drag also work; inner label/form scrolling remains and read-only nodes do not drag. |
| Pro lifetime, C57 | Actual in-app mode switches retain supported positions and viewport; project change, A→B→A, reload and close/reopen reset only Pro visuals. Shared selection, dirty fields and Creator preferences retain their existing behavior. |

Preserve the three supported desktop sizes: 1280×768, 1280×460 and 1700×900.
Directly inspect screenshots, not only assertions; include long labels, selected
details, controls and expanded sticky guidance. Keep the accepted sidebar-height
formula and cancellation geometry covered. No phone/1024px qualification is added.

Presentation-only segments start clean/acknowledged: record zero authoring writes
and unchanged complete graph/stage readbacks for selection, scroll, pan/zoom,
mode switching and position movement. Separate dirty-content/save scenarios may
make expected owned author writes. Brief Cancel can retain ordinary test-owned
form-draft autosave; do not call that a confirmed target change or claim zero
writes for the whole journey. Fixture setup is excluded from interaction counts.

Use native browser wheel/keyboard/pointer input and observe document/transform
results. Synthetic `dispatchEvent` or mocked React Flow props are not interaction
proof. Supported Ctrl-wheel browser input may exercise the pinch path; label it
as emulation, not a physical Mac trackpad test. Live Safari/hardware acceptance
remains distinct from isolated Chromium evidence and is not bypassed.

Extend established tests rather than creating a new harness. Focused unit owners
include `creator-layout`, `creator-presentation`, `graph-presentation`,
`graph-workflow-actions`, `graph-readonly-selection`, `graph-workbench-provider`,
`graph-read-autosave` and `graph-confirmation-read` under `frontend/tests/*.test.ts`.
Add focused cases for the new presentation-session/count projections as needed.
Retire old assertions that Pro wheel must zoom or Pro status must be absent;
replace them with stronger new-contract assertions, not weaker coverage.

The smallest initial browser selection is:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --playwright e2e/creator-workbench-layout.spec.ts \
  --playwright e2e/creator-workbench-operations.spec.ts
```

For the stable candidate also select the whole files
`e2e/graph-interactions.spec.ts`, `e2e/graph-read-recovery.spec.ts`,
`e2e/project-folder-close.spec.ts`, `e2e/recommended-workflow-guide.spec.ts` and
`e2e/shipped-static.spec.ts` in the same native runner. Playwright selection is
whole-file: no test-name/line filter. Layout and operations belong to different
module owners, so `module --module graph` alone does not cover this change.
Ensure affected workbench cases, not only the generic smoke, run against the
fresh built static assets before activation; extend existing checked-static
coverage where needed, retaining development-server runs as separate evidence.

Final qualification is risk-scoped frontend qualification only if the reviewed
actual diff leaves backend/API schemas and payloads, persistence/admission/auth,
provider/prompts, dependencies/locks, package contracts and build tooling unchanged:

```sh
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run typecheck:e2e
npm --prefix frontend run build:deterministic
# Record a sorted SHA-256 tree in this run's private evidence directory.
npm --prefix frontend run build:deterministic
# Compare the second sorted SHA-256 tree with the first; retain generated assets.
```

Follow [development verification](../development.md#risk-scoped-local-frontend-qualification),
with task-owned manifest paths rather than shared scratch files. Run explicit
affected browser/desktop checks on those bytes. If the actual change crosses
that boundary or impact remains uncertain, reassess scope and use the native
unfiltered `full` gate when warranted; do not weaken gates to keep the smaller
label. Preserve failures, diagnose them, and rerun failed/affected checks rather
than unchanged broad suites. No checks in this section have been executed during planning.

## Proposed execution permissions and activation

Approval to implement this complete plan is intended to cover its six frontend
changes, regression-test updates, isolated test fixtures/browser actions, local
qualification, generated assets, documentation, local checkpoint and quiet
frontend activation/readback. These permissions are proposed for the approval
step, not inferred from approval of the designs. Routine in-scope checkpoints
do not need repeated approval; new backend/schema scope, unavailable authority
or a materially different deployment requires direction first.

Root owns P/runtime activation. After candidate qualification, inspect the actual
P revision, clean state, supported service mount and task/queue/validator ownership.
Wait for a safe quiet checkpoint; preserve historical UNKNOWN outcomes and holds.
Compare read-only fingerprints of project identities/data/media/selections,
protected settings, host/accounting and retained uncertainty immediately before
and after activation. No project cleanup, data reset, snapshot/migration system,
provider invocation or deployment to other services belongs to this work.

Use the [creator runtime contract](../../services/creator_workbench/README.md):
the existing read-only checkout mount can expose newly qualified frontend static
assets without restarting unchanged backend/bridge processes. Activate only the
exact qualified candidate after checking backend bytes/contracts are unchanged;
verify installed/mounted static hashes, health and preservation. Retain the
previous qualified checkout/static identity for scoped rollback if activation
fails; never erase projects or downgrade a changed schema to manufacture recovery.
No backend restart is planned. Live Safari readback remains unavailable under
the prior access boundary; static/read-only service checks and isolated built-UI
proof must not be presented as that readback or as owner usability acceptance.

GitHub CI, workflow preparation/publication and any push that triggers CI remain
off without a new direct owner request. Publication is separate; do not alter
workflows or add skip markers. No public release or new automation is included.

## Completion and handoff

Stop when the six scoped outcomes have final candidate-bound interaction/pixel
evidence, applicable local qualification and approved activation/preservation
readback, or report the exact remaining blocker without claiming completion.
Update the existing audit's finding dispositions with links to one dated
implementation verification receipt; preserve its original failed observations.
Report source/static/installed revisions, changed/retained checks, actual results,
open limits and owner acceptance separately. Do not substitute test totals or
service health for the observed workbench journey. Planning ends with this
reviewed proposal; no implementation worker, application edit or activation starts.

Planning review: independent engineering and fixture/verification reads found no
remaining blocker after distinguishing initial editable payload from a persisted
draft and requiring visible working controls in both Pro acceptance paths.
All 309 relative file/directory targets across the four changed documents resolve;
all 15 explicitly named existing unit/browser files exist. These are path checks,
not a general anchor/external-link crawl or executed tests. Whitespace and
documentation-only diff checks pass. No software/browser/build check was run.
