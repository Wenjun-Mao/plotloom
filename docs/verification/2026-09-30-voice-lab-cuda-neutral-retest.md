# Voice Lab: CUDA diagnosis and separately authorized neutral retest

**Result:** The missing Qwen-reference → Index neutral path passed in a
controlled idle window. Four creator/reuse paths now have successful live
evidence across the initial batch and this supplement. This does not turn
the initial nine-call batch into a pass, repair its allocation failure,
establish co-resident reliability, or grant creative acceptance.

The owner replied “go” to the focused diagnosis/retest on 2026-09-30:
**one additional synthesis**, not another audition batch. Runtime remains
`1b7081e`; the prior receipt is `514a40a`. No production source, model, package,
runtime catalog, gateway or API changed. Director contact, integration,
merge and push remain withheld.

## Diagnosis: established layer, unresolved allocator cause

Original trial `vt_d2688889bdb845149eae046172a7785a` stopped during
`IndexTTS2.__init__` / `gpt.to(cuda)`, before reference or dialogue processing.
The matching kernel journal at 00:47:58 America/Toronto reports
`NV_ERR_NO_MEMORY` in `_memdescAllocInternal` and main CUDA graphics-context
buffer allocation. This corroborates the failed primary-context allocation,
not a Qwen voice-format or Mandarin-text defect.

Original file hashes remain unchanged:

- `runtime.log`: `78ca1254f7634faa471b599e868ffe9c135ce2ef092f6d41d8f108d0577618c5`.
- `events.jsonl`: `79e0249d681c120a869535bc7b705429a56b6838e1bc63b8579290968cd0b1a4`.

ComfyUI, embedding inference and Qwen Image were resident before diagnosis.
One observation showed host MemAvailable about 33 GiB while CUDA reported
about 1.14 GiB free. NVIDIA documents
[Spark UMA reporting/reclaimable cache](https://nvidia.custhelp.com/app/answers/detail/a_id/5728/~/unexpected-available-memory-reporting-on-dgx-spark)
and [cache-related allocation issues](https://nvidia.custhelp.com/app/answers/detail/a_id/5776/related/1).
Neither number alone certifies the next driver allocation. These sources do
not prove fragmentation or the exact allocator/cache/driver cause here.
No cache flush, reboot, GPU reset or unrelated-container stop was used.

Subsequent [historical memory review](2026-09-30-reference-strategies-and-memory.md)
recovered the failed trial's sampled minimum: **62.373 GiB MemAvailable**,
with about 69.7 GiB in coarse system samples around the original failure.
The roughly 33 GiB observation above was later diagnosis, not that original
window. Thus available evidence does not support simple whole-host RAM
exhaustion; the precise CUDA allocation cause remains unresolved.

## One controlled dispatch

Lab/gateway queues and ComfyUI were idle. Only the already-authorized idle
Qwen Image service was temporarily paused, then restored.

| Snapshot | Host MemAvailable | CUDA-reported free |
|---|---:|---:|
| Before image-service pause | 34.275 GiB | approximately 4.66 GiB |
| After pause, before dispatch | 69.596 GiB | approximately 39.87 GiB |
| After completed generation | 68.690 GiB | Not sampled |

These are instantaneous observations on shared memory, not separate pools to
add together or guarantees against concurrent allocation.

New trial: `vt_5c9f73af6e404f858a3c9e3cc67c8d9b`.

- Reference: `vg_a8d0b077df4d4691af5e58361f261f66`, SHA-256
  `736efb0a20c15a7356a02bd53ab8375dad44dd4e83c05ce85a9f5b37378572b6`.
- Same dialogue, seed `20260929`, neutral delivery, Index checkpoint/source
  revision and decoding settings. The new runtime fingerprint reflects the
  already-deployed service update, not a model switch or rewritten old snapshot.
- Native mono PCM16 WAV: 22,050 Hz, 3.413333 seconds, peak 0.603760; no technical
  audio warnings. Output SHA-256:
  `f1c005026193dc318335347efb0fed61a9430c19e0ef3320ad8645f61a61f007`.
- Process elapsed 49.696 seconds; peak Torch allocation 7.426 GiB; sampled
  child RSS peak 7.702 GiB; maximum sampled generation children 1.

The observed phases covered resource wait, model loading and synthesis.
Retrieval/hash, native WAV metadata, frozen semantic settings and reference
hash were checked. No reference regeneration, fallback, precision change,
added emotion, seed sweep, H3 generation or hidden retry occurred.
No new listening/ASR/lip-sync or human identity/acting acceptance is claimed.

## Preflight correction, not a second generation

A first diagnostic preflight paused Qwen Image, then incorrectly queried
aggregate gateway readiness as an idle-queue check. Readiness correctly returned
503 while Qwen was down. The preflight stopped before synthesis POST, restored
Qwen, and retained all six existing reuse rows. Its generic private failure
label is preserved, not counted as a model failure or unknown dispatch.

The corrected temporary diagnostic reads dispatch counts via read-only SQLite
during planned image-service pausing, while retaining Lab/ComfyUI idle checks.
Full aggregate readiness is required before and after the window. No production
health contract was weakened or endpoint added. Exactly one synthesis POST
was made under renewed authority.

## Preservation, restoration and retained evidence

The old failed trial's public record and evidence files are unchanged. All
published Voice ID source/H3 hashes are unchanged. The isolated project's
previous MOSS reference selection was restored. Qwen Image `/health` is `ok`
and `/v1/models` identifies `Qwen/Qwen-Image-2.1`; the gateway is fully ready,
with zero queued/active dispatches. The generation child exited; Lab is idle.

Spark service `runtime-inventory/` retains the private receipts and their frozen
temporary diagnostic scripts:
`cuda-neutral-retest-2026-09-30.json` (zero-dispatch preflight incident) and
`cuda-neutral-retest-2026-09-30-generation.json` (completed one-call receipt).
Job evidence remains under `data/runs/vt_5c9f73af6e404f858a3c9e3cc67c8d9b/`.
Existing receipt paths refuse replay and keeping a script does not authorize
another generation. `minAvailableGiB` includes its initial pre-pause value,
not a measured synthesis-only minimum; no exact GPU-memory peak is claimed.

This is verification/documentation only. Closeout reran the 13 affected root
regressions with `uv run --locked pytest -q tests/test_extraction_contract.py`:
13 passed. Changed Markdown relative links and staged patch checks passed.
Prior 40 service tests, browser and wheel smoke remain implementation evidence;
those gates were not repeated or presented as new runs for this docs-only change.

**Next boundary:** Normal Lab jobs never stop another service. Coordinating
resident H3/Qwen Image/voice capacity remains an open operational decision.
Do not silently introduce global scheduling, cache eviction, service cycling
or OOM retries on the strength of one controlled pass.
