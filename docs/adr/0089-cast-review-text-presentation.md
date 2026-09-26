# ADR 0089: Lossless character-review text presentation

Status: accepted for bounded creator walkthrough, 2026-09-26.

## Problem and ownership

The specialist's cast stores inference qualifiers inside descriptive strings.
The editor rendered those strings verbatim, mixing provenance with descriptions.
Its three-column layout grouped a growing trait list beside two short fields.
Safari label activation also removed drag selections by focusing the associated
textarea; separating label/control and setting user-select alone did not fix it.

The specialist owns candidate text; the author owns edits and acceptance. The
UI owns presentation only. No generation prompt, upstream schema, binder,
validator, frozen delivery or accepted revision changes in this slice.

## Decision

- Display an exact trailing `（推断）` or `(推断)` and its spacing in expandable
  inference notes, not in the editable description. Keep the full original
  string in editor state. Editing replaces only the description and preserves
  the qualifier. Rendering/accepting without edits is a lossless round trip.
- Do not infer provenance from unmarked traits or strip free-form sentences,
  internal parentheses or unknown qualifiers. Those can contain material
  creative constraints. Accepted summaries use the same presentation rule.
- Use responsive traits across the top, temperament/appearance side by side,
  then voice and notes. Stack fields on narrow screens.
- Character fields use separate, uniquely associated native labels. Retain
  normal label activation, but cancel that activation when a noncollapsed DOM
  selection intersects the label. Explicit text-selection CSS supports Safari.
  No mouse-down prevention, custom selection implementation or global click
  interception. Other forms are not certified by this bounded reproduction.

## Alternatives and guardrails

Discarding inference markers would lose provenance; moving arbitrary prose with
regex would guess at meaning; changing the upstream schema solely for display
would expand this slice. All are rejected. Original data remains inspectable;
notes explicitly state that annotations are retained when saving. A future
authoring workflow for independently revising provenance needs its own contract.

Tests cover suffix round trips, editing and clearing annotated text, unsupported
prose, unchanged acceptance payloads, unique accessible associations, read-only
controls and selected-vs-normal label activation. Verify drag selection and
ordinary click focus in real Safari, plus desktop/narrow layout checks. No live
creative acceptance or candidate rewrite is authorized by these checks.
