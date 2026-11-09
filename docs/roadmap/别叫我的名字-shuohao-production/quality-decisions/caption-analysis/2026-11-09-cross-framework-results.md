# H3 cross-framework caption comparison

The bounded six-cell investigation is complete. Dialogue overlays appeared in
one of two current-configuration Comfy clips and in none of the four BF16 clips.
Both BF16 paths produced caption-free pictures in this sample, so these results
do not establish an advantage for vLLM-Omni over Comfy. One Comfy BF16 clip's
source speech remains unresolved. No cell is certified as a fully usable or
owner-accepted production clip.

The [reviewed plan](2026-11-09-cross-framework-comparison-design.md) used two
retained seeds in one scene, the unchanged historical prompt, three ordered
references and separate guides at frames 0/60/120. Each original output is
960×544, 260 frames at 24 fps, with native stereo audio. The 10,300 ms request
aligns to 10.833 seconds of video. No quality rerolls, source rewrites, picture
repair or audio replacement were used. Execution order was C1, A1, B1, B2, A2, C2.

## Results and interpretation

| Arm | Executed recipe | Intended contrast |
| --- | --- | --- |
| A | Current Comfy INT8 ConvRot DiT, NVFP4 Qwen and RES20 | Fresh current-configuration control |
| B | Comfy full BF16 logical DiT/Qwen weights, Euler20, shifts12/3 | A→B changes the configuration package |
| C | vLLM-Omni with common logical BF16 weights and its own pipeline | B→C compares the whole native path |

| Cell | Blind ID | Full native decode | Dialogue overlays | Unhinted native-AI source speech |
| --- | --- | --- | --- | --- |
| A1 | clip-06 | Passed | Present | Complete phonetic clause recovered |
| B1 | clip-02 | Passed | None observed | Complete phonetic clause recovered |
| C1 | clip-04 | Passed | None observed | Complete phonetic clause recovered |
| A2 | clip-05 | Passed | None observed | Complete phonetic clause recovered |
| B2 | clip-01 | Passed | None observed | **Uncertain**, including supplemental review |
| C2 | clip-03 | Passed | None observed | Complete phonetic clause recovered |

A1 has bottom-centered Chinese dialogue overlays and smaller malformed Latin
lines at frames 133–177 and 200–256, inclusive. Adjacent frames 132/178/199/257
are clear. Physical shelf/package/banknote printing was assessed separately.
No screen-space dialogue or speech bubbles were observed in the other five
complete frame sets.

For seed1, both B and C had no observed captions where A1 did. For seed2, all
three pictures had no captions observed, while B2's speech could not be qualified.
This is a descriptive paired result, not a causal finding. Two seeds in one scene
do not establish a population failure rate, a reliable remedy or a framework
ranking. Frames and clauses are not additional independent trials.

The evidence supports retaining Comfy as the working production path and
considering a separately authorized replication of the BF16 configuration
package across other caption-prone scenes. A framework migration is not justified
by this comparison alone. No replication, migration or production selection is
started by this recommendation. SGLang, LightX2V and Diffusers remain the
researched alternatives documented in the plan, not extra render arms.

## Assessment coverage and limits

Fresh blinded GPT-6.1 Sol / High reviewers inspected all 260 consecutive native
frames per clip, in 33 contact pages at original detail. They fixed direct
observations before viewing the three references or learning the arm/seed
mapping. The caption finding covers all 1,560 frames; its experimental unit
remains the six clips.

All six also played to the end in the real in-app browser. Playback was muted;
B2 reported three presentation-frame drops and the other five reported zero.
This establishes browser playback, not human hearing or continuous human
perceptual review. Every native file separately passed full decoding, geometry,
frame-count and non-silent stereo-channel checks, with audio/video duration
difference within one video frame.

Audio-only Qwen2.5-Omni-7B received waveform features with no images, script,
ASR or previous responses. Readiness first distinguished an old retained clip's
spoken clause from a zero-waveform silence control, with normal explicit EOS.
The failed earlier combined-AV readiness attempt remains failed. The final
batch reused immutable weights/processor only; each generation used fresh
conversation/cache state. Source words were compared after unhinted responses.

The source clause is “王昊说明早还不上，就把聊天记录给一起干活的人看。”
Five primary responses recover that phonetic clause; 王昊/王浩 are homophones,
so spelling cannot be certified by hearing. B2's primary response contradicted
itself about speech and omitted a transcript. One neutral full-waveform
clarification returned “[unclear].” Both responses are retained; B2 remains
uncertain and cannot count as a usable-clip success.

Scene/action and speech quality have narrower support than the caption finding:

| Scope | Supported observations | Remaining uncertainty |
| --- | --- | --- |
| A1/B1/C1/C2 | Clerk raises gaze; later masked man holds clear coin/blue-paper bag; mask and bag continuity observed | Specific bag gaze, mutual eyeline and shared spatial relationship inferred |
| B2 | Bag/arm enters the clerk shot before the masked-man shot | Deliberate bag gaze, arm identity across cut and exact relationship inferred |
| A2 | Man rises into the clerk's foreground, supporting shared interior placement; later holds bag | Precise bag gaze and mutual eye contact unproven |
| All six audio reviews | Five recover the full phonetic clause; B2 unresolved | Reliable speaker attribution, precise lip synchronization, subtle cutoff/ambience and stereo spatial quality unqualified |

The man's nose and mouth stay masked whenever clearly visible. That limits
visual speaker attribution. Reduced-resolution video-only model reviews provide
supporting temporal descriptions, not primary caption proof. A1's video response
hit its token cap without EOS and invented additional cuts; it is explicitly
partial/unqualified. No human listening or owner creative acceptance is claimed.

## Controlled inputs and qualified differences

The frozen raw prompt, prepared pixel bytes/order/guide times, geometry, logical
weights, external B/C initial-noise values, packed semantics and Euler boundaries
are pinned. Each B/C arm ran its own tokenizer, vision/language encoder, media
preparation, denoiser and decoder; C did not consume B's embeddings or encoded guide tensors.
Exact vendor logical-weight audits cover 535 DiT and 902 Qwen tensors, plus video
VAE and normative FP32 audio weight-norm folding. Full-geometry first evaluations
and independent bit-exact first-update replay passed. All four full B/C traces
retain 20 evaluations, finite predictions and frozen native model-time checks.
Both seeds' consumed target/condition-noise controls were verified.

Effective conditioning and arithmetic are not identical. B uses the image-VAE
posterior mean and GPU FP32 normalization; C samples with seed42 per image,
rounds raw latents through FP16 and normalizes on CPU FP32. Native encoder,
network-ingress/egress precision and model-time rounding differ. Tiny vision
towers reproduced the original features and located the first divergence at
native FP32 RoPE arithmetic; amplification at three final language-feature rows
remains unlocalized and is not declared harmless. These are whole-path
comparisons. They cannot isolate a precision, posterior, encoder or kernel cause,
nor establish a training mechanism or a framework defect.

Source/runtime and model hashes, contracts, native graphs and evidence paths are
in the [evidence index](2026-11-09-cross-framework-evidence-index.json).
Immutable native contracts describe their phase-local state; the final assessment
summary and this report supersede historical “pending review” labels without
rewriting them.

## Execution decisions and measurements

BF16 execution required staged process lifetimes on GB10: independent text
encoding, native media/denoising and, for C, separate native decoding. A task-only
dataclass bridge preserved all three timed guides because the standard C encoder
wire format rejected them. No random-state fields crossed that media boundary.
Temporary owned CPU storage bounded mapped-checkpoint GPU-transfer growth;
destination-weight probes verified exact values without changing arithmetic.

Failed builds, the first C OOM, a later controlled memory stop, the failed CPU
time forecast and unsuccessful audio readiness are retained. The ARM64
cuSPARSELt wheel repair changes its incorrect platform tag/local version, with
every library/header/license payload hash unchanged. The CUDA model-time contract
was frozen from a tiny actual-GPU probe before full media, with no solver change
or numerical tolerance added after seeing outcomes.

| Measured stage | Seed1 seconds | Seed2 seconds | Peak allocated CUDA GB |
| --- | ---: | ---: | ---: |
| A native graph, execution-start to success | 1012.228 | 1016.391 | Not instrumented |
| B staged AV phase, excluding earlier text encoder | 1286.542 | 1302.816 | 77.661 for each |
| C denoising/load phase, excluding separate media/encoder/decoder | 1170.985 | 1182.674 | 72.397 for each |

These boundaries differ and do not establish end-to-end throughput. C's separate
decoder peaks at 11.056 GB allocated. Observed minimum physical memory available
was 25.47–26.74 GB for B and 36.65–36.71 GB for C; B1's observer started late and
does not prove a whole-phase minimum. Decimal GB are used. No complete workflow
latency comparison, provider billing or engineering-cost saving is claimed.

## Restoration and delivery

The same original Comfy/gateway containers and VoiceLab/SGLang units are restored,
with configuration/effective mounts, startup runtime/source/package/arithmetic
flags, node schema and all four original model contents verified. Voice and
reference-image capabilities are ready. Durable/native queues are idle, and no
task GPU container, controller or observer remains active. The embedding service
was left running. Production selections and episode exports were not changed.

Protected DB/media matched exactly before services restarted. The original strict
post-start equality assertion **failed**: unchanged native expiry cleanup removed
ten older managed outputs (seven PNGs and three MP4s), their three source assets
and three prepared inputs, and changed three asset `purge_pending` flags. They
expired during the stopped window, 18:29:41–20:26:22 UTC. These are earlier H3
reliability exercises, not the current three-episode production.

The failed assertion is preserved. A read-only proof adds the exact removed file
pins to current maps and reverses only those three flags in copied memory; it
reproduces the original table and all three original file-tree digests exactly.
Every removed output/source asset has a SHA-identical owner-retained local copy.
Prepared PNG pins were reproduced only in BytesIO with the deployed native
preparer and Pillow11.3.0. No DB state or expired path was reset or recreated.
All other protected tables/trees match, and a final live check proves the
post-start protected state stable. Final socket inspection attributes the
health-check connection to gateway PID1's native persistent GET /health;
it is not an unresolved generation client.

Private task evidence remains under
`.local/ref2va/cross-framework-caption-20261109/`, with matching Spark artifacts.
The verified private archive in its `delivery/` directory contains original MP4s,
frozen inputs, executed adapter snapshots, upstream source/build recipe, audit
and native receipts, fixed reviews and restoration evidence, bound by per-member
SHA-256. Large checkpoints, container images, numerical dumps and contact PNG
corpora remain separately retained, with locations/identities in the index;
the archive is an inspection/reconstruction bundle, not a self-contained runtime.
Historical controllers and admission receipts must not be replayed.

Independent final evidence review found the six outcomes and their limits
consistent. Final checks verify archive members and six media hashes, restoration
reconciliation and documentation consistency. This is an experiment and
documentation checkpoint, not a product release. GitHub CI and push were not
requested or run.
