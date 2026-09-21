# Qwen-Image-2.1 Spark deployment receipt — 2026-09-21

## Scope

This receipt covers the private Qwen-Image-2.1 service and its extension of
the existing MiniMax-H3 gateway. It does not promote Qwen image generation
into Plotloom's authoring UI, and it does not qualify non-square image
canvases.

## Frozen runtime

- SGLang source: `1da8ac10e17baa394c44dafa173382f9ab03d8e9`.
- Qwen model snapshot: `d51d8a5eb184466b47ef1dea8a91c60c7313e30b` under
  `/home/wjmao/models/qwen-image-2.1/model` on Spark.
- Service: `qwen-image-sglang.service`, enabled as a lingering user service,
  bound only to `127.0.0.1:30010`.
- Gateway: authenticated Tailnet control plane on port 8090, with one durable
  SQLite FIFO for both `h3_video` and `qwen_image` work.
- ComfyUI was recreated with `127.0.0.1:8188` rather than its prior all-host
  binding. A timestamped `docker inspect` snapshot is retained on Spark under
  `/home/wjmao/services/spark-comfyui/operations/`.

The released SGLang package did not contain the pinned checkout's native
Qwen-Image-2.1 module. The service therefore places the exact checkout's
`python/` directory first on `PYTHONPATH`; this avoids an editable install that
would otherwise require a Rust toolchain for optional extensions. The service
loaded the Qwen-Image-2.1 pipeline, all components remained resident, and its
private health endpoint responded.

## Real gateway evidence

All Qwen jobs used the fixed 1024×1024, 40-step, CFG-1 contract and generated
one managed PNG. IDs are retained only as operational evidence; prompts and
image bodies are intentionally omitted.

| Case | Job | Result | Gateway elapsed |
| --- | --- | --- | ---: |
| opaque text | `img_9f565ba954d248e386b1756e83031d0b` | 1024×1024 PNG | 36,746 ms |
| opaque one-image edit | `img_655464edc79d48a685031caa00019727` | 1024×1024 PNG | 43,182 ms |
| transparent text | `img_25bde06b3fad4c49a3608cfbeb2aec06` | 1024×1024 RGBA PNG | 37,045 ms |
| transparent one-image edit | `img_b09f48ff5f4e4e9681136439734b0483` | 1024×1024 RGBA PNG | 43,131 ms |

The transparent text result had alpha range `0..255` and 67.87% of pixels at
alpha 5 or below; the transparent edit result had range `0..255` and 68.05%
at alpha 5 or below. These meet the meaningful-alpha threshold used by
SGLang's Qwen-Image-2.1 integration test. This caught and corrected the
earlier insufficient `alpha < 255` test, which would have accepted
near-opaque PNGs.

While Qwen remained resident, H3 quality 8 produced
`h3_8e0005ed3a614443bd1cc3f0d48bc78c` before the queued Qwen jobs could begin:

- 704×1280, 124 frames, 5.167 seconds;
- H.264 video plus AAC audio;
- gateway generation elapsed 561,596 ms;
- no service restart, memory failure, or queue overlap.

Qwen's own server recorded 34,834 MB peak memory for the first 1024×1024
generation. The H3 result demonstrates the shared-lane coexistence policy,
not simultaneous GPU inference.

## Local verification

- Focused gateway coverage: `uv run --locked pytest -q
  tests/services/minimax_h3_gateway/test_qwen_image.py` — 8 passed.
- Full locked Python suite: 661 passed (one existing Starlette deprecation
  warning).
- Frontend unit tests: 177 passed.
- Typecheck, production frontend build, and static freshness check: passed.
- `uv build --wheel` and `uv run --locked python
  scripts/smoke_installed_wheel.py dist`: passed.

The serial Playwright command was also exercised. It exposed 12 failures in
pre-existing workbench journeys whose locators resolve a hidden, duplicate
status badge (for example `Plotloom 服务：已连接`); 24 unrelated journeys passed
before the run was interrupted and 44 had not yet run. No frontend source or
browser assertion belongs to this gateway change, so this receipt records the
failure rather than masking it with a gateway-specific workaround.

## Remaining qualification boundary

The public image routes continue to reject every size except `1024x1024`.
Before adding `832x480`, `960x544`, `1280x704`, `576x1024`, `608x1088`, or
`704x1280`, record both a text-generation and single-image-edit result for
each size, including dimensions, visual review, stability, and memory data.
