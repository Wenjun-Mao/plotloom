# ADR 0056: graph typed edge effects bind the first target-scene entry

## Context

Checkpoint 3B retained a sell edge whose typed prop effects marked the watch
as abandoned and the order note as discarded, while the direct target scene
entered with the watch unfinished and the note discovered. The existing Scene
Beats prompt already instructed typed direct-edge entry state, but executable
enforcement was missing at the Graph admission boundary. The graph validator
checked vocabulary and topology, while the compiler first ran only when Scene
Beats was planned or canonically validated; unsupported multi-input graphs
could therefore be sealed or manually saved before that later failure.

## Decision

For prospective V2 graphs, every direct `entityStateEffects` assignment owns
only the target node's order-one scene `entryState`. Graph admission compiles
the same hash-bound edge-entry contract before either sealing or manual save,
and returns the affected entity and incoming-edge edit guidance. The contract
is then carried through StagePlan, unit context, prompt, response schema,
fragment validation, bounded correction evidence, and final canonical
validation.

An omitted effect creates no requirement. At a target with several direct
incoming edges, an affected entity must be assigned by every edge and to the
same state. Partial or conflicting assignments fail closed: the current
single-entry scene representation has no path-aware typed-state variant.
Later scenes and beats remain free to make explicit, valid transitions.

## Consequences

The contract prevents an unsupported graph from sealing or being manually
saved, and prevents a contradictory Scene Beats aggregate from being installed.
It does not infer generic `stateEffects`, propagate state across paths, rewrite
story content, add a branch executor, or repair historic artifacts. Existing
plans retain their hashes and are recognized as obsolete for recovery; a fresh
run is the supported prospective path.
