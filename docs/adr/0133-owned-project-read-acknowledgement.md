# ADR 0133: Owned project-read acknowledgements

Status: Accepted, 2026-10-08.

## Problem

A genuine disposable two-tab conflict followed by a GET-only503 fault displayed
both “server version loaded” and an authority-failure dialog. Conflict reload
acknowledged before the aggregate read, whose void result conflated success,
failure and supersession. Route epochs alone also could not distinguish two
same-route reads while signal-independent progress reads were outstanding.
The follow-up journey also found a field-blur retry of the already-conflicting
draft. An unsafe discard removed storage but could reveal the same stale conflict.

## Decision

- The project loader returns `loaded`, `failed` or `superseded`. `loaded` means
  the exact aggregate was admitted into the current session; it does not certify
  asynchronous continuation of an existing run. Optional-review and resume
  behavior remain owned by their current contracts.
- Admission/error publication require both current route identity and exact,
  unaborted read ownership. Replaced requests cannot overwrite a newer read.
  An unregistered canonical loader returns superseded, never success.
  The admitted read retains continuation ownership after fetch cleanup so a
  replaced read's late Resume callback cannot reject/observe the newer session.
  Replacement invalidates callback publication, not an already-sent request.
- Conflict reload has a separate pending owner bound to the refreshed route and
  retained conflict. Only successful owned admission acknowledges reload, clears
  transient editor state and remounts the editor. Failure/supersession retain the
  exact conflict; pending prevents duplicate reload/copy/discard operations.
- Unknown project authority takes dialog precedence over recovery/conflict.
  Those workflows remain retained but cannot invite edits while authority is
  unknown. Successful explicit retry reveals them again; there is only one
  recovery/authority dialog at a time.
- All authoring autosave entry points require the currently connected project
  and no unresolved conflict. A current409 closes admission immediately, before
  another blur/timer callback can retry. Explicit resolution owns reopening;
  reload does not merge or write the retained payload. Already-sent writes retain
  their exact acknowledgement semantics; admission does not undo them.
- Explicit unsafe discard removes only the selected local record and matching
  conflict/recovery/editor references, including older same-binding workflow
  snapshots superseded by that record. A changed retained revision requires a
  fresh decision. A save409 captures the newest retained typing, not just the
  rejected request body. Unrelated buffers and acknowledged server drafts remain intact.
  A project-scoped acknowledgement names the discarded local buffer and preserved
  saved content. It does not clear a still-valid read error or claim project loading
  succeeded; dismissal or leaving that project removes the acknowledgement.
  Successful discard reveals its acknowledgement once in normal document flow;
  the dialog's removal must not leave the author scrolled past that feedback.
- Creator copy says server-saved project content, not a creative verdict or
  “canonical version.” Copying a non-graph conflict saves its required earlier
  content in a new project; tasks, review decisions and media are not copied.
  Graph recovery remains a separate same-project operation.

## Consequences and guardrails

No compatibility fallback, implicit draft merge or automatic generation is added.
Unit ownership tests cover held reads, failure, cancellation and replacement;
the actual two-tab browser journey verifies no premature acknowledgement, one
dialog, retry and exact retained/copy payload. Desktop pixel checks use the
supported 1700×900, 1280×768 and 1280×460 sizes. Zero-write guards cover conflict
reload; discard checks ensure that removed content cannot reappear as copyable.
