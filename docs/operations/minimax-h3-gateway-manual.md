# MiniMax-H3 gateway: operator and maintainer manual

**Status:** the documented H3 path is live on `main` as one deliberately
limited, private video backend. This is the human-facing handoff entry point
for operating, verifying, and changing it. It does not contain a Tailnet IP,
bearer secret, raw prompt, or customer media.

For exact machine-readable behavior, the source profile and tests remain the
implementation authority. This manual links them rather than duplicating an
unsafe or easily stale deployment recipe.

## 1. What this system is—and is not

Plotloom uses MiniMax-H3 through a small authenticated gateway running on
Spark. The gateway owns a small reviewed profile catalog, not arbitrary
dimensions or ComfyUI graphs:

| Tier | Landscape | Portrait |
| --- | --- | --- |
| Fast | 832×480 | 576×1024 |
| Standard | 960×544 | 608×1088 |
| High resolution | 1280×704 | 704×1280 |

Every selectable entry uses MiniMax-H3 FL2VA FP8, the official 4-step 768p
Turbo LoRA, one approved PNG/JPEG/WebP keyframe, and 124 frames at 24 fps
(about 5.167 seconds) with H.264/AAC output. Portrait 576×1024 is Plotloom's
new-job default. “High resolution” means more pixels only; it is not a
creative-quality or production-ready claim.

It is **not** a general ComfyUI proxy. Neither Plotloom nor a browser can send
arbitrary graph JSON, custom node names, model paths, seed overrides outside a
frozen job, dimensions, duration, or a provider endpoint. The gateway accepts
only a reference asset, an approved prompt, one catalog profile ID, and an
explicit input-aspect policy.

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
                                      reviewed H3 profile catalog + local models
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
- Legacy workflow template: [`minimax_h3_fp8_turbo4_480p.json`](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_fp8_turbo4_480p.json)
- Plotloom adapter: [`adapter.py`](../../src/plotloom/video_backends/minimax_h3/adapter.py)
  and [`transport.py`](../../src/plotloom/video_backends/minimax_h3/transport.py)
- Boundary decisions: [ADR 0033](../adr/0033-private-minimax-h3-gateway.md) and [ADR 0036](../adr/0036-minimax-h3-profile-catalog.md)
  and [ADR 0034](../adr/0034-provider-neutral-video-adapters-and-local-h3.md);
  [ADR 0035](../adr/0035-backend-owned-video-modules.md) records the module
  and service-package ownership boundary.

## 3. Before deployment

### Spark prerequisites

1. Docker and Docker Compose are available on Spark.
2. ComfyUI is running and is reachable only at `http://127.0.0.1:8188` from
   the host.
3. The MiniMax-H3 custom node and the exact profile assets are installed in
   ComfyUI. The gateway's readiness check requires the following values to
   appear in ComfyUI's `/object_info` response:

   ```text
   MiniMaxH3ImageToVideo
   minimax_h3_fl2va_pruned_fp8_scaled.safetensors
   qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
   minimax_h3_video_vae_fp16.safetensors
   minimax_h3_audio_vae_fp32.safetensors
   minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors
   ```

4. Keep the large model artefacts under `/home/wjmao/models`. Configure
   ComfyUI's model paths or symlinks to use that location. The gateway does
   not search that directory itself—it only verifies what ComfyUI advertises—so
   a file being present there is not sufficient proof that the profile is
   ready.
5. Choose two persistent, private host directories:
   - gateway state and uploaded assets;
   - the directory mounted as ComfyUI's input directory.

   Do not place either inside the Plotloom checkout, a temporary directory, or
   a shared public folder. The gateway records asset hashes and job recovery
   state in its SQLite database. ComfyUI retains the actual output it serves,
   so its output directory also needs a deliberate retention/backup policy.

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
H3_MAX_QUEUE_DEPTH=2

# Private, persistent host paths.
H3_GATEWAY_DATA_HOST_DIR=/home/wjmao/services/plotloom-h3-gateway/data
H3_COMFY_INPUT_HOST_DIR=/path/to/the/comfyui/input/directory
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
  "profileContractVersion": 2,
  "profiles": [{"id": "minimax_h3_fp8_turbo4_portrait_576x1024_v1", "width": 576, "height": 1024, "selectable": true}],
  "maxQueueDepth": 2
}
```

`/health` intentionally performs a ComfyUI/profile preflight. A running
container is therefore not enough: do not enable Plotloom until `/health`
returns `ok` with the full reviewed catalog and contract version.

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
VIDEO_MODEL=minimax_h3_gateway_catalog_v2
VIDEO_AUTH_MODE=bearer
VIDEO_MODEL_API_KEY=the-same-value-as-H3_API_KEY
```

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
2. The workbench requires one explicit aspect policy and prepares an immutable
   production snapshot. It freezes the keyframe, character references,
   approval, adapter/version, profile, prompt, and seed.
3. Plotloom preflights the gateway, uploads the frozen keyframe, and makes one
   durable submission. It never retries a submission whose outcome might be
   unknown.
4. Plotloom polls only the known gateway job ID. It retrieves the MP4 only
   through that gateway ID—never from a provider-controlled output URL.
5. It probes the downloaded bytes. The candidate is eligible only if it is
   H.264/AAC, the exact frozen width/height, 24 fps, 124 frames, and within
   one frame of the frozen duration. A merely playable mismatch becomes `retrieve_needed` with
   `h3_output_profile_mismatch` and cannot be selected.
6. The resulting candidate is unselected. A human reviews visual continuity,
   dialogue/audio quality, and creative suitability before an explicit
   selection. It never changes canonical story data.

### Input-aspect policy

The gateway always emits a 16:9 frame. It will not silently stretch an
approved still:

| Policy | Gateway behavior | Choose it when |
| --- | --- | --- |
| `cover_center_crop` | centre-crops to 16:9, then resizes | the important subject is centrally framed and filling the frame is preferable |
| `contain_pad` | preserves the full image and pads to 16:9 in black | the complete source composition matters more than a filled frame |
| `reject_mismatch` | rejects a non-16:9 input | the input must already be compositionally exact |

Review the prepared policy as a creative choice. It cannot be inferred from a
file extension or silently selected by the server.

## 7. Gateway HTTP contract for maintenance only

The following is a private service contract; it is not a browser API.

| Endpoint | Auth | Purpose |
| --- | --- | --- |
| `GET /health` | no bearer header | Checks ComfyUI and the reviewed catalog; returns status, contract version, safe profile descriptors, queue depth |
| `POST /v1/assets` | bearer | Uploads one PNG/JPEG/WebP, maximum 20 MiB and 30 megapixels |
| `POST /v1/video-jobs` | bearer | Creates one job from `assetId`, prompt, `profileId`, `aspectPolicy`, optional seed |
| `GET /v1/video-jobs/{id}` | bearer | Refreshes a known job |
| `GET /v1/video-jobs/{id}/output` | bearer | Streams the known completed MP4 |

Job response fields are deliberately closed: `id`, `status`, `profileId`,
`aspectPolicy`, `error`, and `outputReady`. Valid states are `reserved`,
`submitted`, `running`, `succeeded`, `failed`, `cancelled`, and
`outcome_unknown`.

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
| `queue_capacity_reached` | H3 or ComfyUI queue is at configured capacity | wait or raise capacity only after measuring memory/throughput; do not add client retries that create duplicate work |
| `input_aspect_mismatch` | `reject_mismatch` received a keyframe whose ratio differs from the selected profile | choose a different explicit policy or supply a matching keyframe |
| `outcome_unknown` | request/response path failed after the durable record was created | inspect the known gateway job and ComfyUI history; never automatically replay |
| `comfy_output_missing` / `comfy_output_unavailable` | ComfyUI did not save the one expected MP4 or output retention removed it | inspect the known job and output retention; preserve evidence, do not claim a candidate was ingested |
| `h3_output_profile_mismatch` in Plotloom | received MP4 did not match the frozen codec/frame profile | retain the evidence, inspect ComfyUI/profile drift, and correct the profile boundary rather than accepting the file |
| Plotloom says H3 is unavailable | H3 flag/key/provider/model is inconsistent, both backends are enabled, or Plotloom cannot preflight | correct the server configuration and restart; browser settings cannot fix it |

Gateway state is stored in `gateway.sqlite3` beneath
`H3_GATEWAY_DATA_HOST_DIR`, alongside uploaded assets. It includes job prompts
and therefore must be treated as private production data. Back it up under the
same access restrictions as project data. Keep the corresponding ComfyUI
output directory long enough for known jobs to be retrieved. Never use a broad
cleanup command against either directory.

## 9. Change management

Do **not** make any of the following as an SSH-only tweak:

- replace a model filename in the frozen profile;
- change dimensions, frame count, FPS, duration, step count, or audio path;
- expose ComfyUI or the gateway publicly;
- point Plotloom at another model or arbitrary URL;
- accept a mismatched output because it plays in a browser.

Each alters a production contract. The required path is: add a new gateway
profile/version in source, add or update a separate Plotloom adapter capability
version, freeze it in production snapshots, add request/response/output tests,
run a bounded probe, record the evidence, and then enable it deliberately.
Historical H3 jobs must retain their old adapter/profile interpretation.

Normal code updates are safer: pull a reviewed `main`, rebuild the gateway
image, verify `/health`, run the relevant Plotloom checks, and only then
restart the production services. Roll back by deploying the previous reviewed
source revision and retain the existing gateway state volume.

## 10. Evidence, current limits, and next review

What has been directly evidenced:

- the legacy 864×480 H3 profile can generate H.264/AAC at its advertised
  frame profile;
- one Mandarin line under one prompt and keyframe was watched by a reviewer as
  intelligible and lip-synced;
- a real temporary Plotloom → gateway → MP4 ingestion path completed once
  without resubmission and produced an unselected candidate.

See the secret-free records:

- [Mandarin dialogue probe](../verification/2026-09-13-h3-mandarin-dialogue-probe.md)
- [adapter and live-ingestion verification](../verification/2026-09-13-p2-h3-adapter-isolated.md)

These are not proof of universal dialogue quality, voice locking, same-person
continuity, cross-shot motion/lighting continuity, production readiness, or
any new catalog profile's performance. Each selectable geometry needs a
separate bounded Spark probe before it can be promoted beyond an available
candidate.
The next intended product checkpoint is a retained, human-reviewed pair of
adjoining shots from the same selected character reference. Only that review
can establish whether this H3 baseline is useful for sequential storytelling.

## 11. Fast handoff checklist

Before an operator declares the H3 path usable after a restart or handoff:

- [ ] ComfyUI is loopback-only and `/health` reports contract version 2 and the full reviewed catalog.
- [ ] H3 model artefacts remain under `/home/wjmao/models` and are visible to
      ComfyUI under the exact required names.
- [ ] Gateway is bound to Spark's Tailnet address, not `0.0.0.0`.
- [ ] Gateway and Plotloom have matching server-only bearer keys; no key has
      entered a URL, browser, repository, or project record.
- [ ] Exactly H3—not H3 and Wan—is enabled in Plotloom.
- [ ] Plotloom has been restarted after configuration changes and reports the
      H3 profile through its safe backend status projection.
- [ ] The gateway state/input directories and ComfyUI output retention are
      private, persistent, and backed up deliberately.
- [ ] A new candidate stays unselected until a human reviews the actual MP4.
