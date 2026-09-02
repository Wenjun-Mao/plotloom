# ADR 0009: Atomic project bootstrap and creation idempotency

## Context

Plotloom previously created a project and four missing stage heads, then relied on
independent stage writes or a generation run to install canonical content. A
client that already has a validated first-stage prefix could therefore expose a
partially initialized project if a later write failed. Retrying the creation
request could also produce a second project.

## Decision

`POST /api/v2/projects` continues to accept the existing `{ "brief": ... }`
body and now returns the authoritative creation aggregate: every existing
`Project` field plus `stages`, a canonical-order `StageEnvelope[]`. This is an
additive response change, so bare creation retains its request shape and
project fields while also returning its four missing stage envelopes. It also
accepts an optional `initialStages` array. When present, that array must be an
ordered prefix of the canonical stage order, beginning with `story_bible`.

The repository creates the project, its stage heads, and every supplied initial
revision in one transaction. Aggregate creation and generation-run completion
use the same in-transaction stage installer, so both apply the same upstream
checks, domain validation, lineage, hashes, and stale propagation rules.

Clients may send `Idempotency-Key` on project creation. The repository binds a
key to a canonical fingerprint of the brief and initial stage prefix in the
same transaction. The key decision takes the SQLite database write boundary
before checking for an existing binding, which serializes distinct repository
instances against the same durable database. A matching replay returns the
same authoritative aggregate, including its canonical stage envelopes; a key
reused for a different request returns a conflict.

SQLite connections explicitly use a bounded one-second `busy_timeout` for
bootstrap writer acquisition. This lets normal overlap wait for the current
bootstrap to commit, then resolve the durable idempotency record. If the wait
is exhausted, the repository raises a retryable contention error and the API
returns `503` with `Retry-After: 1`; clients retry with the same
`Idempotency-Key`.

## Consequences and guardrails

An invalid stage or a persistence failure rolls back the project itself, all
heads, every initial revision, and any idempotency binding. The migration makes
the idempotency binding durable and unique, rather than relying on process-local
retry state. Empty `initialStages` and requests without an idempotency key
retain the prior create behavior, apart from the additive response aggregate.
Writer contention is deliberately bounded rather than surfacing a SQLite
driver error or waiting indefinitely. Tests hold an actual cross-instance
writer lock to cover both matching replay convergence and changed-body
conflict after waiting, and use a one-millisecond test timeout to cover the
retryable exhaustion response without a long delay.
