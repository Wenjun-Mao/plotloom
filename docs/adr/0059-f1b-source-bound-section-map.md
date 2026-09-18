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

The map is intentionally not a general routing graph and does not write,
translate, or require legacy Bible/Graph data.  It supports exactly the F1B
pilot envelope: at least three sections, one decision, exactly two distinct
outcomes, and two declared ending sections.  A normal UI form exposes all
fields; no JSON editing is required.

Each map revision binds to accepted source revision, accepted outline revision,
and accepted outline hash.  Saving demands all three current values and the
expected map revision.  Later source or outline acceptance retains historical
maps but marks the head stale with a reason; it never rewrites a map or installs
a replacement.  Writable existing project folders receive only two additive
tables, with no canonical-stage, source, outline, or asset conversion.

## Consequences and guardrails

- F1B gives explicit reviewable branch authority without making prose parsing a
  hidden authoring operation.
- An old tab, stale source, stale outline revision, or mismatched outline hash
  cannot install a map.  Source/outline changes remain visible as stale state.
- This section map is an F1 source-bound input, not yet player/runtime routing;
  Play retains its existing graph-owned behavior until a later accepted seam
  consumes this map.
- Tests cover persistence/reopen, binary-link validation, CAS, source staleness,
  and a production FastAPI/file-SQLite browser journey.
