# Autosave, automatic resume and project Freeze

Status: implementation, local qualification and bounded activation approved by
the owner on 2026-10-24 through Relay Direct, carrying standing approvals forward.
Planning baseline: retained R `main` at `01337c1b9892116a1cd0fc7f70d565ea8e32505a`.
Installed P starts at qualified `4c6db5ff`. Approval covers this plan's bounded
implementation, local tests, preservation-checked activation and necessary
controlled backend restart. Excluded operations below remain excluded.

## Outcome and owner decisions

The creator works without a project Close ritual: unfinished edits are preserved
automatically, switching/leaving preserves progress, and returning resumes it.
Saving working input does not approve content, install production or start jobs.
Freeze is a deliberate optional restriction, distinct from saving, navigation,
Archive and Delete. This applies to Creator, Professional and their project
authoring/review/media editors, including the shared graph.

Owner-confirmed in this planning conversation on 2026-10-24:

| Decision | Chosen behavior and reason |
| --- | --- |
| Everyday workflow | Autosave; remove project 关闭, 保存并关闭 and 强制关闭 actions/statuses. Idle does not become frozen automatically. |
| Return to a project | Automatically resume matching autosaved edits. Prompt only when versions, ownership or competing edits conflict; avoid a routine 恢复草稿 step. |
| New blank project | Clicking 新建空白项目 immediately creates one persistent unnamed draft, even before a valid Brief exists. Unused blank drafts may remain in the directory. |
| Built-in teaching example | 打开示例项目 is a read-only preview; 创建编辑副本 explicitly creates a persistent editable project. Opening a preview creates no project. Existing saved projects named 示例 are unaffected. |
| Frozen access | Allow read-only browsing and already-ready playback. Block edits, confirmations/approvals and new generation; usual playback/currentness checks still apply. |
| Effect on production | Autosave working edits. Updating confirmed story/production inputs remains an explicit 应用修改/确认 action, so typing does not invalidate existing production. No automatic approval or generation. |

The resume, immediate creation, teaching preview, frozen access and explicit
production-apply choices were each answered explicitly through native question UI.
The earlier suggestion to only rename Close is superseded by this broader workflow.
The completed [directory action plan](2026-10-24-project-directory-actions.md)
remains historical implemented behavior until this plan is implemented.

## Root cause and inspected current behavior

Durability, adoption and folder admission have been combined in user-facing Save/
Close flows. Existing project-owned draft storage is useful, but coverage and
recovery are inconsistent; simply hiding Close would remove some editors' only
server flush. Automatically invoking every Save handler would also approve or
invalidate production. The repair belongs in draft persistence, editor lifecycle
and operation admission, with explicit semantic actions kept separate.

| Current surface | Owning entrypoints | Reuse / gap |
| --- | --- | --- |
| Brief and professional canonical editors | `frontend/src/app/workspace/useProjectAuthoringPersistence.ts`, `frontend/src/features/authoring/useAuthoringDraftAutosave.ts`, `frontend/src/pages/BriefPage.tsx` | Existing delayed draft CAS and explicit canonical writes. Draft validators currently require canonical-valid Brief/stage objects; empty numeric input/incomplete content needs a bounded working-input representation. |
| Creator/Pro graph and source branch map | `frontend/src/features/graph/GraphWorkbenchProvider.tsx`, `GraphWorkbenchContext.tsx`, `frontend/src/pages/SectionMapPanel.tsx` | One typed graph draft owner already shared by both modes; preserve binding/hash/field-buffer safety and explicit confirm/install boundaries. Do not add a second graph autosaver. |
| Source, cast, art and script | `frontend/src/features/authoring/reviewDraftStore.ts`, `ReviewDraftContext.tsx`; `frontend/src/pages/SourceOutlinePage.tsx`, `CastPanel.tsx`, `ArtPanel.tsx`, `ScriptPanel.tsx` | Narrow review buffers retain text locally; `update()` does not schedule a server flush. Server flush is registered with Close; matching recovery is explicit. Script input also carries a section identity. |
| Shot visual intent and image direction | `frontend/src/visual-intent-drafts.ts`, `frontend/src/image-job-direction-drafts.ts` | Existing project/entity/basis-bound durable queues. Preserve exact draft consumption, stale-context refusal and retained writers on target changes. |
| Production intent and presentation | `frontend/src/pages/useProductionBridgeReview.ts`, `ProductionBridgePanel.tsx`, `ProductionPresentationReview.tsx` | Local editor state and an explicit-review Close guard are not durable autosave. Some Save buttons mean adoption; preserve that explicit decision and add separate typed working buffers. |
| Shot presentation and reference/review input | `frontend/src/features/media/keyframes/ShotPresentationReview.tsx`, media reference/image preparation owners | Shot presentation has a tab-session cache and dirty Close/unload guard. Inventory authored notes/directions per entity; consent/file selections cannot become resumed authorization. |
| Navigation, recovery and status | `useWorkspaceNavigation.ts`, `useAuthoringDraftRecovery.ts`, `useWorkspaceProjectLoader.ts`, `WorkspaceController.tsx`, `draft-registry.ts`, `projectDraftCache.ts` | Current navigation flushes the active legacy scope, not every project editor. Several caches are `sessionStorage`; global unload/status coverage is incomplete. Matching recovery often needs a manual click. |
| New project and teaching identity | `src/plotloom/api/contracts.py`, `src/plotloom/brief_contracts.py`, `frontend/src/app/workspace/useProjectInitialization.ts`, creation/reservation owners | `ProjectCreateRequest` requires valid `ProjectBrief`; title/synopsis are nonempty. A persistent unfinished project needs an explicit draft-creation contract; no invented canonical synopsis. The built-in example is currently a local editable workspace persisted only on Save. |
| Stored draft contract | `src/plotloom/domain.py`, `review_drafts.py`, `api/contracts.py`, `persistence/project/drafts.py`, `project_storage/project_handle.py` | Existing per-project `v2_authoring_drafts`, scoped identities, revision comparison, credential exclusion and canonical consumption. Extend typed coverage, not arbitrary browser snapshots. |
| Freeze, reads, snapshots and deletion | `frontend/src/app/workspace/useProjectLifecycle.ts`, `ProjectDirectoryRow.tsx`, `src/plotloom/api/project_folder.py`, `project_storage/registry.py`, `operational_state.py` | Current Close blocks ordinary reads as well as writes. Many GET routes share `opened_project`; frozen browsing needs genuine read-only admission. Snapshot already owns an exclusive operation and does not require closing first. Preserve deletion and UNKNOWN guards. |

## Proposed behavior and architecture

### Working input and explicit adoption

Extend the existing project-owned typed draft mechanism. A separate generic
autosave database would add a second authority and duplicate ownership/revision
rules; it is unnecessary for this scope. Refactor shared queue mechanics only
where the inspected owners need them; retain domain-specific validation/binding.

- Preserve text, incomplete JSON and temporarily invalid form values as bounded,
  typed author input. Canonical validation remains strict at Apply/Confirm. Do
  not broaden accepted-story schemas to make an unfinished editor valid.
- Identify input by project, editor, entity and its source/version basis. Multiple
  script sections, shots, reference targets and production packages must not share
  one mutable buffer accidentally. Acknowledgements cannot clear newer typing.
  Successful deletion erases only that exact project's local journal after its
  server receipt; refused deletion must retain it. Extend existing scoped erasure
  and honest local-cleanup failure reporting to the new journal.
- Keep a durable local journal for unacknowledged authored input and autosave it
  to the project store. This is working-input preservation, not snapshot history
  or a general offline application. Choose the smallest browser store that proves
  tab/browser restart recovery and bounded quota failure behavior; tab-session
  storage alone is insufficient. Preserve separate client ownership/conflict rules.
- Autosave must not call canonical Save/Confirm/Apply/Accept/Dispatch handlers.
  Replace routine persistence buttons with status. Where an existing Save adopts
  content or changes production inputs, give it an accurate explicit Apply/Confirm
  name and preserve its checks. Merely renaming every Save is not completion.
- Matching working edits resume automatically in the correct editor/entity,
  including after server/browser restart. Show 已自动保存 and, where relevant,
  尚未应用. Production/playback continue using explicitly confirmed eligible
  versions; generation controls explain unapplied edits rather than silently
  consuming older or unapproved input.
- Headers and directory identification must reflect the saved working title,
  including unnamed drafts, without changing a confirmed production Brief merely
  to update its display. Keep the working/confirmed distinction visible where it
  matters; do not leave a renamed project apparently unsaved in the directory.
- Retain matching unsent local revisions over older server reads. On version or
  competing-client conflict, preserve both sides and offer the existing explicit
  resolution workflow. Never silently merge/rebase reviewed content or use
  last-write-wins. Lost acknowledgements reconcile the exact receipt/payload
  before any replay; they do not reset revision counters.

### Creation, navigation and save feedback

- New-project intent creates exactly one persisted draft identity immediately,
  with an honest 未命名项目 display and no fabricated confirmed Brief. The new
  contract distinguishes unfinished working input from confirmed production
  prerequisites. Retain strict validation for generation and canonical adoption.
- The built-in teaching example is a read-only preview with an explicit 创建编辑副本
  action. Creating its editable copy uses supported teaching content only; do not
  copy illustrative run/trace history as real execution, approvals or job authority.
  Directory projects with 示例 in their titles retain their actual lifecycle.
- Reuse existing creation reservation/idempotency ownership. A delayed/lost create
  response, double click or route change cannot create duplicates or attach A's
  input to B. Preserve early input locally until its intended project binding is
  acknowledged. Home/Exit/Back must never create an empty project as a side effect.
- In-app project/page/entity navigation checks every applicable pending writer,
  including unmounted editors. Flush promptly without applying content. Once
  preservation succeeds, leave normally and let admitted background jobs continue.
  退出工作区/返回首页 use this preservation path, never the former force-exit
  discard/Close operation. Explicit discard remains a separate deliberate action.
- Show saving, server-saved, locally-preserved-but-unsynced, failure and conflict
  truthfully. An aggregate 已保存 requires every included author-input scope to
  be acknowledged; a local copy alone cannot claim server durability. Status for
  A cannot overwrite B's status after navigation. Aggregate status covers this
  client's editors and retained writers, not unknown input in another client.
- On connection failure, retain a verified local journal and show unsynced state;
  allow safe navigation without discarding that input. If neither local nor
  server preservation succeeds, keep input visible and block ordinary in-app
  departure until retry, copy-out or explicit discard. Do not turn leaving into
  implicit consent to discard. Browser unload cannot guarantee asynchronous work:
  warn only for genuinely unpreserved input; never rely on a final unload request.
- Resume pending draft synchronization after reconnect with current ownership and
  revision checks. Do not resume generation, restore consent or clear UNKNOWNs.
  No cross-device/offline-generation or background-daemon guarantee is added.

### Optional Freeze and related project actions

- Remove project Close/force-close labels and routines from toolbar, directory,
  navigation prompts and notices. Ordinary rows have no 未关闭/未冻结 label;
  current identity and relevant exceptional states remain visible. Closing a
  dialog/window remains ordinary UI behavior.
- 更多 offers 冻结项目 / 解除冻结. Freeze flushes working input without Apply,
  settles the requesting client's writes/reads, then invokes the authoritative
  exclusive/quiescent server gate. Busy or uncertain external work refuses Freeze
  with a reason; it is never cancelled, force-cleared or queued for an automatic
  later Freeze. Idle projects stay editable until the user requests Freeze.
- Frozen projects remain navigable read-only and already-ready stories remain
  playable. Do not secretly Unfreeze to satisfy a GET. Separate read-only access
  from mutation/dispatch admission; loading must not reconcile or acknowledge a
  job, alter a draft, consume consent, or restore edit capability.
- Unfreeze restores editing admission only, without applying drafts or restarting
  jobs. Existing persisted closed states become the product's Frozen state through
  an explicit documented mapping; choose private storage/API names on merit, not
  a vocabulary-only format migration. Preserve source/draft history and IDs.
- Archive/Restore, Freeze/Unfreeze, navigation and Delete remain distinct. Restore
  does not silently Unfreeze. A frozen row can open read-only; 更多 owns Unfreeze.
  Supported Snapshot/Copy commands retain their operation-owned safety checks and
  do not require routine manual Freeze. Direct external folder copying still
  requires the documented stable-folder/exclusive-lease contract; do not imply
  that an arbitrary live filesystem copy is safe. Preserve snapshot/restore CLI.
- Freeze affects the whole project's write admission, but cannot save another
  client's unacknowledged input. Late writes must be refused and retained locally,
  never relabelled saved. Read-only presentation and active-session pan/zoom remain
  separate; do not expand the agreed visual preference lifetime.

### Explicit exclusions

No automatic creative acceptance, canonical installation, generation, job
resubmission/cancellation, media selection or deletion. No provider/settings/
credential autosave into project drafts. No new remote sync service, editor
history system, generic browser snapshot or automatic backup. Preserve authored
notes/requirements without restoring consent checkboxes, explicit review
acknowledgements, file-upload authority or paid-operation authorization. A local
File selection that has not been explicitly imported needs an honest pending-file
guard; do not silently upload it to satisfy autosave. Existing UI-only visual
preferences keep their established lifetime.

## Ordered implementation deliverables

1. **Contract and data preflight.** Finish the concrete editor inventory above,
   including reference/assignment inputs, with exact durable owner and semantic
   Apply action for every editable field. Resolve draft-project creation, partial
   input representation, read-only frozen access and data/rollback shape before
   dependent UI work. Reuse schema/leases/revision machinery where possible. If a
   format upgrade is necessary, prove the smallest explicit preservation-safe
   upgrade on fixtures; never reset valued projects or introduce general legacy
   replay. Record a concise ADR amending the relevant clauses of 0043, 0087,
   0113, 0115 and 0129; update product/engineering specs and acceptance wording.
2. **Persistence foundation and smallest real slice.** Implement immediate draft
   creation and explicit teaching-copy creation, one complete Brief working-input
   autosave/resume path, scoped status,
   local failure preservation and safe navigation. In the existing isolated real
   UI/API/project-folder fixture create A/B, type an unfinished Brief, obtain a
   durable receipt, leave and return automatically, then restart the owned backend
   and open a fresh browser context. Read back the exact unfinished values with
   zero provider calls and unchanged canonical/approval state. Prove this before
   expanding editor coverage or running broad qualification.
3. **Complete editor coverage.** Extend source/cast/art/script, professional stage
   editors, the shared graph and media direction owners, production intent/
   presentation and shot/reference author-input adapters. Keep one shared graph
   writer and exact entity/basis ownership. Remove dependence on Close-time server
   flushes; retain explicit Apply/Confirm and generate eligibility. Verify each
   inventory row, including invalid input, remount and context-change cases.
4. **Navigation and Freeze integration.** Replace the Close surface, complete
   project-wide save/leave aggregation and matching auto-resume, wire Freeze to
   genuine read-only browsing/playback and authoritative write/dispatch refusal.
   Prove frozen ready playback, busy-Freeze refusal, Restore+Frozen ordering and
   unfreeze without replay on disposable fixtures early in this step.
5. **Stable independent review and qualification.** Freeze source for a bounded
   read-only review of persistence, creation, navigation/recovery, frozen read/
   write admission and evidence. One implementation/qualification execution owner
   fixes concrete findings with causal checks. This crosses API/persistence/
   admission contracts, so final qualification is the existing unfiltered local
   `uv run --locked --no-sync python scripts/verify.py full`, not the frontend-only
   exception. Refresh generated assets, verify deterministic complete build trees,
   inspect three desktop sizes and exercise the actual checked/static runtime.
   Retain failures; reuse unchanged evidence and rerun affected checks after
   diagnosed changes rather than repeatedly running the full suite during edits.
6. **Preservation-checked activation and handoff.** Keep a coherent scoped local
   `main` checkpoint. Independently review actual final/source/evidence and idle
   handoff. Capture fresh live identities, quiescence, every current valued project
   (including the eight known at planning), current drafts/assets,
   application/host/settings/accounting and both UNKNOWN
   holds. Activate the qualified source/static/backend through the existing
   deployment route; plan one controlled backend restart if required. Read-only
   native inspection must show the new UI and existing ready story still usable.
   Compare before/after against only the explicitly reviewed format changes;
   preserve all authored/canonical/media values, grants, historical receipts and
   holds. Root closes completed attended workers after collecting actual finals.

## Acceptance and evidence

- A fresh draft exists once after New; incomplete or invalid input survives server
  and fresh-browser restart. No fabricated canonical Brief, duplicate creation,
  phantom projects from Exit/Home, cross-project input or accidental generation.
- Opening the built-in teaching preview performs no create/write; explicit editable
  copy creates one correctly scoped project without job/approval side effects.
  Existing saved examples remain unchanged and editable according to their state.
- Every inventoried input has a durable owner; meaningful text/JSON/raw numeric
  buffers survive fast typing, page/entity/project switches, refresh and remount.
  Creator↔Pro shares the same graph edits. Saved work resumes without Restore.
- Delayed reads, failed/lost acknowledgements, concurrent tabs, basis changes,
  freeze races and local quota/network failure preserve exact input and truthful
  status. Older callbacks do not paint/save/discard newer workspace input.
- Autosave changes only working progress: confirmed source/graph/production hashes,
  approvals, installed media and dispatch counts stay unchanged until the exact
  explicit semantic action. Invalid work cannot be applied or generated.
- Freeze preserves drafts, rejects active/unknown work and later mutations, allows
  read-only viewing/eligible playback, and Unfreeze never replays a job. Archive,
  snapshots/restore, scoped deletion and UNKNOWN safeguards keep their contracts.
- Actual UI journeys cover 新建→编辑→离开→返回, failed save/retry, fresh context,
  two-workbench switching, production drafts and Freeze/read/play/Unfreeze.
  Native Safari and 1280×768 / 1280×460 / 1700×900 pixel inspection complement
  isolated regression proof; no live project edit/freeze/delete is QA authority.
- The first evidence slice precedes scale. Final logs/manifests, exact qualified
  revision, package/runtime identities, explicit reuse, preservation differences
  and human/agent limits are durable. No new media generation is needed.

## Execution permissions, rollout and rollback

The owner approved the complete bounded sequence through Relay Direct, including
local tests/fixtures, necessary typed draft/API/admission changes and a controlled
backend restart at a verified quiet checkpoint. Standing worker/model selection
approvals continue; routine milestone approvals must not be requested again. Work is
serial in retained R `/Users/wjmao/.codex/worktrees/b30f/plotloom`; installed P is
`/Users/wjmao/projects/HU/plotloom`. Model/effort selection and announcements occur
at native dispatch under Relay Direct, with attended read-only subagents and one
source writer. Planning created no tasks; implementation may now dispatch them.

No provider call, new QA grant, historical runtime-grant rebind, authored-value
edit or Freeze/Delete of a live project, bridge restart, push or GitHub CI is
included. Only an explicitly reviewed, fixture-proven structural upgrade may
change existing project storage during activation, preserving all authored values.
No UNKNOWN hold may be cleared. If actual data/activation requirements exceed
this boundary, name the concrete uncovered action and resolve it before execution.

Prove rollback on fixture data before activation. A code/static rollback is
sufficient only if the prior binary can read every stored schema and payload;
verify this, including draft-only project creation. A structural upgrade can make
an older binary incompatible even before the first new edit. After that boundary,
preserve drafts and use a verified readable fallback or forward repair. Preflight
must specify the exact boundary and fallback; hold activation if preservation-safe
recovery cannot be demonstrated. Rollback never means dropping new drafts,
rewriting canonical history or resetting valued projects. Record accepted format
transitions explicitly rather than claiming unchanged database bytes when a
reviewed upgrade actually changes them.

Stop after the approved workflow is implemented, independently reviewed, locally
qualified, preservation-checked and activated, with coherent source/docs and idle
cleanup. No owner personal/creative acceptance or general release claim follows
from agent-operated functional verification.

## Execution checkpoint — D0 / first slice (2026-10-24)

- Contract decision: ADR 0218. Existing SQL layout/rows unchanged; nullable JSON
  Brief identifies unfinished projects. Old-reader compatibility ends at new
  draft-only/new payload writes; qualification must prove a readable current
  fallback, not claim catalog omissions mean compatibility.
- Smallest owned fixture: existing production project-folder runtime, offline
  provider seam, A/B draft-only projects, empty duration and synopsis. This worker
  owns fixture restart/settlement; manager owns installed runtime/Safari.
- First real proof passed before editor expansion: `focused --playwright
  e2e/working-project-autosave.spec.ts`, 1 passed, journey 3.5s / runner 7.802s.
  New A → unfinished title/empty duration → Home → New B → Home → A automatic
  resume → backend restart → fresh context exact readback. Canonical Brief null,
  runs empty, provider requests empty. Focused API restart/replay test also passed.
- Two first failures were test locator errors before round-trip assertions;
  retained logs `.local/autosave-first-slice-browser{,-2}.log` and screenshots/
  traces under `.local/autosave-evidence/`. Accessibility snapshot supplied the
  numeric role/name for the causal selector correction. Passing log:
  `.local/autosave-first-slice-browser-3.log`. No full gate run.
- Next: complete typed editor coverage and frozen pure reads, then stable review,
  one final full qualification and manager-owned preservation/activation.

## Execution inventory — source review checkpoint

The following is the locally qualified source inventory. Composite execution
and retained failed runs are detailed in the verification receipt; root-owned
installed preservation/activation remains separate. All rows use existing typed
project draft CAS; the graph keeps its single writer. A server receipt preserves
working input, never semantic acceptance. Ordinary settings/credentials remain
outside these journals.

| Authored input | Owner/entity/basis | Explicit semantic action / exclusions | Evidence so far |
| --- | --- | --- | --- |
| Brief title, synopsis, selections, raw numeric targets | `brief/root`, project revision; `BriefWorkingInput` | Apply/Confirm converts exact raw receipt; optional title fallback only here | A/B browser restart/fresh context; backend raw adoption, bounds, nullable lifecycle |
| Unsubmitted custom direction label | `review_buffer/brief_custom:group`, fixed basis, base0, <=120 | Enter/+ adds selection; unrelated Apply leaves scratch text | Independent scratch/backend Apply preservation |
| Bible, Scene Beats, Storyboard fields including unfinished numbers/line lists | Existing stage/root, stage revision; named structural working models | Existing explicit stage Apply validates canonical model | Typed partial-stage validator; both raw Beats duration fields |
| Creator/Professional graph including raw JSON | Shared `story_graph/root`, existing graph context and field buffers | Existing graph Confirm/Apply; no second writer | Graph provider/read/admission cases; real leave/restart single-root browser proof |
| Source/adaptation input | `review_buffer/source`, source revision | Confirm Source; no source content accepted by autosave | Fresh browser/backend restart and local-only reconnect after unmount |
| Cast / Art JSON and authored directions | `review_buffer/cast`, `art`; exact candidate/accepted revision/hash/status | Existing explicit candidate/reopened Save; consent excluded | Focused ownership/currentness; real leave/restart cast/art |
| Cast/Art render choice | `cast_settings`, `art_settings`, render-style basis | Prepare remains explicit; provider/profile secrets excluded | Bounded known choice adapter and existing workflow tests |
| Script section JSON | `script:sectionId`, accepted script revision/hash/status | Save only that section; other sections independent | Per-section CAS; browser adaptation selects matching section before auto-resume |
| Production intent / presentation text, spans and reasons | `production_intent:proposal`, `production_presentation:proposal`, proposal revision/hash and source hash | Explicit Save/Confirm; exact applied-entry cleanup; no install/generation | Production basis suite and A/B receipt race tests |
| Shot presentation physical text, literals/mode, reason | `shot_presentation:shot`, source hash/revision | Explicit reviewed confirmation excluded from journal | Typed remount/currentness suite; confirmation stays fresh |
| Visual intent / source-ref raw text | `visual_intent:shot:asset`, storyboard/current media context | Explicit Save normalizes and validates; malformed duplicate/33-line refs can autosave | Invalid raw save/restart; Apply422 retains receipt; quota/offline guards |
| Image-job direction | `image_direction:shot:target`, exact target/context | Explicit prepare/send; blank and whitespace preserved | Exact CAS, retained writers, first quota/offline/unload |
| Keyframe compatibility note | `keyframe_compatibility:shot:asset`, candidate hashes/intent/approval/storyboard basis | Explicit keyframe review; approval excluded | A/B candidate note identities and receipt chains |
| Character reference ideas/import label/origin | `character_reference:character`, cast revision | Prepare/import/send/select explicit; File not journaled | Pending File A→B blocked, explicit cancel→B, no stranded guard |
| Art reference requirements | `art_reference:subject`, accepted art revision/hash | Prepare/select explicit | Known subject adapter; art preparation/ownership tests |
| Reference and same-person observations | `managed_reference:character`, `same_person:binding`, storyboard/identity mapping basis | Reviewer identity, judgment and productionDecision excluded | Fresh reviewer with recovered observations; media currentness tests |
| Managed import origin/additions | `managed_reference:import:shot`, storyboard basis | File selection/upload and rights authority stay explicit | Typed text adapter plus pending-file guard |
| Manual H3 English and raw seed | `h3_directions:shot`, exact source identity and returned source hash | Fresh source read, checkbox, compiled approval and request identity required | Raw00042/English remount; stale source disables editing; rejected race blocks departure |
| Batch English per shot/path | `video_directions:batch`, exact manifest hash and owned shot/path | Directions Apply/recompile and Start explicit | Known manifest/target adapter; complete browser allocation/composite closure in receipt |
| Video pack observations, rejection reason, segment/reopen notes | `video_pack_notes:batch`, `take_rejection:job`, `video_segment_notes:job`; exact review/job/selection/source basis | Operator identity, review judgment, reopen/replace/dispatch authority excluded | Owning adapters/current review suites; final UI allocation/composite closure in receipt |
| Whole-material review text / manual retry directions | `material_review:bundle`, `text_retry:attempt`, exact bundle/run/rejection basis | Judgments, authorization, retry commands and confirmation excluded | Material text projection excludes authority; existing review tests |

Read-only/frozen recovery disables editing and does not resume observers or
reconcile dispatched work. Native report/status and batch current/review queries
use read admission. Service fixtures compare complete logical rows/files and
confirm POST refusal. Real ready UI playback advanced currentTime in both media
panel and play route with zero non-GET project requests.

Independent source review matched the frozen manifests and returned concrete
quota-closure, candidate-identity, navigation, raw-number, reviewer-attribution and
restored-read-lock defects. Focused fixes passed before residual delta review;
residual direct-folder restore, reused local counter and stale-edit race fixes passed causal verification and independent closure. A later existing branch browser fixture exposed write transactions in query helpers and ordinary departure joining an already-owned branch POST. The bounded query/read-head and departure/drain separation fixes have their own focused evidence and delta review. First failures remain in `.local/autosave-*.log`.

Actual rollback fixture: prior `4c6db5ff` directly refuses null-Brief homes with
`ProjectStorageCorruptionError`. It can open/read an extended raw draft, but its
old canonical draft validator refuses the empty numeric payload with
`ValidationError`. Current source reopens both and preserves exact logical rows
and files (`.local/autosave-rollback-proof-2.log`, 1 passed). This does not claim
all raw read-open paths refuse extended payloads, nor that an old binary can
safely continue editing them. Retained qualified source/static remains the
post-boundary fallback; no live rollback/migration was executed.

## Qualification execution boundary

Implementation is committed on local `main`: `008898d7`, `4f072cca`, test-only
`33b3813c`, reviewed post-full backend `7f8c554a`, and final executable/static
candidate `efd665b870f74d2eecb416e0e2e8de8e1800b8cf`. All independent source and
browser-expectation reviews are closed. Durable owner decisions and reasons live
in ADR0218 and owning product/engineering clauses; the decision index and manual
link there. No chat transcript or parallel plan is needed.

The single unfiltered full invocation and its continuations remain failed where
they failed: first frontend1506/14, native3971/9, initial browser328/29, final
stable browser356/1. Diagnosed failed/affected checks and the remaining exact full
command objects close composite qualification under AGENTS.md; no failed run is
renamed green. Fresh frontend1532 passed; both types passed; full affected
lifecycle6 passed after the Restore acknowledgement fixture correction; the351
unaffected final browser cases are reused. Complete deterministic7-file trees
match, final3viewport pixels are retained/inspected, wheel build and installed
smoke passed. No second complete Python run or second `full` invocation occurred.
The [durable verification receipt](../verification/2026-10-24-autosave-and-project-freeze.md)
owns exact selections/results, complete manifests, failure classifications,
evidence reuse and rollback-reader versus old-validator limits. The qualified
source/static/wheel recovery package is retained. Root owns installed data
preservation, activation and Safari review after the worker's actual idle handoff.
No push, hosted CI, live project/UNKNOWN mutation or installed operation is claimed.


## Installed guidance follow-up — same assignment

Manager's read-only Safari review of installed938c7e46 found a guidance projection
defect: generic read-only copy called teaching/Frozen states snapshots and advised
Restore, while teaching-only identity/nav/toolbar/Pro placeholders suggested Save.
The existing lifecycle and `teachingPreview` facts now select truthful status and
next-step wording. No API, persistence, admission, generation, dependency or
preview-data behavior changes. Source review closed on the four-file frontend
manifest `b74ac4e1…`. The original qualification and failures remain retained.

Focused98 and fresh entire1538 frontend cases passed; both types passed. Bounded
browser9 first returned8 passed/1 new ambiguous region locator failure; exact-name
selector correction passed the preview case (including zero writes/provider calls
and exactly one explicit editable copy). Frozen/archive/archivedFrozen guidance
retains project/drafts/runs and admits no browser mutations. Three new checked-
static desktop pixels were retained and inspected. Fresh complete7-file buildA
is recorded; second-build parity, exact wheel/smoke and current readable recovery
package finish this frontend-only handoff. No repeat Python/full/browser358 run
is required by this reviewed presentation-only dependency surface. Root owns P,
Safari and later static activation; the worker does not operate them.
