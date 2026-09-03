# ADR 0011: Trusted provider profiles and bounded generation work units

> **Partial supersession (2026-09-03):** ADR 0013 is authoritative for the
> bounded, visible correction loop and current fail-closed rebuild boundary.
> It supersedes this record's prohibition on automatic semantic retries and
> defers the exact work-unit repair described below; the remaining profile,
> work-unit, sealing, cancellation, and recovery decisions stay in force.

## Context

Plotloom currently freezes public provider settings on a generation run, but
executes each canonical stage as one model request. This works for deterministic
fixtures and small candidates, yet it couples a stage's narrative size to one
provider context window and one HTTP deadline. In the 2026-09-02 local-model
acceptance probe, Story Bible and Story Graph completed while the Scene Beats
request reached the gateway deadline. Increasing that deadline would leave the
same unbounded work unit, make recovery coarse, and risk replaying an outcome
that is not known to be absent.

The current text adapter also assumes a bearer key and a public HTTPS endpoint.
That contract cannot represent the intended deployment: a user-managed,
OpenAI-compatible llama-server may be unauthenticated and reachable over
loopback, a private LAN, or Tailscale HTTP. Conversely, allowing each generation
request to supply an arbitrary URL would turn a convenience feature into an
unsafe network-request surface.

The root problem belongs to the generation application contract. Prompt wording,
larger timeouts, browser retries, or provider-specific exceptions cannot define
bounded work, durable recovery, or a reproducible model environment.

## Decision

### Trusted provider profiles

A generation run references a saved provider profile and freezes its public
version and hash. The snapshot includes at least:

- adapter and model identifiers;
- normalized API root and `authMode` (`none` or `bearer`);
- structured-output capabilities;
- context-window and maximum-output-token limits;
- temperature and other declared sampling controls;
- maximum concurrency, connect timeout, and per-attempt deadline; and
- redirect policy, which is always no-follow.

Secrets remain separate ephemeral leases. `authMode=none` sends no
`Authorization` header and requires no placeholder key. `authMode=bearer`
requires an available server or browser-session lease, but neither the secret nor
its alias is part of the profile snapshot, trace, project, or export.

Provider API roots may use HTTP or HTTPS and may resolve to loopback, private-LAN,
or Tailnet addresses. They must contain a host and optional port only; URL
credentials, query strings, fragments, non-HTTP schemes, and automatic redirects
are rejected. Runs can use only a saved profile selected through the trusted
control plane; request-level endpoint overrides are not accepted. A public or
multi-user deployment needs a separate authentication and authorization decision
before it may expose profile mutation.

### Generation plan

At enqueue, a deterministic planner compiles the requested canonical stage range
and provider-profile snapshot into a run-level `GenerationPlan`. It freezes the
planning policy/version/hash, stage budgets, maximum unit counts and aggregate
sizes, concurrency ceiling, and the canonical inputs that already exist. The UI
can show these bounds before the user starts the run. A request that cannot fit
them is rejected with an actionable reason rather than silently truncated.

The run-level plan does not invent selectors for entities that an earlier stage
has not generated yet. Before the first provider call for each stage, Plotloom
resolves that stage's exact upstream canonical revisions or sealed aggregates and
deterministically writes an immutable `StagePlan`. The Stage Plan freezes its
complete ordered work-unit set, stable selectors, input/dependency hashes, and
per-unit budgets. A downstream Stage Plan can therefore be created only after its
upstream aggregate is sealed; no model call for that stage occurs before its plan
is durable. This preserves a one-click four-stage run without pretending that
future Story Graph nodes or Dramatic Scenes exist at enqueue time.

Planning is domain-aware. Story Bible and small Story Graph requests may remain
single units. Scene Beats are partitioned by stable story-node or dramatic-scene
identity; Storyboard is partitioned by stable dramatic-scene identity or a
deterministic bounded group of scenes. Arbitrary string slicing and array
positions are not work-unit identities.

### Work units, attempts, and aggregates

`GenerationWorkUnit` is a durable child of a run. It freezes:

- stage, stable selector, sequence, and Stage Plan hash;
- canonical input revisions and content hash;
- prompt template/version/hash and bounded variables;
- provider-profile version/hash and resource budget; and
- its attempts, candidate artifacts, validation results, and terminal status.

Every attempt retains the existing prompt/response/validation provenance. A
successful unit produces a typed partial-stage candidate, never a canonical
stage revision. The repository allocates the durable work-unit and attempt IDs;
the prompt subsystem must not create a second unrelated execution identity.
A dispatch marker is committed before crossing the provider boundary, and a
provider response is persisted before parsing or validation.

`SealedStageAggregate` names the Stage Plan and its exact expected unit IDs and their immutable
candidate artifact hashes. Its manifest also records the resolved dependency
fingerprint; prompt, response, validation, and candidate artifact IDs and
hashes; producer attempts; prompt/schema/profile versions; and its own manifest
hash. The seal is written atomically with its accepted aggregate validation and
cannot be amended. Every referenced artifact must belong to the declared run,
stage, unit, and attempt, except for an explicitly named immutable repair source.

Aggregation is deterministic: it rejects missing, extra, duplicate, conflicting,
or out-of-order fragments; then it runs stage-wide and cross-stage gates that
cannot be proven inside a shard. These include stable scene/shot ordering,
reference uniqueness, continuity boundaries, and exactly one `PRIMARY` shot
link per beat while allowing additional `SUPPORTING` links.

Only sealed aggregates are eligible for installation. All requested canonical
stages are still installed in one transaction under the original snapshot and
revision guards from ADR 0004. No unit, fragment, or single-stage aggregate may
become a head early. The final repository command consumes sealed aggregate IDs
and verified manifests, not caller-supplied in-memory payload dictionaries.

### Failure, repair, retry, and cancellation

- A schema- or semantic-invalid successful response is quarantined; it is not
  hidden behind automatic model retries.
- Repair names the exact failed work unit and evidence artifacts. Successful
  sibling units may be reused only when Stage Plan, canonical inputs, prompt, and
  provider-profile hashes still match. The affected aggregate and all dependent
  aggregates are rebuilt and revalidated.
- Transport failure before a request is known to have been accepted may be
  retried only under an explicit, bounded retry policy. Deadline or connection
  loss after submission is `outcome_unknown`; it is never blindly replayed.
- Cancelling queued work can be confirmed locally. Cancelling running work is a
  request until the adapter confirms it or the attempt reaches another terminal
  state. Stopping browser observation does not change run or provider state.
- Startup may resume undispatched units and reuse already sealed units whose
  hashes still match. A run with every aggregate sealed may retry only the final
  transactional commit after rechecking cancellation and snapshot freshness.
  An attempt found after its dispatch marker but before a durable response is
  `outcome_unknown`, is never automatically reissued, and retains its evidence
  for diagnosis.
- If cancellation wins after a provider dispatch, any response that later
  arrives is retained as trace evidence but cannot be sealed or installed. If
  the canonical commit wins first, a later cancellation cannot relabel installed
  revisions as cancelled.

## Rejected alternatives

- Raising the global timeout keeps the stage unbounded and makes failures slower.
- Letting each provider invent its own shard boundaries would make canonical
  behavior and repair non-reproducible.
- Installing successful fragments early would violate atomic generation and let
  users edit an incomplete stage as if it were canonical.
- Retrying every timeout would duplicate paid or resource-intensive work.
- Allowing browser requests to override base URLs would weaken the trusted
  provider-profile boundary.

## Consequences and guardrails

This decision requires new persistence migrations, repository methods, APIs, UI
progress views, planner and aggregate validators before it is implementation
complete. Existing one-attempt runs remain historical evidence; ambiguous
historic artifact bags are marked legacy/unsealed and are neither resumed nor
used as repair sources. Public run/trace APIs evolve additively while the UI is
migrated.

ADR 0004's contiguous-range and atomic-install rules remain unchanged. Once the
new durable markers exist, this decision narrowly supersedes ADR 0005's rule that
every previously running generation must fail at startup: only provably
undispatched work or already sealed evidence may resume. Until that migration is
implemented, the conservative ADR 0005 behavior remains authoritative.

Regression gates must prove deterministic run-level and dependency-bound Stage
planning, including refusal to invent downstream selectors before their upstream
aggregate exists; secret-free profile
snapshots; unauthenticated local HTTP; redirect rejection; context and aggregate
budget refusal; per-unit trace completeness; crash/cancel/unknown-outcome
reconciliation; exact expected-unit aggregation; cross-unit collision and
continuity rejection; targeted repair lineage; and no partial canonical install.
Prompt/schema consistency is a release gate: a template may not instruct the
model to produce a relationship absent from its declared output schema.
