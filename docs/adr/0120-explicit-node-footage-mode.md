# ADR 0120: Explicit node footage mode

Accepted for bounded G0 implementation, 2026-10-06. The manager approved this
repair within the [owner-approved workbench plan](../roadmap/2026-10-06-graph-centred-creator-workbench.md).

## Problem and evidence

The sketch defaults decisions/joins to route controls without footage. Current
F4 binds every section to an episode, upstream validation requires nonempty
scenes/segments, and canonical coverage requires every graph node to have a scene.
Timing allocates positive time to controls. The existing player traverses empty
structural nodes, but this does not establish valid production admission.
The isolated baseline probe demonstrated these failures and the independent
read-only G0 review confirmed their owning boundaries.

## Decision

Require explicit `footageMode` (`footage` or `route_only`) in the current node
schema. Creation policy defaults decisions/joins to route-only and other kinds
to footage. Only decisions/joins may opt out of footage; authors may explicitly
include footage for them. No missing-field defaults, shape inference, migration
or historical reader is allowed.

Route-only sections retain summaries, choices, joins, structural counts and full
routes. They have zero footage time and no screenplay episodes, scenes, beats,
shots or media. Trusted F4/F5 bindings include only footage sections, while
preserving exact full-route and route-only membership context. Timing, work-unit
planning, script, bridge and media currentness freeze/hash-bind this policy.
Changing it requires truthful re-review, never automatic generation or selection.

Preserve ADR 0056's current scene-state boundary. Route-only admission fails when
the node requires an incoming typed scene-entry assignment or required join
facts. Explain explicit footage opt-in and retain the recoverable author draft.
An outgoing control edge targeting a footage scene may still carry valid effects.
Never erase or move effects, invent scene placeholders, propagate path state,
or weaken mandatory footage coverage. No new state runtime or general installed
production replacement is approved.

The model owns prospective prose under frozen IDs/constraints. The author owns
topology, footage inclusion and distinct content/admission/review/selection gates.
Trusted code owns exact membership, binding, timing, validation and currentness.
Current planner topology v3 freezes explicit membership on each node. Binding
copies that field; it never infers membership from kind when reading evidence.
Timing allocation v2 and dialogue capacity v2 reject retired shapes. Current
generation defaults use state-free controls; the prompt explains the opt-in
boundary and retains valid effects from controls into footage nodes.
The complete-graph response schema is v5 and its primary prompt is v3.3.0;
content-fill schema v5 and prompt v2.8.0 preserve trusted planner membership.
Planning policy `m1.5-p0.7` and work-unit contract `m1.15` identify the required
current frozen fields. Retired witnesses fail before execution.
The pinned upstream validators remain unchanged; trusted current-domain input
projection supplies real footage episodes only.

## Alternatives and guardrails

Reject coverage exemptions alone, fabricated scenes/cuts, inferred modes and
compatibility adapters. Explicit target-node boundary records and inherited
path-state execution would broaden the current state contract and are excluded.

G0 must prove state-free route-only traversal and bridge installation, control
footage opt-in, mixed routes, exact bindings and zero-time controls, plus guarded
rejection of typed incoming requirements/required join facts. Footage nodes
missing scenes or selected media must never be skipped. Preserve CAS,
first-install-only, unknown-dispatch and media currentness checks.

## G5 reader correction, 2026-10-06

The existing read-only route reader still required an episode for every graph
node, filtering out valid routes with route-only controls and leaving its loading
view indefinitely. Reader routes now retain all canonical nodes while checking
that episode bindings exactly cover explicit footage membership. Missing footage,
duplicate bindings and unexpected bindings fail closed with a visible mismatch;
no episode is fabricated for a control. Pure and native reader tests guard this
same contract. This closes a missed consumer of the decision above, not a new
membership rule or reinterpretation of prior G0 evidence.
