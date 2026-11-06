# Paused implementation and checkout consolidation

> Storage update, 2026-11-06: historical worktree artifacts later moved under
> `.local/retained-worktree-evidence/` were retired by the [approved cleanup](../roadmap/2026-11-06-local-qa-storage-cleanup.md).
> Their paths below are historical, not available replay inputs. Recorded outcomes
> and limitations remain unchanged; current projects, qualification roots and
> the separate current recovery package were outside that removal scope.

Wenjun requested pausing the Last Projection implementation, retaining wanted
changes on local `main`, and removing the extra development worktrees.
The coordinator released source ownership and has no owned active command,
child assignment or generation. Resumption requires Wenjun's request.

## Source and evidence

The normal checkout `/Users/wjmao/projects/HU/plotloom` now owns `main`.
`af8998af` preserves the unfinished optional-media-review candidate: 37 files,
including ADR 0226, selection/handoff contracts, operator attribution, UI and
regressions. Its verification is incomplete and generated frontend assets are
stale. This checkpoint is not a release or product acceptance; see the plan's
current status for the retained failed/unknown checks and remaining work.

Independent source review found no unique wanted change in the older trees:
their source is already integrated or superseded on `main`. Their exact binary
patches, untracked bytes and dirty fork source are retained in
`.local/worktree-consolidation-20261030/source-snapshots/`; local
`refs/consolidation/20261030/*` retain their original heads. The inventory and
snapshot hashes were independently verified before retirement. The misleading
`submoduleHead` in the original validation-worktree inventory is Git's parent
fallback: that tree's submodule was uninitialized, not a separate fork revision.

Ignored evidence moved intact, with directory inode/device checks, to
`.local/retained-worktree-evidence/{original-worktree}/`. The existing single
qualified recovery moved unchanged to `.local/current-qualified-recovery/`.
`evidence-moves.json` records the mapping; retained records keep historical paths.
Only disposable environments/caches and preserved obsolete source were removed.
All five extra linked worktrees, including the chat's validation worktree, are
archived. The native handoff moved this chat to `/Users/wjmao/projects/HU/plotloom`,
and the normal checkout is restored to clean local `main`. Codex archived the old
worktree after the handoff. When implementation resumes, verify/re-register Relay
completion routing before reuse, replacing the coordinator if necessary.

## Qualified installation remains separate

The previous Docker and native bridge read source from the normal checkout.
Consolidating unfinished source there would have exposed it to the live app.
The existing verified recovery archive was therefore installed at:

`/Users/wjmao/Library/Application Support/Plotloom/creator-runtime/plotloom`

This is the installed qualified source, with standalone recovery Git metadata;
it is not a linked development worktree. All 3,261 recorded files match the
recovery manifest (source `37e65c41`, qualified runtime `985693fe`, fork
`35fac266`). The archive and wheel hashes remain unchanged. The existing locked
provisioning command created a new path-bound native Python receipt, and the
normal prepare path resolved its package/resources without dispatch.

At an empty native queue/slot checkpoint, the existing workbench was stopped and
its exact LaunchAgent definition retained. The bridge was uninstalled/reinstalled
through the existing installation path, and `manage.py start` recreated the
container from qualified source. Docker and the loaded bridge now use the
installation path above. Existing writable project/application paths, private
supervisor/token and H3 configuration paths remain unchanged. Manage this running
installation from that directory; running `start` from development `main` would
attempt to activate the unfinished candidate and is outside this pause.

## Executed checks and limits

- Independent source/mount/LaunchAgent/native-receipt review passed.
- All 14 previously readable project context GETs returned HTTP 200 with exactly
  the historical response hashes. Two pre-existing unreadable homes were not
  reclassified or repaired.
- Two retained selected-playback responses matched their exact derivative hashes;
  Range requests returned the exact first 1,024 bytes with HTTP 206. An initial
  probe used the original-media endpoint against a derivative hash and failed;
  the corrected probe used the documented selected-playback owner. No new media
  quality inspection or full browser acceptance is claimed.
- Preservation compared 1,312 files, 25 database snapshots and four protected
  files. Only two project databases changed: startup refreshed `claim`,
  `revision` and `updated_at` on their existing autopilot rows. All other logical
  tables, assets, settings, current grants and unresolved-dispatch evidence are
  unchanged. No UNKNOWN receipt or reservation was cleared.

Evidence is under `.local/worktree-consolidation-20261030/`, including source
inventory, evidence moves, before/relocated preservation, native preparation,
runtime start, HTTP and selected-media readbacks. No feature implementation,
fresh generation, full qualification, push or GitHub CI was performed for this
consolidation. Local source remains intentionally ahead of publication.
