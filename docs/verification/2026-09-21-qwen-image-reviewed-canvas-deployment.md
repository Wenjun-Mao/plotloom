# Qwen reviewed-canvas contract deployment receipt — 2026-09-21

## Scope

This receipt records deployment of the seven-canvas Qwen-Image public contract
defined by ADR 0073. It is not a new model qualification: the six non-square
canvases were qualified earlier in the linked canvas receipt.

## Released behavior

The Spark gateway now advertises exactly these Qwen image canvases through its
authenticated health projection:

`1024x1024`, `832x480`, `960x544`, `1280x704`, `576x1024`, `608x1088`, and
`704x1280`.

Admission rejects every other dimension. A Qwen job's versioned snapshot holds
its canvas and exact dimensions; dispatch and PNG validation both use that
snapshot rather than a current default. Version-1 square snapshots remain
readable.

## Deployment and real public canary

- The gateway was rebuilt from the committed `services/minimax_h3_gateway/`
  source on Spark. Its private `.env` was excluded from synchronization.
- Qwen SGLang remained active and loopback-only; ComfyUI remained healthy.
- The shared queue was empty before and after the canary.
- A real authenticated `POST /v1/image-jobs/from-text` requested `576x1024`
  with fixed seed `210921`.

The returned status was:

| Field | Value |
| --- | --- |
| Job | `img_90f2413e41dd46e5bb8d3f3fe29258a2` |
| Status | `succeeded` |
| Resolution | `576x1024` |
| Output | PNG, `576×1024` |
| Generation elapsed | 21,291 ms |
| Output retained | yes |

No prompt body, image body, endpoint secret, or other credential is retained
in this receipt.

## Verification

- Focused gateway tests: 36 passed (one existing Starlette deprecation
  warning).
- Full locked Python suite: 664 passed (the same warning only).
- Wheel build and isolated installed-wheel smoke test: passed.
- Spark public health and public image-job status checks: passed.

The underlying six-canvas evidence, including timings, memory, exact output
dimensions, and review copies, is in the [canvas qualification receipt](2026-09-21-qwen-image-canvas-qualification.md).
