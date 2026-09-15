# MiniMax-H3 gateway: colleague API guide

This is a private internal API for generating short MiniMax-H3 clips from one
reference image. It is not a public service or a ComfyUI proxy.

## Connect

You must be connected to the shared Tailscale network.

```sh
export H3_GATEWAY_BASE_URL='http://100.64.35.71:8090'
# Obtain this bearer value from the team out of band. Do not put it in a URL,
# source file, or shared shell history.
export H3_GATEWAY_API_KEY='ask-the-team-for-the-current-key'
export H3_AUTH="Authorization: Bearer ${H3_GATEWAY_API_KEY}"
```

First confirm that the gateway and its reviewed H3 catalog are ready:

```sh
curl --fail --silent --show-error "${H3_GATEWAY_BASE_URL}/health"
```

The response is safe to share: it contains readiness, the selectable profile
IDs, and queue counts, but never a prompt, local path, or secret.

## Safe URL-ingestion test — no video generation

This public Plotloom image is a stable, non-secret test source. It proves your
Tailnet connection, bearer key, URL retrieval, and image validation without
putting H3 work into the queue.

```sh
export H3_TEST_IMAGE_URL='https://raw.githubusercontent.com/Wenjun-Mao/plotloom/main/docs/storyboard-handbook/assets/storyboards/moon-control-room-finished-frame.png'

curl --fail --silent --show-error \
  -H "${H3_AUTH}" \
  -H 'Content-Type: application/json' \
  -d "{\"sourceUrl\":\"${H3_TEST_IMAGE_URL}\"}" \
  "${H3_GATEWAY_BASE_URL}/v1/assets"
```

It returns an `assetId`, detected `mimeType`, dimensions, and SHA-256. Keep
that `assetId` if you want to submit several H3 jobs from the same still.

## Generate one clip in one request

The convenience route fetches the image, stores it, and queues the job. The
following is a real working request once you set the bearer key above. It
**does put one clip into the serial H3 queue**. The sample source is close to
16:9 but not H3's exact 864×480 ratio, so it explicitly uses `contain_pad`.

```sh
curl --fail --silent --show-error \
  -H "${H3_AUTH}" \
  -H 'Content-Type: application/json' \
  -d @- \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs/from-image" <<JSON
{
  "sourceUrl": "${H3_TEST_IMAGE_URL}",
  "prompt": "A quiet cinematic hold. The astronaut turns toward the window, natural breathing, subtle cabin light movement, stable camera.",
  "profileId": "minimax_h3_fp8_turbo4_480p",
  "aspectPolicy": "contain_pad",
  "seed": 42
}
JSON
```

The `202` result is always the ordinary job envelope:

```json
{
  "id": "h3_…",
  "status": "queued",
  "profileId": "minimax_h3_fp8_turbo4_480p",
  "aspectPolicy": "contain_pad",
  "error": null,
  "outputReady": false
}
```

Save the returned `id` locally. The one-step endpoint has no idempotency
mapping: if your HTTP client times out after sending it, do **not** retry
automatically because the job may already be queued. Use the two-step flow
below when retry-safe deduplication or reuse matters.

## Reusable two-step flow

Upload a local file instead of a URL:

```sh
ASSET_ID=$(curl --fail --silent --show-error \
  -H "${H3_AUTH}" \
  -F 'image=@/absolute/path/to/keyframe.png;type=image/png' \
  "${H3_GATEWAY_BASE_URL}/v1/assets" | python3 -c 'import json, sys; print(json.load(sys.stdin)["assetId"])')

curl --fail --silent --show-error \
  -H "${H3_AUTH}" \
  -H 'Content-Type: application/json' \
  -d "{\"assetId\":\"${ASSET_ID}\",\"prompt\":\"A calm, stable close shot.\",\"profileId\":\"minimax_h3_fp8_turbo4_480p\",\"aspectPolicy\":\"contain_pad\",\"idempotencyKey\":\"replace-with-your-stable-unique-request-key\"}" \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs"
```

Use this flow when you want several prompt/seed variations from one keyframe,
or your software might need to retry the second request. Repeating the same
`idempotencyKey` with exactly the same job returns the original job; changing
the request with that key returns `idempotency_conflict`.

## Poll, download, or cancel

```sh
export H3_JOB_ID='paste-the-returned-h3-id'

# Repeat while status is queued/submitted/running/transfer_pending.
curl --fail --silent --show-error -H "${H3_AUTH}" \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs/${H3_JOB_ID}"

# When status is succeeded and outputReady is true:
curl --fail --silent --show-error -H "${H3_AUTH}" \
  -o "${H3_JOB_ID}.mp4" \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs/${H3_JOB_ID}/output"

# Only queued jobs can be cancelled safely:
curl --fail --silent --show-error -X POST -H "${H3_AUTH}" \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs/${H3_JOB_ID}/cancel"
```

Jobs are FIFO and H3 dispatches one video at a time; there is deliberately no
queue-length cap. Completed MP4s remain downloadable for 72 hours. Completed
job records, prompts, and gateway-managed keyframes are removed within 30
days. Keep any clip you want to retain in your own durable storage.

## Images, profiles, and errors

- Raw multipart files and `sourceUrl` downloads are accepted when their
  decoded bytes are JPEG, PNG, or WebP, no larger than 20 MiB or 30 megapixels.
  Host `Content-Type` is not authoritative.
- `sourceUrl` can be an `http` or `https` internal/Tailnet or public URL. It
  is fetched with a 5-second connect timeout, 20-second read timeout, and at
  most three redirects. The URL itself is not stored.
- Use `reject_mismatch` for a compositionally exact keyframe, `contain_pad`
  only when black padding is intentionally allowed, and `cover_center_crop`
  only for the existing reviewed crop workflow.
- Call `/health` for the complete current catalog. The common profiles are
  832×480, 960×544, 1280×704, 576×1024, 608×1088, and 704×1280.
- Typical errors are `source_url_invalid`, `source_url_fetch_failed`,
  `source_url_too_large`, `image_decode_invalid`, `input_aspect_mismatch`,
  `profile_not_supported`, and `one_step_idempotency_not_supported`.

This private-MVP URL feature intentionally does not apply public-service
SSRF/host filtering. Do not expose this gateway outside the trusted team
network without an explicit security redesign.
