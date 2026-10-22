# Plotloom generation gateway

This is the private, typed API in front of Spark's loopback-only ComfyUI H3
service and loopback-only SGLang Qwen-Image service. It is deliberately **not**
a backend proxy: callers cannot submit workflows, select model files, or reach
either runtime directly.

Plotloom is wired to this gateway through the versioned
`minimax_h3_gateway.v6` adapter contract. The two backend-specific document
sets are intentionally separate:

- **H3 video:** [operator manual](../../docs/operations/minimax-h3-gateway-manual.md),
  [Chinese client guide](../../docs/operations/minimax-h3-gateway-client-guide.md),
  [reproducible setup](docs/h3-reproducible-setup.md), and
  [sampling rationale](docs/h3-rationale-and-operations.md).
- **Qwen image:** [operator manual](../../docs/operations/qwen-image-gateway-manual.md),
  [Chinese client guide](../../docs/operations/qwen-image-gateway-client-guide.md),
  and [reproducible Spark setup](docs/qwen-image-spark-setup.md).

The [media-service ownership and release guide](../../docs/operations/media-services.md)
maps independent packages/deployments and the durable, one-active-inference FIFO.

For the underlying Spark/ComfyUI engine rather than the gateway API, use the
[reproducible H3 setup guide](docs/h3-reproducible-setup.md), the
[H3 rationale and operations manual](docs/h3-rationale-and-operations.md), and
the secret-free [D adoption manifest](h3-vae-d-adoption.v1.yaml).
ComfyUI 0.38.0 is unchanged from its [September foundation](h3-runtime-038-adoption.v1.yaml).
D adds a maintained video-only FP16/INT8 loader and FP16 accumulation while
global/audio BF16 remains unchanged; original containers are retained. The original
0.35 image/container/user directory preserved. The
[installation inventory](h3-current-installation.v1.yaml) captures historical
foundation assets; it is not today's runtime or recipe status. New work uses the
reviewed quality/resolution catalog below, not the historical v1 template.

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

The local service contract has six bearer-authenticated client operations plus
one unauthenticated health route. Ordinary FL2VA creation uses a required exact
`resolution` and optional `quality` (default `1`); it never accepts `profileId`:

1. `POST /v1/video-jobs/from-image` accepts a required start frame and optional
   end frame (multipart files or JSON URLs) and durably queues one job.
2. `POST /v1/video-jobs/from-text` is an exploration-only text-to-video route;
   Plotloom does not expose it as an authoring mode.
3. `POST /v1/video-jobs/from-image-with-voice` accepts one first frame and one
   short voice-reference WAV for the separate Ref2VA Base-20 path. It does not
   accept FL2VA `quality` or an end frame; see [ADR 0205](../../docs/adr/0205-h3-ref2va-per-job-voice-reference.md).
4. `GET /v1/video-jobs/{id}` reports a known job, its resolved seed, snapped
   frame count, actual duration, and backend elapsed timing.
5. `GET /v1/video-jobs/{id}/output` serves its gateway-managed completed MP4.
6. `POST /v1/video-jobs/{id}/cancel` cancels only a still-queued job.
7. `GET /health` exposes safe readiness, input modes and queue counts without
   a bearer key.

`POST /v1/assets` and `POST /v1/video-jobs` are deliberately retired. There
is no public asset-ID, idempotency-key, or compatibility creation path.

For a colleague-facing, copy-paste client guide—including Spark's current
Tailnet base URL and a test image—see
[`docs/operations/minimax-h3-gateway-client-guide.md`](../../docs/operations/minimax-h3-gateway-client-guide.md).

The gateway owns one FIFO dispatch worker. Its queue is intentionally not
length-capped: one H3, Qwen image **or** Voice Lab generation runs at a time while
further jobs remain durably queued. All Lab creation/clone/take entrypoints register
through the same lane. Unknown outcomes and unproven child release block dispatch,
without replay. See [ADR 0212](../../docs/adr/0212-published-voice-performance-takes-and-shared-admission.md).

The authenticated `/v1/voice-takes` facade delegates voice resolution and durable
audio ownership to the CPU Voice Lab control service, not gateway media tables.
See the [Chinese client guide](../qwen3_tts_voice_lab/docs/voice-takes-client-guide.md)
and [deployment/recovery](../qwen3_tts_voice_lab/docs/reproduction-and-operations.md).
H3 video still requires explicit audio bytes; no hidden TTS or ID lookup is added.

After completion, the gateway atomically hands off its one expected MP4 from
the mounted ComfyUI output directory into gateway-managed storage, then
removes the ComfyUI source. It retains that managed copy for 72 hours; see
[ADR 0039](../../docs/adr/0039-h3-gateway-managed-output-retention.md).
The corresponding SQLite job record is removed at the 30-day total retention
deadline, after any bound voice input has been released.
No gateway-owned uploaded keyframe remains beyond 30 days, whether or not it
was used by a job. A completed job can release its keyframe earlier when its
last managed MP4 expires. This does not affect Plotloom's canonical project
assets.

New gateway-owned keyframes, prepared inputs, and completed clips use a
portable UTC timestamp prefix (`YYYY-MM-DDTHH-MM-SSZ_`) before their stable
`asset_…` or `h3_…` ID. The ID remains the API identifier; the timestamp is
there for on-host inspection. Deploy the naming contract with a clean gateway
state rather than preserving UUID-only files.

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

## Independent package, checks and images

The gateway and dashboard share this service's `pyproject.toml` and `uv.lock`,
not Plotloom's root environment. The installed package has two CPU entrypoints:
`plotloom-h3-gateway` and `plotloom-h3-dashboard`. Install the `gateway` extra
for image preprocessing (Pillow); the dashboard does not need it. Neither role
installs model inference frameworks. Voice Lab retains its own environment.

From the repository root:

```sh
uv sync --project services/minimax_h3_gateway --locked --extra gateway --group test --no-editable
uv run --project services/minimax_h3_gateway --locked --extra gateway --group test --no-editable pytest -q tests/services/minimax_h3_gateway tests/test_media_service_boundaries.py
node --test tests/services/minimax_h3_gateway/test_dashboard*_ui.mjs
sh services/minimax_h3_gateway/tools/packaging/verify_install.sh
```

The last command builds a wheel and exercises both console entrypoints in fresh
role-specific environments, from a temporary working directory with no source
`PYTHONPATH`. It verifies packaged workflow/static files and viewer non-mutation;
it generates nothing. Local port8091 must be free; alternatively run the same
`tools/packaging/smoke.py` inside each isolated image below. Temporary smoke
environments are printed and retained for diagnosis. Root Plotloom's test run
can still use the explicit service-source fixture; that is not artifact proof.

From **this service directory**, build either image independently:

```sh
docker build -f Dockerfile -t plotloom-h3-gateway:20261022-service-boundaries .
docker build -f dashboard.Dockerfile -t plotloom-h3-dashboard:20261022-service-boundaries .
docker run --rm --network none --entrypoint python \
  --mount type=bind,src="$PWD/tools/packaging",dst=/proof,readonly \
  plotloom-h3-gateway:20261022-service-boundaries -I /proof/smoke.py gateway
docker run --rm --network none --entrypoint python \
  --mount type=bind,src="$PWD/tools/packaging",dst=/proof,readonly \
  plotloom-h3-dashboard:20261022-service-boundaries -I /proof/smoke.py dashboard
```

Both build contexts contain only this subtree. `.dockerignore` admits package
source and build metadata, not models, outputs, private configuration or tooling.
Images install the package non-editably; workflow JSON and dashboard assets ship
in the wheel. Gateway Python3.12.14 and dashboard Python3.12.15 retain their
respective pre-cutover patch versions. The initial service lock preserves the
serving gateway dependency closure. Dashboard converges AnyIO4.14.2→4.15.1,
IDNA3.19→3.20 and urllib3 2.7.0→2.8.0 on that existing gateway closure; unrelated
Plotloom template/database dependencies are removed. This is an explicit,
tested packaging reconciliation, not a general dependency update.

Deployment is separate from building. Do not replace a serving artifact during
active, queued or uncertain work, or during a director-reserved generation window.
Use the existing mounts, secrets and deployment configuration; do not start a
second gateway worker. See the release/rollback procedure in the ownership guide.

## Runtime layout

The separate [private dashboard](docs/gateway-dashboard.md) provides operational
job/queue views, retained-media playback and protected H3 submission through Tailscale HTTPS.
Its independent container/entrypoint never initializes the generation store or
starts dispatch workers; the existing API and retention contract are unchanged.

The gateway package keeps one responsibility per module:

- `api.py` owns FastAPI routing and authentication;
- `gateway.py` coordinates durable jobs without owning transport or files;
- `comfy.py` owns the narrow ComfyUI readiness/history/submission transport;
- `media.py` owns uploaded keyframes, prepared inputs, MP4 handoff and cleanup;
- `store.py` owns the SQLite control plane;
- `workflow.py`, `naming.py`, and `contracts.py` own the frozen workflow,
  timestamped naming, and public settings/contracts respectively.
- `voice_reference.py`, `voice_jobs.py`, and `voice_files.py` own only the
  Ref2VA snapshot/graph, admission/dispatch, and private WAV lifecycle.

`app.py` is intentionally only a compatibility export surface. Keep new logic
in the responsible module rather than growing that façade.

For new H3 work, Plotloom normally sends an aspect-matched keyframe directly
with
`reject_mismatch`. An explicit author-owned `allowLetterbox` mode instead
freezes gateway `contain_pad`; this gateway receives the documented
`aspectPolicy` only and does not infer author intent.
