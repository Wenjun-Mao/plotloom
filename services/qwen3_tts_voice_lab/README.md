# Spark Voice Lab

Private, specialist-side synthetic voice casting. A new visitor sees a project
chooser rather than the retained pilot. Projects are independent content
workspaces, not authenticated user accounts. This service does not change the
Plotloom authoring UI or H3 gateway.

## Authoring contract

- Create a named empty project. Its name, shared brief and audition line can be
  edited with an expected-revision save. Candidate slots have stable unique
  IDs and separate editable directions. Add or regenerate a single candidate
  without rerunning the others.
- Each generation has a new immutable ID and freezes its line, direction,
  model revision and seed. The 24-kHz source WAV and, when eligible, a 32-kHz
  mono PCM16 H3 reference are hash-checked on retrieval. Only 1–10-second,
  at-most-2-MiB prepared audio is H3 eligible.
- Failed regeneration keeps the old usable WAV. Successful replacement switches
  the current pointer before deleting the old unpublished WAV; a lab selection
  of that old generation is cleared. Cleanup failure remains as a scoped SQLite
  debt for retry. A queued clone copies and pins its reference on admission.
- Explicit Publish turns the selected H3-eligible generation into an immutable
  `voiceId` with independent source and H3 WAV copies. Repeating Publish for the
  same generation returns the same ID. Published audio survives regeneration,
  project deletion and restart; there is no retirement endpoint yet.
- One worker handles all design and clone jobs serially. On restart, queued or
  running jobs become `interrupted` and are never silently replayed.
- While a candidate is queued, its card shows how many design or clone jobs
  are ahead. During generation, it shows the observed worker phase and elapsed
  time. The model does not provide a reliable percent complete or ETA; the UI
  does not invent either.

See [ADR 0092](../../docs/adr/0092-voice-lab-projects-and-published-voice-identity.md).

## Run and deployment

Keep checkpoints under `/home/wjmao/models/qwen3-tts/`, never in this Git repo.
The VoiceDesign `model.safetensors` SHA-256 is
`391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522`;
the Base checkpoint SHA-256 is
`38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c`
(Hugging Face revision `fd4b254389122332181a7c3db7f27e918eec64e3`).
The engine verifies weight hashes before inference.

From this module directory, `uv sync --locked --extra inference --group test`
creates an isolated development environment; `uv run --locked pytest -q`
runs fake-model tests. The Spark pilot uses the isolated
`/home/wjmao/services/qwen3-tts-trial/.venv` with `qwen-tts==0.1.1`, Torch
BF16/CUDA, Torch SDPA and this module's installed wheel. Only the Voice Lab
unit should be restarted for updates.

```text
VOICE_LAB_HOST=100.64.35.71
VOICE_LAB_PORT=8897
VOICE_LAB_DATA_ROOT=/home/wjmao/services/plotloom-voice-lab/data
VOICE_LAB_DESIGN_MODEL_DIR=/home/wjmao/models/qwen3-tts/voice-design-1.7b
VOICE_LAB_BASE_MODEL_DIR=/home/wjmao/models/qwen3-tts/base-1.7b
```

`python -m plotloom_voice_lab` runs exactly one worker. Never use multi-worker
Uvicorn for this SQLite/in-process queue. The enabled
[`systemd --user` unit](deploy/plotloom-voice-lab.service) restarts after
reboot and binds only the Tailscale IP. Open
`http://100.64.35.71:8897/` from the Tailnet. Do not publicly expose this
unauthenticated generation service.

## API

All writes return stable error codes in `detail.code`; public responses contain
no server paths or credentials. IDs are opaque. Selected endpoints:

| Operation | Route |
|---|---|
| List/create project | `GET/POST /api/projects` |
| Read/edit/delete project | `GET/PUT/DELETE /api/projects/{projectId}` |
| Add candidate | `POST /api/projects/{projectId}/candidates` |
| Edit/delete candidate | `PUT/DELETE /api/candidates/{candidateId}` |
| Generate only that candidate | `POST /api/candidates/{candidateId}/generations` |
| Generation result/progress/audio | `GET /api/generations/{generationId}`, `/progress`, and `/audio?kind=source\|h3` |
| Select lab reference | `POST /api/projects/{projectId}/selections` |
| New-line trial | `POST /api/clone-trials`, then `GET /api/clone-trials/{trialId}` |
| Publish/resolve immutable voice | `POST/GET /api/voices`, `GET /api/voices/{voiceId}`, `/audio?kind=source\|h3` |

Project, candidate and generation mutations require `expectedRevision`,
`expectedProjectRevision`, and/or `expectedCandidateRevision` as shown by the
request model. Deletion additionally requires the exact current project name.
The old global `/api/rounds` and `/api/selections` authoring routes are gone.
The progress response is secret-free and returns `status`, `queueAhead`,
`phase`, `elapsedSeconds` and `errorCode`. `queueAhead` is null if the request
has not yet reached the in-process queue or is terminal. See
[ADR 0093](../../docs/adr/0093-voice-lab-observed-job-progress.md).

SQLite is at `$VOICE_LAB_DATA_ROOT/voice_lab.sqlite3`. Unpublished WAVs are
under `assets/<candidateId>/<generationId>/`, pinned clone references/results
under `clones/<trialId>/`, and independent published WAVs under
`voices/<voiceId>/`. The first v2 start transactionally migrates the old pilot
rounds/selections/clones to one named pilot project, validating stored hashes.
Back up the exact data root, including SQLite WAL/SHM if live, before installing
a new wheel. Do not delete pilot files to resolve an operational problem.
