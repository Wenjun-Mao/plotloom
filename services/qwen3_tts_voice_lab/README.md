# Spark Voice Lab

Private synthetic voice casting at <http://100.64.35.71:8897/>. Opening `/`
shows a project chooser and never generates or opens old recordings.
Projects are independent workspaces, not authenticated user accounts.

- [Author workflow and pipeline](docs/audio-pipeline-report.md)
- [Reproduction, licenses and operations](docs/reproduction-and-operations.md)
- [Cross-service ownership and selective releases](../../docs/operations/media-services.md)
- [Engine decision](../../docs/adr/0094-voice-lab-independent-engines-and-delivery.md)
- [Published takes and shared admission](../../docs/roadmap/2026-09-30-voice-takes-h3-plan.md)
- [Take API client guide](docs/voice-takes-client-guide.md)
- [Verified shared-admission deployment](../../docs/verification/2026-10-01-published-voice-takes-shared-admission.md)

## Two stages, four independent engines

The 2026-09-30 deployment preserves existing voices and passes offline gates.
The initial live matrix retained a Qwen-reference → Index CUDA failure.
A separately authorized [controlled retest passed](../../docs/verification/2026-09-30-voice-lab-cuda-neutral-retest.md),
without rewriting the failed trial. The later
[reliability closeout](../../docs/verification/2026-09-30-voice-specialist-reliability-closeout.md)
passes a fresh complete nine-call workflow, exact cold/post-H3 probes with
Qwen-Image running, published-byte H3 consumption and idle Lab restart.
General concurrent co-resident reliability and new creative approval are not
established. See the original
[deployment receipt](../../docs/verification/2026-09-30-voice-lab-multi-engine-deployment.md)
and its supplement for the distinct boundaries.

| Stage | Engine ID | Model | Native WAV |
|---|---|---|---|
| Create identity | `qwen_design` | Qwen3-TTS 1.7B VoiceDesign | 24 kHz |
| Create identity | `moss_design` | MOSS VoiceGenerator | 24 kHz |
| Reuse identity | `qwen_base` | Qwen3-TTS 1.7B Base, neutral default | 24 kHz |
| Reuse identity | `index_base` | IndexTTS2, optional delivery control | 22.05 kHz |

Default creation compares Qwen and MOSS. Count is **per selected engine**:
two explicit directions with two engines create four independent slots.
Paired slots share direction, line and numeric seed, not equivalent random
streams. Regenerate or change engine on one slot without affecting siblings.
Save shared text and slot edits explicitly. Unsaved inputs prompt before
project navigation.

Choose either reuse engine independently of the creator. Index accepts no
control, Chinese performance description, or eight manual strengths (0–1).
Words and acting direction are separate. Actual interpreted/effective
strengths are saved before synthesis, including on subsequent failure.
Qwen rejects unsupported emotion-control fields.

Native source bytes, subtype, rate, peak and hash are retained. A separate
deterministic 32-kHz mono PCM16 H3 derivative records resampling and any gain
needed to avoid clipping. Over-range float source gets a warning, never silent
source attenuation. H3 eligibility remains 1–10 seconds and at most 2 MiB.

Explicit Publish produces an immutable `voiceId` with independent source and
H3 WAV copies. Repeating Publish for one generation returns the same ID.
Published audio survives regeneration, project deletion and restart. Failed
regeneration preserves old audio; successful replacement removes only the old
unpublished recording. Edited design makes the old recording noncurrent.

## Runtime and verification

The API loads **no inference model**. The gateway-owned durable FIFO grants one short-lived
supervised engine process in its pinned environment and reaps its process group
before the next job. Qwen, MOSS and Index use separate qualified environments.
All weights remain under `/home/wjmao/models`. Changed frozen settings/files
fail visibly; no fallback. The UI shows queue counts, observed phases and
elapsed time, without invented percent or ETA. Restart interrupts unfinished
jobs, never silently replays them.

All Lab creation, clone trials and durable takes register in the same lane as
H3/Qwen-Image, under [ADR 0097](../../docs/adr/0097-published-voice-performance-takes-and-shared-admission.md).
Missing control configuration leaves jobs visibly waiting, never running locally.
Unknown dispatch/unreaped children hold the lane without retry. Memory/ComfyUI
checks remain supplementary; direct backend clients are outside this guarantee.
The Lab never automatically stops another service.

The standalone CPU-only [memory observer](tools/memory_trace.py) retains
one-second timestamped memory/pressure/process samples for an explicitly
authorized operator window. It generates nothing and does not allocate a CUDA
context. See the [measurement limits and original failure analysis](../../docs/verification/2026-09-30-reference-strategies-and-memory.md)
before interpreting MemAvailable, RSS or Torch allocation as GPU headroom.

Run these commands inside `services/qwen3_tts_voice_lab/`, not the repository root:

```sh
uv sync --locked --group test
uv run --locked pytest -q
uv build --wheel
```

The [systemd user unit](deploy/plotloom-voice-lab.service) uses the lightweight
`/home/wjmao/services/plotloom-voice-lab/.venv`, private
`VOICE_LAB_RUNTIME_CONFIG`, and the existing data root. Run exactly one worker,
never multi-worker Uvicorn. With user linger the unit survives reboot.
This unauthenticated UI is Tailnet-only; private execution routes require a
separate bearer key. Do not expose it publicly.

## API and storage

Public responses expose no filesystem paths or credentials. Revision conflicts
return stable `detail.code`; malformed input uses FastAPI 422.

| Operation | Route |
|---|---|
| Engines | `GET /api/engines` |
| List/create project | `GET/POST /api/projects` |
| Read/edit/delete project | `GET/PUT/DELETE /api/projects/{projectId}` |
| Paired creation | `POST /api/projects/{projectId}/paired-generations` |
| Add slot | `POST /api/projects/{projectId}/candidates` |
| Edit/delete slot | `PUT/DELETE /api/candidates/{candidateId}` |
| Generate one slot | `POST /api/candidates/{candidateId}/generations` |
| Result/progress/audio | `GET /api/generations/{generationId}`, `/progress`, `/audio?kind=source\|h3` |
| Select reference | `POST /api/projects/{projectId}/selections` |
| New-line trial | `POST /api/clone-trials`, `GET /api/clone-trials/{trialId}` |
| Publish/resolve | `POST/GET /api/voices`, `GET /api/voices/{voiceId}`, `/audio?kind=source\|h3` |
| Durable dialogue take | `POST/GET /api/voice-takes`, `GET/DELETE /api/voice-takes/{takeId}`, `/audio?kind=source\|h3` |

SQLite: `$VOICE_LAB_DATA_ROOT/voice_lab.sqlite3`. Unpublished media:
`assets/<candidateId>/<generationId>/`; pinned trials: `clones/<trialId>/`;
published copies: `voices/<voiceId>/`; independent takes: `takes/<takeId>/`. Private runner request/events/log:
`runs/<jobId>/` (no automatic audit-log retention policy yet).
Schema v4 additively preserves old IDs, columns and WAV hashes; historical
provenance stays schema 0, not reinterpreted as today's settings.
Never reset live data to fix an operational issue.

Plotloom Voice ID consumption remains **unimplemented and withheld**. This
slice changes only the specialist Lab; no director message, merge or push.
