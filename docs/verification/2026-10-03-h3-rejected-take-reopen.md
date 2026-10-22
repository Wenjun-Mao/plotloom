# H3 rejected-take reconsideration verification

The current implementation permanently locked a retained rejected H3 take:
there was no explicit event to restore segment reconsideration, and replacing
the job would sever its review history. ADR 0108 adds a separate append-only
reopen command that reuses the shared video-currentness check and advances the
shot selection revision transactionally without selecting or generating.

Verification on 2026-10-03:

- `uv run pytest tests/test_video_review_reopen.py -q` — 12 passed. The stale
  currentness case creates and selects a second approved keyframe binding via
  the normal APIs, confirms the frozen job projects `current: false`, then
  confirms reopen refuses without appending a review event.
- `uv run pytest tests/test_project_storage_video.py -q -k 'whole_job_review_annotations or synthetic_reviewed_segment_survives_reopen'`
  — 4 passed, 28 deselected.
- `npm test -- tests/video-pilot.test.ts` — 29 passed.
- `npm run typecheck` and `npm run typecheck:e2e` — passed.
- `uv run ruff check src/plotloom/api/project_folder_media.py src/plotloom/api/project_folder_video.py src/plotloom/project_storage/project_video.py src/plotloom/persistence/project/media_video.py src/plotloom/persistence/project/media_video_segments.py src/plotloom/video_contracts.py tests/test_video_review_reopen.py`
  — passed; `uv run ruff check src/plotloom/api --select F401` — passed.
- `npm run build:deterministic` — passed and refreshed
  `src/plotloom/static/workbench.js` (SHA-256
  `7e2f7d17666ba456b79160fc53753f8d53ca851e28479e13f2ea60cca6dfa068`). Vite
  emitted its existing advisory for the 701.78 kB workbench chunk.
- `git diff --check` — passed.

No live project, browser, provider, runtime, commit, or push action was
performed. Full-suite and browser E2E verification remain with the parent
workflow.
