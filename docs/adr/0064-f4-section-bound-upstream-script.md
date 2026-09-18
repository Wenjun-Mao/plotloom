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
while Plotloom's review surface labels hook/cliff and duration output as
structural-only rather than product pacing acceptance.

## Consequences

Current source, outline, map/installed graph, cast, and art hashes/revisions
all bind the script candidate and accepted revision. A changed input is visible
as stale and blocks preparation, delivery admission, acceptance, and saves.
Prepared publication blocks close/archive/delete/snapshot until cancellation;
late delivery cannot install content. New folders carry the F4 tables. Older
folders are deliberately unsupported by the new contract rather than silently
migrated or backed up.
