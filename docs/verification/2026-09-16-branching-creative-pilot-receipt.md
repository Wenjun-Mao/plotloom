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
- ImageGen staging cleanup was attempted for both deliveries. The shared root `/Users/wjmao/.codex/generated_images/01a0aa8a-87ac-7352-9af6-0c51314984b8` is mode `0755`, so the helper refused its current-user-private-root check. The preserved task-owned staged files are `exec-372a3297-199e-4d75-9817-25b34185deae.png` and `exec-18bfd9ca-c8d5-4936-b933-61c732438531.png` below that root; no permissions were changed and no deletion workaround was used.
- The identity package pin was created at `2026-09-16T10:08:48Z`, before its generated file at `2026-09-16T10:09:22Z`. The opening generated file was created at `2026-09-16T10:23:03Z`, but its package pin was created at `2026-09-16T10:24:20Z` and its receipt at `2026-09-16T10:24:53Z`. The checkout revision recorded by both pins was `e4f03701465a657f80a46960fcb5444e157a87f2`; the only later commit is this receipt (`167ae82`), so no source change intervened. The prerequisite was missed because the coordinator incorrectly treated the earlier identity-package pin as satisfying the separate opening-package preflight. The opening receipt is hash-valid, but it is not a valid pre-generation attestation; do not represent it otherwise.
- A hash-verified user-review copy is available at `outputs/20260916T140747516355Z__4d7d4856-e407-4467-9432-3d9187b9edf8/review/opening-h3-vj_fe20e9c8b4834933b3621e02adb9f256.mp4`. Its SHA-256 is `0be698d070a0a5353b24516456d4203c0bfac897246eef595478b32de640062a`, matching the ingested job's `outputHash`.
- The in-app browser crashed when native playback was started. Native Chrome is installed but the Mac was locked when it was requested, so Chrome playback could not be attempted. This environment also cannot listen to the clip's audio. Therefore neither visual playback nor audio quality has been accepted, the opening clip is not selected, and later shots were not generated. This preserves the first-shot-review gate and avoids spending the remaining H3/ImageGen budget on unverified work.

## Required continuation

1. Review the accessible opening H3 clip visually and audibly, especially its rain/train ambience, absence of unintended speech, image quality, and continuity.
2. If accepted, explicitly select it, then continue the remaining three shots under correctly pre-pinned image packages.
3. Produce both branch paths through native playback/reopen before final release.
