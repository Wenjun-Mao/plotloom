# ADR 0063: F3B accepted-art reference studies

Status: Accepted, 2026-09-18.

## Context

F3A owns one accepted, upstream-shaped `art.json`, including stable scene and
prop IDs. It intentionally owns no generated image or managed asset. Reusing a
shot job would wrongly require storyboard/Approval authority; a second generic
job store would duplicate the existing manual ImageGen and managed-asset path.

## Decision

F3B adds an accepted-art-bound exploratory proposal on the existing manual
ImageGen exchange. The author chooses only a current stable `scene` or `prop`
ID and supplies a thin render-direction overlay. Trusted code freezes the
accepted art revision/hash and the exact subject hash, copies/verifies the
package, owns currentness, cancellation and lifecycle blockers, and imports
verified candidate bytes as managed assets. ImageGen owns only untrusted
candidate bytes and its prompt/provenance declaration.

The overlay explicitly records cinematic realism beside the preserved upstream
semi-realistic painterly `art.json` direction; it does not reinterpret the
upstream preset or alter canon. Studies are inspectable reusable evidence, not
art acceptance, production selection, a Shot, an Approval, or F5/F7 proof.

## Consequences and guardrails

- A changed/reopened accepted-art revision makes an older proposal visibly
  stale and prevents Copy or current delivery admission; original bytes and
  inapplicable late-delivery evidence remain retained.
- Explicit cancellation is terminal, releases close/snapshot publication
  blockers, and refuses late acceptance. It does not delete the package or
  accepted art.
- The package retains the existing pinned ImageGen preflight, exact staging
  cleanup and managed-asset provenance. No provider, queue, or media store is
  added.
- Project folders use their own exact SQLite schema and do not run application
  Alembic migrations. The immediately preceding F3A folder schema therefore
  receives one exclusive-lease, additive transition that creates only the
  three empty F3B proposal tables and validates the exact result. It does not
  rewrite project rows, replay work, or support older mixed schemas.
