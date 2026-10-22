# Creator completion loop: native creation, selective revision and timing

Status: implementation approved and underway, 2026-10-22. The owner approved
the bounded implementation, real UI E2E and activation via Relay Direct.
Planning baseline: retained R `1edae591`, installed executable P
`6b1cf196`. This is one new bounded milestone, not a reopening of completed
October 10 lifecycle acceptance or the three October 22 example projects.

Authorized capacity extension: the native journey exposed two historical UNKNOWN
image holds on deleted, permanently revoked projects, exhausting local capacity.
The owner explicitly approved exact operator-invoked local-slot retirement with
fresh positive process/home absence and an atomic immutable receipt; UNKNOWN,
spending reservations and original evidence remain unchanged. Read-only readiness
and a narrow pre-text launch refusal expose this historical full-lane condition;
ordinary busy scheduling is unchanged. See [ADR 0174](../adr/0174-bounded-fair-codex-exec-pool.md)
and the [operator guide](../../services/creator_workbench/codex-exec-capacity-recovery.md).
The current native fixture's eight text stages were adopted under the old source;
its run was explicitly cancelled and native continuation became eligible. Quiet
activation and same-project Continue must freeze fresh source authority and reuse
the completed text. Live recovery, exact successor QA grant and E2E are pending.

## Outcome and scope

One creator can create, revise and finish a small story through the normal UI:

`saved Brief → native text/images → material review → batch video → selective
replacement → final review → ending playback → reopen`

Deliver three connected improvements: prove the current native image path,
surface the existing rejected-take replacement contract in the batch review,
and show truthful elapsed time/current status. Retain existing explicit review
and Start decisions. Routine recovery must not require scripts, raw IDs, a
reviewer-name form, database edits or switching to an operator-only API.

The first fixture is a fresh, clearly named disposable QA project, with no
people/dialogue, zero choices, one ending and two footage-bearing shots. Target
the smallest feasible opening/ending structure with one shot per scene; confirm
the actual Brief/topology/creative contracts before launch. Authored duration
must be valid for the selected H3 profile; six to ten seconds total is an
experimental size, not a product pacing requirement. Native generation owns all
required references and first frames. The two-shot target does not promise that
the complete reference inventory contains only two images.

The representative character/branching story and uncoached colleague pilot are
subsequent milestones. This step does not expand providers, introduce an editor
timeline, revise story structure after production, add voice casting, export,
multi-user roles, a telemetry platform or broad Python optimization. Existing
window adjustment remains supported, but building a new window editor is not
part of progress-timing visibility.

## Evidence and root causes

- [October 22 examples](../verification/2026-10-22-rejected-batch-take-replacement.md)
  prove imported ImageGen originals → H3 → delegated QA → actual ending playback.
  They explicitly do not establish native automatic-image-job E2E. The next
  proof must originate in the native Brief/image workflow, without imported
  replacement frames or API-created accepted canonical stages.
- [ADR 0204](../adr/0204-explicit-rejected-batch-take-replacement.md) and the live
  cinematic successor prove selective replacement at the native API. The batch
  gallery currently links out to manual handling and has no replacement action.
  This gap belongs in the creator orchestration/presentation layer; keep the
  native rejection, exact predecessor, reuse and fresh endorsement owners.
- Normal browser requests omit QA attribution. Native automatic material handoff
  currently constructs unnamed-human attribution and its receipts accept only
  that actor. The existing closed QA scopes bind exact projects, storyboards,
  material hashes and original runtime incarnations. A new native fixture
  cannot inherit an old grant, and an agent click cannot impersonate a creator.
  A narrow typed material-handoff/browser-context extension is a prerequisite
  for truthful agent-operated UI acceptance, not a reason to weaken admission.
- Run/attempt/job timestamps exist, but generic `updated_at` is changed by
  controller claims, evidence reconciliation and retrieval failures. It cannot
  be advertised as generation progress. Current activity/batch UI primarily
  exposes state/counts. Useful basic timing can be a read projection of existing
  immutable facts, without a new database clock or provider poller.

## Proposed creator experience

### Create and finish

Use the visible Brief controls and existing automatic preparation action. Show
the current text/image task, progress counts and timing while it runs. Completed
materials open the existing consolidated gallery; normal creators confirm once.
Prepare the video batch, review its directions, explicitly Start, review the
returned clips/native audio, and confirm the complete pack for story playback.

Opening a report, status polling, navigation and elapsed-time ticks never adopt,
retry, approve, resume or dispatch anything. Preserve the implemented completion
navigation and dirty-draft protection rather than introducing another wizard.

### Revise selected takes

1. In the batch gallery, expose a per-take `重新制作这个镜头…` action with a
   concise reason/change input. The confirmation explains that this take will
   be retained as rejected and good takes remain available. It creates no new
   provider submission. Use the native job review/selection-revision checks.
2. Present the exact rejected shot set and offer `仅重做这些镜头`. Use existing
   control to cancel new dispatch for the exact predecessor, then create its
   successor through `replace-rejected` using the returned current revision.
   Already-cancelled exact predecessors do not need another cancellation.
3. The successor shows fresh work versus reused takes, retains the prior settings
   unless explicitly changed, and uses existing direction drafting/editing.
   New takes require fresh English endorsement and explicit Start; do not copy
   old endorsement into a new generation request.
4. On completion, return to the same complete-pack gallery. Reused takes remain
   part of the final review. Confirm current windows/media once, then play the
   story to its actual ending and reopen it with the selections intact.

Rejection, cancellation and successor creation are separate persisted native
operations, not one fictitious transaction. If the chain stops, the UI names the
completed action and the exact remaining action. A lost acknowledgement first
reads the retained batch/jobs; it must not replay generation or silently select
a new predecessor. A content/revision change requires a new current review.
UNKNOWN or still-publishing work stays blocked with its specific explanation.
Repeated clicks are disabled while pending. A superseded rejected take remains
readable and immutable under the current contract.

The first live acceptance performs this revision before whole-pack approval,
matching current replacement eligibility. Replacing already-selected clips or
changing the storyboard is not silently added to this milestone.

### Timing and status

Keep timing deliberately small and precise:

- Run age: `距启动已过 …（含排队、暂停和等待）`, from the native run creation fact.
- Batch age: `清单创建后 …`, from batch creation; do not call time spent drafting
  directions or waiting for Start video-generation time.
- Existing current phase and completed/queued/failed counts remain primary.
- Where useful, show one named durable milestone, such as `上一项素材已采用` or
  `播放片段已就绪`, with its actual immutable decision/proposal/receipt time.
  Scope milestones to the current run/batch; identify reused historical output
  separately so it cannot masquerade as new completion in a successor.
- A failed status read displays that the status is unverified and when it was
  last successfully checked. An increasing clock does not claim worker liveness.

Add a small response-only timing projection to existing GET views. Use server
observation time plus a monotonic browser interval for display, retain the
existing refresh cadence, and recover timestamps after reload. Do not create
per-second writes or extra provider polling. Missing historical timestamps stay
unknown. Terminal views show recorded completion/milestones when available;
otherwise show a labelled creation date, not a forever-growing completion time.

No ETA, historical percentile, GPU-start time, active compute duration or exact
phase duration is promised. Those require evidence not presently retained by all
owners. Capture observed stage/action times from this small journey for the next
performance decision, without building a benchmarking system. Do not sum
overlapping task ages into a claimed total execution duration.

## Truthful delegated QA prerequisite

Ordinary creators keep their existing unnamed-creator confirmations. Agent UI
testing uses the already delegated authority with an explicit visible QA context;
the user must never be recorded as having personally reviewed agent actions.

1. Create the fresh fixture and generate its native materials first, stopping at
   the real material-review boundary. Read exact current board, run/bundle,
   reference decisions and original frame identities/hashes.
2. Add the exact fixture's immutable source grant under ADR 0198 and bind it once
   through the existing trusted operator path in the actual original runtime.
   This is test setup, not a creator step. Preserve all existing grants. Do not
   add a public enrollment API, generic wildcard project grant or title-based
   privilege. Current source grants cannot be known before native output exists.
   The native-material scope additionally freezes the exact run ID, complete
   material bundle/closure hash and endorsed reference identities/original hashes,
   alongside storyboard/frame/profile authority. Use a distinct narrow scope
   shape if needed; do not expand old manual-image grants or use optional fields
   as wildcard authority. The grant covers that bundle, not arbitrary future
   material revisions that merely pass current-request validation. Current command
   revisions are still checked freshly; a controller claim is not material identity.
3. Extend the native atomic material-handoff actor/receipt contract to carry
   typed agent QA, including exact complete bundle/reference/frame endorsement.
   Carry that actor through approval, intent, keyframe/reference decisions and
   currentness/portable readers. Reuse existing write owners; do not fake a
   human handoff or perform individual API selections in place of the UI flow.
4. Expose only a server-verified eligible QA context for this granted original
   project/runtime. Browser QA use must be explicit and visibly labelled. A
   project name, URL, arbitrary reviewer text or client-supplied scope ID cannot
   grant authority. Every write still independently checks the grant and actor.
5. Pass typed attribution through material handoff, rejection, successor setup,
   English endorsement and final AV confirmation. QA observations/evidence use
   the existing inspection contract. Missing, revoked, stale, copied/restored or
   mismatched contexts refuse without falling back to unnamed-human approval.

The implementer owns the smallest context transport/component design after
examining existing session/read boundaries. Its semantics and anti-fallback tests
are fixed by this plan; no global actor toggle or automatic creative approval is
authorized. Amend ADR 0198 for this narrow scope and ADR 0204 for the UI path;
reuse ADR 0162/whole-pack material rules for atomic handoff.

Actual observation remains necessary. Review original frames and actual playback
windows; retain native audio. If listening is unavailable, record the actual
technical audio inspection and lack of listening explicitly. Functional QA
completion must not be presented as perceptual sound-quality or personal creator
acceptance. This first milestone is a technical creator-flow demonstration; the
later representative-story milestone includes listening-based quality review.

## Delivery order and acceptance

One source writer in R; root owns live execution and activation. Use bounded
independent read-only review of the stable candidate, not concurrent writers.

1. **Preflight and first native material attempt.** Establish the installed
   source, provider/bridge readiness, smallest valid fixture, actor prerequisites
   and original runtime. Create/start through UI. Observe actual native text and
   ImageGen receipt/ingestion through complete materials before broad software
   qualification. A source fix required to reach this point gets focused checks
   and the same small journey; do not substitute manual imported images.
2. **Implement the three bounded deltas.** Typed QA material/UI context, batch
   selective replacement and read-only timing. Add the exact material grant only
   after output identities exist. Split cohesive components; reuse controllers,
   native operations and polling. Fix demonstrated blockers in these paths with
   a root-cause note. Unrelated framework work remains separate.
3. **Exercise the real UI loop.** After focused safety checks and a quiet,
   preservation-checked activation, inspect/confirm materials, generate two H3
   takes, request one honestly described revision, produce its replacement,
   confirm the pack and play to the ending. If both initial takes are technically
   sound, record the desired creative variation as a QA revision; do not invent
   a validation failure. Refresh during a known safe boundary, then close/reopen
   the completed project. No scripted product writes fill a claimed UI step.
4. **Stabilize and qualify once.** Review the stable diff and real journey,
   repair concrete findings with focused checks, then perform the applicable
   final local gate and exact-package installation/smoke. Reuse unchanged
   evidence; retain failed attempts as failed. Verify any final activation and
   artifact identity with the same small playback/readback, without automatically
   repeating paid generation. Update the current creator instructions and this
   plan's outcome. Commit the coherent local checkpoint; publication is separate.

The same project must demonstrate native image provenance, two current selected
windows, ending playback and reopen. Its one replacement must add exactly one
fresh dispatched job, retain the rejected original/history and preserve the good
sibling's identity/bytes. UI receipts must retain truthful QA attribution and
current revisions. Read-only timing/refresh must cause zero dispatch or approval
writes. Root owns settlement and reports any unresolved work precisely.

For interruption/lost-ack/UNKNOWN cases, use deterministic existing fixture
tests first. Do not manufacture a live uncertain dispatch or terminate a worker
merely to tick a test box. A supported reload or idle restart can establish the
live recovery observation; it must not become authority to replay provider work.

## Implementation and verification map

| Surface | Primary owners and relevant checks |
| --- | --- |
| Native creation/material review | `api/project_folder_autopilot.py`, `autopilot_handoff_contracts.py`, `persistence/project/autopilot_handoff.py`, handoff intent/binding owners, `features/autopilot/`; existing handoff/bulk-material/native-exec tests |
| QA context and durable attribution | `delegated_qa*.py`, `project_storage/delegated_qa_{grants,validation}.py`, `project_storage/handoff_validation.py`, shared frontend attribution; `test_delegated_qa.py`, handoff and browser attribution cases |
| Selective replacement | `features/video-batch/{api,contracts,VideoBatchPanel,VideoBatchReview}`, a cohesive replacement component, existing video review transport; `test_video_batch_replacement.py`, batch review/recovery and `frontend/e2e/video-batch.spec.ts` |
| Timing | `persistence/project/autopilot_activity.py`, `autopilot_contracts.py`, `persistence/project/video_batches.py`, batch view/service; activity/progress frontend components; state-owner and deterministic-clock tests |
| Current guidance | This plan and roadmap entrypoint; creator manual sections touched by material, replacement and timing UI; amend existing ADRs where their contracts change |

Focused acceptance covers ordinary creator and scoped QA actors, stale bundle
and selection revisions, forged/missing attribution, original/copy/restore
boundaries, cancel-success/successor-failure recovery, lost acknowledgements,
repeat replacement and untouched sibling/history. Reuse existing native UNKNOWN,
budget and dispatch tests rather than a second framework.

Explicit browser cases include rejection-saved/cancellation-failed or lost,
and successor-created/response-lost followed by refresh. Read back the persisted
state and continue the exact remaining action; never replay rejection against
superseded immutable history or accidentally cancel the newly created successor.

Timing regressions cover controller-claim reassignment, evidence-only updates,
unchanged polling and retrieval failure: none may appear as new generation
progress. Include clock skew, reload, project switch, paused/waiting/unknown,
terminal rendering and reused predecessor media. GETs remain read-only.

Use focused → quick/affected browser checks first, deterministic assets and
desktop pixels for changed UI. Typed handoff/persistence changes require final
local release qualification once stable under AGENTS.md. Check exact package
installation and current project readers. No new full run after every checkpoint;
no new test tier or qualification platform.

## Execution permissions and preservation

Implementation is approved for the complete bounded sequence above, including
necessary focused fixes, exact QA fixture/grant setup, local verification,
actual generation/review, quiet activation and final readback, without new
routine checkpoint approvals. One retained-checkout source writer owns code;
the manager owns the original runtime, generation, UI acceptance and activation.

Existing standing authority covers Codex ImageGen and the owner's H3 gateway,
truthful QA decisions on explicitly scoped disposable projects, and prospective
unlimited aggregate budgets unless the owner supplies a finite cap. Use small
experiments; the two-shot/one-replacement design is a test size, not a new budget
limit. Existing frozen finite grants, provider constraints and uncertain-dispatch
rules remain unchanged. Use the configured providers/profile, no paid fallback.

Preserve the three finished example projects, their media, credentials/settings,
host accounting and old UNKNOWN evidence. No old-project deletion, automatic
backups, migration adapter or replay is implied. Keep the new QA project unless
its exact cleanup is separately authorized. Do not modify active pinned inputs
or activate while task ownership/quiescence is uncertain. Use supported
stop/switch/bridge/start or isolated deployment paths and read-only preservation
comparisons. Select the smallest compatible rollback if startup fails; never
run an old schema reader on newly incompatible valued data or erase data to
manufacture recovery.

GitHub Actions/CI, workflow preparation/publication and pushes that trigger CI
remain off pending a new explicit owner request. Hosted CI is not an acceptance
requirement. No public release, new provider, broader story generation or
unrequested authentication/hosting redesign is included.

## Completion report

Report the real creator outcome first: native materials, selective revision,
final playback/reopen, remaining interventions and truthful audio limitations.
Link the one journey's evidence and distinguish UI operations, trusted QA setup,
read-only diagnostics and synthetic failure tests. Record observed waiting versus
operator effort where measured; do not infer unavailable timings. State installed
and qualified revisions, reused/new verification and any concrete remaining gap.
Do not call API-only setup, an imported-image substitute, test totals or service
health the completed native UI journey.

Planning review: independent product and engineering reads found no blocking
scope contradiction. The exact native-bundle grant and the two additional
lost-response browser boundaries above incorporate the engineering clarifications.
Documentation/whitespace checks only; no product implementation or test run.
