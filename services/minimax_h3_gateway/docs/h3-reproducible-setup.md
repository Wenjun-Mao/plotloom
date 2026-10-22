# Reproducing the Spark MiniMax-H3 installation

This guide reproduces the local MiniMax-H3 engine that the Plotloom gateway
uses on Spark. It is deliberately secret-free: it does not contain a Tailnet
address, bearer value, customer prompt, input image, or generated media.

Use the adjacent [D adoption manifest](../h3-vae-d-adoption.v1.yaml)
for the live precision, images, mounts and immediate rollback identity. The
[September runtime manifest](../h3-runtime-038-adoption.v1.yaml) supplies the
unchanged ComfyUI/Torch foundation. The retained
[historical installation manifest](../h3-current-installation.v1.yaml)
supplies foundation asset hashes, not today's runtime/recipe status. The versioned
[corrected candidate manifest](../h3-corrected-turbo4-candidate.v1.yaml)
defines the exact inference recipe to qualify against that runtime.

### Current runtime status · 2026-10-06

ComfyUI **0.38.0 is live** at the pinned adoption-manifest image/commit. Five
initial calls, a CPU decoder-composition regression and a separately approved
corrected landscape pair support bounded maintenance adoption, not a general
quality or memory-reliability guarantee. Only the stable copied `data/user-v038`
was migrated; original image/container/`data/user` remain preserved. See the
[adoption receipt](../../../docs/verification/2026-09-30-h3-comfy038-maintenance-adoption.md).
Historical manifests and original test evidence are not rewritten.

The adopted D overlay retains that **same image and global `--bf16-vae`**, adds
`--fast fp16_accumulation`, and mounts one maintained repository-owned
[video loader](../comfy_nodes/plotloom_h3_video_vae/README.md) read-only. Video
uses the official INT8 ConvRot checkpoint with FP16 compute; stock audio keeps
its FP32 checkpoint and BF16 compute. The reload/clone factory preserves this
split. See [ADR 0213](../../../docs/adr/0213-h3-video-only-vae-precision.md)
and the [D deployment receipt](../../../docs/verification/2026-10-06-h3-vae-d-adoption.md).
Do not use global `--fp16-vae`: it would change audio as well.

## 1. Scope and prerequisites

This has been verified on a DGX Spark / NVIDIA GB10 running Ubuntu 24.04.5,
the r580 driver line, and Docker with NVIDIA Container Toolkit support. A
different GPU, driver, operating system, or ComfyUI revision is a new runtime
candidate and must be qualified rather than assumed equivalent.

The H3 engine is independent of Plotloom. The gateway is optional for a
standalone ComfyUI installation; it is required only when using Plotloom or
the private typed video API.

Before beginning, provide:

- at least 45 GiB for the five H3 assets, plus working space and container
  images;
- a Hugging Face account/token if the model repositories require one;
- a private filesystem for models, input, output, and gateway state;
- a normal, non-root Linux user who owns those directories.

`ffprobe` is not a gateway dependency, but install the host `ffmpeg` package
when operating the service. It provides the standard, independent way to
inspect a retained MP4's stream codecs, geometry, frame rate, and duration
without copying it out of managed storage:

```sh
sudo apt-get update
sudo apt-get install --yes ffmpeg
ffprobe -version
```

Keep all large model assets beneath the established host root:

```text
/home/wjmao/models/comfyui-h3/
```

Do not put models, output, or gateway state in the Plotloom checkout.

## 2. Pin the runner and build the container

The foundation deployment uses the open-source `spark-comfyui` runner at commit
`408a3d3c7c47725851358ec745efb255d5ff7316`. Its preserved baseline image contains
ComfyUI commit `d43a5fa20c8547ff42d13232f589a06536c42b97`, PyTorch 2.14.0+cu130,
and a native GB10 SageAttention build. The adopted derivative pins ComfyUI to
`6b747c0428c343e1417219641db93a4fb7cb69ae` while retaining that GPU stack.

```sh
git clone https://github.com/bjarkebolding/spark-comfyui.git \
  /home/wjmao/services/spark-comfyui
cd /home/wjmao/services/spark-comfyui
git checkout 408a3d3c7c47725851358ec745efb255d5ff7316

./spark-comfyui.sh install
./spark-comfyui.sh tune --persist
```

These runner commands describe the installation workflow; its build can
resolve a newer Comfy checkout/dependencies. They alone cannot reproduce an
old image byte-for-byte. Verify the resulting runtime against the manifest,
or use a preserved exact image. The bounded 0.38 candidate uses the separate
[`comfy038-build.sh`](../tools/comfy038-build.sh) entrypoint: it verifies the
preserved baseline image ID, builds from that immutable ID and pins Comfy's
commit while constraining every non-Comfy package. It is qualification tooling,
not a general production updater. A fresh host without that exact base image
requires a separately qualified clean build. To reproduce the adopted derivative
on a host holding the preserved baseline image, use the checked-in build wrapper
and verify the result against the adoption manifest. A rebuild may have a
different Docker image ID; do not promote it merely because the commit matches.

No third-party custom nodes are installed. Keep `comfyui-nodes.list` empty
except for comments. MiniMax-H3 is supplied by pinned ComfyUI core; D adds only
the repository-owned video loader through a read-only release mount. Never
mount `tools/vae_qualification`: its experimental callback is not production code.

Create the H3-specific mount configuration:

```text
# spark-h3-mounts.conf
models = /home/wjmao/models/comfyui-h3
user = /home/wjmao/services/spark-comfyui/data/user-v038
```

The runner will bind that root to `/opt/ComfyUI/models`. Create normal runner
data directories as needed under `/home/wjmao/services/spark-comfyui/data/`:
`input`, `output`, `custom_nodes`, and `user-v038`. The checked-in
[`comfy038-mounts.conf`](../tools/comfy038-mounts.conf) captures the adopted model
and user mounts. On the existing Spark, `user-v038` already exists: **do not
recopy or overwrite it**. On another migration, inspect catalog contents and
copy the original directory only while admission is paused and queues are empty;
do not apply this empty-catalog disposition to valuable metadata automatically.

## 3. Download and verify assets

Create the exact model tree:

```sh
mkdir -p /home/wjmao/models/comfyui-h3/{diffusion_models,text_encoders,vae,loras}
```

Download the files named in the manifest from these sources:

- base model, text encoder, and VAEs: [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3);
- Turbo LoRAs: [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo).
- optional voice-reference diffusion checkpoint:
  [Comfy-Org/MiniMax-H3 Ref2VA INT8 ConvRot](https://huggingface.co/Comfy-Org/MiniMax-H3/blob/main/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors).

Place each file at exactly its `relativePath` from the manifest. Verify every
download before starting ComfyUI:

```sh
cd /home/wjmao/models/comfyui-h3
sha256sum \
  diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors \
  text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors \
  vae/minimax_h3_video_vae_fp16.safetensors \
  vae/minimax_h3_video_vae_int8_convrot.safetensors \
  vae/minimax_h3_audio_vae_fp32.safetensors \
  loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors
```

Compare the resulting hashes and byte counts with
[`h3-current-installation.v1.yaml`](../h3-current-installation.v1.yaml). A
matching filename is not sufficient evidence of matching weights.

For D, download `vae/minimax_h3_video_vae_int8_convrot.safetensors`
from `Comfy-Org/MiniMax-H3` at revision
`e5eb578a89295337b8ff433a035929ce0279e0b6`, placing it in `vae/`.
Its size is **2,811,065,184 bytes** and SHA-256 is
`52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e`.
Compare this file against the D manifest, not the older installation inventory.
Retain the original FP16 video checkpoint for rollback; audio and model weights
are unchanged. The maintained loader checks the video hash before use.

The separately qualified Ref2VA route additionally requires
`diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors` beneath
the **same** `/home/wjmao/models/comfyui-h3` mount. The Spark trial used
SHA-256 `9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779`.
Verify this exact hash after download; the gateway freezes that model identity
and uses the already listed Qwen3-VL encoder and two VAEs, without a Turbo LoRA.

## 4. Start the engine with the observed runtime policy

The foundation uses SageAttention and BF16 for UNet/text and the global VAE
default, with `SPARK_RESERVE_VRAM` unset. The following runner command recreates
the **BF16 rollback foundation only**, not D's node mount or fast argument:

```sh
cd /home/wjmao/services/spark-comfyui

BIND_ADDR=127.0.0.1 \
SPARK_ATTENTION=sage \
SPARK_BF16=1 \
SPARK_BF16_VAE=1 \
SPARK_STATIC_VRAM=0 \
SHM_SIZE=16g \
./spark-comfyui.sh --mounts ./spark-h3-mounts.conf service
```

This service is restart-managed by Docker and survives a host reboot. It
intentionally exposes ComfyUI only at `127.0.0.1:8188`; the gateway reaches it
through host networking. Do not bind ComfyUI to Tailnet, LAN, or internet
interfaces. `--mounts ./spark-h3-mounts.conf` is mandatory: omitting it starts
a healthy-looking ComfyUI instance with the runner's default model directory,
where the H3 assets are invisible and the gateway must reject work with
`comfy_profile_unavailable`.

Before recreating a container, verify its immutable image ID against the
manifest; do not depend on mutable `latest`. Verify `/opt/ComfyUI/user` resolves to the stable
`data/user-v038` host path, not `data/user` or the experiment copy. The live
container was created with the same runner policy and exact image ID, then
passed a restart smoke check. The original 0.35 container stays stopped under its
rollback name. Do not run the two Comfy containers simultaneously.

To reproduce D on a host with that qualified image and prepared directories,
first stop admission and prove all managed/Comfy work idle. Use a stable source
release for the node, not a moving checkout. This example assumes the exact
October 6 release exists; replace only host paths when reproducing elsewhere:

```sh
docker run -d --name spark-comfyui --restart unless-stopped \
  --gpus all --shm-size 16g --user 1000:1000 \
  -p 127.0.0.1:8188:8188 \
  -e SPARK_BF16=1 -e SPARK_BF16_VAE=1 \
  -e SPARK_STATIC_VRAM=0 -e SPARK_ATTENTION=sage \
  --mount type=volume,src=spark-comfyui-cache,dst=/home/comfy/.cache \
  --mount type=bind,src=/home/wjmao/models/comfyui-h3,dst=/opt/ComfyUI/models,readonly \
  --mount type=bind,src=/home/wjmao/services/spark-comfyui/data/input,dst=/opt/ComfyUI/input \
  --mount type=bind,src=/home/wjmao/services/spark-comfyui/data/output,dst=/opt/ComfyUI/output \
  --mount type=bind,src=/home/wjmao/services/spark-comfyui/data/custom_nodes,dst=/opt/ComfyUI/custom_nodes \
  --mount type=bind,src=/home/wjmao/services/spark-comfyui/data/user-v038,dst=/opt/ComfyUI/user \
  --mount type=bind,src=/home/wjmao/services/spark-comfyui/comfyui-nodes.list,dst=/opt/spark/comfyui-nodes.list,readonly \
  --mount type=bind,src=/home/wjmao/services/plotloom-h3-gateway/releases/h3-vae-d-20261006/services/minimax_h3_gateway/comfy_nodes/plotloom_h3_video_vae,dst=/opt/ComfyUI/custom_nodes/plotloom_h3_video_vae,readonly \
  sha256:db0010004575a508b5ac67fb36ea4ab83cf1964a84e70932019749f330c64110 \
  --fast fp16_accumulation
```

This is a reproduction example, **not** a command to run against an existing
container name. Preserve the old container and configuration before replacing
anything. A fresh host lacking the exact image needs new qualification.

Confirm live runtime identity after startup:

```sh
docker ps --filter name=spark-comfyui
docker exec spark-comfyui sh -lc 'cd /opt/ComfyUI && git rev-parse HEAD'
docker exec spark-comfyui python - <<'PY'
import torch
print(torch.__version__, torch.version.cuda)
print(torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))
PY
curl --fail http://127.0.0.1:8188/object_info > /tmp/comfy-object-info.json
```

The object information must advertise `MiniMaxH3ImageToVideo`,
`MiniMaxH3SigmaShift`, `PlotloomH3VideoVAELoader`, the policy
`h3-int8-video-fp16-audio-bf16.v1`, and required assets. This verifies
availability, not creative quality.
To enable the optional voice route, also verify
`MiniMaxH3ReferenceToVideo`, `MiniMaxH3AddGuide`, `LoadAudio`, `LoadImage` and
the Ref2VA checkpoint name through `/object_info`; `/health` then reports
`voiceReferenceReady: true` separately from ordinary FL2VA readiness.

For a completed gateway-managed MP4, inspect it in place rather than relying
on browser playback alone:

```sh
ffprobe -v error \
  -show_entries format=duration:stream=codec_type,codec_name,width,height,r_frame_rate \
  -of json /path/to/gateway-data/outputs/<managed-file>.mp4
```

## 5. Start the optional typed gateway

The gateway source, Dockerfile, and compose file live beside this guide. Its
operation is documented in the [gateway operator manual](../../../docs/operations/minimax-h3-gateway-manual.md).

```sh
cd /path/to/plotloom/services/minimax_h3_gateway
cp .env.example .env
chmod 600 .env
```

Set only private deployment values in `.env`: a Tailnet bind address, a new
long bearer secret, loopback Comfy URL, and the three persistent host mounts.
Never commit that file. Start the gateway only after ComfyUI is healthy:

```sh
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 gateway
```

The gateway owns serial FIFO dispatch and managed completed-MP4 retention. It
does not expose arbitrary ComfyUI graphs, model paths, or custom nodes.
The Ref2VA route is described in [ADR 0205](../../../docs/adr/0205-h3-ref2va-per-job-voice-reference.md).
Its live qualification used a genuine 576×1024 first frame and an 8-second
PCM16/mono/32-kHz WAV, with reviewed 5- and 8-second outputs. The retained
Spark experiment receipts are under
`/home/wjmao/services/spark-comfyui/data/output/experiments/h3-ref2va-portrait-2026-09-26/`;
they are evidence for this setup, not a general voice or lip-sync guarantee.

## 6. Qualification smoke test

There are two distinct checks:

1. **Runtime readiness:** inspect `/object_info`, verify each asset hash, and
   verify the runner, ComfyUI, Torch, CUDA, and command-line pins.
2. **Recipe qualification:** render a profile-owned workflow, submit a short
   non-sensitive H3 request, and verify the returned MP4 has the expected
   dimensions, valid H.264/AAC streams, frame-grid duration, and recorded
   sampling recipe.

Use the profile-rendered `minimax_h3_template_v2.json`, not the retained
observed v1 template, for new work. Current creation uses `quality` and exact
`resolution`, not legacy `profileId`: quality 1 is V1.2 Turbo4/Euler/6/3,
quality 2 is V1.0 Turbo4/res_multistep/6/3, quality 3 is V1.0 Turbo8/Euler/6/3,
and quality 8 is Base20/res_multistep/native 12/3 without LoRA. The earlier
corrected-v1.0 candidate manifest is retained evidence, not the default today.
See [ADR 0070](../../../docs/adr/0070-h3-quality-resolution-contract.md).

## 7. Update, rollback, and reboot

Do not update ComfyUI, Torch, CUDA, SageAttention, or model files during an
H3 comparison. Any such change creates a new runtime candidate.

- After a normal Spark reboot, Docker restarts ComfyUI and the gateway because
  both are configured with `unless-stopped` policies. Confirm both health
  surfaces instead of assuming startup succeeded.
- Preserve the exact current image, container configuration and user directory
  before an update. The runner's `update --keep` also updates its runner and
  builds Comfy master, so do not use it for a pinned one-variable comparison.
  Image rollback alone does not undo an in-place user-database migration.
- Qualify new Comfy releases against an isolated copy of the user directory.
  Comfy 0.38's migration discards/rebuilds parts of the asset catalog; do not
  point it at production `data/user` without a reviewed metadata disposition.
  For this adoption, production uses a separate stable copy; original `data/user`
  and mount config were preserved without migration.
- Treat a changed model hash, runner commit, ComfyUI commit, runtime flag, or
  workflow-template hash as a baseline change requiring a fresh smoke test.

### Exact immediate rollback on the current Spark

The October 6 baseline pair is `spark-comfyui-bf16-rollback-20261006` plus
`plotloom-h3-gateway-before-vae-d-20261006`. Restore them together: the new
gateway requires the maintained D loader, while the prior gateway renders the
BF16 foundation. Do not start two Comfy workers or reinterpret pending snapshots.

The bounded operator tool verifies persisted gateway/Voice Lab grants, Comfy
queues, original identities, and published voice/take hashes before replacing
anything. It refuses unknown/active work rather than canceling it:

```sh
python3 /home/wjmao/services/plotloom-h3-gateway/releases/h3-vae-d-20261006/services/minimax_h3_gateway/tools/vae_adoption/deploy.py restore
```

Inspect its private receipt first; it is a one-maintenance tool, not a reusable
deployment daemon. It retains D under diagnostic names and restores the original
pair, mounts, environment and data. Confirm readiness and unchanged identity
hashes afterwards. The older 0.35 container/user directory remain a **historical**
second rollback boundary; rolling back to them needs a separately matched
gateway and catalog disposition, not the immediate procedure above. Do not
downgrade user directories, reset CUDA, or delete model/experiment assets.

For why the current runtime is organized this way and historical inference
comparisons, read the
[H3 rationale and operations manual](h3-rationale-and-operations.md).
