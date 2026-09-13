# Plotloom MiniMax-H3 gateway

This is a private, typed API in front of Spark's loopback-only ComfyUI service.
It is deliberately **not** a ComfyUI proxy: callers cannot submit workflows,
select model files, or reach ComfyUI directly.

## Contract

1. `POST /v1/assets` uploads one PNG, JPEG, or WebP reference frame.
2. `POST /v1/video-jobs` creates an asynchronous video job from that asset.
   `aspectPolicy` is mandatory: `cover_center_crop`, `contain_pad`, or
   `reject_mismatch`. The gateway never silently stretches an input frame.
3. `GET /v1/video-jobs/{id}` reports status; `GET .../output` proxies the MP4
   only after the ComfyUI job has completed.

The sole initial profile is `minimax_h3_fp8_turbo4_480p`: the observed Spark
baseline (FP8 FL2VA, NVFP4 text encoder, 4-step Turbo, 864×480, 124 frames at
24 fps, approximately 5.167 seconds). It includes native audio generation but
does not synthesize dialogue unless the prompt asks for dialogue.

## Deployment on Spark

Copy `.env.example` to `.env`, replace the Tailscale address and secret, then:

```sh
docker compose up --build -d
```

The container uses host networking so it can reach ComfyUI at
`127.0.0.1:8188`. Bind `H3_BIND_ADDRESS` to the Spark's Tailscale IP; do not
replace it with `0.0.0.0`. Keep ComfyUI on loopback. No public TLS or reverse
proxy is required for the intended private-Tailnet deployment, but bearer auth
remains mandatory.

## Intentional limits

- One frozen, evidenced profile; no arbitrary widths, step counts, durations,
  graph JSON, model paths, or custom nodes.
- The gateway records a submission with an ambiguous network outcome as
  `outcome_unknown` and never automatically resubmits it.
- Plotloom has not yet been wired to this contract. That future adapter must
  preserve the existing immutable production snapshot and known-job recovery
  semantics rather than adapting the Atlas-specific flow in place.
