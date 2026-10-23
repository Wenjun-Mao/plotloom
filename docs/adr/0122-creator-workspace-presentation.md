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

## Canonical read-only fallback geometry and labels, 2026-10-22

The canonical reader is also used when a source binding or graph draft is
unavailable. Its index-based grid did not match the existing top/bottom edge
handles or the ranked creator lanes, so choice labels could appear on top of
nodes or away from the route they describe.

The canonical reader and editable creator chart now share one topology-only
geometry function. It ranks connected nodes by longest predecessor path, retains
stable sibling order, and gives every incoming label its own lane, including
converging and skip edges. The authoring wrapper continues to supply its existing
presentation-only row hints. Canonical reads pass the graph itself; they do not
construct an authoring draft or alter canonical identity, order, text, effects,
read-only status or mutation ownership.

The read-only React Flow canvas uses the shared card dimensions and explicit
bottom/top handle directions. Its height follows the graph, wide layouts scroll
horizontally, and only the initial fit is held at 1:1; later pan and zoom remain
available. HTML edge labels use the reserved coordinates, wrap within a bounded
scrollable area and remain keyboard reachable with their full text exposed to
assistive technology. Theme variables are scoped to this canvas so installed
React Flow CSS order cannot force white label fills. At the time of the original
qualification, both fallback modes used this same reader; that records the
evidence boundary then, not the enduring presentation contract. Canonical
topology layout and label projection remain shared, while each workspace mode
owns its read-only shell and inspector contract (see the decision below).

## Workspace presentation is independent of write authority, 2026-10-22

The owner reported that the canonical fallback makes Creator and Professional
look the same and puts node details below the graph. The original fallback
replaced the workspace shell, not just its data/write capabilities. Coverage
separately checked editable Creator geometry and unbound read-only safety, but
did not combine those supported conditions. The label repair above retained
that omission; its shared-reader sentence does not authorize mode collapse.

Choose presentation by workspace mode and mutation authority by current validated
source/draft state. Creator keeps its automatic, selectable graph and bounded
right-side inspector for accepted canonical reads too, reusing the existing
geometry and private project-scoped presentation preferences. Professional keeps
its technical canonical reader. Shared topology/field projections are allowed;
creating a fake authoring draft or source binding is not. Canonical identity,
content, currentness and read-only guards remain unchanged. Selection, scrolling
and inspector resizing are viewing operations, never authoring writes.

Guardrails combine mode and authority: supported desktop sizes, opening/default
and changed selection, reload/mode switching, bounded sidebar geometry and resize
cancellation, readable branch/join labels, and unchanged canonical/draft state
with zero authored requests. Existing editable Creator/Professional behavior
remains covered. The permanent C02/C03/C28/C45–C48 checks apply to the relevant
canonical read-only states, not only editable fixtures.

## Owner clarification of inspector height, 2026-10-22

The owner explicitly accepted the reconciliation recommendation: target
`0.85 × full viewport height`, then clamp to the usable visible workspace below
application chrome and its edge clearances. Do not take 85% of an already-reduced
usable height. Selected-node centring, top/bottom clamping, internal body scroll,
reachable header/actions and the short-desktop side-by-side layout remain.
This resolves the older C45 phrase “85% of visible height”; it does not approve
new Professional canvas interactions or code repairs.

Direct approval: `Sidebar height - agreed`, source chat
`01a04525-e907-7630-9640-78790d69e8ae`, turn
`01a166e4-9f25-7df1-a9a7-e363d77a4348` (2026-10-23 UTC / October 22 Toronto).

## Owner-approved Professional page and canvas navigation, 2026-10-23

Both editable and canonical read-only Professional views use ordinary wheel /
two-finger scrolling for native page navigation, retaining intentional inner
form/label scrolling. Ordinary scrolling does not zoom or pan the graph transform.
Pinch or visible zoom/fit controls provide deliberate graph zoom; dragging the
canvas background pans it. Both Pro paths must expose those explicit controls.
Creator's automatic chart and unrelated canvases keep their own contracts.

Reason: inherited wheel-to-zoom consumes page navigation and forces the pointer
into the left rail to scroll. Wheel-to-pan would retain that obstacle; removing
all pan/zoom would lose Pro capabilities. Configure the Pro presentation boundary,
not a global wheel listener or new graph/persistence owner. In the installed
library, disabling wheel zoom alone still consumes scrolling, so native page
scrolling must also be permitted. Canvas-state lifetime remains separately open.

The owner answered `Yes` to adopting this interaction for both Pro views in chat
`01a04525-e907-7630-9640-78790d69e8ae`, turn
`01a166ee-121b-7b61-a53a-4f47deb49897`. This adopts product intent, not implementation
or activation. C56 records the required native interaction checks; the current
implementation gap remains until separately authorized work and verification.
