# H3 video VAE precision and INT8 qualification

**Status:** Owner-approved, implementation started 2026-10-06. The owner approved
this bounded qualification, including its 12-attempt ceiling. Production adoption
is not authorized. Results and restoration evidence will be recorded separately.

**Execution checkpoint:** one A component smoke ran successfully; the runner
stopped on a storage-versus-compute dtype validation bug before any full clip.
The observer contract is corrected and baseline services are restored. See the
[execution ledger](../verification/2026-10-06-h3-vae-qualification.md). A fresh
cold-boundary A smoke would exceed the original one-per-arm component cap and
requires resumed authority; no extra full-generation calls are proposed.

Specialist checkout: `plotloom-h3-ref2va-gateway`, branch
`codex/h3-ref2va-gateway`, clean starting commit `de6e088`.
Plotloom integration, director contact, merge and push remain held.

## Outcome and existing evidence

Determine whether FP16-accumulation kernels and the official INT8 ConvRot video
VAE offer useful measured speed/memory improvements without material visual or
audio regression on our actual H3 material. Deliver a reproducible comparison,
not an assumed speedup or automatic production switch.

Read-only inspection on 2026-10-06 confirms the live baseline:

- ComfyUI 0.38.0, commit `6b747c0428c343e1417219641db93a4fb7cb69ae`;
  image `sha256:db0010004575a508b5ac67fb36ea4ab83cf1964a84e70932019749f330c64110`.
- Torch/CUDA/SageAttention and the GB10 memory-management modification remain
  the [adopted stack](../../services/minimax_h3_gateway/h3-runtime-038-adoption.v1.yaml).
- `--bf16-unet --bf16-text-enc --bf16-vae`; no
  `--fast fp16_accumulation`.
- Video checkpoint `minimax_h3_video_vae_fp16.safetensors`, 5,207,808,496 bytes;
  audio checkpoint `minimax_h3_audio_vae_fp32.safetensors`.
- The INT8 video checkpoint is not installed. The current runtime already
  contains the upstream optimization code; no Comfy upgrade is needed here.
- Quality 1 is V1.2 Turbo4/Euler/6/3; quality 2 is
  V1.0 Turbo4/res_multistep/6/3. Ref2VA uses its separately qualified model/path.

The installed FP16 fast-path predicate requires FP16 CUDA activations. A
checkpoint's filename describes storage, not necessarily execution precision.
In particular, global VAE flags can affect the audio VAE too. Resolve effective
video/audio dtype and kernel dispatch before interpreting any timing.

Primary sources: [Comfy optimization PR 16187](https://github.com/Comfy-Org/ComfyUI/pull/16187),
[kernel PR 167 and RTX 5090 measurements](https://github.com/Comfy-Org/comfy-kitchen/pull/167),
[official INT8 checkpoint](https://huggingface.co/Comfy-Org/MiniMax-H3/blob/main/vae/minimax_h3_video_vae_int8_convrot.safetensors).
Those measurements do not establish GB10 end-to-end gains or visual equivalence
for our clips. A smaller checkpoint also does not prove lower peak memory.

## Scope and comparison

Keep the exact Comfy image, packages, diffusion/text/audio checkpoints, attention,
sampling recipes, frame count, prompts, reference bytes and seeds fixed.
Use four serial configurations:

| Arm | Video checkpoint | Video execution | FP16 accumulation |
| --- | --- | --- | --- |
| A | Existing FP16 | Current BF16 baseline | Off |
| B | Existing FP16 | FP16 | Off |
| C | Existing FP16 | FP16 | On |
| D | Official INT8 ConvRot | FP16 floating operations, INT8 quantized operations | On |

B is the precision-only control. B→C isolates the fast flag; C→D isolates the
checkpoint change; A→D measures the complete proposed change. This is a bounded
screen, not a statistically qualified performance benchmark.

**Audio invariant:** preserve the verified baseline audio execution dtype in
every arm, as well as its FP32 checkpoint bytes. If the baseline actually
executes BF16, state that explicitly; do not silently relabel or correct it to
FP32 during this comparison. An audio-precision change is a separate decision.
Record parameter and activation precision, not merely loader flags.

Use the narrowest experiment-only per-VAE precision control needed to enforce
this invariant. Do not blindly replace a global BF16 flag with FP16 and change
both VAEs. If isolation requires modifying core kernels, diffusion/text compute,
or the production API, stop and revise the plan before generation.

Excluded: newer Comfy/Torch/kernel upgrades, Sol/Spectrum/VDN, new checkpoints
other than this video VAE, new recipes/qualities/resolutions, voice tuning,
Plotloom/UI/API changes, retention resets, deletion and production promotion.

## Ordered deliverables

### 1. Freeze the experiment and prove its controls

- Refresh the exact runtime/launch/mount inventory. Preserve the current image,
  container configuration and user directory; do not rebuild from a moving tag.
- Implement scoped operator tooling and focused tests under
  `services/minimax_h3_gateway/tools/` and its existing test location. Reuse
  inventory, no-replay, media inspection and memory helpers where suitable;
  do not rerun the historical five-call script as though it were a new trial.
- Pin the INT8 download to an immutable upstream revision and verify its SHA256
  before loading. Expected official file SHA256 at planning time:
  `52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e`.
  Store it beneath `/home/wjmao/models/comfyui-h3/vae/`; retain the FP16 file.
- Prove actual GB10 kernel availability/dispatch and independent audio precision
  with a small bounded component smoke, before any full generation. An import
  or exposed kernel symbol is not proof that the optimized path ran.
- Instrument actual video encode/decode boundaries with CUDA synchronization
  or CUDA events. Report loader/offload time separately where measurable;
  distinguish CPU wall time from GPU timings. Apply identical observer overhead
  across arms, and do not time asynchronous kernel launches as completed work.
- Test arm/asset/dtype guards, unchanged audio binding, graph differences,
  cache refusals, receipt uniqueness, call cap and unknown-outcome handling.

### 2. Freeze three representative cases

1. Quality-1 FL2VA landscape, 1280x704.
2. Quality-1 FL2VA portrait, 704x1280.
3. Dialogue-bearing Ref2VA portrait, 576x1024, using an already retained
   published-voice/performance reference and the existing Base20 recipe.

All use 124 frames at 24 fps (approximately 5.167 seconds). Choose a retained
line short enough to fit; freeze its exact expected dialogue. Use existing
reviewed assets, not newly generated voices/images. Inspect prepared pixels and
prompt together before freezing. Do not repeat the historical padded-doorway
landscape mistake. Any optional end frame must remain identical across arms.

Freeze per-case seed, start/end/reference-audio hashes, prompt, model/LoRA
hashes, graph and output settings. No silent cropping/padding or changed prompt
between arms. Graph differences are limited to video VAE control and output
destination; record global launch differences separately.

### 3. Execute the bounded serial comparison

**Approved cap: 12 full-generation submission attempts total**, one per
case×arm. Rejections/failures count too; no automatic replacement or replay.
Component smokes are separately recorded and bounded to one small workload per
arm; they do not produce additional full clips or become a tuning sweep.

Respect the [shared dispatch boundary](../adr/0097-published-voice-performance-takes-and-shared-admission.md):
do not bypass the generation lane because Comfy's queue looks empty. Enter a
verified maintenance window: stop new managed dispatch, drain/reconcile all
H3/Qwen-Image/Voice Lab jobs and grants, and exclude direct backend callers.
If this cannot be established with current controls, stop before testing.
Do not cancel someone else's work or treat lease expiry as proof of completion.

Use isolated experiment user/output directories. Do not migrate the production
Comfy catalog. Restore the current configuration between experiment and normal
service. Other resident services remain in a consistent state across arms;
do not gain an apparent improvement by stopping them only for a candidate.

For each arm, start from the same documented cold process/cache boundary. Run
the three cases in the same order and label cold versus later runs. Assert that
sampler, image/audio encoding and video/audio decoding actually execute; output
prefix changes alone are not cache invalidation. Record model-load and warm-state
differences. Preserve seed/input identity even when precision changes numerical
results; do not claim identical latent trajectories.

Persist uncertainty before each sole submission and save the accepted prompt
ID immediately. On timeout, error, OOM, unexplained dtype change or unrelated
work, preserve evidence and stop. Unknown dispatch stays unknown until resolved;
do not tear down still-active inference merely to restore the service.

### 4. Review, restore and recommend

- Independently inspect MP4 dimensions, 124 frames, duration, codecs and native
  audio; fully decode both streams. Check intended words, no extra speech or
  subtitles, identity, lip-sync, temporal defects and tile seams.
- Provide one local side-by-side review page with all 12 clips, frozen inputs
  and comparable frame samples. Owner visual/audio review is separate from
  technical acceptance. No automatic quality score substitutes for it.
- Record submit-to-completion wall time, video VAE encode/decode timings,
  memory observations, dispatch/fallback facts and failures. Host MemAvailable
  and process RSS/HWM are not exact GPU allocation peaks. Capture per-arm
  measurement boundaries; do not reuse cumulative HWM as a per-job peak.
- Optional same-latent decode metrics may isolate decoder error if captured
  without another denoising run; report their limits. MP4 differences alone
  combine VAE, sampling and compression effects, not just quantization error.
- Restore exact baseline runtime/flags/mounts, reopen managed admission only
  after idle/health checks, and prove existing published voices/takes unchanged.
  Keep the INT8 file and experiment evidence; do not remove any setup/assets.
- Save a secret-free receipt under `docs/verification/`; retain raw graphs,
  prompt/audio bodies, clips and detailed logs privately under the specialist
  experiment roots. Local media belongs in `plotloom-canaries`, not Downloads.

## Acceptance, adoption and verification

The experiment succeeds when controls and runtime identity are proven, all
12 planned clips have attributable valid observations, both streams decode,
baseline restoration and service health pass, and review material is available.
A safely captured failure is a useful outcome, but not a passed qualification.
No minimum speedup is invented: report observed ratios and memory, with no
general GB10 throughput claim from one run per cell.

Recommend adoption only if the candidate has no material owner-reviewed visual
or audio regression and offers a measured operational benefit. If C is useful
but D regresses, recommend C rather than forcing INT8; retaining A is valid too.
Production adoption remains a separate owner decision after these results.
It must establish a maintainable video-only precision policy, update the current
template/readiness/snapshot implications and reproducibility manifest as needed,
and record the decision in an ADR. No temporary experiment shim is silently
promoted into production or used to reinterpret queued frozen jobs.

Run focused locked Python checks first, then the affected gateway test suite
and tool lint/syntax checks once stable. Verify documentation links, recipe/
input/hash invariants and receipt redaction. Do not rerun unrelated frontend,
E2E or wheel gates for tools/docs-only work; expand gates if shipped code changes
are separately approved. Use one source/runtime owner. A single bounded
independent read-only review of the stable harness should precede generation;
it does not authorize another writer or additional calls.

**Stopping condition:** bounded results or a preserved blocker, baseline/service
state accounted for, and a recommendation awaiting owner review. No director
message, production switch, merge or push.

Related decisions: [runtime isolation](../adr/0095-h3-runtime-qualification-and-catalog-isolation.md)
and [shared admission](../adr/0097-published-voice-performance-takes-and-shared-admission.md).
