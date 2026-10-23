# Creator / Professional specification audit · 2026-10-22

Status: findings for owner review; **no application fixes implemented**.

Historical audit status above describes its original checkpoint. The subsequent
owner-approved repairs are tracked in the [October 23 implementation receipt](2026-10-23-workbench-spec-alignment.md):
findings 1–4 have source repairs and focused regression evidence; stable review,
final frontend qualification and activation are recorded separately there. Original
failed observations and their evidence below remain unchanged.
Code baseline `8d3b259a` (executable equivalent to installed `21c6d6be`);
all changes in this assignment are documentation. No activation, live-project
mutation, provider call, push or GitHub CI. The inspected browser origins are
fresh test-owned fixtures, not the owner's Safari page or a live-data surrogate.

## Result and deliverables

- [Spec map](../specs/README.md): product/UX, engineering and architecture owners
  by workflow, with decision history/scope/evidence kept separate.
- [Complete catalogue](../specs/adr-catalogue.md): all 214 pre-existing numbered
  ADRs plus documentation-only 0217, exact full-slug coverage, no renumbering.
- [Workbench product baseline](../specs/workbenches-product.md),
  [engineering contracts](../specs/workbenches-engineering.md) and
  [architecture responsibilities](../specs/workbenches-architecture.md).
- [Intent questions](../specs/conflicts.md): initially height formula and
  Professional visual-state lifetime, each with suggestion/reason/trade-off.
  The owner has since accepted the height formula; see the follow-up below.
- Four deviations below: three targeted browser reproductions and one source/
  rendered-control omission. Their proposed repairs are not approved or executed.

The workbench requirements were consolidated before implementation audit.
Other product domains are mapped to their existing owners, not fully rewritten
or behavior-audited. An ADR's presence/status excerpt does not promote agreement,
implementation, qualification, activation or creative acceptance.

## Findings — recommendations, not changes

### 1. P2 — Editable Creator lets a valid choice label overlap its target card

Requirement: C06/C07/C15, product baseline's layout/visual section; labels must
remain readable, distinct from real cards and associated with the correct edge.

Evidence: on test project `ad2d5a10-4d76-44dc-ae51-f19b68797df2`, entered a valid
300-character Chinese option through the real node-inspector input and saved
the draft. Independent GET confirms length 300 and unchanged topology. Its label
measured 182px wide × 360.796875px high with `overflowY=visible`/no max height;
the label rectangle intersected `branch-1` through the card's full 112px height.
Root directly inspected the [1280×460 viewport](../../output/playwright/workbench-spec-audit-20261022/creator-long-choice-overlap-1280x460.png):
the lower label text runs behind the target card instead of remaining readable.
The numeric measurement was taken before the short-window resize, at 1700×900.

Cause/layer: [CreatorChart](../../frontend/src/features/graph/CreatorChart.tsx)
renders the complete label in an absolute button; `.creator-edge-label` in
[creator-workbench.css](../../frontend/src/features/graph/creator-workbench.css)
line 37 limits width only. [creatorLayout](../../frontend/src/features/graph/creatorLayout.ts)
lines 3/51–57 uses fixed row spacing/label centres. Current draft and accepted
option schemas allow 300 characters. Canonical labels separately cap/scroll
height, so the recent canonical repair does not cover editable Creator.

Suggestion: bound editable labels within their reserved lanes, preserving the
entire text through keyboard-accessible reading and the existing exact-edge
editor, reusing the canonical accessibility pattern where appropriate.
Reason: repair the presentation/layout contract without truncating story data,
tightening the accepted schema or changing graph identity. Trade-off: long text
requires scrolling/expansion; fully expanded measured row spacing is an
alternative but makes long graphs substantially taller. Add editable long-label
card/label intersection and full-text keyboard checks after repair approval.

### 2. P2 — Professional canvas selection is disconnected from shared details

Requirement: C02/C07/C08/C28 and ADR 0155's shared-selection clause; two views
share selection and graph/details must agree, including keyboard operation.

Evidence: entering Pro from Creator with `结局 B` selected leaves details on that
node but zero `.react-flow__node.selected` elements. Explicitly focused the real
Pro node `choose`, then pressed native Enter: focused ID remained `choose`,
details remained `结局 B`, and selected-node class count remained zero. This is
browser DOM/keyboard proof, not a claim that a screenshot showed both offscreen
canvas and details simultaneously. Initial Pro captures were scrolled below
the canvas and are retained as context, not standalone selection-pixel evidence.

Cause/layer: [ProfessionalGraphWorkbench](../../frontend/src/features/graph/ProfessionalGraphWorkbench.tsx)
lines 23–26 omits `selected` and memoizes without the shared selected ID;
lines 57–67 supplies controlled nodes without a selection-change adapter and
forwards owner selection only on mouse click. `GraphNodeDetails` reads the
shared owner correctly. Installed React Flow keyboard selection does not invoke
that supplied click handler. The shared provider already owns correct selection
and late-receipt guards; replacing its authority would be the wrong layer.

Suggestion: project shared selection into Pro nodes and route native keyboard
selection to that same owner, keeping visual positions separate.
Reason: align canvas, inspector and navigation without a second graph/store.
Trade-off: selection events must avoid feedback loops and accidental authoring
writes. Guard mode entry, folded identity selection and keyboard activation;
Undo/late-ACK/drag manifestations remain unverified in this audit, not additional
reproduced failures. Position persistence is a separate unresolved spec question.

### 3. P2 — Canonical-only Brief target preview omits current graph counts

Requirement: C29/C30 and ADR 0122's explicit target-change preview: show current
actual graph counts alongside before/after targets. Source-less accepted graphs
are a supported read-only state and intentionally have no authoring draft.

Evidence: test project `59cc76bb-394c-443a-9fb2-c65167794ece` has the valid
four-node split. Its GET reports the explicit source-binding read-only reason
and `draft=null`. Changed node budget 4→5, opened Save's confirmation, and
directly inspected the [preview](../../output/playwright/workbench-spec-audit-20261022/canonical-target-preview-missing-counts.png).
It shows target deltas but says the graph draft does not exist and omits actual
counts. Cancelled rather than confirmed; full graph-workbench before/after JSON
is byte-identical. This is missing disclosure, not loss of the canonical graph.
Read-only persistence inspection after cancellation confirms formal node budget
is still 4; retaining a form draft is not target confirmation.

Cause/layer: [BriefPage](../../frontend/src/pages/BriefPage.tsx) line 134 passes
only `graphOwner.draft`; [BriefTargetPreview](../../frontend/src/features/graph/BriefTargetPreview.tsx)
lines 11–16 computes counts only from that draft. The display contract incorrectly
depends on write-capable draft availability, echoing the earlier sidebar root cause.

Suggestion: expose a topology-only count projection that accepts either the
current authoring draft or accepted canonical graph, explicitly naming the basis.
Reason: viewing actual structure must not require or fabricate editing authority;
reuse one counting semantics rather than duplicate route arithmetic.
Trade-off: draft and canonical counts can differ, so the preview must identify
which current view it describes. Cover canonical, draft and unknown-read cases.

### 4. P3 — Pro global actions omit currentness/prerequisite disclosure

Requirement: ADR 0155's global-control placement/status clause (lines 117–123),
product baseline's shared-state section. The advisory guide is not the owning
status for whole-graph Save / Confirm / Apply controls.

Evidence: `.graph-workflow-status` is absent in Pro; Root inspected the
[1700×900 controls viewport](../../output/playwright/workbench-spec-audit-20261022/pro-global-controls-no-currentness.png).
[ProfessionalGraphWorkbench](../../frontend/src/features/graph/ProfessionalGraphWorkbench.tsx)
lines 41–45 passes no status to `GraphWorkflowActions`, whose line 23 renders it
only when supplied. Creator supplies the admission reason. In the fixture with
no accepted Outline, Pro additionally enabled Confirm where Creator disabled it.
Confirm was **not clicked**: provider lines 305–306 reject missing accepted Source/
Outline before acknowledgement/flush, so this is not a write/authority bypass.

Suggestion: share the prerequisite-aware status/action projection with Pro rather
than copy status strings or relax provider checks.
Reason: show the actual reason/next step beside the controls and avoid inviting
an operation that is known to refuse. Trade-off: modest presentation coupling
to the existing shared projection; preserve Pro's distinct geometry and detailed
controls. Test status and action availability together in both modes.

## Coverage and limits

These rows are coverage dispositions, **not blanket PASS badges**. A source review
can show an owner/guard exists without proving every interaction/state works.
The full permanent checklist and subchecks remain authoritative.

| Existing checks | Audit disposition / evidence |
| --- | --- |
| C01 | Executable diff unchanged; seven assets match prior qualified build. Fresh checked-static cases run; no live Safari loaded-resource readback claimed. |
| C02–C05 | Mode/readonly distinction, ranked rows, scrolling and sidebar inspected in source; six canonical and three editable layout cases pass. Pro selection deviation #2 remains. |
| C06–C08 | New editable long-label and Pro keyboard deviations #1/#2 reproduced. Retained canonical label/readability checks remain valid; not a universal accessibility pass. |
| C09–C14 | Add/reuse/insert/exact connection owners and immutable command path source-reviewed; row+ geometry in existing layout cases. Full operation combinations not rerun. |
| C15–C18 | Label/card deviation #1; real-card/edge/preview/cancel ownership source-reviewed. Native drag/connect permutations not newly exercised. |
| C19–C26 | Safety, endpoint preservation, explicit deletion and safe bypass paths source-reviewed; no new destructive operation or refusal matrix run. |
| C27–C28 | One shared owner, field ownership and mode navigation reviewed; canonical selection/mode tests pass, Pro projection fails #2. |
| C29–C32 | Current Brief/count/target owners reviewed; canonical preview deviation #3 reproduced. No parameter changes confirmed. |
| C33–C36 | Shared Undo/CAS/ACK/read/admission guards reviewed; no complete delayed-receipt/Undo replay in this audit. Pro currentness disclosure #4. |
| C37–C39 | Independent read-only review and fresh isolated fixtures; no owner reset or whole-product/human acceptance claim. |
| C40–C44 | Story exact section/scene projection, lossless JSON ownership, route-only modes and guarded installed-cut handoff source-reviewed. No new provider/media acceptance. |
| C45–C47 | Supported three-size cases pass; right sidebar/resize cancellation retained. Height formula was unresolved during the original audit and is now settled by the owner follow-up; real OS blur not exercised. |
| C48–C50 | Type/start/join/edge buffers and exact previews source-reviewed; no complete native conversion/join/delete/Undo matrix. Pro position lifetime was unresolved at initial audit and is now settled by the owner follow-up. |
| C51–C53 | GET-read withdrawal/recovery, project/epoch guards and consent stages source-reviewed; prior unchanged nine graph-read recovery cases retained, not rerun here. |
| C54–C55 | Existing entrypoints/help ownership inspected; Brief target-preview journey reproduced. Not every source/report/help state visually replayed. |
| P01–P02 / P05 | Brief→source→shared graph basis and target separation reviewed; no new source/suggestion generation or adoption. |
| P03–P04 / P06 | Task/report/projection and exact identity owners reviewed; no new cancellation/reopen/media-lifecycle qualification. |
| E01–E22 including dotted subchecks | Mapped to the existing playbook; full Create → same-project Revise → Recover, provider quality, all-route playback and whole-product E22 visual acceptance remain UNVERIFIED by this assignment. |

The prior `21c6d6be` sidebar/selection/horizontal-owner repair is already present
and passes the affected cases; it is not reported again as an open defect.
Pro's technical canonical list/pan/zoom and non-Creator geometry are intentional,
not deviations. Narrow/mobile support, new Pro layout persistence, and a replacement
story/version manager are not inferred requirements.

## Execution and evidence

Read-only workers used explicit requested GPT-6.1 Sol / Medium for workbench
baseline/Creator and independent Pro review, GPT-6 Luna / Max for catalogue review.
Effective settings were not separately audited. Root was the sole doc writer and
new browser executor, independently checking the cited source and screenshots.

New run (unchanged source, fresh fixtures):

```sh
PLOTLOOM_E2E_RETAIN_PARENT=/Users/wjmao/.codex/worktrees/b30f/plotloom/.local/workbench-spec-audit-20261022/fixtures \
  uv run --locked --no-sync python scripts/verify.py focused \
  --playwright e2e/creator-workbench-layout.spec.ts
```

E2E typecheck and **9/9 cases passed** (32.2s browser; 34.494s runner). This did
not cover the newly reproduced defects. The initial `SPEC:307` selection was
refused before execution: the native focused policy accepts whole-file specs.
The permitted whole file then provided fresh fixture roots for attended checks;
no test/assertion/code was edited. Existing 1,483 frontend unit and 20 focused
browser evidence from the preceding repair is retained for unchanged inputs,
not represented as a fresh full suite or this audit's complete coverage.

Attended browser loaded the shipped `/v2` assets using the existing typed offline
fixture server with blank provider keys. One test-owned draft label was changed
through UI and saved; its topology stayed unchanged. Canonical target adjustment
was cancelled rather than formally confirmed; ordinary Brief form draft autosave
also wrote only within that test fixture. Both actual origins were isolated fresh
roots; no live app access.
Console checked on the editable tab: zero messages/errors/warnings.

Retained harness limitations: first Pro mouse click was offscreen under the long
canvas, so the subsequent key sequence is not keyboard evidence. After checking
the installed CLI's callback signature, explicit focus + native Enter produced
the separate successful observation above. No forced click, app-state injection,
assertion weakening or product patch was used. Pro native drag feedback and Undo
remain unverified; the two then-open intent ambiguities were not counted as product failures.

[Logs, JSON observations and fixtures](../../.local/workbench-spec-audit-20261022/)
and [browser snapshots/captures](../../output/playwright/workbench-spec-audit-20261022/)
remain local. The documentation convention deliberately links existing owners;
it does not rewrite historical ADRs, old evidence or the original sketch.

Closeout checks: all 215 current numbered ADR slugs occur exactly once in the
catalogue; all 416 relative file/directory targets in the eight new documents
resolve (a path check, not a general external-link/anchor crawler).
`git diff --check` passes and the diff outside `docs/` is empty. All seven static
files still match the preceding qualified build. Source/catalogue reviewers found
no remaining concrete report blocker. The owned CLI browser and both test servers
were closed; disposable evidence remains. The installation was not switched or
restarted and no live project was accessed.
A staged whitespace check caught extra trailing blank lines in the generated
catalogue; they were removed before the final baseline-to-HEAD diff check.

## Owner handoff

All three intent questions are now settled. Suggested next step after review:
authorize one bounded repair slice for selection, label containment, count
projection and status parity with the proposed regressions. These share
presentation/authority seams but do not require backend permission changes.
Reason: address concrete observed defects first while preserving the agreed
graph ownership; trade-off is leaving unrelated unverified lifecycle/media states
for their separately scoped qualification. No repair is scheduled or started.
The [October 23 alignment plan](../roadmap/2026-10-23-workbench-spec-alignment.md)
now proposes that delivery together with adopted C56/C57 Pro behavior, with
explicit early UI proof, qualification and activation boundaries. Implementation
approval is still pending.

## Chat reconciliation addendum

The owner's follow-up asked whether chat-agreed designs were absent from docs.
[Direct chat reconciliation](../specs/conflicts.md#chat-decision-reconciliation)
covers the original workbench design/implementation decisions and later relevant
amendments, with exact human-decision references and bounded history coverage.
The central map's false proposal-only status for the approved/completed October
22 creator milestone was corrected alongside its stale roadmap index. Buried
native-completion/recovery/replacement/timing/QA clauses and small layout/Brief
discovery omissions were consolidated from their existing approved owners.

These documentation corrections do not change the executable baseline or the
four reported code findings. Newly explicit native-workflow clauses link their
existing bounded completion evidence; this audit did not freshly replay those
provider/media journeys or certify their unexercised combinations. The two
intent questions were left open with recommendations at that checkpoint. No definite chat-only
agreement absent from all docs was established in this bounded pass; other chats
and earlier history remain outside its coverage.

Addendum checks: all 391 relative file/directory targets in the eight changed
documents resolve; the 215 numbered ADRs still occur exactly once in the
catalogue, and all 22 cited chat turn/message IDs occur in the read primary
history. These are path/reference checks, not a general anchor/external-link
crawl. `git diff --check` passes; the diff outside `docs/` is empty. Independent
read-only GPT-6.1 Sol / Medium source cross-check and GPT-6 Luna / Max final
consistency review found no blocking documentation issue (requested settings;
effective settings not separately audited). No software suite, browser or
provider journey was rerun for this documentation addendum.

## Owner height decision and Professional scrolling follow-up

The owner accepted `0.85 × full viewport height`, clamped to usable workspace,
and reported that scrolling over the main Professional area zooms the canvas
instead of moving the page. Exact source: chat turn
`01a166e4-9f25-7df1-a9a7-e363d77a4348` (October 23 UTC / October 22 Toronto).
The [0122 clarification](../adr/0122-creator-workspace-presentation.md#owner-clarification-of-inspector-height-2026-10-22),
product baseline and C45 now record the accepted height formula.
[useCreatorGeometry](../../frontend/src/features/graph/useCreatorGeometry.ts)
lines 38–39 already targets `innerHeight × .85` before available-space clamping;
this source observation is not new browser qualification.

Professional wheel diagnosis: editable
[ProfessionalGraphWorkbench](../../frontend/src/features/graph/ProfessionalGraphWorkbench.tsx)
lines 57–67 supplies no explicit wheel policy. Its source-unbound path enters
[CanonicalGraphReader](../../frontend/src/features/graph/CanonicalGraphReader.tsx),
which invokes [CanonicalGraphCanvas](../../frontend/src/features/graph/CanonicalGraphCanvas.tsx)
without Creator's selection callback; lines 117–119 therefore leave the wheel
props undefined. Installed React Flow defaults enable wheel zoom and scrolling
prevention. Its wheel handler calls `preventDefault()` before graph zoom, matching
the user's observation. This is a presentation/input-ownership issue, not a
graph, persistence or dispatch failure. No live browser reproduction was made.
The installed version is React Flow 12.11.5. Disabling `zoomOnScroll` alone would
still consume ordinary wheel input through the wrapper; the proposed policy
must also allow native page scrolling with `preventScrolling={false}`.
Current mocked presentation tests assert inherited Pro defaults, not actual
wheel propagation, so they do not establish that page navigation is usable.

This new usability report is distinct from the four earlier deviations: the
old contract preserves Pro pan/zoom but did not specifically settle ordinary
wheel ownership. [Proposed interaction](../specs/conflicts.md#owner-review-required):
ordinary wheel/two-finger scroll navigates the page, deliberate pinch or visible
zoom/fit controls zoom, and canvas dragging pans. Preserve intentional inner
form/label scrolling and both editable/canonical Pro paths; do not apply a
global wheel rewrite or disable Pro navigation. Reason: remove the left-rail
pointer workaround. Trade-off: wheel-only zoom becomes explicit. Canvas-state
persistence is a separate unresolved decision. Editable Pro already has visible
zoom controls; extending equivalent controls to canonical-only Pro is part of
the proposal, not an existing capability claim.

After approval, native regressions should check wheel over background/nodes/edges,
document movement with unchanged graph transform, intentional pinch/controls/pan,
inner scrolling, both authority states and short desktop windows, with no
authored writes. No implementation, tests, generated assets, activation, provider
calls, push or CI are part of this follow-up.

Follow-up documentation checks: 346 relative file/directory targets resolve,
whitespace checks pass and the diff outside `docs/` is empty. Independent
read-only review found no blocking inconsistency; no runtime test was run.

## Professional navigation decision adopted, 2026-10-23

The owner answered `Yes` to adopting ordinary wheel/two-finger page scrolling,
deliberate pinch/visible zoom controls and canvas-background drag-pan for both
editable and canonical read-only Pro. Direct source: turn
`01a166ee-121b-7b61-a53a-4f47deb49897`. The preceding proposal/diagnosis records the
state before this adoption; [0122](../adr/0122-creator-workspace-presentation.md#owner-approved-professional-page-and-canvas-navigation-2026-10-23)
and the product baseline now own the agreed behavior. C56 adds native acceptance
coverage without renumbering existing checks.

Current code still inherits the diagnosed wheel defaults. C56 is not implemented
or newly verified, and no old browser pass establishes it. This is a gap against
a newly adopted contract, not a claim of violating a previously explicit wheel
rule. Pro visual-state lifetime was still unresolved at that checkpoint. No code/test/static,
runtime, project, provider, publication or CI change follows from this design
adoption; implementation remains a separate authorization.

Adoption documentation checks: all 350 relative file/directory targets in seven
changed documents resolve, all 215 numbered ADRs retain exact-once catalogue
coverage, and whitespace/documentation-only diff checks pass. Independent
read-only consistency review found no blocker; no runtime test was run.

## Professional visual-state lifetime adopted, 2026-10-23

The owner accepted retention of supported Pro positions/pan/zoom across mode
switches within the active project session, resetting on project change, reload
or close/reopen. Direct approval: chat turn
`01a166f5-3fed-7ef2-93a0-5ef6abd00f4b`. [0122 lifetime](../adr/0122-creator-workspace-presentation.md#owner-approved-professional-visual-state-lifetime-2026-10-23)
and the product/engineering/architecture views now record it. Shared selection,
dirty content and Creator preferences are not reset by this Pro visual boundary.
C57 adds mode-retention/reset acceptance without claiming implementation or a pass.

No intent question remains in this bounded reconciliation. The four original
deviations and newly adopted Pro navigation/session requirements remain unfixed
or unverified as recorded; no application/test/static changes or activation are
part of this documentation closeout. Implementation needs separate authorization.

Closeout documentation checks: all 408 relative file/directory targets in nine
changed documents resolve; 215 ADRs retain exact-once catalogue coverage and C57
occurs once in the playbook. Whitespace/documentation-only diff checks pass.
Independent review's authorization-wording clarification was incorporated;
no runtime test was run.
