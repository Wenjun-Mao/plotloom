# Persistence media/control modularization receipt

## Status

Implementation candidate completed its required independent review and awaiting
director result review. The preserved intermediate baseline is
`3c68de6a0b119c8836451cb8fea574ae1cde12d2`; it was a passing checkpoint, not
completion acceptance.

## Ownership correction

The former `project/media.py` (2,474 lines) mixed immutable asset lineage,
visual intent/admission, selection/preview, character references, manual image
work, video lifecycle, and legacy media tasks. It is now a 72-line typed
construction root over focused `media_*.py` owners (15–345 lines); the retained
legacy facade delegates directly to those fixed typed collaborators. Typed
`KeyframeAdmission`, `ImageJobCurrentness`, and `VideoJobCurrentness` own the
session-local currentness/admission predicates; they neither open leases nor
reference the retained repository.

The former `application/profiles.py` (668 lines) is now a 179-line explicit
composition layer over `profile_values.py`, `profile_bootstrap.py`,
`profile_catalog.py`, `profile_admission.py`, and `profile_settings.py`
(73–239 lines). `ProviderSettingsPersistence` remains the one owner of the
two-row active-profile/settings projection transaction.

The full persistence-tree line audit finds `legacy_repository.py` at 1,538
lines as the only remaining greater-than-500-line persistence module. Its actual
single responsibility is
documented runtime compatibility composition: construction, named lease/row/
codec guards, and explicit public delegation while runtime callers retain the
`SQLiteRepository` surface. No other persistence module exceeds 500 lines.

## Preserved contracts and checks

- Schema/table ownership, stable hashes/JSON, public repository signatures,
  project-ID/admitted-profile guards, and secret rejection are unchanged.
- Image/reference delivery still admits or rejects under the existing lifecycle
  lease; video reservation/dispatch/release still uses that same lease and the
  shared application ledger session—no nested transaction was added.
- Existing image/video/profile characterization covers stale/revoked lineage,
  delivery idempotency and cancellation/recovery, plus revision and admission
  conflicts. The modularization contract additionally checks every new owner
  is sub-400 lines and has no retained-facade back-reference.
- Independent read-only review restored exact facade signatures, removed a
  duplicate keyframe-admission residue, and required the full-tree size audit.
  The focused post-correction suite passed 59 tests (modularization, image jobs,
  P2/H3 video, profile repository, and provider profiles); FastAPI emitted its
  existing TestClient deprecation warning.
- Locked final gates: frozen dependency sync; 674 passed, 9 skipped Python
  tests; 132 frontend unit tests; frontend typecheck and production build with
  no generated-static diff; 30 browser E2E tests; and a built-wheel installed
  smoke including the Alembic structure/migration check. The frontend build
  retained its existing large-chunk warning; E2E retained its environment
  `NO_COLOR` warning.

No provider call, replay, configuration/data/runtime cutover, migration, or
frontend/generated-static change was performed.
