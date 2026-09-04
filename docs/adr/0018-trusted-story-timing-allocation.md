# ADR 0018: Trusted story timing allocation

## Status

Accepted.

## Context

The first M1-C live-model preflight exposed two related contract errors. Scene
Beats asked the provider to count Unicode characters, apply a language and
delivery rate, and reproduce the resulting dialogue duration. It also allowed
the provider to choose each dramatic scene's absolute duration. A response
could therefore be narratively sound yet fail exact arithmetic, and a
correction could make the immediate dialogue fit by expanding the scene and
silently violating `ProjectBrief.targetPlaythroughSeconds`.

These are deterministic scheduling decisions, not creative judgments. The
Brief already owns the playthrough target, the sealed Story Graph owns path
shape, and the versioned dialogue timing profile owns the text-duration rule.
Leaving their arithmetic in a prompt made the canonical result dependent on a
model's counting behavior and allowed correction to weaken an upstream author
constraint.

## Decision

### The Brief target is a hard upper bound

`targetPlaythroughSeconds` is the maximum duration of any complete story path.
It is not a request to add padding when authored material needs less time.

After Story Graph is sealed, the pure `scene_timing_allocation.v1` planner:

- computes deterministic topological depths;
- divides the Brief target across those depths using integer milliseconds;
- gives every node at the same depth the same cap, so a path can visit at most
  one allocation per depth;
- records whether all complete paths traverse every depth and are therefore
  exact rather than merely bounded; and
- freezes the complete allocation and its hash in the Scene Beats StagePlan.

The allocation is derived from the run's frozen Brief and sealed Story Graph,
never from a later mutable project head. It is included in dependency, plan,
prompt-contract, work-unit, repair, and seal lineage. A missing or mismatched
allocation fails closed; it is not reconstructed from current project state.

### The model owns proportions, not arithmetic

The Scene Beats response contract no longer accepts canonical
`durationBudgetUnits` or `estimatedDurationUnits`. The provider supplies a
bounded, relative `durationWeight` for each scene. The trusted binder:

1. derives every dialogue cue duration from its text, language, delivery, and
   the frozen versioned timing profile;
2. establishes a minimum of one millisecond or the scene's total dialogue
   minimum, whichever is greater;
3. partitions the remaining frozen node cap by relative weights using integer
   largest-remainder allocation with authored order as the tie-breaker; and
4. writes the resulting canonical scene budgets and cue estimates.

Generated scenes therefore partition the node cap exactly without requiring a
model to perform character counting or integer conservation. The canonical
authoring schema and UI retain both duration fields because they are useful,
editable production facts. Manual saves may use less than a node cap but may
not exceed it.

If dialogue minima cannot fit the frozen node cap, semantic validation returns
`semantic.dialogue_exceeds_node_budget`. A bounded correction may shorten or
remove nonessential dialogue or select a faster supported delivery. It may
never increase the node or path allocation.

### Dialogue capacity is planned before the provider call

Trusted timing derivation alone does not tell a provider how much dialogue can
fit. The first live Alpha preflight showed the resulting gap: primary Scene
Beats responses repeatedly exceeded a node budget, while bounded corrections
often succeeded only after the validator rejected them. The validator was
correct, but the primary prompt lacked the deterministic capacity facts needed
to satisfy it on the first attempt.

The pure `dialogue_capacity.v1` planner therefore derives a conservative
authoring envelope from the exact frozen scene allocation and dialogue timing
profile. For every Story Graph node it permits at most two dramatic scenes and
four dialogue cues. It reserves the one-unit minimum for both possible scenes,
divides the remaining node budget equally across four cue slots, and projects
each timing rule into an exact `maxTextCodepoints` value. The invariant is:

```text
scene floors + all permitted cue slots <= frozen node duration
```

The complete timing profile and capacity plan are frozen in both the Scene
Beats StagePlan and each work unit. Their public versions and hashes, plus the
selected node guidance, bind the request contract. The primary prompt receives
the bounded guidance directly; the response schema enforces the global scene
and cue counts; and local semantic validation applies the language/delivery
rule to each cue before retaining the existing whole-node budget check as a
defense in depth. A node too small to fund the fixed envelope fails with
`dialogue_capacity.node_budget_too_small` before any provider call.

The same frozen timing profile remains authoritative after model execution.
`commit_sealed_run` validates the Scene Beats aggregate and evaluates the
Storyboard gates with the profile parsed from that run's hash-valid Scene
Beats StagePlan. It never consults the process default at install time. A
sealed run that requests Scene Beats or Storyboard but lacks that same-run
provenance fails closed before canonical mutation. Consequently a standalone
Storyboard-only sealed run is not installable in this contract version; it
must be submitted with Scene Beats so the timing authority is explicit. Manual
canonical saves remain a separate authoring path and select the current
versioned profile at the time of that save.

The fixed limits are a versioned product policy, not a provider heuristic.
Changing them requires a new capacity-policy version. Neither startup recovery
nor compilation may reconstruct a missing historical capacity contract from a
new process default.

## Rejected alternatives

- **Keep exact timing arithmetic in the prompt.** Rejected because character
  counting and integer multiplication are deterministic program work and
  caused otherwise usable responses to fail.
- **Let correction enlarge a scene budget.** Rejected because that repairs a
  downstream symptom by violating the Brief's upstream playthrough contract.
- **Force one scene per Story Graph node.** Rejected because a node can contain
  several dramatic scenes; the binder can partition their shared cap without
  removing that authoring choice.
- **Add provider- or model-specific timing instructions.** Rejected because
  the ownership error is common to every provider and belongs in the shared
  planner/binder contract.
- **Rely on rejection-and-correction to teach the capacity.** Rejected because
  deterministic limits belong in the primary contract, and first-pass quality
  should not depend on consuming a correction attempt.
- **Encode language/delivery conditionals with provider-specific JSON Schema.**
  Rejected for this version because profile capability currently guarantees
  only basic JSON Schema support. Global array limits are projected into the
  schema; rule-specific text limits remain explicit prompt facts backed by the
  same local semantic authority for every provider.
- **Pad manual edits to the target.** Rejected because the target is an upper
  bound; shorter authored paths remain valid and should stay shorter.

## Consequences and guardrails

- The timing allocator is pure, versioned, deterministic, and hash-bound.
- Tests cover malformed graphs, infeasible targets, sibling-depth equality,
  exact generated paths, shorter skip-depth paths, and stable hashes.
- Tests prove Scene Beats schema excludes model-authored canonical timing,
  binder output conserves the frozen cap, dialogue estimates are trusted, and
  an impossible dialogue minimum is rejected before binding.
- Tests prove planning uses the frozen Brief and compilation rejects an
  allocation derived from a different Brief or Story Graph.
- Tests prove dialogue-capacity hashes are deterministic, each node envelope
  satisfies its arithmetic bound, primary schemas carry the count limits, and
  oversized cues are rejected against their exact frozen rule.
- Tests change the process default after sealing and prove canonical Scene
  Beats validation and Storyboard gates still replay the run's frozen profile;
  missing or provenance-free sealed contracts mutate no canonical head.
- Canonical validation rejects manual scene totals above a node's versioned
  cap while allowing shorter authored totals.
- Historical terminal records remain readable. New or resumed execution may
  not reinterpret an older nonterminal contract as the new timing contract.
- Startup recovery marks a nonterminal run that reached an obsolete Scene
  Beats timing or dialogue-capacity contract as failed with
  `recovery.scene_timing_contract_obsolete`, preserves its plans/artifacts,
  and requires an explicit new submission.

This decision refines ADR 0016's timing ownership and supersedes ADR 0017's
model-facing dialogue-duration repair mechanism. ADR 0017's bounded lineage,
safe issue data, and fail-closed correction rules remain in force.
