# ADR 0056: graph typed edge effects bind the first target-scene entry

## Context

Checkpoint 3B retained a sell edge whose typed prop effects marked the watch
as abandoned and the order note as discarded, while the direct target scene
entered with the watch unfinished and the note discovered. The graph validator
checked the vocabulary against the Story Bible, but no prompt, fragment, or
canonical Scene Beats validator enforced the post-edge state at the target.

## Decision

For prospective V2 Scene Beats contracts, every direct `entityStateEffects`
assignment owns only the target node's order-one scene `entryState`. The
hash-bound edge-entry contract is compiled from the sealed graph and is carried
through StagePlan, unit context, prompt, response schema, fragment validation,
bounded correction evidence, and final canonical validation.

An omitted effect creates no requirement. At a target with several direct
incoming edges, an affected entity must be assigned by every edge and to the
same state. Partial or conflicting assignments fail closed: the current
single-entry scene representation has no path-aware typed-state variant.
Later scenes and beats remain free to make explicit, valid transitions.

## Consequences

The contract prevents a contradictory Scene Beats aggregate from sealing or
being manually saved. It does not infer generic `stateEffects`, propagate state
across paths, rewrite story content, add a branch executor, or repair historic
artifacts. Existing plans retain their hashes and are recognized as obsolete
for recovery; a fresh run is the supported prospective path.
