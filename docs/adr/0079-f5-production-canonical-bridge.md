# ADR 0079: F5 production canonical bridge

Status: Accepted for scoped implementation, 2026-09-22. Product and creative
acceptance remain separate.

## Context

F5A persists an accepted, source-bound upstream storyboard as review evidence.
Current image, video, and playback owners consume the separate canonical V2
Bible, graph, SceneBeatPlan, and Storyboard. U4 proves coherent F1–F5 reading,
not a production projection. In the retained pilot, one F4 scene occurrence
has nine F5 cuts while the current editable Brief planning policy permits two
to four shots per canonical scene.

## Decision

Add a dedicated F5 production-bridge proposal/acceptance owner. It deterministically
freezes accepted F1–F5 plus the project brief, builds a reviewable V2 canonical
proposal with source provenance, and installs it only after an explicit
revision/hash-protected acceptance. F5 remains raw review evidence; the bridge
does not run a model, create an upstream-style shot store, select references,
approve a storyboard, or submit media.

The proposal maps each F5 cut to one canonical shot, not to one H3 job or one
source segment, and maps each F4 scene occurrence to exactly one canonical
dramatic scene. It preserves source-cut coordinates and exact milliseconds,
treats F5 H3 text as review evidence rather than a provider prompt, and
refuses an unsupported exact source duration at video preparation without
conversion. A count outside the frozen Brief's editable shot-range policy is a
visible blocking proposal conflict, not authorization to invent dramatic
segmentation or silently alter the Brief.

F2 consumer mappings provide canonical character IDs only after V2 ID
validation; F3 is evidence and explicit entity mapping, never image selection.
The first install targets empty Bible/SceneBeatPlan/Storyboard heads only.

Canonical invalidation must follow recorded input revisions and upstream
readiness rather than stage order alone. This keeps a source-map graph that has
no Bible input current across the bridge Bible install, while normally authored
or transitively dependent stages continue to stale. The bridge records the
retained graph revision/hash with its three installed canonical revisions.

## Consequences

The implementation needs typed proposal/admission persistence, deterministic
source-preserving projection tests, input-provenance invalidation tests, a
usable Chinese proposal review with explicit acceptance controls, atomic
installation, and a narrow bridge-aware duration guard at video preparation.
It does not migrate existing canonical projects, replay or rewrite F4/F5
history, add a compatibility layer, or change provider capabilities. Existing
canonical review, reference, keyframe, media, and playback owners remain the
next explicit workflow steps.

The detailed mapping, acceptance sequence, exclusions, and test scope are in
[the bridge design](../verification/2026-09-22-f5-to-production-canonical-bridge-design.md).
