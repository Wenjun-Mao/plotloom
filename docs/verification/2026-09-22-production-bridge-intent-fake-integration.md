# Production-bridge dramatic intent — fake integration check

This check covers the approved bounded follow-on in ADR 0079. It is an
implementation verification, not creative or product acceptance. No real text
provider, paid fallback, image, video, or H3 call was made.

## Contract and automated checks

- A pending proposal has source excerpts as evidence, but no completed
  objective/purpose wording and no installation authority.
- A versioned Chinese prompt requests only `suggestedText` for trusted exact
  IDs. The local binder rejects missing, extra, duplicate, and blank targets;
  a successful fake response creates a review revision only.
- A dispatched result is not auto-retried after process loss, and late results
  cannot replace an author edit, cancellation, or changed source. Bearer test
  credentials are absent from persisted attempt data.
- Completing dramatic intent does not remove the nine-shot Brief policy
  conflict or permit installation under the original 1–4-shot Brief.
- `uv run pytest -q`: 701 passed (one existing Starlette/httpx deprecation
  warning). `frontend/npm test`: 190 passed. `frontend/npm run typecheck` and
  `frontend/npm run build` passed. `git diff --check` passed. An independent
  GPT-5.6 Terra read-only review reported no actionable finding.

## Retained browser fixture

The isolated fixture lives at `.local/relay/bridge-intent-preview/`; it is not
the U4 lighthouse project. While the local preview process remains running,
open `http://127.0.0.1:8810/v2/?project=11a21b92-bd62-464e-a382-2003c5dee8b0&stage=source#storyboard-review`.
To restart against the retained root, run
`uv run python -m scripts.bridge_intent_preview --root .local/relay/bridge-intent-preview --port 8810`.
The script labels its deterministic fake adapter. A new process makes its
first attempt fail as known-not-sent; a deliberate retry returns the exact
target set. The author can review, edit, save, and explicitly accept it.

Browser checks at 1440 and 1920 pixels covered failed-call/retry, disabled
acceptance for unsaved edits, review revision after save, and explicit final
acceptance. Console errors/warnings: zero. Screenshots are retained under
`output/playwright/bridge-fake-*`; the fixture data and screenshots are local
verification artifacts, not canonical project edits. The selected local text
profile's metadata was inspected read-only; live dispatch readiness and
provider response quality remain unverified.

## Provenance follow-on and current preview (same date)

The prior UI could call a retained model suggestion a source excerpt after an
author save. The stored contract now separates accepted-source `sourceExcerpt`,
optional original model `suggestedText`, and final `text`; suggestion origin is
independent of review state. Regression checks cover inference → edit/save →
reload → acceptance and a second inference from the saved proposal. The second
prompt and frozen job use the original excerpt, not the first model's wording.
The original accepted fake fixture's five revisions are projected read-only
from revision 1 and the model job provenance; its accepted rows were not
rewritten. The currently visible first entry is source “Lin chooses.”, original
fake-model suggestion “角色在此推动冲突并改变局势：opening-s1-objective”, and final author
text “林必须在灯塔供电与码头救援之间作出不可逆的选择。”

The unaccepted fixture is isolated at
`.local/relay/bridge-intent-preview-unaccepted/` and currently served at
`http://127.0.0.1:8811/v2/?project=2697451c-f69b-4083-a61f-1856c5d6d818&stage=source#storyboard-review`.
The preserved accepted fixture is served with the current UI at
`http://127.0.0.1:8810/v2/?project=11a21b92-bd62-464e-a382-2003c5dee8b0&stage=source#storyboard-review`.
Both servers use `scripts/bridge_intent_preview.py` with their respective roots
and ports. The visible simulated-data/fake-model warning comes from the preview
server's bridge response, not a URL flag; reopening either URL without a flag
still shows it. The unaccepted fixture remains at proposal r1, with no model
job or installation. Browser checks at 1440 and 1920 showed the pending and
accepted states with zero console errors/warnings. Current screenshots:
`output/playwright/bridge-followon-final-pending-1440.png` and
`output/playwright/bridge-followon-final-accepted-1920.png`.

Read-only local profile metadata: selected `default` r11, enabled,
`openai_compatible` adapter v1, model `qwen3527b`, bearer authentication,
JSON-schema capability disabled, context window 32768, max output 16384,
attempt timeout 600 seconds; a text key is configured. This is structural
eligibility only. No live call, connectivity check, billing, or model-quality
acceptance was performed.

The independent GPT-6 Sol high-reasoning read-only review identified the
URL-dependent fake warning and, after the server-owned label fix and an
explicit runtime-construction seam, found no remaining actionable issue.
The final corrected revision passed `uv run pytest -q` (703 tests; the same
Starlette/httpx deprecation warning), `frontend/npm test` (192 tests),
`frontend/npm run typecheck`, `frontend/npm run build`, and `git diff --check`.
