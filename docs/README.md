# Plotloom documentation

## Current product contracts

- [Development and operations](development.md)
- [Spark generation operations index](operations/README.md)
- **MiniMax-H3 video:** [operator and maintainer manual](operations/minimax-h3-gateway-manual.md), [Chinese client guide](operations/minimax-h3-gateway-client-guide.md), [reproducible setup](../services/minimax_h3_gateway/docs/h3-reproducible-setup.md), and [sampling rationale](../services/minimax_h3_gateway/docs/h3-rationale-and-operations.md)
- **Qwen-Image-2.1 image:** [operator and maintainer manual](operations/qwen-image-gateway-manual.md), [Chinese client guide](operations/qwen-image-gateway-client-guide.md), and [reproducible Spark setup](../services/minimax_h3_gateway/docs/qwen-image-spark-setup.md)
- [Shared H3/Qwen generation lane](adr/0072-shared-qwen-image-and-h3-generation-lane.md) and [reviewed Qwen canvas contract](adr/0073-qwen-image-reviewed-canvas-contract.md)
- [Backend-owned video module decision](adr/0035-backend-owned-video-modules.md)
- [MiniMax-H3 reviewed profile catalog](adr/0036-minimax-h3-profile-catalog.md)
- [Reviewed keyframe aspect preparation](adr/0037-reviewed-keyframe-aspect-preparation.md)
- [H3 gateway durable FIFO dispatch](adr/0038-h3-gateway-durable-fifo-dispatch.md)
- [H3 gateway-managed output retention](adr/0039-h3-gateway-managed-output-retention.md)
- [Saved-profile conformance runner](conformance.md)
- [Three-story Alpha acceptance runner](alpha-acceptance.md)
- [ADR authority and discovery index](adr/README.md); the old
  [capability/adoption matrix](roadmap/archive/superseded/2026-09-02-capability-matrix.md)
  is historical, not an active delivery plan
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
