# Creator and Professional: agreed product / UX baseline

Consolidated 2026-10-22 from owner-approved requirements at `8d3b259a`.
This records agreed intent, not inferred behavior or new feature approval.
Existing C/P/E identities are retained. Detailed acceptance subchecks remain in
the [permanent playbook](../creative-workflow/graph-workbench-acceptance.md);
[engineering](workbenches-engineering.md), [architecture](workbenches-architecture.md)
and [conflicts](conflicts.md) are separate views of the same contract.

Primary approval: [October 6 plan](../roadmap/2026-10-06-graph-centred-creator-workbench.md),
[0119](../adr/0119-current-workbench-visual-roles.md),
[0120](../adr/0120-explicit-node-footage-mode.md)–[0123](../adr/0123-node-context-story-production-workflows.md),
[0127](../adr/0127-reusable-creator-lifecycle-acceptance.md), later scoped amendments
including [0132](../adr/0132-creator-ui-reading-boundaries.md),
[0138](../adr/0138-one-current-story-explicit-rebuild.md),
[0145](../adr/0145-current-read-authority-for-graph-and-directory.md) and
[0155](../adr/0155-recommended-creative-workflow-guide.md).
Later approved creator-completion requirements are consolidated below from
[the October 22 plan](../roadmap/2026-10-22-creator-completion-loop.md),
[0198](../adr/0198-delegated-disposable-qa-authority.md) and
[0204](../adr/0204-explicit-rejected-batch-take-replacement.md).
[Chat provenance](conflicts.md#chat-decision-reconciliation) does not create new scope.

## Shared purpose and state (C02, C27–C28, C34–C36, C51–C54, P01–P06)

- Two views of one project/current graph, root draft, settings and selection;
  no second story, graph writer or readiness authority. Navigation retains dirty
  and unsent fields, correct node/project ownership and explicit recovery.
- Creator is the graph-centred authoring/Story/Production view. Professional
  retains detailed structure controls and a pan/zoom technical canvas. Their
  presentation differs, not the authority to mutate the same admitted graph.
- A source-unbound accepted canonical graph is readable/playable under existing
  prerequisites but cannot be overwritten through source authoring. Creator
  keeps an automatic selectable chart/right read-only inspector; Professional
  keeps its technical canonical reader. Never fabricate a draft or binding.
- Saving a draft, confirming content and applying the route are separate whole-
  graph operations above/outside the node inspector, with shared truthful status.
  These actions do not imply media generation, approval, selection or deletion.
  Separately approved pre-video/batch automation retains its own explicit frozen
  authority ([0162](../adr/0162-pre-video-autopilot-authority.md),
  [0191](../adr/0191-whole-pack-human-material-confirmation.md),
  [0193](../adr/0193-batch-video-authority.md)); the manual-workflow separation is
  not a blanket prohibition on those independently scoped operations.
- Distinguish waiting, failed read, confirmed empty, incomplete, mismatch, stale,
  read-only and unknown outcome. Name the reason and available next step. Failed
  graph/Source retries read only; retained content does not restore write authority.
- The compact recommended six-step guide is advisory below the toolbar. Both
  graph views are step 4 with a separate view label, not a completion percentage.
  Existing guards and owning controls remain authoritative; at most one next action.

## Creator layout and visual roles (C03–C08, C45–C48, C55, E22)

- Deterministic longest-path ranks, stable sibling order, no sibling wrapping or
  free node-position dragging. Real nodes are cards; actual choice text belongs
  to directed edges, with distinct incoming lanes/skip gutters, not fake nodes.
- The borderless graph grows naturally: document owns vertical navigation, graph container
  owns horizontal scrolling/private `chartX`. Three to six siblings stay one rank.
- The right inspector follows the selected node's centre, clamped to usable
  workspace. Its body scrolls while header/actions remain reachable. Never move
  it below the graph on short desktop windows. Target height is `0.85 × full
  viewport height`, clamped to usable visible workspace, not 85% of the reduced
  usable height ([owner clarification](../adr/0122-creator-workspace-presentation.md#owner-clarification-of-inspector-height-2026-10-22)).
- Automatic width: 380px at content width >=1120px, otherwise 300px. Manual range
  300–520px, <=45% of content, preserving 480px chart plus divider gap. Native drag,
  keyboard arrows/Home/End/Shift and double-click reset are supported. Cancel,
  Escape, Tab, capture/divider/window focus loss restore the original preference;
  release commits once. No form remount, lost buffer/focus/tab/scroll or author write.
- Authoring supports desktop browser width >=1280px; short 1280×460 is included.
  The visible/documented boundary is not a promise of narrow/mobile authoring.
  Matrix: 1280×768, 1280×460, 1700×900. Unrelated readers/media have their own scope.
- Use current shared dark roles: 14px body, 19px workspace/16px section headings,
  12px support, calm surfaces, gold action/selection and sparse borders. Long
  Chinese/empty fields, selected state, focus and necessary operations stay legible.
  OS light preference does not imply an application light theme.
- Technical IDs/full structure are folded where specified; impact prose uses
  readable titles/kinds/options. Help is a description, not the input name.
  Structural help uses one normal-flow region after fields, with hover/focus/pinned
  precedence, accurate ARIA and no obstruction. Keyboard must reach main controls.

## Professional page and canvas navigation (C56–C57)

In both editable and canonical read-only Pro, ordinary wheel/two-finger scrolling
navigates the page, preserving intentional inner form/label scrolling. It does
not zoom or pan the graph transform. Pinch or visible zoom/fit controls zoom;
dragging the canvas background pans. Do not require moving the pointer to the
left rail to scroll the page. Creator and unrelated canvases retain their own
contracts. [Owner-approved decision](../adr/0122-creator-workspace-presentation.md#owner-approved-professional-page-and-canvas-navigation-2026-10-23).
Preserve supported Pro positions and canvas pan/zoom across mode switches within
the active project session. Reset this visual state on project change, reload or
close/reopen, not authored work or shared selection. Do not add durable layout
storage or new read-only dragging ([lifetime decision](../adr/0122-creator-workspace-presentation.md#owner-approved-professional-visual-state-lifetime-2026-10-23)).
Implementation and qualification are recorded separately in the
[alignment receipt](../verification/2026-10-23-workbench-spec-alignment.md).

## Exact structural editing (C09–C26, C33, C48–C50, C53)

- One + per actual Creator row adds only to that row. Infer a parent only if all
  members have direct choice input from the same decision. Otherwise ask/leave
  pending. A common join/ending default stays visible, editable and optional.
- Reuse retains a detached node's identity/prose/type/outputs. Exact-edge insert
  preserves incoming edge identity/choice/effects and original target/downstream;
  continuation/pending options follow the selected kind. Do not guess connections.
- Click and handle-drag edits share exact preview semantics. Independently edit
  each input/output, including compatible nonadjacent ranks. Displaced targets
  survive. Reject no-op, self/cycle, start input, ending output and illegal degrees.
- Editing-dialog consent and immutable structural-preview consent are distinct
  where applicable. Cancel each separately; in-flight preparation owns dismissal.
  Failed/stale/repeated confirmation cannot partially apply the result.
- Opening node is protected. Explicitly choose deletion method. Only-delete
  retains pending edge identity/text/effects and never cascades into media.
  Bypass requires the exact safe unique effect-free continuation; no guessed option.
- Type/opening changes and separate join-contract add/remove disclose exact
  before/after effects, direct input membership and removed fields. Retained join
  fields survive input changes. Clearing/removing an edge is not node deletion.
- One structural Undo restores its whole draft transaction and safe selection,
  not Brief, accepted Script, approvals or media. Newer explicit selection/content
  cannot be overwritten by late receipts. Invalid/unfinished JSON remains recoverable.

## Brief, authoring and admission (C29–C32, C35–C36, P01–P02, P05)

- Explain actual complete-route choices, endings, nodes, max options, joins and
  storyboard targets. Validate integers/ranges/relationships from current Brief:
  nodes <=128, choice degree <=6; do not inherit sketch-only 30-node/100-edge caps.
- Settings do not reshape the graph; graph edits do not silently raise capacity.
  Before/after target changes require explicit preview using actual graph counts.
  Current structure targets/checks and a return to Brief stay reachable from the
  graph workspace; moving every Brief parameter into an inline editor is not an
  approved first-release requirement.
- Incomplete/pending drafts may be saved but not confirmed/applied as complete.
  Distinguish structural error, incomplete and target mismatch. Fail atomically.
- Suggestions create a reviewable shared draft; current settings and actual graph
  freeze into each task. Confirmation/current source and application are separate.

## Story, production, reports and revision (C40–C44, C54, P03–P06, E10–E18)

- Story projects the exact accepted section/episode and every ordered scene
  occurrence, including repeated places. Scoped editing retains complete episode
  JSON and original ownership across node/tab/mode changes; recovery is explicit.
- Production lists all exact scene/cut coordinates and stable installed shot IDs.
  Current bound handoff enters the existing shot/media owner. Missing, stale,
  uninstalled or unknown authority suspends the action with readable guidance.
- Decision/join defaults are route-only, with no independent footage/time/scene/
  shot/media. Explicit inclusion changes require confirmation and downstream review.
  Route-only nodes still participate in routing/count/state validation.
- Prepare/send/check/cancel/read/accept/install/select stay distinguishable with
  truthful node versus whole-package scope. No invented node-only generation owner.
  Originals/reports remain readable without being rewritten after accepted edits.
- One same-project story can change after installation: confirmation/application
  makes affected production outdated, retaining old media. Explicit fresh whole-
  package review/rebuild, new relevant approval/current selections and all-route
  playback are required. A new proposal never borrows installed authority.
  This narrowly supersedes old first-install-only exclusions, not safety guards.

## Native completion, selective revision and status

These clauses consolidate the separately approved October 22 milestone, not new
C/P/E identities or a claim that the workbench audit exercised native generation.

- The bounded creator journey is saved Brief → native text/images → material
  review → video-batch setup and explicit Start → selective take revision →
  complete-pack review → ending playback → reopen. Imported-image examples and
  synthetic browser fixtures are not proof of native image completion.
- Routine creator recovery must not require scripts, raw IDs, a reviewer-name
  form, database edits or an operator-only API. Exceptional historical UNKNOWN
  capacity retirement has a separately approved operator contract; it preserves
  UNKNOWN outcomes/reservations/evidence and does not authorize replay.
- Batch generation fills missing clips and stops for one final whole-pack review;
  it does not automatically select clips for playback. Image/video completion
  navigation exposes the result without hiding the useful top section or losing
  dirty work. [The batch plan](../roadmap/2026-10-18-batch-video-production.md)
  owns the detailed flow.
- Per-take rejection records a concise reason and exposes the exact rejected-shot
  set. Selective replacement retains rejected history and good siblings, shows
  fresh versus reused work, and requires fresh English endorsement and explicit
  Start. Reused takes remain in complete-pack review. This bounded path replaces
  current unselected rejected takes before whole-pack approval; it does not imply
  replacement of already-selected clips or storyboard changes.
- Run/batch age includes waiting and must be labelled accordingly, not called
  active generation time. Status uncertainty shows the last successful check.
  Milestones belong to the current run/batch; reused media is labelled historical.
  Terminal views use recorded completion or labelled creation dates. A ticking
  age is not worker liveness; ETA and compute/phase duration are not promised.
- Agent UI QA requires explicit visible project-local opt-in, reset by navigation.
  Missing/failed/stale QA context refuses QA writes without falling back to a
  human actor. The server owns exact grant/currentness checks; technical audio
  inspection without listening never becomes perceptual or owner acceptance.

## Qualification is not a feature claim (C01, C37–C39, E01–E22)

Exact candidate/static/loaded resources, actual interactions and directly inspected
pixels are distinct from source review or old receipts. Create → Revise in the
same project → Recover requires scoped current evidence. Unexercised combinations
stay UNVERIFIED/PARTIAL. Agent QA, native-provider E2E and owner creative acceptance
are separate. The current audit is not permission to generate, mutate live projects
or repair code. See the dated audit for observations and limits.


## Project directory actions (C58, approved 2026-10-24)

Only the current workspace project offers 保存并关闭项目 / 退出工作区. Other rows
have explicit 打开 / 重新打开 / 恢复 according to their existing folder/lifecycle
state; archived open titles remain readable. Archived closed titles explain and
require Restore before capability-gated Reopen. 更多 holds management copying, archive,
noncurrent 关闭项目 and exact confirmed deletion. Keyboard and short-screen
reachability are required. Positive latest-run activity explains ordinary Close/
archive restrictions; incomplete/absent summary facts cannot claim idle or disable
supported deletion preview/current Exit. [ADR 0113](../adr/0113-project-save-close-and-force-exit.md#state-aware-directory-actions--2026-10-24)
owns the contract; the [dated plan](../roadmap/2026-10-24-project-directory-actions.md)
separates implementation, verification, activation and owner acceptance.
