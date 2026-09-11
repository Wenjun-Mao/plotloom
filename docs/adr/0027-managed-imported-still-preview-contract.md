# ADR 0027: Managed imports and reviewed still-preview contract

## Status

Accepted and implemented for the approved P0 slice, 2026-09-11. This is the
implementation record for the non-generative boundary authorized by ADR 0026.

## Decision

- Imported JPEG/PNG originals are content addressed through `ArtifactStore`,
  fully decoded within fixed byte/pixel limits, and re-read after publication.
  Safe display derivatives are distinct stored bytes; neither replaces the
  original.
- A managed-asset record is project scoped and has a separate immutable
  provenance declaration. Identical bytes may therefore have distinct import
  declarations. Imports never create `GenerationRun`, `Artifact`, `MediaTask`,
  provider settings, or provider evidence.
- Visual intent is versioned and exploratory. A reviewed keyframe binding is a
  separate immutable record that checks an active project, exact READY
  storyboard, active Approval/gates, asset ownership, shot/scene context, and
  expected selection revision in one lifecycle transaction.
- A P0 still preview freezes exactly three contiguous scene shots from those
  reviewed bindings with ordered authored durations, exact asset hashes,
  source/approval identities, selection revision, projection version and
  manifest hash. Loading derives `current`, `stale`, `revoked`, `missing`, or
  `corrupt`; it never edits the historical manifest or silently replaces it.
- Individual managed-asset deletion is not exposed. Permanent deletion of a
  media-bearing project refuses before mutation with
  `project_managed_assets_present`; duplicate keeps its existing canonical-only
  boundary and does not copy managed-media bindings. Media-aware erasure and
  reclamation remain a named follow-up.

## Consequences and guardrails

The public managed-media endpoints are deliberately project-scoped and accept
only upload bytes, never local paths or remote URLs. Missing/corrupt byte-store
observations stay distinct from Approval applicability. Provider hard stops and
ProductionSnapshot ownership are unchanged. Regression coverage exercises
decode limits, deduplicated-corrupt blob refusal, independent provenance,
selection revision conflict behavior, manifest/asset-hash corruption,
immutable stale preview history and the permanent-delete guard.
