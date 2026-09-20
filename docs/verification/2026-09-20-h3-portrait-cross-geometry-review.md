# H3 portrait cross-geometry review

Date: 2026-09-20  
Status: base-20 advances as the portrait quality candidate; no public-profile promotion

## Scope

This review joins the valid 608×1088 Turbo screen with additional paired
576×1024 and 704×1280 screens. Each Turbo candidate used the same two scenes
(audio-only dialogue and restrained motion) and six fixed seeds at every
geometry. The 20-step base candidate then used the same controls at all three
portrait tiers.

The earlier labels for a faulty eight-step run remain excluded; this review
uses only the repaired true-eight-step receipt.

## Technical evidence

The base candidate completed 36/36 clips: twelve at each geometry. `ffprobe`
confirmed H.264 video, AAC audio and 124 frames for every file. Each receipt
records `base_model_with_native_sigma_defaults`, no LoRA file, no sigma-shift
override, 20 steps, `res_multistep`, and effective 12/3 shifts:

- [576×1024 receipt](supporting/h3-base20-cross-geometry-2026-09-20-576x1024.json)
- [608×1088 receipt](supporting/h3-base20-cross-geometry-2026-09-20-608x1088.json)
- [704×1280 receipt](supporting/h3-base20-cross-geometry-2026-09-20-704x1280.json)

The direct ComfyUI MP4s remain on Spark under:

```text
/home/wjmao/services/spark-comfyui/data/output/experiments/h3-base20-cross-geometry-2026-09-20-576x1024/
/home/wjmao/services/spark-comfyui/data/output/experiments/h3-base20-cross-geometry-2026-09-20-608x1088/
/home/wjmao/services/spark-comfyui/data/output/experiments/h3-base20-cross-geometry-2026-09-20-704x1280/
```

They are experiment media rather than gateway-managed output.

## Human review summary

| Candidate | Dialogue across portrait tiers | Motion across portrait tiers | Disposition |
| --- | --- | --- | --- |
| V1.2 four-step / Euler | No issue reported in all reviewed dialogue clips. | Seed-dependent drift and shake at 576×1024 and 704×1280; earlier 608×1088 review also reported eye defects and shake. | Retain only as a fast experiment candidate. |
| V1.0 eight-step / Euler | No issue reported in all reviewed dialogue clips. | Seed-dependent shakes at both additional tiers; blinking lights at 704×1280 and earlier 608×1088. | Retain only as a fast experiment candidate. |
| Base 20-step / res_multistep | No issue reported. | No issue reported in all 36 cross-geometry clips. | Advance as the portrait quality candidate. |

This is strong comparative evidence for the 20-step base recipe, not a
statistical proof of general superiority. The screen used two related source
images and two scene types; it does not test a second end frame, a distinct
character/shot sequence, landscape composition, capacity, or throughput.

## Quality-catalog implication

Do not map numeric gateway quality levels yet. The evidence supports a future
`quality=high` entry backed by the exact base-20 recipe, but a public catalog
needs immutable profile/version snapshots plus the remaining continuity and
two-frame tests. The Turbo candidates may later supply a lower-latency tier;
the current evidence does not justify treating the eight-step candidate as a
better quality level than V1.2 four-step.
