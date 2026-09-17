# ADR 0053: synopsis proposal is a Brief/Bible/Graph review boundary

## Decision

Checkpoint 2 treats the existing `ProjectBrief` as the sole required creative
input and the existing Story Bible and Story Graph as the sole generated
proposal. The proposal UI composes those canonical revisions for review; it
does not persist a proposal record, create a new run kind, or introduce an
approval framework.

A proposal run requests exactly `story_bible` and `story_graph`. Its review
states the derived graph counts separately from the author's planning target,
and it explicitly names scenes, shots, and media as out of scope. Editing
remains in the canonical Brief, Bible, and Graph editors. A missing working
title is normalized to the visible `未命名故事` default only when saved; supplied
values remain unchanged.

“Accept and continue” is an explicit navigation boundary into scene planning,
not storyboard Gate/Approval or audiovisual acceptance. It is disabled when
either proposal stage is stale, so an upstream edit must be re-generated rather
than silently carrying an old graph forward.

## Consequences

The first review loop is small, reloadable, and uses current save/revision and
stale-stage contracts. It neither produces downstream content nor promises
runtime, cost, or provider outcomes. A later checkpoint may add a distinct
acceptance record only if it needs durable semantics beyond this explicit UI
transition; it must not overload storyboard approval.
