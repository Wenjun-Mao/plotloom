# Qwen-Image-2.1 gateway: operator and maintainer manual

**Status:** Qwen-Image-2.1 is a private, always-resident Spark image backend.
It accepts text generation and one-reference image editing through the shared
Plotloom generation gateway. This manual owns its public image contract,
operation, recovery, and qualification boundary. It does not define H3 video
sampling or ComfyUI operation; use the separate
[H3 operator manual](minimax-h3-gateway-manual.md) for those.

For reproducible host installation, use the versioned
[Qwen Spark setup guide](../../services/minimax_h3_gateway/docs/qwen-image-spark-setup.md).
For colleagues calling the private API, use the Chinese
[Qwen client guide](qwen-image-gateway-client-guide.md). Neither document
contains the bearer secret.

## 1. Contract and non-goals

Qwen admits two image routes:

| Endpoint | Input | Output |
| --- | --- | --- |
| `POST /v1/image-jobs/from-text` | JSON prompt plus canvas choices | one managed PNG |
| `POST /v1/image-jobs/from-image` | exactly one source image plus the same choices | one managed PNG |

Every admitted job freezes exactly one reviewed canvas, one seed, 40 steps,
CFG 1, one output, and `backgroundMode`. The allowed output canvases are:

| Direction | Exact values |
| --- | --- |
| square | `1024x1024` |
| landscape | `832x480`, `960x544`, `1280x704` |
| portrait | `576x1024`, `608x1088`, `704x1280` |

The gateway rejects arbitrary dimensions, multiple reference images, caller
model paths, caller step counts, caller batch sizes, H3 `quality`, and video
parameters. Text and image edit requests use independent routes; an edit may
send either multipart `image` or JSON `sourceUrl`, never both.

`backgroundMode=transparent` is a model request for an actual alpha PNG. The
gateway verifies meaningful alpha; it never applies background-removal
postprocessing. A transparent request whose delivered PNG has no meaningful
alpha fails rather than being silently published as an opaque cutout.

The canvas selection and frozen snapshot version are governed by
[ADR 0073](../adr/0073-qwen-image-reviewed-canvas-contract.md). The shared
lane is governed by [ADR 0072](../adr/0072-shared-qwen-image-and-h3-generation-lane.md).

## 2. Runtime and trust boundary

```text
Tailnet callers and Plotloom
              │ bearer-authenticated image and video APIs
              ▼
    Spark generation gateway :8090
    durable SQLite FIFO; one active inference
          │                         │
          ▼                         ▼
Qwen SGLang :30010             H3 ComfyUI :8188
127.0.0.1 only                 127.0.0.1 only
```

`GET /health` is intentionally unauthenticated for Tailnet readiness checks;
all job and output endpoints require the gateway bearer. It reports only safe
metadata such as `imageResolutions`, `queuedJobs`, and backend readiness. It
does not reveal prompts, outputs, host paths, or keys.

Qwen and H3 stay resident to avoid repeated model loading. The gateway owns
one unlimited durable FIFO, so at most one SGLang or ComfyUI inference call is
active. Source downloading, image decoding, and safe managed-output transfer
do not hold that GPU lane. Direct calls to `127.0.0.1:30010` or
`127.0.0.1:8188` bypass this guarantee and are not normal operating paths.

The service sources are intentionally separate:

- gateway module: [`services/minimax_h3_gateway`](../../services/minimax_h3_gateway/);
- Qwen loopback systemd unit:
  [`qwen-image-sglang.service`](../../services/minimax_h3_gateway/deploy/qwen-image-sglang.service);
- Qwen transport and public contract:
  [`qwen_image.py`](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/qwen_image.py)
  and [`contracts.py`](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/contracts.py);
- exact canvas catalog and frozen snapshot parser:
  [`image_catalog.py`](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/image_catalog.py).

## 3. Deployment and reboot checks

The local Qwen service is the lingering user service `qwen-image-sglang`.
Before treating an install or reboot as recovered, check it without printing
any secret:

```sh
systemctl --user is-enabled qwen-image-sglang
systemctl --user is-active qwen-image-sglang
loginctl show-user wjmao -p Linger
curl --fail http://127.0.0.1:30010/health
```

The expected answers are `enabled`, `active`, `Linger=yes`, and an HTTP
success. The service must listen only on `127.0.0.1:30010`; do not bind SGLang
to a LAN, Tailnet, or public interface.

Gateway source or configuration changes require rebuilding only the gateway.
Qwen runtime changes require restarting only the systemd user service. In
either case, wait until the shared queue is empty and then verify:

```sh
curl --fail http://100.64.35.71:8090/health
```

The health response must include every Qwen `imageResolutions` value above and
must report the gateway as ready. A running container or user service alone is
not sufficient evidence that a new job can be safely admitted.

## 4. Job lifecycle, output handoff, and retention

New image jobs begin as `queued`. The worker moves one job through submission,
generation, managed-output validation, and `succeeded`; it can instead end in
`failed`, `cancelled`, or `outcome_unknown`. Only `queued` jobs can be
cancelled safely.

For Qwen, `generationElapsedMs` starts immediately before the gateway calls
SGLang and ends when it observes the model response. It excludes source URL
fetch/decode and writing the final managed PNG, so it is useful operational
latency rather than a precise GPU-only benchmark.

The gateway validates the returned PNG against the **frozen** width, height,
and background-mode snapshot before publishing it. It stores the accepted PNG
under gateway-managed storage, never directly exposes SGLang's working files,
and names new managed files with a UTC allocation prefix followed by the stable
job or asset ID.

| Material | Retention | After expiry |
| --- | --- | --- |
| completed managed PNG | 72 hours | `outputReady` becomes false; output is not regenerated |
| job row and transient gateway input | 30 days | API returns `job_not_found` after cleanup |
| Plotloom canonical asset | controlled by Plotloom | never deleted by gateway cleanup |

Treat gateway SQLite as private production data: it can contain prompts and
job provenance. Do not run broad cleanup commands against its data directory.
The cleanup worker removes only database-owned managed files.

## 5. Fault handling

| Observation | Root layer | Safe response |
| --- | --- | --- |
| `qwen_image_unavailable` | loopback SGLang is not healthy | restore the user service, then re-check gateway health; do not expose SGLang publicly |
| `image_resolution_not_supported` | caller chose an unreviewed canvas | use an admitted exact canvas; qualifying a new one requires a contract change, not an SSH-only setting |
| `qwen_image_alpha_missing` | model did not return meaningful alpha | retain task evidence; retry intentionally with a different prompt/seed or request `opaque` |
| `qwen_image_output_invalid` | output did not meet frozen PNG/canvas contract | preserve evidence and inspect Qwen/gateway logs; do not accept the file merely because it opens |
| `qwen_image_submit_outcome_unknown` | request may have reached SGLang but response certainty was lost | never auto-replay; inspect the known job and service logs first |
| `gateway_output_expired` | valid PNG exceeded its 72-hour delivery window | regenerate deliberately; the old output cannot be restored |
| queued jobs do not advance | another H3 or Qwen inference holds the shared lane, or a backend is unhealthy | inspect `/health`, gateway logs, and the known active job; do not bypass the queue with a direct backend call |

## 6. Qualification and change management

The documented 1024 square service deployment is recorded in the
[Qwen deployment receipt](../verification/2026-09-21-qwen-image-2-1-spark-deployment.md).
The non-square canvas qualification is recorded in the
[canvas qualification receipt](../verification/2026-09-21-qwen-image-canvas-qualification.md).
Those records demonstrate exact dimensions, one text generation and one
single-reference edit per canvas, timing, memory, and visual review; they do
not claim universal creative quality or pixel-perfect edit fidelity.

The following require a versioned source change, regression tests, a bounded
real canary, evidence, and a new or updated decision record:

- add, remove, or reinterpret a public canvas;
- change steps, CFG, batching, precision, VAE handling, or background policy;
- permit multi-image editing or direct browser access to SGLang;
- change the shared serialization/retention boundary;
- treat a generated asset as a Plotloom-authoring workflow rather than a
  colleague-facing capability.

Do not make any of those as an SSH-only tweak. Roll back routine software
changes by redeploying the prior reviewed source revision while preserving
gateway state; do not replay `outcome_unknown` work automatically.

## 7. Handoff checklist

- [ ] `/health` reports all seven `imageResolutions`, `dispatchConcurrency: 1`,
      and no unexpected active dispatch.
- [ ] `qwen-image-sglang` is enabled, active, lingering, and loopback-only.
- [ ] Qwen model/cache remains under `/home/wjmao/models/qwen-image-2.1`.
- [ ] ComfyUI and SGLang remain loopback-only; the gateway is Tailnet-only.
- [ ] No bearer value appears in source, URL, screenshot, or browser storage.
- [ ] A managed PNG is imported into durable project storage before its
      72-hour output retention expires.
- [ ] Any new canvas or runtime tuning has an explicit qualification receipt
      before it reaches the public contract.
