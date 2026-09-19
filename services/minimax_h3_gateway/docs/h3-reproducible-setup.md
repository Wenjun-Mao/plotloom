# Reproducing the Spark MiniMax-H3 installation

This guide reproduces the local MiniMax-H3 engine that the Plotloom gateway
uses on Spark. It is deliberately secret-free: it does not contain a Tailnet
address, bearer value, customer prompt, input image, or generated media.

Use the adjacent [current-installation manifest](../h3-current-installation.v1.yaml)
for pinned versions, asset hashes, and the observed runtime. The manifest is
an inventory of the live September 2026 installation, not an approved
inference recipe: its known sampling-contract divergence is documented below.

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

Keep all large model assets beneath the established host root:

```text
/home/wjmao/models/comfyui-h3/
```

Do not put models, output, or gateway state in the Plotloom checkout.

## 2. Pin the runner and build the container

The observed deployment uses the open-source `spark-comfyui` runner at commit
`408a3d3c7c47725851358ec745efb255d5ff7316`. Its built image contains ComfyUI
commit `d43a5fa20c8547ff42d13232f589a06536c42b97`, PyTorch 2.14.0+cu130, and
a native GB10 SageAttention build.

```sh
git clone https://github.com/bjarkebolding/spark-comfyui.git \
  /home/wjmao/services/spark-comfyui
cd /home/wjmao/services/spark-comfyui
git checkout 408a3d3c7c47725851358ec745efb255d5ff7316

./spark-comfyui.sh install
./spark-comfyui.sh tune --persist
```

The deployment intentionally has no external custom nodes. Keep
`comfyui-nodes.list` empty except for comments; MiniMax-H3 is supplied by the
pinned ComfyUI core revision.

Create the H3-specific mount configuration:

```text
# spark-h3-mounts.conf
models = /home/wjmao/models/comfyui-h3
```

The runner will bind that root to `/opt/ComfyUI/models`. Create normal runner
data directories as needed under `/home/wjmao/services/spark-comfyui/data/`:
`input`, `output`, `custom_nodes`, and `user`.

## 3. Download and verify assets

Create the exact model tree:

```sh
mkdir -p /home/wjmao/models/comfyui-h3/{diffusion_models,text_encoders,vae,loras}
```

Download the files named in the manifest from these sources:

- base model, text encoder, and VAEs: [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3);
- Turbo LoRAs: [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo).

Place each file at exactly its `relativePath` from the manifest. Verify every
download before starting ComfyUI:

```sh
cd /home/wjmao/models/comfyui-h3
sha256sum \
  diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors \
  text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors \
  vae/minimax_h3_video_vae_fp16.safetensors \
  vae/minimax_h3_audio_vae_fp32.safetensors \
  loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors
```

Compare the resulting hashes and byte counts with
[`h3-current-installation.v1.yaml`](../h3-current-installation.v1.yaml). A
matching filename is not sufficient evidence of matching weights.

## 4. Start the engine with the observed runtime policy

The current Spark policy uses SageAttention, BF16 for the UNet and text
encoder, FP32/default handling for the VAE, 16 GiB of reserved unified memory,
and a loopback-only ComfyUI port:

```sh
cd /home/wjmao/services/spark-comfyui

BIND_ADDR=127.0.0.1 \
SPARK_ATTENTION=sage \
SPARK_BF16=1 \
SPARK_BF16_VAE=0 \
SPARK_RESERVE_VRAM=16 \
SHM_SIZE=16g \
./spark-comfyui.sh --mounts ./spark-h3-mounts.conf service
```

This service is restart-managed by Docker and survives a host reboot. It
intentionally exposes ComfyUI only at `127.0.0.1:8188`; the gateway reaches it
through host networking. Do not bind ComfyUI to Tailnet, LAN, or internet
interfaces.

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

The object information must advertise `MiniMaxH3ImageToVideo` and every file
listed in the manifest. This verifies availability, not creative quality.

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

## 6. Qualification smoke test

There are two distinct checks:

1. **Runtime readiness:** inspect `/object_info`, verify each asset hash, and
   verify the runner, ComfyUI, Torch, CUDA, and command-line pins.
2. **Recipe qualification:** render a profile-owned workflow, submit a short
   non-sensitive H3 request, and verify the returned MP4 has the expected
   dimensions, valid H.264/AAC streams, frame-grid duration, and recorded
   sampling recipe.

Do not use the current checked-in Turbo template as a new qualification
baseline yet. It is missing the explicit `MiniMaxH3SigmaShift` required by the
installed 4-step LoRA. The next H3 maintenance slice will add profile-owned
sampling fields and qualify a corrected recipe before this guide's observed
state can be promoted to `qualified`.

## 7. Update, rollback, and reboot

Do not update ComfyUI, Torch, CUDA, SageAttention, or model files during an
H3 comparison. Any such change creates a new runtime candidate.

- After a normal Spark reboot, Docker restarts ComfyUI and the gateway because
  both are configured with `unless-stopped` policies. Confirm both health
  surfaces instead of assuming startup succeeded.
- Preserve the current image before an intentional runner update using the
  runner's `update --keep` option. Its `update --rollback` path restores the
  previous image.
- Treat a changed model hash, runner commit, ComfyUI commit, runtime flag, or
  workflow-template hash as a baseline change requiring a fresh smoke test.

For why the current runtime is organized this way, profile selection policy,
and the upcoming four-step/FP8/quality comparison sequence, read the
[H3 rationale and operations manual](h3-rationale-and-operations.md).
