# ADR 0015: Exact work-unit repair is an immutable child execution

## Status

Accepted for M1-R.

## Context

Plotloom's generation runner already persists prompts, responses, validation,
candidate fragments, stage plans, and sealed aggregates. A rejected model
response can therefore identify one failed work unit precisely. The historical
repair path predates work units, however: it reuses whole-stage candidates and
cannot safely repair one shard. The current code correctly fails closed rather
than weakening artifact ownership.

Simply attaching a parent candidate to a new run is not valid. Work-unit IDs,
stage-plan hashes, dependency hashes, attempts, artifacts, and seals all belong
to one run. Relaxing those checks would let unrelated cross-run evidence enter
an aggregate and would make later canonical installation unverifiable.

## Decision

### Repair is a new child run, not a mutation of its parent

An exact repair creates a `repair` child run with an immutable
`WorkUnitRepairScope`. The scope binds all of the following before any provider
request is scheduled:

- parent run and source stage plan, including their hashes;
- the target source work unit, selector, input hash, and dependency hash;
- the rejected attempt plus its persisted response and validation evidence;
- the parent's canonical snapshot, generation plan, topology where applicable,
  provider profile snapshot, and upstream seals;
- every successful sibling fragment that is eligible for reuse; and
- one content-derived scope hash and request idempotency binding.

The parent run, work units, attempts, artifacts, candidates, stage plans, and
seals remain immutable. A child never claims or updates a parent work-unit row.

### Eligibility is decided transactionally by the server

The repository evaluates and freezes eligibility in the same write
transaction. Exact repair is allowed only when:

1. the parent run is `quarantined`;
2. its frozen canonical snapshot is still current;
3. the target belongs to that run, is `quarantined`, and is not represented by
   a sealed aggregate;
4. the target's latest failed attempt has a persisted response and a rejected
   validation artifact with a stable known outcome code;
5. the target is not `failed`, `cancelled`, or `outcome_unknown`; and
6. every sibling selected for reuse has complete, accepted, hash-consistent
   evidence from the source stage plan.

Rejections use stable `repair.*` reason codes. The UI consumes those explicit
decisions and never infers repairability from trace prose or from the presence
of a failed attempt.

### Reuse is explicit and child-owned

Each reusable source fragment receives an immutable
`FragmentReuseBinding`. The binding proves its source plan, unit, producer
attempt, candidate hash, selector, and dependency fingerprints. After checking
that binding, the repository creates child-local execution evidence which
retains `sourceArtifactId`; it does not bypass normal run/unit ownership checks.

The target unit alone is sent to the provider and retains the normal primary
plus bounded correction contract. The repaired stage is aggregated from the
new target fragment and the verified child-local sibling fragments. Every
downstream stage is planned again from the new aggregate and must generate and
seal against its new dependency hash. No mismatched downstream seal is reused.

The child succeeds only after the existing full-range atomic installer accepts
one child-owned seal for every requested stage. Any failure leaves canonical
heads unchanged.

### Progress and evidence have separate read surfaces

`GET /api/v2/runs/{runId}/progress` is the polling surface. It contains bounded
run, stage, work-unit, latest-attempt, seal, and server-authorized action
projections with stable reason codes. It never contains prompts, model
responses, canonical payloads, endpoints, IP addresses, or secrets.

Full prompt, response, validation, and lineage evidence remains available only
through the existing on-demand trace surfaces. The workbench displays exact
repair only when `repairEligible` is true and distinguishes it from an explicit
whole-stage rebuild.

### Frozen provider and recovery semantics do not change

The child inherits the parent's frozen provider profile. The repair request
cannot select another profile. A browser session key may only satisfy that
frozen profile for the child submission; it is never persisted.

Queued child repairs may resume safely. A provider dispatch with no durable
response becomes `outcome_unknown` and is never replayed blindly. Cancellation
after dispatch can prevent sealing and installation, but cannot turn the sent
request into a retryable attempt. Completed child seals may only be retried
through the existing atomic installation boundary.

The legacy stage-level repair endpoint remains readable and callable for
historical compatibility, is marked deprecated, and is not used by the new
workbench.

## Rejected alternatives

- **Relax artifact ownership across runs.** Rejected because source existence
  alone does not prove selector, dependency, producer, or plan equivalence.
- **Overwrite the failed parent unit or seal.** Rejected because it destroys
  the evidence that justified quarantine and makes concurrent review unsafe.
- **Repair the target and reuse downstream seals.** Rejected because the new
  fragment changes the dependency hash even when its surface JSON happens to
  look similar.
- **Treat any failed/outcome-unknown attempt as repairable.** Rejected because
  execution failure is not rejected model content, and an unknown remote result
  cannot be replayed safely.

## Consequences and guardrails

- Migrations are additive and do not rewrite historical snapshots, plans,
  seals, hashes, or JSON.
- Tests must prove one failed shard is the only provider request repeated,
  successful sibling source hashes remain unchanged, and parent evidence is
  byte-for-byte stable.
- Tests must reject stale snapshots, cross-run/unit references, sealed targets,
  execution failures, cancellation, and unknown outcomes before provider
  dispatch.
- Restart and cancellation tests must preserve the same child scope and
  idempotency binding, with no partial canonical installation.
- Progress-payload tests must fail if prompt, response, payload, endpoint,
  model output, or secret material enters the polling projection.
