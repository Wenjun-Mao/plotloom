# Specification reconciliation and owner review

Baseline: `8d3b259a`, 2026-10-22. These are documentation/intent dispositions,
not permission to repair code. Clear supersession is recorded; uncertainty is
not silently normalized to current implementation.

## Owner review required

No unresolved intent questions remain in this bounded workbench reconciliation.
The owner accepted sidebar height, Pro page/canvas navigation and Pro visual-state
lifetime. Their decisions are recorded below. Design adoption does not approve
implementation, activation or the reported code repairs.

Sources: [approved plan](../roadmap/2026-10-06-graph-centred-creator-workbench.md#approved-reference-and-product-boundaries),
[ADR 0122](../adr/0122-creator-workspace-presentation.md),
[ADR 0121](../adr/0121-current-source-graph-authoring.md),
[C28/C45/C48](../creative-workflow/graph-workbench-acceptance.md).
Audit other unambiguous clauses independently; these questions do not invalidate
the whole baseline. Current code is evidence of an implementation choice, not
proof that the owner selected that choice.

## Resolved by explicit decision or scoped supersession

| Older wording | Current controlling clause | Preserve |
| --- | --- | --- |
| Sidebar height: full viewport versus visible/usable height | Owner accepted `0.85 × full viewport`, clamped to usable workspace; [0122 clarification](../adr/0122-creator-workspace-presentation.md#owner-clarification-of-inspector-height-2026-10-22), current C45 | Centre/clamp, internal scrolling, reachable header/actions, no 500px cap and side-by-side short-desktop layout; no code/activation approval |
| Professional ordinary wheel input inherited canvas zoom/scroll prevention | Owner accepted page scrolling, deliberate pinch/visible zoom controls and background drag-pan for both Pro views; [0122 decision](../adr/0122-creator-workspace-presentation.md#owner-approved-professional-page-and-canvas-navigation-2026-10-23), C56 | Intentional inner scrolling, Pro pan/zoom capabilities, current graph/selection authority; lifetime is the separate decision below. Design adoption is not implementation/activation approval. |
| Professional position/pan/zoom lifetime was unspecified | Owner accepted active-project-session retention across mode switches, resetting on project change/reload/close-reopen; [0122 lifetime](../adr/0122-creator-workspace-presentation.md#owner-approved-professional-visual-state-lifetime-2026-10-23), C57 | Shared selection/dirty/content/Creator preferences; no durable layout or new read-only positioning. Trade-off: reopening loses the custom Pro view. Implementation/verification remain pending. |
| First-install-only / general replacement excluded in the October 6 plan and ADRs 0079/0118/0121/0123 | [0138](../adr/0138-one-current-story-explicit-rebuild.md) explicitly supersedes first-install-only, enabling same-project reviewed rebuild | Source/CAS/currentness/dispatch guards, retained assets and separate fresh approval; not silent replacement |
| Shared canonical fallback reader originally used by both modes | October 22 [0122 amendment](../adr/0122-creator-workspace-presentation.md#workspace-presentation-is-independent-of-write-authority-2026-10-22) and current C02/C03/C28/C45 | Shared topology/fields; distinct Creator side inspector and Pro technical shell; no new write authority |
| Narrow stacking/touch qualification in ADR 0119 | October 6 approved workbench desktop boundary / ADR 0122 / C47 | No new narrow/mobile authoring scope; unrelated readers/media retain their own contracts |
| Old mandatory hosted CI or old capability-matrix authority | [0199](../adr/0199-local-release-qualification.md), current AGENTS and [ADR discovery guidance](../adr/README.md) | Historical failures remain failed; optional CI requires direct request; roadmap owns current approved scope |

## Different layers, not contradictions

- “Confirm once” is atomic immutable-preview application, not a prohibition on
  the distinct edit-dialog → preview consent stages in C53, nor a merger of draft
  Save / content Confirm / route Apply. Preparation owns temporary dismissal.
- Advisory guidance never mutates automatically. Separately approved automation
  may dispatch under its own frozen run/grant; that does not make navigation or
  an ordinary save implicit generation authority.
- A record marked proposed, candidate, in progress or separately qualified is not
  made accepted/current/shipped by appearing in the catalogue. Inspect exact
  clause adoption and its later receipt; uncertainty stays explicit.
- Architecture provenance is historical because its README explicitly says so;
  no owner decision is needed to stop calling it a fresh dependency map.

Unindexed ADRs and duplicate numbering are discovery defects, not proof of
product disagreement. The catalogue addresses discovery without renumbering the
two distinct `0040` records or inventing a missing `0164`.

## Chat decision reconciliation

Reconciled 2026-10-22 (Toronto). Primary source: this chat, titled
`narrative-forge main`, thread `01a04525-e907-7630-9640-78790d69e8ae`.
Read-only pagination reached 2026-10-02 UTC, covering the original October 5–6
workbench discussion/approval and later amendments through the current request.
Dates below are UTC; source plans may use Toronto dates. Other chats and earlier
history are not certified by this pass. Ambient app content, prototype clicks,
assistant proposals and forwarded `From:` worker reports are not human approval.

The original workbench choices have written owners. No definite chat-only
agreement missing from all documentation was established in this bounded pass.
The concrete gaps were incomplete consolidation and one incorrect approval-status
projection. That does not establish that every design discussion was captured.

### Direct decisions and current homes

Each turn reference below is in the source chat above. Proposal context and later
implementation approval are considered together; trying a sketch is not by itself
approval to change the application.

| Direct human decision | Primary chat reference | Current home and disposition |
| --- | --- | --- |
| Graph as main workspace, with capable Creator and detailed Professional views | October 5, `01a109eb-84b4-7893-9844-cb51528f580d`; naming agreement `01a109ed-029a-7161-8ec8-8ff46f7a2896` | [Approved October 6 plan](../roadmap/2026-10-06-graph-centred-creator-workbench.md), product shared-state clauses and ADRs 0121/0122 already capture one project/two views. |
| Centre of inspector follows centre of node, without leaving the screen | October 5, explicit clarification `01a10a22-a01e-7450-92a2-3415fafa1616`, then “That's settled” in `01a10a25-8b54-7691-be0a-f17541d468c0` | Product layout and [0122](../adr/0122-creator-workspace-presentation.md) capture it. The later owner follow-up below settles the previously unresolved height denominator. |
| One row-level plus; broad incoming-connection editing and deletion | October 5, `01a10c37-45a2-7cd0-8fec-09c70b29f022`; October 6, `01a10ea8-c85d-7ba2-812f-6607f02689eb` | Product exact-editing clauses and C09–C26 capture the approved safe operations, not unrestricted invalid links/deletion. |
| Story and Production organization | October 6, proposal `01a10ecf-f7f9-7253-8455-5f9ab0e0124a`, sketch trial `01a10ed2-5e14-7492-b770-d28c4bbf4a16`, later implementation approval below | [0123](../adr/0123-node-context-story-production-workflows.md), approved G3/G4 and product Story/Production clauses capture real workflows; sketch simulations do not establish production capability. |
| Natural full-height chart, taller/wider inspector, divider and desktop boundary | October 6, `01a10f2d-9cde-7420-8a40-a0c2886c4e80`; explicit divider implementation and >=1280px instruction `01a10f40-4bd4-77f1-9f2a-d681b047d2d8` | Approved plan/0122/C45–C47 already capture these. Restored the plan's omitted “borderless” requirement to the consolidated product view. |
| Reusable checklist each UI revision; implement the reviewed plan without obsolete compatibility layers | October 6, `01a10eb5-49d0-7732-9713-8484224d3f46`; explicit implementation `01a10f6d-9324-7400-a296-1fb9aea3cc6e` | [Permanent playbook](../creative-workflow/graph-workbench-acceptance.md), approved plan and current engineering owners capture this. Clean sketch resets are not authority to reset real projects. |
| Generate missing video clips, then one final review; completion-scroll fixes include images | October 18, chosen answer in `01a14f43-2bff-72e0-8772-a8e00efbb2fd`, addition `01a14f4a-0ba9-7053-b0fc-122b4ea5324f`, implementation `01a14f57-beed-7f21-885c-b96e3db4f548` | [Batch plan](../roadmap/2026-10-18-batch-video-production.md), [0193](../adr/0193-batch-video-authority.md). Added the product summary; generation does not auto-select playback media. |
| Remove reviewer-name paperwork; truthfully attribute delegated disposable-QA decisions | October 19, `01a153bc-7871-7ae3-8ef8-01b53eea924a`, explicit scoped delegation `01a153e0-cfb5-7342-8d1e-f2dc8f5ac015` | [0198](../adr/0198-delegated-disposable-qa-authority.md) and the later approved exact native-context amendment. Consolidated visible opt-in/reset, server authority and refusal without human fallback; original finite grants remain exact. |
| Create, revise and finish through UI: native images, selective replacement and truthful timing | October 22, planning agreement `01a1640e-dc54-74a0-a70d-b86b9fbc66a7`; explicit implementation/UI E2E/activation `01a16418-2f38-7472-9c18-93f979f7b895` | [Completion plan](../roadmap/2026-10-22-creator-completion-loop.md), [0204](../adr/0204-explicit-rejected-batch-take-replacement.md) and [verification](../verification/2026-10-22-creator-completion-loop.md). Corrected false proposal-only status and consolidated the already-agreed product/engineering/architecture clauses. |
| Exceptional safe capacity recovery, then minimize the demonstrated avoidable UNKNOWN path | October 22, explicit capacity answer message `01a1642e-b454-7f71-9c72-929dce1c0813` in the preceding turn; corrective implementation `01a1648c-6670-7f11-a69e-7fa5e567ccc5` | [0174](../adr/0174-bounded-fair-codex-exec-pool.md), completion plan/report. Operator local-slot retirement preserves uncertainty/reservations/evidence; it is not ordinary creator recovery or a universal UNKNOWN cure. |
| Restore Creator side-panel details instead of making both modes look alike | October 23, `01a1665f-88b1-7421-8f33-8affa4a169a4` | [0122 mode/authority amendment](../adr/0122-creator-workspace-presentation.md#workspace-presentation-is-independent-of-write-authority-2026-10-22), product baseline and [repair evidence](../verification/2026-10-22-creator-canonical-sidebar.md). Already captured; no new editing authority. |

### Documentation corrections and reasoning

The first map at `02604646` repeated the roadmap index's stale planning-only
status for the creator-completion milestone. The detailed plan and direct later
human approval contradicted that status. The correction belongs in discovery
and consolidation, not in application code or a new product decision. Completed
bounded E2E/composite qualification remain separate from GA, perceptual quality
and owner creative acceptance; the original failed runs stay failed.

Already-written completion requirements were missing or too thin in the
consolidated views: the native journey, ordinary recovery without operator tools,
selective revision with persisted-state recovery, truthful timing and visible
exact QA attribution. These now point to their existing owners. Native provenance
and the detailed report's listening/crop/intervention limits are retained rather
than promoted into a new broad acceptance claim.

The early idea of making all “剧情结构与分镜” parameters editable beside the
graph was broader than the subsequently approved G2 requirement: expose structure
targets/checks and a return to Brief. The consolidated product now makes that
reachable return explicit. Recommendation: retain Brief as the current settings
owner unless a later inline-editor change is deliberately approved. Reason:
preserve the reviewed first-release scope and avoid duplicate settings forms;
trade-off: editing high-level settings still takes navigation. This is not an
implementation deviation established by the initial idea alone.

### Remaining owner review

The owner subsequently accepted the sidebar-height recommendation in turn
`01a166e4-9f25-7df1-a9a7-e363d77a4348`: `Sidebar height - agreed`.
The same message reports Professional's wheel/page-navigation problem. The owner
then answered `Yes` to adopting the proposed interaction for both Pro views in
turn `01a166ee-121b-7b61-a53a-4f47deb49897` (October 23 Toronto).
The owner then answered `Yes` to retaining Pro positions/pan/zoom across mode
switches in the active project session, resetting on project change/reload, in
turn `01a166f5-3fed-7ef2-93a0-5ef6abd00f4b` (October 23 Toronto). Reopening loses
the custom view; shared selection and authored work retain their own contracts.
All three intent questions are resolved above. Design adoption and historical
implementation approvals do not authorize
the [four current code repairs](../verification/2026-10-22-workbench-spec-audit.md).
