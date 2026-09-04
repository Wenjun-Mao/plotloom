# ADR 0019: Exact fragment and join-state contracts

## Status

Accepted.

## Context

The M1-C live preflight exposed three instances of the same boundary error.
The model could invent an audio-event ID that had no stable canonical meaning;
the previous join check treated a source node's shared exit state as if it were
the result of one particular outgoing edge; and a locally accepted work-unit
fragment could rely on guarantees checked only after aggregation or canonical
installation. These are contract mismatches, not provider-specific failures.

## Decision

### Trusted code owns canonical audio event identity

The model supplies an ordered audio-event description only. The storyboard
binder derives each canonical event ID from its canonical shot ID and ordinal.
This is separately versioned as `audio_event_ids.v1`, including in the UUID
derivation namespace itself: it does not change the existing
`fragment_ids.v1` namespace used for scene, beat, cue, and shot IDs.
Audio timing repairs name the exact local event path and a safe replacement or
removal action; they do not expose free-form validator prose as generation
authority.

### State values have finite canonical JSON identity

All V2 fragment and canonical validators reject non-finite or non-JSON values
in continuity facts and beat deltas. Equality is finite canonical JSON
identity, so `1` and `1.0` are intentionally different values. The shared
primitive is used by fragment validation, aggregate/canonical validation, and
join compilation; no layer uses permissive serializer output or Python's
numeric-coercing equality as a substitute.

### Join facts are post-edge transition facts

`StoryNode.exitState` is shared before an outgoing choice. A direct incoming
`StoryEdge.stateEffects` assignment is the state after that edge and is the
only authority for a join's required entry facts. For every required key:

- every declared direct incoming edge assigns a finite canonical JSON value;
- values for a key outside `allowedDifferences` are byte-for-byte canonical
  JSON equal; and
- an allowed difference requires reconciliation and compiles to a deterministic
  tagged map retaining every incoming edge, source, and value.

Trusted code hashes this `join_required_state_values.v1` contract with the
sealed graph. Scene Beats receives only the selected node's exact entry facts;
its binder, semantic validator, aggregate validator, and canonical validator
must all require the same value. It must not require mutually exclusive
post-edge values on a source scene exit. A future need to model state *between*
scenes and edges requires a first-class transition-state domain, not path
propagation heuristics in a prompt adapter.

### A fragment is valid only if its aggregate can be canonical

Primary, correction, repair, and reused fragments run the same relevant
cross-reference, timing, continuity, dialogue, audio, and join checks that
their aggregate and canonical stage enforce. Aggregation repeats the complete
stage validation before sealing. Canonical installation remains the final
transactional defense, never the first point at which a normal model fragment
discovers a required invariant.

New Scene Beats StagePlans freeze the exact join-state value contract version
and hash, and include both in their StagePlan hash. Historical plans retain
their original shape for reading. A nonterminal run with an old planning policy
or without that marker is terminalized during startup recovery with a stable
rebuild-required code; it is never silently replanned or sent to a provider.

### Storyboard owns downstream dialogue-timing provenance

A canonical Scene Beats revision stores authored cues and their estimated
durations, but it intentionally does not assert which generator timing policy
produced them. A later Storyboard-only run may therefore consume a READY Scene
Beats revision without requiring the prior run to be present or rerun. Current
Storyboard StagePlans freeze their own complete `DialogueTimingProfile`, bind
it into their dependency and StagePlan hashes, and use it for fragment sealing
and atomic installation. A StagePlan is created before provider work, so this
is a planning-time choice rather than a seal-time fallback.

There is no lookup from a Storyboard run to a same-run Scene Beats StagePlan,
no reconstruction from a host default at seal/install time, and no attempt to
infer provenance from a canonical payload or an unrelated old run. If a
nonterminal current Storyboard plan lacks or fails to verify this field,
startup recovery and exact repair fail closed with a stable rebuild-required
reason. Terminal historical JSON and hashes remain untouched.

For exact repair, a child Storyboard StagePlan is new immutable evidence but
not a new policy decision. It inherits the valid parent Storyboard profile
when that parent had reached Storyboard. If the parent quarantined earlier in
Scene Beats, the child first inherits the parent Scene Beats profile for its
repaired Scene Beats plan; after that aggregate seals, downstream Storyboard
uses that child-local frozen profile. In neither case does repair read the
current default after the parent was frozen.

### Corrections receive frozen numeric and topology facts, never prose guesses

A correction deliberately omits the broad primary scoped context.  It must
therefore receive explicit, bounded authority for every cross-field invariant
it can repair.  Current Storyboard contracts carry `StoryboardTimingGuidance`:
the selected scene cap, full beat identities and order, effective shot-count
bounds, and canonical cue IDs, order, and durations, but never dialogue text.
The compiler sets the effective maximum to
`min(configuredMaxShots, cueCount + sceneBudget - cueDurationTotal)` and binds
it directly to the response-schema `shots.maxItems`; every schema-valid shot
count therefore has a timing lower-bound solution.  A sealed cue total plus
the empty-shot floor that cannot fit the selected scene cap is a pre-provider
`contract.storyboard_timing_infeasible`, not a model correction.

When a schema-valid response has safe cue/coverage identity, each timing issue
receives the same hash-bound `StoryboardTimingRepairPlanFact`.  The plan gives
the complete target order, durations, cue schedule, PRIMARY/SUPPORTING maps,
and original audio indexes to remove.  A correction applies it verbatim and
performs no arithmetic or coverage inference.  The plan parser independently
checks frozen identities, canonical order, cue uniqueness, coverage, exact
durations, budget, and hash; a timing plan suppresses standalone audio facts
because it already contains all required removals.  If coverage is not safe,
the coverage contract repairs it first and no timing plan is issued.

The timing fact additionally carries `guidanceHash`, the stable hash of the
complete frozen `StoryboardTimingGuidance` in the original prompt contract.
The embedded plan repeats and self-validates that guidance before validating
its own plan hash.  At correction replay, trusted code reparses the original
contract guidance and requires the same hash before a correction prompt can be
persisted or dispatched.  This rejects a re-hashed but internally valid plan
for another scene, cue set, budget, or configured shot bound; artifact storage
is evidence, not a channel for substituting a different correction authority.

For Scene Beats, a node-wide dialogue overage receives an auditable
`DialogueNodeBudgetRepairFact`.  Trusted code derives a delete-and-renumber
plan using the same per-scene one-unit floor as the validator; the model must
apply the exact plan rather than count characters or milliseconds itself.

For Story Graph, `EdgeStateEffectJsonRepairFact` covers every malformed edge
state value, including ordinary choices, with the frozen edge ID and both
topology-owned endpoints but no guessed replacement value. Join-specific
facts include the frozen direct incoming edge IDs and source node IDs for
missing or conflicting join effects and missing reconciliation. A promoted allowed-difference key
also carries the edges that must receive it in the same correction.  A fact
may carry an exact value only when all surviving convergent peers prove one;
`hasExpectedValue` distinguishes that authority from a legitimate JSON null.
No fact may infer a topology endpoint or choose a branch value arbitrarily.

## Rejected alternatives

- **Ask the model to create durable audio IDs.** Rejected because retries and
  repairs cannot establish stable identity from an untrusted local label.
- **Project branch effects onto source exits.** Rejected because one shared
  source node cannot simultaneously hold different outcomes for several edges.
- **Accept broad or prose-based correction hints.** Rejected because they make
  validation text an unversioned generation contract.
- **Ask a correction to rederive timing or join endpoints from its previous
  response.** Rejected because neither sealed cue timings nor topology edges
  are fully present in the correction packet.
- **Rely on final installation to catch fragment errors.** Rejected because it
  wastes bounded attempts and makes shard-level repair evidence misleading.
- **Add provider, model, or alias exceptions.** Rejected because these are
  shared domain contracts.

## Consequences and guardrails

- Tests cover missing/conflicting incoming assignments, deterministic variant
  values and hashes, exact join-entry matching, and the independence of source
  exits from branch effects.
- Pipeline reconstruction fixtures must satisfy the complete edge-value
  contract before and after a typed join-array correction, so the asserted
  repair fact remains the only rejection cause.
- Tests cover binder-derived audio IDs and exact audio timing repairs.
- Tests cover text-free storyboard timing guidance, deterministic dialogue
  delete/renumber plans, and pre-provider timing impossibilities.
- Tests cover topology-bound join repair facts, including JSON null authority
  and same-turn promotion of allowed keys onto direct incoming edges, plus
  non-join finite-JSON repair facts that cannot alter endpoints.
- Tests cover finite JSON parity in fragment and canonical validators,
  including the deliberate `1` versus `1.0` distinction and non-finite facts
  or beat deltas.
- Tests preserve historical prompt/StagePlan parsing without injected fields,
  while current Storyboard traces record `audio_event_ids.v1` and current
  Scene Beats recovery requires the frozen join marker.
- Every new fragment-level invariant requires a test proving an accepted
  fragment can pass aggregate and canonical validation without a hidden
  compatibility path.

This decision refines ADR 0013's model-neutral correction boundary, ADR 0017's
typed repair facts, and ADR 0018's trusted timing ownership. It does not alter
the immutable run, seal, profile, or atomic-install rules in ADR 0011 and ADR
0015.
