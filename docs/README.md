# Plotloom documentation

## Current product contracts

- [Development and operations](development.md)
- [Capability and adoption matrix](roadmap/capability-matrix.md)
- Current ADRs: [0004](adr/0004-canonical-generation-contract.md),
  [0005](adr/0005-generation-runs-and-quarantine.md),
  [0006](adr/0006-media-adapter-boundary.md),
  [0008](adr/0008-capability-based-adoption-tracking.md),
  [0009](adr/0009-atomic-project-bootstrap.md), and
  [0010](adr/0010-plotloom-clean-repository.md)
- [Initial extraction provenance](provenance/initial-extraction.md)

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
