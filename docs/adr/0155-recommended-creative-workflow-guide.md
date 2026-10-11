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
