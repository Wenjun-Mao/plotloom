# ADR 0155 — Recommended creative workflow guide

Status: accepted, 2026-10-10.

## Context

Plotloom has a suggested creative sequence across existing routes, but each
page owns its own controls and state. Creators need a compact way to orient
themselves and see one useful next step without turning the sequence into a
wizard or creating a second approval authority. Source, accepted outline,
branch-map admission, canonical stage heads, playback prerequisites and local
draft navigation already have separate owners.

## Decision

Show one always-visible, compact guide directly below the workspace toolbar on
the Brief, source/outline, branch, creator, production/review and storyboard
routes. It presents the six recommended steps, expands to show current status,
and offers at most one context-aware navigation or playback action. The guide
is advisory: manual graph authoring, return navigation and all existing save,
confirm, install, and unsaved-draft guards remain authoritative.

Derive workflow status from existing project, source-review, branch-task and
stage-head reads. Share one project/revision-scoped source-review owner across
the guide and source/graph views; coalesce concurrent reads and reject late
results after project changes or mutations. A branch-task observation is usable
only for the exact outline, accepted-map and Brief basis it read. An outline is
current only when its source revision matches; an applied branch additionally
requires exact source, outline, map, graph revision and content-hash agreement.
Unavailable reads remain unknown. Playback status only invites a player check
when its required stages are present; static reports are explicitly reading
only. The source editor reports its transient dirty state to the guide so the
guide can suppress navigation while source text is unsaved; save and navigation
guards in the owning page remain authoritative. A blank workspace without a
project is labeled unsaved, while a project still being loaded remains unknown.

## Alternatives and consequences

Page-local hard-coded progress would duplicate status ownership and drift from
the existing admission rules. A blocking wizard would restrict the supported
hand-authored and return paths. A separate server endpoint or persisted guide
state would add authority and storage without new product capability. The
chosen guide adds no persisted state or generation behavior; unknown status
can make guidance less specific until the owning read succeeds.

Regression coverage must retain route/phase mapping, currentness and hash
checks, failed/read-only states, playback versus static-reading language,
source-draft action suppression, unsaved-versus-loading status, supported
desktop visibility and the existing draft-navigation dialog.

## State-specific next controls (2026-10-10 refinement)

The owner walkthrough found that delivered branch suggestions still received
a generic instruction. Route selection correctly advanced to the branch step,
but task-specific instructions were incorrectly nested in the outline step
and therefore unreachable. The guide must select its next instruction within
the current step, naming the actual owning control when its state is known.

Observe the existing graph-draft owner using the same dirty/completeness checks
as the branch editor. Delivery invites review and optional import; import is
not confirmation. A complete dirty draft points to its confirm/save control,
an incomplete draft requires missing fields, a clean confirmed map points to
route application, and only a matching applied route invites the creator view.
Loading, failed, stale, busy, read-only and unsaved-source states take precedence
over unavailable actions. Observe the owning branch panel's edit restrictions,
including partial page-read failures; a shared source read alone cannot prove
its controls are available. The named manual refresh retries both the page read
and its shared graph-draft read without replacing unsent edits. No new persisted guide state, approval authority or
automatic mutation is introduced. Regression tests must traverse this actual
route/state sequence and failed-read recovery, not merely assert the step number
or sticky geometry.

## One graph, two editing views (2026-10-10 refinement)

The walkthrough exposed a classification mismatch: professional graph editing
selected branch preparation (step 3), while creator graph editing selected step
4, despite both consuming the same graph-draft owner. Both graph routes now
belong to step 4, `剧情图编辑`; the active view is labeled separately. Source-page
branch preparation remains step 3. The index denotes the current activity, not
a completed percentage or a persisted monotonic progress counter. Switching
graph views must not imply loss of progress, new graph copies or acceptance.

Label the workbench switch as two views of one graph, and mark only the actual
graph route selected (neither on other pages). Both views retain the same
admission/read guards and independent save, confirm and apply operations;
navigation uses the existing draft protections. Regressions must check both
directions, shared unsaved edits/selection, unchanged canonical versions and
failed/read-only states rather than merely making the displayed number sticky.

## Confirmed graph response handoff (2026-10-10 refinement)

The filming-mode regression exposed missed writers: graph confirmation returned
the accepted section map, and application returned the current graph admission,
but the provider discarded both responses and refreshed only its graph/project.
Both graph views and the guide still consumed the older shared source review.
The exact-map apply guard correctly rejected the first mismatch; after successful
application the UI still reported that the graph was waiting to be applied.

After a successful, project/epoch-owned section-map confirmation or application, the graph
provider must publish its returned source review to the existing workspace read
owner before the independent graph/project refresh. The required callback is wired once
by the workspace, not separately by each view. Replacement invalidates older
in-flight source reads using that owner's existing epoch; late confirmations
or applications after project changes must not publish. Failed writes publish nothing. A failed
or superseded follow-up graph read retains the successful confirmation outcome
but still blocks graph operations under ADR 0145.

Do not relax exact-map admission, infer acceptance from a local checkbox, create
a second review owner, or require a page reload. API payloads, persistence, CAS,
separate confirmation/application and production currentness remain unchanged.
Regression coverage must retain the returned review, failed-write and held-read
boundaries, project-switch isolation, both views' apply path and installed-media
preservation after an explicit footage change.

## Whole-graph action scope (2026-10-10 refinement)

Save, confirm and apply operate on the whole graph, not the selected node.
Placing them in the Creator node inspector falsely suggests node-scoped approval.
Both views therefore use a shared, labeled whole-graph action region above the
canvas, outside node details. Keep operation captions, the no-video-generation
notice and graph currentness status with those global controls. Node selection
must not change their scope; all existing handlers and admission rules remain
unchanged. Regressions check this separation and native confirm/apply behavior.

The confirmation caption must describe approval, not imply another draft-only
save. Confirmation flushes pending edits and records a new accepted section-map
revision, without applying the route. If an applied route exists, confirmation
marks its old admission/graph context stale; dependent production needs review
against the new version. Show this consequence before the action, including
step 5/6 for script, storyboard and production review, and preserve the distinction
between outdated status and deletion. Existing artifacts are retained and none
of these actions generates video. Keep this explanation shared by both views
and associated with Confirm for assistive technology. It documents existing
semantics, not a new confirmation gate, automatic application or forced rebuild.

## Applied-route production entry (2026-10-10 refinement)

An applied route must not leave the compact guide at generic graph-editing
advice. On both graph views, show the verified applied status separately from
one concrete next instruction: select the first reachable section requiring
footage, by its accepted title, and open the Creator `制作` tab for step 5/6.
Professional view first names its existing return-to-Creator control. Follow
topology from its start identity, not section storage order or node selection;
skip route-only and unconnected nodes. With no reachable footage, ask the
author to check filming requirements rather than claim production is complete.
If the target title is not unique across visible graph sections, ask the author
to select a filming node on the current route instead of naming an ambiguous
single target; identity uniqueness does not imply title uniqueness.

Only show current application when exact admission/head identity checks pass
and the shared graph-draft read is ready, editable, settled and matches the
accepted map. Pending field buffers are unconfirmed edits: name the pending
input and its existing blur-to-submit action rather than asking for unrelated
node/choice/connection edits. Dirty/incomplete,
stale, failed, busy and read-only states take precedence; confirmation without
application points to Apply. The guide observes existing owners, adds no
persisted state, and performs no selection, approval or production mutation.
The step index remains the current graph-view activity, not a completion ratio.
Guard status/instruction transitions after native confirmation/application and
both-view desktop visibility as well as the pure state projection.

The step name is orientation, not a clickable control. The October11 owner
correction supersedes conditional prerequisite advice: the guide must observe
actual Script and source-storyboard accepted review state before naming the next
control. Lift the existing Creator production read into one workspace observer
shared by both graph views, the guide and the Creator inspector. Read unchanged
Script, source-storyboard, canonical storyboard-review and bridge APIs; keep
all writes with their existing owners. Do not infer acceptance from stage heads.

Missing, pending, reopened and retained review states name their owning sidebar
entry and state-specific review task. Current Script and source-storyboard
identities must match before directing the author to the whole-package review;
installed mirror identities must also match before naming `镜头审核与媒体`.
Accepted review currentness owns the authored-route versus canonical-graph
distinction: production installation can rebind canonical graph/Bible heads
without changing authored content. Do not reject current accepted reviews merely
because their frozen canonical graph identity predates that rebind.
Loading, failed or inconsistent reads explicitly remain unknown and name the
existing Production retry control. Key reads by project/revisions/binding and
activation, suppress late responses, and recheck on return from review pages.
Story/Production tab and graph-view switching share that read and do not trigger
another request or change the verified advice. This is advisory observation,
not tab tracking, approval, generation or a new admission gate.

## Retained Source display and guide priority (2026-10-10)

Pending or failed source reads take precedence over dirty-buffer instructions.
Retaining an editor for review does not restore currentness or permission to
confirm. The guide must first ask the author to wait or retry the read, then
return to unsaved-draft guidance once verification succeeds. Guard both read
states with dirty buffers in the model and native browser refresh regressions.

## Script-page task progression (2026-10-11)

The Script-page guide must observe the active ScriptPanel's read and operation
state, not repeat generic review advice before a candidate exists. Publish a
project/activation-owned advisory observation from that existing owner, with no
additional API read or write. Loading/failed reads, busy operations and unsaved
chapters precede missing, prepared, delivered and accepted instructions. Name
the actual prepare, retry, confirm or continue control. Clear observation on
page exit and reject late observations after project changes; retained evidence
does not restore current review authority.

An active replacement candidate retains the previous accepted script without
making that candidate stale. Project the candidate's own review status first;
retained old evidence only blocks continuation on that old version. Guard fresh
replacement preparation and delivery as well as first-candidate transitions.

## Preparation prerequisites and Art progression (2026-10-11)

The continued owner walkthrough rejected Script preparation because Art was not
confirmed, while the guide repeated Prepare. The Art page also offered generic
review advice without a candidate. Observe the active Art or Script panel's
existing read, operation failure, draft and style-selection state through one
stage-scoped advisory channel. A structured prerequisite rejection must name
its existing owning navigation, rather than repeat an action the server denied.
Do not infer prerequisite readiness from a missing candidate, add duplicate
reads, or turn technical generation/delivery into creative acceptance. Art
preparation requires a chosen style; its text proposal and reference images
remain distinct. Stage changes invalidate old observations just like project
and activation changes. Existing admission and all mutation payloads stay owned
by the panels and server.

The same walkthrough then reached missing Role settings. Extend that existing
channel to the mounted CastPanel's verified read, selected style, operation,
draft staleness and existing design-validity guard. Role advice must not request
review before preparation, nor name a disabled confirmation when required
personality/appearance fields are invalid. Keep text confirmation distinct from
appearance-image generation and from Art/Script acceptance. This is the same
advisory contract; no new read, mutation, automatic dispatch or creative approval.

Role's existing parent read must revalidate on workspace refresh, just as the
Art/Script owners do. Scope its readiness to the current project/refresh token;
pending or failed reads may retain display but cannot enable Continue or image
actions, or republish old acceptance as current advice. Use the same Cast read
owner, preserve editor buffers and reject obsolete completions; no guide-owned
request or automatic acceptance.
