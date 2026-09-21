# ADR 0074: Native Codex image-specialist dispatch

**Status:** Accepted

## Context

P1.5 already freezes an image package and validates a specialist completion
manifest, but a creator had to move a `Copy` assignment into a Codex task and
manually refresh the gallery. The initial trial also exercised a storyboard
shot instead of the intended accepted-cast Characters flow. Relay forwarding
is reporting, not application transport. The recent H3/Qwen capability is not
an admitted Plotloom image backend.

## Decision

The optional local runtime uses the supported `codex queue --thread … --message
…` CLI to send one immutable package path to one explicitly configured,
persistent image-specialist task. The task ID and the one-in-flight reservation
live only in host-local runtime configuration/state, never in project data,
packages, manifests, or gallery provenance. Queue acceptance is not completion.

Before queuing, Plotloom writes the existing confined package and records the
job exported. This applies equally to storyboard image jobs and to accepted-cast
character-reference proposals; both retain their existing repository/package
owners and validation paths. A crash-safe local reservation prevents every
retry for that job, including an ambiguous queue outcome. One host-local
in-flight job is allowed. Only an accepted or inapplicable delivery releases
the global reservation. Cancellation and an immutable package conflict stop
publication but are not evidence that the native task stopped; queue timeout
or any nonzero CLI exit is equally ambiguous. Their leases remain reserved
until a terminal delivery is admitted, rather than allowing a second specialist
call to overlap a possibly running first one. Before a later job is rejected as
busy, Plotloom may reconcile only the exact local task/job lease through the
supported Codex App Server `thread/read` status: `idle` releases it; `active`,
`notLoaded`, errors, or an unreadable response do not. This host-local status
check neither rewrites the package nor treats product cancellation as worker
termination.

Releasing on cancellation, package conflict, or a nonzero queue exit was
rejected: each is product or caller state, not a worker-stop acknowledgement.
Timeout-based or blind stale-lease cleanup was also rejected because it could
overlap two specialist executions. Lease acquisition, release, and idle
reconciliation share one host-local lock, so a stale completion cannot remove
a replacement lease.

Characters presents two distinct creator operations: creating a proposal only
freezes its accepted-cast request; **发送给 specialist** explicitly queues it.
The accepted-cast gallery automatically observes current exported proposals
through the existing refresh endpoint. Existing package/hash/currentness
validation is the sole publication path, so a stale, cancelled, foreign, or
late delivery remains non-publishing, and automatic observation never selects
a candidate.

## Consequences

- The specialist is replaceable behind this small runtime adapter; no provider
  registry, new candidate store, or queue framework is introduced.
- An unavailable/busy/unknown native task is an actionable dispatch state, not
  a reason to fall back to manual copying, H3, Qwen, or automatic retry.
- A queue receipt and a real ImageGen result are separate evidence. Creative
  acceptance and image selection remain explicit creator actions.
