# ADR 0059: F1B source-bound reviewed section map

Status: Accepted, 2026-09-18.

## Context

F1A accepts an immutable, upstream-shaped outline but deliberately leaves its
prose without routing authority.  Reusing the legacy Bible/Graph pipeline as a
prerequisite would make the F1 path depend on a second creative generation
route; silently extracting choices from prose would make trusted code invent
authorial decisions.

## Decision

F1B adds one small project-local section-map record beside the F1A review
record.  The author owns stable section IDs, section summaries, the one choice,
both choice labels, their described consequences, and their explicit, distinct
ending-section links.  The model/upstream owner remains the unchanged accepted
`outline.json` and report.  Trusted code owns structural validation, immutable
map revisions, hash/revision binding, and CAS.

The map is intentionally not a general routing graph. It supports exactly the
F1B pilot envelope: one entry/choice section and two distinct reachable ending
sections. Once first saved, section, choice, outcome, and endpoint IDs are
immutable; author text remains editable. A normal UI form exposes all fields;
no JSON editing is required.

Each map revision binds to accepted source revision, accepted outline revision,
and accepted outline hash. Saving demands all three current values and the
expected map revision. Later source or outline acceptance retains historical
maps but marks the head stale with a reason; it never rewrites a map or installs
a replacement.

An explicit install is the only route from a current map into `StoryGraphV2`.
Trusted code compiles the three author-owned section IDs to one START and two
ENDING nodes, and the two authored outcomes to CHOICE edges. The choice label
and consequence remain traceable on each edge; entity effects are forbidden.
The entry node's out-degree is the decision, so the existing player needs no
synthetic fourth decision node. Installation CAS-binds source/outline/map
revisions and hashes plus the canonical graph revision in one transaction. A
small binding receipt names that canonical graph revision; it is not a second
route store. It may replace only a graph that the same receipt already owns,
never an unrelated graph. Source, outline, or map changes stale only that
admitted graph and actual downstream consumers.

The normal graph contract remains unchanged. The admission reuses its DAG,
reachability, node/edge, and V2 structural validation under the fixed F1B
shape, deliberately setting only fixed route-count expectations (zero explicit
`decision` nodes, two endings, no joins). It neither admits Bible-dependent
entity effects nor creates a global validation bypass. Writable existing
project folders receive one additive binding table in addition to F1B's prior
map tables, with no canonical-stage, source, outline, or asset conversion.

## Consequences and guardrails

- F1B gives explicit reviewable branch authority without making prose parsing a
  hidden authoring operation; canonical graph data is the sole routing state
  consumed by existing route derivation, route cards, and future Play.
- An old tab, stale source, stale outline revision, or mismatched outline hash
  cannot install a map.  Source/outline changes remain visible as stale state.
- Tests cover fixed shape, immutable IDs with editable text, persistence/reopen,
  graph/source/map CAS, stale graph admission, and a production
  FastAPI/file-SQLite browser journey that installs and displays both routes.
