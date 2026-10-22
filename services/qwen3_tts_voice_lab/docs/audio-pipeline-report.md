# Voice Lab audio pipeline and intended use

Scope: the specialist Spark Lab, separate from Plotloom authoring.
[ADR 0209](../../../docs/adr/0209-voice-lab-independent-engines-and-delivery.md)
defines the multi-engine contract; [ADR 0212](../../../docs/adr/0212-published-voice-performance-takes-and-shared-admission.md)
adds published-identity takes and shared admission.

## Two separate decisions

Creating a compelling voice and preserving it while delivering new lines
are different problems:

```text
Project + shared audition line + explicit candidate directions
  ├─ Qwen VoiceDesign ─┐
  └─ MOSS Generator ───┴─ native identity recordings
                           ↓ listen / blind shuffle / compare / select
                         frozen reference + transcript + new words
                           ├─ Qwen Base: neutral reuse
                           └─ IndexTTS2: none / Chinese direction / manual strengths
                           ↓ temporary project-owned clone trials
                         explicit Publish of selected creation recording
                           ↓ immutable Voice ID + source/H3 copies
                         Voice ID + exact dialogue + delivery
                           ↓ durable Take ID + native/H3 WAV
                         audition / select / download for H3
```

All four creation/reuse combinations are supported by the contract and tests.
The initial 2026-09-30 matrix retained a Qwen → Index CUDA failure; a controlled
image-service pause subsequently passed that path. The separately authorized
[closeout](../../../docs/verification/2026-09-30-voice-specialist-reliability-closeout.md)
now passes a fresh nine-call matrix and the exact neutral path before and after
H3, with Qwen-Image running. It also verifies publication, exact H3 consumption
and idle Lab restart. These are bounded serialized technical results, not
broad memory/concurrency reliability or new human identity/acting approval.
The [deployment receipt](../../../docs/verification/2026-09-30-voice-lab-multi-engine-deployment.md)
retains the initial failure rather than retroactively claiming that batch passed.
Same-person identity,
pronunciation, naturalness and acting are separate judgments.
A technically valid WAV is not creative approval.

## Author workflow

1. Open [Voice Lab](http://100.64.35.71:8897/) and create/choose a named project.
   Save its shared brief and audition line. Keeping the line constant helps
   compare voices without different words becoming a confound.
2. Select Qwen, MOSS or both; enter one explicit direction per requested slot.
   Count means **per engine**; total is also shown. No hidden LLM invents
   variations. Paired slots share input binding but independent IDs/failures.
   Regenerate one slot without changing siblings.
3. Listen, blind-shuffle/hide design information, and compare two recordings.
   Blind mode hides engine identity; it is not loudness-matched or a controlled
   preference study.
4. Select a current creation recording. Choose Qwen Base (neutral default) or
   Index for **复用测试**. Enter new words separately from acting direction.
   Admission copies and hash-pins the exact reference and transcript.
5. Index offers none, Chinese description, or eight manual strengths.
   Description mode shows actual classifier/effective strengths. Copy them
   to manual controls and adjust visible components if useful. No overall
   intensity slider or hidden normalization.
6. Publish the selected creation recording when ready and copy its `voiceId`.
   Clone trials do not replace the identity or automatically publish a voice.
7. In **台词表演**, select that published Voice ID, exact words, engine and
   optional delivery. Each generation creates a new independent Take ID.
   Listen, download native or H3 WAV, or copy controls as a new draft.
   The identity/take choice survives refresh; opening the page starts nothing.
   Casting projects may be deleted without deleting these assets.

Index's pinned order is 快乐/愤怒/悲伤/害怕/厌恶/低落/惊讶/平静.
Each value is a finite strength 0–1, not a sum-to-one probability contract.
`emo_alpha=1.0`. The classifier's output is a proposal, not proof of successful
acting. Qwen Base rejects unsupported emotion controls.

## Listening findings, not universal presets

The owner and a Chinese-speaking friend slightly preferred MOSS creation in a
small comparison. Original MOSS D remained preferred over refinements, but was
not perfectly natural. Neutral Qwen/Index reuse both preserved its identity
well enough that no reliable winner was heard.

Chinese-description Index urgency and reassurance passed bounded listening.
Fear/surprise numeric control sounded anxious, not decisive urgency.
Calm-heavy frustration missed the target; anger-heavy control was too angry;
explicit anger `0.25` passed restrained frustration twice.
These [captured observations](../../../docs/roadmap/2026-09-29-voice-lab-multi-engine-plan.md)
are not statistical rankings or guarantees for a new voice.

## Identity and media contracts

| ID | Meaning |
|---|---|
| `projectId` | Mutable named workspace |
| `candidateId` | Stable independently editable creation slot |
| `generationId` | Frozen creation attempt; current pointer may be replaced |
| `trialId` | New-line attempt with pinned reference, words and delivery |
| `voiceId` | Explicit immutable publication independent of the project |
| `takeId` | Immutable line-specific performance anchored to a published Voice ID |

Native WAV bytes stay unchanged: Qwen/MOSS 24 kHz, Index 22.05 kHz.
Subtype, hash, duration, sample peak and warnings are recorded.
A separate 32-kHz PCM16 H3 copy records deterministic resampling and any gain.
It does not trim, time-stretch or repair already-clipped source audio.
H3 publication requires 1–10 seconds and at most 2 MiB prepared audio.

Failed regeneration keeps old audio. Success switches only that slot before
removing the older unpublished WAV. Edited design makes old audio noncurrent.
Published copies survive regeneration, deletion and restart; repeated Publish
for one generation returns the same ID. There is no published-voice retirement
API or media-retention timer in this slice.

## Runtime and H3 boundary

One lightweight Lab execution worker supervises **one short-lived model process per
job**, using separate Qwen/MOSS/Index environments. The gateway grants execution
from one durable lane covering all Lab entrypoints plus H3/Qwen-Image. No four-model warm cache.
Exact package/file inventories and runtime fingerprints prevent substitution.
Process exit is the model-release boundary; cold loading adds latency.
Restart interrupts dispatched work, never replays it; known unstarted outbox entries
stay queued. Queue counts, observed
phases and elapsed time are shown without fabricated percent or ETA.
The lane releases only after known terminal status and child-group release proof.
Lost execution acknowledgements are queried, never resubmitted. Uncertainty
blocks later work. Memory/ComfyUI checks remain supplementary; direct backend
clients and unrelated GPU services are outside managed admission.

See [reproduction and operations](reproduction-and-operations.md) for ARM64
dependencies, licenses, migration and recovery.

The H3 video creation endpoint takes audio bytes, not Voice/Take IDs. The new
gateway [take facade](voice-takes-client-guide.md) creates/downloads durable
audio separately; it does not hide TTS inside video creation. The Ref2VA boundary
remains one image plus a mono 32-kHz PCM16 reference, 960×544 or 576×1024,
requested 5–8 seconds. The closeout verified one real job with exact published
reference bytes; it adds no gateway Voice ID lookup.
A reference guides identity; it is not an exact soundtrack/lip-sync guarantee.
Review words, mouth timing, extra speech and subtitles separately.

Later Plotloom work must bind a Voice ID to a character, import/hash-pin audio
in Plotloom-owned storage, freeze it in production snapshots, and distinguish
identity from dialogue-specific delivery. The matched owner review favored the
urgent line-specific Index take for that shot; this is not a universal automatic
default or exact-waveform dubbing claim.
The [handoff note](../../../docs/verification/2026-09-26-voice-candidate-handoff-draft.md)
is held; no director message/integration is authorized here.

## Source map

[API](../src/plotloom_voice_lab/app.py) ·
[engine registry](../src/plotloom_voice_lab/engines/catalog.py) ·
[supervisor](../src/plotloom_voice_lab/engines/process.py) ·
[media preparation](../src/plotloom_voice_lab/media.py) ·
[publication](../src/plotloom_voice_lab/voices.py).
