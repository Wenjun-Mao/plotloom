# H3 cross-framework caption comparison — implementation plan

## Current status

Updated: 2026-11-09. Owner: root/current director, sole source writer on the
retained Plotloom checkout. Baseline: `7bed67a59ee8eecf2eb0886a478ef9f2d6422ae2`.
Status: **bounded six-cell investigation complete**, with the qualified outcomes
in the [final report](2026-11-09-cross-framework-results.md) and
[evidence index](2026-11-09-cross-framework-evidence-index.json).

The owner authorized E2E execution, necessary tests and autonomous technical
judgment while unavailable; the other Plotloom director remains paused. All six
fixed cells have original native AV, full decode, consistent blinded all-frame
visual review, unhinted native-AI audio review and actual browser playback.
A1 has dialogue overlays; none were observed in the other five clips. Five
primary audio reviews recover the complete phonetic source clause. B2 remains
uncertain after one neutral supplemental review. Precise speaker/sync, subtle
ambience/cutoff and some required gaze/spatial actions remain unqualified;
no full usable-clip or owner creative acceptance is claimed.

Independent encoders, exact logical-weight audits, full-size first updates and
both seeds' consumed controls passed under the declared native-path differences.
The same original services are restored with capability/runtime/model/readiness
checks and idle resource closure. Protected data matched before startup. Strict
post-start equality failed and remains failed: native expiry cleanup removed
older reliability assets. Exact in-memory reconciliation reproduces all original
digests, every removed output/source has a verified retained copy, and all other
protected state matches. No DB reset or expired-file recreation was performed.

The six-cell stopping condition is met. The private bundle retains source,
inputs, original AV, fixed reviews and operational evidence; bulky runtime/model
artifacts remain separately identified. The final recommendation is to retain
Comfy and consider separately authorized configuration-package replication,
without starting it. Production selections/exports, CI and publication were not
changed. Unrelated checkout changes are preserved.

## Execution qualification amendment (before new model/media results)

The common contract is exact source prompt/pixels/order/times, common source
logical weights, own independent encoders, target-noise values, layout semantics,
and common Euler-20 solver boundaries. Native media preparation is deliberately
retained: B uses the Comfy image-VAE posterior mean and GPU FP32 normalization;
C samples the posterior with seed 42 per image, rounds the raw latent through
FP16, then normalizes/patchifies on CPU FP32. This is a semantic conditioning
difference. Encoded reference/guide values and all VAE preparation policies are
**not matched**. Retain their actual clean tensors and descriptive differences.

The B→C conclusion covers the combined framework path, including posterior
selection, encoding arithmetic and native decoding. It cannot isolate kernels,
precision or posterior selection. An independent Sol/High review confirmed this
qualification remains within the selected whole-framework-path comparison; it
prevents an unqualified “identical conditioning/shared setup PASS” claim. The
frozen raw fixture is unchanged. The task-local
`.local/ref2va/cross-framework-caption-20261109/qualification-contract-v2.json`
records this decision before any new model/media outcomes.

Native denoising precision also differs: Comfy rounds incoming packed target
latents to BF16 before H3's FP32 projector upcast, and returns negative RF velocity
at that input dtype. C keeps FP32 latent-projector inputs and FP32 RF velocity
outputs. Both consume the same external FP32 initial-noise tensors; their actual
network-ingress values and numerically realized updates are not claimed identical.
Retain raw sampler states, actual projector inputs, predictions and the first
updated states. Compare canonical signs/packing and quantify cast effects
separately. A second independent Sol/High scope review accepted this explicit
native-path qualification before predictions or new full media.

B/C also use explicit common base backend flags. Their video solver grids are
bit-identical; C adopts the frozen Comfy-derived audio solver boundaries. Native
FP32 model-time rounding remains separately forecast and measured. The B audio
checkpoint is a task-local normative FP32 fold from the vendor's weight-norm
parameters plus config buffers, preserving common source logical weights without
assuming the preconverted Comfy export is bit-identical.

The initial CPU forecast of native model-time rounding was incomplete. A tiny
actual scalar-GPU test exactly reproduced all 20 observed B values: CUDA's
constant division uses a rounded FP32 reciprocal, with differences from C at 15
indices (video maximum `2^-24`, audio maximum `5*2^-24`). The solver grids are
unchanged. Version 3 of the task qualification contract freezes exact measured
device bit patterns, with no numerical tolerance; native time-embedding hooks
verify them. The failed forecast preflight is retained as failed.

Large-load diagnostics reproduced anonymous-memory growth when native GPU copies
read checkpoint mappings directly. Temporary independent CPU storage bounded the
same transfers; Comfy's bounded native-layer probe also verified exact destination
values for ten real weights. C uses that storage in its iterator; B uses native
per-module load-state hooks. Parameter mapping, source values and dtypes remain
unchanged. C's native media encoding and native decoder run in separate processes;
the task dataclass bridge preserves all three timeline guides because the standard
encoder wire format rejects them.

## Outcome and acceptance

Use retained caption-prone inputs to investigate whether H3's caption behavior
changes with configuration or framework while preserving its native audio.
The owner chose clean, faithful output per attempt over throughput, excludes
picture repair, and selected three arms:

| Arm | Setup | Contrast |
| --- | --- | --- |
| A | Current Comfy INT8 ConvRot / NVFP4 configuration and current recipe | Fresh historical-style control |
| B | Comfy on the selected shared supported setup | A→B: configuration-package change within Comfy |
| C | vLLM-Omni on that same shared setup | B→C: framework-path difference under the shared contract |

Do not attribute A→C alone to the framework, or individual A→B effects to a
particular precision/sampler change. B and C must each run their own tokenizer,
text/vision encoder, media preparation, denoising and decoding. A shared external
noise fixture is allowed; feeding B's embeddings or encoded guides into C is
only a narrower diagnostic and cannot satisfy the independent-pipeline claim.

| Claim | Required evidence | Fresh media | Current status |
| --- | --- | --- | --- |
| The experiment addresses the selected question | Frozen three-arm fixture and differences; independent B/C encoding; no source rewriting | No | Complete, unchanged raw fixture |
| Shared setup is supported and fits the actual Spark workload | Exact source/artifact identities, staged process lifecycle, actual geometry/reference memory evidence | Yes | All six native AV complete; staged BF16 path qualified |
| B/C effective inputs and recipe are controlled | Prompt/pixels/order/times; logical weight mapping; token/position contracts; actual noise; sigma/update/evaluation trace | Yes | Four full20 traces and both-seed controls passed under declared native-path differences; encoded/arithmetic equality not claimed |
| Each cell follows the actual intended path | Submitted/admitted/consumed configuration, intermediate binding, complete native AV and decode/provenance receipt | Yes | Six original AV, native receipts and full technical decode retained |
| Caption and native-speech observations are comparable | Blinded consistent visual and audible review; source words checked; actual coverage and uncertainty retained | Yes | All six assessed; B2 speech uncertain; speaker/sync and some scene actions unqualified |
| The result can guide the next decision | All six cells reported, including failures; A/B and B/C contrasts; no unsupported causal or success-rate claims | Yes | Final report: no demonstrated vLLM advantage; separate replication considered, not launched |
| Existing work remains intact after the experiment | Protected-state comparison, no duplicate/unknown work, resource release and restoration/readback | No extra render | Pre-start equality passed; strict post-start equality failed, exact native-retention reconciliation retained; same services restored, other protected state matches, post-start state stable and task resources closed |

A complete investigation can report no improvement or all captions recurring.
It cannot claim a reliable remedy from two seeds in one scene. Missing speech,
unheard audio, changed input, dropped guides or a feasible-looking API response
cannot count as a usable-clip pass. If preparation cannot qualify a shared setup,
deliver a precise feasibility report and unfinished acceptance rows; do not label
that a successful cross-framework caption test.

## Decisions and scope

User decisions: clean direct H3 output; native audio retained; quality per attempt
first; include SGLang and vLLM in research; use the three-arm shared-setup design;
remain in brainstorm/plan until a separate execution instruction.

The first common setup below is the planner's technical choice within that
direction. The director may make ordinary packaging, module, process-isolation,
container and diagnostic choices that preserve the experiment. Runtime changes
and model execution were outside the earlier planning phase; the later E2E
instruction now authorizes scoped execution as recorded above.

The fixture is the exact historical-prompt H arm from the completed
[caption pilot](2026-11-09-channel-tests.md): E02-09, pilot clip-02 and clip-04.
The first had captions; the second had none observed in its recorded review
coverage. Neither is certified as a completely usable clip. Read:

- `.local/ref2va/caption-channel-tests-20261109/design.json` for input pins,
  original seeds and guide identities.
- Its `packets/clip-02/{prompt.txt,request.json}` and `packets/clip-04/` for
  unchanged inputs. Preserve seeds `8903669569368281099` and
  `4809202367604096106` as exact signed-64-bit integers, never JS Numbers.
- Its retained `collected/`, `closure-proof.json`, native graphs and fixed scores
  for historical controls, not fresh experimental results.

All arms preserve exact prompt/dialogue and source guide bytes, prepared
960×544 contain/pad pixels, three ordered image references PLUS separate timed
guides at pixel frames 0/60/120, 260 output frames at 24 fps, and native stereo
AV. Keep the 10,300 ms request distinct from its aligned 260/24-second output.
No captions, bubble graphics, TTS, audio replacement, cropping, inpainting,
refinement, interpolation or prompt expansion is added after generation.

The smallest live study is six cells: two retained seeds × A/B/C. No production
selection or episode export changes. SGLang, LightX2V and Diffusers are researched
alternatives, not additional render arms. E03-24 attempt-01 is a future replication
candidate, outside this initial experiment. Six cells define the study, not an
account spending ceiling or prohibition on necessary technical diagnostics.

## Framework decision

| Framework | Relevant finding | Decision for this plan |
| --- | --- | --- |
| ComfyUI | Working current references-plus-timed-guides path | A control and B common-setup arm |
| vLLM-Omni | Actual H3 native AV, arbitrary timeline guides alongside references, Euler/RES support, upstream GB10 recipe | C; first independent pipeline to qualify |
| SGLang | Direct H3 path supports references and first/last keyframes; inspected interface lacks three arbitrary timeline anchors | Keep as documented alternative; its Comfy-backed DiT integration cannot independently test the text encoder |
| LightX2V | Direct Ref2AV and INT8 ConvRot support; current exact guide/sampler/encoder contract differs | Defer; no evidence of caption advantage |
| Diffusers | Documented independent joint AV pipeline; current artifact, guide and sampler contracts differ | Defer; no evidence of caption advantage |

The actual alternate is vLLM-Omni, not ordinary vLLM LLM serving. Its
`quality=lossless` profile disables certain approximations/features; it does not
prove BF16 weights, identical numerics or lossless MP4 encoding. Nothing in the
research establishes a caption-free framework. The earlier Diffusers-first
proposal is superseded by this broader source investigation.

## First common B/C setup and feasibility decision

Use original unpruned H3 Ref2VA BF16 logical weights and BF16 Qwen conditioning.
Initial source candidates are `MiniMaxAI/MiniMax-H3` snapshot
`42ed227ee7df40d41602854ae760620d6eb651fe` and the BF16 Comfy exports at
`Comfy-Org/MiniMax-H3@54472221d27c695fca9621b0c3ed52f06c4af707`:
`minimax_h3_ref2va_bf16.safetensors` and
`qwen3vl_32b_minimax_h3_bf16.safetensors`. These names identify candidates, not
verified equivalent weights. Establish source provenance and streamed logical
tensor mapping, including QKV ordering and Qwen's selected hidden layer. Use a
mechanically checked reformat if needed; do not introduce a new quantizer/kernel
or silently substitute the existing pruned INT8/NVFP4 files.

B and C use each framework's own Qwen text/vision encoder in a separate process,
retain its conditioning with source hashes, then exit that process before loading
the DiT/media stage. Verify process exit and physical shared-memory release.
Comfy's ordinary unload-to-CPU is not sufficient on GB10. vLLM's precomputed-text
path must consume C's own encoder output and its own native media preparation.
Keep original logical AV VAE weights and declared common primitive compute policies matched. Native posterior-selection/normalization differences are explicitly retained under the execution qualification amendment; do not claim equivalent encoded media. A VAE-format limitation remains a qualification issue.

Proposed common sampler: Euler with 20 actual model evaluations and native
video/audio shifts 12/3. This makes the update correspondence simpler to check
than two different RES implementations; A retains its original RES20 recipe.
This is an explicit B/C configuration change. Match the actual sigma sequences,
predicted-variable parameterization and per-stream updates, not only the name
or nominal step count. No Turbo/LoRA, approximate caches or prompt rewriting.

BF16 staged residency is a feasibility candidate, not a fit claim. The published
vLLM Spark example used online FP8, one reference and a different duration/shape;
it does not qualify three references, three guides and this longer output. Check
physical memory and allocator use through conditioning, one denoise step and
decode. Select meaningful reserve/headroom from observed host requirements before
full generation. Do not attempt to solve shared-memory pressure by CPU offload.

If the full case does not fit, first diagnose retained allocations, staging and
supported memory-efficient exact operations. These routine in-scope repairs do
not require repeated user permission after execution is authorized. If it still
requires common quantization, changed media geometry/timing/guides, a different
host, an external provider or substantial new model/kernel support, return the
concrete finding and options to the director/user. Do not silently broaden the
study. A common FP8 fallback must establish shared quantization semantics; Comfy
FP8 exports and vLLM online FP8 are not automatically equivalent.

## Implementation sequence and evidence

### 1. Bind the fixture and execution envelope

Create a new task-local experiment directory, separate from the completed pilot;
reuse retained input bytes and receipt/guard patterns without rerunning its
closed controllers or changing historical grants. Pin repo/runtime commits,
container/package identities, model sources, precision, prepared images and
proposed arm differences. Check the currently installed runtime state and disk
capacity before large downloads; use a single necessary task family, not the
entire model repository. Keep credentials out of artifacts and command output.

Establish the actual audio-review route using a retained clip before fresh
renders. A supported audio-capable agent or human listener may perform the
review; the owner need not personally listen if qualified delegated review is
available. ASR alone is not listening. If no actual listening route is available,
record that readiness gap and arrange the smallest assisted review; do not
promise complete audio-quality acceptance from transcripts.

### 2. Build isolated adapters and validate without generation

Retain the current installed Comfy image/configuration for A. Run B and C from
separate task-specific environments, preserving the original runtime and model
files. Use one source writer. Keep adapters task-local unless a narrowly required
reusable product change is separately identified; no new backend product,
persistent job platform, generic converter framework or deployment automation.

Implement small cohesive preparation/encoding, arm-execution and collection
modules, reusing existing native APIs. Target about 400 handwritten lines per
file; evaluate responsibility separation before substantial edits above that.
Any new durable product API/runtime contract needs its normal ADR and affected
checks; this plan prefers no product behavior change.

Relevant entrypoints:

- Existing Plotloom `services/minimax_h3_gateway/src/plotloom_h3_gateway/reference_execution.py`
  and its reference workflow template bind A's real prompt/reference/guide path.
  Retained pilot `prepare.py`, `run.py`, `native_guard.py`, `follow_collect.py`,
  `retain_closure.py` and `prepare_media.py` show input/intent/retention patterns.
  Reuse functions/patterns, not the old six-job identities, fixed counters or
  expired launch windows.
- Installed Comfy `comfy_extras/nodes_minimax_h3.py`,
  `comfy/text_encoders/minimax.py`, `comfy/ldm/minimax/model.py` own conditioning,
  special tokens, guide packing and joint AV. B may need task-only
  conditioning export/import nodes to enforce process-lifetime separation.
- vLLM `vllm_omni/model_executor/models/minimax_h3/encoder.py`,
  `encoder_processing.py`, `text_encoder.py` and `timeline_guides.py` own C's
  independent encoding. `diffusion/models/minimax_h3/pipeline_minimax_h3.py`
  owns `_extract_text_conditioning`, `_merge_timeline_guides` and noise injection;
  `packed_sequence.py`, `sampling.py`, `denoise_loop.py` own layout and updates.
- Use existing focused vLLM contracts such as `test_minimax_h3_timeline_guides.py`,
  `test_minimax_h3_packing.py`, `test_ref2va_initial_noise_preparation.py` and
  relevant quantization/encoder tests. Test new adapters with retained tensors
  and offline requests, forbidding unintended live dispatch.

Check exact prompt/token IDs/reference order, image pixels and preprocessing,
logical tensor values, packed reference/guide row positions and update masks,
AV schedules and lossless seed transport. Export one canonical video/audio and
conditioning-noise fixture per seed, with shapes/layout/dtype and hashes; both B
and C consume those actual values. A retains its original native RNG semantics.
Do not count shared B embeddings as an independent C encoder test.

### 3. Qualify the actual model boundary and first journey

After the separately authorized execution phase begins, validate staged memory
release, finite intermediate outputs and the same full-case conditioning layout.
Inspect independent encoder outputs and representative DiT predictions/updates.
Predetermine tolerances from dtype/operator expectations before inspecting media;
exact source/token/layout/noise contracts remain exact. Bit-identical final
images are not required. Explain numerical differences rather than choosing a
convenient tolerance after seeing captions. A material setup mismatch blocks the
matched claim and must be repaired or reported as a different experiment.

Exercise one original-size complete C journey as the first C pilot cell, not an
unrecorded extra quality sample. Predeclare this ordering exception and complete
that same seed's A/B counterparts before choosing the remaining cells' balanced
order. Retain the first clip regardless of quality. A technically valid first
clip is not permission to change the scene or chase a favorable outcome.

This is the meaningful direction review: decide whether the shared setup is
qualified, whether a bounded repair is needed, or whether feasibility evidence
requires a scope decision. No new routine human sign-off is inserted when the
approved setup passes. After two unsuccessful attempts at the same criterion,
reassess the cause/method under AGENTS.md rather than repeating it unchanged.

### 4. Complete the six-cell comparison

Run serially on the shared Spark resource. Before the first submission and at
runtime handoffs, use current gateway/Lab nonterminal, unresolved-intent, durable
shared-lane and native-queue checks. Coordinate a quiet window and prevent
admissions racing the experiment; a task-only lock that other producers ignore
is not sufficient. Determine the existing supported quiesce/reservation operation
before deployment. Never clear uncertain state or cancel unrelated work.

Use fresh identities and a durable intent before each admitted cell; record the
known job/process and consumed setup. Unknown acknowledgments are reconciled by
identity without blind resubmission. Technical recovery follows known state:
failures are retained, diagnosed and safely retried only after known termination
and ownership checks, with any replacement explicitly linked. The six planned
cells are fixed; technical retries are not silently additional independent trials.
No automatic output-quality rerolls or seed search. If a repair changes the
shared setup, invalidate affected comparison cells and preserve their history;
requalify and rerun the affected matched set, not unrelated checks.

For every valid output, retain actual admission/native graph or equivalent
execution trace, setup/inputs/intermediate pins, complete original AV, source
hashes, full decode and geometry/frame-rate/audio checks, plus elapsed time and
memory measurements if available. Production media and selections remain intact.

### 5. Blind assessment, interpretation and closeout

Use anonymous clip IDs without arm/seed clues in filenames or metadata exposed
to the assessor. Fix scores before revealing the mapping. The same protocol
covers all cells: continuous video playback, a frame-complete inspection set
with native-resolution checks of text-like regions, and actual audio listening.
Record precisely which material was inspected; uncertainty is not a clean pass.
ASR assists only after an unhinted transcript/observation, with source clauses
compared afterward. Check caption/bubble presence, full source words,
intelligibility/speaker/synchronization, and required scene/actions separately.
Distinguish authored physical writing from unwanted dialogue overlays.

The report presents all cells and A/B plus B/C contrasts. A clean picture with
missing or unresolved speech is not a usable-clip success. If both B/C differ
from A, investigate the configuration package; if B/C differ, replicate before
claiming a framework advantage. Neither divergence nor agreement proves a model
training mechanism or a framework bug. Do not estimate population failure rates
from these two seeds or turn frames/clauses into independent trials.

After known terminal/retention closure, release experiment resources and restore
any temporarily quiesced original runtime/admission state. Verify original
artifact identity, health, protected records/media and readiness without an
unsolicited new generation. Leave experiment models/media for review; remove
only explicitly disposable task-owned temporary files/processes under the normal
cleanup policy. No broad deletion, database reset, old-grant rewrite or release.

## Permissions and director discretion

Current permission (owner's later instruction, superseding the planning-only
boundary): implement this plan E2E, conduct needed tests and experiments, and use
best judgment while the owner is unavailable. The other Plotloom director is
paused until further notice; verify actual live state before resource changes.
Record consequential decisions here. Routine technical choices and bounded
repairs within the agreed result do not require another owner question.

This covers scoped dependency/model downloads, isolated Spark environments and
adapter files, staged model loading, diagnostic model checks, the six-cell
experiment and known-state technical recovery, coordinated temporary quiescence
or unloading of idle shared services when needed, restoration and task-owned
cleanup. Preserve active/uncertain work and native access requirements. User
absence does not permit unrelated destructive actions or broader provider costs.
The initial six-cell study remains the primary deliverable; additional diagnostics
must answer a concrete qualification question rather than chase quality outcomes.

Still outside scope: GitHub CI/Actions or triggering pushes; paid/external
providers; production migration; replacing selected clips; changing source
story/dialogue/guides; interrupting active or uncertain work; deletion of retained
assets; broad quantizer/kernel development. Unexpected needs in those categories
return with concrete evidence and options. Do not stop for an estimate overrun
alone or invent account budgets or general retry ceilings.

## Estimate and review points

The following engineering forecast is historical; execution and its final review
are complete. Measured stage timings and their limits are in the final report.

Engineering forecast: roughly 4–10 working days through isolated bridges,
logical-weight/input qualification, bounded integration repairs, review fixes,
assessment tooling and closeout, assuming the BF16 staged candidate is viable.
This is a forecast, not a deadline. Downloads and six serial renders add waiting;
their total is not yet defensibly bounded because exact full-case BF16 memory
and latency are unmeasured. Update the end-to-end forecast after the compatibility
assessment and the first qualified full-size journey. Do not extrapolate the
published single-image FP8 timing as this case's measured performance.

Step back earlier on an incompatible loader/conditioning contract, persistent
memory failure, inability to reserve the shared resource, or absence of a usable
audio-review path. A quantized fallback or broad port may be disproportionate;
present that finding rather than spending an open-ended effort on supporting
infrastructure. The final review decides what the evidence supports and whether
a separate second-scene replication is worth requesting. It does not trigger it.

## Planning reviews

Outcome/completeness review completed read-only on 2026-11-09, with GPT-6.1 Sol
and Xhigh requested explicitly in a fresh context. Verdict: ready for planning
handoff subject to the second review; no actionable findings. It challenged
missing-speech false successes, shared conditioning hiding encoder defects,
uncontrolled setup differences, and infrastructure-only completion. The plan's
evidence and separate completion states exclude those false success claims.

Avoidable-restriction review completed read-only on 2026-11-09, with a separate
GPT-6.1 Sol and Medium requested explicitly in a fresh context. Verdict: ready
for planning handoff; no actionable findings. It confirmed that routine recovery
and continuation do not require repeated approval, resource serialization and
unknown-dispatch guards are justified, and the six-cell scope does not invent an
account budget or technical-retry ceiling. No success/evidence changes were
requested, so no first-review recheck was needed.

Both reviews assessed the plan, not runtime feasibility or media outcomes. They
do not authorize execution. The first common setup still requires the stated
qualification work during a separately authorized execution phase.

## Research and prior evidence

- [Initial research and superseded proposal](2026-11-09-research-brainstorm.md)
- [Completed six-render caption pilot](2026-11-09-channel-tests.md)
- [Installed conditioning/tokenizer evidence](</Users/wjmao/projects/HU/plotloom/.local/ref2va/caption-research-20261109/research-notes.md>)
- [Common setup options and source candidates](</Users/wjmao/projects/HU/plotloom/.local/ref2va/caption-research-20261109/planning-setup-options.md>)
- [vLLM source/headers](</Users/wjmao/projects/HU/plotloom/.local/ref2va/caption-research-20261109/vllm-conditioning-feasibility.md>)
- [SGLang findings](</Users/wjmao/projects/HU/plotloom/.local/ref2va/caption-research-20261109/sglang-conditioning-feasibility.md>)
- [LightX2V/Diffusers findings](</Users/wjmao/projects/HU/plotloom/.local/ref2va/caption-research-20261109/cross-runtime-feasibility.md>)

The failed hostname lookup in one environment note is historical and does not
establish that the Spark is offline: a separate approved read-only route succeeded
for installed source and checkpoint-header inspection. Alternate installations,
current capacity and live admission readiness still require fresh checks at the
appropriate execution phase. No runtime, media or product qualification is
claimed by these planning records.
