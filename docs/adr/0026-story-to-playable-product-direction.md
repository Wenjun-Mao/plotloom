# ADR 0026: Story-first visuals and pause-and-choose playback

## Status

Accepted direction and P0 architecture amendment, 2026-09-11, following the two
external reviews and user authorization to amend the records. Not implemented.
The P0 implementation plan revision 1 was approved on 2026-09-11. This record
amends ADRs 0012/0016 only for the explicit non-generative paths below; it does
not lift provider `production_pipeline_not_ready` checks. Later media execution
and branching-runtime contracts still require their own bounded plans.

## Context

The text workbench now has a usable storyboard foundation, but the user's desired
result is a playable branching audiovisual story. Most projects start with only
a story; later projects may bring visual assets whose originals must be preserved.
Requiring an exhaustive asset library before showing shots delays creative
feedback. Treating native audiovisual generation as silent video likewise misses
the intended first-video experience.

## Accepted product decisions

- Cinematic realism is the initial target. Creators primarily select/refine
  proposals, with detailed editing available.
- Development-session generated images may enter through the same controlled
  import workflow as other supplied assets. They are not evidence that Plotloom
  called an image backend, nor a dependency on this coding session in the product.
- Deliver a visual pilot, an audiovisual clip, an in-app sequential scene and
  finally a playable branching sequence. Native audio is included when supported.
- Initial decision playback stops after the node sequence, holds the last frame,
  shows options and waits indefinitely. No timed/implicit choice. Chosen edges
  follow the canonical graph; playback is not another authoring authority.
- Three initial keyframes depict one continuous dramatic moment. One audiovisual
  clip remains the first technical result; an adjoining-shot test must establish
  cross-cut identity, action, voice and sound before expanding scene production.

## Decision: three explicit authority boundaries

1. **Import/exploration:** controlled imports, immutable originals and versioned
   visual intent may exist before storyboard Approval. Exploratory associations
   are candidates, not reviewed production bindings. Development-generated images
   are imports with declared provenance, never fabricated provider successes.
   P0 includes no exploratory provider generation.
2. **Reviewed still preview:** an explicitly non-generative immutable projection
   binds exact approved storyboard/upstream revisions, applicable Approval and
   gate identity, reviewed selection revisions, asset hashes, selected visual
   intent, ordered shot IDs and authored durations, plus projection version/hash.
   Admission checks current authority coherently in the repository. Historical
   previews remain readable and labelled stale/revoked when no longer applicable;
   no implicit rebuild follows a head or selection change. Missing/corrupt media
   is separate from staleness. This is not a ProductionSnapshot or MediaTask.
3. **Provider production:** unchanged hard stop until full ProductionUnit and
   ProductionSnapshot admission exists. No raw-Shot shortcut or generic
   exploration flag can bypass it. P0 projection inputs may be reused later, but
   must be revalidated and frozen under the production contract, not relabelled.

## Supporting decisions

1. **Byte identity is not provenance identity.** Reuse content-addressed storage
   under separate managed-asset records. Deduplicating bytes must not merge
   different import declarations or make generation evidence run ownership
   nullable. Verify usable stored bytes before publishing an imported asset.
2. **Visual intent is explicit.** Suggested design details remain proposals until
   selected; additions changing narrative facts go through canonical editing and
   normal stale propagation. Compilers deterministically render chosen intent.
3. **Artifacts and choices are separate.** Originals are immutable, derivatives
   separately identified, and selected reference/candidate bindings revisioned.
   Semantic likeness preservation requires review, not just a content hash.
   Selection is revision-checked and scoped to its project and reviewed context.
   A preview captures a coherent set atomically; selecting a candidate need not
   rebuild every preview. Never auto-promote a newly completed task. Retention
   includes historical bindings/projections, with explicit permanent-delete
   semantics rather than silently orphaned files or erased shared bytes.
4. **Playback is a derived snapshot.** A session pins a manifest of graph/state
   semantics, ordered media bindings and artifact hashes. Draft preview can show
   gaps; complete mode requires current approved inputs and all reachable media.
   Shared-node reuse must satisfy incoming-state and join contracts. Completeness
   eventually covers reachable depiction contexts, not merely shot IDs. Existing
   join descriptors are not a complete playback state engine; P4 must define
   initial state and incoming-edge resolution without rewriting canonical facts.
5. **Audio and timing remain authored intent versus observed output.** Native
   audio capability and actual track presence are distinct from content fidelity.
   DialogueCue remains authoritative. Measured clip duration drives delivery
   playback; creative retiming is not a silent binder repair.

## Alternatives and consequences

- Full asset library first: rejected as the initial workflow; expand only after
  representative shots demonstrate usefulness.
- External-editor-only delivery: rejected for basic sequential/branching preview;
  professional editing/export can complement Plotloom later.
- Silent video followed by mandatory TTS: not the default; retain as a future
  alternative if native-audio pilots expose a concrete unmet requirement.
- Relax all media approval rules: rejected. Exploration has an explicit subject
  and lifecycle; it cannot impersonate approved production.
- Exhaustive provider platform before a visible pilot: rejected. Import and
  selection establish a reusable first product slice before live integrations.

P0 requires domain/API/migration and UI tests for import/selection authority,
immutable provenance, coherent snapshots, stale/revoked applicability, safe
retention and unchanged provider hard stops. Playback graph equivalence and
exactly-once choice effects belong to P4, not P0. Existing historical contracts
must remain readable and unchanged.

## Follow-up

See [the roadmap](../roadmap/story-to-playable-alpha.md) for milestones, open
questions and independent-review synthesis. The
[P0 implementation plan](../roadmap/p0-imported-still-preview-plan.md) owns the
bounded next implementation proposal. No source change is implied by accepting
the roadmap; execution needs approval of that plan and a separate handoff.
