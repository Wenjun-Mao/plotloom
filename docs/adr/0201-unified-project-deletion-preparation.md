# 0201 — One prepared project deletion flow

Status: accepted for implementation, 2026-10-19; source qualification is separate.

## Problem

Every current-project row offered ordinary deletion and automatic-material
abandonment before inspecting either command's prerequisites. The latter never
cancelled a run: paused runs were rejected, while projects without automatic
attempts were told to use the other command. Global generic busy feedback hid
the task that actually required attention. A paused run is not an idle project.

## Decision

One **删除项目…** entry obtains a passive server deletion preview. The server
chooses ordinary deletion, supported explicit stop, stopped automatic-material
abandonment, or an exact blocker. An ordinary idle project requires one exact-title
confirmation. Stop and abandonment additionally require explicit acknowledgement
that remote UNKNOWN outcomes and reservations remain truthful. Neither preview
nor cancelled consent mutates tasks, revokes authority, or erases content.

Any retained Codex Exec attempt selects the guarded host-abandonment path, including
terminal attempts: a pre-confirmation process-absence observation alone cannot
qualify a final ordinary eraser with no host revocation owner. Ordinary erasure
independently refuses retained Exec records under its exclusive lease. Cancelled
publication rows never make retained UNKNOWN work ordinary-idle.

Only the existing automatic-material cancellation/abandonment ownership domain
can offer stop. Host packet/attempt identity validation remains required, while
host erasure/quiescence blockers are not prerequisites to request supported exact
cancellation. They remain required after the stop and at final erasure. Cancellation
acknowledges withdrawal of local automatic authority and a supported stop request;
it never attests remote cancellation or process termination. Existing host process
ownership predicates alone decide whether a signal is safe. Unrelated/manual publications, text/media/video work and active
video batches retain their blocking gates. Archived/closed projects with a run
that still needs control must first be restored/reopened. Immediate-prior homes
retain their passive deletion-only catalog and original preview path, with no
upgrade to admit stopping. Pending acknowledged erasure retains its original
exact receipt/consent retry contract (ADR 0190).

The stop endpoint checks exact run ID and revision in the actual lifecycle write
transaction, alongside title, project/lifecycle revisions and a confirmed scope
hash. Scope binds the home inode, current material authority and recorded work
identities. It deliberately excludes transport status changes caused by stopping;
new material, a successor run, new work or another home requires fresh consent.
The existing control service owns cancellation and pending-work cleanup. Its text
and image controllers cancel only their named owner domains: the required running
image regression exposed both controllers cancelling the same executor attempt.
Partitioning at those owners removes duplicate requests within one command. No
unknown remote cancellation, process signalling exception, broader revocation,
UNKNOWN clearing or reservation release is introduced.

An admitted draft that settles after preview changes the consented material
scope. Final deletion refuses that old consent, preserves the newer local typing,
and resumes its existing queues. After those edits settle, a new preview and
explicit confirmation can delete the project. Waiting for admitted transport is
not permission to silently widen the previously confirmed scope.

After cancellation commits, the server rereads deletion preparation and returns
it with the acknowledged cancellation. This avoids deadlocking the browser's
existing project-read suspension. Failed rereading leaves cancellation acknowledged
and deletion blocked. The client checks the fresh scope before the final command;
both ordinary and abandonment erasure owners also check the supplied scope under
the exclusive project lease. A compare-before-write GET alone is insufficient.
Base direct deletion and prior/pending consent remain their existing contracts;
the prepared current-project flow always supplies the scope hash.

The lifecycle owner keeps one synchronous command token through preparation and
execution. A cohesive deletion hook owns consent, per-project phase/error feedback,
read/write quiescence and cleanup. Unsent drafts are discarded only after an
acknowledged erasure. Cancellation ACK followed by deletion failure is reported as
stopped but not confirmed deleted. Lost ACKs remain unconfirmed; neither a refused
request nor observation automatically retries, falls back or resumes destruction.

## Alternatives and guardrails

Always-visible specialized controls, frontend-only eligibility, automatic fallback
after 409, treating pause as idle, and adopting a newly wider post-stop scope are
rejected. Keep ordinary idle deletion least powerful. Regressions cover exact run
CAS, paused ordinary-delete refusal, late material changes at both final erasers,
UNKNOWN retention, manual blockers, lost ACK/no replay, isolated idle home erasure
and retained prior/pending deletion. No migration, service, deployment or provider
change belongs to this decision.
