# ADR 0064: F4 section-bound upstream script authority

Status: Accepted, 2026-09-18.

## Context

The pinned `novel-script` format is a small batch of numbered episodes, while
the F1B pilot is three stable DAG sections: an opening decision and two ending
consequences. Treating every route as a separate episode would duplicate shared
content; translating it through the legacy Scene Beats payload would create a
second creative authority.

## Decision

F4 persists the upstream `script.json` unchanged except for one additive
top-level `sectionBindings` array. It maps every frozen F1B section ID exactly
once to a distinct upstream episode number. Plotloom trusted code owns that
mapping, input binding/currentness, revisioning, cancellation, lifecycle
blocking, and section-scoped replacement. The specialist owns the candidate
JSON/report. The author owns source facts, adaptation choice, and explicit
acceptance/editing.

F1B's accepted outline is a section map rather than upstream episode data. F4
therefore freezes that accepted outline unchanged and derives a transient,
unpersisted `outline.json` only for the pinned script validator/executor: three
ordered section summaries plus accepted cast IDs/names and no beats, Bible,
shot, or new creative facts. This is an execution adapter, not a second outline
or new canonical projection. The F1 section form also has no episode duration,
so the adapter binds the author-owned project playthrough target from the
existing brief, divides it across the three frozen sections, and records that
target in the script binding. Upstream's three-minute default cannot silently
expand the pilot.

The complete script remains one accepted revision. A reopened author edit names
one stable section and replaces only its bound episode; all other accepted
episodes are copied from the preceding revision. F5's consumer seam is the
accepted upstream script plus this mapping. It replaces only overlapping
scene/beat authoring responsibility; it neither emits shots nor retires any
still-used media path.

Upstream validation and its HTML render remain authoritative derived artifacts:
they are not wrapped or altered by Plotloom. The pilot is honestly non-episode:
required upstream hook/cliff strings state route-entry/terminal applicability,
while Plotloom's review surface labels hook/cliff and aggregate duration across
mutually exclusive endings as structural-only rather than product pacing
acceptance. Frozen per-section and complete-route ceilings remain applicable
technical admission constraints.

## Consequences

Current source, outline, map/installed graph, cast, and art hashes/revisions
all bind the script candidate and accepted revision. A changed input is visible
as stale and blocks preparation, delivery admission, acceptance, and saves.
Prepared publication blocks close/archive/delete/snapshot until cancellation;
late delivery cannot install content. New folders carry the F4 tables. Older
folders are deliberately unsupported by the new contract rather than silently
migrated or backed up.

## Amendment: F4 admission boundary and timing ownership (2026-09-18)

The initial F4 candidate exposed six contract gaps: a prepared script did not
block recovery snapshots, generic schema initialization could make a legacy
folder look F4-capable, the equal split treated the author target as a required
duration, section-to-episode assignment was not frozen as a positional
contract, the UI could present stale selection/report context, and deferred
responses could outlive their owner. These are admission and ownership defects,
not specialist-output defects; correcting a candidate after delivery would leave
the invalid states reachable.

The format-10 folder manifest is the explicit breaking F4 boundary. A format-9
manifest is rejected at folder admission with reset-required guidance. It is not
migrated, backed up, or rewritten, and F4 tables are created only after that
manifest has been admitted. Existing valued folders remain untouched.

The author owns the declared `targetPlaythroughSeconds`; trusted graph timing
owns the derived ceilings. The target is a hard maximum for a complete route,
never a required runtime or a minimum. For the exact three-section pilot,
trusted input freezes an opening cap of 90 seconds and a cap of 90 seconds for
each mutually exclusive ending when the target is 180 seconds. Each actual
route is consequently capped at 180 seconds. Script validation checks the
bound section and actual route caps, does not sum mutually-exclusive endings,
and never pads a script to a cap. Changing the declared target or its trusted
allocation stales candidate delivery, acceptance, and edits.

Trusted code freezes the exact ordered section-to-episode mapping in the
request/binding before a specialist starts. Candidate delivery, acceptance, and
scoped saves require that exact mapping; a permutation is rejected even when it
is a bijection. The current accepted JSON and the original upstream report stay
inspectable without reopening. Reopen/project/revision transitions clear the
current section selection and draft; an author edit replaces only its bound
episode and preserves the serialized untouched episodes byte-for-byte.

Prepared script publication participates in every recovery/lifecycle blocker.
Cancellation releases the blocker and invalidates the prepared row so a late
delivery cannot install. UI request ownership is scoped to the active project
and component lifetime, and is released only after its response/promise settles.
