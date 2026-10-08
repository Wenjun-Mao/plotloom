# ADR 0140: Native Codex dramatic-intent candidates

Status: implemented candidate; software qualification and native acceptance are separate.

## Cause and decision

The creator launchers compose native specialists but no API intent executor or
text admission. The existing intent executor requires a frozen API profile;
native text packages define no dramatic-intent stage. This is a missing bridge
capability, not a missing credential or a transport alias.

Add `bridge-intent` to the existing creative exchange with a local specialist and
local contract pin. Native intent jobs use the existing bridge job owner, with
an explicit transport and frozen request; they have no API profile. The request
owns project/job identity, proposal revision/hash, source inputs, replacement
target and every bounded target's source identity. The specialist owns only
complete `id`/`suggestedText` suggestions and a deterministic derived report.

Preparation freezes a candidate package and its execution pin. An explicit send
uses the installation's text specialist registry and its existing reservation,
receipt and unknown-outcome guards. Persist dispatch intent before attempting
the send. Send first rechecks the clean current execution pin against the stored
project-owned pin, before reserving, marking dispatch or queueing. Preparation's
check alone is insufficient: checkout drift between preparation and send would
otherwise consume a lease for execution the specialist must refuse. A mismatch
or dirty checkout leaves the queued request and its pin untouched; send never
regenerates authority. Unknown sends cannot be resent; inspection after restart reads the
same package/delivery and receipt, without starting a new job. Cancellation
prevents admission but retains reservations until a validated real delivery.

Delivery verification checks the frozen package, exact execution revision and
skill hashes, manifest identity, file hashes, deterministic report and strict
complete suggestions binder. The project owner rechecks current source, exact
proposal and replacement target under its transaction. Cancelled or stale jobs
retain delivery evidence without changing the proposal. Duplicate checks do not
append another revision. Failed, partial or wrong-identity deliveries cannot
release a reservation or become content.

A fresh complete delivery creates a new `model_suggested` proposal only. The
author must explicitly save the whole intent package, review presentation and
confirm production through the existing contract. There is no autoaccept,
provider fallback, credentials rewrite or historic request migration.
Qualification exposed a shared review gap: API delivery marked model suggestions
installable, and installation checked only `pending`. Both transports now retain
an explicit review conflict until `author_saved`; installation enforces that
state independently. The UI allows saving an unchanged complete suggestion
package, so author confirmation does not require a meaningless prose edit.

API inference remains an independent capability. Runtime API and native
availability are separate, truthful projections; a missing text specialist is
native `not_configured`. Current schema adds native job fields and rejects old
folders through the existing exact-schema classifier, without a backfill.
Remove the encountered pre-pin historic recovery helpers and recovery column.
Current frozen pins remain project-owned; a missing pin fails closed rather than
being inferred from a historic commit. This does not retire current terminal
delivery reconciliation, operational recovery or snapshots.

## Alternatives and guardrails

Reject pretending Codex is an API profile, copying API credentials, a second
queue/transport, automatic resends, and accepting partial suggestions. Focused
regressions own identity, currentness, cancelled late deliveries, restart/report
reopening, unknown-send reservation preservation and explicit author review.
The real UI-origin native job and same-project rebuild journey remain acceptance
work after a clean committed software-qualified checkpoint.
