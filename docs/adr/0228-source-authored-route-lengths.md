# ADR 0228: Unequal choice counts in explicitly adopted source routes

## Status

Accepted for faithful production of the approved Last Projection graph.

## Decision

An explicitly adopted source map owns its complete route topology. Its routes
may end after different numbers of choices. At source-map admission, the saved
Brief's `decisionPointsPerPath` is the upper bound for each complete route.
The generic canonical generation validator and planner keep their exact-count
contract. No persisted field or planner output is reinterpreted or rewritten.

The source-map validation entrypoint explicitly selects this bounded policy,
including installation and subsequent source/Bible identity checks. Keep all
other graph checks: reachability, DAG, endings, node budget, maximum out-degree,
join contracts, typed state, route-only legality, source/CAS bindings and
independent language checks. A shorter adopted route does not authorize extra
choices, hidden flags, truncated dialogue or a bypass of technical validation.

## Context and consequences

The approved seven-role story has one choice on the short ending route and two
on each longer route. The previous equality check cannot admit it for any
scalar Brief value. An explicit source topology is stronger routing authority
than a planner's uniform route template. Preserve its six edges and four exact
choice labels, while retaining the Brief's resource bound and the unchanged
generation defaults. This is a current source-admission contract correction,
not a per-project exception or a new setting.

## Explicit source authority before F1

The unchanged uniform planner cannot produce two decisions on every route,
three endings and no joins. A successful seed is therefore not a prerequisite
for an accepted, explicit author structure. `SourceMaterial.authoredStructure`
reuses the typed topology, section and choice contracts and is part of the exact
accepted source hash. Trusted code validates and freezes it into F1 as
`source-structure.json`, with that source hash. Instructions and currentness
checks identify this author authority; they do not claim planner success or
accept a model-created topology as source. Optional echoes and language checks
must use this exact frozen artifact.

Seedless author drafts/maps carry the exact source hash and may initialize only
from that accepted typed structure. Their first save is compared with the
trusted initialization, then normal edit/adopt/CAS rules apply. Null seed or
`topologyOrigin:author` alone grants no authority. Existing real seeds remain
immutable. Sources without this optional field serialize exactly as before;
Brief-derived sources cannot attach it or change their exact-synopsis invariant.
The existing source API is sufficient for explicit import, and the source UI
must display and preserve the structure on ordinary saves. Reopen and snapshots
retain both author evidence and current adopted routing.
