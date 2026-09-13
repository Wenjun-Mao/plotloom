# Plotloom documentation

## Current product contracts

- [Development and operations](development.md)
- [MiniMax-H3 gateway operator and maintainer manual](operations/minimax-h3-gateway-manual.md)
- [Backend-owned video module decision](adr/0035-backend-owned-video-modules.md)
- [Saved-profile conformance runner](conformance.md)
- [Three-story Alpha acceptance runner](alpha-acceptance.md)
- [Capability and adoption matrix](roadmap/capability-matrix.md)
- Current ADRs: [0004](adr/0004-canonical-generation-contract.md),
  [0005](adr/0005-generation-runs-and-quarantine.md),
  [0006](adr/0006-media-adapter-boundary.md),
  [0008](adr/0008-capability-based-adoption-tracking.md),
  [0009](adr/0009-atomic-project-bootstrap.md),
  [0010](adr/0010-plotloom-clean-repository.md),
  [0011](adr/0011-provider-profiles-and-generation-work-units.md),
  [0012](adr/0012-approved-storyboards-and-production-units.md),
  [0013](adr/0013-model-neutral-reliable-generation.md),
  [0014](adr/0014-project-lifecycle-and-workbench.md),
  [0015](adr/0015-exact-work-unit-repair.md),
  [0016](adr/0016-versioned-authoring-quality-gates-and-approval.md),
  [0017](adr/0017-alpha-validation-and-correction-boundaries.md),
  [0018](adr/0018-trusted-story-timing-allocation.md),
  [0019](adr/0019-exact-fragment-and-join-state-contracts.md),
  [0020](adr/0020-alpha-public-score-sheet-drafts.md), and
  [0021](adr/0021-alpha-source-provenance.md)
- [Initial extraction provenance](provenance/initial-extraction.md)
- [Remote CI receipt for `3bf4551`](https://github.com/Wenjun-Mao/plotloom/actions/runs/33671097019)
- [Local text-provider smoke receipt](verification/2026-09-02-local-text-smoke.md)

## Historical extraction decisions

- [ADR 0003](adr/0003-v2-strangler-architecture.md) records the completed
  strangler/extraction strategy and is superseded by ADR 0010 for current
  repository behavior.
- [ADR 0007](adr/0007-archify-architecture-documentation.md) records why the
  V1/V2 comparison readers were created. Those readers are now a historical
  evidence archive, not a current runtime map.

## Architecture readers

- [Architecture index](architecture/README.md)
- [Input-to-storyboard workflow](architecture/input-to-storyboard-workflow.html)
- [Architecture delta](architecture/v1-v2-architecture-delta.html)
- [Lineage and repair lifecycle](architecture/v2-lineage-and-repair.html)

## Research archive

- [Storyboard handbook](storyboard-handbook/index.html)
- [Prompt Pipeline Lab](prompt-pipeline-lab/index.html)

The research readers preserve the evidence used to design Plotloom, including fixed-revision analysis of Narrative Forge and shuohao-skills. They are documentation only: references to old source paths do not create runtime or build dependencies.
