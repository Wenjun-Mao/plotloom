# Voice Lab multi-engine deployment and bounded qualification

**Status:** Implementation deployed; live qualification **incomplete**. No
Plotloom handoff, integration, merge or push. The owner-approved generation
cap is exhausted; this receipt does not authorize another call.

- Implementation: `1b7081e`, specialist branch `codex/h3-ref2va-gateway`.
- Starting implementation checkpoint: `01b285b`; planning baseline `077b1c4`.
- Authority: [approved plan](../roadmap/2026-09-29-voice-lab-multi-engine-plan.md).
- Decision: [ADR 0209](../adr/0209-voice-lab-independent-engines-and-delivery.md).
- Deployment: Voice Lab 0.2.0, Spark private UI/API on port 8897.
- Final wheel SHA-256:
  `67a330278e34b6dbdf62a1d6783caaf4341a3c71872670bf869346596b9623b2`.
  Mac-built and Spark-installed release hashes match. The final wheel adds
  typed OOM reporting and audio-warning presentation; no extra inference was
  spent to redeploy those changes.

## Delivered behavior

Creation uses independent Qwen VoiceDesign and MOSS slots, paired by default
with an explicit count per engine, common directions/text/seed, and independent
regeneration. Reuse independently selects neutral Qwen Base or IndexTTS2.
Index supports none, Chinese description, or manual eight-strength controls;
actual classifier scores are persisted before synthesis and can be copied to
manual controls. There is no hidden normalization, retry or model fallback.

The API loads no Torch/model cache. One FIFO worker supervises a short-lived
process in the selected pinned environment and reaps it before admitting the
next child. Immutable job snapshots bind model/settings and the private runtime
fingerprint. Resource waits are advisory, **not a global GPU scheduler or a
guarantee that CUDA can allocate despite host MemAvailable**.

Native WAV bytes/sample rate/subtype/hash remain authoritative. H3 preparation
is a separate versioned 32-kHz mono PCM16 derivative with recorded attenuation.
Finite FLOAT over-range and possible full-scale PCM16 clipping are warnings,
not source edits or a claim that existing distortion has been repaired.

## Offline gates and review

| Gate | Result |
|---|---|
| `cd services/qwen3_tts_voice_lab && uv run --locked pytest -q` | 40 passed; one existing Starlette/httpx deprecation warning |
| `node --check` on service `web/app.js`, `web/reuse.js` | Passed |
| Real FastAPI/file-SQLite browser fixture and `tests/browser_journey.js` | Passed: paired creation, independent Index reuse, actual-vector copy, native-audio warning, publication, blind listening, cancelled discard/no orphan project, project isolation and refresh |
| `uv build --wheel --out-dir dist` | Passed, final hash above |
| Isolated installed-wheel CPU import/package smoke | Passed; app imports without Torch; packaged `web/reuse.js` present |
| `uv run --locked pytest -q tests/test_extraction_contract.py` at repository root | 13 passed |
| `git diff --check` / staged patch check | Passed |

Tests cover all four creator/reuse combinations with deterministic adapters,
additive migration, source-byte preservation, publication after project
deletion, stale design guards, partial-pair failure, observed vectors on failed
synthesis, frozen adapter arguments, process crash/timeout/group shutdown,
resource waits, and typed OOM classification. Offline fixtures are not live
model reliability or creative acceptance.

One attended read-only reviewer (`gpt-6-luna`, high; requested Terra unavailable
in the built-in subagent catalog) identified auxiliary draft leakage and unused
frozen decoding fields. Both were fixed and checked by bounded follow-up. The
MOSS processor correction was also reviewed. No detached task, provider call,
source writer, or Relay lifecycle was delegated. No broad Plotloom frontend
suite was rerun: its runtime/source/packaging were untouched.

Retained, visually inspected 1440×900 viewport evidence:

- [Paired candidate UI](supporting/voice-lab-multi-engine-browser-1440x900.png).
- [Index controls and actual scores](supporting/voice-lab-multi-engine-reuse-1440x900.png).
- [Real Spark trials after restart, including failed lineage](supporting/voice-lab-multi-engine-spark-restart-1440x900.png).

Browser fixture audio is explicitly synthetic test output. The Spark screenshot
shows real retained results. Full-page stitching produced repeated viewport
bands in this browser surface, so it was replaced with viewport captures rather
than presented as valid evidence.

## Preservation and deployment

The exact idle backup is retained on Spark at
`/home/wjmao/services/plotloom-voice-lab/backups/2026-09-30-multi-engine/`.
It contains SQLite, media, prior service unit, preservation inventory and
migration proof. No development reset or model removal was performed.

`tools/verify_cutover.py` passed after final restart: SQLite integrity `ok`,
schema version 3, all old columns/rows preserved, **13 original WAV hashes
unchanged**, and the old published Voice ID resolves the same source/H3 bytes.
Baseline table counts were projects 2, slots 3, generations 3, selections 1,
reuse trials 3, published voices 1. Original preferred MOSS D trial evidence
and its model files were not replaced by the new technical project.

The new technical publication
`voice_f2da8670374546579b3048fd9d1222d4` also survives restart unchanged:

- Source: `10f307bab2f1451e10fae880c72f72e39102104e88ff6812734f2cd6ccae536f`.
- H3 derivative: `d83363680b5e4e13b8cbf7d21b8ce5516caaf247493db811dca70fcb303b5742`.

This publication proves the API/persistence workflow, not owner creative
approval of the newly generated voice. It does not supersede preferred MOSS D.

The CPU control-plane environment uses the exported locked service dependencies.
The same wheel was installed without dependency upgrades into the retained
Qwen, MOSS and Index environments. Source/model/native dependency hashes and
effective package inventories were captured; model files remain under
`/home/wjmao/models`. [Reproduction/operations](../../services/qwen3_tts_voice_lab/docs/reproduction-and-operations.md)
records qualified runtime boundaries, native Index normalizer and exact license
notices. Captured inventories are not a verified generic pip-only rebuild.

The user service is enabled with lingering and process-group shutdown. Final
health reports four configured engines and idle worker; that is configuration
availability, not four inference passes. Qwen Image was temporarily stopped for
the controlled window and restored: `/health` is `ok` and `/v1/models` reports
`Qwen/Qwen-Image-2.1`. The H3 gateway reports ready/zero active or queued jobs;
ComfyUI is empty. Lab/gateway bind the private Tailscale address, not loopback.
No H3/video generation, global GPU reset, container removal or model deletion
occurred. Owned local browser-fixture services are stopped at closeout.

## Exact live call accounting

Technical project: `vp_4a431100e77b407a9cf655392d337f6b`.
**Three creation + six reuse attempts: seven succeeded, two failed.**

| Attempt | Frozen engine/path | Result |
|---|---|---|
| `vg_a8d0b077df4d4691af5e58361f261f66` | Qwen Design | Completed, native 24-kHz FLOAT |
| `vg_41e76d9e3c2e498abdc6eafe5683003f` | MOSS Design | Failed before inference: custom processor rejected forwarded `local_files_only` |
| `vg_cf06991faf60477483934b48f2760091` | Explicit MOSS regeneration, third creation allowance | Completed, native 24-kHz FLOAT; Qwen sibling hash unchanged |
| `vt_ca3959665c774373ab3868c78042806e` | MOSS → Qwen Base neutral | Completed, 24 kHz |
| `vt_572b3a4855254235a7b6dbb680fbb11f` | MOSS → Index neutral | Completed, 22.05 kHz |
| `vt_008a602d37fd40b69d9702434fc45856` | Qwen → Qwen Base neutral | Completed, 24 kHz |
| `vt_d2688889bdb845149eae046172a7785a` | Qwen → Index neutral | Failed at CUDA context/model loading; no speech output |
| `vt_ed6bc579e00e485387b28efcf00d434b` | MOSS → Index Chinese description | Completed, actual calm strength 1; **not evidence of achieved urgency** |
| `vt_b74b5c19843c458caa3bfbf816174f1a` | MOSS → Index manual anger 0.25 | Completed; no new human acting approval |

The MOSS failure was a qualified custom-processor API mismatch. Removing the
unsupported processor kwarg, retaining model-loader local-only plus supervisor
offline mode, and testing frozen arguments corrected that layer. The explicit
third creation call spent the remaining allowance; it was not a hidden replay.

The Index failure is a Torch AcceleratorError reporting CUDA OOM at
`cuDevicePrimaryCtxRetain` / `gpt.to(cuda)`, before reference/utterance processing.
Host available memory and child exit do not explain CUDA headroom. Its exact
driver/shared-resource cause remains **unresolved**. Later Index calls succeeded,
but do not erase that failure. New typed `generation.oom` reporting makes this
class observable; historical `generation.failed` rows/logs were not rewritten
and this observability change is **not an OOM fix**.

## Memory evidence and limits

Across the private receipts: nine observed child PIDs, maximum sampled
concurrent generation children **1**, maximum sampled child RSS **7.729 GiB**,
maximum successful-process Torch allocation **10.764 GiB** (MOSS), and maximum
host total-minus-MemAvailable **86.441 GiB**. The latter includes other services
and unreclaimable/cache accounting; it is not exact GPU-only or physical-RAM
peak. Samples were one-second observations, not kernel-level peak telemetry.
The completion receipt ends with no child process and MemAvailable 68.791 GiB.
The lightweight API's observed idle RSS was approximately 122 MiB and its maps
contained no libtorch; no claim of an exact return of Linux cache usage is made.

Later read-only CUDA information reported approximately 20.97 GiB device-free;
ComfyUI and embedding inference remained resident. That observation is not
contemporaneous proof of the failed attempt's allocator/driver state. No
additional generation or forced cache unload was used to investigate it.

Private evidence is retained under
`/home/wjmao/services/plotloom-voice-lab/runtime-inventory/`:
`qualification-2026-09-30.json`,
`qualification-2026-09-30-completion.json`, and
`qualification-2026-09-30-delivery.json` (final status
`incomplete_known_failure`). Original failed request/event/runtime logs remain
under service `data/runs/`. Guarded continuation modes spent only the remaining
creation/control allowances, never the failed neutral attempt again.

## Remaining acceptance boundary

1. Diagnose the shared-host CUDA admission/context failure without preempting
   unrelated work. A controlled headroom check and **one explicitly authorized**
   Qwen → Index neutral retest is the next bounded verification, not a seed sweep.
   The current cap permits no extra synthesis.
2. New description wording (“坚定、果断、时间紧迫，迅速下达指令，不害怕、不惊慌。”)
   classified as raw/effective `[0,0,0,0,0,0,0,1]`, in 2.081 seconds. This is an
   open classifier/prompt-boundary observation, not a universal urgency recipe.
   Earlier owner-accepted phrasing remains separate bounded evidence.
3. No ASR, new perceptual acceptance, cross-shot H3 proof or Plotloom Voice ID
   consumer was produced here. Keep director contact and integration on hold
   until the owner releases that boundary.

No tasks were messaged, no Relay assignment started, and no merge/push was made.
