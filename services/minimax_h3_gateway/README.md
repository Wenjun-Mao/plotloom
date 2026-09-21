# Plotloom generation gateway

This is the private, typed API in front of Spark's loopback-only ComfyUI H3
service and loopback-only SGLang Qwen-Image service. It is deliberately **not**
a backend proxy: callers cannot submit workflows, select model files, or reach
either runtime directly.

Plotloom is wired to this gateway through the versioned
`minimax_h3_gateway.v6` adapter contract. Use the complete
[H3 gateway operator and maintainer manual](../../docs/operations/minimax-h3-gateway-manual.md)
for deployment, security, Plotloom configuration, lifecycle, recovery, and
the exact limits of verified behavior.

For the underlying Spark/ComfyUI engine rather than the gateway API, use the
[reproducible H3 setup guide](docs/h3-reproducible-setup.md), the
[H3 rationale and operations manual](docs/h3-rationale-and-operations.md), and
the secret-free [current-installation manifest](h3-current-installation.v1.yaml).
The manifest deliberately distinguishes the observed live installation from a
qualified inference profile. New work uses the separate corrected candidate
manifest until real-model qualification promotes it.

The separate [8-step sampling evaluation manifest](h3-8step-sampling-evaluation.v1.yaml)
and [four-step v1.2 evaluation manifest](h3-turbo4-v12-evaluation.v1.yaml)
record the evidence behind public gateway quality paths. The gateway exposes
only their reviewed, versioned recipe definitions—not arbitrary node choices.
The [20-step base evaluation manifest](h3-base20-evaluation.v1.yaml) defines
the non-Turbo candidate: its graph removes, rather than zeroes, the Turbo LoRA
and sigma-shift override nodes so it uses H3's native 12/3 shift defaults.
Its real-model screen is recorded in the portrait cross-geometry review and it
is available as public quality `8`.
The bounded [dialogue visual-text robustness study](h3-prompt-robustness-study.v1.yaml)
tests prompt rendering against visible-text artifacts without changing an
admitted profile; its Spark-only runner lives in `tools/`.

### Bounded prompt study runner

Run the study only on Spark, directly against loopback ComfyUI, while its
queue is empty. It requires an existing image already under ComfyUI's input
mount and writes its media under the supplied experiment subfolder:

```sh
python3 services/minimax_h3_gateway/tools/h3_prompt_robustness_study.py \
  --template services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json \
  --input-name <existing-comfy-input.png> \
  --output-subfolder experiments/<study-id> \
  --receipt /home/wjmao/services/spark-comfyui/data/output/experiments/<study-id>-receipt.json
```

It submits twelve direct, serial ComfyUI experiments: three fixed seeds × two
declared recipes × two prompt contracts. It refuses to begin if ComfyUI already
has queued work. Its JSON receipt contains identifiers, prompt hashes, output
descriptors and timings—not prompt text, credentials, or a profile promotion.

The separate `tools/h3_vertical_recipe_qualification.py` runs the larger,
vertical-first qualification matrix declared in
[`h3-vertical-recipe-qualification.v1.yaml`](h3-vertical-recipe-qualification.v1.yaml).
It compares complete recipes only; it is not a gateway operation or a public
profile selector.

The local service contract has five bearer-authenticated client operations plus
one unauthenticated health route. Creation uses a required exact `resolution`
and optional `quality` (default `1`); it never accepts `profileId`:

1. `POST /v1/video-jobs/from-image` accepts a required start frame and optional
   end frame (multipart files or JSON URLs) and durably queues one job.
2. `POST /v1/video-jobs/from-text` is an exploration-only text-to-video route;
   Plotloom does not expose it as an authoring mode.
3. `GET /v1/video-jobs/{id}` reports a known job, its resolved seed, snapped
   frame count, actual duration, and backend elapsed timing.
4. `GET /v1/video-jobs/{id}/output` serves its gateway-managed completed MP4.
5. `POST /v1/video-jobs/{id}/cancel` cancels only a still-queued job.
6. `GET /health` exposes safe readiness, input modes and queue counts without
   a bearer key.

`POST /v1/assets` and `POST /v1/video-jobs` are deliberately retired. There
is no public asset-ID, idempotency-key, or compatibility creation path.

For a colleague-facing, copy-paste client guide—including Spark's current
Tailnet base URL and a test image—see
[`docs/operations/minimax-h3-gateway-client-guide.md`](../../docs/operations/minimax-h3-gateway-client-guide.md).

The gateway owns one FIFO dispatch worker. Its queue is intentionally not
length-capped: one H3 **or** Qwen inference request runs at a time while any
further jobs remain durably queued. This is a concurrency guarantee, not a
retention policy; see [ADR 0072](../../docs/adr/0072-shared-qwen-image-and-h3-generation-lane.md).

After completion, the gateway atomically hands off its one expected MP4 from
the mounted ComfyUI output directory into gateway-managed storage, then
removes the ComfyUI source. It retains that managed copy for 72 hours; see
[ADR 0039](../../docs/adr/0039-h3-gateway-managed-output-retention.md).
The corresponding SQLite job record is removed 30 days after that handoff,
rather than 30 days after the MP4 expires.
No gateway-owned uploaded keyframe remains beyond 30 days, whether or not it
was used by a job. A completed job can release its keyframe earlier when its
last managed MP4 expires. This does not affect Plotloom's canonical project
assets.

New gateway-owned keyframes, prepared inputs, and completed clips use a
portable UTC timestamp prefix (`YYYY-MM-DDTHH-MM-SSZ_`) before their stable
`asset_…` or `h3_…` ID. The ID remains the API identifier; the timestamp is
there for on-host inspection. Deploy the naming contract with a clean gateway
state rather than preserving UUID-only files.

## Qwen-Image-2.1 contract

The same authenticated gateway also accepts text-to-image and **single**
reference-image edit jobs at `/v1/image-jobs`. Initial admission is exactly
`1024x1024`, one PNG output, 40 steps and CFG 1. `backgroundMode` is either
`opaque` or `transparent`; transparent requests must return actual PNG alpha
and are never postprocessed into a cutout. Multi-image editing is not part of
this contract. See [the Spark Qwen setup guide](docs/qwen-image-spark-setup.md)
and [ADR 0072](../../docs/adr/0072-shared-qwen-image-and-h3-generation-lane.md).

Keep ComfyUI on `127.0.0.1:8188`, bind this gateway only to Spark's Tailscale
address, and keep its bearer key server-side. Do not replace the documented
quality catalog with an SSH-only edit: quality changes require a new versioned
gateway/Plotloom contract and verification.

## Module boundary and future extraction

This directory is the git-tracked source module for the gateway: its container
definition, environment template, typed HTTP service, and profile catalog stay
together under `services/minimax_h3_gateway/`. Plotloom's adapter deliberately
lives elsewhere under `src/plotloom/video_backends/minimax_h3/`; it consumes
the versioned HTTP contract and must not import gateway runtime code.

That boundary keeps the current same-repository deployment reproducible while
allowing a later extraction into its own repository without changing the
Plotloom production contract. Until such an extraction is explicitly approved,
gateway source changes, profile changes, and their operator documentation are
reviewed and versioned here with Plotloom.

## Runtime layout

The gateway package keeps one responsibility per module:

- `api.py` owns FastAPI routing and authentication;
- `gateway.py` coordinates durable jobs without owning transport or files;
- `comfy.py` owns the narrow ComfyUI readiness/history/submission transport;
- `media.py` owns uploaded keyframes, prepared inputs, MP4 handoff and cleanup;
- `store.py` owns the SQLite control plane;
- `workflow.py`, `naming.py`, and `contracts.py` own the frozen workflow,
  timestamped naming, and public settings/contracts respectively.

`app.py` is intentionally only a compatibility export surface. Keep new logic
in the responsible module rather than growing that façade.

For new H3 work, Plotloom normally sends an aspect-matched keyframe directly
with
`reject_mismatch`. An explicit author-owned `allowLetterbox` mode instead
freezes gateway `contain_pad`; this gateway receives the documented
`aspectPolicy` only and does not infer author intent.
