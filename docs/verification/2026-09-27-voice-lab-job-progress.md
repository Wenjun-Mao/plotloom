# Voice Lab queue and generation progress — 2026-09-27

## Result

On the retained specialist branch, added an observed progress projection for
candidate voice generation and changed field captions so their text can be
selected without losing accessible names. [ADR 0208](../adr/0208-voice-lab-observed-job-progress.md)
records the queue and phase contract. No Plotloom authoring code changed and
no Plotloom director contact, merge or push occurred.

The final wheel installed on Spark is
`/home/wjmao/services/plotloom-voice-lab/releases/progress-final-2026-09-27/plotloom_voice_lab-0.1.0-py3-none-any.whl`,
SHA-256 `4cc950f3cee928f398bbdd66f686fc833d949eaa6f9573ada5ad81265a56f735`.
The previous wheel remains available under `releases/projects-final-2026-09-27/`.

## Checks

- Voice Lab fake-engine tests: 13 passed. A blocked worker showed a running
  `synthesizing` phase and monotonic elapsed time; a second generation queued
  behind the active generation and a clone reported `queueAhead=2`. Terminal
  projection and unknown-ID behavior were also checked.
- Full repository Python suite: 783 passed; one upstream Starlette deprecation
  warning. JavaScript syntax, wheel build, isolated installed-wheel smoke and
  `git diff --check` passed.
- Real browser on Spark: drag-selecting `新增候选方向` produced exactly that
  selection while the textarea remained named `新增候选方向`. A temporary project
  generated a candidate while the card displayed observed `模型准备中` and later
  `语音合成中`; the completed 1.92-second WAV was playable and H3-eligible.
- The temporary project and its unpublished audio were deleted by exact-name
  confirmation. Live SQLite reported `integrity_check=ok`, zero active jobs
  and zero cleanup debts. Existing user and pilot projects were untouched.
- After final UI correction, the service restarted healthy. No second live
  generation was needed for that presentation-only change.

Independent second-agent review remains pending. This verification does not
claim that a model reports percent complete, ETA, or GPU-only inference time.
