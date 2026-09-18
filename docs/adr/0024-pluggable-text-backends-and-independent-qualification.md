# ADR 0024: Pluggable text backends and independent qualification

## Status

Accepted by the user on 2026-09-07; implementation pending. This amends the
M1-C release policy, not the historical M1.5 or two-profile Alpha evidence.
The `default` application canary has finished under its frozen contracts:
Story Graph quarantined after three attempts, without partial installation or
unknown outcome. Its shared join-correction finding is tracked separately from
this module change. The `qwen36_35b` lane is deferred, not deleted,
failed, qualified, or periodically retried.

## Context

The existing `ProviderAdapter` and `TextProviderResolver` ports, named profiles,
capability contracts, and run snapshots already separate most provider concerns
from authoring. However, `SnapshotTextProviderResolver` always constructs an
OpenAI-compatible adapter, profiles have no reversible disable lifecycle, and
Alpha publication requires two profiles simultaneously. An unavailable second
host therefore blocks qualification of an otherwise usable first backend.

These are integration, lifecycle, and acceptance-policy concerns. They do not
justify a new story pipeline, weaker validators, or model-specific corrections.

## Decision

### Internal modules, shared authoring contracts

- The core owns topology, prompts, schemas, binding, bounded correction,
  validation, seals, atomic installation, and Approval. Backends cannot override
  this authority or secretly retry a request.
- Protocol adapters translate one request/response through the existing port.
  A trusted, explicit registry selects an adapter by stable ID/version, never
  by a model alias, endpoint heuristic, or arbitrary import path. The initial
  entry is the existing OpenAI-compatible implementation; llama-server and
  vLLM can share it. A new protocol needs a tested adapter, not duplicated
  authoring code. Third-party package loading is outside this change.
- Optional runtime diagnostics are separate from protocol transport. For
  example, llama-server slot checks do not become mandatory vLLM endpoints.
  Keep declared capacity distinct from observed capacity and record the
  observation's source/time; unknown capacity is not a verified pass. Use
  operator-supplied deployment evidence when a runtime cannot expose it.
- A named profile selects protocol, endpoint/model, capabilities and execution
  policy. Secrets retain their existing profile-scoped resolution. HTTP over
  Tailscale remains supported. Unsupported combinations fail before dispatch.

### Reversible profile availability

Availability is control-plane state, independent of execution configuration and
its frozen hash. Add revision-checked enable/disable operations; existing
profiles migrate as enabled without changing historical snapshots.

Disabling blocks admission of new runs, including new repair/rebuild runs, and
excludes the profile from new qualification jobs. Already-admitted queued or
running work may drain under its frozen profile, including its bounded
corrections. Explicit cancellation remains separate; disabling is not proof of
remote cancellation. Existing recovery rules still govern interrupted work.
Retain profile configuration, projects, attempts, artifacts, and receipts.

Disabling the selected or last enabled profile is allowed: keep the selection
as a preference, expose that it is unavailable, and require an explicit enabled
selection before new generation. Never silently choose another backend.
Re-enable requires fresh readiness evidence before qualification; connectivity
and qualification are separate from the operator's enabled/disabled choice.
Profile deletion retains its existing protection rules and is not “unplug.”
No lifecycle action stops, installs, or reconfigures a remote server.

Adapter selection/version must be frozen for new runs in a new snapshot schema
version. Preserve exact V1/V2 decoding, JSON, hashes, plans and seals; their
resolver behavior remains the existing OpenAI-compatible path. Changing a
profile affects only future runs. Credentials, final-content extraction,
sanitization, `outcome_unknown`, and immutable repair lineage remain governed
by ADRs 0013, 0015 and 0017.

### Independently qualified backend configurations

Separate the core product gates (automated correctness, browser persistence,
packaging and CI) from qualification of the particular backend configurations
advertised as supported. At least one backend must qualify for a usable Alpha;
an unavailable or unqualified backend is explicitly listed as deferred or
experimental, not evidence that another backend failed.

Introduce a separately versioned single-backend qualification mode. For each
frozen backend configuration on the accepted source/contract identity:

- Use the same three fixed Chinese stories, three repetitions each: **9/9**
  four-stage runs must complete and install atomically.
- At least **30/36** stage aggregates pass on the first attempt. Each unit has
  at most one primary plus two corrections. Unknown outcomes, secret leakage,
  and partial canonical installation disqualify the result. No cost or speed
  threshold is introduced.
- Deterministically select repeat one of each story, blind the three samples,
  and apply the existing `codex_external_review` rubric: no fatal contradiction,
  no score below 3/5, each sample mean at least 3.5/5, and each dimension's
  median across these three samples at least 4/5. Do not create product Approval.
- Freeze the exact expected sample set before execution; no dropping failed
  stories, choosing successful repeats, or combining incompatible candidates.
  Preserve the current secret-free/public versus private review-pack boundary.

The release claim names its supported, qualified configurations. Qualification
binds source and generation contracts, adapter version, public execution
configuration and known model/deployment identity. A stable alias is not proof
that its underlying model is unchanged. Record operator-declared deployment
identity when stronger evidence is unavailable; changing the model or material
execution configuration requires requalification. Old receipts remain readable
historical facts, not a new configuration's qualification.

The existing two-profile `alpha_chinese_three_story.v1` mode and receipts retain
their exact 18-run/six-review meaning. A new nine-run receipt must carry its own
acceptance version and expected cardinality; it must not pass a legacy gate by
changing global constants or relabelling partial output. Cross-backend
comparison remains useful optional evidence, not a host-availability dependency.

## Rejected alternatives

- Separate story pipelines for each model/runtime: duplicates contracts and
  encourages provider-specific tolerance.
- Delete a failed profile or fail over an existing run: destroys configuration
  or changes the run's frozen authority.
- Treat all saved profiles as mandatory release targets: makes unrelated host
  outages a global blocker and turns experimental configurations into promises.
- Count one successful canary as Alpha qualification, or redefine old receipts:
  loses the workload, quality, and provenance guarantees.
- Build a dynamic plugin marketplace first: no current requirement justifies
  its packaging, security, or lifecycle surface.

## Delivery and guardrails

**Execution-order amendment, approved 2026-09-07:** the retained llama canary
failed at Story Graph. First close the two concrete availability-review findings
and integrate that small slice. Next fix the observed shared join-correction
failure with focused regressions and attempt one full llama creation journey,
including storyboard content inspection and edit/save/reopen. Registry/V3
snapshots, runtime diagnostics and qualification-mode expansion wait until that
product outcome works. This reprioritization does not weaken the architecture
or per-backend qualification thresholds and does not authorize a pipeline rewrite.

Then complete only the remaining modularity needed for independent qualification,
with one stable-candidate review. Tests must cover registry
refusal, historical hash preservation, revision conflicts, disabled admission
and drain/cancel races, no active-profile fallback, session-secret isolation,
backend-specific diagnostics, and strict old/new qualification cardinalities.

If the same canary failure class persists after the focused fix, checkpoint and
reassess the contract rather than starting another open-ended correction cycle.
Freeze and verify the eventual candidate, run the llama qualification and
three blinded reviews, and retain vLLM for later independent re-enablement.
Do not claim implementation or release acceptance from this decision record.

## Related records

- [Completion plan](../roadmap/archive/superseded/2026-09-07-m1c-completion-plan.md)
- [Model-neutral generation](0013-model-neutral-reliable-generation.md)
- [Alpha provenance](0021-alpha-source-provenance.md)
- [Bounded delivery](0023-bounded-delivery-and-evidence.md)
- [Alpha runner documentation](../alpha-acceptance.md)
