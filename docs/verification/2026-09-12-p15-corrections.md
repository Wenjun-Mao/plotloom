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

## Status

This correction candidate resolves the director's implementation gaps subject to
the stable full verification gate and independent director review. It does not
claim P1.5 acceptance, human review, Flow completion, external ImageGen
execution, video readiness, or a new visual pilot.
