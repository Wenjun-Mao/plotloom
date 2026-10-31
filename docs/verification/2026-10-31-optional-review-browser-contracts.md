# Optional-review browser contract follow-up

The current Last Projection candidate keeps media observations optional while
requiring explicit source-bound selection and technical validity (ADR 0226).
Remaining workbench descriptions incorrectly required audiovisual inspection;
older browser fixtures also used retired mandatory-review labels and gates.
The descriptions now state optional observations. Browser fixtures exercise
current selection payloads, truthful absent/failed/uncertain observations and
preserved source, CAS, byte, rejection/reopening and no-dispatch safeguards.

Independent review inspected the actual diff against `cef4b65b`: product edits
are text literals only. APIs, request construction, persistence, admission,
provider/prompt behavior, dependencies, build tooling and package contracts
are unchanged. The 472-line keyframe panel has one wording edit; no new
responsibility or architectural extraction is warranted. Existing backend
evidence remains reusable. Generated workbench assets were refreshed.

Executed in the retained macOS arm64 / locked Python 3.12.13 / Node 24.18.0
envelope, with one qualification owner:

- `verify.py quick`: 184 frontend files, 1,703 cases and both type checks passed.
- `verify.py focused`: all 34 selected Playwright cases passed across
  `autopilot-review`, `aspect-ratio-currentness`, `branching-video-preview`,
  `imported-still-preview`, `image-jobs` and `video-batch`. Earlier focused
  evidence also passed the unchanged `autopilot-guidance` and cross-shot
  journeys. The segment-annotation label repair awaits downstream coverage.
- Two `npm --prefix frontend run build:deterministic` invocations produced
  identical SHA-256 trees across all nine workbench/player asset files.
- Desktop material-selection footer pixels were inspected: optional notes,
  retained observations and the explicit selection action are legible.

Evidence is retained under `.local/last-projection-resume/` in
`optional-wording-quick-final.log`, `optional-browser-repair-focused-2.log`,
`optional-wording-build-{1,2}.log` and
`optional-wording-asset-determinism.json`. The interrupted unfiltered attempt
(120 passed, eight failed, four interrupted, 234 not run) and first focused
repair attempt (23 passed, eight failed) remain failed/incomplete evidence;
their actionable failure context is preserved separately.

This is a verified bounded checkpoint, not a full-suite or release pass.
The complete unfiltered browser suite, wheel/installed-package gates, original
game production/playback/export, activation and recovery remain open under the
owning roadmap. The older `aa6e8754` full invocation remains failed; its 13
diagnosed Python failures were separately closed by focused repairs, with 112
downstream affected contracts passing on `cef4b65b`. Do not repeat unchanged
backend qualification solely for these frontend wording/fixture changes.
Hosted CI and push were not requested and were not run.
