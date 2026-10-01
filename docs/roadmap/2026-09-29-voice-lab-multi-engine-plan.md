# Spark Voice Lab: independent creation and reuse engines

**Status:** Approved by the owner on 2026-09-29; implemented and deployed on
2026-09-30. The initial nine-call qualification was incomplete after a CUDA
OOM; a separately authorized one-call
[controlled neutral retest passed](../verification/2026-09-30-voice-lab-cuda-neutral-retest.md),
so all four creator/reuse paths now have successful live technical evidence.
The old failure remains intact; general co-resident CUDA reliability and new
creative acceptance are not established. The renewed call allowance is spent.
See the [original deployment receipt](../verification/2026-09-30-voice-lab-multi-engine-deployment.md)
and its separate supplement; neither authorizes another generation.
Count-per-engine and the neutral Qwen Base default were accepted before “go”.
Planning baseline: `077b1c4` on the retained specialist branch
`codex/h3-ref2va-gateway`. This is the single plan for the multi-engine slice,
following the implemented [project/Voice ID plan](2026-09-26-spark-voice-lab-projects-plan.md).
The hold on Plotloom-director contact, Plotloom changes, merge and push remains.

The owner subsequently approved one [matched H3 reference-strategy pair](../verification/2026-09-30-reference-strategies-and-memory.md),
using retained original MOSS D and an already-reviewed Index line-specific take,
with timestamped host-memory logging. Stop after those two clips; further voice
tuning is paused unless a concrete reported problem justifies new scope.
Identity references remain permanent anchors and performance takes remain
separate. The pair does not by itself choose a production H3 default or resolve
the original CUDA allocation failure.

## Outcome and evidence

Make the existing Spark UI useful for two separate decisions:

1. Create and compare a voice identity with Qwen VoiceDesign or MOSS.
2. Use the chosen, frozen reference for new speech with Qwen Base or IndexTTS2,
   optionally controlling its delivery without changing the reference identity.

The owner and a Chinese-speaking friend slightly preferred MOSS in the
[Stage-1 comparison](../verification/2026-09-28-moss-voicegenerator-isolated-trial.md).
Original MOSS D remained the preferred, imperfect reference after refinement.
The [MOSS D reuse comparison](../verification/2026-09-29-moss-d-stage2-reuse-comparison.md)
found no reliable same-person advantage between Qwen Base and Index.
Chinese-description Index urgency passed on two lines/two seeds each;
reassurance passed on one line/two seeds. In the
[frustration investigation](../verification/2026-09-29-index-frustration-control-comparison.md),
calm-heavy text interpretation missed frustration, anger-heavy interpretation
was too angry, and explicit anger `0.25` passed restrained delivery in two takes.
These are bounded findings, not a universal acting preset or model ranking.

Stop isolated audition searches. The next evidence must demonstrate the
working workflow, model isolation, persistence and failure safety.

## Approved user behavior

### Stage 1: create a voice

- Keep the existing named projects, editable shared brief/audition line,
  candidate directions, independent regeneration and immutable publication.
- Default comparison creates **Group 1 — Qwen** and **Group 2 — MOSS** from
  the same explicit directions and audition line, without a hidden LLM inventing
  variations. Support selecting just one engine when desired.
- The number is **per selected engine**. Two
  directions with both engines produce four candidate slots. Show both the
  per-engine count and total before submission.
- Paired candidates share an input-design binding for comparison but have
  independent candidate/generation IDs and completion states. A failed MOSS
  job does not invalidate the Qwen result. Equal numeric seeds are not a claim
  of equivalent random streams between engines.
- Every candidate identifies its creation engine. Generate/regenerate acts
  only on that slot; changing its engine is an explicit revisioned edit and
  makes the prior generation noncurrent with respect to that design. Never
  silently replace siblings or regenerate both groups on a single-slot action.
- Preserve blind shuffle, revealable design details, two-candidate comparison,
  selectable label text and truthful queue/phase feedback. Blind listening
  conceals engine identity until reveal; it is not a loudness-matched study.

### Stage 2: reuse the chosen voice

- Choose Qwen Base or Index independently of the Stage-1 engine. All four
  creation/reuse combinations are supported. The neutral-reuse default
  remains Qwen Base; Index is selectable for delivery control. No automatic
  engine fallback or preference inferred from the small listening trials.
- Keep spoken text separate from performance direction. Qwen Base offers
  reference reuse without an emotion-control claim; reject unsupported control
  fields rather than silently ignoring them.
- Index offers three explicit modes: no added emotion control, Chinese
  description, or manual emotion strengths. In description mode, the actual
  classifier output is persisted before speech synthesis and displayed with
  the result, including on a subsequent synthesis failure. It is a proposal
  produced by a classifier, not proof that the requested delivery was achieved.
- Manual mode exposes the eight supported categories with Chinese labels:
  happy, angry, sad, afraid, disgusted, melancholic, surprised, calm. Inputs
  must be exactly eight finite strengths in `0..1`, in the pinned order.
  A user can copy a prior interpreted vector into manual controls and adjust
  it before creating a new take. Reject simultaneous text/manual control input.
- Keep `emo_alpha=1.0` as in the qualified trials; manual intensity adjustment
  changes the visible component strengths. Do not add a second overall slider
  or hidden normalization in this slice. Record the classifier's raw vector
  and the actual vector used for synthesis. The trials do not establish a
  universal description-to-emotion mapping.
- Reuse jobs pin the source generation/audio hash and exact reference
  transcript on admission. New delivery trials never replace the identity
  reference or automatically publish a new Voice ID. A result can be auditioned
  beside the reference; semantic acceptance remains distinct from valid audio.

No separate classifier-preview service or endpoint is required in this slice:
classification is a visible phase of a normal reuse job. Preview-before-generation
can be reconsidered only if the working workflow demonstrates a need.

## Architecture and runtime contract

### Independent adapters, one serial owner

- Retain the cohesive Voice Lab service/package and current public identity
  resources. Split inference into a small engine registry, process supervisor,
  and stage-specific adapters/runners under the service; do not add model logic
  to project repositories, the H3 gateway, or Plotloom runtime.
- The lightweight API owns persistence and the existing serial queue. For
  each admitted job, start one short-lived engine process using that engine's
  pinned environment. Finish validation, terminate/reap that process and its
  children, then allow the next generation process. No inference models remain
  resident in the API process; no four-model warm cache or extra model servers.
- Use the existing qualified Qwen, MOSS and Index installations as provenance
  inputs, then package reproducible engine environments. MOSS's model/codec and
  Index's optional classifier are dependencies of their respective job, not
  independent concurrent generation services. Load the Index classifier only
  for description mode.
- Process isolation is preferred over one mixed Python environment because
  the qualified ARM64 dependency/native-library setups differ. It also makes
  process exit an explicit model-release boundary. Cold loading adds latency;
  warm-process reuse and automatic reordering by engine are deferred.
- Use a bounded typed process request/result protocol and managed output paths;
  server configuration, not user input, selects executable/environment paths.
  Do not shell-interpolate author text. Child failures/timeouts/OOM must be
  visible and leave prior candidate audio and published voices intact.
- Show actual queued/waiting-for-resources/loading/interpreting/synthesizing/preparing/finalizing
  phases, queue-ahead counts and elapsed time. No invented percentage or ETA.
  Preserve restart interruption and no automatic replay of queued/running jobs.

### Frozen jobs and preserved assets

- Extend candidate/job schemas with stage-valid engine IDs. Freeze engine,
  source/checkpoint/codec/classifier revisions, adapter version, model settings,
  exact text, resolved seed, source binding and requested delivery mode at
  admission. Append the observed/effective vector as execution evidence before
  synthesis; do not rewrite the immutable admission snapshot. Registry
  changes cannot silently change queued execution; unavailable frozen versions
  fail visibly rather than falling back.
- Migrate existing service records as the exact known Qwen engines. Preserve
  all existing IDs, WAV bytes/hashes, published voices and old provenance; do
  not reset the live Voice Lab or rederive old media. This scoped migration is
  required to preserve current user-valued assets, not a legacy API shim.
- Publication retains the exact creation provenance and independent source/H3
  copies from [ADR 0092](../adr/0092-voice-lab-projects-and-published-voice-identity.md).
  A published identity is not bound to a future reuse engine. Same-generation
  repeated Publish still returns the same Voice ID.
- Fix the media boundary rather than forcing Index's native `22050 Hz` output
  through the current Qwen-only `24000 Hz` validator. Preserve native mono
  output and format/hash; validate each adapter's declared output contract.
  Keep finite/empty/duration checks and derive H3's separate `32000 Hz` PCM16
  reference without modifying the source.
- Prevent silent clipping in derived files. Retain raw over-range float source
  as reviewable evidence with a warning; any necessary derivative attenuation
  must have a named deterministic preparation version and recorded gain.
  Already clipped PCM16 samples cannot be repaired by attenuation. Do not trim,
  time-stretch or claim automatic transcript correctness. H3-ineligible long
  candidates remain playable but cannot be published under the current H3 gate.
- Existing replacement, clone pinning, stale-input checks, project isolation
  and safe cleanup remain mandatory. No candidate-retention timer or published
  voice deletion is introduced.

### Spark resource boundary

- Store all weights under `/home/wjmao/models`; install source/runtimes and
  managed data under `/home/wjmao/services`. Preserve trial originals and model
  installations; do not create parallel copies of large checkpoints.
- One active **Voice Lab** inference process does not establish a global GPU
  lock across H3, Qwen Image and unrelated services. Check available host memory
  and observable generation activity before loading; defer visibly when the
  configured headroom is insufficient. Idle checks are advisory, not an atomic
  cross-service exclusion guarantee. A global Spark scheduler is out of scope.
- The lab never automatically stops other services. Run live qualification in
  an operator-controlled idle window. If the already authorized temporary
  Qwen Image stop is needed for trial headroom, record it and restore both its
  health and model endpoint before finishing. Do not preempt active work.

## Ordered deliverables

1. **Contract and reproducibility.** Confirm the exact installed source/model
   licenses for the intended private deployment; record restrictions without
   claiming general legal approval. Package/lock the proven ARM64 dependencies,
   including Index's native Linux normalizer and compiler headers. Do not ship
   the trial-only normalizer monkeypatch. Record a concise ADR for stage/engine
   separation, process isolation, delivery interpretation and media preparation.
   Define strict request/result schemas and preservation migration first.
2. **Adapters and lifecycle.** Implement all four stage-specific engines with
   the single process supervisor, frozen jobs, native audio validation and
   bounded failure paths. Extend repositories and progress projection. Test
   fake subprocesses and migration/replacement safety before real inference.
3. **Working author UI.** Add grouped creation, count/total clarity, per-slot
   engine editing, independent reuse-engine choice, Chinese direction/manual
   strengths, observed controls and playable results. Keep publication and
   the project chooser explicit; opening `/` must not generate anything.
4. **Qualification and documentation.** Install the wheel/runners on Spark,
   restart only an idle Voice Lab, execute the bounded workflow below, and
   update the service README, audio-pipeline report and reproduction/operations
   instructions. Maintain the withheld director-handoff note, not a message.

Affected entrypoints: `services/qwen3_tts_voice_lab/src/plotloom_voice_lab/`
(`contracts`, `identity`, `engine`, `worker`, repositories, `media`, `migration`,
`app`, `web/`), its `tests/`, packaging/deploy files and scoped docs. Add cohesive
`engines/` modules rather than a catch-all adapter file. Split growing modules
near the repository's 400-line target; do not broaden into unrelated refactoring.

## Verification and stopping conditions

- Focused service tests cover engine/stage mismatch, paired batch count and
  partial failure, revision conflicts, per-slot regeneration, frozen settings,
  native sample formats, clipping warnings/derivatives, text/manual controls,
  invalid vectors, classifier evidence before synthesis, and no silent fallback.
- Test process crashes/timeouts/stop/restart and model-release ordering with
  fake child processes: at most one generation child, no live child after job
  finalization/service stop, preserved old audio and no silent job replay.
  Verify source pinning, migration, stale inputs, safe deletion and immutable
  Voice ID resolution survive both engines and source-project deletion.
- Run locked service Python tests, service JavaScript checks, real FastAPI /
  file-SQLite browser tests, wheel build and installed-wheel/runner smoke.
  Run affected repository regressions on the stable candidate. The unrelated
  Plotloom frontend suite is not a substitute for Voice Lab browser evidence;
  repeat broader gates only if shared code/packaging changes justify them.
- Real Spark cap: **three Stage-1 calls and six Stage-2 calls**, plus classifier
  invocations required by the description job. Create one paired Qwen/MOSS
  design; regenerate one slot and prove the sibling hash unchanged. Reuse one
  frozen generation from each creator through each reuse engine (four neutral
  calls), then one Chinese-description urgency take and one manual restrained
  frustration take from the chosen MOSS reference. No extra seed sweep.
- During that journey, select/publish, switch projects, refresh and restart;
  demonstrate pinned clone references and unchanged published Voice ID bytes.
  Record process exit, available-memory recovery, peak host/process/Torch
  measurements separately and mixed-engine serial order. Do not promise that
  Linux page-cache usage returns to an exact pre-run number.
- Technical acceptance requires valid retrievable output, correct persisted
  contracts, released processes and restored services, not a claim that every
  new voice sounds human. Check words/obvious defects with available tools;
  seek owner review only for a material perceptual decision or regression.
  License or resource blockers are reported before dependent deployment.
- One bounded independent review on the stable implementation; no parallel
  source writers or task creation during planning. Stop after the receipt and
  useful working lab. If a live criterion fails twice, preserve evidence and
  reassess its layer instead of expanding audition searches.

Excluded: Plotloom character/UI integration, gateway Voice ID lookup, new H3
or lip-sync trials, model training, human recordings, global GPU scheduling,
public authentication, automatic voice retirement, merge/push and director
contact. A later owner-approved handoff determines Plotloom consumption.

## Downloads cleanup · completed during planning

The owner authorized removing the local comparison packages. Nine directories
were moved, recoverably, to
`/Users/wjmao/.Trash/plotloom-voice-comparisons-2026-09-29.iYEnJN/`:

- `plotloom-voice-casting-2026-09-26`
- `plotloom-voice-reuse-2026-09-26`
- `plotloom-index-tts2-comparison-2026-09-28`
- `moss-vs-qwen-2026-09-28`
- `moss-d-refinement-2026-09-29`
- `moss-d-stage2-comparison-2026-09-29`
- `moss-d-chinese-emotion-2026-09-29`
- `moss-d-delivery-followup-2026-09-29`
- `moss-d-frustration-controls-2026-09-29`

Spark originals, reference audio, model installations, service-managed voices
and repository receipts/runners were not changed. Historical receipt paths
describe the original audition location; the local packages are no longer in
Downloads. Unrelated Downloads, including image-canvas qualification, remain.
