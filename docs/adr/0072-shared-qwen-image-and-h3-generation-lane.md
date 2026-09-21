# ADR 0072: Shared Qwen-Image and H3 generation lane

**Status:** Accepted

## Context

Spark hosts both MiniMax-H3 video generation through ComfyUI and
Qwen-Image-2.1 through SGLang. Running their GPU inference concurrently risks
unpredictable memory pressure and makes a successful request an unreliable
capacity signal. A second image-only queue would also let work overtake or
overlap the established H3 FIFO.

Qwen's documented Spark recipe supports native 1024×1024 text generation,
single-reference editing, and PNG alpha output. Plotloom needs a bounded,
inspectable service contract before non-square image canvases become public.

## Decision

The existing gateway SQLite database and one dispatch worker are the sole
generation admission lane. H3 video and Qwen image jobs share FIFO order and
only one backend invocation may be active. Fetching source URLs, decoding,
normalization, and copying a completed result do not hold that GPU lease.

Qwen-Image runs as a loopback-only `systemd --user` service. The gateway is
the only Tailnet-facing image API and stores all delivered PNGs under its
managed data root. Image jobs initially admit only exact `1024x1024` output,
one output, 40 steps, CFG 1, and optional server-resolved seed. The two image
routes are text generation and single-reference editing; multi-image editing
is intentionally absent.

`backgroundMode=transparent` asks Qwen for alpha and requires a valid PNG
with non-opaque alpha. It never removes a background in gateway postprocess.
Outputs expire after 72 hours; jobs and transient inputs expire after 30 days.

## Consequences

- H3 remains the private Plotloom video backend; no new Plotloom image UI is
  implied by the colleague-facing gateway routes.
- A Qwen or H3 failure cannot trigger an automatic replay after an uncertain
  backend submission.
- The six existing Plotloom video canvases require recorded Qwen generation
  and single-edit qualification before they are added to the image allow-list.
- ComfyUI and SGLang must remain private; direct callers would bypass the
  serialization contract.
