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
