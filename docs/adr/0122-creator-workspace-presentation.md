# ADR 0122: Creator graph presentation over the shared authoring owner

Status: accepted within owner-approved G2 scope, 2026-10-06.

## Problem

A freely positioned professional canvas cannot express the approved automatic
rows, natural page scroll and bounded inspector without mixing layout into route
identity or creating another graph store. The v9 sketch supplies interaction and
visual references, not application code or persistence authority.

## Decision

`creator` is a workspace navigation destination. Mode changes use existing draft
navigation gates; both modes consume ADR 0121's root. Connected ranks follow longest
paths; detached row hints remain presentation-only. Siblings never wrap. Only the
chart pans horizontally; the document owns vertical navigation. Exact-edge controls
and connection dragging dispatch the same immutable command preview.

Incoming edge labels own distinct lanes within each rank's gap, including
converging and skip links. Selection is a project-scoped private browser preference;
selection-only navigation never creates an authored revision. Structural commands
and Undo explicitly set the selection along with their transaction.

Row-parent inference requires a direct choice input from the same decision for
every row member. A detached member makes the parent unspecified. Preview labels
use titles, kinds and actual option text; exact identities remain available in
folded technical detail. Human-readable impact explanations contain no raw IDs.

Saving changed Brief structure targets requires an explicit before/after preview
with the current graph's actual counts. Confirming changes targets and currentness;
it cannot reshape the graph or increase capacity implicitly.

Inspector sizing and scroll/selection preferences live in versioned private browser
presentation state, outside authored drafts, approval and production fingerprints.
Sizing mutates CSS geometry in place without remounting forms. Pointer cancellation,
Escape and lost capture restore the initial preference; release commits once.
The width is 300–520px, at most 45% of content, preserving 480px chart plus divider.
Automatic width is 380px at content width >=1120px, otherwise 300px. Height aims at
85% of viewport and clamps to the visible workspace below the application toolbar.

The creator workbench requires desktop browser width >=1280px, including short
windows. Phone/narrow authoring is formally unsupported. Existing unrelated readers
and portrait media are outside that boundary.

## Alternatives and guardrails

Reject free-position dragging in creator mode, sibling wrapping, a second graph or
local autosave owner, inner vertical chart scrolling and sizing in story state.
Professional fine controls retain their supported current behavior. Qualification
requires native pointer/keyboard/scroll interactions and actual screenshot inspection
at 1280×768, 1280×460 and 1700×900. Tests do not establish owner acceptance.

## G5 cancellation regression, 2026-10-06

Independent review found that the combined Tab-then-Escape native exercise masked
missing Tab cancellation. The geometry owner now cancels an active pointer gesture
on Tab or divider blur, restoring its original width without a release commit;
Tab retains normal focus movement. Native qualification exercises Tab and Escape
separately, then releases the pointer and checks the persisted width. This repairs
the existing presentation contract; it adds no story or production authority.

Manager review also identified window focus loss while a textarea retains focus:
pointer-down prevents focus transfer, so divider blur alone cannot cancel it.
The same geometry owner listens for window blur and removes that listener on
cleanup. Cancellation restores either the automatic (`null`) or explicit width;
a subsequent pointer release is idempotent. A deterministic delivered-blur
exercise reproduced the old 380→469px tentative width remaining active, then
checks restoration, preference, editor focus/caret/content/scroll and zero
authored writes with native pointer gestures. Actual OS blur delivery is not
claimed: headed browser-tab activation did not deliver that event on this host.

## Coverage walkthrough refusal presentation, 2026-10-06

The backend correctly refused a cycle, but the editing dialog closed before
asynchronous validation finished and the error appeared above a long graph.
Preparing a preview now returns explicit admission success: failure retains the
dialog, values and local error; only success closes it. Direct inspector commands
show refusal in the visible inspector header, not above the off-screen workspace.
Cancel/Escape cannot dismiss an in-flight preparation. Native edit, preview and
discard dialogs share the current surface/typography contract. Checkbox/radio
controls are excluded from text-input sizing and use explicit compact geometry.

Qualification covers the original cycle and capacity failures, direct node-role
refusal, retained endpoint values and zero mutation, with separate viewport
inspection. This changes feedback ownership, not graph validity or admission.
