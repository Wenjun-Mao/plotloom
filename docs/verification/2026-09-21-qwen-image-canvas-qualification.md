# Qwen-Image-2.1 canvas qualification receipt — 2026-09-21

## Scope and decision boundary

This is an evidence-only qualification of the six Plotloom candidate image
canvases. It does **not** change the public gateway contract: the gateway
continues to admit only `1024x1024` for Qwen image jobs until the results have
also received an explicit visual/product review.

For each canvas, one 40-step, CFG-1 opaque text generation and one
single-image edit were run with fixed seeds. The edit used the preceding text
output as its source, so it tests the same canvas in both provider routes.

## Runtime and serialization

- Model: `Qwen/Qwen-Image-2.1`, served by the pinned private SGLang service on
  Spark.
- Canvases: `832x480`, `960x544`, `1280x704`, `576x1024`, `608x1088`, and
  `704x1280`.
- The public gateway queue and ComfyUI queue were empty before the run.
- The gateway container was stopped only for this direct-provider experiment,
  preventing a concurrent H3 or public Qwen dispatch; its shell-level
  fail-safe restarted it on exit. Its post-run health response reported zero
  queued and zero active dispatches.
- Provider image bodies were copied into the dedicated operator evidence root,
  then the provider's incidental source-checkout outputs were removed. They
  are not gateway-managed production assets.

The retained remote evidence is:

`/home/wjmao/services/qwen-image-sglang/experiments/qwen-image-canvas-qualification-2026-09-21/`

It contains the twelve PNGs and a secret-free `receipt.json`. A local review
copy is at:

`/Users/wjmao/Downloads/qwen-image-canvas-qualification-2026-09-21/`

## Technical results

Every request succeeded, returned a PNG at the exact requested dimensions, and
had no transparency requirement. `inference` is the provider-reported model
time; it does not include any gateway preparation or output-transfer work.

| Canvas | Text inference / peak memory | Edit inference / peak memory | Exact-size result |
| --- | ---: | ---: | --- |
| `832x480` | 15.079 s / 32,616 MB | 16.395 s / 32,598 MB | pass |
| `960x544` | 18.477 s / 33,034 MB | 20.393 s / 33,018 MB | pass |
| `1280x704` | 33.058 s / 34,334 MB | 37.897 s / 34,318 MB | pass |
| `576x1024` | 21.674 s / 33,254 MB | 23.791 s / 33,238 MB | pass |
| `608x1088` | 24.602 s / 33,514 MB | 27.640 s / 33,478 MB | pass |
| `704x1280` | 32.901 s / 34,334 MB | 38.100 s / 34,320 MB | pass |

The representative wide and portrait pairs were inspected for gross scaling or
padding artifacts; each uses its requested native composition rather than a
square image embedded in a larger blank canvas. This is not a claim of
creative-quality acceptance for every output. The full twelve-image set is
retained for the product visual review.

## Outcome

The model/service can technically generate and edit all six target sizes with
bounded memory (32.6–34.3 GB in this sample). After the retained set received
product approval, ADR 0073 promoted the six canvases alongside `1024x1024` as
the public exact-size allow-list. The promotion adds gateway regression
coverage and frozen execution snapshots; this receipt remains the evidence
for that decision rather than silently widening the API from an out-of-band
experiment.
