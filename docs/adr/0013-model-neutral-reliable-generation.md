# ADR 0013: Model-neutral reliable generation

## Status

Accepted.

## Context

The first local-model probes exposed two different failures that looked alike in
the UI. One provider spent its output allowance on a separate reasoning field
without producing final content. Another returned valid JSON but violated the
Story Graph's global topology constraints. The legacy application appeared more
successful because it installed a loosely checked combined tree/storyboard and
silently filled or dropped invalid values.

Changing model aliases, weakening canonical validation, or repeatedly sending
the same prompt would hide those root causes. Plotloom also needs more than one
saved OpenAI-compatible endpoint, while credentials must remain outside public
profiles and durable evidence.

## Decision

Text providers are represented by named, revisioned, public profiles. A run
freezes a versioned profile snapshot, resolved execution policy, and per-stage
budgets. Profile behavior is selected only through typed capabilities and
policies; model, provider, and alias strings never activate special code paths.
Secrets are resolved by frozen profile ID and remain ephemeral.

Named profiles govern text generation only. Image and video tasks continue to
freeze their own global public settings; a text-profile selection neither
selects nor overrides a media provider, model, endpoint, or credential policy.

New Story Graph runs freeze a deterministic `story_graph_topology.v1` plan before
provider dispatch. Plotloom owns node and edge identities, kinds, endpoints,
start, endings, and joins. The model fills only narrative copy, choice effects,
and join semantics. The binder requires an exact ID set, reconstructs the
canonical graph, and still runs every existing graph validator. A structurally
infeasible brief fails before any provider call.

Scene Beats and Storyboard shards expose only response-local aliases (for
example `localSceneId`, `localBeatId`, and `localShotId`). The trusted binder
maps those aliases to deterministic UUIDv5 IDs from the immutable selector and
validated local order; model-supplied aliases never become canonical IDs.
Selector-owned parents (`storyNodeId` and `sceneId`) are not part of the model
schema: the binder injects them from the frozen work unit, while any legacy or
attempted parent override is rejected as an extra field rather than silently
discarded.

Storyboard PRIMARY coverage is likewise a closed structural contract. The
model maps every frozen Beat ID to exactly one response-local Shot ID through
`primaryShotLocalIdByBeat`; the schema fixes the exact key set, and the binder
creates canonical PRIMARY links. Optional `supportingBeatLinks` can add only
SUPPORTING coverage inside the same shard. This lets one shot intentionally
cover a continuous beat span without asking the model to reconstruct fixed
roles, parent IDs, or canonical link identities.
Join continuity remains explicit: each frozen join contract names its required
state keys, and the affected fragment schemas require those keys on incoming
exit states and join entry states before aggregation runs the cross-shard
validator.

Planning keeps a portable byte estimate for memory and input-budget limits; it
does not pretend that bytes are provider tokens. Tokenization and the exact
context-window decision belong to the selected provider/model. The planner
only rejects byte-budget excesses and the provable case where the declared
output allowance alone consumes the declared context window.

A validation failure may create at most the profile's configured number of
explicit correction attempts, capped at two. Each attempt has durable lineage,
prompt/response/validation evidence, and a stable outcome code. A correction
receives the immutable contract, closed response schema/topology, previous
final content, and stable validation code/path pairs; it does not duplicate the
broader creative-context messages and cannot alter topology or provider policy.
The previous final is serialized as an explicitly untrusted JSON string, and
the rendered packet must remain within the work unit's frozen input-byte
budget before dispatch. The first correction repairs the prior final; the last
correction is a distinct, ordinal-bound strategy that reconstructs the document
from the closed schema instead of deterministically repeating invalid syntax.
Extraction corrections explicitly require ASCII JSON delimiters and escaping;
the extractor never silently normalizes full-width punctuation. Exhaustion
quarantines the work unit. This narrowly
supersedes ADR 0011's prohibition on automatic semantic retry: corrections are
permitted only because they are bounded, visible, and auditable rather than
hidden retries.

Work-unit terminal states preserve the causal boundary. `quarantined` means a
durably recorded model response exhausted its explicit extraction, schema, or
semantic corrections and remains available for review. A known provider,
contract, persistence, or local execution failure is `failed`; an uncertain
post-dispatch result is `outcome_unknown`. Callers choose `failed` versus
`quarantined` explicitly rather than inferring it from an outcome-code prefix.

Assistant `message.content` is the only model text eligible for canonical
parsing. Separate reasoning remains raw trace evidence and is never concatenated
with final content. When `content` is a typed part array, only explicit `text`
and `output_text` parts are final; reasoning and unknown part types remain raw
evidence. Typed request extensions may emit only supported fields such as
`chat_template_kwargs.enable_thinking`; arbitrary provider JSON is forbidden.

Every structured generation prompt uses a presence-strict contract. Properties
listed in any schema object's `required` array must be emitted even when their
only valid value is `null`, an empty collection, or an empty string; nullable
does not mean omittable. Native JSON Schema support is an explicitly probed
profile capability and may improve syntax and closed-object adherence, but it
does not replace Plotloom's local presence, schema, binding, and semantic
validators. This is necessary because otherwise-compatible servers can accept
`response_format=json_schema` while incompletely enforcing nested `$defs`.
Before dispatch, Plotloom therefore expands non-recursive local `$ref` values
into an equivalent self-contained schema. Standard annotations such as
`description` are retained; `default` is removed from generation schemas
because omission is invalid at this trust boundary and some constrained
decoders treat it as permission to omit a required property. Recursive
references or sibling validation constraints fail before the provider boundary
rather than being merged ambiguously.

Historical provider snapshots, generation plans, and sealed manifests retain
their original serialized fields and hashes. Missing profile schema version
means the legacy V1 snapshot contract. New defaults must never be materialized
into historical payloads.

The legacy singleton provider-settings endpoint is only a compatibility
projection over the active text profile plus global media settings. A write to
that projection must name the active profile ID and its expected revision; it
fails with a conflict if either has changed, so an old settings screen cannot
overwrite a newer named-profile edit.

Migration `0006_v2_model_profiles` preserves those historical hashes by safely
terminating only its pre-contract non-terminal attempts and runs, marking them
as requiring a newly submitted run rather than rewriting their evidence.
Migration `0007_v2_run_failure_codes` adds stable run-level `failureCode` and
`failedStage` fields so planning, aggregation, canonical-validation, and
otherwise-unhandled worker failures can be classified without parsing prose.
It also backfills the exact 0006 migration terminalization code; startup
recovery assigns stable codes to legacy interruption, ambiguous dispatch,
non-recoverable work units, and orphan work-unit states.

## Consequences and guardrails

- Updating or activating a profile affects only future runs.
- Public profile APIs and conformance receipts contain availability flags and
  hashes, never keys, endpoint credentials, prompts, reasoning, or generated
  prose.
- Provider envelopes are untrusted evidence. Before any durable write,
  Plotloom recursively redacts secret-shaped fields and exact outbound
  credentials while retaining numeric usage counters. Adapter-level
  sanitization is repeated at the orchestration boundary so third-party
  adapters cannot bypass the persistence rule.
- Deleting a profile also removes its browser-session key mapping. Profile ID
  reuse must never inherit a credential entered for the deleted profile.
- Run-scoped secret leases and cancellation entries are released even when a
  queued run is cancelled before a worker can transition it to running.
- A response with reasoning but no final content has the stable outcome
  `response.missing_final_content`; an ambiguous dispatched request remains
  `outcome_unknown` and is not replayed.
- Exact repair of a failed work unit is deliberately still out of scope. The
  current boundary fails closed and requires a rebuild from the failed stage;
  future repair must freeze the target unit, sibling fragments, aggregate, and
  downstream seals before it can be introduced.
- The same deterministic planner, binder, correction policy, and qualification
  gate apply to every model profile.
- Connection probes exercise a declared native JSON Schema capability instead
  of merely proving that plain Chat Completions work. The minimal probe is a
  necessary endpoint check, not proof that a provider handles every production
  schema correctly; the fixed full-pipeline qualification remains the final
  authority. Profiles may therefore declare different capabilities without
  introducing model-, alias-, provider-, or endpoint-specific code paths.
- `textMaxConcurrency` is a frozen safety ceiling, not a throughput promise.
  A runner may conservatively execute fewer work units concurrently—including
  serial execution—without changing the profile contract.
- A profile is pipeline-qualified only after three complete four-stage runs,
  with at least ten of twelve stage aggregates passing on their first attempt.
  Each secret-free receipt identifies the fixed workload by `workloadHash` and
  its distinct sample by `sampleOrdinal`; token use and latency are recorded
  but are not qualification thresholds. The initial M1.5 gate was satisfied on
  2026-09-03 by two saved real profiles with three successful samples each;
  the immutable receipts are retained in
  [`2026-09-03-m15-conformance.jsonl`](../verification/2026-09-03-m15-conformance.jsonl).
- Partial profile/run batches are diagnostic probes. Only the explicit strict
  M1.5 mode may claim the two-profile, three-sample release gate.
