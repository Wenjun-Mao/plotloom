# Historical UNKNOWN image attempts: operational closeout

Status: operationally closed after read-only review on 2026-10-24 Toronto.
Historical remote outcomes remain UNKNOWN. No host status, accounting reservation,
queue, grant, project or evidence was changed by this review.

## Finding and recommendation

These are two permanently revoked, deleted QA projects. Their local execution
capacity was already retired on October 22. Fresh supported native retirement
previews returned the original receipts, alreadyRetired=true, localCapacityState=retired
and remoteOutcome=preserved_unknown for both exact attempts.

Close both incidents operationally and retain their historical records. There is
no remaining execution-capacity recovery to perform. Routine preservation may
verify these rows, but unchanged historical UNKNOWN records are not unfinished
operational work or a reason to resubmit a request.

| Exact attempt | Deleted project | Existing retirement receipt | Retained accounting |
| --- | --- | --- | --- |
| 06e80972-9dde-41ff-be71-b477c1477465 | 765ce4d9-12e3-4d96-8944-b49ba381fdf2 | d7e5c374-bd43-401b-bc56-80202336a5e7 | One reserved image-budget unit |
| 3405616d-55a3-4f81-9dee-01e79550f25b | f03a5e3d-6a75-4f5c-b29a-21420ce9a7b6 | f352d7f5-1ca7-4e5d-a133-7d830374500f | One reserved image-budget unit |

The fresh host ledger records zero local execution slots, zero validator entries,
zero enabled queue entries and zero attempts in active execution states. Both
retirement previews have no blockers. All host table fingerprints match before
and after the read-only requests. The reservations belong to these deleted
projects; they are distinct from local concurrency slots and do not establish
whether any monetary charge occurred.

## Why the historical outcomes remain UNKNOWN

For 06e80972, retained stdout and a reported instruction-access denial lack a
completed-turn event and an observed process exit. They do not prove a terminal
failure or absence of dispatch. For 3405616d, refusal text, a completed turn and
genuine exit 0 exist, but the historical rg command's unbound configuration
prevents exhaustive no-dispatch proof. These limits are recorded in the
[original evidence review](2026-10-22-creator-completion-loop.md#authorized-local-capacity-extension)
and [content-ownership receipt](2026-10-19-automatic-image-content-ownership.md).

The existing no-dispatch recovery path also requires a publication-authorized
project and the original confined home/package. Both projects are revoked and
deleted. Restoring data, replaying work, weakening the proof reader or assigning
success/failure would not supply the missing historical facts.

The current attempt contract requires an unsettled image's project-budget
reservation to remain reserved. Administrative accounting disposition would be
a separate contract decision, independent of proving a remote outcome. It is not
needed to release execution capacity here. No accounting write-off is claimed.

## Executed review and closure boundary

At 2026-10-25T03:37:24Z, the manager used the existing authenticated container shim
to run only exec-capacity-retirement-preview for each exact project/attempt pair.
No retirement, settlement, retry, cancellation or generation command was sent.
The safe readback, counts and complete host-table fingerprints are retained at
.local/unknown-hold-closeout-20261024-root/native-readback.json.

An independent read-only contract review agreed with this operational closeout
and identified no supported stronger outcome from the retained evidence. The
manager checked the owning recovery, capacity and attempt-validation contracts
and independently verified the live receipts. Documentation-only verification
checks links, commands and the diff; no executable change or test rerun is required.

This is a completed operational assessment, not a new ledger terminal state or
creative acceptance. Reopen only for new authoritative evidence bound to these
exact attempts, or an explicitly scoped administrative-accounting decision.

Owning runbook: [local capacity versus remote outcome](../../services/creator_workbench/codex-exec-capacity-recovery.md).
