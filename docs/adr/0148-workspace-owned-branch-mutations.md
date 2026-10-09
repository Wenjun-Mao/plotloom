# ADR 0148: Workspace-owned branch mutations

Status: implemented and independently reviewed; scoped frontend/browser
qualification passed, combined release/native qualification pending, 2026-10-09.

## Problem

Source→Brief→Source unmounts the branch panel. Its local pending ticket was
cleared although an admitted cancellation POST continued. The remounted panel
could read before commitment, expose a second cancellation and ignore the first
completion. Same-component basis tests did not exercise this boundary.

## Decision

A narrow workspace-owned operation owner retains per-project pending flight,
completion generation and readable error/unknown status. Prepare/cancel share
synchronous admission; unmount only removes subscribers. The panel owns task
GET data, acknowledging exact project/basis/read epoch/completion generation.
Completion causes a fresh GET; late precommit reads cannot restore obsolete
authority. Failed reads expose explicit read recovery, never mutation replay.
Bind accepted value/error to owner/project/basis/completion generation and read
retry identity in render, not only a passive effect. Mutation/adoption callbacks
must validate their own acknowledged identity before dispatch and publication.
No server/API change, compatibility fallback, persistent cache or automatic POST
retry is justified. Adoption remains a dirty-guarded read into a local draft.

Register sent flights with existing project quiescence. Close/snapshot drain,
force-close disposition and delete suspension join the admitted POST. They must
not await its subsequent GET: lifecycle already suspends reads, so that would
deadlock. Failed/unknown results refuse drainage until a matching successful
read establishes the current task. UI read acknowledgment and lifecycle POST
settlement remain distinct boundaries. No sent request is erased by “discard”.
Assign the joinable flight before notifying pending subscribers: a synchronous
subscriber can begin lifecycle drainage from that notification.

## Guardrails

Actual unmount/remount, A-B-A, same-project basis changes, late GET, rejection and
failed refresh; duplicate admission/readonly; each lifecycle disposition joins
the held flight and blocks new commands, including reopening after force-close.
Real-server desktop replay preserves source/graph and proves the visible
cancelled state. Retain stale-task cancellation eligibility and dirty-draft
protection. Do not infer native specialist cancellation from a task cancellation.

Qualification: [scoped receipt](../verification/2026-10-09-branch-mutation-ownership.md).
