# Published voice → performance take → H3

**Status:** All four specialist checkpoints implemented and technically verified,
2026-10-01; see the [completion receipt](../verification/2026-10-01-published-voice-takes-shared-admission.md).
Owner approval was 2026-09-30 for “Go ahead and finish all four checkpoints.”
Planning baseline: `e288623`, retained `codex/h3-ref2va-gateway` checkout.
No Relay execution, Plotloom source changes, director contact, merge or push.

## Planning review, 2026-10-01

The planning-only review reused this document without authorizing new inference.
Source inspection at local HEAD
`43ff815` confirms that the durable take domain, shared admission lane, gateway
facade and Lab take controls are already present. This is implementation
progress, not final deployment acceptance. Preserve the original approval and
baseline above rather than restarting or duplicating the four-checkpoint plan.

The following bounded closeout sequence was subsequently completed under the
continued four-checkpoint goal; evidence is in the completion receipt:

1. **Finish the deployed UI artifact.** Build and smoke the Voice Lab wheel from
   its own service directory. The latest source adds manual Take ID copying when
   the Clipboard API is absent or denied on Tailnet HTTP. At a verified idle
   boundary, install the new wheel without dependency/model changes or data
   resets; retain the previous release and verify the pinned inference source
   fingerprints. Restart only the two control services as needed.
2. **Verify the actual caller journey.** Confirm the existing file-SQLite browser
   journey, then use the deployed Lab to restore the selected voice/take, listen,
   download and manually copy the Take ID. Retain a 1440×900 screenshot. Recheck
   idle service restart and persistence with existing accepted results only;
   do not press Generate or submit another video.
3. **Reconcile evidence and operational documentation.** Inspect the retained
   exact-ID qualification/restart receipts before making acceptance claims.
   Keep original observer failures separate from inference outcomes. Record
   the bounded call counts, immutable audio/hash binding, FIFO/process release,
   data preservation, actual deployed artifact and verification gaps. Segmented
   memory observations are not an uninterrupted peak-memory measurement or a
   historical CUDA root-cause diagnosis. Update the held integration note and
   ADR adoption status only to match verified evidence.
4. **Close locally, then stop.** Secret-scan the scoped changes, inspect retained
   screenshots, preserve generated evidence outside tracked source where
   appropriate, stop owned test services and make a cohesive local evidence
   commit. Audit all four checkpoints against the receipt. Director contact,
   Plotloom integration, merge and push remain withheld.

No additional voice/video generation, quality sweep, resident model cache,
H3 Take-ID resolver or automatic creative approval is part of this closeout.
If retained evidence does not establish a gate, record the gap and reassess the
method; an observer failure is not permission to replay accepted inference.

This is a specialist slice, not a reopening of the implemented
[multi-engine Lab plan](2026-09-29-voice-lab-multi-engine-plan.md).
The adopted durable boundary is [ADR 0212](../adr/0212-published-voice-performance-takes-and-shared-admission.md).

## Outcome

A caller can give the gateway a published `voiceId`, exact dialogue and explicit
delivery controls, obtain a durable `takeId`, audition/download its audio, and
feed its prepared WAV into the existing H3 Ref2VA endpoint. Permanent identity
and line-specific performance remain separate. No hidden TTS step is added to
video creation; H3 still generates a new soundtrack, not an exact WAV replay.

The owner's [matched reference review](../verification/2026-09-30-reference-strategies-and-memory.md)
found much stronger urgency with the line-specific Index take while both
clips retained identity, accurate words and good lip-sync. This supports this
workflow for that shot, not universal superiority or an automatic H3 default.
Further quality tuning and historical CUDA investigation remain parked.

## Verified planning baseline and limits

- Published Voice IDs already have independent native/H3 copies, hashes and
  frozen provenance; they survive candidate regeneration and project deletion.
- Current reuse requires a selected project's `generationId`; trial WAVs are
  project/candidate-owned and have no downloadable H3 derivative contract.
- H3 already accepts reference bytes through
  `POST /v1/video-jobs/from-image-with-voice`, freezes their hashes and has its
  own input/output retention. No H3 renderer/model change is necessary.
- The gateway's durable FIFO currently covers H3 and Qwen-Image. Voice Lab has
  a separate in-process queue for all four voice engines. Advisory idle/memory
  checks do not prevent overlapping admissions; see [ADR 0211](../adr/0211-voice-lab-shared-host-operating-boundary.md).
- The preferred original MOSS D remains retained experimental audio. Existing
  technical publication `voice_5689e99835494d2f8024485523c4dbf6` is **not** that
  reference. Do not fabricate its publication lineage or substitute it for D.
  Formal import/publication of trial-origin identities is a separate decision,
  not a prerequisite for proving the API with an existing published identity.

## Contract

### Identity and take ownership

- A take resolves **published `voiceId` only**. It must not depend on a mutable
  selection, candidate, project or filesystem path supplied by the caller.
- Create one stable `takeId` before enqueueing. The same ID identifies queued
  work and its eventual result; do not require a second public job/result ID.
- Freeze the identity hash/reference transcript, exact spoken text, requested
  delivery, engine/model/runtime snapshot and resolved seed at admission.
  Record Index's observed/effective emotion vector separately before synthesis.
- Every regeneration creates a new take. Completed bytes never change behind
  an existing ID. Failure must preserve other takes and the identity anchor.
- Voice Lab owns take metadata, verified native audio and a versioned H3
  derivative under its managed root, independently of the source project.
  Preserve native sample rate/subtype and the current deterministic preparation
  policy; no trimming, stretching, source gain edits or transcript rewriting.
- Audio may be technically valid but H3-ineligible. Preserve playable native
  audio and expose `h3Eligible` plus its issue code; reject H3-audio retrieval
  when no eligible derivative exists. Preserve the current 32-kHz mono PCM16,
  1–10-second, at-most-2-MiB reference contract.
- Published voices and durable takes have no automatic expiry in this slice.
  An explicit confirmed take deletion removes its managed audio, not its
  identity or caller-owned copies. Reject deletion of queued/running/unresolved
  work. Retain a minimal deleted-result marker so an ID cannot be resurrected
  by delayed registration/execution. No published-voice deletion API is added.
- Gateway video/image media remains 72 hours and gateway job records 30 days.
  Its cleanup must not delete Voice Lab's durable voices or takes.

### Public gateway API

| Operation | Route |
| --- | --- |
| Queue a take | `POST /v1/voice-takes` → `202` |
| List takes for an identity | `GET /v1/voice-takes?voiceId=…` |
| Inspect result and progress | `GET /v1/voice-takes/{takeId}` |
| Fetch verified WAV | `GET /v1/voice-takes/{takeId}/audio?kind=source\|h3` |
| Explicitly delete a terminal take | `DELETE /v1/voice-takes/{takeId}` |

Creation accepts `voiceId`, `text`, required `engineId` and optional `seed` and
`delivery`. Admit `index_base` and `qwen_base` through their existing reuse
adapters. Omitted seed resolves to the current random 32-bit default. Keep
current nonblank text length limits and strict extra-field rejection.

Index supports `none`, Chinese description (`text`) and explicit eight-strength
`manual` delivery; Qwen rejects non-`none` controls. Reuse the existing typed
delivery contract and `emo_alpha=1.0`, without inventing acting presets.
No changes to Lab's neutral Qwen default or Stage-1 engine choices are implied.

Responses expose IDs, status, actual queue/phase/elapsed information, frozen
author inputs, actual delivery evidence, audio hashes/duration/format and H3
eligibility. Do not expose credentials, host paths or fabricated percentage/ETA.
Use the gateway's existing bearer authentication; configured private service
addresses and credentials are never caller-selectable or returned.

Gateway routes delegate voice resolution/storage/execution to the Voice Lab
module; they do not import inference dependencies. Existing H3 multipart input
remains `image` + `voiceAudio` + its current typed fields. No video `takeId`
resolver, all-in-one speech/video request, public idempotency key, automatic
fallback or silent resubmission is introduced.

### One shared admission owner

The gateway owns the durable cross-service FIFO. Voice Lab remains the voice
execution/storage owner, but its independent inference dispatch is retired
in the integrated Spark deployment. **All** Lab creation/reuse entrypoints,
not just new takes, must enter the same lane as H3/Qwen-Image.

- Use typed lane records referencing the owning service and frozen job ID/hash.
  Do not force voice work into video-only resolution/quality/frame columns or
  duplicate voice assets in the gateway's temporary-media tables.
- Register gateway-local jobs atomically with their lane entry. Voice Lab
  records admission and a durable registration outbox in its own transaction.
  A unique owner/job binding makes registration deduplicated and recoverable;
  do not pretend the two SQLite transactions are one atomic transaction.
- Global FIFO order is the lane's durable registration sequence, not clocks
  from two services. Before registration, report waiting-for-registration and
  unknown queue position. Registration reconciliation is safe CPU bookkeeping,
  not permission to repeat an inference request.
- Only the lane dispatcher may request private Voice Lab execution. A Lab
  worker executes a frozen job under that grant, reports actual phases/evidence,
  and terminates/reaps its supervised process group before releasing the lane.
  Public/UI routes cannot bypass this boundary. Keep one dispatcher and one
  voice execution owner; preserve native per-engine environments.
- Persist dispatch intent before starting inference. On ambiguous submission,
  timeout, restart or failed process-release proof, block further dispatch until
  the exact owned operation is reconciled. Query known job status; never infer
  completion from healthy service status, expire a lease to admit overlap, or
  blindly repeat execution. Unknown dispatch remains visible and unreplayed.
- Never replay interrupted/running voice work automatically. Known never-started
  entries may remain queued; cancelled/interrupted/deleted domain records must
  not execute through a stale lane entry. Preserve current terminal evidence.
- Existing headroom and observable external-Comfy checks remain supplementary.
  The guarantee covers managed gateway/Lab entrypoints, not direct backend
  clients or unrelated GPU services. No automatic service stop/cache flush,
  preemption, warm voice residency or queue-length cap.

## Ordered implementation checkpoints

1. **Durable take domain, offline first.** Review/accept ADR 0212; add strict
   schemas, repositories, preservation migrations, voice-ID resolution,
   frozen reference copying, native/H3 media publication and deletion guards.
   Preserve all existing IDs, hashes and user-valued assets. Retain current
   project-scoped clone trials as a distinct audition feature, not a production
   take or a compatibility shim. No new API may generate outside the shared lane.
2. **Shared admission and execution.** Implement the typed durable lane,
   registration/reconciliation and narrow private execution/status protocol.
   Route existing H3, Qwen-Image and every Lab generator through it. Test with
   fake runtimes/processes, including cross-service restart and uncertain result
   handling, before enabling the deployment. Technical module/table/protocol
   details belong to the implementer, subject to the invariants above.
3. **Gateway facade and small working Lab surface.** Add the public routes and
   a published-voice take panel: choose a published identity, enter dialogue and
   delivery, generate, see actual progress, listen, copy `takeId`, download source
   or H3 WAV, list/regenerate without replacement, and explicitly delete.
   Keep current candidate audition controls; distinguish temporary trials from
   durable takes without double headings or an extra approval bureaucracy.
   Refresh restores the identity/take selection; opening the page generates
   nothing. Update the Chinese API examples and reproduction/pipeline docs.
4. **Idle cutover, bounded qualification and held handoff.** Deploy only the
   control-plane gateway/Lab changes at an agreed idle boundary. Preserve models,
   experimental originals, current ComfyUI image and Qwen-Image runtime. Complete
   the gates below, record actual results and update the held integration note.
   Stop after this useful slice, with no message or code change in Plotloom.

Affected areas: `services/qwen3_tts_voice_lab/` contracts, repositories,
worker/process boundary, media, migration, `web/`, deploy, tests and docs;
`services/minimax_h3_gateway/` typed admission, dispatch, private transport,
API, store, deploy and docs; focused gateway tests under
`tests/services/minimax_h3_gateway/`; related ADR/roadmap/verification records.
Add cohesive modules and split responsibility before growing files past the
repository's size guardrail. Do not refactor unrelated Plotloom code.

## Acceptance and failure tests

- Published-ID reuse works after source candidate regeneration/project deletion;
  bad/missing/corrupt references fail before inference. Catalogue changes cannot
  alter queued snapshots. Unsupported engine/delivery combinations are rejected.
- Native/H3 hashes verify; ineligible audio stays playable without an H3 promise.
  New attempts cannot overwrite previous takes; failed publication leaves no
  usable partial result. Confirmed deletion cannot remove another identity/take,
  external files or an admitted H3 job's independent frozen input.
- Real SQLite/API tests cover registration gaps, duplicate bookkeeping, stale
  entries, ordering across all producer types, cancellation, service shutdown,
  child/process-group reaping, both service restart orders, disconnected control
  transport, lost execution acknowledgements and failure evidence persistence.
  Maximum managed concurrent inference is one; unknown work blocks the lane.
- Prove existing H3/Qwen contract, frame snapping, retention and audio hash
  binding remain unchanged. No legacy profile interpretation or new H3 tuning.
- A real FastAPI/file-SQLite browser journey uses fake audio runtimes for identity
  choice, Chinese description/manual controls, progress, audio playback, multiple
  immutable takes, explicit deletion, refresh and source-project deletion.
  Retain/inspect a 1440×900 screenshot; do not label fixture audio real inference.
- Run locked Voice Lab tests, syntax checks and service wheel/installed-runner
  smoke; run `uv run --locked pytest -q` at repository root, including gateway
  and extraction checks. Stage new service files when the tracked-file extraction
  test requires it. Build/smoke the existing packaged gateway/source distribution.
  Check scoped docs/patches and secret-free evidence. Root Plotloom frontend is
  not changed: repeat its build/static/E2E gates only if a shared packaging or
  actual frontend change makes them relevant, not as a substitute for Lab tests.
- One bounded independent review on the stable candidate, serial source ownership;
  address concrete findings only. No background/unattended worker or Relay task.

### Real Spark cap after implementation approval

Exactly **two Index take calls and one H3 call**; no Stage-1 generation,
new reference import, Qwen-Image inference or seed/quality sweep. Use the retained
published technical MOSS identity, labelled as such, the already-reviewed urgent
dialogue/direction and explicit seeds. Do not present it as original MOSS D.

Generate take 1; queue its H3 job and take 2 in a recorded registration order.
Verify serial execution, child release before H3, take-1 hash unchanged after
take 2, both source/H3 downloads, Ref2VA's exact selected audio hash, valid
portrait dimensions/duration and native audio. H3 uses the current Base-20
576×1024/8-second contract and existing matched first frame. Failures do not
authorize a replacement run. Use the existing CPU memory observer; no extra
CUDA instrumentation or historical OOM root-cause claim.

Restart idle gateway and Lab; verify published identity/take bytes, lane
reconciliation, actual UI refresh and healthy idle services. Preserve terminal
failures and all prior voices/media. Technical output validity is not acting
approval or proof of exact speech reuse. Owner review is needed only for a new
material perceptual decision or regression, not routine technical testing.
After two failed attempts at a gate, retain evidence and reassess scope/method.

Cutover prerequisites: confirm no active/queued managed work or unrelated Comfy
job; record exact deployed revisions/configuration and data integrity. Use
preservation migrations, not resets. If rollout fails, stop the new dispatch
owner; do not restart the old independent queues while an operation is unresolved.
Revert control-plane service configuration only after proving owned work is idle
and checking migration rollback/read compatibility. No deletion of installations.

## Specialist delivery versus later Plotloom work

**Here:** gateway API, durable voice takes, common admission, Lab interaction,
operational reproduction, bounded evidence and a withheld integration brief.

**Later, director-owned and not authorized here:** character→`voiceId` binding;
Dialogue Cue→selected take; audition/selection UI; dialogue/delivery revision
staleness; production snapshot and retained audio/provenance; matching H3 prompt
words to selected dialogue; explicit reference-strategy choice and Plotloom's
own retention. This must not turn a generated take into automatic approval.

No Plotloom backend or author UI, exact-waveform dubbing/lip-sync system,
arbitrary remote audio/path import, public auth redesign, new voice presets,
resource optimization, model training or additional diagnosis is included.
Do not contact the director, merge or push until the owner releases those holds.
Commit cohesive local checkpoints and a final receipt once implemented/verified;
Progress and evidence are recorded here and in the final verification receipt.

## Implementation closeout · 2026-10-01

| Checkpoint | Verified delivery |
| --- | --- |
| 1 · Durable take domain | Published-ID-only resolution, frozen reference/inputs, immutable native/H3 audio, guarded deletion, preservation migration |
| 2 · Shared admission | All managed producers share durable FIFO; outbox/grant reconciliation, process release and unknown-dispatch blocking verified |
| 3 · Gateway and Lab | Authenticated take API; real file-SQLite browser journey; deployed playback/download/manual-copy/selection restoration |
| 4 · Cutover and evidence | Copy migration proofs; two Index takes plus one H3 job; exact audio binding; idle restart preserving three voices and 60 WAVs; held handoff updated |

Runtime/source revision `43ff815` is qualified. Final documentation and screenshots
are committed separately without changing runtime code. No new acting acceptance
is claimed; source clipping warnings remain visible. The original observer
failures and segmented memory traces remain retained. No inference was replayed.
The director/contact/Plotloom/merge/push holds above are still in force.
