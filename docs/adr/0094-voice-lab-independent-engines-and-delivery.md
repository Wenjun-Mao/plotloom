# ADR 0094: Independent voice engines and observable delivery controls

**Status:** Accepted for specialist implementation, 2026-09-29. Plotloom
integration, director contact, merge and push remain on hold.

## Context

The existing Lab hard-codes Qwen model identities and 24-kHz audio. Qualified
MOSS creation and Index reuse have different dependency environments and Index
produces 22.05-kHz audio. Text classification also overshot or suppressed the
owner's requested restrained frustration; successful synthesis is not acting
acceptance. Keeping four models resident is unnecessary on shared Spark memory.

## Decision

- Creation (`qwen_design`, `moss_design`) and reuse (`qwen_base`, `index_base`)
  are independent, stage-checked choices. Paired creation counts are per engine
  and expose their total. Slots have independent IDs and a shared design binding.
- Freeze engine/model/adapter settings per job; append observed classification
  before synthesis without modifying that snapshot. Index has none/text/manual
  modes with separate spoken text and Chinese delivery direction. Expose the
  eight interpreted strengths and permit explicit manual adjustment; do not
  silently map frustration to a fixed vector. Keep alpha at 1.0.
- One Lab worker starts one short-lived model subprocess in its own pinned
  environment. Reap its process group before the next job. The API loads no
  inference models. Resource admission is advisory across other services, not
  a global GPU lock; never automatically stop them or replay interrupted work.
- Known Torch allocation/accelerator OOM is reported as `generation.oom`, not
  flattened into a generic synthesis failure. A successful process exit frees
  that process's resources; it does not prove readiness of the next CUDA context
  on a shared host. MemAvailable includes reclaimable cache and is not CUDA
  allocatable-memory evidence. No hidden retry is introduced to mask this gap.
- Preserve native source WAV bytes, declared sample rate and provenance.
  Finite over-range FLOAT audio remains reviewable with a warning. A separately
  versioned H3 derivative may attenuate resampling overshoot, recording gain;
  it never changes source bytes, timing or transcript. Full-scale PCM16 samples
  warn about possible existing clipping, which attenuation cannot repair.
- Preserve current IDs, hashes and published voices through a scoped v2→v3
  migration. Existing terminal evidence is not rewritten to imply a new run.

## Alternatives and consequences

A mixed Python environment risks the proven ARM64/native dependency boundary.
Warm servers add memory residency and scheduling state before a demonstrated
need. Cold job processes instead add loading latency and provide a clear release
boundary. Model-specific rates belong in adapters/media contracts, not a special
downstream bypass. Separate immutable publication continues to protect identity
from regeneration and project deletion under ADR 0092.

## Guardrails

Test frozen execution, isolated failure, shutdown/restart, source pinning,
publication, audio formats and actual classification evidence. Qualify the
working UI with the bounded nine-generation journey in the
[approved plan](../roadmap/2026-09-29-voice-lab-multi-engine-plan.md), not another
seed sweep. License notices and exact source/model versions remain deployment
requirements; no model-quality or legal-compliance guarantee is claimed.
