# ADR 0036: MiniMax-H3 reviewed profile catalog

## Context

The original H3 gateway exposed one 864×480 landscape profile. Portrait
authoring and higher-resolution candidates require several geometries, but a
free-form width/height request would allow an unreviewed ComfyUI graph or a
mismatched delivered MP4 to masquerade as a frozen production candidate.

## Decision

H3 version two exposes a typed, ordered allowlist. New Plotloom jobs default
to portrait fast (`576×1024`) and may explicitly choose only these profiles:

| Tier | Landscape | Portrait |
| --- | --- | --- |
| Fast | 832×480 | 576×1024 |
| Standard | 960×544 | 608×1088 |
| High resolution | 1280×704 | 704×1280 |

All use the presently evidenced FP8 / official four-step Turbo LoRA workflow,
124 frames at 24 fps with native audio. “High resolution” describes pixel
count only; it is not a creative or production-quality approval.

The old `minimax_h3_fp8_turbo4_480p` profile stays in the gateway solely for
historical jobs. It cannot be selected for new work. Each catalog profile has
an immutable ID and version; Plotloom freezes its geometry, profile version,
seed and aspect policy in a V3 job snapshot. The gateway rejects unknown IDs;
the adapter rejects a response or downloaded output that differs from that
frozen profile.

## Consequences

- The UI has no free-form dimensions and does not silently fall back.
- The gateway renders catalog geometry with trusted `PrimitiveInt` nodes,
  rather than a caller-provided graph or a resolution heuristic.
- Plotloom and the independently deployed gateway retain matching allowlists
  as a deliberate trust boundary; tests compare their safe public descriptors.
- Each profile needs Spark evidence before it is called production-ready.
  Existing evidence applies only to the legacy 864×480 profile.
