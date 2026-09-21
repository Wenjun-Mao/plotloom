# ADR 0073: Qwen-Image reviewed canvas contract

**Status:** Accepted

## Context

The shared H3/Qwen generation gateway originally exposed only `1024x1024` for
Qwen-Image-2.1. The service itself could accept other dimensions, but exposing
provider capability without evidence would make output framing, memory demand,
and edit behavior an accidental contract.

On 2026-09-21, the private Spark service generated and single-image-edited one
PNG at each of six candidate Plotloom canvases. Every result had exact output
dimensions and used 32.6–34.3 GB peak memory. The retained evidence and visual
review copy are recorded in the Qwen canvas qualification receipt.

## Decision

The public Qwen image routes accept exactly these seven output canvases:

- `1024x1024`
- `832x480`, `960x544`, `1280x704`
- `576x1024`, `608x1088`, `704x1280`

They reject any other dimension, including values the underlying provider may
support. Each admitted job freezes its canvas, width, height, and
`imageContractVersion` in its execution snapshot. Dispatch and managed-output
validation read that snapshot—not a mutable current default—so a queued job
cannot be rendered or published at a different size after the catalog changes.

Version-1 square snapshots remain readable for existing retained jobs;
version-2 snapshots encode the reviewed multi-canvas contract.

## Consequences

- Callers select an exact intended delivery canvas; no implicit crop, padding,
  or arbitrary resize policy is introduced for Qwen image generation.
- The gateway's H3 and Qwen metadata retain separate allow-lists because the
  square Qwen canvas is not an H3 video canvas.
- Any future canvas needs equivalent text and one-reference-edit evidence,
  product review, contract tests, and a successor decision record.
