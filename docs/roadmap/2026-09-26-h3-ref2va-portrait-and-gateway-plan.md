# H3 Ref2VA portrait, gateway and Plotloom voice candidates · 2026-09-26

**Status:** Draft for review. Planning only; not authorization to change the
gateway, Plotloom, or deployed services.

## Outcome and evidence boundary

Provide a direct, one-step way to generate an H3 video from a reviewed first
frame and a short voice-timbre reference, while leaving the existing FL2VA
`from-image` and `from-text` contracts and defaults unchanged. Then let
Plotloom manage several auditionable Voice Candidates per character and select
one under a stable Voice ID. Repeated shots resolve that ID to an immutable
reference revision rather than requiring the author to find and upload the
same audio each time. Portrait feasibility and gateway transport come first;
Plotloom authoring is a later, separately owned product checkpoint.

The completed [Spark Ref2VA trial](2026-09-25-h3-voice-reference-trial.md)
used the INT8 ConvRot Ref2VA base model at 960×544, 8 seconds, 20
`res_multistep` steps and native 12/3 shifts. C1/C2 voices sounded like the
same person to the user; C2 had good lip-sync; the original C1 line was
off-screen. The user accepted one C1 medium-shot visible-speaking retake.
This is evidence for a narrow capability, not broad reliability, exact
waveform reuse, or any portrait resolution. Exact prompts, hashes, MP4s,
receipts and the user's review are retained on Spark under
`/home/wjmao/services/spark-comfyui/data/output/experiments/h3-ref2va-voice-2026-09-25/`.

The current gateway has one FIFO generation lane, direct
`POST /v1/video-jobs/from-image` and `/from-text` routes, a frozen
quality/resolution execution snapshot, and 72-hour video / 30-day job-input
retention. Its qualities `1/2/3/8` describe reviewed FL2VA sampling paths;
`quality=8` is Base-20, not a voice-reference switch. See
[ADR 0070](../adr/0070-h3-quality-resolution-contract.md),
[ADR 0050](../adr/0050-unified-h3-generation-contract.md), and the
[client guide](../operations/minimax-h3-gateway-client-guide.md).

## Ownership and integration boundary

| Owner | Delivers | Does not own |
|---|---|---|
| This H3 specialist task | Checkpoints A–C: Spark Ref2VA qualification, the gateway route/worker/persistence/renderer under `services/minimax_h3_gateway/`, gateway-scoped tests and ADR, deployment, Chinese colleague/operations docs, and an evidence-backed handoff. | Plotloom's character/Voice ID schema, authoring UI, production snapshot, or app-side transport. |
| `narrative-forge main` / Plotloom director | Checkpoint D: project-owned Voice Candidates and stable Voice IDs, selection revisions and retention, `src/plotloom/` transport/production provenance, `frontend/` authoring and review UI, Plotloom migration/ADR/tests, and integrated two-shot acceptance. | Spark model installation or gateway-owned FIFO/retention internals. |

The specialist may use an isolated gateway-source worktree while Plotloom's
checkout is active, but source ownership stays serial: no concurrent edits to
the same files, no mixed commits, and no gateway deployment presented as
Plotloom integration. The director can review the proposed interface while
A/B run; Plotloom source implementation waits for the versioned B/C handoff.

The cross-boundary contract is deliberately small. Plotloom resolves a stable
`voiceId` to one frozen candidate/revision and sends that candidate's audio
bytes with the first-frame bytes through the gateway multipart route. The
gateway returns its job ID and retains the submitted audio hash; it does not
look up a Plotloom character or voice. Plotloom joins that job ID and gateway
audio hash to its own frozen `characterId`, `voiceId`, selection revision and
candidate ID. The new route's admission receipt includes the audio SHA-256
so Plotloom can compare it with its locally computed candidate hash. A hash
mismatch or changed selection before admission fails closed rather than
silently switching the queued job's voice. Ordinary status need not repeat
the hash or expose candidate metadata.

Before D starts, the specialist hands over: exact gateway source revision and
deployed version; request/status/error examples and audio limits; retained
fixture hashes and Spark canary paths; objective verification and separate
human audiovisual review; supported resolution/duration boundary; and any
unresolved risks. The director verifies the handoff against the installed
gateway, then owns Plotloom integration and final product acceptance. The
specialist remains available for gateway/model defects without editing the
director-owned product paths.

## Checkpoint A — true-portrait feasibility before gateway work

1. Select or create one genuinely portrait 576×1024 C01 first frame with the
   same reviewed identity and a continuously visible speaking face. Review
   the still before spending an H3 run. Do not put a landscape frame in a
   portrait canvas with padding or silently crop away her face.
2. Freeze the portrait image, the accepted C01 voice-reference WAV, one short
   Mandarin line, prompt, seed, model hash, frame count and graph. Check that
   Plotloom/ComfyUI queues are free and memory headroom is adequate. Keep the
   current model installation, Qwen-Image, FL2VA gateway and retained trials.
3. Run one direct-ComfyUI Ref2VA canary at 576×1024 and the gateway's
   proposed five-second default request duration. Inspect the actual frame
   count/duration, full decode, native audio, portrait composition, complete
   line, same perceived voice, visible lip-sync, and absence of extra speech
   or subtitles. Human review is required; machine checks alone do not pass.
4. If the five-second result fails because speech is late or incomplete, do
   not reroll it blindly. Diagnose from the retained prompt/output, then one
   eight-second portrait diagnostic may separate duration pressure from a
   geometry/model problem. If five seconds passes and the proposed 5–8-second
   admission range is still wanted, run a bounded eight-second portrait
   capacity check before enabling that range. Stop for a new decision if
   portrait performance or memory remains unacceptable. No gateway
   implementation before this gate.

Acceptance for A: at least one reviewed true-portrait clip has an intact
first-frame identity, complete authored dialogue, recognizably matching C01
voice, acceptable visible lip-sync, correct 576×1024 geometry and native
audio; the ComfyUI job has a known terminal outcome and no unrelated service
or work was interrupted. A five-second failure is recorded rather than hidden
by a passing eight-second diagnostic.

## Checkpoint B — explicit, bounded gateway capability

Implement only after A passes, using one serial source owner and a tracked
gateway-source branch/worktree coordinated with Plotloom main. Do not live-patch
the deployed source as the sole authority or edit Plotloom's active dirty
checkout. Add a concise ADR for the new public and persistence contracts.

- Add one direct route, proposed
  `POST /v1/video-jobs/from-image-with-voice`. JSON supplies downloadable
  `sourceUrl` and `voiceSourceUrl`; multipart supplies `image` and
  `voiceAudio`. Do not add a two-step public asset API or mix URL and file
  input styles in one request. Require one first frame and one audio
  reference; end-frame conditioning and T2V with a voice reference are out
  of scope.
- Treat this as a distinct `inputMode=image_voice` with a fixed, reviewed
  Ref2VA Base-20 execution path. The route does not accept caller-selected
  FL2VA `quality` values; status may report resolved `quality=8` alongside
  `inputMode=image_voice` so the two paths are never conflated. The frozen
  job snapshot binds model and renderer identity, recipe, resolution, frame
  count, seed, prompt, reference SHA-256, and prepared input names. Dispatch
  reads only the snapshot, not a mutable catalog lookup. The creation receipt
  returns the reference SHA-256 for the caller's provenance check; ordinary
  status stays concise.
- Proposed admission is optional `durationSeconds`, default five, with an
  initial 5–8-second range at only 960×544 and 576×1024. This is a bounded
  **technical admission range**, not a claim that every intermediate duration
  or prompt is creatively qualified. Enable the portrait range only after A
  establishes a reviewed five-second result and bounded eight-second capacity;
  if either fails, narrow the admission contract before implementation. Do not
  expose other resolutions or 9–15 seconds based on these trials. Existing
  FL2VA routes keep their optional five-second default and 5–15-second range.
- Admit a short, bounded, decodable voice-reference audio file and normalize
  it once to the tested ComfyUI input form. The initial public audio format,
  byte and duration limits must be fixed in the ADR and rejection tests from
  a preflight of the accepted WAV; no open-ended media ingestion or silent
  trimming. Store a private job-to-audio binding, not a fake image asset or
  reusable public voice library. On partial admission failure, remove newly
  unreferenced files. Do not return audio bytes, source URLs, prompts, or
  private paths in ordinary status responses. Gateway jobs identify the exact
  audio by immutable content hash; they do not own or resolve Plotloom Voice
  IDs. Direct audio remains usable by colleagues and for controlled trials.
- Reuse the existing durable FIFO worker, unknown-submission behavior,
  cancel/status/output routes, shared H3/Qwen generation serialization,
  managed output transfer and cleanup. Audio input must remain available
  while its job can execute, then follow the existing bounded input-retention
  horizon; output expiry remains 72 hours and job records remain 30 days.
  Existing FL2VA requests and queued snapshots remain executable without a
  migration reinterpretation.
- Document that the audio is a **timbre/delivery reference**, not exact
  waveform reuse or a guarantee that arbitrary text will be spoken
  perfectly. Keep dialogue text in the explicit prompt. Do not introduce a
  separate dub/lip-sync stack, automatic voice identification, or an
  implicit fallback to another model.

Acceptance for B: strict JSON/multipart admission and rejection tests,
frozen-snapshot/restart/cleanup tests, tests proving the existing paths use
zero voice bindings and the new path uses exactly one,
and renderer graph assertions pass; the existing gateway and Plotloom
transport tests remain green. Deploy one isolated live gateway canary using
the reviewed portrait frame and voice reference. It must pass queue, status,
output, full-decode and human audiovisual review without altering the old
route's behavior. Record secret-free hashes and exact source revision.

## Checkpoint C — gateway documentation and Plotloom handoff

Update the Chinese Bruno-only colleague guide and H3 operations/reproducibility
manual with the new route, supported inputs, tested settings, limits, sample
request, retention and caveats. Hand the public contract, source revision,
Spark evidence, Voice Candidate design, and unresolved quality boundaries to
`narrative-forge main` before D begins. Document that Plotloom owns the stable
Voice ID and candidate lifecycle, whereas the gateway owns only a frozen
per-job audio input; the two retention policies must not be conflated.

## Checkpoint D — Plotloom Voice Candidate design and authoring

This is a **separate Plotloom-owned implementation checkpoint**, not a
side-effect of deploying B. Coordinate a clean, scoped checkout
with `narrative-forge main`; do not edit Plotloom's active dirty checkout or
claim that a gateway canary authorizes product integration. Record the durable
identity, selection, media-currentness and retention decisions in a Plotloom
ADR before source changes. Update Plotloom's authoring and operations docs
when this checkpoint is implemented.

- Keep three distinct identities: canonical `Character ID` says who speaks;
  immutable `Voice Candidate ID` identifies an imported reference clip; stable
  project-scoped `Voice ID` is the character's selected voice slot. A Voice
  ID resolves to one selected candidate and an incrementing immutable
  selection revision. Replacing the candidate advances the revision without
  silently changing prior jobs. Candidate audio bytes and content hash are
  immutable; editable labels/review notes are not generation inputs.
- Start with user-imported, short, decodable audio; keep source/provenance,
  language, duration, label and review notes visible. Generated/TTS candidates,
  automatic speaker recognition and a global shared voice marketplace are
  excluded. Define Plotloom-owned retention for selected and previously used
  candidates independently of the gateway's 72-hour output / 30-day job
  retention; a referenced candidate must not disappear merely because a
  gateway job expires.
- Let the author import multiple candidates for a character, play and compare
  them, then explicitly select, replace or archive. An audition can use the
  same short line and reviewed shot for meaningful A/B comparison. Selection
  is a human decision, not an automatic voice-match score or storyboard
  Approval. Reject accidental selection of a candidate belonging to another
  project/character; define the explicit reassignment path if needed later.
- At video admission, resolve `Voice ID` to its candidate and revision once;
  freeze `characterId`, `voiceId`, selection revision, candidate ID and audio
  SHA-256 in Plotloom's production/job provenance. Send the resolved audio to
  B's one-step gateway route. The gateway need not know Plotloom's voice
  registry, and a mutable selection must never be re-resolved for a queued
  job. Missing, archived or mismatched voice selection blocks only the
  voice-controlled path; existing FL2VA authoring remains available.
- Preserve old clips and their exact voice provenance when selection changes.
  Surface an explicit review-needed/currentness reason for clips made from an
  older selected revision; do not silently relabel, delete, or automatically
  regenerate them. Keep dialogue text owned by `DialogueCue`. Review perceived
  voice consistency across distinct shots and lip-sync separately when a
  speaker is visible.

Acceptance for D: two candidate imports, playback/comparison, deliberate
selection and replacement, stable Voice ID with advancing revision, refresh
and restart persistence, scoped retention and deletion protection, frozen
queued-job provenance, and a two-shot human review showing the intended same
character/voice without asserting perfect cloning. Tests cover missing/stale
selection, cross-character misuse and old-clip review-needed behavior. No
audio bytes, credentials or private source URLs leak through ordinary status.

## Stop conditions and exclusions

### Next-plan clarification — specialist handoff, 2026-09-26

The specialist reports user agreement to include reviewed Voice Candidates /
stable character Voice IDs and post-generation speech evidence in the next
Plotloom plan. This records planning scope, not implementation completion or
permission to adopt an experimental reference as a canonical voice.

- **Current capability:** neither Plotloom nor the gateway has a Voice
  Candidate generator or library. The gateway accepts a supplied per-job WAV;
  it does not design, clone, select or persist a reusable Voice ID.
- **Trial provenance:** the specialist reports that C1, C2 and portrait trials
  reused an eight-second mono 32 kHz WAV manually extracted from the earlier
  director-reviewed C original H3 clip. It was explicitly not adopted as a
  canonical voice asset. Evidence pointers are ADR 0090 on specialist branch
  `codex/h3-ref2va-gateway` and Spark's
  `/home/wjmao/services/spark-comfyui/data/output/experiments/h3-ref2va-voice-2026-09-25/README.md`.
  These are specialist-provided pointers, not a new local verification.
- **Plotloom ownership:** candidate provenance, human review, selection
  revisions and stable character voice identity remain provider-neutral
  product responsibilities, distinct from gateway inference (checkpoint D).
- **Separate next-plan workstream:** retain post-generation ASR and alignment
  evidence comparing actual speech, timing and unexpected words against
  canonical `DialogueCue`. Preserve transcript uncertainty and manual review;
  evidence must not rewrite canonical dialogue or automatically accept media.
  Choose the ASR/alignment implementation and acceptance criteria in a scoped
  follow-up plan; no service choice or implementation is made here.

Stop before source changes if A does not pass or if Plotloom needs the H3
queue. Never replay an uncertain submission. Preserve current models,
experimental outputs and user-valued assets; no setup cleanup without
explicit confirmation. No broad seed/resolution/duration sweep, voice-clone
guarantee, speaker recognition, authentication redesign, unrelated gateway
refactor, or Plotloom UI work outside D is included. Review failure
concentration before loosening validators or adding fallback behavior.

## Contract choice to confirm after portrait qualification

The working recommendation is optional `durationSeconds`, default five, with
only 5–8 seconds at the two named resolutions once A's portrait five-second
review and eight-second capacity check pass. This is a middle ground between
an awkward exact-tuple allowlist and the untested full 5–15-second FL2VA
range. Confirm or narrow it against A's actual results before editing the
gateway API or persistence contract; no higher-resolution or longer-duration
Ref2VA claim is implicit. This choice does not change the existing routes.
