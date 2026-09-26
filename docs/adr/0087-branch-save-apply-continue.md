# ADR 0087: Branch save, apply and continue guidance

Status: accepted for the bounded creator-walkthrough improvement, 2026-09-26.

## Problem

The branch editor presented two equally prominent actions and one shared
fine-print explanation. After applying routes it still invited redundant
updates and gave no next step. Its apply action used the saved map even while
the visible form contained unsaved edits. The persistence operations are
distinct and correct; the UI did not expose those distinctions adequately.

## Decision

Keep separate save and apply operations and all server revision checks.
Associate a readable description with each button. Derive the primary action
from local edits, saved-map currentness and matching graph admission:

- Unsaved or modified map: save is primary; applying and continuing are blocked.
- Unchanged saved map: save is disabled unless the map is stale and requires
  explicit reconfirmation against current inputs. Do not trap stale maps behind
  equality checks.
- Current saved map not yet applied: apply is primary. Explain that it uses
  saved branches and updates story routes, not scripts or media.
- Current, unchanged map with a matching current graph: show 故事路线已就绪
  and make 继续：角色设定 primary. Redundant apply is disabled.
- Continue navigates through the existing project-scoped workspace navigation
  to Characters. It performs no generation, acceptance or persistence write.
  Do not discard unsaved source or branch edits to navigate.

Busy/read-only states and stale source/outline bindings retain their guards.
An admission merely labelled current is insufficient if it refers to another
saved map or no longer matches the loaded graph. Failed saves/applies must not
advance the displayed next step. Unrelated existing graph ownership remains a
server-side admission constraint, not a reason to bypass installation checks.

## Alternatives and consequences

A combined save-and-apply button would obscure the two decisions and expand
transaction behavior. A generic Next link would let users leave behind pending
edits or unapplied content. Keeping both gold buttons with longer help text
would not resolve the hierarchy problem. These alternatives are rejected.

This is one bounded pattern implementation, not a global wizard or a change
to the one-choice/two-ending model. No automatic content generation, creative
acceptance, schema migration or live-project modification is included.
Regression coverage must include dirty, clean, stale, busy, saved/unapplied,
applied and mismatched-admission states plus navigation without writes.
