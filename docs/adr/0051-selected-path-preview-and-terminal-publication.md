# ADR 0051: selected-path preview and terminal publication disposition

## Decision

Step 4 playback projects only explicitly selected, ingested, current video
jobs onto one currently valid route from `deriveRoutes(graph)`. `groupStoryboard`
owns scene and shot order. An absent or invalid route produces no sequence;
exclusive branches cannot be merged. Missing route clips remain visible as
missing, and the native player retains its existing cut, stale-event guard, and
final-frame hold.

An image job already recorded as `cancelled` is terminal for close and snapshot.
The row and any late delivery evidence remain durable; late packages are
inapplicable and cannot publish candidates. Other nonterminal publication
states continue to block lifecycle transitions.

The deprecated whole-run repair endpoint and persistence chain are removed.
Exact work-unit repair remains the sole repair command.

## Consequences

Playback does not introduce routing, choice, stitching, or persistent player
state. This decision does not authorize a provider call, cancellation, or data
reset. Earlier historical-readability wording does not require adapters for
retired contracts under the lean current-contract policy.
