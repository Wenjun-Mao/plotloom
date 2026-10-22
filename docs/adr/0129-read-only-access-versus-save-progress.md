# ADR 0129: Read-only access versus save progress

Accepted 2026-10-07.

## Problem

The workspace passed archived, closing and snapshotting access restrictions as
the `saving` flag to three professional editors. Archived pages therefore
claimed an active save while no save was running. Storyboard also used that flag
to lock its media workbench and confirmation flows.

## Decision

`saving` represents only the actual canonical save operation. The workspace
fieldset continues to enforce project access restrictions for professional
editors. Storyboard receives an explicit required `readOnly` prop for its media
and confirmation owners; these actions lock when either state is true. Only an
actual save changes the Save label to progress wording.

The existing server access, revision and dispatch guards remain unchanged.
There is no compatibility prop default or read-only-to-busy adapter. Storyboard
feedback components move into a cohesive page-local module before extending the
page contract.

## Guardrails

Unit checks distinguish idle, saving and read-only states, verify the media
access flag is forwarded, and prevent hook-owned confirmation while locked.
The real archive journey visits Story Bible, Scene Beats and Storyboard: normal
Save labels remain disabled, upload and snapshot mutations remain disabled, and
restoring archive access does not modify retained media. These browser checks
exercise actual upload/snapshot locks; the unit media component is mocked.
Local shot dialogs remain protected by the workspace disabled fieldset.
Read-only must never be presented as an in-progress write.
