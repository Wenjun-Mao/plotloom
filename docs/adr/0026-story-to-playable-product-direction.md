# ADR 0026: Story-first visuals and pause-and-choose playback

## Status

Product direction accepted in discussion. Architecture amendments below are
**proposed for review**, not implemented. ADRs 0012 and 0016 remain the executable
approval/media authority until explicitly amended and tested. This record does
not lift `production_pipeline_not_ready`.

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

## Proposed architecture amendments

1. **Exploration and production have different subjects.** Reference exploration
   may bind a versioned visual brief and exact available Bible inputs before
   storyboard Approval exists. Its immutable exploration snapshot may produce
   candidates, not production-ready shots. Promotion requires explicit reference
   selection, compatibility review and the active storyboard Approval required
   by ADR 0012. This narrows the current blanket rule only after amendment;
   raw-Shot production remains forbidden.
2. **Visual intent is explicit.** Suggested design details remain proposals until
   selected; additions changing narrative facts go through canonical editing and
   normal stale propagation. Compilers deterministically render chosen intent.
3. **Artifacts and choices are separate.** Originals are immutable, derivatives
   separately identified, and selected reference/candidate bindings revisioned.
   Semantic likeness preservation requires review, not just a content hash.
4. **Playback is a derived snapshot.** A session pins a manifest of graph/state
   semantics, ordered media bindings and artifact hashes. Draft preview can show
   gaps; complete mode requires current approved inputs and all reachable media.
   Shared-node reuse must satisfy incoming-state and join contracts.
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

Accepting technical amendments requires domain/API/migration and UI tests for
exploration promotion, immutable provenance, stale selection, no raw-shot bypass,
playback graph equivalence, exactly-once choice effects and incomplete-preview
labelling. Existing historical contracts must remain readable and unchanged.

## Follow-up

See [the roadmap](../roadmap/story-to-playable-alpha.md) for milestones, open
questions and independent-review briefs. Before P0, settle the exploration
amendment and cross-reference the exact changes from ADRs 0012/0016. This ADR
records the decision boundary without retroactively rewriting their history.
