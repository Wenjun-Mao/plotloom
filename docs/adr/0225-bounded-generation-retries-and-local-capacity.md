# ADR 0225: Bounded generation retries and local execution capacity

Status: accepted for implementation, 2026-10-28, following the owner's explicit
“Agreed, make it happen.” Supersedes dedicated no-dispatch/forensic recovery and
older blanket prohibitions on automatic retries and dead UNKNOWN local slots.
Snapshot/restore and current user-valued work remain supported and protected.

## Decision

Remove the dedicated forensic/no-dispatch recovery workflow and its unactivated
size-limit expansion. Retain ordinary job status, actual outputs, process ownership
and accounting needed by execution; do not recreate recovery under another name.

New repeatable generation uses configurable automatic retries, default one retry
after the initial attempt. Each retry has a distinct existing job/attempt identity
and retained predecessor lineage. Never resend an already used identity. Persist
the allowance/current attempt so restarts, concurrent controllers and late results
cannot create extra attempts or overwrite the current result. Semantic content
correction remains separate from execution retry.

Before retry or local-slot release, positively confirm recorded worker, CLI and
validator ownership has stopped using the existing lifecycle. Timeouts and missing
acknowledgments alone are insufficient. A still-running local attempt is never
retried. Dead local occupancy can be released while remote outcome remains UNKNOWN;
that uncertainty and possible spending stay truthful. No forensic settlement,
project revocation/deletion or invented refund is required to free shared capacity.

Deleted-project garbage collection keeps its separate permanent-revocation and
positive original-home absence requirements. Its owner retains the absence
helper even though local-capacity retirement no longer uses it. Missing or
replaced installation paths, symlinks and inaccessible homes fail closed before
collection; local-slot release never grants project deletion or history erasure.

Every attempt still consumes the applicable original generation authority and
finite job/image/requested-second budgets. Possible prior spending is not credited
back merely because local work stopped. The owner accepts bounded possible duplicate
generation/cost. Authorization/configuration/permission errors that cannot improve
on retry stop immediately; explicit cancellation stays cancelled. Exhaustion creates
a clear failure for that job, with a manual retry under existing generation
authority; unrelated eligible work continues.

Fix demonstrated causes, including recognizing precisely supported benign
`clock.sleep` evidence in the normal parser. Unsupported events never become
successful output by assumption. Use existing controllers, immutable identities,
claims and budget owners, without a generic retry engine or deployment framework.

## Public control and read contract

New launch, single-video, batch and explicit language-check requests freeze
`automaticRetryLimit` (strict nonnegative integer, default 1). Persist actual
`automaticRetriesUsed` separately from total successors; a manual attempt does
not reset the automatic allowance. Older frozen omission grants no retry authority.

Read projections expose current physical job/attempt, retained predecessors,
used/frozen counts, pending/exhausted/stopped state and possible prior cost. The
language-check API keeps its logical check anchor stable while each successor's
request/receipt remains bound to its own real identity. Observation admits no work.

Native checkpoint retry projections use persisted physical-attempt classification
and current successor lineage. A repeatable failed/UNKNOWN current attempt still
awaiting local-stop reconciliation is `retry_pending`, never `ready`; a semantic
rejection, nonretryable stop, ungranted retry or superseded attempt is `stopped`.
The existing exhaustion marker remains `exhausted`. Projection performs no host
polling and grants no dispatch authority. The run may remain active for unrelated
work and explicit manual retry; exact checkpoint/activity/retry evidence owns the
failed job's visible outcome rather than an unconditional global run-state change.
Cancelled, taken-over, stale and handed-off runs have withdrawn automatic retry
authority: their read projection is `stopped` even when the retained physical
attempt remains failed/UNKNOWN or has an exhaustion marker. Preserve that attempt,
allowance usage, possible cost and history rather than rewriting its classification.

The existing project controller process lease also advances authorized standalone
language checks; run-bound checks retain their run controller. Admission claims are
atomic under the existing lifecycle transaction. Durable logical cancellation
fences prepared successors before cancellation RPC; GET/reconcile never dispatch.

Exact authenticated host observations durably acknowledge admission even while an
attempt remains spawn_intent. A claim alone never establishes acknowledgment.
Repeatable UNKNOWN checks with remaining retry authority wait for positive local
stop and reconcile; they do not dispatch a successor while an owner remains alive.
Checker read projections expose `executionPending` for this waiting condition,
independently from a semantic verdict or completed-result adoption.

Explicit manual retry uses UUID command identity and exact failed/current job and
attempt with the owning run/batch CAS. Native run, language-check and video-batch
owners expose `retry-execution`/`retry` actions; no semantic rejection is invented
for a transport failure. An acknowledged-or-lost-ack repeat cannot allocate another
successor, and changed ownership, cancellation, nonretryable errors, stale sources
or exhausted generation authority refuse. UI re-reads ambiguous results before
another action and never posts retry merely because a page opens.

Known capacity deferral belongs to the exact unacknowledged attempt, not the
run-wide blocker. Persist the authenticated typed `not_found + capacity_deferred`
fact in existing owner evidence; unrelated image work may leave the global blocker
empty. Re-admission of that same original identity requires this exact fact and
current execution authority. Consume the fact durably before another admission
RPC, so a lost acknowledgement cannot reuse it. A found/acknowledged attempt,
transport ambiguity or UNKNOWN never gains resend authority from an old marker
or UI blocker. No stop proof, terminal settlement, budget refund or new attempt
is inferred. Pause/cancel and namespace/provenance guards remain mandatory.

For native run checkpoints, this consumable control evidence is the optional typed
`executorAdmissionDeferral` member of `CheckpointEvidence`, excluded when absent.
It binds the exact executor attempt and immutable identity digest. It does not
alter append-only result facts. Recording, consuming and clearing use the existing
checkpoint CAS/command owner; consumption commits before the external RPC. No new
table, host request field, attempt identity or generation allowance is introduced.

Native bridge retry/correction keys retain the bridge installation scope at both
reservation and spawn-intent consumption; these owners use the same logical-stage
classification. During an explicit run cancellation, an exact already-persisted
terminal failed native bridge attempt may settle its publication owner through
the existing failure operation only after an authenticated matching host response
positively proves local stop. Preserve attempt/receipt facts, failure/refusal
classification, costs and checkpoints. This grants no retry or new dispatch and
does not weaken cancelled/UNKNOWN publication holds. Ambiguous, mismatched or
unproven-stop work keeps its hold; retained historical cancelled records are not
rewritten. Real permission/safety refusals are not automatically resumed.
Bridge adoption validation follows the existing decision's exact checkpoint ID
to the same-project, same-run physical operation key. A logical stage/owner name
cannot replace a correction/retry checkpoint identity on adoption or reopen.
Native evidence collection includes every exact physical retry/correction attempt
of each logical stage. Observed bridge attempt counts may exceed one; they do not
grant generation authority. Keep first-pass defined as accepted with exactly one
attempt and preserve the existing qualification metric. Policy and validated
lineage continue to enforce generation limits independently of this receipt view.

Pause fences pending execution owned by the current run. Adopted checkpoints are
already terminal publication evidence; inherited adopted checkpoints retain their
validated ancestor provenance and do not acquire new current-run attempt rows.
Skip adopted checkpoints during pending-execution suspension rather than looking
up or contacting historical process identities. Keep the exact missing-attempt,
identity and dispatch-disabled guards for every unadopted pending checkpoint.

## Existing attempts and acceptance

A transient SQLite lifecycle writer conflict during an ordinary controller step
defers that step. It is not an execution failure, a run blocker, a cancellation or
retry authority. The next ordinary step rechecks current owner/run/attempt identity;
persisted admission intent and UNKNOWN guards continue to prevent duplicate work.
Actual storage failures and contract violations keep their existing failure paths.
This closes an observed foreground-resume race before completed-image adoption.

The two identified old local holds may release only their positively stopped LOCAL
occupancy. Preserve the 苏棠 project, all media, original UNKNOWN/possible-cost facts
and every current home/H5 export. Do not retry, resume or drain the old H5 run.

Qualify default one/zero/configured retry counts, restart persistence, cancellation,
late-result/current-attempt ownership, concurrency, nonretryable errors, remaining
grants/budgets and independent continuation. One coordinator owns integrated local
qualification, supported activation and exact old-slot application. Real bilingual
text, images, H3 audio and four route plays remain required product evidence;
software checks or local-slot release do not establish media acceptance.
