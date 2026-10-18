# Batch video production and workflow completion

Status: approved for implementation and the consolidated delivery permissions
below, 2026-10-18. The owner requested execution through Relay direct and gives
standing approval for separate Relay worker chats, recorded in `AGENTS.md`.
Actual owner-story generation and human material/video approval remain separate
explicit actions; implementation approval does not perform them.

## Current implementation checkpoint

The delegated source owner has implemented steps 1–4 in the retained checkout
`/Users/wjmao/.codex/worktrees/b30f/plotloom`. Independent stable review findings
were addressed at native proposal, retained prediction, foreground intent and
player read owners. Step 5 local software qualification is complete through
full-run evidence, an exact corrected navigation-spec rerun and downstream wheel
checks. Initial product source is `575907e7`; its test-contract revision is `52ad5889`.
Manager-review corrections are implemented at `20e3c65b`: startup/index isolation,
current adopter execution authority, exact-run completion intent and retained
proof-boundary coverage. Their affected checks pass; see
`docs/verification/2026-10-18-batch-video-corrections.md` for scoped requalification
and reuse of unaffected full evidence.
See `docs/verification/2026-10-18-batch-video-production.md` for exact evidence,
retained failures, measured latency and the live-provider/hosted-CI gaps.
The manager closed correction review and authorized delivery. Source is published
at `00773e65`; unfiltered hosted CI was dispatched. One exact incompatible
cancelled development home was permanently removed through native revocation and
erasure, with UNKNOWN host facts/reservations preserved. Activation remains
pending because the other home's native revocation guard cannot prove absence
of a reused PID/group; the old `7b90bbc7` installation remains healthy. See
`docs/verification/2026-10-18-batch-video-publication-and-activation.md` for exact
targets, irreversible deletion, preserved settings, CI state and stopping evidence.

## Outcome and settled choices

Add a batch path beside manual video production: prepare one setup, explicitly
start production of all missing clips, then review all results together. The
creator makes one final whole-pack decision before new clips enter story playback.
There are no normal-case per-shot approval checkboxes or compulsory essays.
Existing manual preparation, editing and review remain available.

Batch scope is every unique production shot across all current story routes,
deduplicated by shot identity, not the selected route, filter or shot. Route-control
nodes do not produce clips. The current five-reference/42-shot project is a
realistic acceptance fixture, not a hard-coded product limit.

Owner choices: generate all missing clips, then one final review; unresolved
problems block whole-pack approval. Do not automatically select newly generated
clips for playback. Fix slow material loading, silent confirmation waits and
completion navigation in both the earlier image/material flow and the new video
flow. Preserve the distinction between technical qualification and creative
acceptance, including actual video and native-audio review.

Source baseline: `c5aabe252a83c6aa6708fbbbcf4fe704a771eaa3` in retained checkout
`/Users/wjmao/.codex/worktrees/b30f/plotloom`, on `main`. The same installation is
`/Users/wjmao/projects/HU/plotloom`, at `7b90bbc7` when inspected; production source
is identical, with a documentation-only successor in the retained checkout.
Recheck both before implementation. The completed
[whole-pack material review](2026-10-17-bulk-material-review.md) is the starting
contract, not unfinished work to recreate. Narrative Forge V1 stays out of scope.

## Evidence and root causes

The owner's screenshots show 30–40-second gallery loading, a gray confirmation
button with no useful progress, eventual successful material approval, and a
completion page below its useful next-action panel. They then reached the manual
storyboard page, with 42 shots missing playback clips. These are reported UI
observations, not a new audit of the project's current database.

Read-only source tracing and local measurements identified these owning layers:

- Every image/metadata route opens the project. `ProjectStore.open` performs full
  current review/autopilot admission, including repeated geometry provenance and
  artifact hashing. One localhost image took 0.957 seconds, almost entirely
  before transfer, versus 0.003 seconds for health. A read-only project-open
  profile took 0.977 seconds: 0.866 in review admission, with 168 geometry checks
  and 336 artifact gets. This demonstrates repeated admission work, not the exact
  share of the reported end-to-end delay or a network-only diagnosis.
- `useDeliveryEvidence.ts` starts four metadata reads. The gallery renders 47
  selected images and, after metadata arrives, 42 retained originals. Repeated
  full-project admission is amplified across those reads. Hidden-original media
  loading and request fan-out are secondary opportunities, not the root fix.
- `AutopilotWorkspace.tsx` polls every five seconds and updates `awaiting_review`,
  making “审阅完整素材” available without revealing it. Successful material review
  sets the run, closes the dialog and awaits `onChanged`, also without revealing
  its next action. Thus the earlier image batch has the same completion gap.
- General workspace navigation does not establish completion scroll/focus.
  Existing media navigation reveals local targets but lacks the dynamic sticky
  header offset already measured by `workspaceViewport.ts`.
- Video preparation/dispatch/reconciliation and segment review exist per shot;
  there is no durable project-wide batch owner or atomic whole-video-pack review.
  The current H3 directions editor requires source-bound reviewed English; it is
  not an existing automatic batch translation/preparation service.

Fix shared read/admission ownership, explicit operation state and completion
navigation at their owning layers. Do not hide these problems with a timeout,
fake approval text, relaxed evidence checks or a browser loop of 42 button clicks.

## Batch setup and frozen authorization

Place “批量生成缺失视频” prominently in the storyboard production entry and the
post-material-review next-action panel, with manual production alongside it.
Opening setup or preparing directions does not submit an H3 job. Present one
consolidated setup and prompt-review surface, not a sequence of per-shot forms.

Inventory the exact current project before offering Start:

| Existing state | Batch treatment |
| --- | --- |
| Current, explicitly selected usable playback clip | Keep unchanged; no generation or rewritten approval |
| One unambiguous current ingested candidate | Reuse and prepare an unselected review proposal; no H3 call |
| Exact compatible prepared job | Adopt only under the displayed manifest and reviewed-direction authorization |
| Known submitted/retrievable job | Observe/reconcile its existing prediction; never resubmit |
| UNKNOWN, ambiguous, rejected or stale evidence | Show a targeted preflight exception; no implicit replacement or reopening |
| Genuinely missing eligible clip | Plan one generation attempt within frozen limits |

“Missing” must not mean “not currently selected”: a pending or uncertain provider
outcome is not permission for another paid attempt. Existing conflicting work is
resolved explicitly through its owner, not erased by batch setup.

Show the global qualified H3 profile/quality, native-audio behavior, exact target
count, existing/reused work, per-shot authored playback length versus requested
source duration/frames, and explicit crop/pad choices where supported. Freeze a
stable per-target seed and dispatch identity. Default to one concurrent H3 job,
one attempt per missing target, a finite job cap and total requested-seconds cap.
Use existing qualified profiles/durations; do not infer support from a broader
gateway envelope. Show costs only if an authoritative estimate is available;
otherwise show the workload and absence of a monetary estimate honestly.

Use the configured existing assistant workflow to draft complete English
directions from exact saved sources. Add a narrow preparation job kind if needed,
reusing existing process supervision, limits and reporting rather than creating
a new agent platform. Keep authored dialogue/visible text in its required original
form; do not rewrite the story or truncate canonical sources to fit field limits.
Unsupported inputs become preflight errors before H3 dispatch.

The setup exposes every source-bound English direction and compiled prompt for
review. One explicit “开始批量制作” action endorses that displayed exact manifest
and its directions, using a typed batch-reviewed basis. AI drafting alone never
sets `reviewed_english=true`. Do not programmatically tick the existing individual
consent control or fabricate individual authored notes. The batch basis must be
validated by shared preparation/dispatch readers, not only accepted by this UI.

Bind authorization to the exact approval/storyboard/visual-selection revisions,
shot and keyframe/end-frame lineage, intent, source and directions hashes,
compiled prompt, timing, geometry choices, seed, profile and backend fingerprint.
Preflight the complete manifest before any new H3 call. Settings/source changes
invalidate affected consent and require a freshly displayed manifest; opening a
new preview must not silently authorize changed work. No new images, end frames,
characters or scene generation are included in this path.

## Durable execution and recovery

Add a small project-owned video-batch aggregate with frozen target links to
existing video jobs. Project files own portable facts/results; the application
owns the execution lease and provider-dispatch accounting. Reuse
[ADR 0045](../adr/0045-project-video-dispatch-ownership.md) and current job owners;
do not extend a frozen pre-video autopilot policy or invent cross-database
atomicity. Copies/restores cannot acquire fresh dispatch authority automatically.

One controller holds the bounded execution lease; short native transactions
record claims before transport. Do not hold database transactions across remote
generation. The runner uses existing prepare, submit, reconcile, ingest, media
probe and segment-proposal owners. The browser observes durable progress and is
not required to remain open. Refresh, process restart and another tab cannot
create duplicate jobs or competing dispatch owners.

Recheck target currentness, exact authorization and remaining caps before every
dispatch. A conflicting edit suspends unsent work and marks affected results
stale without deleting outputs or retroactively changing frozen requests. Prepare
frame-exact, unselected playback proposals only when supported: authored playback
length must remain exact at 24 fps and covered by the source. A default source
window is a proposal, not approval. No silent rounding, retiming, stitching,
audio fabrication or fallback backend is allowed.

Pause stops new dispatch; already dispatched work remains observable and its
outputs are retained. Resume requires the same still-current authorization and
unspent limits. Cancellation is local intent, not proof of remote cancellation
or an UNKNOWN resolution. Definite failures are shown and retained; any new paid
attempt needs a fresh explicit bounded continuation, never an automatic retry
loop. Known predictions may be polled; uncertain submission outcomes retain their
reservation and block replacement until safely resolved. Lost acknowledgments
are reconciled by exact batch/job identity and readback, not replayed POSTs.

## One final video review

On completion, show “审阅全部视频” with exact ready/failed/blocked counts and
direct exception links. The review includes all new/reused proposals in the
frozen scope and identifies already approved clips kept unchanged. Present
playable clips, native audio and exact timing; expose full source clips and
generation evidence in details. Play on deliberate user action, not 42 parallel
autoplays/downloads. Use the existing owner for explicit window adjustments.

One “确认全部视频并用于故事” action records structured human confirmation of the
displayed clips, native audio, intent and playback windows. Optional shared notes
remain optional. Do not claim watched/listened telemetry, author observations,
invent a reviewer name, or add a compulsory playback/scroll-tracking gate.
Opening the review, finishing generation or preparing a segment is not approval.

Failures, unresolved flags, missing/unreadable media, timing errors, latest
rejections and stale bindings block the whole action. A generic batch assertion
cannot override a rejection or convert uncertainty to PASS. Exceptional resolution
remains explicit under existing review rules; no partial-pack approval in this
slice. Cancelling review writes no approval and preserves existing selections.

The trusted owner recomputes the full scope and all per-shot selection revisions,
validates every target, then atomically records new selections and one immutable
versioned receipt in the project lifecycle transaction. No sequence of independent
selection requests, last-write-wins behavior or partial save on a late failure.
Store a truthful linked whole-pack basis consumed by shared playback/admission
readers. Do not rewrite unaffected selections or weaken normal manual contracts.
If the commit succeeds but subsequent refresh fails, report saved status separately
and reconcile it; never label the committed approval failed or submit it again.

## Loading and confirmation performance

First benchmark a realistic 42-shot project both awaiting material review and
with completed v3 handoff facts, then with prepared video-review facts. Capture
cold/warm gallery readiness, request/byte counts, admission work and confirmation
commit versus post-commit refresh time. An empty mock project is not sufficient.

Define a shared storage read/admission contract before changing execution:

- Separate cheap exact schema/project identity, lifecycle and confinement checks
  for inspection from full authority admission. Asset reads still verify requested
  bytes and lineage as required; corruption cannot become an approved substitute.
  Apply one named contract across equivalent readers, not an autopilot-only bypass.
  Cheap inspection alone cannot attest human approval, verified provenance or
  dispatch readiness; those projections require their exact validated evidence.
- Keep full currentness/evidence admission at writes, approval, dispatch and other
  authority boundaries, and required restore/export validation. Identify every
  current caller and preserve its actual security/authority obligations.
- Memoize repeated geometry/native proof only within an exact validated request
  or snapshot, with mutation invalidation. Do not introduce a global TTL,
  database-revision-only or mtime-only “already valid” cache. Files can change
  independently of SQL. Any cross-request proof reuse needs a separately explicit
  asset/store-incarnation/invalidation design and adversarial tests before use.
- Coalesce duplicate metadata reads and defer hidden retained-original pixels
  until requested where appropriate. Prioritize visible selected images and use
  bounded media loading; retain all provenance disclosures and unreadable-media
  blockers. Video sources use on-demand loading rather than eager full downloads.

Proposed local acceptance budgets on the controlled realistic fixture are warm
gallery readiness within five seconds, cold within ten seconds, and material
confirmation durable commit within five seconds. Report actual measurements and
environment, including network effects separately; these are targets, not measured
results or internet-wide guarantees. If missed, diagnose before claiming success.
Use deterministic work-count/contract regressions in CI, not fragile universal
wall-clock assertions. Do not reopen the paused general Python optimization work.

## Progress feedback and completion navigation

Use a shared, operation-owned completion reveal for both image and video flows:

| Transition | Reveal after successful state transition |
| --- | --- |
| Image/material batch becomes ready for review | “审阅完整素材” and exact readiness/blockers |
| Material approval commits and dialog closes | Approved status and batch-video/manual-production entry |
| Video batch becomes ready for final review | “审阅全部视频” and failures/holds if any |
| Final video approval commits | Saved status and story-playback next action |

Immediately show meaningful preparing/running/saving labels, live completed versus
total counts, and pause/recovery controls where applicable. Distinguish “正在保存
审阅…” from “已保存，正在刷新制作状态”. An error or uncertain acknowledgment has
a visible recovery action, not an indefinitely gray button. Prevent duplicate
submissions synchronously; do not make a fake percentage or success claim.

Reveal once for the explicit foreground operation in the same project/run/route,
after the target DOM and refreshed state are ready. Polling may detect image or
video completion, but must not scroll on every refresh or auto-open a review.
Do not steal focus/scroll while the user is typing, has dirty edits or another
modal, has hidden the tab, or has navigated elsewhere. Clear pending intent on
cancel/takeover/project/run/route changes. Background, rehydrated or already
completed runs show status plus an explicit “查看结果” link instead of jumping.

Explicit successful approval reveals its next-action panel without restoring the
old scrolled graph position; cancel preserves prior workspace position and
unrelated edit buffers, without adding a review-draft autosave service.
Normal “进入手动视频制作” navigation lands at the useful production/batch panel.
Explicit shot/entity deep links retain their precise target instead. Account for
actual sticky topbar/guide geometry through the existing viewport owner, support
reduced motion and keyboard/screen-reader focus, and do not merely scroll to a
generic page top hidden beneath sticky chrome.

## Ordered implementation and verification

One source writer owns integration in the retained checkout. Use bounded
read-only specialist review where useful; default Luna/Max for bounded probes,
Sol/Medium for ambiguous integration and Sol/High only for difficult/high-risk
architecture. Set and report actual supported dispatch settings.

1. **Contracts and feasibility.** Recheck baseline/activity; inventory all 42
   unique fixture targets, timing/profile eligibility and existing work states.
   Prove source-bound batch English preparation through the existing assistant
   contract. Record concise ADRs for batch direction/dispatch/review authority and
   shared inspection admission, including rejected alternatives and invalidation.
   Make current-versus-proposed boundaries explicit; do not declare ADRs accepted
   merely because this draft exists. Establish cold/warm performance evidence.
2. **Shared loading and completion behavior.** Correct repeated admission at its
   storage owner with targeted adversarial tests; add submission feedback and
   shared completion reveal to image readiness and material approval first.
   Exercise actual navigation/scroll positions, not only button existence.
3. **Frozen batch setup and runner.** Add cohesive batch models/repository/service,
   API projection, assistant preparation and durable controller using existing job
   owners. Exercise restart, pause, lease contention, stale edits, caps and UNKNOWN
   using provider fakes before any live smoke. Keep large existing files from
   absorbing unrelated orchestration; prefer small workflow-local modules.
4. **Whole-video-pack review.** Add review projection, atomic receipt/selection
   owner, exception UI, playback integration and video completion reveals. Verify
   late-target rejection rolls back the entire approval and latest failures cannot
   fall back to an older passing review.
5. **Stable qualification and delivery.** Independent review of authority,
   dispatch/recovery and the full user journey; resolve findings at their owners.
   Run proportional checks below, record evidence, commit/push normally, then
   safely activate the same installation only under the permissions below.

Primary source owners: `src/plotloom/project_storage/` (current schema/admission,
autopilot validation and video service), `src/plotloom/persistence/project/`
(video preparation, jobs, segments and new batch facts), `video_contracts.py`,
`video_jobs.py`, H3 directions/adapter and `api/project_folder_video.py`.
Frontend owners: `features/autopilot/` (`AutopilotWorkspace`, `MaterialReview`,
delivery evidence/disclosures), `app/workspace/` (navigation and viewport),
`features/media/media-owner-navigation.ts`, `StoryboardPage.tsx`, `video-pilot.tsx`,
`h3-directions-review.tsx`, segment review and new cohesive batch components.

Start with focused native cases, including `autopilot-review`, media navigation,
workspace viewport and `video-pilot-review` unit/browser owners. Add batch API,
repository, worker, directions, selection and playback cases. Include long complete
sources, multi-route deduplication, existing-good/missing mixtures, no-provider
preflight, ambiguous/UNKNOWN jobs, missing configuration, duplicate/lost requests,
two tabs, restart/copy/restore, stale CAS, late FAIL and atomic rollback. Shared
read tests cover out-of-band asset corruption, schema/WAL changes, confinement,
project replacement/lifecycle and inspection versus authority boundaries.

Browser journeys cover image Start → polled completion → visible review action,
approval → useful production entry, batch Start → leave/reload → resume → final
review → explicit playback selection. Check supported desktop sizes, sticky
offsets, keyboard/reduced-motion behavior, cancel/dirty-edit preservation and
background completion without focus theft. Mock providers, not authority facts.

Use `uv run --locked --no-sync python scripts/verify.py quick` and exact `focused`
selectors during iteration. Review `module --show` for the deduplicated affected
owners, including creative production, media lifecycle, playback, project lifecycle
and affected shared API/generation/provider/presentation dependencies; update
`scripts/testing/module-ownership.json` for new tests. Run chosen contract/browser
depths, not a disguised full suite after each edit. This cross-layer persistence,
admission and dispatch change requires one stable final `verify.py full` gate.
Reuse unchanged evidence after diagnosed focused corrections under AGENTS rules;
record composite qualification honestly. Hosted CI, live technical smoke and
human creative acceptance are separate claims. Documentation-only plan edits
need diff/link/command consistency checks, not a test-suite run.

## Consolidated execution permissions for approval

The owner's implementation approval authorizes the following bounded work through
delivery without milestone reapproval:

- Source, typed schema/current-format changes, concise ADRs, tests, checked assets
  and workflow documentation in Plotloom; ordinary in-scope root-cause corrections,
  bounded subagent review, local qualification, normal commit/push to `main`
  without force and any repository-required unfiltered CI dispatch.
- Same-installation activation/restart using existing credentials/settings after
  fresh native worker/validator/queue and dispatch checks establish safe idleness.
  Do not cancel owner activity to manufacture idleness. If unsafe, finish source
  delivery and report activation pending; do not interrupt or restart blindly.
- The owner's standing test-data policy: permanently remove exactly identified
  incompatible development projects, without backup or recovery, after validating
  targets and safe quiescence. No retention-only migrations/compatibility layer.
  Compatible projects can remain. Do not wipe unrelated projects, credentials or
  application-private accounting, or falsify unsettled remote/UNKNOWN outcomes.
  Report exact material deletions and that they are unrecoverable.
- Isolated development qualification with fakes first; at most one complete
  42-shot assistant directions-draft qualification plus one corrective definite-
  failure attempt within existing configured budgets. At most two H3 clip
  submissions totaling ten requested source seconds, using currently qualified
  settings and existing backend/account, for end-to-end technical smoke. No
  uncertain resubmission, provider fallback or extra paid retries. Record actual
  use; these bounded calls are covered by implementation approval. Live smoke also
  needs a still-current, already owner-reviewed fixture; do not synthesize human
  approval facts. If unavailable, finish provider-fake/transport qualification and
  disclose the live-smoke gap instead of blocking delivery or inventing consent.
- Read-only live inspection of the owner's project. Do not approve its creative
  materials/videos or launch its 42-shot generation. Actual story generation is a
  separate explicit UI Start action over the creator-reviewed manifest and caps.
- Recover an installation failure using a known compatible build when safe.
  Check reader/schema compatibility before rollback; use the scoped incompatible-
  test-data policy if necessary, never forged receipts or hidden backward readers.

New providers/accounts, secrets/access changes, higher spend/caps, unsafe restarts,
unsupported timing/media transformations, broad worker-platform redesign or a
material authority/scope pivot require new direction. Do not remove product
snapshot features just because incompatible test data need no backup. No finished
movie export, branch flattening, automatic creative acceptance or general Python
optimization is included.

## Completion standard

Done means the qualified, published and safely activated feature can run a
missing-only batch durably, with exact reviewed prompts and bounded dispatch,
then await one explicit atomic final review before new playback selections.
Both image and video completion/approval flows reveal the useful next action
without disrupting unrelated work. Report actual latency measurements, technical
verification, activation and any gaps separately. The owner's generated story and
creative acceptance are not implementation completion requirements.

## Approved activation follow-up: process-incarnation quiescence

Owner approval, 2026-10-18: implement a narrowly reviewed PID-reuse fix for the
native deletion guard, then complete safe activation. The published feature is
not yet installed: a completed worker's numeric PID/group was reused by an
unrelated CUA process, and the existing guard intentionally requires numeric
absence. No supported terminal-worker recovery path resolves that condition.

Define a named positive quiescence proof: numeric PID/group absence, or conclusive
retirement of the exact recorded isolated group incarnation. Validate platform
semantics and reliable observations before admitting the latter; completed state,
command changes, identity mismatch or leader disappearance alone are insufficient.
Ambiguous/unsupported probes remain blocking. Record the durable contract in an
ADR and independently review it before publication or live use. Cover surviving
descendants, real reuse versus exec/command changes, birth ambiguity, permissions,
sampling races, spawn/publication fencing, validators and stale previews.

Preserve all retained attempt facts, receipts and UNKNOWN capacity; do not
retroactively fabricate exit witnesses, clear identity fields, bypass revocation,
send nonzero signals to unrelated processes or reset CUA. Use the same source
writer and affected verification, then manager review before the existing scoped
deletion/activation continuation. No live generation or creative approval is added.

The [bounded investigation](../verification/2026-10-18-process-incarnation-proof-investigation.md)
found no conclusive retrospective proof for the retained identity. The guard is
unchanged and activation remains blocked; no future identity framework was added.
Separately, the required hosted run failed and needs serialized remediation.
