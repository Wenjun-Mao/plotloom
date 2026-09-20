# H3 vertical-first recipe qualification

Date: 2026-09-20  
Status: historical first portrait screen; later contract work is recorded in ADR 0070

## Purpose and controls

This direct-ComfyUI experiment compared three complete LightX2V recipes at
608×1088 portrait: v1.0 four-step/res_multistep, v1.2 four-step/Euler, and
the ModelTC README v1.0 eight-step/Euler candidate. Each recipe used six fixed
seeds for an audio-only dialogue condition and a restrained-motion condition.
All delivered files were 124-frame, 24 fps H.264/AAC clips, approximately
5.167 seconds long. It neither submitted gateway jobs nor changed a public
gateway profile.

The complete declared experiment is
[h3-vertical-recipe-qualification.v1.yaml](../../services/minimax_h3_gateway/h3-vertical-recipe-qualification.v1.yaml).

## Execution integrity

The original twelve clips labelled as eight-step are excluded. Their runner
selected the eight-step LoRA but inadvertently left inference steps hard-coded
to four. This was detected from the source contract and anomalously equal
elapsed times, not inferred from creative output. Commit `1cdb912` fixes the
recipe model and adds a rendered-graph regression test that requires eight
steps, Euler sampling, and 6/3 video/audio shifts.

Only that invalid subset was rerun. The rerun receipt records all twelve true
eight-step results, each with the frozen complete recipe and a 174.5–180.3 s
ComfyUI elapsed time:
[h3-vertical-recipe-qualification-2026-09-20-rerun-eight.json](supporting/h3-vertical-recipe-qualification-2026-09-20-rerun-eight.json).

The original technical receipt remains retained for the valid twenty-four
four-step outputs and the invalid, explicitly excluded twelve:
[h3-vertical-recipe-qualification-2026-09-20.json](supporting/h3-vertical-recipe-qualification-2026-09-20.json).

All MP4s are direct ComfyUI experiment outputs on Spark:

```text
/home/wjmao/services/spark-comfyui/data/output/experiments/h3-vertical-recipe-qualification-2026-09-20/
/home/wjmao/services/spark-comfyui/data/output/experiments/h3-vertical-recipe-qualification-2026-09-20-rerun-eight/
```

They are not gateway-managed media and therefore do not follow gateway
retention cleanup.

## Human creative review

The reviewer found the v1.0 four-step candidate unsuitable for further
qualification: all six dialogue clips showed subtitle-like text artifacts and
all six motion clips showed a minor eye defect.

The two remaining candidates each pass the dialogue condition in this small
screen but have motion trade-offs:

| Candidate | Dialogue, six clips | Motion, six clips | Interpretation |
| --- | --- | --- | --- |
| v1.2 four-step / Euler | No issue reported. | Minor eye defects in every clip; milder than v1.0 four-step. Mild/obvious shake was noticed for three seeds. | Advances, but temporal stability remains a concern. |
| v1.0 eight-step / Euler, valid rerun | No issue reported; imagery may appear slightly sharper, but that is not a firm comparison. | Blinking lights for two seeds; slight/obvious frame shake for two other seeds. | Advances, but temporal stability remains a concern. |

These observations are deliberately not a statistical ranking. They establish
that both finalists merit the next controlled comparison and that no current
recipe is safe to promote as a public default.

## Historical next gate

The stated cross-geometry screen was completed and reviewed in
[the companion receipt](2026-09-20-h3-portrait-cross-geometry-review.md).
The subsequent public contract is captured in
[ADR 0070](../adr/0070-h3-quality-resolution-contract.md); this document
retains the original screen results and does not itself prescribe the current
gateway catalog.
