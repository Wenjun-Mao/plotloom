# ADR 0119: Shared visual roles for the current workbench

Accepted October 4, 2026 under the approved sketch-led visual assignment.

The shared base and later creator styles repeatedly defined the same roles.
Nested bordered groups, oversized titles, tiny technical labels and three equal
Source columns made controls and supporting detail compete with the active task.
The owning layer is presentation, not generation or workflow state.

Use the approved dark sketch's 14px body, 19px workspace heading, 16px section
heading, 12px support text, calm dark surfaces, gold selection/action and sparse
structural borders. Narrative reading retains a larger title and 15px prose.
Warnings, currentness, instructions and next actions remain visible. Optional
preset additions use native disclosures; author values remain in the component.
Help keeps its existing grouped pointer/focus/tap/Escape contract with a small
label-aligned glyph and an adequate target (44px on narrow screens).

Styles have ordered owners: `shell-reading.css`, `media-tools.css`,
`authoring.css`, then shared creator roles in `creator-ui.css`. Exact later
role declarations are consolidated into their original rule. The four-line
`styles.css` is the entrypoint. Edit the owning rule instead of appending a new
cascade patch. Page composition uses explicit semantic classes: Brief directions
share columns where space allows; Source separates authoring/task work from
full-width accepted reading; the existing graph inspector stays beside the
canvas only when its actual workspace width supports it. Narrow layouts stack. Overlay cards size against their padded container, not
the viewport; directory identity sits above wrapping actions on narrow screens.

Reject a token-only/font-shrink pass and a copied demo workflow: neither repairs
page composition. Routes, controls, state ownership, prompt/API contracts,
dispatch, acceptance and currentness remain unchanged. Generated reports retain
their original evidence, including report styling; production never reads the
sketch or V1 paths.

Guardrails: real rendered route/state captures at desktop, compact and narrow
widths; focus/help bounds, scroll, touch targets and reduced-motion checks;
existing draft/currentness/consent regressions; deterministic static build;
read-only review and exact normal-project/settings preservation comparisons.
Human walkthrough acceptance remains separate from technical delivery.
