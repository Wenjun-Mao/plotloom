# ADR 0132: Creator UI reading boundaries

Status: Accepted, 2026-10-08.

## Problem

The whole-product UI audit found presentation-layer failures: helper text
became part of a field's accessible name, a workspace settings dialog painted
under the sticky topbar despite fitting the viewport, and recovery links reused
identical shot prose for different story positions. Data and handlers were intact,
but readers and automation could not reliably identify the intended action.
A keyframe summary action also scrolled to content in a closed disclosure,
while deep-link navigation used a separate disclosure-opening implementation.
The native video screen also rendered an initial empty job array as a confirmed
absence before its budget, backend and job reads had settled.
The Brief's unbounded settings column stayed sticky even when taller than the
viewport, making its lower help dock unreachable by ordinary page scrolling.
The player also presented successfully read but absent production stages as a
failed request, and scene-card grid styling leaked into the generic Add Scene
control, wrapping its label into the card's narrow number column.

## Decision

- A shared `Field` with one direct native input/select/textarea binds a sibling
  native label to that control. Help is an accessible description, not its name.
  Existing names and description IDs remain intact. Compound controls retain
  their own semantics inside a labelled group; do not invent one control owner.
- Workspace-wide dialogs mount at the workspace overlay boundary, outside
  navigation/editor sticky or scrolling containers, alongside other global dialogs.
  Local component dialogs are not made global without an owning reason.
- Shared draft consent carries an explicit navigation, archive or close intent;
  a close boolean cannot represent archive semantics. Navigation/archive discard
  removes only unacknowledged local edits and retains already-saved drafts.
  Directory close-discard deletes the exact current-stage draft after quiescence;
  close-save retains recoverable drafts without confirming formal content. The
  topbar's explicit save-and-close goes directly through that save disposition.
  Recovery distinguishes server-saved, session-only and reconciliation drafts;
  a server-saved draft is recoverable, not falsely described as unsaved.
- The profile owner installs the current catalog used for both run admission and
  Inspector guidance. Durable project loading must refresh through that owner,
  not read the same catalog behind its back. Missing exact frozen profiles,
  missing credentials and failed catalog reads remain distinct; a failed read
  cannot open an unrelated form or be overwritten by a missing-key explanation.
  Guidance never borrows the active profile's key or automatically resumes work
  after a key save. Shared credential guidance is action-neutral because repair
  and continuation use the same admission boundary. Current responses supply
  required readiness and trusted adapters; retired settings fallback, inferred
  readiness and single-key migration are removed rather than kept as adapters.
  The selected configuration editor is not the server's current-use configuration:
  label it “当前编辑的模型配置”; mark only the server-owned active option “当前使用”.
  Activation is an explicit “设为当前使用” action. Missing/read-failed configuration
  guidance describes withholding a new execution request, not stopping an existing
  run. Primary settings labels use “密钥”, with protocol names left in diagnostics.
- Story-media recovery labels include the owning node and ordered scene/shot
  position, with the node position always included rather than conditionally
  prefixed after a title collision. Display prose is not identity; exact shot IDs still own links and API
  actions. Frozen creative text, media eligibility and selection do not change.
- Media summary actions and media deep links share one owner-navigation routine:
  open the target's owning disclosures before scrolling. Navigation is read-only;
  it does not prepare, dispatch, approve or select media.
- Unknown, failed and confirmed-empty reads are distinct UI states. The video
  workflow exposes empty-candidate advice and production controls only after
  all owned project reads succeed. Initial failures offer a named read-only retry;
  stale successes and failures from another project cannot replace current state.
- Unbounded Brief form columns scroll with the document rather than sticking
  above unreachable lower controls. The bounded graph inspector keeps its own
  positioning contract; this is not a change to graph editing behavior.
  Expanded service diagnostics also remain in document flow. Opening them from
  a scrolled sticky toolbar reveals the summary anchor with nearest scrolling;
  closing does not scroll or change focus. Do not scroll the whole unbounded
  panel into view or restore a tall sticky overlay above authoring controls.
- Successfully read but missing playback prerequisites have their own typed
  state and a link to the preparation owner, not a transport-error retry.
  Actual failed reads keep their named read-only retry. Optional new Art tasks
  are visibly distinct from the confirmed revision and never replace it implicitly.
- The story reader distinguishes missing/stale story routes or Script from
  transport failures, linking to the owning Creator or Script preparation view.
  An optional Storyboard read failure preserves the qualified Script and selected
  route; its named retry repeats only that read. Currentness and report sandbox
  checks remain unchanged.
- Script/Storyboard original-report readers share subject-specific Chinese
  labels and explicitly identify the read-only presentation. Retained originals
  do not track later confirmed-content edits; report JavaScript is not called
  “脚本” in creator guidance where it can be confused with the story's “剧本”.
  Reading labels and helpers do not change static projection, report bytes,
  admission, sandbox permissions or generation/confirmation actions. Original
  reports may cover more episodes than the selected route-filtered reader.
- Failed gallery refreshes retain known images and local author inputs, but
  suspend mutations until a successful owned read. Manual retry pending belongs
  to its retry operation, independently of the latest-read owner; an overlapping
  observation cannot strand the retry button. Session changes invalidate both.
  Read-only/error states do not start automatic delivery observation. Guidance
  must reflect that authority, and an empty gallery must not claim a selected
  identity reference. The archived workspace fieldset still disables its controls;
  reading retained values is not a claim of interactive archived comparison/retry.
- Run, attempt and subtask states have distinct Chinese presentation labels;
  stable codes and original attempt data remain inspectable. A persisted failed
  attempt with `outcomeUnknown=true` is presented as uncertain, not known failure.
  Pending cancellation remains observable; the deliberate server re-signal action
  says “再次请求取消,” not an apparently first cancellation. This is presentation
  alignment, not a new cancellation/retry contract or a compatibility adapter.
  Trace stage selection, status and failure explanation use separate rows;
  adding evidence must not squeeze a short status badge or task identity into
  fragmented text. This is a surface layout rule, not a short-screen workaround.
  Both empty event details and their progress helper must follow actual event
  availability; an in-progress event uses an accent tone, never success green.
  Uncertain attempts use a neutral request event kind, not a failure-record tag.
  Full timestamps occupy their own row above event context; a fixed time column
  cannot safely contain ISO dates. Desktop capture asserts non-overlapping bounds.
  Outcome-unknown guidance describes the uncertain result, not only whether the
  request arrived. Rebuild guidance warns that fresh requests can duplicate work;
  it does not add or remove server-issued operation eligibility.
  The obsolete trace-to-quarantine adapter, its historical test and deprecated
  raw-output/repair-hint fields are retired. Current progress owns repair lists
  and eligibility; original trace evidence remains readable, not rewritten.
- Reviewed original/segment previews surface native browser media errors with
  readable recovery guidance and exact secondary error evidence. An explicit
  reload reads only that same media; it never generates, selects or autoplays.
  Media identity changes reset preview-local error state. Playing either preview
  pauses other original/segment previews; story playback remains independently owned.
  Error guidance has a player-owned stacked layout, so descriptive copy cannot
  squeeze its recovery controls. Expanded raw evidence wraps without being truncated.
- Structural card layouts target cards, not every button in their container;
  generic actions retain their normal control layout. Chinese interface fallback
  errors and directory/run/configuration times use one readable Chinese/24-hour presentation while
  retaining exact HTTP status, raw error evidence and timestamp values.
  Timestamp presentation uses the reader's local timezone; it does not normalize
  or rewrite stored times or raw trace evidence.

## Alternatives, consequences and guardrails

Reject selector exceptions, higher nested z-index values and rewriting creative
source to make labels unique: each treats a downstream symptom. Preserve bounded
shot descriptions and explanatory structural gaps. Test native label/control and
name/description separation, dialog hit testing as well as bounds at all three
supported desktop sizes, identical-prose shots with exact recovery targets,
and keyframe-summary clicks that reveal their owner without API writes.
Direct viewport inspection remains required by E22; DOM visibility is insufficient.
Do not infer completed playback from reaching duration: a decoder may disconnect
without a native ended event. Preserve that failure and diagnose it separately;
error presentation is not a decoder fix, timeout workaround or quality approval.
Native browser gates retain event/decoder snapshots before teardown even on early
failure. Diagnostic snapshot, byte collection and detach are bounded and mark
incomplete reads; they must not delay or weaken unchanged playback/ended acceptance.
Every native collector caller supplies its exact response filter and trace reader;
the plain fixture probe cannot silently inherit the application playback endpoint.
Completed partial HTTP byte ranges are data attachments, not standalone MP4s;
only a complete response object may carry that media filename/type. Retain the
exact Content-Range, response hash and available bytes without reconstructing media.
Screenshot journeys wait for the intended content state, not just a page heading;
an eligible repair capture must show an enabled repair control before recovery.
