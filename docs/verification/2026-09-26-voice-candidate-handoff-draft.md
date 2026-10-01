# Synthetic voice candidates: specialist evidence and withheld Plotloom handoff

**Status:** Draft for later handoff. This is evidence and a question list, not an
approved Plotloom implementation plan or permission to contact its director.
The owner asked on 2026-09-26 to hold further director instructions until the
specialist-side choices are settled.

## What the specialist has established

- The gateway's accepted [Ref2VA contract](../adr/0090-h3-ref2va-per-job-voice-reference.md)
  consumes one frozen 32-kHz mono PCM16 WAV per image-and-voice job. It does not
  generate voices, manage Voice IDs, guarantee exact spoken words, or perform
  lip-sync measurement. Its admitted bounds are 1–10 seconds and at most 2 MiB
  for the reference, with 960×544 or 576×1024, 5–8-second video jobs.
- The earlier reference was an eight-second WAV extracted from a reviewed H3
  clip (SHA-256 `1982764d633299cb52d3dcf7c2cf1e068cfa511b68c7bbdf72665fdcaa55de4f`).
  It worked in the bounded two-shot and gateway canaries but is not a managed
  character voice asset.
- On Spark, an isolated `qwen-tts==0.1.1` trial generated four fictional
  Mandarin female voice candidates with the same audition text. Model:
  `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`, weights SHA-256
  `391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522`.
  Model files reside under `/home/wjmao/models/qwen3-tts/`; the environment and
  originals are under `/home/wjmao/services/qwen3-tts-trial/`. The original
  24-kHz float WAVs were preserved, with separate 32-kHz mono PCM16 derivatives.
  Full instructions, seeds, file hashes and measured audio properties are in
  `/home/wjmao/services/qwen3-tts-trial/experiments/2026-09-26/manifest.json`.
- The owner preferred candidate A among A–D, while explicitly noting possible
  first-listen bias, and said all four synthetic samples sounded cleaner than
  the extracted H3 reference. This is a subjective audition, not a controlled
  source-quality or model-quality measurement.
- Candidate A's H3-ready WAV is 5.04 seconds, SHA-256
  `a70bd1814953a7c9c9826368bd240408e4217b2f47e9d4cbc4e7da5c7b09e52f`.
  It was tested on the previously reviewed C1 visible-speaking and C2
  lighthouse shots, retaining their first frames, lines, seeds, prompt form,
  model and Base-20 recipe. Both eight-second outputs completed, decoded fully,
  and contain H.264 960×544 plus AAC 32-kHz audio. Output SHA-256 values are
  C1 `c11c0d6d545cbffaf5bda9f9d4aa7650f4da2ec46e2caeda2ba0a240450c7a05`
  and C2 `68bfc9f1f80c5481e4d724ecf00d660885f26bf074142e60e5bb7a8cd0869fa8`.
  The owner reviewed these two clips and replied “all good.” Preserve that as
  bounded acceptance of the pair, not separate numeric scores or broad
  reliability proof. Spark receipts and exact review wording are under
  `/home/wjmao/services/spark-comfyui/data/output/experiments/h3-ref2va-qwen-voice-a-2026-09-26/`.
- The Qwen Image service was stopped only for model setup/generation and then
  restored; its `/health` returned `ok`. No Plotloom product code or gateway
  contract changed during this voice-casting trial.
- A subsequent [Base-clone trial](2026-09-26-voice-reuse-trial.md) generated six
  technically valid Candidate A reuse samples across three new Mandarin lines
  and two seeds. The owner judged that all six retain Candidate A's identity,
  while both urgent samples lack urgency. This is bounded cross-line identity
  evidence, not a general continuity guarantee or accepted acting control.

## Likely Plotloom ownership when handoff is authorized

These are candidate responsibilities to resolve with the director, **not** an
instruction to begin implementation now.

1. Own a character-scoped Voice Candidate library: immutable audio bytes/hash,
   source kind, model/version/seed or import provenance, transcript/language,
   preparation lineage, duration and technical validity. Preserve source audio
   separately from the gateway-ready derivative. Imported human voices need a
   permission/provenance policy; the initial scope is synthetic voices.
2. Make audition and selection explicit. A stable Voice ID or selection record
   should point to an approved candidate revision; changing a descriptive
   prompt must not silently regenerate or replace that voice. Show comparison,
   approval, replacement/revocation and currentness in the character workflow.
3. Keep identity, performance and dialogue separate. The selected reference
   guides timbre; canonical Dialogue Cues and shot prompts own words and acting
   direction. Do not infer exact transcription or lip-sync from the reference.
4. Freeze the selected candidate ID, audio hash and prepared bytes into each
   video production snapshot. Upload that exact WAV per job through
   `POST /v1/video-jobs/from-image-with-voice`; the gateway deliberately has
   no reusable Voice ID resolver. Plotloom must retain its own selected audio
   independently of gateway input/output expiry and must not silently fall
   back to ordinary FL2VA or switch voices on retry.
5. Review generated dialogue as an audiovisual result: same-person voice
   across shots, intended words, visible mouth timing, extra speech and
   subtitles. A future ASR/alignment pass may supply evidence and timing, but
   must not automatically grant creative approval.
6. Cover stable selection, revision/currentness, exact audio handoff, restart,
   missing/stale reference, cancellation and unknown-dispatch behavior in
   tests. A technically successful job must remain reviewable, not
   auto-approved.

## Specialist update · 2026-09-30 (still withheld)

The multi-engine implementation separates creation (`qwen_design`,
`moss_design`) from reuse (`qwen_base`, `index_base`) in the named-project Lab.
Qwen remains neutral reuse default; Index offers Chinese-description
interpretation and manual strengths. Actual vectors are evidence, not acting
approval. Short-lived engine processes replace resident inference in the API.
Existing Voice IDs remain independent of creator/reuse selection and survive
the additive migration.

The [deployment receipt](2026-09-30-voice-lab-multi-engine-deployment.md) records
the exhausted nine-call cap and one unresolved CUDA OOM in Qwen → Index neutral
reuse. The separately authorized
[controlled retest](2026-09-30-voice-lab-cuda-neutral-retest.md) now passes that
path without rewriting the initial batch. The later
[reliability closeout](2026-09-30-voice-specialist-reliability-closeout.md)
passes a fresh nine-call workflow and the exact neutral path both cold and
after H3 with Qwen-Image running. One real H3 job consumes the exact published
bytes; a real idle Lab restart preserves project/trials and 54 WAVs.
General co-resident concurrency and new creative acceptance remain unproven.
This is still not authorization for director contact or handoff.

See the [current pipeline report](../../services/qwen3_tts_voice_lab/docs/audio-pipeline-report.md)
and [specialist plan](../roadmap/2026-09-29-voice-lab-multi-engine-plan.md).
This note is not an instruction to the director. Plotloom still needs a later
approved Voice ID import/character binding and frozen-media contract; none is
implemented by the Lab. No universal emotion presets were accepted.

## Integration-ready facts, not instructions to begin

Entry point: [Voice Lab README](../../services/qwen3_tts_voice_lab/README.md).
Its [pipeline report](../../services/qwen3_tts_voice_lab/docs/audio-pipeline-report.md)
explains author behavior; [reproduction/operations](../../services/qwen3_tts_voice_lab/docs/reproduction-and-operations.md)
pins models, environments, licenses, deployment and recovery. Follow
[ADR 0097](../adr/0097-published-voice-performance-takes-and-shared-admission.md)
for current managed shared admission. H3, Qwen-Image and all Lab synthesis now
share one durable FIFO; direct backend clients/unrelated GPU services remain
outside that guarantee. ADR 0096 remains historical evidence of the prior
operator-serial boundary, not the current managed dispatch design.

| Concern | Existing contract | Future Plotloom ownership |
|---|---|---|
| Resolve an identity | `GET /api/voices/{voiceId}` returns immutable metadata, transcript, model/engine snapshot, source/H3 hashes | Import provenance and bind an explicit selection to a character |
| Download audio | `GET /api/voices/{voiceId}/audio?kind=source` or `kind=h3` | Verify bytes against the matching hash and retain both in Plotloom storage |
| Reuse/acting | Published `voiceId` + gateway `POST /v1/voice-takes`, `engineId`, exact words, optional `seed` and `delivery`; immutable `takeId`, status/list and verified source/H3 download | Bind a selected take to a canonical Dialogue Cue, retain audio/provenance and make audition/approval explicit |
| Video input | Gateway multipart `POST /v1/video-jobs/from-image-with-voice`: `image`, `voiceAudio`, `prompt`, `resolution`, `aspectPolicy`, optional seed/duration | Send frozen verified audio bytes; never send a Voice ID expecting the gateway to resolve it |
| Failure/retention | Durable voices/takes have no TTL; confirmed terminal Take deletion is explicit. Unknown dispatch/unreleased process holds the shared lane, never replays. Gateway media expires after 72 hours and job records after 30 days | Own production copies, unknown-dispatch handling, revocation/currentness and retention |

Reuse controls are `{"mode":"none"}` (Qwen or Index),
`{"mode":"text","description":"坚定、果断、时间紧迫"}` (Index), or
`{"mode":"manual","vector":[0,0.25,0,0,0,0,0,0]}` (Index). The latter
is one explicitly reviewed restrained-frustration experiment, not a default
emotion preset. Index returns actual classification/effective strengths;
successful synthesis must not become automatic acting approval.

The newly published technical ID `voice_5689e99835494d2f8024485523c4dbf6`
demonstrates the byte handoff; it is not the owner's preferred original MOSS D
or an instruction to install a character selection in Plotloom.

Specialist completion covers engine adapters, Lab projects/candidates, review
controls, immutable publication and performance takes, shared managed dispatch,
exact gateway input and operation evidence. Project-scoped clone trials remain
temporary auditions, not the production Take contract.
Plotloom character binding, production snapshots, author-facing approvals,
dialogue-take selection and its own asset retention remain director-owned
**future work**, requiring the owner's release of the hold.

## Specialist closeout · 2026-10-01 (still withheld)

The [four-checkpoint receipt](2026-10-01-published-voice-takes-shared-admission.md)
records deployed published-ID takes, the authenticated gateway facade, exact
audio-byte handoff and one managed cross-service generation owner. The
[Chinese client guide](../../services/qwen3_tts_voice_lab/docs/voice-takes-client-guide.md)
specifies the current public API. There is no synthesis hidden inside video
creation: create/inspect/audition a take, download its verified H3 WAV, then
upload those bytes to the existing image-with-voice route.

The capped live proof used two Index takes and one H3 job, followed by GET-only
completion and idle restart checks. Three published identities and 60 managed
WAVs survive restart unchanged. The technical MOSS publication above is still
not original MOSS D. No new acting approval, universal reference-strategy
default, exact-waveform promise or old-CUDA root-cause claim follows.

When handoff is authorized, the director needs to design character→Voice ID and
Dialogue Cue→Take selection, revision/hash currentness, retained production
audio and explicit reference strategy. Freeze the exact selected bytes and
matching words in the production snapshot; do not silently switch engine,
voice or delivery after a failure. These remain later Plotloom decisions, not
instructions or code changes delivered here.

## Decisions still open for an authorized handoff

- Plotloom's author-facing default between an identity audition and an explicit
  dialogue-specific take. Both are available; the matched shot favored the
  performance take, but no universal default was demonstrated. A take must not
  replace identity implicitly.
- Plotloom's author-facing delivery/selection workflow and review gates.
- Whether future comparisons should loudness-match; current blind listening
  hides identities but is not a controlled study.
- Plotloom-side retention and consent policy, and exact selection/currentness
  rules, must be decided before proposing a product schema.

**Handoff rule:** Do not send this draft to the Plotloom director, merge it to
main, or represent candidate A as a canonical Voice ID until the owner releases
the hold and the open decisions are reviewed.
