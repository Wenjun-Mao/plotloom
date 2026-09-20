# H3 quality and resolution contract deployment

Date: 2026-09-20  
Status: deployed and runtime-verified

## Scope

Commit `2a5b54a` replaces the gateway's public recipe-profile selector with an
explicit `quality` plus exact `resolution` contract. It admits qualities
`1`, `2`, `3`, and `8`, and the six reviewed landscape/portrait dimensions.
The same contract applies to direct image-to-video and the exploration-only
text-to-video route. Plotloom remains image-to-video only and submits quality
`1` explicitly.

The complete durable decision is [ADR 0070](../adr/0070-h3-quality-resolution-contract.md).

## Clean-state cutover

Before deployment, Spark reported an empty ComfyUI queue, zero active gateway
dispatches, and zero queued gateway jobs. The previous gateway SQLite/media
state (43 completed historical jobs) was recoverably moved to:

```text
/home/wjmao/services/plotloom-h3-gateway/archive/gateway-data-pre-quality-contract-20260920T170418Z
```

No ComfyUI experiment output or model asset was moved. The new gateway
container was then rebuilt from the committed source and started against a
fresh gateway data directory. Its unauthenticated health projection reported:

- generation contract version `6`;
- default quality `1`;
- qualities `[1, 2, 3, 8]`;
- resolutions `832x480`, `960x544`, `1280x704`, `576x1024`, `608x1088`, and
  `704x1280`;
- image and text input modes; and
- zero queued or active work.

## Local verification

All checks were run from the committed source before deployment:

| Check | Result |
| --- | --- |
| Locked Python suite | 653 passed |
| Frontend unit suite | 165 passed |
| Frontend typecheck/build/static freshness | passed |
| Browser E2E suite | 79 passed, 1 skipped |
| Installed-wheel smoke test | passed |

The full browser suite initially exposed a timing race in an unrelated exact
work-unit repair journey: its default ten-second wait could expire while the
independent repair projection was legitimately hydrating under parallel load.
The test now waits up to thirty seconds for that server-derived state; its
three-repeat parallel run and the full suite both passed. This changes test
stability, not generation behavior.

## Spark canaries

One exact-ratio 576x1024 portrait image was admitted as a single FIFO sequence
in the order `1 -> 2 -> 3 -> 8`. All jobs requested five seconds, froze 124
frames at 24 fps, and completed without a retry or error. `ffprobe` confirmed
a 576x1024 H.264 video stream plus a native AAC audio stream in every managed
output.

| Quality | Frozen path | Backend elapsed | Delivered duration |
| ---: | --- | ---: | ---: |
| 1 | V1.2 Turbo-4 / Euler / 6-3 | 104.614 s | 5.167 s |
| 2 | V1.0 Turbo-4 / res_multistep / 6-3 | 103.044 s | 5.167 s |
| 3 | V1.0 Turbo-8 / Euler / 6-3 | 161.208 s | 5.167 s |
| 8 | Base-20 / res_multistep / native 12-3 | 322.642 s | 5.167 s |

The stored quality-8 snapshot recorded the base topology, no LoRA and no
sigma-shift override. Qualities 1--3 each recorded their corresponding Turbo
LoRA and explicit 6/3 shifts. This validates that queued dispatch reads its
immutable snapshot rather than the mutable live catalog.

After the FIFO lane cleared, an independent quality-1 text-to-video canary at
576x1024 also succeeded: 124 frames, 24 fps, 5.167 seconds, H.264 video and
an AAC audio stream, with 98.034 seconds of measured backend elapsed time.
Text-to-video remains an operator/colleague exploration route, not a Plotloom
authoring mode.

This receipt deliberately records no bearer value, endpoint address, prompt,
or output URL. Gateway-managed canary media follows the normal 72-hour output
retention policy.
