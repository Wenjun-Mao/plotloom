# Story to playable Alpha: development roadmap

Status: **direction amended after external review, 2026-09-11**. User-approved
direction and P0 authority boundaries are recorded in ADR 0026. This is not
authorization to implement every milestone or evidence of available media
production. The bounded [P0 plan](p0-imported-still-preview-plan.md) revision 1 is Approved;
later technical details remain subject to their own planning and acceptance.

**P1 direction amendment, 2026-09-11:** the user selected a Codex image specialist
with manual job handoff as the first image backend. See
[ADR 0028](../adr/0028-agent-operated-image-jobs.md) and the
[P1 revision 2 draft](p1-image-generation-plan.md). Automatic dispatch and external
image-provider qualification are not P1 prerequisites. This is not implemented.

Source baseline: `9afbefd2f82a620d79b82cd6607571057f23a6c4`, locally clean on
`codex/m1b-alpha` before this documentation change. Repository:
<https://github.com/Wenjun-Mao/plotloom>. Review publication branch:
`codex/m1b-alpha`; this is not a merge to `main` or an Alpha release.
Review source at the [immutable baseline](https://github.com/Wenjun-Mao/plotloom/tree/9afbefd2f82a620d79b82cd6607571057f23a6c4).
The roadmap and review prompts are subsequent documentation-only additions.

## Start here

The outcome is a **short, playable branching audiovisual story inside Plotloom**.
The creator starts mainly with a synopsis, chooses and refines proposals, and
can edit details. Intermediate deliveries must be useful on their own.

Read this roadmap first, then [ADR 0026](../adr/0026-story-to-playable-product-direction.md)
for decision boundaries. The [capability matrix](capability-matrix.md) remains
the implementation progress authority. The [M1-C completion plan](m1c-completion-plan.md)
still owns text qualification; this roadmap does not waive its gates.

External review prompts are in
[creative workflow review](story-to-playable-review/creative-workflow.md) and
[architecture and delivery review](story-to-playable-review/architecture-delivery.md).
Both reports have been returned. Their [synthesis](story-to-playable-review/synthesis.md)
records evidence limits and Use/Test/Park/Discard dispositions; the original
review prompts retain their publication-time context.

## 1. Where we actually are

| Area | Established baseline | Not established |
|---|---|---|
| Text authoring | Project lifecycle, session drafts, four-stage editors, deterministic graph, bounded correction, exact unit repair, atomic installation, structured dialogue/audio/state, gates and Approval | Formal independent M1-C qualification and fresh remote CI |
| Real creation | A prior llama canary produced an editable, persistent storyboard; later readiness probe verified restored connectivity | A probe is not generation; one canary is not qualification |
| Local verification | Existing ledger records 524 Python passes/9 skips, 115 frontend passes, 23 browser journeys, build and installed-wheel smoke | These are retained results, not tests rerun for this document; skipped historical media specs do not prove production |
| Media | Historical adapter/worker code and production ADRs provide starting points | New media is deliberately blocked pending approved production snapshots; managed binary assets, candidate selection and playable preview remain to build |

Evidence: [readiness ledger](../verification/2026-09-10-provider-readiness-offline-candidate.md).
The earlier canary was at a different source revision and is not relabelled as
current acceptance. Existing alpha code still advertises the legacy matrix;
single-backend qualification support must be checked and completed narrowly
before running the independent gate. Do not confuse completed adapter modularity
with completed qualification tooling.

## 2. Confirmed product direction

- Story-first, usually with no visual assets. Future character images, concept
  art and photographs must be importable, with originals preserved.
- Initial visual target: cinematic realism, not a restriction on future styles.
- The main interaction is selecting/refining Plotloom proposals; detailed
  structured editing remains available.
- Early images may be generated directly in the development conversation and
  imported into Plotloom. These are real assets, not fake provider successes.
  This route does not imply local/free generation or an embedded product feature.
- Native audio belongs in the video pilot when the selected backend supports
  it. Separate TTS, stem editing and mixing are later options.
- Plotloom itself provides sequential preview; an external editor is optional.
- The destination is branching playback. Initially, a node's sequence finishes,
  its last frame is held, choices appear, and the viewer chooses without a timer.
  Playback follows the selected edge. No implicit default choice.

## 3. The intended creative journey

`Synopsis → editable storyboard → visual proposals → selected references →
keyframes → audiovisual clips → sequential scene → pause-and-choose story`

Start small: one protagonist, one principal location and three complementary
keyframes showing one continuous dramatic moment. Close-up, environment and
action are useful coverage choices, not a mandated sequence. Start with two
comparable visual directions; add a third only if useful. Reuse selected frames
as references when suitable rather than automatically building separate sheets.
Generate one audiovisual clip, then test its neighbour before expanding scene
production. One clip proves no cross-shot voice or action continuity.

Visual proposals fill missing appearance, costume, lighting and sound intent in
a versioned **visual brief**. They must not silently invent canonical narrative
facts. A proposed military insignia, for example, may imply an affiliation and
needs explicit story review; a lighting suggestion usually does not.

Separate creative proposal generation from deterministic compilation. The
compiler assembles selected intent, shot/cue/state references and capability
constraints; it does not ask an image endpoint to write another prompt. Keep
generated candidates separate from the creator's selected production inputs.

Show proposed additions and what varies between alternatives; offer neither,
keep current and refine one aspect. Separate selecting an unspecified portrayal
from approving changes to narrative facts, including consequential sound cues.

Recommended review moments: visual direction, keyframe consistency, then
audiovisual performance across the cut and into the choice hold. A compact
creator-readable continuity strip may expose existing facts, action boundaries
and selected intent; it is not another authoring stage. Missing facts remain
proposals. Avoid approval clicks for every exploratory variation.

## 4. Delivery sequence

These are vertical slices, not a requirement to finish a general media platform
before showing a picture. Exact task/file boundaries are planned at each slice.

| Milestone | Observable deliverable | Exit evidence |
|---|---|---|
| Q — Text qualification closeout | One explicitly supported text configuration; other profiles remain independently experimental/deferred | Existing core gates, 9 fixed runs, three blinded reviews, source-bound receipt and fresh CI before claiming M1-C |
| P0 — Imported visual pilot | Import four real images, compare alternatives, select three consecutive shots in one scene and play a labelled still animatic | Real FastAPI/browser journey; exact approved projection, original bytes and selections survive refresh/restart; replacement/history, stale/revoked and missing/corrupt states distinguished |
| P1 — Specialist-backed image jobs | Prepare/copy a frozen job to the Codex image specialist; Refresh to ingest, compare and select generated/refined keyframes | Approved job identity, observed imagegen execution, complete validated delivery, idempotent Refresh, explicit selection and restart persistence; no automatic bridge required |
| P2 — First audiovisual clip | Animate one selected keyframe with one short line and environmental sound; play it inside Plotloom | Real video downloaded and inspected, native audio present and reviewed, exact reference/shot/cue lineage retained |
| P2 exit experiment — The adjoining shot | Add one neighbouring clip with the same character; test a distinct short cue if evaluating voice consistency | Normal-speed, muted and audio-only review across the cut and final hold; do not expand scene production until blocking continuity defects are resolved |
| P3 — Sequential audiovisual scene | Play several selected clips in shot order inside Plotloom | Play/pause/seek and shot navigation; measured durations; no accidental repeated/cut dialogue; refresh retains selected sequence |
| P4 — Playable branching Alpha | Follow a small story through choices and distinct outcomes, then restart/explore | Every reachable branch in the chosen complete story is playable; state and joins agree with canonical graph; pause-and-choose works |

Q and P0 are separable work scopes: media development can use a manually reviewed
existing storyboard while formal text qualification remains explicitly open.
This is not authorization to dispatch parallel agents. Do not repeatedly change
the qualification candidate while collecting its evidence. Q must pass before
the combined product is advertised as a qualified story-to-playable Alpha.

### P0: smallest useful asset and preview slice

- Controlled upload/import, not arbitrary server-path reads. Store original bytes
  with content hash, observed MIME/dimensions, origin and available rights metadata;
  label unknown provenance rather than fabricate it. Thumbnails are derivatives.
- Reuse the existing byte store with separate managed-asset records. Deduplicate
  bytes, not provenance; imports must not fabricate generation runs. Validate
  actual raster content, bounded decoding and existing stored bytes before use.
- Associate artifacts with stable character/location/prop/style/keyframe roles.
  Distinguish identity, design, composition and style reference intent. Byte
  preservation is guaranteed by storage; generated identity fidelity needs review.
- Compare candidates and explicitly select them using revision-checked bindings.
  Replacement preserves history and marks affected derived work stale.
- Provide a still-image sequence using authored durations, visibly labelled an
  animatic, not a generated video. Capture exact applicable Approval, canonical
  inputs, reviewed selection revisions and hashes in a coherent immutable still
  projection. It is non-generative, not a complete ProductionSnapshot.
- Keep offline viewing of imported assets possible; test missing/corrupt files,
  import limits, project isolation and safe referenced-file retention/deletion.

ADR 0026 now distinguishes import/exploration, reviewed still preview, and provider
production. Build only the artifact/selection/projection subset this journey uses;
provider API/repository/worker hard stops remain closed. Plan asset retention
explicitly, including history and permanent deletion; do not build general GC.
No paid-provider job system is needed to prove this first outcome.

### P1–P2: real generation without changing narrative authority

ADR 0028 specializes the principles below for P1: manual handoff replaces automatic
submission; completed-file ingestion replaces provider downloading/polling. Named
HTTP media profiles, remote lifecycle adapters and video capabilities are later
integration work. Frozen production inputs, explicit selection and uncertainty
boundaries remain mandatory.

- Implement ADR 0012's production projection initially as one shot per unit,
  retaining future contiguous multi-shot support without implementing it now.
- Freeze an immutable ProductionSnapshot at admission: exact canonical revisions,
  active Approval, selected reference hashes, visual intent, cue/audio schedule,
  compiler/planner versions and effective public provider configuration.
- Resolve named media profiles through explicit versioned adapters and declared
  capabilities. Reuse sound text-profile patterns, not text-specific assumptions.
  Endpoint/model aliases must not control domain behavior.
- Capability checks cover input modes/reference combinations, output duration,
  dimensions, native audio, upload transport and sync/async lifecycle. Refuse
  unsupported combinations; do not silently drop references or dialogue.
- Track submission uncertainty separately from definite failure. Persist remote
  task identity when available; reconcile after restart. Browser cancellation
  is not proof of remote cancellation. Never blindly replay an unknown submission.
- Keep execution outcome, ingestion state and cancellation intent distinct. Poll
  exhaustion is not proof of remote failure; a retrieval retry must not regenerate.
  Define dispatch authorization cutoff and atomic claim/idempotency before P1.
- Download and validate output before claiming an offline-usable artifact. Retain
  task evidence and useful failure state when generation succeeded but ingest
  failed. Temporary provider URLs are not durable identities.
- Preserve HTTP/LAN/Tailscale for configured trusted services. External providers
  may require upload or reachable URLs; do not expose the local server to satisfy
  them. No secrets in snapshots, artifact metadata, logs or public receipts.

The P2 clip should have one visible character, an intelligible short line, a
clear action and environmental sound. Listen/watch for speaker correctness,
wording, language, lip synchronization, performance and unwanted sounds.
Audio-track presence alone is not success. Native speech must not become a new
authoritative DialogueCue merely because the model improvised it.
Keep complete utterances within individual pilot clips. This is a diagnostic
choice, not a permanent authoring restriction. Review the neighbouring clip for
apparent recasting, repeated action/lines, changed voice and unsuitable sound cuts.

### P3: playback is not a full editor

Selected clips play with simple cuts in storyboard order. Include play/pause,
seeking, mute/volume, navigation to the shot and a small “replay this cut” control.
Use observed delivery durations
for playback, keeping authored timing separate; never silently retime canonical
shots to fit provider output. A mismatch requiring truncation, stretching or
changed dialogue needs an explicit production decision.

Review across cuts: identity/costume, spatial direction, action continuity,
voice, ambience, music and clipped/repeated lines. Initially recommend native
dialogue/ambience/SFX with non-diegetic music off where controllable, avoiding
unrelated music restarting per clip. Mixed native tracks are not editable stems.
If the pilot cannot meet the scene's sound needs, document the specific failure
before adding a separate sound pipeline.

An incomplete preview may use labelled still/text placeholders. It must never
be labelled a finished scene. Test loading/errors, browser gesture requirements,
unsupported media and recovery without duplicating audio playback. Use browser
integration tests plus human listening/viewing; neither substitutes for the other.

### P4: one authoritative branching story

- Derive a versioned playback manifest from the canonical graph, production
  selections and artifact hashes; do not maintain a second editable branch graph.
- A viewing session pins that manifest so edits do not change its story mid-play.
- After a decision node's clips end, stop its audio, hold its final frame and
  present choices. Selection applies the authored edge effects exactly once.
  Non-decision transitions continue automatically; endings show ending/restart UI.
- Joins must respect the canonical continuity/reconciliation contract. If one
  shared clip cannot depict both incoming states, surface that conflict; never
  silently normalize narrative state to make playback work. Shared media is
  reusable only when the required context is compatible.
- Restart resets session state; revisit/navigation must not reapply effects by
  accident. Provide keyboard-operable choices and clear loading/error feedback.
- Complete mode requires current approved inputs and playable selected media for
  every reachable depiction context, plus valid choices/joins/endings. A shot's
  available dry-coat clip does not satisfy a wet-coat incoming path. Draft mode may inspect
  incomplete branches but declares gaps. Returning to an old manifest is historical
  preview, not approval of the current head.

Recommended first branching pilot: one decision, two meaningfully different
outcomes, reusing the initial scene. Add a small join-containing test fixture to
exercise state correctness, without making a whole feature film the first trial.
The existing join compiler supplies incoming-edge descriptors, not initial-state
or arbitrary path-state runtime semantics. P4 must define those explicitly.
Neutral framing can avoid depicting a difference but cannot erase it; when that
difference matters again, require compatible media or authored reconciliation.
Finish dialogue, action and necessary sound tails before the indefinite choice
pause. Do not introduce persistent ambience as an unapproved playback change.

## 5. Decisions still open

| Question | Current recommendation | When to settle |
|---|---|---|
| First image execution route? | Settled: Codex built-in image specialist with manual job handoff; no external image API prerequisite | P1 access and real-output acceptance |
| First video endpoint and spending policy? | Qualify one; user supplies/chooses account and approved live scope; no automatic batches | Before P2 real integration trial |
| Must character voice be identical across clips? | Treat recognizability as a review target; make no guaranteed voice-lock claim without endpoint evidence | P2 evaluation, before expanding P3 |
| Provider duration does not fit authored shot? | Expose discrepancy; explicit selection/edit or production timing decision, never hidden canonical rewrite | P2 contract |
| Imported person's identity/likeness constraints? | Preserve original; record intended uses/rights and require review of generated fidelity | P0 import UX |
| Packaging/export beyond in-app playback? | Later portable playback bundle with local assets; not required for first P4 | After P4 |

Wan 3.0 is a candidate, not a dependency. The
[fal image-to-video API](https://fal.ai/models/alibaba/wan-3.0/image-to-video/api)
documents a required start image, optional end image and generated audio enabled
by default. Alibaba's
[Wan 3.0 guide](https://www.alibabacloud.com/help/zh/model-studio/wan3-video-generation-guide)
documents native audiovisual output and separate first/last-frame versus
multimodal-reference modes. Do not infer fixed-first-frame plus voice-reference
support for an endpoint from the model family name. These are documentation
observations during planning, not account-backed compatibility or quality tests.
Atlas-specific support has not been verified. Recheck the chosen endpoint before
coding, including prompt expansion and whether its actual prompt is returned.

## 6. Non-goals and guardrails

No V1 runtime, legacy content migration, public multi-user deployment, remote
server administration, model-specific story logic, general plugin loader, full
nonlinear editor, timed choices, branching overlays on moving video, separate
TTS/mixing, large batch automation or final export platform in the initial slices.
No new images or paid video calls are made by approving this document alone.

Preserve exact historical snapshots/hashes. Preserve imported originals and
candidate history. Production cannot use stale Approval or an arbitrary Shot URL.
Changing a selected artifact creates new bindings/snapshots, not rewritten history.

## 7. Applying the efficiency lessons

Follow [ADR 0023](../adr/0023-bounded-delivery-and-evidence.md), with these concrete
checks at each milestone:

1. Name one creator-visible outcome, verified baseline, owned files, cheapest
   direct attempt, required evidence and stop condition before implementation.
2. Use one owner by default. If delegation is justified, give a separately owned
   bounded task and minimal context; Terra is the default. No standing coordinator
   or repeated status-polling loop is needed for this roadmap.
3. After one support-only checkpoint, attempt the visible outcome. For P0 that
   means importing/selecting/reopening images, not building more infrastructure.
4. Run focused tests during changes; full required suites on the stable candidate
   and repeat when affected changes justify it. Review once, reopen for specific
   findings. Do not waive failures or dilute creative acceptance.
5. If the same failure survives a targeted fix, preserve evidence and reassess
   ownership/contract. No open-ended prompt retry or increasingly tolerant parser.
6. Record code result, product result and qualification separately in existing
   progress records. Capture available usage deltas; unavailable cost measurement
   is disclosed, not a reason to build another monitoring system.

No calendar or token-cost estimate is asserted yet. Calibrate from P0's accepted
result before scheduling larger slices. Full release gates retain Python,
frontend unit/type/build/static freshness, real FastAPI Playwright, wheel/install,
secret boundaries and relevant live/creative checks; this docs-only draft needs
only document/link/diff review.

## 8. Review and next action

Two complementary independent consultations were completed:

- Creative workflow reviewer: simplify the path to cinematic, coherent scenes;
  challenge reference, selection, continuity and sound assumptions.
- Architecture/delivery reviewer: inspect exact accessible source, falsify unsafe
  ownership/lifecycle assumptions, and propose the smallest complete P0 slice.

Keep reports unchanged and record synthesis separately, classifying insights as
Use/Test/Park/Discard. Verify relied-upon claims proportionately. Reviewer
agreement is not product acceptance or an instruction to rewrite existing code.

The [synthesis](story-to-playable-review/synthesis.md) was reviewed and the user
authorized these amendments and approved revision 1 of the bounded
[P0 implementation plan](p0-imported-still-preview-plan.md). Next is the separate
execution handoff. Q remains separately scoped and open. No extra consultation
round, automatic live generation or detailed speculative task tree for P1–P4 is
required. The prior GitHub packet remains identifiable by commit; these later
amendments do not rewrite what the reviewers inspected.
