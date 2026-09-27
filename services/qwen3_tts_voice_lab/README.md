# Spark Voice Lab

Private, specialist-side synthetic voice casting. This service does **not**
create Plotloom character Voice IDs or change H3 gateway jobs. It is the
working successor to the [static UI study](../../docs/voice-lab-prototype/README.md).

## Contract

- One Mandarin audition line and 2/4/6/8 separately editable voice directions
  form an immutable casting round. Each candidate has a server-generated seed,
  stable ID, frozen model/hash provenance and original 24-kHz WAV.
- A separate 32-kHz mono PCM16 derivative is available only when the source
  meets the H3 gateway's 1–10-second / 2-MiB reference bounds. Files are never
  overwritten. A missing or failed derivative does not invalidate the original
  audition or prevent lab selection; it is visibly ineligible for H3. No
  automatic candidate retention cleanup is active.
- Selecting a candidate records a lab-only decision. It enables a Base-model
  new-line trial with the original WAV and frozen audition transcript. The
  trial does not guarantee emotion or exact H3 dialogue.
- One worker processes VoiceDesign rounds and Base-clone trials serially.
  Restart marks queued/running work `interrupted`, not replayed. The service
  never stops or reserves H3/Qwen Image processes. Avoid concurrent heavy
  Spark generation; a resource failure is visible and requires a new round.

See [ADR 0091](../../docs/adr/0091-spark-voice-lab-candidate-boundary.md).

## Reproduce and run

Model checkpoints stay under `/home/wjmao/models/qwen3-tts/`. The reviewed
VoiceDesign `model.safetensors` SHA-256 is
`391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522`;
the Base checkpoint SHA-256 is
`38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c`
(Hugging Face revision `fd4b254389122332181a7c3db7f27e918eec64e3`).
The adapter verifies the weight hashes before inference. Do not place model
files in this Git repository.

From this module directory, `uv sync --locked --extra inference --group test`
creates an isolated development environment; `uv run --locked --group test
pytest -q` runs fake-model tests. The Spark pilot uses the already isolated
`/home/wjmao/services/qwen3-tts-trial/.venv` with `qwen-tts==0.1.1`,
Torch BF16/CUDA and Torch SDPA, plus this module's installed wheel. That
environment is not used by the other services. For a clean replacement,
install the locked inference extra in a new venv and update only the Voice Lab
unit's `ExecStart` after verifying matching CUDA wheels.

Required runtime variables for the retained Spark install:

```text
VOICE_LAB_HOST=100.64.35.71
VOICE_LAB_PORT=8897
VOICE_LAB_DATA_ROOT=/home/wjmao/services/plotloom-voice-lab/data
VOICE_LAB_DESIGN_MODEL_DIR=/home/wjmao/models/qwen3-tts/voice-design-1.7b
VOICE_LAB_BASE_MODEL_DIR=/home/wjmao/models/qwen3-tts/base-1.7b
```

`python -m plotloom_voice_lab` runs exactly one worker. Never use multi-worker
Uvicorn for this SQLite/in-process queue contract. The
[`systemd --user` unit](deploy/plotloom-voice-lab.service) is enabled with
linger on Spark; it restarts after reboot and binds only the Tailscale IP.
Open `http://100.64.35.71:8897/` from the Tailnet, or use an SSH tunnel to
`127.0.0.1:8897`. Do not forward this unauthenticated generation UI to the
public Internet.

## API and evidence

- `POST /api/rounds` with `{"auditionText":"…","directions":["…","…"]}`
  returns a round ID. `GET /api/rounds` lists recent rounds and
  `GET /api/rounds/{id}` provides per-candidate progress.
- `GET /api/candidates/{id}/audio?kind=source|h3` serves hash-checked WAVs.
- `POST /api/selections` with `{"candidateId":"vc_…"}` records the current
  lab reference. `GET /api/selections` returns current and history.
- `POST /api/clone-trials` with `{"candidateId":"vc_…","text":"…"}` creates
  a Base-clone trial for the selected candidate. `GET /api/clone-trials/{id}`
  and `/api/clone-trials/{id}/audio` expose status and hash-checked output.
- `GET /health` reports process and checkpoint availability; it does not test
  current GPU headroom or promise that another Spark service is idle.

SQLite is at `$VOICE_LAB_DATA_ROOT/voice_lab.sqlite3`; generated source and
H3-ready WAVs are under `$VOICE_LAB_DATA_ROOT/assets/<candidateId>/`, and
reuse WAVs under `clones/<trialId>/`. Do not delete these user-valued files to
solve an operational problem. If a process stops mid-write, inspect the
interrupted record and any unreferenced `.pending-*.wav` before starting a
new round. The API never exposes raw server paths.
