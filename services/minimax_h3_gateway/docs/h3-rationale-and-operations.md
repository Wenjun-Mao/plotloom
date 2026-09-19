# MiniMax-H3 rationale and operations manual

This manual explains the engineering choices behind the Spark H3 stack. It is
not a client API guide; colleagues who need the typed private API should use
the [gateway client guide](../../../docs/operations/minimax-h3-gateway-client-guide.md).

The adjacent [installation manifest](../h3-current-installation.v1.yaml)
records the observed live stack. It distinguishes observed facts from an
approved inference recipe so that a plausible-looking video never hides a
configuration mismatch.

## 1. System boundaries

```text
Plotloom authoring server
        │ frozen prompt, approved frame, reviewed profile
        ▼
Private H3 gateway
        │ typed FIFO job; no arbitrary graph or model selection
        ▼
Loopback-only ComfyUI on Spark
        │ profile-rendered H3 graph
        ▼
MiniMax-H3 FL2VA model + native audio/video decode
```

ComfyUI is the inference engine, not the public service. The gateway is the
only private-network integration point and owns durable queueing, input
preparation, output handoff, and retention. Plotloom consumes that narrow
contract; it must not import gateway runtime modules or direct ComfyUI calls.

## 2. Why this model stack

The stack uses MiniMax-H3 FL2VA because one model can generate video and a
native synchronized audio track from text and optional first/last images. The
installed components have distinct responsibilities:

| Component | Reason for inclusion |
| --- | --- |
| FL2VA FP8 diffusion model | Fits the high-throughput GB10 runtime while retaining the H3 video/audio architecture. |
| Qwen3-VL MiniMax-H3 text encoder | Provides H3-compatible prompt conditioning. |
| Video VAE | Decodes H3's video latent stream. |
| Audio VAE | Decodes H3's jointly generated audio latent stream. |
| LightX2V FL2VA Turbo LoRA | Reduces denoising work for fast narrative iteration. |

This is not an identity-reference, lip-sync guarantee, dialogue editor, or
final-postproduction pipeline. Speech, sound effects, and music are prompted
jointly and must be reviewed as creative output.

## 3. Runtime policy versus inference profile

These two layers are intentionally separate.

| Runtime policy: one Spark worker | Inference profile: one H3 recipe |
| --- | --- |
| ComfyUI/Torch/CUDA revisions | FL2VA or another supported H3 family |
| GPU and attention backend | exact LoRA asset and checksum |
| BF16 choices and memory reservation | LoRA strength |
| `--fast fp8_matrix_mult` experiment | steps, video/audio shifts |
| container image and host mounts | sampler, scheduler, denoise |

`--fast fp8_matrix_mult` is a process-level optimization. It is not a creative
profile property: one stable Spark runtime may serve several H3 recipes.

Conversely, a Turbo adapter is not adequately described by `turbo=true` and a
step count. Its LoRA, shifts, sampler, scheduler, and denoise must travel
together as an explicit, versioned recipe.

## 4. Current state and the known divergence

The observed engine has the right 4-step v1.0 768p LightX2V LoRA, strength
`1.0`, four steps, `res_multistep`, `simple`, and denoise `1.0`. It does not,
however, render ComfyUI's `MiniMaxH3SigmaShift` node.

ComfyUI defaults H3 to video shift `12` and audio shift `3`. LightX2V's
published 4-step 768p FL2VA recipe is `4 steps / 6 video shift / 3 audio
shift`. The resulting active `12 / 3` trajectory is valid enough to render,
but it is not the adapter's published sampling contract. [LightX2V's recipe](https://github.com/ModelTC/LightX2V/blob/main/README.md)
documents the intended four-step configuration.

This is a configuration-quality defect, not an indication that every existing
video is unusable. It also should not materially affect elapsed time because
the model, geometry, frames, and number of denoising evaluations are unchanged.
It does mean historical clips are not an authoritative quality baseline for
the canonical 4-step recipe.

The repair belongs in the profile/workflow contract: render the appropriate
`MiniMaxH3SigmaShift` node for each profile, bind it into both scheduler and
model conditioning, and test the rendered graph. A gateway-side workaround or
per-request hidden adjustment would make evidence and later profile changes
harder to interpret.

## 5. Geometry, duration, and frame conditioning

The reviewed catalog permits six multiples-of-32 outputs:

| Tier | Landscape | Portrait |
| --- | --- | --- |
| Fast | 832×480 | 576×1024 |
| Standard | 960×544 | 608×1088 |
| High resolution | 1280×704 | 704×1280 |

Requested duration is a whole number from five through fifteen seconds. H3 is
24 fps and uses the `17k + 5` frame grid: a five-second request is 124 frames,
or approximately 5.17 seconds. The profile catalog—not a browser/client—owns
this conversion.

H3 accepts zero, one, or two frame conditions: text-only exploration,
start-frame image-to-video, and start/end-frame image-to-video. Gateway image
preparation owns aspect behavior (`reject_mismatch`, deliberate padding, or
deliberate crop) before the H3 graph is submitted. The graph must not hide an
authoring decision by silently changing aspect treatment.

## 6. Candidate profile policy

The following states keep experiments from silently becoming production:

| State | Meaning |
| --- | --- |
| Observed | Present on a host; captured in the manifest. |
| Candidate | Complete declared recipe; may be tested with retained evidence. |
| Qualified | Passed the agreed smoke, visual, audio, timing, and rollback checks. |
| Production | Explicitly selected default after qualification. |
| Retired | Cannot receive new work but remains interpretable in historical evidence. |

The immediate comparison sequence is:

1. Correct the current 4-step v1.0 recipe to its explicit `6 / 3` shifts and
   establish a new quality baseline.
2. On that corrected recipe, compare current launch settings with only
   `--fast fp8_matrix_mult` added. ComfyUI labels this flag experimental, so
   it needs a visual and stability check as well as a timing check. [ComfyUI
   CLI source](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy/cli_args.py)
3. Compare complete candidate recipes, not isolated LoRA files: the corrected
   4-step v1.0 baseline, a newer 4-step candidate, and the 8-step v1.0 768p
   quality candidate.

LightX2V identifies its 8-step v1.0 768p LoRA as a higher video/audio-quality
option. The associated Comfy guidance says a profile should set LoRA, step
count, and both shifts together; its published 768p 8-step values are `8 / 6
/ 3`. [Model table and guidance](https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/README.md)

Do not infer that a sampler validated for the eight-step profile is automatically
better for the four-step profile. The currently observed four-step graph uses
`res_multistep`/`simple`; candidate recipes must state and test their own
sampler/scheduler pair.

## 7. What a useful comparison records

For each candidate, hold prompt, frame inputs, seed, geometry, duration, and
runtime revision fixed. Record:

- profile recipe and workflow-template hash;
- generation elapsed time, output frame count, dimensions, and codec;
- audio presence and intelligibility where dialogue is requested;
- start/end-frame adherence, temporal consistency, motion, geometry, color,
  and subject continuity;
- crashes, OOMs, unexpected worker behavior, and rollback result.

One attractive clip is evidence, not qualification. Compare static/dialogue,
moderate-motion, and difficult-motion shots before promoting a profile.

## 8. Operational rules

- Keep ComfyUI loopback-only; expose only the authenticated gateway to the
  private Tailnet.
- Keep model assets under `/home/wjmao/models`; verify hashes before use.
- H3 dispatch is serial. Queue depth can grow, but there is one active H3 job.
- Gateway MP4s are retained for 72 hours; SQLite records and gateway keyframes
  are cleaned after 30 days according to their respective lifecycle rules.
- A changed asset hash, source revision, runtime flag, or profile recipe is a
  new candidate, not a transparent maintenance update.

For precise installation and recovery steps, use the
[reproducible setup guide](h3-reproducible-setup.md). For the private API,
use the separate client guide; neither document should be extended with a
secret or customer media.
