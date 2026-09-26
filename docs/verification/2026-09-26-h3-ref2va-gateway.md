# H3 Ref2VA per-job voice gateway · 2026-09-26

## Scope and source

- Gateway-only source commits: `80f3a85` and `652bf37` on
  `codex/h3-ref2va-gateway`.
- Added `POST /v1/video-jobs/from-image-with-voice`, one private per-job WAV
  binding, a frozen Ref2VA graph/snapshot, additive SQLite migration and
  strict admission/retention tests. Existing FL2VA and Qwen routes are
  unchanged. Plotloom Voice ID, UI and product transport are not implemented
  here; those belong to the director's later checkpoint.
- Deployment copied only the committed
  `services/minimax_h3_gateway/src/plotloom_h3_gateway/` package to Spark's
  existing gateway build context. A checksum dry-run after deployment found
  no source differences. ComfyUI, Qwen, models and old experiment outputs were
  not modified. A scoped pre-change SQLite backup and previous Python package
  were retained under
  `/home/wjmao/services/plotloom-h3-gateway/backups/2026-09-26-pre-ref2va-80f3a85/`.

## Objective checks

| Check | Result |
| --- | --- |
| `uv run --locked pytest -q` with tracked submodule initialized | 783 passed after the Spark-discovered permission repair; one Starlette dependency deprecation warning |
| Focused gateway + existing Plotloom H3 transport | 84 passed after the repair |
| Changed-code Ruff check | passed |
| Frontend Vitest / TypeScript / build | 221 passed / passed / passed; generated static diff clean |
| Wheel build and installed-wheel smoke | passed |
| `git diff --check` | passed |
| Spark ComfyUI queue / gateway jobs before deploy | 0 running, 0 pending / 0 queued, 0 active |
| Spark gateway health after rebuild | `voiceReferenceReady: true`, `voiceContractVersion: 1` |
| Spark SQLite after additive migration | `PRAGMA integrity_check = ok`; `job_voice_bindings` present |

The broad Playwright run was stopped after 20 passing tests and repeated
failures in pre-existing authoring UI journeys. The first inspected failures
waited for navigation and buttons absent from the current workbench (for
example the retired `工作台阶段` region); no gateway browser UI is changed in this
slice. This is a **verification gap**, not a pass or a waiver for Plotloom's
product acceptance. Gateway HTTP, worker, persistence and existing transport
paths are covered by the locked Python suite.

## Live Spark canaries and root-cause correction

- One admission only: `h3_de42f1cab796450890815a95eb61c9dc`, 202 response,
  `inputMode=image_voice`, quality 8, 576×1024, requested 5 s, 124 frames,
  seed `20260923`. The creation-only voice SHA-256 matched the reviewed WAV:
  `1982764d633299cb52d3dcf7c2cf1e068cfa511b68c7bbdf72665fdcaa55de4f`.
- The reused genuine portrait first frame SHA-256 is
  `4237ad89a723b7f059d3238eb3aca92acc6373d726b07b7161ef7e37af932d10`.
  Both inputs match the earlier direct-ComfyUI reviewed experiment under
  `/home/wjmao/services/spark-comfyui/data/output/experiments/h3-ref2va-portrait-2026-09-26/`.
- Comfy history definitively recorded `execution_error` at `LoadAudio`:
  permission denied opening the prepared WAV. The gateway had written that
  shared Comfy input as `root:root 0600`, while Comfy runs as `1000:1000`.
  Its status `error` also carried `completed=false`, which the previous
  gateway poller did not recognize as terminal. The initial job had no output.
- Commit `652bf37` fixes both originating contracts. The source WAV remains
  gateway-owned `0600`; the separate Comfy copy is owned by the shared input
  directory owner, also `0600`. The history poller treats Comfy `error` and
  `execution_error` as terminal without disclosing traceback text. Tests
  cover file ownership, failed ownership rollback, and terminal projection.
  The full locked Python suite then passed 783 tests. Only the gateway package
  was rebuilt on Spark; the first job now reads `failed` with stable code
  `comfy_execution_failed` and a completion timestamp. Its evidence remains.
- One replacement job, `h3_457c3519c8614004b1596459e04d6c58`, was
  admitted after both gateway and Comfy queues were empty, reusing the exact
  retained image, voice bytes, prompt, seed, aspect policy, resolution and
  requested duration. Its 202 voice hash matched the initial reviewed WAV.
  The new Comfy input was inspected as `1000:1000 0600`; the private source
  remained `root:root 0600`.
- The replacement reached `succeeded`, `outputReady=true`, with no error.
  Submission was `2026-09-26T16:36:04.078Z`, Comfy completion was observed at
  `2026-09-26T16:44:15.170Z`, and backend elapsed time was 491,092 ms. Its
  exact managed MP4 is
  `/home/wjmao/services/plotloom-h3-gateway/data/outputs/2026-09-26T16-44-15Z_h3_457c3519c8614004b1596459e04d6c58.mp4`.
  The SQLite and file SHA-256 both equal
  `ab49d526750f5a82ac5d32aae4e093375f504b324d7ba7876ce788ad54061dd5`;
  size is 983,818 bytes. `ffprobe` reports H.264, 576×1024, 124 frames,
  AAC stereo 32 kHz and 5.167 seconds. `ffmpeg` decoded both streams fully
  without error. The authenticated `/output` returned HTTP 200 `video/mp4`
  with that same byte count and hash.
- A byte-identical review copy was retained separately under
  `/home/wjmao/services/spark-comfyui/data/output/experiments/h3-ref2va-gateway-2026-09-26/`.
  The existing local Comfy tunnel at `127.0.0.1:8891` returned HTTP 200 for
  that file. This experimental review copy is not a gateway-managed output
  and does not inherit the gateway's 72-hour expiry. **Human audiovisual
  review of the replacement is pending; technical output checks do not
  assert voice consistency or lip-sync quality.**

No creative acceptance is inferred from a 202 response, health report, test
count or prior direct-Comfy trial. The gateway canary must reach a known
terminal status and its exact output must be reviewed before the B checkpoint
is called accepted. The director receives a separate API handoff after this
technical gate.
