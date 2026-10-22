# ADR 0142: Shot titles are display identity, not composition

Status: accepted

## Problem and evidence

The revised native E2E story repeats a complete English image direction as a
bold shot-card and detail heading. Bridge projection assigns `frame or action`
to `title`; reviewed presentation replaces it again with full composition.
Storyboard cards and the detail heading also omit the shared bounded label.
This confuses display identity with generation instructions and makes the
desktop editor needlessly tall.

## Decision

The deterministic bridge assigns a concise scene/shot-position title. Presentation
review owns action, composition and visible text, not titles. Authored titles
remain editable. Storyboard card and inspector headings use the same bounded
display-label function as the media workbench; full title and composition remain
in their editing fields and frozen evidence. Position, scene and shot IDs continue
to own navigation, not display prose.

No stored records, frozen jobs or reviews are rewritten. This is a current
projection contract plus a uniform display rule for all authored text, not a
historical-data adapter. New requests still follow normal currentness checks.

## Alternatives and consequences

CSS-only clipping leaves the wrong title-generation contract in place. Automatic
summarization would add invented meaning or another model dependency. Truncating
canonical composition would lose generation constraints. None is adopted.

Tests assert concise projected titles, exact retained composition, preservation
of an explicit title through presentation review, and bounded rendered headings
with unchanged editable fields and zero draft writes. Native desktop pixels are
verified separately from unit tests.
