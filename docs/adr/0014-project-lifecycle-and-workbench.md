# ADR 0014: Project lifecycle and the authoring workbench

## Status

Accepted and implemented for M1-B0.

## Context

The existing create/get/patch path can persist canonical content, but it does
not define what makes a project selectable, archived, duplicable, or
irreversibly deletable. Treating archive as an ordinary content edit would
invalidate canonical revisions for an operational concern; treating browser
state as navigation authority would also allow a late request for project A to
replace the workbench after the user has switched to project B.

The resulting contract belongs at the project and workbench boundary, not in
individual stage editors or as a V1-compatible UI patch.

## Decision

### Lifecycle is separate from authored content

A project has an `active` or `archived` lifecycle state and an independent,
optimistically checked `lifecycleRevision`. Archiving or restoring changes only
that lifecycle revision; it does not manufacture a new canonical content
revision. Active projects accept normal authoring and generation work. Archived
projects remain readable but reject every content mutation, generation,
approval, and media submission.

Archive is refused while the project is busy: a non-terminal generation run,
work unit, or media task exists. Restore is an explicit lifecycle operation.
Both archive and restore require the expected lifecycle revision so a stale list
or second browser tab cannot silently change the state.

Permanent deletion is deliberately outside the ordinary project action path. It
is offered only for an archived, non-busy project, requires an explicit
irreversible confirmation bound to its stable project ID and expected lifecycle
revision, and removes its durable project-owned data. There is no implicit
delete on archive, browser close, route change, or failed save. Deletion must
not be represented as a reversible archive action or a background cleanup.
Execution artifacts are inline database evidence and cascade with their run.
`MediaTask.outputUri` is an opaque provider result, not a managed local-file
ownership record, so permanent deletion removes that reference but never
dereferences or unlinks its URI. A future managed blob store must establish
explicit ownership and cross-project reference checks before it may delete
files.

### Duplicate only reviewable canonical work

Duplicate creates a new active project with a fresh identity and revision
history. It copies the `ProjectBrief` plus the longest contiguous prefix of
canonical stages that is `READY` in pipeline order. It stops at the first stage
that is absent or not ready; it never skips ahead to copy a later stage.
Runs, work units, attempts, approvals, production units, media tasks,
artifacts, browser drafts, and lifecycle history are not copied. The duplicate
therefore starts as an independently editable draft, not as a claim that old
execution or approval evidence applies to it.

### Save is explicit; browser recovery is provisional

Canonical changes reach the server only through explicit Save, with the
appropriate expected content revision. `sessionStorage` may retain an unsaved
draft keyed by project ID, stage, and the authoritative revision from which it
was edited so a refresh can offer recovery. It is not a second persistence
system, does not auto-save or cross browsers, and cannot overwrite a fresher
server revision. A fresh authoritative read precedes recovery; a mismatched,
deleted, or archived project can show/discard the draft but cannot save it.
Successful save and explicit discard clear the corresponding draft.

### URLs own navigation; project-scoped work uses a navigation epoch

The URL is the sole source of truth for selected project, workbench page,
focused entity, and selected run. Create, switch, duplicate, archive/restore,
and delete navigate by changing the route; components do not maintain a
competing selected-project authority. Changes that replace the loaded project,
page, or run start a new navigation epoch and abort or ignore visible updates
from older work. Entity-only focus changes are deliberately lighter: they
remain browser-history addressable without cancelling a canonical save that
still belongs to the same loaded project and stage.

A response may repaint visible state only when its captured project ID, page,
and epoch still match the current URL. A server-accepted save nevertheless
clears the exact session draft that produced it. If its response arrives after
navigation made the visible cache unsafe to update, the project is marked for
an authoritative reload. A user already back on that project is revalidated in
a fresh read epoch immediately when no newer local draft would be overwritten;
otherwise the refresh remains pending and the draft conflict is made explicit.
Save single-flight state is generation-bound, so an obsolete completion cannot
strand the editor or clear a newer operation. This prevents stale asynchronous
work from cross-contaminating projects without reviving a draft that is already
canonical on the server.

### Plotloom workbench is original product work

M1-B uses a Plotloom-native three-panel authoring layout: project and asset
context on the left, scene/shot or stage work in the centre, and the complete
Inspector on the right. It preserves the desired short authoring feedback loop,
but is not a pixel-for-pixel reconstruction of Narrative Forge V1. Its layout,
navigation, empty states, and media placeholders serve Plotloom's canonical
contracts and must not import V1 runtime code or assets.

## Consequences and guardrails

- List results expose lifecycle state and lifecycle revision; archived projects
  are visibly distinct and remain available for read-only inspection.
- Project catalog cursors use immutable creation facts, rather than mutable
  activity timestamps, so a project updated while paging cannot move past the
  caller's cursor boundary.
- APIs and UI tests must prove stale lifecycle conflicts, busy archive refusal,
  archived write refusal, confirmed-delete boundaries, and the duplicate-prefix
  rule (including a gap before a later ready stage).
- Browser tests must cover explicit save, refresh draft recovery, draft/server
  revision conflict, route switching during delayed responses, and the
  three-panel workbench without media.
- Any future retention, export, or recoverable-trash policy is a separate
  decision. It must not weaken the explicit permanent-delete contract here.
