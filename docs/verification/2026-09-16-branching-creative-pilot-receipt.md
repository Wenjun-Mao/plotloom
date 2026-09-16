# Branching creative pilot receipt — 2026-09-16

## Scope and current result

- Project: `4d7d4856-e407-4467-9432-3d9187b9edf8` — **末班车的银色吊坠**.
- Canonical structure: one character (梅), one location (旧火车站候车厅), four scenes/shots, one decision, and two terminal outcomes. Story Bible, DAG, scene beats, and storyboard are `READY`; the storyboard is structurally approved at revision 1 with 130 required gates passing.
- The opening still (`shot_opening`) was generated, accepted as asset `7f62ddbc-25f6-43ca-88cb-21b9b8e94d38`, explicitly selected as its reviewed keyframe, and given a Codex visual identity review (`7a1e937d-919d-49c9-bd95-041464c1b753`).
- One H3 submission was made for the opening only: `vj_fe20e9c8b4834933b3621e02adb9f256`, profile `Landscape · Fast · 832 × 480`, 5 requested seconds, `cover_center_crop`, native audio. It completed and was ingested at 5.167 seconds, but is deliberately **unselected**.

## Counts

| Item | Result |
| --- | --- |
| ImageGen calls | 2 of 5 maximum (identity reference, opening keyframe) |
| H3 submissions | 1 of 4 maximum (opening only) |
| Accepted ImageGen delivery receipts | 2 |
| Reviewed/selected still keyframes | 1 of 4 |
| Ingested/selected H3 clips | 1 / 0 |
| Native path playback | not reached |

## Evidence and gaps

- The opening ImageGen delivery receipt is accepted at `outputs/20260916T140747516355Z__4d7d4856-e407-4467-9432-3d9187b9edf8/runs/20260916T142212424926Z__ij_626bc04948ad4b0394b57e10ad4895b2/jobs/ij_626bc04948ad4b0394b57e10ad4895b2/delivery/completion.json`; its delivered still hash is `d38a5a14843fa8ef5124eb76f2c0e3507af22525849d7381f699e195100d7dd0`.
- ImageGen staging cleanup was attempted for both deliveries. The helper refused because the shared staging root was not private to the current user; the exact staged outputs were preserved. No deletion workaround was used.
- The opening job's specialist pin was created after, rather than before, image generation. The accepted receipt is hash-valid, but it is not a valid pre-generation attestation; do not represent it otherwise.
- The in-app browser crashed when native playback was started. This environment also cannot listen to the clip's audio. Therefore neither visual playback nor audio quality has been accepted, the opening clip is not selected, and later shots were not generated. This preserves the first-shot-review gate and avoids spending the remaining H3/ImageGen budget on unverified work.

## Required continuation

1. Review the accessible opening H3 clip visually and audibly, especially its rain/train ambience, absence of unintended speech, image quality, and continuity.
2. If accepted, explicitly select it, then continue the remaining three shots under correctly pre-pinned image packages.
3. Produce both branch paths through native playback/reopen before final release.
