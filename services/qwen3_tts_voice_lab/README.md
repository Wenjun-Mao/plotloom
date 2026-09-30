# Spark Voice Lab

Private synthetic voice casting at <http://100.64.35.71:8897/>. Opening `/`
shows a project chooser and never generates or opens old recordings.
Projects are independent workspaces, not authenticated user accounts.

- [Author workflow and pipeline](docs/audio-pipeline-report.md)
- [Reproduction, licenses and operations](docs/reproduction-and-operations.md)
- [Engine decision](../../docs/adr/0094-voice-lab-independent-engines-and-delivery.md)
- [Approved scope](../../docs/roadmap/2026-09-29-voice-lab-multi-engine-plan.md)

## Two stages, four independent engines

The 2026-09-30 deployment preserves existing voices and passes offline gates.
The initial live matrix retained a Qwen-reference → Index CUDA failure.
A separately authorized [controlled retest passed](../../docs/verification/2026-09-30-voice-lab-cuda-neutral-retest.md),
completing successful technical evidence for all four reuse paths without
rewriting the failed trial. Co-resident CUDA reliability and creative approval
are not established. See the original
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

The API loads **no inference model**. One FIFO worker starts one short-lived
supervised engine process in its pinned environment and reaps its process group
before the next job. Qwen, MOSS and Index use separate qualified environments.
All weights remain under `/home/wjmao/models`. Changed frozen settings/files
fail visibly; no fallback. The UI shows queue counts, observed phases and
elapsed time, without invented percent or ETA. Restart interrupts unfinished
jobs, never silently replays them.

Memory/ComfyUI checks are advisory, not a global GPU lock. The Lab never
automatically stops another service. See the reproduction guide for idle
cutover and the checked CPU control-plane lock.

```sh
uv sync --locked --group test
uv run --locked pytest -q
uv build --wheel
```

The [systemd user unit](deploy/plotloom-voice-lab.service) uses the lightweight
`/home/wjmao/services/plotloom-voice-lab/.venv`, private
`VOICE_LAB_RUNTIME_CONFIG`, and the existing data root. Run exactly one worker,
never multi-worker Uvicorn. With user linger the unit survives reboot.
This unauthenticated service is Tailnet-only; do not expose it publicly.

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

SQLite: `$VOICE_LAB_DATA_ROOT/voice_lab.sqlite3`. Unpublished media:
`assets/<candidateId>/<generationId>/`; pinned trials: `clones/<trialId>/`;
published copies: `voices/<voiceId>/`. Private runner request/events/log:
`runs/<jobId>/` (no automatic audit-log retention policy yet).
Schema v3 additively preserves old IDs, columns and WAV hashes; historical
provenance stays schema 0, not reinterpreted as today's settings.
Never reset live data to fix an operational issue.

Plotloom Voice ID consumption remains **unimplemented and withheld**. This
slice changes only the specialist Lab; no director message, merge or push.
