# ADR 0128: Checked graph-edit safety diagnostics

Accepted 2026-10-07.

## Problem

The shared structural guard correctly refused a seventh decision output, but
reduced the checked count and enforced limit to an internal counter identity.
The API returned a generic transition message and the workbench retained only
that string, leaving creators without the constraint or a useful next action.

## Decision

Structural admission collects a named diagnostic alongside each existing
violation severity. The counter projection and comparison retain their current
semantics: incomplete drafts are allowed; an edit cannot introduce or worsen a
structural violation. Only introduced/worsened diagnostics are exposed.

Both API compositions return HTTP 409 with `code: graph_edit_unsafe`, `message`,
and `diagnostics`. Each diagnostic contains `code`, stable `identity`, `severity`,
`previousSeverity`, and checked `facts`. Degree facts include `nodeId`,
`nodeKind`, `actual` and `limit`; the enforced limits remain decision
`min(6, brief.maxOutDegree)`, ending zero, and ordinary node one. Capacity facts
measure unique node count against the actual Brief node budget. Other facts
identify the checked edges/nodes and required kinds or input counts.

The shared workbench owner preserves the API details. One presenter resolves
current node titles and presents the constraint and corrective action in both
workbenches and editing/confirmation dialogs; raw identities, codes and facts
remain in collapsed technical details. Generic errors retain their messages.
Busy and revision-conflict handling are unchanged.

## Alternatives and consequences

Parsing counter strings in the browser cannot recover measured facts and would
couple product wording to an internal identity format. Relaxing the guard would
change graph admission and mask the issue. Neither is adopted. Diagnostics are
now a public API contract; tests cover exact checked facts, unchanged draft and
canonical heads on refusal, detail preservation and creator-visible guidance.
