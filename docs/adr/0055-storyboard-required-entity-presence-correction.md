# ADR 0055: storyboard required-state corrections distinguish depiction from continuity

## Context

Storyboard validation has always correctly required every `requiredEntityStates`
entry to name an entity depicted by the same shot. A retained checkpoint-3A
run nevertheless exhausted correction attempts after its generic instruction
left the model to choose between adding an entity to shot membership and
deleting its requirement. It retained an off-screen mailed prop even though
the shot action and composition did not depict it. World entry/exit facts were
being treated as shot-presence candidates.

## Decision

Prospective Storyboard requests state that `requiredEntityStates` records only
same-shot depiction; off-screen continuity remains in `entryState` and
`exitState`. Prospective corrections for
`semantic.required_entity_not_in_shot` carry a typed, source-bound snapshot of
the rejected requirement, same-shot membership, action, and composition. The
directive prefers deleting an off-screen requirement and permits adding
membership only when the shot actually depicts that entity.

The membership validator remains strict. The fact does not select a creative
outcome, inject an entity, weaken validation, or change exact-repair semantics.
Frozen attempts retain their original prompt identity and are not replayed with
this contract; a current fresh continuation is the supported path when current
upstream stages must be preserved.

## Consequences

Correction provenance records why this narrow choice was available without
moving story-level continuity into shot membership. Existing Scene Beats,
Storyboard, gate, and repair owners remain unchanged. The contract versions
advance for new work only.
