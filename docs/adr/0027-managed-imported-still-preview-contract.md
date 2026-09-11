# ADR 0027: Managed imports and reviewed still-preview contract

## Status

Accepted and implemented for the approved P0 slice, 2026-09-11. This is the
implementation record for the non-generative boundary authorized by ADR 0026.

## Decision

- Imported JPEG/PNG originals are content addressed through `ArtifactStore`,
  fully decoded within runtime-configured byte/pixel limits, and re-read after
  publication. `PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_BYTES` defaults to 8 MiB
  (1–64 MiB) and `PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_PIXELS` to 24,000,000
  (1–100,000,000). Safe display derivatives are distinct stored bytes; neither
  replaces the original.
- A managed-asset record is project scoped and has a separate immutable
  provenance declaration. Identical bytes may therefore have distinct import
  declarations. Imports never create `GenerationRun`, `Artifact`, `MediaTask`,
  provider settings, or provider evidence.
- Storage publication occurs only inside the repository's lifecycle-admission
  lease, after an active project is verified and before immutable metadata is
  admitted. Rejected or archived projects therefore do not start a new blob
  publication; P0 does not attempt unsafe shared-blob cleanup after a storage
  failure.
- Visual intent is versioned and exploratory. A reviewed keyframe binding is a
  separate immutable record that freezes the exact intent ID/revision and
  checks an active project, exact READY storyboard, active Approval/gates,
  asset ownership, shot/scene context, and expected selection revision in one
  lifecycle transaction. The workbench exposes identity, composition, style,
  source references, provenance additions and an explicit retained candidate;
  it never creates an opaque intent during selection.
- A P0 still preview freezes any nonempty contiguous subset of one scene from
  reviewed bindings. The four-image/three-shot plan is an acceptance fixture,
  not a product-wide cardinality rule. Frames retain ordered authored durations,
  exact asset hashes, reviewed intent IDs/revisions, source/Approval identity,
  approval gate-set version, canonical input revisions, selection revision,
  projection version and manifest hash. Loading derives `current`, `stale`,
  `revoked`, `missing`, or `corrupt`; it never edits the historical manifest or
  silently replaces it. Currentness follows only the frozen frame's same-shot
  binding and same asset/role intent stream, not unrelated selection appends.
- Individual managed-asset deletion is not exposed. Permanent deletion of a
  media-bearing project refuses before mutation with
  `project_managed_assets_present`; duplicate keeps its existing canonical-only
  boundary and does not copy managed-media bindings. Media-aware erasure and
  reclamation remain a named follow-up.

## Consequences and guardrails

The public managed-media endpoints are deliberately project-scoped and accept
only upload bytes, never local paths or remote URLs. Missing/corrupt byte-store
observations stay distinct from Approval applicability. The workbench refreshes
when project, selected Shot, board revision or Approval changes, aborting
superseded requests; it restores the persisted current per-Shot selection and
intent context, while a compatibility note remains an explicit review act.
Provider hard stops and ProductionSnapshot ownership are unchanged. Regression
coverage exercises configured decode limits, invalid/animated JPEG/PNG input,
admission before blob publication, cross-project refusal, deduplicated-corrupt
blob refusal, independent provenance, selection revision conflict behavior,
intent/binding currentness, manifest/asset-hash corruption, immutable stale
preview history, real file-SQLite browser refresh/restart/playback, and the
permanent-delete guard. The runtime's local-port preflight uses `SO_REUSEADDR`
so a normal same-port restart is not rejected solely because the stopped
listener remains briefly in `TIME_WAIT`; a hosting-provided `PORT` remains an
exact-port contract and never falls back to a different listener.
