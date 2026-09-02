# ADR 0007: Archify for V1/V2 architecture documentation

**Status:** Historical documentation decision. The extraction described below
is complete; [ADR 0010](0010-plotloom-clean-repository.md) governs current
runtime and repository boundaries.

## Context

V2 is being rebuilt as an extraction-ready product whose final repository will
contain no V1 code. During that work we need a durable way to compare V1 and V2
without implying a runtime dependency between them. A plain module graph misses
the contracts that matter most: prompt construction, canonical stage ordering,
validation, atomic commit, evidence lineage, secret flow, and recovery.

## Decision

- Use Archify as an external, documentation-only build tool. It is not a Python,
  JavaScript, frontend, backend, or production runtime dependency.
- Keep authored typed JSON specifications and their checked self-contained HTML
  readers in `docs/architecture/`.
- Use Architecture Delta for the component/responsibility comparison, a
  Workflow for input-to-storyboard behavior, and a Lifecycle for V2 run and
  repair semantics. Do not force all three concerns into one diagram.
- Preserve stable component and connection IDs across V1 and V2 when the
  conceptual responsibility remains comparable. Use new IDs for genuine
  replacements or additions.
- Model V1 and V2 as isolated system boundaries. Comparison artifacts and
  parity tests may relate them; production arrows may not.
- Treat the current files as authored working-tree snapshots. Add Archify
  repository/source evidence only when the represented code is committed at an
  exact public revision.

## Rejected alternatives

- A single Mermaid diagram is easy to edit but does not provide a validated
  Before / Delta / After receipt or the same explorable reader.
- An automatic dependency scanner cannot recover dynamic dispatch, browser
  event wiring, prompt semantics, domain ID relationships, or prohibited/absent
  dependencies without curated facts.
- Adding Archify to the application dependency tree would couple production to
  a documentation renderer and complicate the eventual V2 extraction.

## Consequences and guardrails

The authored JSON is reviewable architecture code, so semantic changes require
the same care as other durable contracts. Generated HTML must come from a
showcase-valid specification and pass Archify containment checks; screenshot
receipts still require human inspection. Tool version and regeneration commands
are recorded beside the artifacts. The future V2-only repository may retain its
V2 diagrams and the historical comparison reader, but it must not acquire any
V1 runtime source or import through this documentation workflow.
