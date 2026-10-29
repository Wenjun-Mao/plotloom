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

## Existing attempts and acceptance

The two identified old local holds may release only their positively stopped LOCAL
occupancy. Preserve the 苏棠 project, all media, original UNKNOWN/possible-cost facts
and every current home/H5 export. Do not retry, resume or drain the old H5 run.

Qualify default one/zero/configured retry counts, restart persistence, cancellation,
late-result/current-attempt ownership, concurrency, nonretryable errors, remaining
grants/budgets and independent continuation. One coordinator owns integrated local
qualification, supported activation and exact old-slot application. Real bilingual
text, images, H3 audio and four route plays remain required product evidence;
software checks or local-slot release do not establish media acceptance.
