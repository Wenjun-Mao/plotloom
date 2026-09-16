# Branching creative pilot receipt — 2026-09-16

## Scope and current result

- Project: `4d7d4856-e407-4467-9432-3d9187b9edf8` — **末班车的银色吊坠**.
- Canonical structure: one character (梅), one location (旧火车站候车厅), four scenes/shots, one decision, and two terminal outcomes. Story Bible, DAG, scene beats, and storyboard are `READY`; the storyboard is structurally approved at revision 1 with 130 required gates passing.
- All four image jobs have an accepted ImageGen delivery and an explicitly selected reviewed still keyframe. The three non-opening stills each have a Codex-attributed same-person visual review against frozen reference decision `1d9ed569-e752-4e2d-bfc2-ddcc423c73dd`; these are visual assessments, not creator/product approvals or face-recognition results.
- H3 jobs were submitted once only, with profile `Landscape · Fast · 832 × 480`, five requested seconds, and explicit `cover_center_crop` treatment. All four have ingested and are explicitly selected after user review.

## Counts

| Item | Result |
| --- | --- |
| ImageGen calls | 5 of 5 maximum (identity reference plus four keyframes) |
| H3 submissions | 4 of 4 maximum (one per shot) |
| Accepted ImageGen delivery receipts | 5 |
| Reviewed/selected still keyframes | 4 of 4 |
| Ingested/selected H3 clips | 4 / 4 |
| Native path playback/reopen | not executed: native Chrome automation is unavailable on this host |

## Accepted opening clip

- Opening H3 job: `vj_fe20e9c8b4834933b3621e02adb9f256`.
- User review record: `d56a8851-85a-4fbd-a173-05e122491aa5`, reviewer `user`, decision `select`.
- Exact attributed acceptance: **“Everything is good with the video.”**
- The accepted bytes are `0be698d070a0a5353b24516456d4203c0bfac897246eef595478b32de640062a`; this matches both the job `outputHash` and the hash-verified review copy at `outputs/20260916T140747516355Z__4d7d4856-e407-4467-9432-3d9187b9edf8/review/opening-h3-vj_fe20e9c8b4834933b3621e02adb9f256.mp4`.
- The director accepts this opening for creative-pilot use with the procedural limitation below. It must never be described as having a compliant pre-generation package pin.

## Later clip evidence and user selection

| Shot | H3 job | Local review copy | SHA-256 / technical inspection |
| --- | --- | --- | --- |
| `shot_decision` | `vj_209ec588da44460ab10bfcf4fc351abb` | `outputs/20260916T140747516355Z__4d7d4856-e407-4467-9432-3d9187b9edf8/review/decision-h3-vj_209ec588da44460ab10bfcf4fc351abb.mp4` | `5ceac4a5569a8a8ba96e1d4962f6ea2fd0229d7dd68244f7aa6d93c946b5ada1`; H.264/AAC, 832×480, 24 fps, 5.167 s |
| `shot_return` | `vj_d3de4bbe38af4993acad08cbba2517f5` | `outputs/20260916T140747516355Z__4d7d4856-e407-4467-9432-3d9187b9edf8/review/return-h3-vj_d3de4bbe38af4993acad08cbba2517f5.mp4` | `2fc8c0ca52a7822859e18c06c01db2fc7bc20cfdd334142a89be89b4798107fd`; H.264/AAC, 832×480, 24 fps, 5.167 s |
| `shot_departure` | `vj_8b47370268e5463997302a3aaaf53fc8` | `outputs/20260916T140747516355Z__4d7d4856-e407-4467-9432-3d9187b9edf8/review/departure-h3-vj_8b47370268e5463997302a3aaaf53fc8.mp4` | `9e9355179e826c8eaebf0cce65a4194781c34f621f09c619fb29d654a791c100`; H.264/AAC, 832×480, 24 fps, 5.167 s |

The hashes above match the respective ingested jobs' `outputHash` values. These are container and byte-integrity checks only; Codex did not hear their audio.

- The user approved all three with the exact feedback: **“All three are approved. However, the departure ending clip has some minor random H3 video generation defects on her face on a few frames, it's not a plotloom code or asset issue, but it does mean that we need a way to regenerate any of the video clips during the human manual review process. It would be best that we can regenerate as many video clips as we want and they will be all connected for review and choose from. And once the human reviewer decides on which one to use as final, the rest can be deleted.”**
- Normal user `select` reviews bind decision to hash `5ceac4a5569a8a8ba96e1d4962f6ea2fd0229d7dd68244f7aa6d93c946b5ada1` (review `27125b2e-6941-4568-a302-eb9df5b8a152`), return to `2fc8c0ca52a7822859e18c06c01db2fc7bc20cfdd334142a89be89b4798107fd` (review `747a048a-0443-4326-974f-c1bce61d3cc0`), and departure to `9e9355179e826c8eaebf0cce65a4194781c34f621f09c619fb29d654a791c100` (review `fbb495a0-8008-4428-830d-bfb133835030`).
- Departure is selected with its stated minor intermittent H3 face-generation defects, not as defect-free. The reviewer explicitly identified this as neither a Plotloom code issue nor an asset issue.

## Image-generation provenance and limitations

- Correct pre-generation pins exist for decision `ij_d8e271e26e8c476187c028cf7dd56cc8`, return `ij_bae6ed66ffbf4a3ca21c2e9193fa58f2`, and departure `ij_3f74bd4616f8402b9118c8d7d43f6656`; their pins bind each job and request hash at revision `90f3a5956ac7e04a3c7879743bcc4c1bf5174276` before its ImageGen task ran.
- The opening ImageGen delivery receipt remains accepted and hash-valid at `outputs/20260916T140747516355Z__4d7d4856-e407-4467-9432-3d9187b9edf8/runs/20260916T142212424926Z__ij_626bc04948ad4b0394b57e10ad4895b2/jobs/ij_626bc04948ad4b0394b57e10ad4895b2/delivery/completion.json`, with delivered still hash `d38a5a14843fa8ef5124eb76f2c0e3507af22525849d7381f699e195100d7dd0`.
- The identity package was pinned before generation. Opening was not: its file was created at `2026-09-16T10:23:03Z`, its package pin at `2026-09-16T10:24:20Z`, and its receipt at `2026-09-16T10:24:53Z`. The prerequisite was missed by treating the separate identity-package pin as sufficient. No source change intervened, but this does not repair the ordering or create retroactive attestation.
- The decision delivery initially surfaced one rejected receipt for an incorrect identity-hash attestation; the corrected receipt is accepted and bound to the frozen reference hash. The rejected receipt remains auditable and was not repurposed.
- Cleanup was attempted once for every generated ImageGen file. The shared staging root `/Users/wjmao/.codex/generated_images/01a0aa8a-87ac-7352-9af6-0c51314984b8` is mode `0755`, so the helper refused its current-user-private-root check. No permissions were changed and no deletion workaround was used. The preserved staged task files are `exec-372a3297-199e-4d75-9817-25b34185deae.png`, `exec-18bfd9ca-c8d5-4936-b933-61c732438531.png`, `exec-02698f01-4539-483e-b4d8-b76407657de2.png`, `exec-d8bca3f4-012e-45dd-af6a-16421d5ae9dd.png`, and `exec-cc59abe2-ac2d-4391-b08d-fe5111763b38.png`.

## Native playback/reopen boundary and next scope

- Native Chrome automation is unavailable on this host. The approved return and departure paths were therefore not played or reopened natively, and no simulated playback evidence is recorded. A current in-app page confirmed all four video jobs are ingested and selected, but that is state inspection, not native playback.
- No new generation was performed after approval; the ImageGen and H3 caps remain exhausted. All current artifacts are preserved.
- Regeneration of multiple candidate clips, review-connected alternatives, final-only selection, and deletion of rejected alternatives are a separate requested product scope. They were not implemented in this assignment.
