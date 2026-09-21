# ADR 0074: Native Codex image-specialist dispatch

**Status:** Accepted

## Context

P1.5 already freezes an image package and validates a specialist completion
manifest, but its `Copy` action depends on a human moving an assignment into a
Codex task and manually refreshing the gallery. Relay forwarding is reporting,
not application transport. The recent H3/Qwen capability is not an admitted
Plotloom image backend.

## Decision

The optional local runtime uses the supported `codex queue --thread … --message
…` CLI to send one immutable package path to one explicitly configured,
persistent image-specialist task. The task ID and the one-in-flight reservation
live only in host-local runtime configuration/state, never in project data,
packages, manifests, or gallery provenance. Queue acceptance is not completion.

Before queuing, Plotloom writes the existing confined package and records the
job exported. A crash-safe local reservation prevents every retry for that job,
including an ambiguous queue outcome. One host-local in-flight job is allowed;
only an accepted/inapplicable delivery or explicit cancellation releases it.
Existing package/hash/currentness validation is the sole publication path, so a
stale, cancelled, foreign, or late delivery remains non-publishing. The UI
observes current exported jobs and refreshes the existing gallery automatically;
it never selects a candidate.

## Consequences

- The specialist is replaceable behind this small runtime adapter; no provider
  registry, new candidate store, or queue framework is introduced.
- An unavailable/busy/unknown native task is an actionable dispatch state, not
  a reason to fall back to manual copying, H3, Qwen, or automatic retry.
- A queue receipt and a real ImageGen result are separate evidence. Creative
  acceptance and image selection remain explicit creator actions.
