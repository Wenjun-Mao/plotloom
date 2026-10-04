# 0113: Save-and-close and explicit force exit

Status: Accepted, 2026-10-04.

## Problem and evidence

The directory's Close drain reports success for an unloaded project but compares
its absent revision with zero and refuses to commit. New source/review editors
also hold authored input outside the legacy draft registry. Calling that flow
Save-and-close would silently lose those buffers. Neither problem belongs in
the server's exclusive/quiescent folder-close gate.

## Decision

- Normalize an absent writer revision to zero throughout the shared coordinator.
- Offer **保存并关闭项目** in the workspace and directory. Persist recoverable
  author input before asking the existing server Close contract to close. Draft
  persistence is not confirmation, acceptance, installation or generation.
- Add the bounded `review_buffer` draft scope for named source, section-map,
  cast, art and script editors. Store authored text and its original review
  basis, not arbitrary component state, settings or credentials. Partial/invalid
  editor JSON may be recovered; only canonical actions validate/accept it.
  Use existing exact draft CAS and project admission. Recovery is explicit and
  mismatched bases cannot be silently applied to a newer authority.
  Leaving a project resets its in-memory editing/adoption flag, so reopening
  requires recovery even when the same browser instance survives.
  Workspace Save-and-close completes its directory inspection before requesting
  exclusive Close; its own read must not occupy that gate or erase a Close error.
  Capture workspace ownership before that inspection and abandon the close if
  navigation changes it; a delayed close cannot clear a newer workspace.
  Cached directory rows are non-actionable while inspection is pending, so
  row-based Close cannot race that same lease. Local new-workspace/window exit
  remains available.
  Retained explicit-review guards bind to one project/editor session rather
  than a reused component's latest callbacks; forcing another project cannot
  discard current input.
  Late explicit draft-discard receipts may finish their exact server CAS, but
  cannot reset editor input after project, editor or review authority changes.
  Explicit production-presentation review and reference-image preparation/file
  inputs are not authoring-buffer acceptance. Dirty input there blocks ordinary
  Close with a specific explanation rather than being silently discarded or
  approved. Confirmed force exit may discard that local input. File pickers,
  consent checkboxes and generation options are never recovered as authorization.
- **强制关闭** requires confirmation. Discard this tab's unsent edits, preserve
  acknowledged drafts and canonical/media data, and leave jobs running. Settle
  already-started draft writes before asking the unchanged safe-close gate.
  Mark queues abandoning before awaiting flights; a settled old receipt must
  not resume a flush loop and send input the author just chose to discard.
  If that gate refuses busy work, exit the current workspace but label the
  project as still open for background tasks, never copy-safe closed. Unknown
  server outcomes are reported as unconfirmed, never inferred terminal.
- Closing a directory popup is **关闭窗口**. Closing a project never deletes it;
  archive and separately confirmed permanent deletion retain their meanings.

## Rejected alternatives and guardrails

Do not bypass the Close gate, release uncertain job ownership, cancel generation,
save/approve canonical content implicitly, snapshot the whole browser, or erase
other clients' drafts. Regression coverage includes no-writer close, scoped
force discard, failed saves, CAS/basis mismatch, restart recovery and busy jobs.
The Chinese manual remains deferred by the creator's instruction.
