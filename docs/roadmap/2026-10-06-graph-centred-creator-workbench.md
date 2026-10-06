# Graph-centred creator workbench implementation plan

Status: owner-approved for implementation on 2026-10-06 (Toronto), with the
current-contract-only instruction below. Created 2026-10-06. Baseline inspected:
`e542f49c4e815d797f17e0a83c0631c54f9f6ea3`.

## Outcome and first-release scope

Make **创作工作台** the graph-centred main workspace, with a supporting node
inspector and real Story/Production workflows. Keep **专业工作台** for detailed
existing controls. Both modes operate on the same project, stable identities,
author drafts, accepted evidence and playback graph; neither creates a second
story or production authority.

The owner clarified that existing installed productions are development demos,
not completed productions requiring migration. Target the new-project authoring
journey through reviewed production, and use rebuildable demos for qualification.
Do not build a general replacement/migration system for installed productions in
this first batch. This limits structural re-installation, not reading existing
production or using already-supported current shot/media actions.

Graph drafts and accepted playback still have different lifetimes. Saving a new
draft never silently replaces an installed graph or rebinds existing media. Keep
current production readable and make any blocked re-admission explicit. If an
installed demo blocks an exercise, an owner-authorized rebuild may use an exactly
identified disposable fixture/project; no special “demo bypass” of production
validation is introduced. No data reset is necessary or performed during planning.
General post-installation revision/replacement remains a named later capability,
not an unimplemented behavior disguised as a working button.

## Current-contract-only implementation instruction

The owner's implementation approval explicitly requires **zero backward-compatibility
layers, migration adapters, historical replay paths or legacy fallback code**.
Building-phase breaking changes and targeted disposable-data resets are preferred
to preserving executable old contracts. This instruction supersedes any earlier
wording in this plan that could be read as requiring old graph/schema behavior.

- Define one current graph-authoring/admission contract for both workbench modes.
  Consolidate obsolete competing write paths instead of wrapping them in compatibility
  adapters. Preserve supported fine controls and safety semantics, not old interfaces.
- Audit affected graph/source/draft/script/production/persistence paths for historical
  versions, shape-tolerant reads, old-schema branches and fallback projections. Remove
  confirmed obsolete execution code and its obsolete tests; add current-contract
  regression coverage. Record discovered targets and proof of retirement in the
  implementation receipt. Do not merely rename or hide compatibility machinery.
- Planner→authoring→runtime compilation and current scene/shot presentation are
  normal domain transformations, not permission for an old/new-version adapter.
  Keep exact typed current inputs and explicit validation rather than tolerant reads.
- No data-migration or old-contract replay system is part of delivery. If stale
  development data blocks the new contract, identify the exact disposable target,
  check dispatch safety, reset/rebuild only that target and report the change.
  Credentials, protected settings and unrelated data remain protected.
- Do not remove active product functions or concurrency/currentness/dispatch guards
  merely because they preserve user work or previous accepted revisions. Identify
  what is genuinely obsolete and why before removal; record durable retirements.

The read-only launch audit identified these concrete candidates for G0/G1
confirmation and retirement, not a blanket name-based deletion rule:

- Binary SectionMap execution in `source_outline_contracts.py`,
  `source_structures.py`, `persistence/project/source_outline.py`, and the frontend
  source structure types/editor/recovery helpers; replace old binary fixtures with
  current-contract coverage.
- The independent professional StoryGraph stage-write branch in workspace
  persistence/API/canonical/workflow owners; consolidate into the shared current
  admission contract. This is a competing write path, not legacy merely by age;
  other current stage writes and exact draft consumption remain supported.
- Historical intent-package reconstruction in
  `persistence/project/production_bridge.py::_intent_package`, and its legacy
  projection regression fixtures; use strict current-package inputs.
- Historical graph/stage model selection and run-snapshot schema defaults in
  `domain.py`, `persistence/project/repository_codecs.py`,
  `generation_snapshots.py` and `validation.py`; verify exact retired schemas and
  remove their executable reads while retaining current snapshot binding/rejection.

Current production projection, typed draft validation, CAS/currentness,
snapshot/restore and unknown-dispatch guards are not compatibility machinery.
Version-like provider names alone do not justify deletion.

## Approved reference and product boundaries

Reference: the owner-approved v9 sketch, `plotloom-graph-editing.rows.v9`, at
`/Users/wjmao/.codex/visualizations/2026/08/27/01a04525-e907-7630-9640-78790d69e8ae/plotloom-graph-editing.html`.
Artifact SHA-256:
`ef5b9a1a0d452973bcfb95f56fa69d3aa3513fb0a6e3594e6669bbc8e6286d57`.
Its sibling `plotloom-graph-editing-parts/` owns the modular source, acceptance
checklist, v9 receipt and view/scroll/inspector decisions. These are design and
engineering references, not production code, production acceptance or runtime
dependencies. Do not import the sketch or Narrative Forge V1 into Plotloom.

- Graph first; deterministic automatic layout. Free-position node dragging is
  excluded. Dragging a connection handle and resizing the inspector are different,
  supported interactions. Keep existing professional canvas behavior unless a
  shared-authority correction requires a separately explained change.
- Natural full-height, borderless chart; page owns vertical scrolling. Wide rows
  pan horizontally inside the graph. Never wrap siblings into apparent next steps.
- Inspector centre follows the selected node's centre, clamped to the visible
  workspace. Use available height, approximately 85% of the viewport when space
  permits; its body scrolls while header and actions remain reachable.
- Default inspector width 380px in roomy content, 300px in compact desktop content.
  A slim draggable/keyboard divider uses the sketch's bounded sizing contract
  (300–520px, at most 45% of content, preserving 480px graph space and divider gap).
  Double-click restores automatic sizing. Resizing must not remount forms or alter
  authored state, Undo, dirty flags, acceptance or production fingerprints.
- **Desktop browser width at least 1280px. Phone, narrow and 1024px authoring
  support are formally dropped, not deferred.** Put this visibly in the interface,
  developer entrypoint and permanent acceptance checklist. Test short desktop
  windows; do not create phone layouts or phone acceptance work. Portrait output
  media and unrelated backend tests are not retired by this screen-width decision.
- Reuse the delivered visual system: restrained hierarchy, surfaces, spacing,
  typography, compact information icons and hover/focus explanations.
- Every sketch revision starts with a clean sample; that is **not** permission to
  automatically reset projects. Credentials, protected settings and unrelated data
  remain preserved. Disposable QA fixtures reset between exercises; any existing
  demo rebuild must identify its exact target and scope and report what changed.

## Current architecture and the root cause to address

The approved interaction is more capable than the current write contracts:

| Current owner | Reusable behavior | Required change or boundary |
| --- | --- | --- |
| Brief / topology planner | Deterministic feasible structure, explicit decisions, route targets | Today source-map save requires exact planner topology; manual structural edits need an explicit author-owned reviewed contract. |
| SectionMap / source admission | Source/outline revision binding; compiles into canonical StoryGraph | Suggestion adoption, map confirmation and graph installation remain separate; editing may not forge a planner receipt. |
| Canonical StoryGraph | Stable nodes/typed edges/join contracts; sole routing authority | Generic graph save requires the Story Bible path; it cannot substitute for early source-first admission. |
| Authoring drafts | Revision/CAS recovery, navigation gates, save-and-close | Current stage schema cannot recover every unfinished sketch state, such as blank required content or a pending edge target. |
| Script and production bridge | Exact section→episode→scene occurrence→cut→canonical shot bindings | A graph node is not one scene or video. Bridge installation is currently first-install-only. |
| Media / playback | Reviewed references, keyframes, video candidates, explicit selections | Retain exact provenance, currentness, dispatch and selection guards; no independent creator-mode readiness state. |

Root-cause note: missing operations are not simply hidden controls. The source
route freezes planner-owned topology, while the generic graph editor writes through
a different admission path. Structural source replacement after production is
forbidden. Building row+, reconnect and delete against whichever save button is
available would bypass source currentness or contradict installed-production guards.
Repair ownership and draft/admission contracts before composing those controls.

Preferred approach: extend the existing source-bound authoring contract to accept
explicitly reviewed author edits, with planner output retained as seed/provenance;
compile that accepted structure into the existing sole runtime StoryGraph. Use one
current graph command/admission interface and shared selectors in both modes.
Preserve correct source evidence and current Bible/state validation without a
compatibility adapter for competing old entrypoints. G0 establishes which existing
paths become the current owner and which retire; do not invent source evidence or
retain independently editable copies to accommodate old demos.

Alternatives considered: a presentation-only facade is smaller but cannot deliver
the approved editing; an independent creator graph/pipeline would duplicate
authority and diverge from professional mode. Replacing source admission wholesale
with generic canonical saves would also lose the source-first approval boundary.

## Shared editing and review contract

1. Keep unfinished work in a typed, recoverable **authoring draft**. Pending targets,
   missing prose and detached nodes are explicit draft states, never silently lost
   and never installed as a playable graph. Presentation ranks/width/selection are
   separate from routing and production provenance.
2. Planner suggestions and author edits have explicit provenance. Preserve original
   accepted evidence; do not mutate historical hashes or relabel author edits as the
   original deterministic plan. Structural target checks apply to the actual edited
   graph. Brief targets and actual structure remain visibly distinct.
3. Commands produce an immutable proposed result, impact summary and preview pinned
   to the draft revision. Confirm once applies the entire transaction; cancellation,
   failed validation and stale previews apply nothing. Frontend preview and server
   validation share semantics, not necessarily duplicated implementation code.
4. Row+ adds to that logical row. Infer a shared choice parent only when unambiguous;
   otherwise require a compatible source or leave the node visibly detached. It
   never creates an implicit branch from an ordinary continuation. A shared immediate
   join/ending may be a visible, editable default; commit both previewed connections.
   No three-across cap. Separate presentation hints for unfinished rows from edges.
5. “插入新一行” previews splitting one exact connection, or explicitly creates an
   unconnected draft step without changing that connection. In a connected split,
   preserve the original edge identity, choice label and fact/entity effects on
   source→inserted-node; create a fresh continuation to the old target for a scene
   or join. Effects retain their original traversal point. Review affected join
   incoming IDs/reconciliation and source bindings. A decision needs explicit
   onward choices, with unfinished options visibly pending; an ending has no onward
   continuation. Never silently discard the old target or guess a decision option.
6. Existing incoming and outgoing connections are editable by exact edge/option.
   Compatible nodes are not restricted to a neighbouring row. Preserve displaced
   nodes and unrelated links. Retain detached input identity/text/effects in the
   draft. Reject self-links, cycles, ending outputs, illegal degrees and invalid
   start references with useful reasons. Draft edits may reduce existing errors,
   but may not introduce or worsen structural violations.
7. Delete a selected development/decision/join/ending/detached node with impact
   preview and an explicit method, with no method preselected: only-delete, or safe
   bypass. Offer bypass only for a scene/join with incoming links and exactly one
   connected continuation, after validating every retargeted input. Do not guess a
   decision option or bypass a multi-input join into a single-entry node. Never
   cascade-delete downstream nodes, scenes or media. Incoming links may remain
   pending in the draft. The current opening is protected; any existing professional
   start reassignment must be explicit and revalidated.
8. Each confirmed structural edit is one session-draft Undo transaction restoring
   node content, links and selection together. Undo is not rollback of server
   approval, dispatched jobs or selected media. A draft-only save keeps history on
   the same canonical base; a canonical admission or externally changed base resets
   that history after draft/conflict reconciliation. Older content explicitly
   recovered on a new base is a new draft requiring current validation, not restored
   historical acceptance authority.
9. Recoverable draft save, content confirmation, canonical admission, generation,
   review, bridge installation and media selection stay distinct. Mode/node/tab
   changes cannot discard or save edits into another node. Reuse CAS/conflict and
   navigation gates; show actionable stale, incomplete, failure and outcome-unknown
   states. No silent Brief increase or graph reshaping in either direction.

Record the new ownership/draft/operation decisions using repository ADR conventions
during G0/G1. Link them here; do not reinterpret completed old ADRs or receipts as
approval of new behavior. Implementation may choose cohesive module boundaries and
the layout algorithm, provided these observable contracts hold.

G0's bounded [explicit node footage decision](../adr/0120-explicit-node-footage-mode.md)
was approved by the manager on 2026-10-06 after the isolated feasibility probe
and an attended independent GPT-6.1 Sol / Medium domain review. Route-only
controls retain full route context but have no footage episodes or duration.
Current scene-owned state requirements require explicit footage inclusion;
there is no new path-state engine or weakening of source/production validation.

[ADR 0121](../adr/0121-current-source-graph-authoring.md) records the current
shared draft/admission owner and the confirmed historical execution retirements.

## Ordered delivery slices and gates

One serial source owner on the retained checkout; bounded independent read-only
reviews at stable candidates. No parallel writers across shared graph/persistence
owners. Model selection follows ADR 0023 at native dispatch, not worker-brief prose.
Every slice must be useful and qualified before later slices rely on it.

### G0 — Bind authority and prove the contract seam

- Bind the first-release/demo and no-compatibility scope above. Define the single
  current graph admission contract, retiring obsolete competing write paths.
  Document author-edited topology provenance, draft validity, stale/affected consumer
  rules, stable IDs and exact-edge semantics in concise ADRs.
- Prove source draft→validated map→canonical graph round-trip with a three-option
  structure, an inserted step, a join and retained source bindings. Show a malformed
  or unfinished draft can recover but cannot be admitted.
- Verify that route-only decision/join nodes can legitimately have no footage in
  current script/bridge/player contracts. If not, identify the smallest required
  contract change and obtain a bounded design decision before dependent work; do
  not fabricate cuts, hide mandatory media or claim unsupported “无需画面”.
- Define how installed demo fixtures are rebuilt for qualification without weakening
  first-install-only admission. Existing queued, dispatched or outcome-unknown jobs
  still constrain reset/rebuild. General production replacement is outside this batch.
- Gate: no unresolved authority ambiguity or scope guess. A feasibility conflict
  returns here for a bounded decision, not a downstream UI workaround.

### G1 — Shared graph operations and durable draft integration

- Add cohesive typed command/impact/validation/history modules. Implement row+, exact
  insertion, pending connections, incoming/outgoing retarget, explicit deletion and
  Undo against stable identities. Separate draft completeness from edit safety.
- Integrate revision-bound draft autosave/recovery, atomic save/admission and
  conflicts. Both modes consume the same draft owner; no second local graph store.
- Implement the current source/graph structure contract without old binary-map,
  generic-graph or draft-schema compatibility fallbacks. Rebuild identified stale
  demo fixtures where needed rather than migrating them. Preserve current-schema
  accepted content and media when edits stale them; no forged bindings. Add explicit
  setting/actual-graph validation and target adjustment previews.
- Gate: domain and API tests cover metadata retention, join impacts, cancellation,
  double submission, stale preview, reload, failure and currentness. Confirm the
  admitted canonical schema remains complete and playback-valid.

### G2 — Creator workspace and deterministic graph presentation

- Add the two mode entrypoints and graph-first shell through existing navigation
  gates. Implement automatic ranks/lanes/edge routing, one+ per row, readable option
  labels, natural page scroll, horizontal-only graph panning and clamped inspector.
- Add the resizable tall inspector without remounting edits; selected detail and
  graph stay synchronized. Expose current structure targets/checks and a return to
  Brief. Keep technical trace/repair in professional detail views.
- Gate: actual browser exercise **and** screenshot inspection at 1280×768,
  1280×460 and 1700×900, including 3–6 siblings, skip-level links, long labels and
  top/middle/bottom selection. No mobile or 1024px qualification.

### G3 — Real Story authoring, suggestions and review

- Story inspector shows summary, connections and expandable “场景、动作与对白”.
  Bind sections to accepted script episodes and all their scene occurrences. Use a
  lossless current-schema projection; do not discard supported screenplay fields on save.
- Reuse source/outline/branch/script task controllers, report reopening, candidate
  adoption, review and scoped episode revision/hash checks. Assistant-generated
  branches populate a reviewable draft, not mandatory blank manual forms.
- Keep characters/art references and source evidence reachable. Preserve per-node
  unsaved text through selection and mode changes or apply an explicit navigation gate.
- Existing generation is often stage/package-scoped. A node-context action must state
  its actual affected scope; do not ship a fake node-only generator. Independently
  scoped new backend jobs require a separately justified contract, not sketch parity.
- Gate: current-source task freezing, automatic result checking, retry/cancel/reopen,
  accepted report access, dirty conflicts and late/stale deliveries are exercised.

### G4 — Production inspector through existing production owners

- Show node→script scene occurrences→ordered cuts/shots via exact bridge bindings,
  never array indices or a one-video-per-node assumption. Present currentness and
  review status from existing owners. Explain missing/uninstalled/stale mappings.
- Reuse bridge preparation/whole-package review/explicit installation, storyboard
  approval, reference selection, keyframe candidates/review, video candidates and
  explicit selection. Preserve actual media-task safety and provider configuration.
- Route-only no-footage defaults and explicit footage inclusion use the G0-qualified
  contract, after any required bounded decision. Replace every demo action with a
  real supported command or a clearly unavailable explanation. Do not ship simulated
  readiness as real production.
- Gate: no automatic generation, approval or media selection; exact shot provenance,
  stale handoff suspension and existing selected playback remain correct.

### G5 — Integrated qualification, documentation and owner handoff

- Promote the sketch's acceptance checklist into Plotloom's permanent development
  workflow. Map all C01–C47 and P01–P06 to real features and candidate-bound evidence;
  rewrite demo-only claims and sample-reset items for disposable fixtures/preservation.
  Enabled production features cannot remain “deferred because this is a sketch”.
- Run the complete repeated user scenario and desktop visual matrix below, with
  native clicks, text entry, wheel/pan, keyboard and connection-drag operations.
  Independently inspect the final changes and evidence; fix blockers, rerun affected
  exercises and bind the final receipt to final source/static/package artifacts.
- Update creator documentation and visible desktop boundary. Verify credentials,
  protected settings and unrelated data are unchanged; document every exact demo
  reset/rebuild. A new runtime does not approve or auto-upgrade an authored graph.
- Run established full release gates, then publish/activate only under the approved
  implementation brief and verified quiescence/preservation procedure. No live
  provider calls, project promotion or creative acceptance are implied by UI delivery.
- Gate: owner starts a fresh walkthrough of the qualified real workbench. Engineering
  verification, owner UI acceptance and creative/media acceptance remain separate.

## Implementation entrypoints and regression anchors

Reuse and extend, rather than duplicate:

- Shell/state: `frontend/src/app/workspace/WorkspaceController.tsx`,
  `WorkspaceViews.tsx`, authoring persistence/recovery hooks and draft registry.
- Graph/domain: `frontend/src/pages/GraphPage.tsx`, `frontend/src/graph-editor.ts`,
  `frontend/src/model.ts`, `frontend/src/types.ts`; new cohesive workbench feature
  modules. Split affected oversized owners before adding more responsibilities.
- Source: `frontend/src/pages/SectionMapPanel.tsx`, `sourceStructureModel.ts`,
  `src/plotloom/source_outline_contracts.py`, `source_structure_validation.py`,
  `branch_suggestions.py`, `persistence/project/source_outline.py` and `drafts.py`.
- Validation: `src/plotloom/canonical_schema.py`, `validation.py`, topology planner,
  canonical persistence and authoring-draft API contracts.
- Story/production: `ScriptPanel.tsx`, `StoryPrototypePage.tsx`,
  `ProductionBridgePanel.tsx`, `StoryboardPage.tsx`, `production-bridge-handoff.ts`,
  existing keyframe/media/video controls; `persistence/project/script.py`,
  `production_bridge.py` and `production_bridge_projection.py`.
- Existing anchors: `frontend/tests/graph-editor.test.ts`; browser specs
  `graph-interactions`, `source-outline-section-map`, `project-folder-authoring-drafts`,
  `workspace-presentation`, `workspace-home`, `production-bridge-shot-handoff`;
  Python tests `test_project_storage_source_outline`, `test_production_bridge`,
  `test_production_bridge_intent`, `test_project_review_drafts`,
  `test_script_delivery_linkage`, and `generation/test_story_graph_topology`.

Contract references: ADRs [0056](../adr/0056-graph-typed-edge-entry-state-boundary.md),
[0059](../adr/0059-f1b-source-bound-section-map.md),
[0118](../adr/0118-brief-owned-source-topology.md), and the script/production
ADRs indexed in [the decision entrypoint](../adr/README.md). Historical binary
scope in ADR 0059 is reference evidence, not an executable contract to retain.

## Mandatory acceptance and release evidence

- Repeat the owner's scenario from a disposable clean fixture: add parallel 123 →
  add 222 → insert 333 → reconnect 123 to 222 → change 333's incoming source → edit
  its outgoing link → delete 333 with safe bypass → Undo → only-delete → Undo →
  exercise deletion of choice/join/ending/detached nodes → cancel → save/reopen.
  Observe graph, actual edges, option labels, previews and inspector after each step.
- Exercise clicks and connection dragging separately; do not infer one from the
  other. Check preview/commit parity, both arrows committed, metadata and downstream
  content retained, current opening protected, no partially committed failures.
- Check 3–6 parallel nodes, multiple decisions/joins, skipped levels, long graph,
  long Chinese text, detached/pending structure, Brief mismatch, capacity refusal,
  short desktop height, inspector resize cancellation and keyboard controls.
- Check both modes, fresh/recovered/conflicted drafts, stale candidates, reports,
  script/scene/shot identity, media selections, save-and-close and existing playback.
- Every UI revision uses the permanent checklist. Functional assertions and direct
  visual observations have separate evidence; screenshot existence is not inspection.
  No unexplained console/resource errors. After two repeated failed acceptance
  attempts, reassess root cause before another patch.
- Start with focused domain/API/browser checks; finish with the established
  [development gates](../development.md): lock check, configured lint, full Python
  and frontend tests, types, deterministic build/bundled static verification, full
  E2E, wheel build and installed-wheel smoke. Use disposable DB/fake transport for
  generation/media QA. Bind remote CI to the published candidate and distinguish
  pending from passed; never reuse old counts as new acceptance.
- Receipt names exact source and executable candidate, checks, observed screenshots,
  independent review, preservation evidence and any remaining gaps. Owner acceptance
  is recorded afterwards, not inferred from successful automation.

## Progress

- Planning: current architecture and v9 requirements inspected; bounded independent
  read-only contract audit and plan review completed. The owner clarified that
  installed productions are disposable demos, removing first-release migration
  requirements. No application code changed or tests executed.
- The owner approved G0–G5 implementation and explicitly required removal of
  encountered backward-compatibility code on 2026-10-06.
  A bounded independent read-only launch audit found no plan blocker and recorded
  concrete retirement candidates above; it ran no implementation or tests.
  No service activation, provider call, project/data reset, commit or push has occurred
  as part of this assignment. Delegation follows native task-creation permissions.
- G0 investigation: Relay worker `01a110d6-1520-7bb1-9d06-b88d89bafa14`
  registered to the retained manager; local `main` and `origin/main` matched
  `e542f49`. The isolated probe completed with zero provider dispatches: a
  nine-node/two- and three-option/one-join source-map round trip installed r1;
  a valid exact-edge insertion was rejected by planner equality; omitted
  decision/join scenes failed coverage and empty F4 episodes failed upstream
  validation. Existing branch/script linkage checks: 19 passed. The manager
  approved ADR 0120's bounded repair; positive current-contract proof and G0
  retirement/shared ownership qualification remain required before G1.
- G0 qualified: [contract receipt](../verification/2026-10-06-graph-workbench-g0.md)
  binds the current candidate, retirements and closed independent findings. Full
  Python 1,162 passed; frontend 512 passed; types, deterministic static build,
  lock and configured lint passed. Current route-only and footage-opt-in proofs
  pass through reviewed production and playback coverage. No provider dispatch,
  reset, activation, commit or push. G1 now owns shared draft commands/integration;
  G2–G5 remain unimplemented and unqualified.

- G1 qualified: [shared-operation receipt](../verification/2026-10-06-graph-workbench-g1.md)
  binds exact draft/CAS commands, recovery, Undo, retired competing UI owners and
  closed independent findings. Focused backend 58 passed; full frontend 511 passed;
  types and fresh static build passed. Source-map and current graph native browser
  exercises passed separately. No provider dispatch/reset/activation/commit/push.
  G2 now owns creator presentation; G2–G5 remain unqualified.

- G2 qualified: [creator-presentation receipt](../verification/2026-10-06-graph-workbench-g2.md)
  binds current source/static, 12 inspected desktop screenshots, four operation
  screenshots and closed independent review findings. Native browser six cases
  passed; full frontend 513 passed; app/E2E types and current static build passed.
  Repeated 123→222→333, real connection drag, deletion/Undo, capacity, reuse,
  retained-choice restoration and target preview are exercised. No provider
  dispatch/reset/activation/commit/push. G3 active; G3–G5 remain unqualified.

- G2 amended qualification: the dated receipt retains prior hashes and closes
  all-member row-parent inference and primary human preview labels. Native four
  cases, backend20 and frontend513 passed; types/static gates collected. Independent
  manager and attended read-only review closed those bounded residuals.
- G3 qualified: [Story receipt](../verification/2026-10-06-graph-workbench-g3.md)
  binds exact F4 scene occurrences, lossless scoped episode edits, dirty node/tab/
  mode/reload retention, current task/report controls and closed independent review.
  Backend28 plus linkage/branches19 passed; frontend515, types/static exit0.
  Native evidence is21 passing cases plus one separately passing repaired branch
  case, not a clean combined22 run. Prior failures and corrected report/selection
  diagnoses remain recorded. No provider/reset/activation/commit/push. G4 active;
  G4–G5 remain unqualified and full release/owner acceptance remain pending.

- G4 qualified: [Production receipt](../verification/2026-10-06-graph-workbench-g4.md)
  binds every repeated F4 scene/current cut and exact installed shot handoff,
  first-install-only footer, zero-write browsing and preserved production.
  Backend45, frontend528, clean combined native2 and existing media/playback4
  passed; types/static exit0. Independent read-only review found no G4 blocker;
  two viewport captures directly inspected. No provider/reset/activation/commit/
  push. G5 active: permanent checklist, final-candidate matrix, full gates and
  quiescent publishing/activation remain unqualified; owner acceptance separate.

- G5 locally qualified: [integrated receipt](../verification/2026-10-06-graph-workbench-g5.md)
  binds the permanent47C/6P checklist,39 hashed inspected desktop/Story/operations
  captures, closed stable independent review and source/static/wheel fingerprints.
  Python1182, frontend538/76, focused native37 and final full native190 passed;
  types, lock/lint, archived reader, deterministic build, isolated wheel smoke
  and compile gates exited0. Prior failed diagnostics remain recorded. Publication
  is pushed at `c8f59b7`, with full exact-revision remote CI running. Exact demo
  Graph/map retirement and normal activation are held by
  an independent retained native queued receipt, despite global busy=false;
  no reset, service stop/activation or provider dispatch has occurred. All normal
  project/application/files/credential fingerprints remain unchanged. Separate
  authority for exact native terminal reconciliation is required before resuming
  activation. Owner usability/creative/media acceptance remains separate.
