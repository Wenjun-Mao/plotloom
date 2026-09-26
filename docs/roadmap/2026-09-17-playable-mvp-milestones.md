# Playable MVP milestones — Shuohao-first delivery

Revision 4 — **Approved direction and checkpoint roadmap**, 2026-09-17.
The user approved the architecture and requested this full roadmap. This is the
single current tracker; bounded implementation assignments remain director-owned.
[ADR 0057](../adr/0057-shuohao-first-creative-workflow.md) records the ownership
decision. [Revision 3 history](archive/superseded/2026-09-17-playable-mvp-milestones-r3-history.md) preserves
earlier scope and evidence, not the current assignment queue.

## Now / Next / Later · 2026-09-25

- **Now:** The director approved the pacing-first integration recommendation
  below and one bounded longer-shot trial. The director confirmed both lines
  and coherent voice/pose in the earlier two-shot
  assembly, but rejected the naturalness of the six-second cut. The six-second
  values came from agent-authored test storyboard cuts, not a user requirement.
  The first gateway quality/duration integration slice and frozen per-candidate
  F5 editorial timing control are implemented for review. The
  [single longer opening trial](../verification/2026-09-25-u4-h3-longer-opening-trial.md)
  ingested a technically valid, unselected 12.25-second quality-8 original
  from one 12-second continuous cut; sampled frames show a material concern
  that the fuse enters the upper socket despite the authored no-choice action.
  The director subsequently reported no intrinsic video defects and confirmed
  the apparent insertion. After the intended action was explained, they agreed
  to separate positive quality feedback from the action-fidelity mismatch and
  close the trial without another generation. This is not creative acceptance
  or general quality-8 qualification.
  All takes and segments remain unselected. Preserve the
  [adjacent-shot evidence](../verification/2026-09-24-u4-h3-adjacent-shot.md).
- **Next (approved):** Prioritize a director-operated end-to-end creator
  walkthrough, not an extended series of isolated media experiments. Use a small
  persistent story and the real UI from source through media review to playback.
  Do not require all 27 lighthouse cuts to be produced first.
- **Later:** Let observed walkthrough friction determine the next product
  priorities. H3/audio research stays with the director's specialist; broad media
  qualification, other lighthouse route cuts and optional polish remain deferred.

### Timing/continuity integration checkpoint (completed planning basis)

Deliver a source-backed design, not another generation or a trimming workaround:

1. Bind the current [gateway guide](../operations/minimax-h3-gateway-client-guide.md)
   to Plotloom's adapter: the gateway documents 5–15 integer seconds and optional
   ending-image input, while `H3_QUALIFIED_DURATION_FRAMES` admits only 5/8 and
   `transport.py` currently sends only `image`. Requested seconds are not exact
   measured playback duration. Resolve frame-grid details with the specialist
   if needed; do not invent a frame-count catalogue.
2. Specify the editable timing authority and invalidation path before code:
   `production_bridge.py` maps source cut seconds to canonical milliseconds;
   `media_video_segments.py` currently restricts its reviewed path to 6/8-second
   source shots and an 8-second request. Decide how an explicitly reviewed
   timing or shot-structure revision reaches those owners without weakening
   source provenance, approval, selection, or currentness checks. A generation
   covering multiple shots needs an explicit mapping, not duplicate whole-take
   selections for each shot.
3. Amend ADR 0082 for the proposed timing workflow and specify duration and
   optional end-frame integration, including immutable image provenance,
   full-prompt review, dispatch safety and measured output validation. Trimming
   remains optional editorial work, not the default goal. End-frame conditioning
   is guidance, not a guarantee of exact continuity.
4. Define tests for supported/unsupported durations, endpoint-image changes,
   stale source/approval, measured timing and audio preservation; then define a
   1440/1920 creator walkthrough that makes pacing and boundaries understandable.

The original planning checkpoint stopped at an implementation brief; the director
has now approved the recommendation below. Its implementation must resolve the
named gateway facts before depending on them. Success means the next trial is
chosen for narrative pacing and continuity, not an arbitrary six-second test
value. Existing exact-timing safety remains in force until explicitly revised;
approval to implement/generate does not select or creatively accept media.

The dated checkpoint ledger below preserves earlier phase-specific exclusions,
model choices and push instructions as history. This current assignment and its
explicit stop points govern the bounded experiment.

### Implementation brief for review: pacing-first H3 integration

**Status:** Director-approved direction, 2026-09-25. The first gateway
quality/duration slice is implemented for review; later integration and the
new live trial have not started. Retain the heading anchor for existing design links.
The director reports random shaking in qualities 1/2/3 and substantially more
stable output in quality 8. This is useful director evidence, not a controlled
benchmark or a guarantee. Quality 1 remains useful for development; propose
quality 8 as the initial production-review choice, always visibly frozen.

**Recommended delivery order:**

**First-slice checkpoint (2026-09-25):** Plotloom now exposes explicit quality
1 development and quality 8 production-review choices, independent of six
resolutions, with a versioned new-job catalog. Existing frozen quality-1 IDs
retain their old meaning. The strict 5–15 integer-second request maps to the
gateway's exact 24 fps `17k+5` frame grid and is frozen and checked through
adapter, transport, job response and output validation. The prompt-review
surface shows chosen quality, request, expected frames, seed and start-image
hash; changed controls invalidate a prepared review. Request capacity is not
playback eligibility: the current reviewed segment/source-timing restrictions
remain. No end-image input, source retiming, general playback-duration support,
provider call or creative acceptance is part of this checkpoint.

Verification at this checkpoint: 752 backend tests, 217 frontend unit tests,
frontend typecheck and deterministic static build passed. A focused offline
browser check passed at 1440 and 1920 widths for default quality 8, switching
to quality 1, 15-second/362-frame display and blocked six-second-source
preparation. The retained browser source-to-selection/restart spec still uses
an older folded-control and profile contract and is not claimed as a passing
journey; refreshing and rehearsing that journey belongs to the later creator
E2E milestone. This is technical verification, not director audiovisual review.

1. **Gateway capability integration.** Update `video_backends/minimax_h3/adapter.py`
   and `transport.py`, their public profile descriptors, frozen-job contract and
   workbench controls. Replace hard-coded quality 1 with explicit reviewed quality
   profiles (first slice: 1 and 8; do not add 2/3 just because the gateway accepts
   them). Keep resolution separate from quality. Version new profile/catalog
   semantics; never relabel existing quality-1 jobs. Expose development/production
   intent as a visible initial choice, not an automatic quality fallback. Bind
   quality, duration, seed and both image hashes into prompt review and the job.
   The specialist's [time-estimate reference](../operations/minimax-h3-generation-time-estimates.md)
   now states upward snapping to the `17k + 5` frame grid (5→124, 8→192,
   15→362). Verify this against gateway contract evidence and obtain the quality-8
   descriptor before implementation. Validate output against the frozen request, not a loose
   5–15-second range. Keep uncertain dispatch non-retryable without reconciliation.
2. **Optional reviewed end frame.** Add a shot-owned managed-asset decision for
   the ending image, independent of the starting keyframe. Carry its bytes/hash,
   provenance, reviewed aspect treatment and source revision through preparation,
   prompt rendering, transport and currentness. A changed end image invalidates
   prepared review; a changed live decision makes old jobs stale rather than
   changing their frozen bytes. Use the official first/last-frame prompt mode,
   not a second image appended to the current single-image compiler. Verify that
   mode with the specialist/official guide before coding it. No automatic linking
   of one clip's last frame to another clip or assertion that the output matches
   the end image exactly.
3. **Explicit editorial revision, not forced trimming.** Keep gateway request,
   measured take and approved story timing distinct. For this first story trial,
   recommend revising the F5 opening segment into one longer shot covering both
   existing lines and actions, then using the existing reviewed bridge path on
   an isolated copy with empty canonical heads. Preserve the original project
   and trial assets. Do not retrofit the installed bridge or introduce a second
   timing override. Review the revised shot's pacing, coverage and source binding
   before confirming canon and obtaining fresh approval/keyframe prerequisites.
   The director approved trying this structure; the new source revision still
   requires the normal review and acceptance flow, not an implicit installed edit.
   If two angles are preferred, retain two shots and plan their boundary explicitly;
   a single generated take mapped across multiple canonical shots is deferred.
4. **Generalize reviewed playback only after ownership is settled.** Replace the
   6/8-source-and-8-request special case in `media_video.py` and
   `media_video_segments.py` with frame-representable, explicitly authored timing
   covered by the measured take. Keep exact-window/audio verification, optional
   annotations, CAS and explicit selection. Do not automatically shorten a useful
   take to an old test value. If no good window matches the approved timing,
   return to an explicit editorial revision or reject the take; never silently
   change the timeline. Arbitrary frame-rational story durations and accepting a
   measured whole take as new timing require a separate design if the current
   integer-millisecond representation cannot express them exactly.

**Implementation checkpoint (2026-09-25):** The optional reviewed end-frame
decision, frozen first/last-image prompt and transport, hash/currentness guards,
and frame-representable playback windows are implemented. Offline storage and
transport tests plus an isolated shipped-static browser journey verify a reviewed
end image and a 7.5-second/180-frame selected derivative from an eight-second
take at 1440/1920. This does not install a revised F5 shot, qualify live H3
audio/video, start the quality-8 longer-take trial, or complete the director's
retained hands-on creator E2E; those remain the next review/trial milestones.

**Acceptance:** Adapter/transport tests cover quality 1/8, wrong returned quality,
unsupported duration and exact frame mapping, absent/present end image and changed
image hashes. Storage tests cover stale F5/Brief/approval/reference, rollback and
selection revision races. Segment tests cover longer frame-representable windows,
insufficient output, clipped/invalid audio and unchanged original bytes. Browser
tests at 1440/1920 must distinguish draft versus production quality, request versus
measured/story duration, optional end frame, and unselected versus playable media.
No test passing substitutes for director audiovisual review.

**Trial checkpoint after implementation:** Review the full prompt, images, quality
8 setting and proposed shot structure before one bounded longer-take trial. Choose
the nominal duration for the performed exchange, within the supported envelope;
do not prescribe six seconds or the maximum fifteen without a pacing reason.
Assess both complete lines, shaking, action fidelity, voice/pose and start/end
sound. A quality-8 longer take changes multiple variables and is not evidence that
quality alone caused improvement. Stop and reassess a failed or uncertain call;
do not auto-select, auto-retry, generate other route cuts or add TTS.

### Generation scheduling and next director walkthrough

Use the specialist-maintained [generation-time estimates](../operations/minimax-h3-generation-time-estimates.md)
as the single scheduling reference; do not duplicate its full table or turn it
into a live countdown. Quality 8 at 960×544 is estimated at 16.5 minutes for a
12-second request and 22.5 minutes for 15 seconds. Reserve at least 1.5× those
times, plus queue, transfer and review. These horizontal/long-duration cells are
estimates, not same-combination measurements. End-frame conditioning has no
independent timing matrix. H3 and Qwen share the serial channel. Keep progress
honest and recoverable across page reload; unknown dispatch must not trigger
another request simply because an estimate elapsed. For the later quality-8
trial, prefer the existing job completion/reporting mechanism when available.
Otherwise use coarse checks based on the estimate, keep queue time separate
from generation time, and avoid repeated model polling while expected running.
An elapsed estimate never authorizes an automatic retry after uncertain
dispatch; this preference is not a fixed ETA or a new monitor.

**Next milestone: hands-on creator E2E.** The director explicitly wants personal
use and feedback to guide priorities after the longer-shot trial. Provide one
small, retained, editable project with a complete short route, sized for practical
generation/review rather than reusing the entire 27-cut test as a prerequisite.
The director should be able to create or edit the source, review the outline and
characters/art, accept the script/storyboard, prepare references and keyframes,
request video, inspect/select media, and play the resulting route through the
normal UI. A playback-only or read-only fixture is not this deliverable.

Before inviting the director, rehearse the same journey at 1440/1920 and record
any agent-only operations or missing handoffs as actual blockers. Do not hide
manual database setup or terminal-only mutations behind an E2E claim. Provide
one stable entry URL, retained state, clear next actions and understandable wait,
failure and retry behavior. Preserve existing user-valued projects and media;
do not install login-startup services. Reuse valid reviewed assets where useful,
but disclose prepopulated steps rather than claiming the user performed them.

Track only: integration ready → longer-shot review → UI journey rehearsed →
director walkthrough → feedback-ranked fixes. After the trial, scope generation
count and minimal story for this walkthrough before further media dispatch; this
milestone is not permission for an unbounded production batch. Separate blocking
usability gaps from optional polish and H3 model research. Success is the director
completing the workflow and giving actionable feedback, not another test-count
or isolated-clip receipt. No additional prototype subsystem or broad refactor is
required merely to prepare the walkthrough.

### Active follow-on: editable creator walkthrough preparation

The director agreed to close the quality-8 trial and proceed. Next deliverable:
one retained, editable small-story project, one stable entry URL, and a short
ordered walkthrough. Do not present the lighthouse trial as that deliverable.

- [x] Preserve the longer take and record quality feedback separately from its
  action-fidelity mismatch; no new generation or selection.
- [ ] Audit the actual UI path from project/source creation through text review,
  canonical confirmation, media prerequisites, generation, selection and playback.
  Source-outline, script and storyboard panels currently expose explicit copied
  specialist handoffs and manual delivery refresh. Record these as visible manual
  steps, not automatic execution; do not silently add a new dispatch system.
- [ ] Choose the smallest story supported by the existing source/graph/timing
  contracts and state its shot count, proposed media-call budget and quality-8
  waiting expectations before dispatching any new media.
- [ ] Rehearse at 1440/1920 using supported APIs/UI, record any terminal-only
  prerequisite or missing handoff, and fix demonstrated in-scope blockers.
  Keep prepopulated demonstration data distinct from actions the director will do.
- [ ] Hand off the editable project with clear starting state, next action,
  wait/recovery behavior and a list of still-manual specialist steps. Preserve all
  existing projects and avoid login-startup services.
- [ ] Let director feedback rank subsequent product work; leave H3/audio model
  research with the specialist and do not restart the closed clip experiment.

## Dated checkpoint ledger

The attended walkthrough has delivered bounded presentation slices: the U2
route-focused reader, the U3 Characters appearance workspace, and the F3B
environment/prop gallery plus explicit reference choice. Their technical and
bounded usability records live in the
[usability review plan](2026-09-18-creator-workflow-usability.md); none is
creative/media approval, a production consumer, or a whole-workflow redesign.

The U0/U1 navigation and workflow assessment is complete historical planning;
the bounded U1a implementation is accepted at `94cf165`. The retained U4
lighthouse walkthrough received connected, read-only usability acceptance at
`a869e7c`, recorded in its verification receipt. Neither acceptance authorizes
provider or generation work. At that checkpoint, the next F5-to-production/F7
activity was the documented canonical bridge: a reviewable proposal and explicit
atomic install, with no implied approval, reference selection, or provider
dispatch. The isolated-copy result is recorded below.

**Isolated U4 production-readiness diagnosis (2026-09-23).** The
[read-only walkthrough](../verification/2026-09-23-u4-production-readiness-walkthrough.md)
confirms a current, installed 27-shot bridge in the isolated copy, but no
storyboard Approval, selected references/keyframes, media jobs or playable
routes. The accepted bridge gives no shot-specific handoff into the canonical
workbench. Twenty-six exact 6-second F5 cuts conflict with H3's presently
qualified 5/8-second contract; no silent retiming or provider dispatch is
authorized. A bounded candidate next slice is a read-only, shot-specific
handoff and preparation-status display in the existing owners. Production
duration policy and F6/F7 quality/selection need separate decisions and proof.

**Bounded U4 shot handoff (technical implementation, 2026-09-23).** The
accepted/current bridge now links an installed cut to its exact canonical
Storyboard shot, whose existing media owner shows a read-only, source-bound
preparation summary. The [verification receipt](../verification/2026-09-23-u4-shot-handoff-readiness.md)
separates technical checks from product acceptance. This closes the missing
navigation/status-display slice only. It does not approve Storyboard or media,
select references/keyframes, generate assets, resolve exact-duration policy,
or establish F6/F7 readiness.

**Production timing policy — completed design step (2026-09-23).**
[ADR 0082](../adr/0082-proposed-production-playback-timing.md) separates
authored shot time, qualified backend request, measured take and an explicitly
reviewed playback segment. Its recommended first implementation would preserve
the 26 six-second and one eight-second U4 cuts, and permit an eight-second H3
take to be considered for a six-second frame-exact window only after author
review of the final picture and sound. At this design checkpoint there was no
approval to change admission, trim/derive media, select a take, generate an
asset, or call a provider. The following bounded implementation approval now
settles the editorial choice; it still stops before live canary or U4
production. Exact source duration and present F6 audiovisual
non-qualification remain unchanged.

**Approved bounded reviewed-segment slice (2026-09-23; technically implemented;
director inspection pending).** The
director approved ADR 0082's recommended policy: preserve authored timing and
the original take; permit the creator to choose any contiguous exact-duration
frame window with its sound, preview the final local derivative, then explicitly
confirm its selection. Deliver trusted probe/derivation, durable lineage- and
hash-bound review/selection, a minimal Chinese creator UI, and one verified
selection projection for both ordered and branching playback. Evidence must
include deterministic labelled synthetic audiovisual fixtures, six/eight-second
and arbitrary in-point/audio-boundary cases, refusal/currentness/CAS/restart
tests, fresh frontend assets and browser inspection at 1440/1920. Retain a
usable isolated synthetic walkthrough with ownership/teardown recorded and
obtain independent stable-delta review. Stop at verified technical delivery
and director inspection: no real provider calls or U4 edit, no nominal-six
qualification, no promotion of rejected F6 clips, no source retiming, no
automatic selection, no asset deletion, no Batch C, and no push. Separate
creative/audiovisual product acceptance and any later live canary remain open.
The retained [technical receipt](../verification/2026-09-23-reviewed-playback-segment.md)
records the synthetic proof, browser walkthrough, independent review, and
remaining product-acceptance boundary. No live-media acceptance is implied.

**Director synthetic-usability follow-up (2026-09-23).** At local commit
`303b616`, the director reported that the reviewed-segment controls were
improved and personally confirmed a segment and played the synthetic exercise
on 8831. This accepts that bounded interaction, not synthetic content as real
media or a U4 creative decision. A subsequent separately authorized
[one-shot real U4 trial](../verification/2026-09-23-u4-real-shot-trial.md)
prepared one ImageGen first frame, made one H3 submission, and retained an
exact six-second derivative preview in an isolated copy. Its audiovisual
selection remains open for attended director audition; other route cuts have
no playable media.

**U4 H3 prompt correction (bounded implementation and one live C trial,
2026-09-24; partial director listening complete).** The director identified B's extra sentence as the canonical
Chinese action, so the stronger “only vocal utterance” comparison condition
is retired for new trials. The official [H3 single-image guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/.agents/skills/h3-prompt-writing/SKILL.md)
requires English rewritten directions while keeping dialogue and visible text
in their original language. A reviewed, source-bound direction package and
full-prompt preview now precede preparation; old A/B jobs and recordings stay
immutable. The [living playbook](../operations/h3-prompt-writing-playbook.md)
and [offline complete-prompt evidence](../verification/2026-09-24-h3-reviewed-directions-offline.md)
record current guidance and its proposed rendering. The separately authorized
[C trial](../verification/2026-09-24-u4-h3-reviewed-english-trial.md) matched
that prompt and ingested one original plus two unselected exact six-second
proposals in a fresh isolated copy. The director heard no extra spoken action
sentence and a clear, complete “一枚，只够一边。” in the original; the original
0–6-second proposal cuts the line after “一枚，”. The later 2–8-second proposal
preserves the complete speech, per the director's subsequent listening. Its
opening-action and sound boundaries, visual story fidelity, and whole-shot
acceptance remain open. No segment is selected and F6 cross-clip voice
consistency remains unqualified.

**Current bounded production experiment — 2026-09-24.** With the same reviewed
C prompt, first-frame PNG, profile, crop, eight-second/192-frame/24-fps
960×544 request and native audio, prepare one new, explicitly recorded seed
variation in a fresh isolated supported copy. Inspect its original and any
proposed segment with sound before considering one adjacent shot containing
the same speaker. That shot needs its own accepted source, reviewed first
frame, dialogue and prompt; preserve the source order and cut ownership.
At most one C variation and one adjacent H3 submission are in this slice,
without blind retries, automatic selection or creative acceptance. Stop for
director listening and review at each media boundary. The intended outcome is
a short real sequence, not production of all 27 route cuts.

**Simulated bridge wording follow-up (2026-09-22).** The director found the
simulated flow fairly clear and requested “确认投产提案” for the action,
“投产提案已确认” for the accepted status, and an explicit note that
confirmation creates scene/shot data without generating images or video.
This copy-only refinement also aligns conflict, unsaved-edit, and completion
messages. It records usability feedback only—not live-provider quality,
creative acceptance, or image/video acceptance.

**Bounded dramatic-intent follow-on (approved 2026-09-22).** Extend the
source-bound bridge proposal with an asynchronous, durable inference job over
the existing text profile/adapter seam. A versioned Chinese prompt may return
only suggested wording for the exact trusted objective/purpose target set;
trusted code binds coordinates, hashes, currentness, and a new review revision.
The author edits/saves/accepts the whole package before any empty-head canonical
installation. Preserve the original U4 source/Brief, nine-cut policy conflict,
and all existing media/selection gates. Verification uses a deterministic,
labelled fake text transport and production-shaped browser review; no live paid
or provider call, creative acceptance, media dispatch, new provider/credential
system, or broad scheduler rewrite is authorized. Stop at a stable verified
implementation and independent contract review; product acceptance is separate.

**Isolated live-intent trial (separately authorized 2026-09-22).** The
[retained-copy trial](../verification/2026-09-23-production-bridge-live-intent-trial.md)
used one real text completion, generated all 57 source-bound suggestions, and
saved 15 development-review edits while retaining model-original wording and
provenance. It did not change the original U4 project or accept creative work.
Canonical installation remains **unmet**: three nine-cut scenes conflict with
the original 2–4-shot Brief, and confirmation was not called. A changed-Brief
copy showed that current whole-chain invalidation stales F4/F5, so resolving
the policy/source-shape dependency needs a separate scoped decision; it was
not patched into this trial. No further provider or media dispatch is implied.

### U4 — coherent retained text-story walkthrough (approved 2026-09-22)

Build one durable, isolated development project through the existing F1–F5
source, specialist-handoff, review, and reader contracts. The director supplied
the Chinese lighthouse dilemma as the bounded premise and delegates routine
development choices, including expansion into original Chinese source text and
the minimal reusable cast, locations, and props, to the agent. The project must
retain an agent-authored-source declaration and agent-reviewed technical
acceptance; it must never be presented as human creative approval. Accept only
current source, outline, canonical one-choice/two-ending graph, cast, art,
script, and exact F5A binding through supported product APIs, with retained
package/delivery provenance, reproducible startup/teardown, restart discovery,
and an inspected production-shaped reader at 1440px and 1920px. Reuse the
existing text specialist and review owners; do not mock deliveries or repurpose
technical fixtures. Exclusions: providers and media generation, images/video,
production-shot installation, broad UI redesign, new backends, and product or
human creative acceptance. Stop when the director can inspect the retained
walkthrough. Local commits are authorized; do not push.

**Connected walkthrough acceptance (2026-09-22).** The director inspected the
retained project through the isolated reader and reported that it looked good.
This accepts the U4 scope of a coherent, connected, read-only F1–F5 walkthrough
and its route-focused usability only. It does not accept the authored creative
content as a final creative decision, install a canonical production storyboard
or media, qualify H3, prove playback, or change any F7 approval/selection
contract. The retained [U4 receipt](../verification/2026-09-22-u4-lighthouse-walkthrough.md)
and [F5-to-production canonical bridge design](../verification/2026-09-22-f5-to-production-canonical-bridge-design.md)
preserve the boundary and the next implementation scope.

## Outcomes and starting point

**M1 is achieved:** the user tried one small playable branching film successfully.
Preserve its working Play view, selected media and attributed reviews.

**M2:** a user brings a synopsis or source story, reviews/refines proposals, and
finishes a coherent playable branching film without developer intervention.
Finished means complete intended routes with selected audiovisual assets and a
usable viewing experience, not flawless first-generation media or cinema quality.
Manual specialist handoff is acceptable initially; dependence on developer edits,
database intervention or hidden prompt surgery is not M2 completion.

Existing project storage, review, image specialist, video alternatives, H3 dispatch
and branching playback are foundations to reuse, not rebuild. Earlier proposal
and storyboard engineering checks remain evidence of those implementations.
Old 3B never achieved quality acceptance and is **superseded as a delivery path**.
Custom two-phase generation integration and further qualification-only work on
the old authoring pipeline are paused. No code is deleted by this plan.

Shuohao trials establish only bounded screenplay feasibility:
[corrected Terra trial](../verification/2026-09-17-shuohao-screenplay-reuse-trial.md)
and [Qwen API trial](../verification/2026-09-17-shuohao-qwen-api-adaptation-trial.md).
Only novel-script has been exercised on one short ending; the other four stages
and the complete workflow are unqualified. Qwen needed review-guided revisions;
profiles and formats differed. These are not controlled superiority comparisons.

## Agreed architecture

- One Terra-first repo specialist invokes five Shuohao-derived stage skills:
  outline, characters, art, script and storyboard. Tasks may be disposable; the
  versioned skill and files carry the workflow. No five-service architecture.
- Select and pin an upstream revision deliberately. The reference checkout at
  `/Users/wjmao/projects/HU/reference-repos/shuohao-skills` is research material,
  not a portable runtime dependency. F0 chooses a reproducible project-local
  dependency strategy with upstream license/NOTICE; no global skill installation.
- Plotloom owns projects, interactive routing, source/accepted revisions, review,
  assets, production and playback. Specialists propose creative content; they do
  not silently replace accepted material.
- Reuse upstream JSON as stage data where suitable. Markdown/HTML are derived
  reports, never parallel editable authorities. Reuse report presentation before
  rebuilding equivalent UI; isolate its scripts from the host and keep edits
  bound to authoritative data. Do not force all upstream data through obsolete
  Plotloom fields merely to keep the old implementation.
- Begin with a manual job-package handoff patterned on the image specialist.
  A skill requires an agent executor; it is not a server. Automation and other
  executors are deferred until the working path merits them.
- Qwen configuration is preserved but Qwen is not in the immediate authoring
  delivery path. No dual implementation or model benchmarking project.
- Job files live under the project's ignored `outputs/` storage, within their
  owning project/job home, with timestamped job folders where appropriate.
  No loose user-level generated files; no credentials in artifacts.

## Source and interactive structure

Support three source routes: synopsis → Terra-authored source story; externally
written story/treatment; existing work supplied for adaptation. Do not require a
full novel: a complete short treatment can suffice. Record source attribution,
usage rights/permission as supplied, adaptation intent and invented additions.
Never invent missing source text or claim legal clearance from a checkbox.

Use one shared story and character/art bibles, with a DAG of stable story-section
IDs. Choices connect sections; a viewer sees one route, not every optional section.
Display episode numbers where useful, but do not use sequence position as identity.
Write shared content once; do not duplicate every full route into an independent
episode. Each writing brief includes relevant prior events, incoming choice,
entity facts, intended consequence and ending/handoff.

The first integrated pilot is one small story, one decision and two distinct
endings, cinematic realism and pause-and-choose. Its scope/duration is frozen at
F1 before generation, not tuned after results. Reconvergence is deliberately later,
not abandoned. No new inventory/combat/state-dependent game engine is implied.
Episode-only hook/cliff requirements must be explicitly inapplicable for sections
that lack them, never fabricated or silently counted as passed.

## Checkpoints and live tracker

F0 through F5A now have bounded technical seams. The rows below distinguish
implemented lifecycle contracts from their still-required live specialist and
human creative evidence; no row is product acceptance merely because its
technical boundary exists.
Characters/art/script may iterate together; ordering describes acceptance
dependencies, not a rigid waterfall. Each delivery updates this table.

| ID | Deliverable and reuse | Acceptance evidence / next exit | Replacement obligation |
| --- | --- | --- | --- |
| F0 — Foundation and handoff **(candidate boundary delivered; [receipt](../verification/2026-09-17-f0-shuohao-handoff-receipt.md); not full F0 acceptance)** | Pinned Shuohao; checkout-operated repo specialist; minimal project-local request/candidate transport | Fresh recursive checkout can resolve the pinned skill and return a traceable, validated outline candidate/report. Candidate readiness verifies the complete frozen package and rejects malformed/stale delivery before a future owner can install it; no user-home runtime dependency. Pin/license and five-stage field/gap map recorded. F0 has no review or canonical-install owner proof. | F1 must select and prove the user-operable review/install owner; old authoring entrypoints are identified but not yet retired; no parallel general orchestration framework. |
| F1 — Source + novel-outline **(F1A lifecycle and F1B source-bound mapping/canonical-route admission delivered; creative/product acceptance pending)** | Three source routes; reviewed story direction, characters/assets inventory, sections, choices and endings | F1A persists declared synopsis/imported/existing-work source material and accepts/reopens a candidate-only upstream `outline.json` through the F0 exchange. Prepared external publication blocks project lifecycle/snapshot transitions until explicit cancellation; late cancelled delivery cannot alter canon. F1B adds an author-reviewed, source/outline revision-and-hash-bound map with exactly one entry/choice and two labelled consequence/ending links. It saves/reloads/reopens independently of Bible generation, then explicitly and atomically installs only its current three authored IDs into the existing graph routing owner. Source, accepted-outline, or map changes visibly stale only that admitted graph and actual consumers; unrelated graph ownership is not overwritten. This is technical proof, not invented human creative approval; F1 remains unaccepted until a fresh synopsis is genuinely human-reviewed as a one-choice/two-ending story. | Replace overlapping Brief/Bible/Graph proposal-writing logic only as the new path becomes usable; retain routing authority, not a second graph. |
| F2 — novel-characters **(F2A source-bound cast review and F2B attended two-study technical proof delivered; [F2A receipt](../verification/2026-09-18-f2a-cast-review-receipt.md), [F2B receipt](../verification/2026-09-18-f2b-cast-identity-proof.md); not human creative, F5 cross-shot, or F7 voice acceptance)** | Shared character bible, motivation, appearance/voice direction, identity references; existing ImageGen handoff | F2A prepares, refreshes, inspects and explicitly accepts one upstream `cast.json` bound to accepted source/outline/F1B sections, preserving a thin explicit consumer-ID seam. F2B freezes that accepted cast revision/hash and appearance direction through existing identity-reference/proposal currentness, with no duplicate media authority and no Story Bible/Shot/Approval prerequisite. In the disposable F2A project, a live original and a reference-byte-conditioned refinement were generated, inspected, explicitly selected, independently visually reviewed, and persisted through reload and close/reopen. Text direction and this two-study evidence are not proof of generated voice consistency. | F3 is the next creative-stage seam. F5/F7 production cross-shot and voice proof remain separate. |
| F3 — novel-art **(F3A text-first candidate/review path corrected for format admission, lifecycle recovery, upstream validation, reloadable frozen handoff, and committed production-browser regression at `bfc2b57`; [F3A receipt](../verification/2026-09-18-f3a-art-review-receipt.md). F3B attended two-study technical proof delivered; [original receipt](../verification/2026-09-18-f3b-art-reference-proof.md), with complete upstream-currentness, project-epoch, and unmount callback-ownership correction tracked separately in its [correction receipt](../verification/2026-09-18-f3b-currentness-correction.md); not human creative, F5 cross-shot, or production acceptance.)** | Shared locations/props, visual anchors and justified state/lighting variants | F3A freezes source/outline/map/graph/cast inputs, validates with the pinned upstream `novel-art` validator, and adds only a thin exact section-ID projection. Format-8 folders fail explicitly before open; fresh format-9 folders preserve stable scene/prop IDs and section usage through accept/reopen/save/restart. Prepared art blocks close/archive/delete/snapshot and recovery; cancellation remains user reachable and rejects late installation. Reload re-copies the same frozen assignment; current accepted JSON is inspectable without reopening, while reopening controls edits. F3B proves inspectable reusable environment/prop managed-reference candidates through the canonical art current-subject admission and current package/provenance owners, visibly labels missing/changed currentness, and does not infer physical meaning from ambiguous state labels. | Replace duplicated asset-authoring rules; retain managed asset storage/selection. |
| F4 — novel-script **(current-contract three-section technical proof delivered; first missing-binding candidate preserved/rejected; [receipt](../verification/2026-09-18-f4-novel-script-receipt.md); not human creative or product acceptance)** | Source-faithful action/dialogue for every pilot section using upstream writing/check/report workflow | One current Terra/high delivery bound exact `opening → 1`, `beacon → 2`, `dock → 3`, with source facts and two decision consequences intact. The headed production-browser proof re-copies/refreshes the frozen package, technically accepts it, reloads read-only JSON/original report, saves an opening-only edit while byte-preserving the two ending sections, and survives backend restart. Pinned validator/render and applicable section/route caps pass; hook/cliff and aggregate mutually-exclusive-ending duration stay explicitly product-inapplicable. | Replace overlapping scene/beat authoring, not wrap every old field in a new layer. No custom plan-expand subsystem by default. |
| F5 — novel-storyboard **(fresh F5A specialist delivery through production technical review delivered; [fresh receipt](../verification/2026-09-18-f5a-fresh-specialist-production-review-receipt.md), [lifecycle receipt](../verification/2026-09-18-f5a-source-bound-storyboard-review-receipt.md). The preserved content-split candidate remains historical evidence in its [production-seam receipt](../verification/2026-09-18-f5-storyboard-production-seam-receipt.md), not the fresh delivery, human creative approval, or product acceptance.)** | Script-derived review direction and reports; reuse upstream validation/render and the F0 handoff | F5A freezes the current accepted F4 script revision/hash, complete transitive binding, section/episode order, F4 section/route caps, and review-only 2–8s cut / 15s segment policy; it persists only raw upstream JSON/report as a review revision and visibly stales it with its source. A fresh package was re-copied, validated, refreshed, inspected, explicitly accepted, and preserved through backend restart and normal close/reopen. Independent content review passed. Attended native visual/creative review remains required because the Mac was locked; no creative approval is implied. Candidate `maxCutSeconds` is configurable upstream only within the frozen F5A review policy; production H3 remains fixed5 until separately qualified. No V2 SceneBeats projection, source-to-shot installation, media dispatch, or selected reference is a prerequisite or outcome of review-only evidence. | Replace overlapping scene/beat authoring only when a separately accepted product owner exists; retain this review/currentness seam and do not add a duplicate shot/prompt compiler. |
| F6 — Audiovisual qualification **([readiness receipt](../verification/2026-09-18-f6-h3-audiovisual-readiness.md), [offline 5/8-second contract receipt](../verification/2026-09-18-f6-h3-eight-second-offline-contract.md), [first live non-qualifying receipt](../verification/2026-09-18-f6-h3-first-clip-live-receipt.md), [offline corrective prompt proof](../verification/2026-09-18-f6-dialogue-prompt-offline-proof.md), and [corrected final-budget live receipt](../verification/2026-09-18-f6-h3-corrected-dialogue-clip-receipt.md); not audiovisual or production acceptance)** | Test native H3 dialogue, speaker attribution, cross-clip voice consistency and prompt effectiveness | Plotloom admits explicit 5- and 8-second H3 I2V contracts. Two and only two F6 live submissions are retained, both unselected. The first objectively ingested 8-second H.264/AAC clip is non-qualifying because its fixture froze a generic prompt. The final-budget corrected job froze and independently reviewed one C01/Lin Che `我在这里。` cue, quiet-room/no-narration/no-music direction, reviewed aspect, profile, and 8-second/192-frame/24-fps request; its output objectively ingested at 8.000 seconds, 192 frames, 24 fps, `576×1024`, H.264/AAC. Subsequent human review rejected the corrected clip: an unintelligible character-spoken utterance under one second around 4s precedes the recognizable intended line; unwanted burned-in subtitles show the intended line during both utterances. Audiovisual qualification failed; objective delivery remains valid. The cause is unproven. Voice consistency remains unqualified because the first clip has the wrong prompt. | No speculative TTS/lip-sync stack; no pad/trim/stitch workaround, duplicate queue, F5-to-media compiler, retry, or third submission. Keep F5/F7 production-reference and mapping choices explicit. |

| F7 — Reviewed production | Existing ImageGen/H3 jobs, alternatives, regenerate/select/discard across the pilot | Human can compare and choose clips, regenerate a defect and discard unselected candidates safely; selections, source revisions and provenance survive reopen. Missing media and failures actionable. | Reuse current media backend/accounting; avoid duplicate queue or candidate store. |
| F8 — Integrated playable pilot | All pilot sections produced, explicit choices, two endings, restart | Genuine native playback of both paths, held choices/endings, refresh/close/reopen; no wrong-branch footage or missing selected media. Creative/audio acceptance distinct from automated checks. | Reuse current player; stitching/export optional, not another playback engine. |
| F9 — Reconvergence | Minimal source-owned reconciliation for compatible incoming histories | One fresh branching/join example preserves differing consequences or explicitly reconciles them. Incompatible histories remain separate or visibly blocked; no unexplained state reset. | Reuse graph; add only evidenced context/authoring needs, not a general symbolic story engine. |
| F10 — M2 independent creation/delivery | Fresh contrasting stories through source → five stages → production → playback | Creator completes supported stories using documented UI/specialist handoff without developer repair; all intended paths complete, revisions/recovery usable, delivery opened by intended viewer. Settle local/portable/hosted delivery scope here before claiming completion. | Retire all replaced authoring entrypoints/tests for retired contracts; retain tests for supported safety and product behavior. |

### Deferred F6 prompt optimization — agreed separation

- **Evidence:** retain both F6 clips unselected. The user's review rejects the corrected clip for extra speech and unwanted repeated subtitles; do not reinterpret it as a transport failure or accepted native dialogue.
- **Prompt alignment:** MiniMax's pinned [H3 skill](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/.agents/skills/h3-prompt-writing/SKILL.md) and [base guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/.agents/skills/h3-prompt-writing/references/base-en.txt) now govern the single-image prompt contract; see the [living playbook](../operations/h3-prompt-writing-playbook.md). Do not reuse unreviewed Chinese non-dialogue directions or the failed vocal-control condition.
- **Experiment:** the separately authorized U4 C trial used a guide-compliant reviewed English-direction prompt with verbatim Chinese dialogue. Its technical [receipt](../verification/2026-09-24-u4-h3-reviewed-english-trial.md) and subsequent director listening establish the narrow original-line observation above, not a general mechanism or audiovisual qualification. The current bounded seed/adjacent-shot assignment is recorded in the current review pause; this historical F6 separation does not enlarge it.
- **Product review:** keep regenerate/compare/select/discard in F7's existing candidate workflow; prompt improvement does not remove human acceptance.
- **Fallback decision:** if bounded evidence shows native speech remains unsuitable, separately assess controlled audio. Do not build a speculative TTS/lip-sync stack or redesign the text pipeline now. Cross-clip voice consistency remains an independent unmet gate.

## Execution and acceptance

The completed F5A integration closeout preserves baseline `bf4cc11` and tests
`ba271a6b3a9267dff4d103943339d8cbcddb82e9` in a fresh recursive local clone:
18 focused production FastAPI/file-SQLite browser cases, 627 locked Python tests,
162 frontend units, both typechecks, reproducible static build and fresh installed
wheel smoke pass. [Receipt](../verification/2026-09-18-f5a-source-bound-storyboard-review-receipt.md)
and [independent Terra/high delta review](../verification/2026-09-18-f5a-integration-delta-review.md)
retain actual checks, demonstrated fixes, failures and the main-worktree hygiene
discrepancy. Deliverable: current-package deterministic end-to-end review proof,
only demonstrated contract/UI/snapshot/gate defects repaired. Exclusions: fresh
specialist/creative approval, live generation, providers/H3, upstream changes,
legacy projection, retained databases, compatibility, CI/AGENTS and directory
cleanup. Stop condition: commit on main without push, stop owned services and
collect actual Relay source release. Technical proof does not accept F5 content
creatively or qualify production media.

The fresh live F5A specialist technical delivery is now complete. The next
bounded F5 action is an attended native visual/creative review of that accepted
review evidence; it is not implementation of the remaining rows or a provider
experiment. Director may dispatch successive settled slices without routine user
confirmation, using Terra and Relay serial source ownership. Each assignment
states exact deliverable, scope, reused components, checks, exclusions and stop
condition.

Before implementation of each slice, identify model-, author- and code-owned fields.
Use existing tools/contracts first. Changes to ownership need concise ADR updates.
Do not demand backwards compatibility for retired development formats; preserve
valued projects/assets and current integrity safeguards. Resets are scoped to
identified disposable data, not blanket cleanup authorization.

GitHub CI is a deliberate manual-trigger check, not an automatic acceptance
blocker for every push. Run it when its evidence is needed; retain the workflow's
jobs and `workflow_dispatch` entrypoint rather than adding a separate CI path.

Verify progressively: focused tests while editing; relevant production UI/runtime
journey and independent source-backed review on a stable candidate; broader
Python/frontend/build/wheel gates proportional to executable changes. Docs-only
work needs links/consistency/diff checks, not full runtime suites. Never count
unrun/inapplicable gates as passed. Capture latency/tokens if available without
inventing cost metrics. After two failures at one criterion, reassess rather than
repeat a broad task or add more machinery.

Every checkpoint records implementation, tests and creative/product acceptance
separately, plus replaced/deleted paths (or a concrete reason retirement is not
yet safe). Director reviews and pushes verified scoped work after checking remote
divergence. No force push, active-writer ref mutation or concealed failing gates.

Escalate only material changes: new paid services, changed rights assumptions,
destruction of valued work, source authority ambiguity, altered acceptance or
product scope. Native Codex ImageGen and owned H3 development calls are authorized;
that is not automatic audiovisual Approval. Model/provider choice changes and new
audio services must follow the settled scope, not be silently introduced.

## Named open decisions

- **F0:** exact upstream revision and smallest reproducible dependency/adaptation
  method; source/export schema mapping and safe report embedding.
- **F1/F9:** section-versus-episode rules and explicit join context. Do not force
  episode pacing rules onto endpoints or promise all DAGs before qualification.
- **F6:** measured deployed H3 voice/dialogue capability, whether separate audio is
  necessary, and resulting production tradeoffs.
- **F10:** supported story envelope and distribution/hosting boundary; manual
  specialist operation must be documented and user-operable if retained.

These are checkpoint-owned investigations, not reasons to delay F0, and not
authorization for generalized frameworks.
