# P1.5 correction receipt — candidate, not acceptance

Date: 2026-09-12

This receipt records the bounded corrections after the director withheld P1.5
acceptance. It does not alter the retained pilot records, claim a Flow result,
or accept the milestone. The retained pilot directory remains read-only:
`/Users/wjmao/projects/HU/plotloom-p15-pilot-FBSu6o`.

## Attribution and decision ownership

The historical pilot's “human visual comparison” wording is preserved as
historical text; it was not evidence of identified human participation. The
observed engineering/visual inspection was performed by Codex and is described
as a **Codex engineering/visual assessment**, not human review or a product
decision. Product decisions remain explicit creator/product actions in Plotloom:
reference selection/replacement and any recorded reviewer label are durable
creator-owned decisions. The UI explicitly warns that a Codex assessment must be
labelled Codex and cannot be presented as a human/product decision.

## Corrected product surface

- Story Bible now exposes the story-first proposal path without a Shot,
  downstream stage, or storyboard Approval. It supports an existing current
  candidate as `parentCandidateAssetId`, delivery refresh, explicit initial
  selection, and explicit replacement. The first selection correctly uses
  reference revision zero when no state row exists yet.
- Proposal cards expose eligible candidate-to-refinement selection and copy a
  selectable assignment when clipboard access is unavailable.
- Same-person review displays the selected candidate beside every exact frozen
  primary and complementary asset from its job's `characterIdentity` mapping.
  It labels character, role, frozen decision/revision and hash, and retains
  historical review status. It never substitutes a current reference decision
  for a frozen asset.
- The Story Bible comparison keeps current and replaced reference decisions
  visible with their actual managed assets and explicit current/history status.

## Specialist preflight boundary

New P1.5 packages opt into package version 4 and `p1.5-pin.v1`. Before ImageGen,
the repository skill calls `scripts/pin_image_specialist.py`, which accepts only
the supported v3/v4/codex-specialist-v2/skill-v2 combination, requires the
relevant execution code and skill to match `HEAD`, and refuses an existing pin.
Refresh requires the completion provenance to match that pre-generation pin.

This is a bounded operational attestation, not proof of when a local operator
generated pixels: both delivery files remain untrusted until validation, and
their matching fields cannot establish wall-clock ordering. Frozen historical
v3 packages do not opt in and continue to verify under their original contract.

## Browser evidence

`frontend/e2e/image-jobs.spec.ts` runs a real FastAPI process against a
test-owned file SQLite database, artifact root, and exchange root. The
story-first journey starts with only a saved Story Bible, uses retained raster
fixtures marked as simulations (no new ImageGen call), and exercises proposal,
parent refinement, explicit r1 selection, r2 replacement, and reference history.
The existing approved-shot manual handoff journey remains covered separately.

The retained 1440×900 stale-reference browser evidence is
[`p15-reference-replacement-stale.png`](supporting/p15-reference-replacement-stale.png).
Its read-only source capture is
`/Users/wjmao/projects/HU/plotloom-p15-pilot-FBSu6o/evidence/reference-replacement-stale-after-restart.png`;
the companion three-shot browser preview is
`/Users/wjmao/projects/HU/plotloom-p15-pilot-FBSu6o/evidence/three-shot-preview.png`.
These are retained pilot evidence, not new generated images or a replacement for
the correction browser test.

The corrected panel capture from the focused browser run is available in this
candidate's local Playwright output at
`frontend/test-results/image-jobs-P1-self-contain-fb917-ef-after-an-intent-revision/p15-frozen-reference-comparison-1440x900.png`.
It uses two distinct retained raster fixtures, labels the primary and
complementary frozen references, and is test output rather than a new generated
asset.

## Verification on the compatibility candidate

The stable verification chain ran after compatibility commit
`87d5637e5717a9135c17250dfaa3b74f4ad1be83` (which follows implementation
commit `0d550d2`). The final narrow follow-up below changed the exchange
awaiting-state contract, frozen-history display, and focused regressions after
that full chain; it intentionally ran only its affected checks rather than
blindly repeating every unrelated gate.

| Gate | Command | Result |
| --- | --- | --- |
| Full Python | `uv run --locked pytest -q` | passed. A subsequent read-only collection reports **558** tests; the full-run terminal summary was not persisted, so this receipt intentionally does not invent a pass/skip split. |
| Focused image contracts | `uv run --locked pytest -q tests/backend_core/test_image_jobs.py` | **17 passed**, 1 dependency deprecation warning. |
| Frontend static checks | `cd frontend && npm run typecheck && npm run test && npm run build` | typecheck passed; **124 passed** across 13 Vitest files; Vite build passed and regenerated tracked static assets. |
| Browser | `cd frontend && npm run test:e2e` | passed. Read-only Playwright listing reports **26** browser tests in 11 files; the focused image-job run was **2 passed**. |
| Package | `uv build --wheel && uv run --locked python scripts/smoke_installed_wheel.py dist` | wheel build and isolated installed-wheel smoke passed. |
| Specialist skill | `uv run python /Users/wjmao/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/plotloom-image-specialist` | passed. |
| Pin behavior | isolated synthetic package invoking `uv run python scripts/pin_image_specialist.py --package …` | initial pin passed; existing-pin and unsupported-skill preflight were rejected. |

`git diff --exit-code -- src/plotloom/static` passed after the build, and the
worktree was clean at the full-gate checkpoint. The current read-only
collection/listing values above were recorded while reconciling this receipt;
they are not a replacement test run.

## Final narrow follow-up after the full-gate checkpoint

The final correction makes a valid, standalone v4 `executor-pin.json` an
`awaiting_delivery` state rather than false rejected delivery history. Any
malformed/wrong pin or any other undeclared partial entry remains rejected. It
also keeps an invalidated selected candidate's original frozen primary and
complementary references visible in a history panel after a current-reference
replacement.

- `uv run --locked pytest -q tests/backend_core/test_image_jobs.py` — **18
  passed**, 1 dependency deprecation warning. This covers valid pin-only
  awaiting behavior and unchanged empty delivery history.
- `cd frontend && npm run typecheck && npm run test:e2e -- image-jobs.spec.ts`
  — typecheck passed; **2 passed**. The browser journey uses distinct retained
  primary/complementary references, asserts both frozen images before and after
  replacement, and captures the corrected comparison panel above.

The full Python/frontend-unit/build/full-browser/wheel gates in the preceding
table predate only this final narrow delta; they remain accurate results for
`87d5637`, not claims that those broad commands were rerun afterward.

## Status

This correction candidate passed its stable full verification gate and remains
subject to independent director review. It does not
claim P1.5 acceptance, human review, Flow completion, external ImageGen
execution, video readiness, or a new visual pilot.
