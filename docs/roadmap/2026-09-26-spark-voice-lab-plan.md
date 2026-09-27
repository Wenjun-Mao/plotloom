# Spark Voice Lab: functional synthetic casting MVP

**Status:** Proposed specialist-side implementation plan; not authorization to
implement, merge, push, or contact the Plotloom director. The owner chose a
private same-origin UI and generation API on Spark. Plotloom product integration
and the director handoff remain explicitly on hold. The per-candidate-direction
choice in step 1 is my recommendation and awaits the owner's answer; it is not
yet an approved requirement.

## Outcome and evidence

Turn the accepted [static Voice Lab](../voice-lab-prototype/README.md) into a
working way to design, generate, audition, compare, preserve, and explicitly
choose synthetic Mandarin voice candidates. The original four-candidate trial
used distinct written directions. The [Candidate A reuse trial](../verification/2026-09-26-voice-reuse-trial.md)
found a recognizable same-person voice across three new lines and two seeds,
while both urgent samples lacked urgency. Identity reuse is promising within
that bound; acting control is not established.

Success means a specialist can create a new casting round from the browser,
return after service restart to inspect exact unchanged audio and provenance,
choose a stable candidate reference, and try that reference on a new line.
Neither the choice nor a successful clone becomes a Plotloom character Voice ID
or a guarantee of emotional delivery.

## Boundary and approach

- Create a cohesive `services/qwen3_tts_voice_lab/` service in this specialist
  checkout. Serve the UI and private API from one Spark origin, reachable only
  through the owner's private network or SSH tunnel. Reuse the prototype's
  interaction language and comparison affordances; do not import its bundled
  example WAVs as live database records automatically.
- Keep model weights exclusively under `/home/wjmao/models/qwen3-tts/`. Pin
  the proven VoiceDesign and Base revisions, `qwen-tts` version, audio-prep
  algorithm, and deployment dependencies. Store the service, SQLite and
  generated media separately under `/home/wjmao/services/`; preserve the
  existing trial evidence. No Plotloom package, H3 gateway route, or ComfyUI
  graph change is part of this slice.
- Use one serial generation worker. Load the needed model on demand for a
  batch, release it afterward, and never stop/preempt H3, Qwen Image or other
  Spark services. The lab does not claim cross-service GPU scheduling; an
  overlapping heavy job or insufficient memory must fail visibly and safely.
  The operator guide must say when to defer lab work rather than hiding this
  resource boundary.
- Keep audition and generated audio until an explicit later retention/deletion
  policy is approved. Do not apply the H3 gateway's 72-hour/30-day cleanup to
  user-valued voice candidates. Provide storage visibility, but no automatic
  candidate deletion in this MVP.

An independent Spark service fits the specialist ownership and retention
boundary. Adding casting state to the H3 gateway would conflate a video job
transport with durable voices; implementing it inside Plotloom would violate
the current handoff hold and prematurely settle character-level authority.

## Contract and user journey

1. **Design a round (proposed).** Enter a shared Mandarin audition line and choose 2, 4,
   6, or 8 candidates. Give each candidate an editable voice direction; the
   UI may copy the shared brief into each field, but must show the exact
   direction that will be submitted. A blank candidate direction is rejected.
   The service records the exact per-candidate text, resolved random seed,
   language, model revision and generation parameters. It does not silently
   use an LLM to invent alternate directions. A new draft or regenerated
   direction creates a new round, never overwrites an existing WAV.
2. **Generate without ambiguous replay.** `POST` creates an immutable round
   and returns a round ID immediately. The worker advances explicit
   queued/running/completed/failed states and records each candidate as it
   completes. On crash/restart, preserve completed outputs and mark an
   interrupted in-flight generation for review; do not replay it silently.
   An intentional retry creates a new round or candidate attempt with new ID.
   Write audio to a temporary managed file, validate it, then atomically
   publish the file and database record; partial results remain visible as
   partial, never as a completed round.
3. **Preserve candidate identity.** Each immutable candidate has a stable
   `candidateId`, its original 24-kHz audio and hash, transcript, exact design
   instruction, seed, model/version, round ID, timestamps, and validity
   checks. Derive a separate 32-kHz mono PCM16 H3-ready WAV with its own hash
   and preparation version. If the source cannot meet H3's 1–10-second,
   2-MiB reference contract, keep it reviewable but label it ineligible; do
   not trim, stretch or silently replace it.
4. **Audition and compare.** Render dynamic saved rounds rather than hard-coded
   A–D cards. Preserve one-at-a-time playback, blind shuffle, revealable
   directions, two-candidate quick comparison, and candid loading/error
   states. Blind mode conceals labels/directions without changing the audio or
   candidate IDs. Do not claim loudness-controlled blind testing when no
   level matching is performed.
5. **Make selection meaningful.** Use an explicit action such as “选为复用参考”
   rather than “本页偏好.” It records a reversible, timestamped lab selection
   pointing to an immutable `candidateId` and enables a new-line reuse test.
   Selection changes never mutate candidate bytes or retroactively alter
   past clone trials. This lab selection is not Plotloom approval or a final
   product Voice ID.
6. **Test reuse on a new line.** For a selected candidate, create an immutable
   Base-clone trial with new Mandarin text and resolved seed, using the
   candidate's original audio and exact transcript. Show the resulting audio
   beside the reference, record its provenance, and ask separately whether
   identity, words and intended delivery worked. Do not infer urgency from
   punctuation or publish a performance score automatically.

The API should expose only these workflow resources (round creation/status,
candidate metadata/audio, selection history, and clone-trial creation/status).
Define exact paths and schemas in a concise ADR before implementation. Public
responses must not expose filesystem paths, model-internal prompts other than
the author's own directions, stack traces or credentials. Apply finite input,
upload and candidate-count bounds; reject malformed or mixed states rather
than coercing them.

## Ordered implementation checkpoints

1. **Contract and service skeleton.** Record the specialist/Plotloom boundary
   in an ADR; create a locked, independently deployable Python service with
   same-origin static assets, health/readiness, private-network binding and a
   small SQLite schema. Keep module responsibilities cohesive and avoid adding
   voice state to the H3 gateway.
2. **Generation and durable media.** Implement immutable rounds/candidates,
   the one-worker VoiceDesign adapter, atomic file publication, H3 derivative,
   restart reconciliation and bounded error codes. Test fake-model paths before
   using the real model. Preserve existing Spark trials and model files.
3. **Working browser journey.** Replace the prototype's disabled Generate
   control and fixed cards with API-driven rounds, progress, playback and
   compare. Add explicit lab selection and Base-clone trial only after
   immutable candidate retrieval works. Keep the accepted simple wording and
   remove prototype disclaimers rather than layering new status chrome.
4. **Deployment and verification.** Install on Spark as a private reboot-safe
   service, document reproduction/operations and recovery, and run one real
   multi-candidate round plus a selected-candidate new-line clone. Review the
   UI after restart from the private origin. Record hashes, statuses, model
   versions, timing and resource observations without claiming creative
   acceptance. Stop if other Spark generation work needs the GPU.

## Acceptance and non-goals

- Automated tests cover request bounds, 2/4/6/8 directions, seed recording,
  immutable candidate IDs/audio, derivative validity, blind/compare behavior,
  explicit selection/reselection, clone provenance, partial failure, restart,
  no silent replay, and no cross-service stop action.
- A real Spark journey proves a browser-created round yields playable audio;
  the same IDs, file hashes, selection and clone trial survive service restart.
  The generated H3 derivative passes the gateway's technical audio contract.
- The owner may review creative quality, but implementation acceptance does
  not assert that every candidate is good, that an urgent line sounds urgent,
  or that H3 will lip-sync every new dialogue shot.
- Out of scope: Plotloom character binding or production Voice IDs, gateway
  Voice ID lookup, human-voice import/consent, voice training, emotion-control
  claims, ASR/alignment, H3 video generation, bulk cleanup, public Internet
  access, and changing other Spark services.

**Stop condition:** Once the standalone lab is verified and its limitations are
recorded, return to the owner for review. Do not send the withheld Plotloom
handoff or merge/push specialist work until the owner explicitly releases that
hold and decides the product boundary.
