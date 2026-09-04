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

The original pure `dialogue_capacity.v1` planner derived a conservative
authoring envelope from the exact frozen scene allocation and dialogue timing
profile. For every Story Graph node it permitted at most two dramatic scenes
and four dialogue cues. It reserved the one-unit minimum for both possible
scenes, divided the remaining node budget equally across four cue slots, and
projected each timing rule into an exact `maxTextCodepoints` value. The
invariant was:

```text
scene floors + all permitted cue slots <= frozen node duration
```

The two-profile preflight showed that this was safe but too restrictive: even a
node with only one creative line received no more than one fourth of the node
time. `dialogue_capacity.v2` is therefore the new-plan default. It retains at
most two dramatic scenes, reduces the fixed dialogue envelope to two cue slots,
and freezes `ProjectBrief.language` as `authoringLanguage`. For that language,
it derives a portable `schemaMaxTextCodepoints`: the smallest cap safe for every
permitted delivery. The provider-facing Scene Beats schema fixes `language` to
`authoringLanguage` and applies that value as `text.maxLength`; if it is zero,
`dialogueCues.maxItems` is zero. Local semantic validation remains authoritative
for every provider, including ones without native JSON Schema.

The complete timing profile and capacity plan are frozen in both the Scene
Beats StagePlan and each work unit. Their public versions and hashes, plus the
selected node guidance, bind the request contract. The primary prompt receives
the bounded guidance directly; the response schema enforces the global scene
and cue counts plus v2's portable language/text cap; and local semantic
validation applies the frozen rule to each cue before retaining the existing
whole-node budget check as a defense in depth. A node too small to fund the
fixed envelope fails with `dialogue_capacity.node_budget_too_small` before any
provider call.

When a schema-valid Scene Beats response exceeds a cue cap, the runner derives
a `DialogueCapacityRepairFact` only from its stable issue path, frozen node
guidance, and parsed cue metadata. It contains the exact cap, current codepoint
count, and compatible delivery limits, never dialogue text or validator prose.
The correction prompt treats this fact as its only capacity authority. Missing,
malformed, cross-language, or stale facts authorize no capacity repair.
If a provider returns a cue language that differs from the frozen authoring
language, validation emits
`semantic.dialogue_language_not_authoring_language` and does not query the
timing profile with that untrusted language. This is ordinary model feedback
eligible for bounded correction; a valid authoring-language-only profile is
never required to add wildcard rules merely to validate an out-of-contract
response.

The same frozen timing profile remains authoritative after model execution.
At the time this ADR was accepted, `commit_sealed_run` located Storyboard
timing provenance through a same-run Scene Beats StagePlan, so standalone
Storyboard-only sealed runs were deliberately not installable. That specific
same-run lookup is superseded by ADR 0019's Storyboard-owned provenance rule:
current Storyboard StagePlans freeze and hash their own complete profile at
planning time, while a Storyboard-only run may consume a READY Scene Beats
revision from an earlier run. Seal and install still never consult a process
default. A missing or invalid current StagePlan profile fails closed before
canonical mutation; it is not inferred from a canonical payload, parent run,
or deployment default. Manual canonical saves remain a separate authoring
path and select the current versioned profile at the time of that save.

The fixed limits are a versioned product policy, not a provider heuristic.
Changing them requires a new capacity-policy version. Historical v1 plans,
hashes, prompts, and recovery records retain their original four-cue shape and
must never be recalculated with v2 defaults. Terminal history remains readable,
but startup recovery terminates a nonterminal v1 Scene Beats run and requires a
fresh submission because its prompt and derived work-unit hashes cannot be
replayed under v2. Neither recovery nor compilation may reconstruct a missing
historical capacity contract from a new process default. V2 also rejects a
timing profile that lacks an exact or wildcard rule for any delivery before a
provider call; an incomplete trusted policy is a planning fault, not a model
correction opportunity.

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
- **Encode delivery-specific conditionals with provider-specific JSON Schema.**
  Rejected because profile capability guarantees only basic JSON Schema support.
  V2 instead emits one portable frozen-language `text.maxLength` safe for all
  delivery choices; semantic validation remains the common authority.
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
