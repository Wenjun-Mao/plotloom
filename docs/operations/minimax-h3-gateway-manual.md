# MiniMax-H3 gateway: operator and maintainer manual

**Status:** the documented H3 path is live on `main` as one deliberately
limited, private video backend. This is the human-facing handoff entry point
for operating, verifying, and changing it. It does not contain a bearer
secret, raw prompt, or customer media. Colleagues who need to call the private
service should use the separate, copy-paste
[client guide](minimax-h3-gateway-client-guide.md), which records the current
Tailnet base URL and a non-secret test image.

Qwen-Image-2.1 is a separate image backend with its own
[operator manual](qwen-image-gateway-manual.md),
[Chinese client guide](qwen-image-gateway-client-guide.md), and
[reproducible setup guide](../../services/minimax_h3_gateway/docs/qwen-image-spark-setup.md).
The two backends share the durable FIFO, but their generation contracts and
runtime maintenance procedures are not interchangeable.

For exact machine-readable behavior, the source profile and tests remain the
implementation authority. This manual links them rather than duplicating an
unsafe or easily stale deployment recipe.

The underlying Spark/ComfyUI installation is documented separately from this
gateway runbook: [reproducible setup guide](../../services/minimax_h3_gateway/docs/h3-reproducible-setup.md),
[rationale and operations manual](../../services/minimax_h3_gateway/docs/h3-rationale-and-operations.md),
and [current-installation manifest](../../services/minimax_h3_gateway/h3-current-installation.v1.yaml).
The qualification manifests record the evidence behind the currently admitted
quality paths. A running H3 container alone is never proof of creative
acceptance.

## 1. What this system is—and is not

Plotloom uses MiniMax-H3 through a small authenticated gateway running on
Spark. The gateway owns four reviewed quality paths and six exact output
resolutions, not arbitrary dimensions or ComfyUI graphs:

| Tier | Landscape | Portrait |
| --- | --- | --- |
| Fast | 832×480 | 576×1024 |
| Standard | 960×544 | 608×1088 |
| High resolution | 1280×704 | 704×1280 |

| `quality` | Frozen path |
| ---: | --- |
| 1 | V1.2 Turbo-4 / Euler / explicit 6:3 shifts |
| 2 | V1.0 Turbo-4 / res_multistep / explicit 6:3 shifts |
| 3 | V1.0 Turbo-8 / Euler / explicit 6:3 shifts |
| 8 | Base-20 / res_multistep / native 12:3, no Turbo LoRA |

Quality 1 remains the gateway's omitted-field default. Plotloom explicitly
offers quality 1 for development and quality 8 for production-review
candidates; its new-work initial choice is quality 8. Neither is a creative
acceptance guarantee.
The gateway can render zero, one, or two H3 frame sockets: text exploration,
start-frame I2V, or start/end-frame I2V. It accepts requested
whole-second durations 5–15 and snaps them to the node's 24 fps `17k + 5`
frame grid (5 seconds is 124 frames, about 5.167 seconds). Output is H.264/AAC.
Portrait 576×1024 is Plotloom's new-job default. “High resolution” means more
pixels only; it is not a creative-quality or production-ready claim.

It is **not** a general ComfyUI proxy. Neither Plotloom nor a browser can send
arbitrary graph JSON, custom node names, model paths, seed overrides outside a
frozen job, dimensions, duration, or a provider endpoint. The gateway accepts
only a frozen prompt, a quality, an exact resolution, permitted duration/seed
choices, and—where I2V is used—an explicit input-aspect policy.

The gateway can create a video with an AAC track. It does not mean dialogue,
lip sync, performance, voice continuity, character continuity, or a creative
selection has passed. Those remain human review decisions in Plotloom.

## 2. Architecture and trust boundary

```text
Plotloom server                         Spark (private Tailnet host)
---------------                         -----------------------------
server-only bearer key ───────────────► H3 gateway :8090
frozen video snapshot                   (typed, authenticated API)
                                           │ host networking only
browser ◄──── reviewed MP4 candidate ◄────┤
  no endpoint or key                      ▼
                                      ComfyUI :8188
                                      bound to 127.0.0.1
                                      reviewed H3 quality/resolution catalog + local models
```

The browser talks only to Plotloom. Plotloom's H3 transport accepts a
credential-free loopback, private-LAN, or `100.64.0.0/10` Tailnet host root;
the intended deployment is the Spark Tailnet address. ComfyUI must remain on
`127.0.0.1:8188`. Do not bind it to a LAN interface, Tailnet interface, or the
internet.

The one bearer value is stored twice by design: as `H3_API_KEY` for the
gateway and `VIDEO_MODEL_API_KEY` for the Plotloom server. They must be the
same secret. It is never a browser setting, a project field, an artifact, or a
loggable URL credential.

The implementation and decision records are:

- Gateway service: [`services/minimax_h3_gateway`](../../services/minimax_h3_gateway/)
- Gateway catalog: [`profile_catalog.py`](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/profile_catalog.py)
- Active profile-rendered workflow: [`minimax_h3_template_v2.json`](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json)
- Plotloom adapter: [`adapter.py`](../../src/plotloom/video_backends/minimax_h3/adapter.py)
  and [`transport.py`](../../src/plotloom/video_backends/minimax_h3/transport.py)
- Boundary decisions: [ADR 0033](../adr/0033-private-minimax-h3-gateway.md), [ADR 0036](../adr/0036-minimax-h3-profile-catalog.md)
  and [ADR 0034](../adr/0034-provider-neutral-video-adapters-and-local-h3.md);
  [ADR 0035](../adr/0035-backend-owned-video-modules.md) records the module
  and service-package ownership boundary, while [ADR 0038](../adr/0038-h3-gateway-durable-fifo-dispatch.md)
  records the gateway-owned FIFO worker. [ADR 0050](../adr/0050-unified-h3-generation-contract.md)
  records the direct-generation boundary and [ADR 0070](../adr/0070-h3-quality-resolution-contract.md)
  records the quality/resolution clean cutover.

## 3. Before deployment

### Spark prerequisites

1. Docker and Docker Compose are available on Spark.
2. ComfyUI is running and is reachable only at `http://127.0.0.1:8188` from
   the host.
3. The built-in MiniMax-H3 node and the exact profile assets are installed in
   ComfyUI. The gateway's readiness check requires the following values to
   appear in ComfyUI's `/object_info` response:

   ```text
   MiniMaxH3ImageToVideo
   MiniMaxH3SigmaShift
   minimax_h3_fl2va_pruned_fp8_scaled.safetensors
   qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
   minimax_h3_video_vae_fp16.safetensors
   minimax_h3_audio_vae_fp32.safetensors
   minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors
   minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors
   minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors
   ```

4. Keep the large model artefacts under `/home/wjmao/models`. Configure
   ComfyUI's model paths or symlinks to use that location. The gateway does
   not search that directory itself—it only verifies what ComfyUI advertises—so
   a file being present there is not sufficient proof that the profile is
   ready.
5. Choose three persistent, private host directories:
   - gateway state, uploaded assets, and its managed completed MP4s;
   - the directory mounted as ComfyUI's input directory;
   - the directory mounted as ComfyUI's output directory.

   Do not place any of them inside the Plotloom checkout, a temporary
   directory, or a shared public folder. The gateway records asset hashes and
   job recovery state in SQLite, moves only its validated completed H3 MP4
   from ComfyUI output into its own storage, and expires that copy after 72
   hours. ComfyUI output is therefore a handoff source, not the retained
   delivery location.

### Network and key prerequisites

- Obtain Spark's Tailnet address. It is a deployment value, not repository
  documentation.
- Generate a long random bearer secret and protect the gateway `.env` with
  restrictive local permissions. Do not reuse a text or image-provider key.
- Leave both paid-Wan and H3 flags disabled until the health check succeeds.
  Plotloom refuses to enable both at once.

## 4. Deploy or restart the gateway on Spark

From the checked-out Plotloom repository on Spark:

```sh
cd services/minimax_h3_gateway
cp .env.example .env
chmod 600 .env
```

Edit only the deployment values in `.env`:

```dotenv
# Spark's Tailnet address; never 0.0.0.0.
H3_BIND_ADDRESS=100.x.y.z
H3_PORT=8090

# A new, private bearer secret.
H3_API_KEY=replace-with-a-long-random-secret

# ComfyUI stays loopback-only.
H3_COMFY_URL=http://127.0.0.1:8188
# H3 dispatch is always serial. Queue length is intentionally unlimited.
H3_WORKER_POLL_SECONDS=0.5
H3_DISPATCH_WORKER_ENABLED=true

# Private, persistent host paths.
H3_GATEWAY_DATA_HOST_DIR=/home/wjmao/services/plotloom-h3-gateway/data
H3_COMFY_INPUT_HOST_DIR=/path/to/the/comfyui/input/directory
# Must be ComfyUI's exact output directory, writable by the gateway so it can
# move only its validated completed H3 MP4s into gateway-managed storage.
H3_COMFY_OUTPUT_HOST_DIR=/path/to/the/comfyui/output/directory
```

`docker-compose.yml` uses host networking so the gateway can reach the host's
loopback-only ComfyUI. It binds the gateway only to `H3_BIND_ADDRESS`; this is
why using `0.0.0.0` is prohibited.

Start after the H3 profile is actually visible in ComfyUI:

```sh
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 gateway
curl --fail http://100.x.y.z:8090/health
```

An expected health response is structurally equivalent to:

```json
{
  "status": "ok",
  "generationContractVersion": 6,
  "defaultQuality": 1,
  "qualities": [1, 2, 3, 8],
  "resolutions": ["832x480", "960x544", "1280x704", "576x1024", "608x1088", "704x1280"],
  "queuedJobs": 0,
  "activeDispatches": 0,
  "dispatchConcurrency": 1
}
```

`/health` intentionally performs a ComfyUI/profile preflight. A running
container is therefore not enough: do not enable Plotloom until `/health`
returns `ok` with all four quality paths and contract version.

For an ordinary restart after configuration-free changes:

```sh
docker compose restart gateway
docker compose logs --tail=100 gateway
curl --fail http://100.x.y.z:8090/health
```

Never use the real bearer value directly on a shell command line or paste it
into a ticket. For an authenticated contract check, load it from the protected
environment in a secure operator shell; do not put it into shell history.

## 5. Enable Plotloom deliberately

On the machine that runs Plotloom, add these server-only values to the
repository-root `.env` (or equivalent protected process environment):

```dotenv
PLOTLOOM_ENABLE_WAN_P2=false
PLOTLOOM_ENABLE_H3_GATEWAY=true
VIDEO_PROVIDER=minimax_h3_gateway
VIDEO_BASE_URL=http://100.x.y.z:8090
VIDEO_MODEL=minimax_h3_gateway_catalog_v7
VIDEO_AUTH_MODE=bearer
VIDEO_MODEL_API_KEY=the-same-value-as-H3_API_KEY
```

`VIDEO_MODEL=minimax_h3_gateway_catalog_v7` is Plotloom's default admission
marker. Plotloom sends its reviewed image bytes with the explicitly frozen
quality `1` or `8`, selected exact resolution, and 5–15 integer-second request.
It does not expose T2V or gateway qualities 2/3 as authoring choices. The
playback segment path still has its narrower reviewed source-timing contract.

Restart Plotloom after changing `.env`. A host environment variable takes
precedence over `.env`, so investigate both if the running service reports an
unexpected backend. Never expose the endpoint or key in the browser. The
workbench may select a reviewed catalog profile and display its capability,
but it cannot choose an arbitrary backend, graph, or dimension.

The public API's `GET /api/v2/video-backend` is the safe way to check what
Plotloom believes is enabled. It must identify the H3 adapter and reviewed
profile catalog but never return the secret.

To disable H3 safely, set `PLOTLOOM_ENABLE_H3_GATEWAY=false` and restart
Plotloom. Do not delete the gateway's state merely because it is disabled:
historical known-job evidence must stay recoverable until the project's normal
retention decision says otherwise.

## 6. What happens during a Plotloom H3 job

The production sequence is intentional and one-way:

1. A user has a valid project, a selected and approved keyframe, and—when a
   visible character exists—an applicable, human-reviewed character reference.
2. A new Plotloom job requires an aspect-matched reviewed keyframe and freezes
   `reject_mismatch` in its immutable production snapshot. For a deliberate
   framed image inside a larger canvas, the author can explicitly opt into
   **allow letterbox**, which freezes `contain_pad`; it does not waive any
   keyframe, provenance, profile, approval, identity or output checks. Plotloom
   also offers reviewed crop and ImageGen adaptation preparation before this
   point. The snapshot freezes the keyframe, character references, approval,
   adapter/version, profile, prompt, seed, and input policy.
3. Plotloom checks the gateway contract and sends the frozen keyframe directly
   as one multipart `from-image` request. The gateway owns transient frame
   admission itself; no gateway asset ID or idempotency key crosses this
   boundary. The gateway accepts it into its local FIFO queue without waiting
   for H3. Its one worker is the only component that
   may later submit to ComfyUI, and it never retries a submission whose
   outcome might be unknown.
4. Plotloom polls only the known gateway job ID. The gateway copies, verifies,
   and removes its exact completed MP4 from ComfyUI output before it reports
   success. Plotloom retrieves bytes only through that gateway ID—never from
   a provider-controlled output URL or a ComfyUI endpoint.

5. It probes the downloaded bytes. The candidate is eligible only if it is
   H.264/AAC, the exact frozen width/height, 24 fps, and the frame count bound
   to that job's frozen request on the `17k+5` grid (for example 124 for five,
   192 for eight, and 362 for fifteen seconds).
   Observed duration must also be within one frame of the frozen frame-count
   duration. A merely playable mismatch becomes `retrieve_needed` with
   `h3_output_profile_mismatch` and cannot be selected.
6. The resulting candidate is unselected. A human reviews visual continuity,
   dialogue/audio quality, and creative suitability before an explicit
   selection. It never changes canonical story data.

### Input-aspect policy

The gateway emits the selected catalog geometry. It will not silently stretch
an approved still. It retains all three policies so historical frozen jobs stay
interpretable, but new Plotloom work uses only the first and third rows below:

| Policy | Gateway behavior | Choose it when |
| --- | --- | --- |
| `cover_center_crop` | centre-crops to the selected geometry, then resizes | historical frozen jobs only; new Plotloom work creates a reviewed crop first |
| `contain_pad` | preserves the full image and pads to the selected geometry in black | an author explicitly chose **allow letterbox** for that frozen job |
| `reject_mismatch` | rejects an input whose ratio differs from the selected profile | the default for new Plotloom work; the input is already compositionally exact |

The gateway receives the frozen policy but does not infer author intent from a
file extension or silently select a policy. The decision boundary and required
review path are recorded in [ADR 0037](../adr/0037-reviewed-keyframe-aspect-preparation.md).

## 7. Gateway HTTP contract for maintenance only

The following is a private service contract; it is not a browser API.

| Endpoint | Auth | Purpose |
| --- | --- | --- |
| `GET /health` | no bearer header | Checks ComfyUI and catalog; returns status, direct input modes, safe profile descriptors, queue count and fixed concurrency |
| `POST /v1/video-jobs/from-image` | bearer | Required start image plus optional end image: multipart `image`/`endImage`, or JSON `sourceUrl`/`endSourceUrl`; queues one I2V job |
| `POST /v1/video-jobs/from-image-with-voice` | bearer | Separate Ref2VA Base-20 path: one start frame and one bounded WAV, multipart `image`/`voiceAudio` or JSON `sourceUrl`/`voiceSourceUrl` |
| `POST /v1/video-jobs/from-text` | bearer | JSON text exploration only; no Plotloom authoring path and no image/aspect fields |
| `GET /v1/video-jobs/{id}` | bearer | Refreshes a known job |
| `POST /v1/video-jobs/{id}/cancel` | bearer | Cancels only a job that is still `queued` |
| `GET /v1/video-jobs/{id}/output` | bearer | Streams the known gateway-managed completed MP4 |

`POST /v1/assets` and `POST /v1/video-jobs` are retired and return 404.
Job response fields are deliberately closed: `id`, `status`, `inputMode`,
resolved `quality`, `resolution`, `aspectPolicy`, `seed`, `requestedDurationSeconds`,
`frameCount`, `actualDurationSeconds`, `generationSubmittedAt`,
`generationCompletedAt`, `generationElapsedMs`, `error`, and `outputReady`.
`generationElapsedMs` starts after ComfyUI accepts the workflow and ends when
completion is observed; it excludes image preparation and managed-file handoff.
Valid states are `reserved` (legacy only),
`queued`, `submitting`, `submitted`, `running`, `transfer_pending`,
`succeeded`, `failed`, `cancelled`, and `outcome_unknown`. A retained job can
remain `succeeded` with `outputReady: false` after its MP4 expires.
New jobs return `queued`; the gateway's single worker owns the only transition
that can submit to ComfyUI.
Only the Ref2VA creation receipt adds `voiceReferenceSha256` for caller-side
provenance comparison; ordinary status does not expose the voice file, hash,
URL or path. Its status projects `inputMode=image_voice`, `quality=8`; the
`h3_contract=ref2va` database field distinguishes it from FL2VA Base-20.

Ref2VA is an optional checkpoint under `/home/wjmao/models/comfyui-h3`.
`/health` reports `voiceReferenceReady` independently; admission performs a
fresh Ref2VA preflight before retaining inputs. A missing Ref2VA model/node
must not make existing FL2VA jobs or their frozen snapshots disappear. The
new path admits only 960×544 or 576×1024, 5–8 requested seconds, and a
1–10-second, at-most-2-MiB PCM16/mono/32-kHz WAV. It canonicalizes the WAV
header without trimming or changing the reference samples. It is a timbre
and delivery reference, not an exact transcript, waveform or lip-sync promise.
The frozen snapshot and private audio binding are defined in
[ADR 0090](../adr/0090-h3-ref2va-per-job-voice-reference.md); Plotloom owns
stable Voice IDs and candidate retention in a separate product checkpoint.

For private internal callers, `sourceUrl` accepts `http` and `https`, including
Tailnet URLs. The gateway follows at most three redirects, uses a 5-second
connect and 20-second read timeout by default, streams no more than 20 MiB,
then identifies the decoded image bytes as JPEG/PNG/WebP. It retains neither
the source URL nor a copy of its query string. This is deliberately a trusted
Tailnet MVP; do not expose it to untrusted networks without a new URL-fetch
security decision.

The gateway deliberately imposes no job-count limit. It serializes H3 work and
persists FIFO order in gateway SQLite; it does not treat ComfyUI's generic
backlog as its own queue. If ComfyUI has trusted external work, the worker
waits before submitting the next gateway job. See [ADR 0038](../adr/0038-h3-gateway-durable-fifo-dispatch.md).

### Managed output handoff and retention

The gateway has a writable mount of ComfyUI's output directory, but it never
serves that directory. When ComfyUI reports the one expected MP4, the gateway
copies it into `H3_GATEWAY_DATA_HOST_DIR/outputs`, fsyncs and hashes the copy,
then removes that exact source file. Only then is the job `succeeded` and
downloadable. A restart during this step leaves `transfer_pending`; the worker
resumes the frozen transfer without generating another video.

New gateway-owned files begin with a human-readable UTC allocation timestamp,
then retain their immutable API ID: `YYYY-MM-DDTHH-MM-SSZ_asset_<uuid>.<ext>`
for admitted frames, `YYYY-MM-DDTHH-MM-SSZ_h3_<uuid>_start.png` or `_end.png`
for prepared ComfyUI inputs, and `YYYY-MM-DDTHH-MM-SSZ_h3_<uuid>.mp4` for
completed clips.
Ref2VA additionally uses `YYYY-MM-DDTHH-MM-SSZ_h3_<uuid>_voice.wav` in both
the private gateway input directory and ComfyUI's mounted input directory.
The original submission hash and prepared-file hash are separate frozen
values. Audio and its prepared first frame remain while queued/running,
then are released at successful MP4 expiry or after 30 days for terminal
unsuccessful jobs. A 30-day record purge cannot bypass an audio-file deletion
failure.
The timestamp tells an operator when the gateway created its copy; use the
embedded `asset_…` or `h3_…` ID for API requests and forensic correlation.
Deploy this as a clean gateway-state cutover: reset prior gateway SQLite and
managed files instead of carrying a second filename convention.

Gateway-managed MP4s are deleted 72 hours after that handoff. Their SQLite job
record remains `succeeded`, but its `outputReady` flag is false and an output
not retrieved by then is reported as `h3_gateway_output_expired` to Plotloom.
It is not recreated or silently accepted. The cleanup loop considers only
exact database-owned gateway output names—it never performs a broad cleanup of
ComfyUI output or the gateway data directory. See [ADR 0039](../adr/0039-h3-gateway-managed-output-retention.md).

The succeeded job record—and its stored prompt—remains only until 30 days after
the original successful handoff. After that total deadline, a gateway status
or output request returns `job_not_found`; there is no MP4 to retrieve or
recreate. At the earlier 72-hour MP4 expiry, the gateway already removes that
job's prepared ComfyUI input and may delete a keyframe when no linked gateway
video remains unexpired. Independently, no gateway-uploaded keyframe survives
beyond 30 days from upload. The database keeps only a small inaccessible
metadata row while a job still requires it for SQLite foreign-key integrity.
This applies only to transient gateway copies, never to a Plotloom project
asset or character reference.

An `outcome_unknown` means the gateway cannot establish whether the submission
reached ComfyUI. Treat it as non-replayable. Diagnose it using the gateway
database, ComfyUI history, and logs; do not submit the same job again “just in
case.”

## 8. Troubleshooting and recovery

| Symptom or code | Likely cause | Safe action |
| --- | --- | --- |
| gateway container exits at startup | missing `H3_API_KEY` or an invalid path/setting | correct protected `.env`, then restart; do not weaken authentication |
| `/health` returns `comfy_unavailable` | ComfyUI is down, not loopback-reachable, or not responding | restore ComfyUI at `127.0.0.1:8188`, then repeat health check |
| `/health` returns `comfy_profile_unavailable` | node or exact model/LoRA/VAE name is missing from ComfyUI | fix ComfyUI's installed profile/model mapping under `/home/wjmao/models`; do not edit a running gateway workflow to bypass the check |
| `401 unauthorized` | bearer mismatch between caller and gateway | rotate/align `H3_API_KEY` and Plotloom's `VIDEO_MODEL_API_KEY`, then restart both services as needed |
| `job_not_cancellable` | job may already have crossed into ComfyUI | retain and poll the known job; only `queued` work can be cancelled safely |
| `request_fields_invalid` | URL/file channels were mixed, a field repeated, or retired `idempotencyKey` was sent | use exactly one direct input channel and the documented fields only; do not blindly retry a timeout |
| `input_aspect_mismatch` | `reject_mismatch` received a keyframe whose ratio differs from the selected profile | choose a different explicit policy or supply a matching keyframe |
| `outcome_unknown` | request/response path failed after the durable record was created | inspect the known gateway job and ComfyUI history; never automatically replay |
| `comfy_output_missing` | ComfyUI did not save the one expected MP4 before gateway handoff | inspect the known job and ComfyUI history; preserve evidence, do not claim a candidate was ingested |
| `gateway_output_transfer_pending` | the gateway copied or is copying the exact output but has not safely removed the ComfyUI source | retain the known job and let the worker retry the frozen handoff; do not generate again |
| `gateway_output_integrity_mismatch` | a source file changed after a partial gateway copy | preserve both files for inspection; the gateway will not publish or delete either one |
| `gateway_output_expired` | the completed gateway-owned MP4 exceeded its 72-hour retention | retain the job evidence; Plotloom records `h3_gateway_output_expired` and never treats expiry as a retryable generation |
| `h3_output_profile_mismatch` in Plotloom | received MP4 did not match the frozen codec/frame profile | retain the evidence, inspect ComfyUI/profile drift, and correct the profile boundary rather than accepting the file |
| Plotloom says H3 is unavailable | H3 flag/key/provider/model is inconsistent, both backends are enabled, or Plotloom cannot preflight | correct the server configuration and restart; browser settings cannot fix it |

Gateway state is stored in `gateway.sqlite3` beneath
`H3_GATEWAY_DATA_HOST_DIR`, alongside uploaded assets and the gateway-managed
`outputs/` directory. It includes job prompts and therefore must be treated as
private production data. Back it up under the same access restrictions as
project data. The gateway removes only its known source MP4s from the mounted
ComfyUI output directory and expires its own copies after 72 hours. Never use
a broad cleanup command against either directory.

## 9. Change management

Do **not** make any of the following as an SSH-only tweak:

- replace a model filename in the frozen profile;
- change dimensions, frame count, FPS, duration, step count, or audio path;
- expose ComfyUI or the gateway publicly;
- point Plotloom at another model or arbitrary URL;
- accept a mismatched output because it plays in a browser.

Each alters a production contract. The required path is: add a versioned
quality path in source, update the separate Plotloom adapter capability,
freeze it in gateway job snapshots, add request/response/output tests, run a
bounded probe, record the evidence, and then enable it deliberately. This is
a clean cutover: prior `profileId` state must be archived and reset, never
migrated or replayed under a new quality meaning.

Normal code updates are safer: pull a reviewed `main`, rebuild the gateway
image, verify `/health`, run the relevant Plotloom checks, and only then
restart the production services. Roll back by deploying the previous reviewed
source revision and retain the existing gateway state volume.
The Ref2VA release is additive: it migrates the existing SQLite control plane
without resetting FL2VA jobs or their frozen snapshots. Before deployment,
check that no gateway job is actively submitting, verify the Ref2VA model hash
and Comfy nodes, and retain a scoped database copy for rollback. Deploy only
the reviewed gateway revision; do not live-edit its Python source on Spark.

## 10. Evidence, current limits, and next review

What has been directly evidenced:

- one Mandarin line under one prompt and keyframe was watched by a reviewer as
  intelligible and lip-synced;
- a real temporary Plotloom → gateway → MP4 ingestion path completed once
  without resubmission and produced an unselected candidate.
- all six current H3 catalog geometries delivered their exact H.264/AAC,
  124-frame, 24-fps media contract in a bounded Spark probe.

See the secret-free records:

- [Mandarin dialogue probe](../verification/2026-09-13-h3-mandarin-dialogue-probe.md)
- [adapter and live-ingestion verification](../verification/2026-09-13-p2-h3-adapter-isolated.md)
- [v2 profile catalog probe](../verification/2026-09-13-h3-profile-catalog-probe.md)

These are not proof of universal dialogue quality, voice locking, same-person
continuity, cross-shot motion/lighting continuity, production readiness, or
comparative creative performance at any catalog geometry. The catalog
geometry/media contract is evidenced; the next intended review is still
required before a profile is treated as a useful sequential-storytelling
baseline.
The next intended product checkpoint is a retained, human-reviewed pair of
adjoining shots from the same selected character reference. Only that review
can establish whether this H3 baseline is useful for sequential storytelling.

## 11. Fast handoff checklist

Before an operator declares the H3 path usable after a restart or handoff:

- [ ] ComfyUI is loopback-only and `/health` reports generation contract version 6, all four quality values, and all six resolutions.
- [ ] H3 model artefacts remain under `/home/wjmao/models` and are visible to
      ComfyUI under the exact required names.
- [ ] Gateway is bound to Spark's Tailnet address, not `0.0.0.0`.
- [ ] Gateway and Plotloom have matching server-only bearer keys; no key has
      entered a URL, browser, repository, or project record.
- [ ] Exactly H3—not H3 and Wan—is enabled in Plotloom.
- [ ] Plotloom has been restarted after configuration changes and reports the
      H3 profile through its safe backend status projection.
- [ ] Gateway state/input/output mounts are private and persistent; the
      gateway-managed `outputs/` retention is 72 hours and ComfyUI output is
      mounted writable only for exact gateway handoff files.
- [ ] A new candidate stays unselected until a human reviews the actual MP4.
