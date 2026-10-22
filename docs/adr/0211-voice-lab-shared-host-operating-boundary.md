# ADR 0211: Voice Lab shared-host operating boundary

Original specialist identifier: ADR 0096; renumbered during main integration on 2026-10-22.


**Status:** Accepted for the specialist deployment, 2026-09-30. No Plotloom
integration, director contact, merge or push is authorized by this decision.

## Context

The original Index CUDA-context allocation failed while other services were
resident. A controlled Qwen-Image pause allowed the exact reference/words/seed
to pass. The renewed closeout now also passes with Qwen-Image running, both
before and after a real H3 job. The latter starts with 30.553 GiB MemAvailable.
This does not identify or repair the original allocator failure: MemAvailable
and a successful context allocation are different evidence.

## Decision

- Keep the current on-demand voice subprocess contract. Do not keep four
  voice models resident, automatically stop another service, unload its cache,
  retry OOM, or substitute an engine. No runtime resource-policy code changes
  are justified by the two successful renewed probes.
- The supported shared-host qualification/maintenance workflow is an
  **operator-reserved serial window**. Before starting, require Voice Lab idle,
  gateway active/queued counts zero, ComfyUI queue empty and Qwen-Image ready.
  Do not accept another generation through another service during that window.
  Leave existing unrelated work alone. This is an operating restriction, not
  an API-enforced reservation or new distributed scheduler.
- Normal Lab admission retains the existing memory/ComfyUI advisory checks.
  They are not atomic against gateway admission and do not inspect an active
  SGLang inference request. Uncoordinated simultaneous callers remain outside
  the demonstrated reliability boundary. The gateway's own H3/Qwen FIFO does
  not include Voice Lab.
- A known generation failure remains terminal and visible; unknown dispatch
  never grants another POST. Diagnose the actual layer and explicitly authorize
  any changed experiment rather than rewriting the failed evidence.

## Alternatives and consequences

Raising a memory threshold would turn an unexplained allocation failure into
an arbitrary wait, not repair its cause. Automatically stopping Qwen-Image or
flushing ComfyUI caches would hide a cross-service policy choice. A simple lock
released by process exit is insufficient when a remote inference result is
unknown. Do not introduce any of those as an untested quick fix.

The current technical closeout is usable for serialized specialist work, not
an unattended multi-client resource guarantee. If simultaneous service use
becomes required, first design a shared admission owner with durable unknown-
dispatch handling and restart/concurrency tests. That is a named follow-up,
not implied implementation in this receipt.

## Evidence and guardrails

The [closeout receipt](../verification/2026-09-30-voice-specialist-reliability-closeout.md)
separates cold, warm and controlled-pause evidence. Preserve the original OOM,
published bytes and terminal attempts. Keep one supervised voice child and
reap it before another starts. Expose actual queue/phases; do not advertise
health/configuration as a successful inference guarantee.

## Detailed memory evidence

The 2026-09-30 bounded reference-strategy comparison adds an opt-in, CPU-only
operator trace, not a runtime admission guarantee or another API. Sample host
memory, pressure, swap and labelled process RSS with UTC/monotonic timestamps;
retain the actual sampling gaps and job phase/ID. GPU memory unavailable from
Spark NVML remains explicitly unmeasured. Never start a second CUDA context
just to instrument an active job, or add overlapping UMA/RSS/Torch values.
Trace failure must be visible and must not erase the underlying job failure.
See [historical evidence and measurement boundaries](../verification/2026-09-30-reference-strategies-and-memory.md).

The owner's subsequent review parks investigation of the isolated historical
CUDA incident unless it recurs. Preserve evidence and the observer; do not
claim the cause is fixed, remove serial safeguards, schedule additional probes,
or add automatic recovery merely because current runs passed.
