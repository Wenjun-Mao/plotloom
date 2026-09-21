# Qwen-Image-2.1 on Spark: reproducible private setup

This is the operational source of truth for Spark's local image backend. It
uses the documented [SGLang Qwen-Image-2.1 Spark recipe](https://docs.sglang.io/cookbook/diffusion/Qwen-Image/Qwen-Image-2.1), not an arbitrary Diffusers or ComfyUI variant.

## Layout and service boundary

```text
/home/wjmao/models/qwen-image-2.1/model       Qwen checkpoint and HF cache
/home/wjmao/services/qwen-image-sglang/source pinned SGLang checkout
/home/wjmao/services/qwen-image-sglang/.venv  pinned runtime environment
127.0.0.1:30010                               private SGLang API
100.64.35.71:8090                             authenticated Plotloom gateway
```

Qwen and H3 stay resident, but the gateway's durable FIFO permits only one
SGLang or ComfyUI inference request at a time. Do not use the loopback SGLang
or ComfyUI APIs directly for normal work; doing so bypasses that capacity
contract.

## Installation and reboot behavior

1. Create `/home/wjmao/services/qwen-image-sglang` and clone an exact SGLang
   revision. Record its commit SHA, `uv.lock`/resolved package versions, CUDA,
   PyTorch, and driver details in the deployment receipt.
2. Create the virtual environment with the released SGLang diffusion runtime:

   ```sh
   uv venv /home/wjmao/services/qwen-image-sglang/.venv --python 3.12
   uv pip install --python /home/wjmao/services/qwen-image-sglang/.venv/bin/python \
     "sglang[diffusion]" --prerelease=allow
   ```

   The service unit then places the pinned checkout's `python/` directory
   first on `PYTHONPATH`. Do not replace this with an editable install unless
   the host also has the Rust toolchain needed to build SGLang's optional
   extensions; the Spark runtime does not require those extensions.

3. Download `Qwen/Qwen-Image-2.1` only into
   `/home/wjmao/models/qwen-image-2.1/model`; do not allow a default cache
   elsewhere. Install `deploy/qwen-image-sglang.service` under
   `~/.config/systemd/user/`, run `systemctl --user daemon-reload`, enable it,
   and verify `systemctl --user is-enabled qwen-image-sglang`.
4. Verify that `loginctl show-user wjmao -p Linger` is `Linger=yes`, so the
   user service returns after a Spark reboot without an interactive login.

The service uses explicit `--model-type diffusion`, `--model-id Qwen/Qwen-Image-2.1`,
and `--pipeline QwenImage21Pipeline` with the local model path. The first option
selects SGLang's diffusion command parser; the full Hub ID lets its native registry
match the local checkout. Together they force SGLang's
native pipeline instead of allowing a generic Diffusers fallback when a local
directory hides the upstream repository identity. `PYTHONPATH` deliberately
selects the pinned source checkout: installing it editable would require a Rust
toolchain solely to build optional extensions, while the tested runtime already
has its compatible binary dependencies. The service otherwise uses
native precision, resident components, eager execution,
automatic SDPA, full-image VAE decoding, `--performance-mode speed`, loopback
binding, one output, and no batching. Any change to those choices is a new
qualification, not an environment-only tuning tweak.

## Gateway contract and retention

The gateway accepts only these exact image canvases: `1024x1024`, `832x480`,
`960x544`, `1280x704`, `576x1024`, `608x1088`, and `704x1280`. It calls SGLang
with 40 steps, CFG 1, PNG response, and a single server-resolved output.
`backgroundMode=opaque` and
`backgroundMode=transparent` are passed through exactly to Qwen; transparent
requests also receive the stable cutout instruction that Qwen requires for
alpha generation. The gateway accepts a transparent result only when its PNG
has both alpha 0 and alpha 255, with more than 40% of pixels at alpha 5 or
below—the same meaningful-alpha threshold used by SGLang's own Qwen test.
It never applies background removal itself. Image output is retained for 72 hours; its job record and transient
input image are retained for 30 days. Plotloom must import any selected asset
it needs to keep.

## Required qualification evidence

Before enabling the service, record four 1024×1024 canaries: opaque text,
opaque one-image edit, transparent text, and transparent one-image edit. Each
transparent canary must decode as RGBA and contain pixels with alpha below 255.
Then prove the resident Qwen service and the established H3 quality-8 memory
path can share the gateway's single generation lane.

The six non-square canvases completed one text-generation and one
single-reference-edit qualification each on 2026-09-21. The retained
[canvas qualification receipt](../../../docs/verification/2026-09-21-qwen-image-canvas-qualification.md)
records the exact sizes, timings, memory, and review copies. Do not add an
arbitrary new canvas without an equivalent qualification and a new versioned
gateway contract.
