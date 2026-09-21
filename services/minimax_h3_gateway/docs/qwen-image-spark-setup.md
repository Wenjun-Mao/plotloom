# Qwen-Image-2.1 on Spark: reproducible private setup

This is the reproducibility source of truth for Spark's local image backend.
It uses the documented [SGLang Qwen-Image-2.1 Spark recipe](https://docs.sglang.io/cookbook/diffusion/Qwen-Image/Qwen-Image-2.1),
not an arbitrary Diffusers or ComfyUI variant. For the public gateway contract,
operation, and incident handling, see the separate
[Qwen gateway operator manual](../../../docs/operations/qwen-image-gateway-manual.md).

## Layout and service boundary

```text
/home/wjmao/models/qwen-image-2.1/model       Qwen checkpoint and HF cache
/home/wjmao/services/qwen-image-sglang/source pinned SGLang checkout
/home/wjmao/services/qwen-image-sglang/.venv  pinned runtime environment
127.0.0.1:30010                               private SGLang API
100.64.35.71:8090                             authenticated Plotloom gateway
```

The current reproducible baseline is:

| Item | Frozen value |
| --- | --- |
| SGLang source | `1da8ac10e17baa394c44dafa173382f9ab03d8e9` |
| model snapshot | `d51d8a5eb184466b47ef1dea8a91c60c7313e30b` |
| model location | `/home/wjmao/models/qwen-image-2.1/model` |
| service | `qwen-image-sglang.service`, bound to `127.0.0.1:30010` |
| gateway lane | one active H3 **or** Qwen inference request |

The authoritative initial installation evidence is the secret-free
[deployment receipt](../../../docs/verification/2026-09-21-qwen-image-2-1-spark-deployment.md).
Do not put the Hugging Face token or any gateway bearer value in this document,
the systemd unit, command history, or source tree.

Qwen and H3 stay resident, but the gateway's durable FIFO permits only one
SGLang or ComfyUI inference request at a time. Do not use the loopback SGLang
or ComfyUI APIs directly for normal work; doing so bypasses that capacity
contract.

## Installation and reboot behavior

1. Create `/home/wjmao/services/qwen-image-sglang` and clone the exact SGLang
   revision above. If reproducing it on a different host, record its resolved
   package versions, CUDA, PyTorch, and driver details in a new deployment
   receipt rather than silently treating this machine's evidence as portable.
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

3. Download the reviewed Qwen snapshot only into
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

## Exact service command

The tracked `deploy/qwen-image-sglang.service` intentionally runs the
following command. Keep it loopback-only and use its `PYTHONPATH` boundary;
the local checkout supplies the native Qwen-Image-2.1 pipeline that the released
package alone did not provide for the reviewed source revision.

```sh
/home/wjmao/services/qwen-image-sglang/.venv/bin/sglang serve \
  --model-type diffusion \
  --model-path /home/wjmao/models/qwen-image-2.1/model \
  --model-id Qwen/Qwen-Image-2.1 \
  --pipeline QwenImage21Pipeline \
  --performance-mode speed \
  --host 127.0.0.1 \
  --port 30010
```

Useful post-install checks are:

```sh
systemctl --user daemon-reload
systemctl --user enable --now qwen-image-sglang
systemctl --user is-active qwen-image-sglang
loginctl show-user wjmao -p Linger
curl --fail http://127.0.0.1:30010/health
```

After a Spark reboot, the lingering user service should return without an
interactive login. If it does not, inspect `journalctl --user -u
qwen-image-sglang` and verify the exact local source, virtual environment, and
model paths before changing runtime options.

## Gateway integration required for reproducibility

This loopback SGLang service is not the normal caller interface. Reproduce the
gateway from the same Plotloom source revision and use its private image API;
direct use of `127.0.0.1:30010` bypasses the shared H3/Qwen FIFO and invalidates
capacity assumptions. The gateway's Tailnet `/health` endpoint is intentionally
unauthenticated and exposes only readiness metadata; its image-job endpoints
remain bearer-authenticated.

The public image contract—reviewed canvases, one-output/40-step/CFG-1 policy,
single-reference editing, transparent-alpha validation, snapshots, and
72-hour/30-day retention—is owned by the
[Qwen gateway operator manual](../../../docs/operations/qwen-image-gateway-manual.md)
and [ADR 0073](../../../docs/adr/0073-qwen-image-reviewed-canvas-contract.md).
Do not duplicate that catalog as a local SGLang setting or change it on Spark
without the corresponding gateway contract update.

## Required qualification evidence

Before enabling a fresh installation, record four 1024×1024 canaries: opaque
text, opaque one-image edit, transparent text, and transparent one-image edit.
Each transparent canary must decode as RGBA and contain meaningful alpha. Then
prove the resident Qwen service and the established H3 quality-8 memory path
can share the gateway's single generation lane.

The six non-square canvases completed one text-generation and one
single-reference-edit qualification each on 2026-09-21. The retained
[canvas qualification receipt](../../../docs/verification/2026-09-21-qwen-image-canvas-qualification.md)
records the exact sizes, timings, memory, and review copies. Do not add an
arbitrary new canvas without equivalent qualification and a new versioned
gateway contract.
