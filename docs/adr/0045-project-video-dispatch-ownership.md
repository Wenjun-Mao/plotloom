# ADR 0045: Project-video lifecycle and installation dispatch ownership

## Status

Accepted, 2026-09-14. This advances the direct format-7 project-folder
composition after ADR 0044. It does not cut over the retained runtime,
migrate retained ledger rows, alter the gateway, or permit a paid provider
call.

## Context

Project video jobs, their review decisions, downloaded bytes, and their frozen
H3 request evidence must survive copying a project folder. Conversely, an
installation-wide allowance and an in-flight network-dispatch identity cannot
be copied with a project. The old Wan pilot puts both concerns in one SQLite
transaction. Project and application databases cannot truthfully make that
claim.

## Decision

The direct composition has a typed project-video repository over the
project-local SQLite schema and a separate application dispatch ledger. The
project database owns the job/request snapshot, provider identity, local output
hash and path, review decisions, and selection. Downloaded MP4 bytes are
written through the project-owned artifact store, so local playback and
snapshot/restore need neither the old application database nor a gateway URL.

The application database owns immutable dispatch identities, reservation state,
and append-only events. A globally unique dispatch identity is reserved before
the project records a dispatch claim; the claim is persisted before any upload
or submit request. Since this crosses two databases, a failed or unknown
intermediate operation retains a conservative reservation. Only the proved
pre-dispatch cancellation path releases it. Repeating a request returns its
existing identity rather than reserving twice. A missing accounting bootstrap
disables paid dispatch rather than synthesizing a new 100-second allowance.

Each direct H3 prepare freezes a typed binding of adapter ID/version and a
secret-free fingerprint of the configured transport instance. The fingerprint
is derived locally from validated configuration; project evidence contains no
API key, authorization header, userinfo, endpoint, or signed URL. The current
transport must produce that exact binding before preflight, upload, submit,
poll, or download. Two H3 endpoints therefore cannot become interchangeable
merely because their adapter and selected profile match, including during
known-ID restore reconciliation.

H3 is a separately configured development backend. Its frozen H3 profile and
request contract are project evidence, but it never mutates the historical Wan
allowance. Missing or mismatched H3 configuration fails explicitly and never
falls back to Atlas. Tests use the existing typed fake H3 transport only.

The direct project-video lifecycle is composed with a ledger-free media owner.
It accepts only the exact versioned `local_capacity_v1` H3 policy; an absent,
unknown, or paid policy is rejected before a project row, reservation, or
transport call. The retained Wan lifecycle remains the sole owner of its
same-transaction pilot hooks and historical 15/100 allowance tables.

Portable recovery records unfinished video rows as explicit recovery
operations. Restored known provider IDs may be explicitly reconciled/downloaded
only with a separately configured, matching frozen backend. Unknown and
pre-dispatch work remains unknown/not-submitted; recovery never submits,
regenerates, or fabricates a remote outcome. Close treats every nonterminal
video row as a local busy condition. A cancel intent remains local and does not
assert remote cancellation.

## Consequences

The direct project-folder API can prepare, submit, reconcile, cancel, review,
select, and range-serve project-owned video with its existing H3 client
contracts. Its direct composition is intentionally separate from the retained
runtime until a later cutover. Temporary test fixtures may explicitly initialize
or import application accounting facts; this milestone does not mutate retained
15/100 Wan records or perform a ledger migration.

## Rejected alternatives

- A cross-database transaction claim: SQLite transactions cannot span the two
  independent files.
- Copying the application database or allowance into a snapshot: it would leak
  installation state and make a copied folder replenish or double-spend budget.
- Replaying an interrupted request or falling back to Atlas: neither is safe
  evidence of a non-dispatch, and both can spend or regenerate unexpectedly.
