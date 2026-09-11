# ADR 0029: Manual image-handoff usability and identity-reference boundary

## Status

Accepted for the P1 usability checkpoint, 2026-09-11.

## Context

The P1 handoff preserved canonical integrity but obscured normal operator
states: unsent directions disappeared on navigation, Copy did not use the
clipboard, absent delivery looked broken, and a newly created project did not
show its already-persisted Gate receipt. Separately, textual character context
and same-shot `parent_output` do not establish cross-shot visual identity.

## Decision

Directions are session-only drafts scoped by project, shot, and exact original
or refinement target. Their Approval/storyboard/reference context is validated;
an outdated draft remains visible for explicit recovery or discard, never
silent reuse. Copy attempts the browser clipboard and otherwise supplies
selectable text. Refresh returns a non-mutating awaiting state only for an
absent/empty inbox; once any delivery entry exists, malformed or partial input
still fails closed and remains diagnosable.

The UI names P0 imported stills, P1 manual image handoff, and unavailable video
separately, including the prerequisites for each. First-save hydration reads
the existing storyboard review/Gate receipt rather than inventing a new gate or
approval action.

Cross-shot character consistency remains a future contract. A subsequent
assessment will design approved project-level identity references, frozen
reference revisions, multi-character mapping, user-provided originals, and
visual cross-shot review. It must separate stable identity from state, costume,
composition, and style before adding a schema or generation behavior.

## Consequences

No draft becomes canonical until Prepare, no export implies specialist action,
and no waiting response implies valid output. P1 makes no same-person fidelity
claim. The existing immutable request, delivery, Approval, and selection
contracts remain unchanged.
