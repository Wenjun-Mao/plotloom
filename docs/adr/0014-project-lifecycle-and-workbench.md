# ADR 0014: Project lifecycle and the authoring workbench

## Status

Accepted and implemented for M1-B0 and M1-B1. The complete local checkpoint
verification gate passed before the M1-B1 commit.

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

### Source workflow fragments select an accessible owner presentation

The creator sidebar's `stage=source` fragments are a presentation-selection
contract, not a request to scroll an aggregate page. `source`, `art`, `script`,
and `storyboard-review` each expose the matching main heading and only that
owner's working content. The existing source, Art, Script, and F5A components
remain mounted behind native `hidden` boundaries so a same-project fragment
change preserves local owner drafts without leaving inactive controls in the
focus or accessibility tree. Every owner keeps its own read/error/currentness
state; a failed source aggregate read must not hide an independently available
owner or replace its truthful state. Invalid fragments select source.

This belongs in the workbench presentation contract because routing, focus,
draft continuity, and independent owner failure semantics meet there. It does
not add production routes, APIs, persistence state, or dependencies between
the source aggregate and its secondary owners.

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

### M1-B1 keeps authoring relationships and recovery explicit

The four V2 canonical stages are edited as stable-ID records, rather than as
anonymous form rows. Authors can add, remove, and reorder the records owned by
their stage. A relationship that crosses a record boundary is a separate,
visible operation: reconnecting a graph edge, moving a Beat or DialogueCue, or
moving a Shot to another scene first presents its affected references and only
then applies an ID-preserving migration. Deletion likewise presents its impact;
the UI may not silently discard cross-stage references to make a form look
valid.

Server validation failures are authoring feedback, not an opaque HTTP error.
Current-schema write failures return a structured `422` with stable issue paths.
Request-body validation projects only `code`, `path`, and `message`; it must not
echo rejected input or validator context because defensive secret rejection is
part of this same boundary.
The workbench resolves either stable-ID or array-index paths to the relevant
record and editable field, selects it through the URL, and focuses that field.
It retains the complete issue list for cases where a path has no editable
target. This is intentionally a presentation of the server contract; browser
code does not reinterpret a failed validation as permission to install data.

A queued or running bearer-authenticated run may resume only when its exact
frozen profile has a server key or a session key in the current tab. Missing
credentials open a clear recovery state for that profile; the workbench must
not auto-resume with the active profile or silently switch models. Progress
polling stays small and secret-free, while prompt/response evidence remains an
on-demand trace view.

## Consequences and guardrails

### 2026-09-14 workspace ownership correction

The workbench retains one project-session identity: the URL route plus its
navigation epoch remains the only authority for currentness. Frontend file
ownership may separate profile/session-key state, directory paging, run
polling and trace evidence, and view components, but none may mint a second
route epoch or independently decide that a project response is current.
Authoring draft CAS remains owned by its existing autosave contract; a run
poll or profile refresh cannot clear a newer editor draft. This is a frontend
composition correction only: it does not change API bodies, server actions,
storage, lifecycle semantics, or the rule that frozen runs use only their exact
profile-scoped credential.

The correction therefore gives navigation, loader, canonical authoring save,
draft recovery, and lifecycle operations separate frontend owners. The
controller composes those owners around the one URL/epoch fact; it may cancel a
load or save when navigation advances, but cannot decide an aggregate response
is current or implement a canonical/draft mutation itself.

The final correction makes that ownership explicit in
`useWorkspaceSession.ts`: it owns the canonical snapshot, route ref, and one
navigation epoch. Loader, navigation, authoring, and run hooks submit named
transitions through narrow session contracts. A trace route with an explicit or
implicit run selection enters a pending state that removes any stale run,
progress, and evidence until aggregate hydration accepts a current selection;
abandoning that selection has a named cancellation transition. This prevents a
late load, poll, save, or trace selection from repainting a later route without
introducing a new API, persistence, or credential contract.

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
- M1-B1 tests must cover stable-ID add/delete/reorder operations, explicit
  relationship migration impact confirmation, server `422` issue-path focus,
  frozen-profile credential gating, and a real-browser exact-repair to
  approval/reload lineage. These are authoring and recovery contracts, not
  optional visual polish.
- Any future retention, export, or recoverable-trash policy is a separate
  decision. It must not weaken the explicit permanent-delete contract here.
