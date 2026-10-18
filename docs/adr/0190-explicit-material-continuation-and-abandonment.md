# 0190 — Explicit material continuation and project abandonment

Status: accepted; implementation `dd3033d6` locally qualified, 2026-10-18.
See the [verification record](../verification/2026-10-17-material-continuation-and-abandonment.md)
for full-baseline and scoped corrective evidence; activation and hosted CI are separate.

## Problem

Cancellation withdraws automatic authority. One run per project and Brief-only
launch admission leave completed work without a new automatic continuation path.
Force Close exits the workspace but cannot prove unknown remote work is settled;
ordinary deletion correctly refuses its still-publishable project.

## Decision

Continue creates a successor run with fresh frozen execution authority and an
immutable predecessor link. Adopted checkpoints are inherited through exact
origin IDs and evidence hashes; original policies, attempts, receipts, decisions
and frame bytes remain unchanged. Shared provenance validation resolves the
original owner. Frames retain their original generation and selection decisions.
Admission rechecks the current material closure and uses project lifetime job and
image caps. Unresolved predecessor operations block continuation with their exact
job identity; cancellation, missing output and process death never permit resend.
The original stopped run may reconcile exact late evidence before continuation.
Terminal failure or not-started proof may permit a new successor operation.
Delivered but unadopted original candidates also block this continuation path;
they are not automatically relabelled or adopted by the successor. The observed
old project containing both an unadopted delivery and an UNKNOWN frame therefore
does not become eligible merely because the remote uncertainty later settles.
Continuation consent binds predecessor ID, revision and material closure. The
unique lineage leaf owns currentness; equal or backwards timestamps do not select
an ancestor or invalidate a real successor. Inherited frames resolve their exact
original selection decision owner independently of timestamps.

Abandon-and-delete is a separate explicit destructive command, bound to a fresh
server preview, revisions and exact title. Under project exclusion it obtains a
durable host dispatch/publication revocation before erasure. All recorded local
process groups and spawn windows require positive quiescence. Remote UNKNOWN
outcomes, reservations and host capacity stay truthful and retained. Revocation
is independent of current execution pins and survives restart or failed erasure.
Ordinary idle deletion remains available. Force Close means workspace exit when
safe close is refused; it does not mean backend cancellation or safe closure.
The automatic run must already be explicitly stopped. Other specialist-chat,
manual generation, video and provider work retain their ordinary blocking gates.
The installation lifecycle ledger retains only the exact deletion consent,
manifest/home inode and host revocation acknowledgment until erasure completes.
This is deletion recovery metadata, not a content backup. The directory exposes
pending deletions after restart even when erasure already withdrew the manifest;
retry requires renewed explicit title/uncertainty consent and never runs on read.
An unacknowledged request may refresh explicit consent only for the same home
inode and manifest, after rereading the server preview. An acknowledged revocation
is immutable. Retry revalidates the directory and held lock after lease acquisition
and anchors recursive erasure to the approved directory descriptor.
Recording the installation's host-revocation acknowledgment irreversibly
quarantines that pending project identity from new writable admission, even when
erasure fails before manifest withdrawal. Registry admission checks the durable
intent after acquiring the project lease; existing shared handles prevent the
exclusive acknowledgment transition. Reopen, lifecycle mutation, dispatch,
in-place upgrade and recovery copying/publication obey the same predicate.
Create/resume also check before publishing any home. Passive inspection,
directory and pending-deletion reads remain available and never resume erasure.
Only explicit original-consent erasure retry can finish the acknowledged intent.
Before acknowledgment, fresh preview/CAS remains required; a lost host response
does not create a stale-consent retry shortcut. No application transaction spans
project lease acquisition or filesystem erasure.
This quarantine is installation-scoped, not global revocation of retained bytes.
Composed recovery obeys its supplied installation ledger. The standalone portable
restore operator (ADR 0044) intentionally has no application-root authority and
still refuses existing identities/destinations; an external offline copy cannot
remove this installation's quarantine or grant it execution authority.
Abandonment reads the exact current or immediate-prior layout directly and does
not require upgrading an UNKNOWN project. Ordinary continuation uses the named
preserving schema upgrade after original ownership is resolved.
The directory has a separate passive deletion-only catalog for exact
`pre_continuation` homes: manifest identity, title and revisions, not a canonical
project summary or an eligibility claim. It excludes every identity with an
existing deletion intent and resolves duplicate identities across all manifests.
Listing takes passive read leases and makes no host calls, migrations or writes.
Only the dedicated abandon action is available; click obtains a fresh server
preview and new title/unchecked-uncertainty consent. Current project discovery,
opening and controller admission remain exact-current. Catalog errors do not
disable the independent current-project directory.
Exact prior-layout validation context must survive nested geometry, reviewed
source, cross-shot, frame and retained-handoff validation. Current mutation/session
entrypoints remain strict-current; table absence never selects a validation mode.
Geometry derivatives retain one canonical checkpoint owned by the preparation's
recorded origin run. Continuation copies are accepted only through exact adopted
predecessor links with identical evidence; every matching copy is validated, not
silently ignored. Original geometry/native decisions and bytes remain authority.

## Alternatives and consequences

Uncancelling or rebasing a frozen run would change old authority. A fresh project
would regenerate completed work. Clearing UNKNOWN or its reservation would invent
terminal evidence. These approaches are rejected. No additional service, automatic
backup, human approval or creative acceptance is introduced. Explicit migrations
preserve original rows and JSON. Regression coverage must bind inherited origins,
currentness, lifetime caps, no-resend, revocation races and exact project isolation.
