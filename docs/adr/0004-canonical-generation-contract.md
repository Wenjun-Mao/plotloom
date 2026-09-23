# ADR 0004: Canonical stages, revisions, and stale propagation

> **Current identity scope (2026-09-23):** The UUID sentence below records the
> original canonical-stage decision, but is not a UUID-only rule for authored
> entity IDs. Current `StableId` accepts concise delimiter-free alphanumeric,
> underscore, and hyphen IDs; trusted generation may bind its own immutable IDs.
> Record/project identity and revision-bound snapshot identity are separate
> contracts. See `src/plotloom/canonical_schema.py` and the generation binders.

## Context

The legacy text prompt asks for a complete story tree and storyboard in one
response, while its installer enforces only a subset of that promise. It also
conflates narrative nodes, dramatic scenes, beats, and camera shots. This allows
invalid topology to look like a successful storyboard and makes partial rebuilds
unsafe.

## Decision

Plotloom has four canonical stages:

1. `story_bible`
2. `story_graph`
3. `scene_beats`
4. `storyboard`

Each stage has a typed payload, a current integer revision, provenance, and a
status of `missing`, `ready`, or `stale`. Entities use stable UUIDs; relationships
refer to stable IDs while execution resolves an immutable `id@revision` snapshot.

The interactive graph is a reachable directed acyclic graph with one start,
valid endings, explicit state patches, and explicit join contracts. Beats and
shots are separate entities connected by first-class `ShotBeatLink` records.

A valid first-time generation may automatically advance through all four stages.
Editing a stage increments its revision and marks every downstream stage stale;
it never spends model credits automatically. Rebuilding stale data requires an
explicit user action and creates new revisions rather than overwriting history.
Every generation request names one contiguous range in the canonical order;
disjoint ranges are rejected instead of being normalized into an unsafe partial
dependency closure.

## Consequences and guardrails

No default values may be silently inserted to make an invalid model candidate
canonical. Media and export tasks consume immutable snapshots, never mutable
stage heads. Optimistic writes require `expectedRevision` and reject conflicts.
All candidates requested by one run are validated and installed in one database
transaction, so a downstream failure cannot leave an upstream partial commit.
