# MiniMax-H3 Mandarin dialogue probe

Date: 2026-09-13  
Scope: one private Spark gateway smoke; not a Plotloom candidate selection or
multi-shot acceptance.

## Frozen conditions

- Gateway profile: `minimax_h3_fp8_turbo4_480p`.
- Reference: the previously reviewed Mara keyframe, prepared with the
  explicit `cover_center_crop` policy.
- Prompt direction: a restrained close-up, one calm breath, then the Mandarin
  line `我找到了。`; natural audible female Mandarin speech, visible lip sync,
  no narration or music, quiet room tone.
- Gateway job: `h3_22150413e5fa445aafdbf28ed6c4e9ec`.
- Result SHA-256:
  `20cb342e1586836e8f3226377b3917616a602f6247ba924980b149b8e209c60d`.
- Observed container: H.264 video, AAC audio, 864x480, 24 fps, 5.167 seconds.

## Review observation

The project reviewer watched the actual gateway-proxied output and reported
that the line is intelligible and lip-synced.  The audio stream is present and
materially above the earlier non-dialogue smoke's level (mean volume -34.2 dB
for this probe versus -56 dB for the earlier ambience-only clip).

## Boundary

This is evidence that the fixed H3 profile can produce a satisfactory spoken
line under these exact conditions.  It does **not** establish reliable
dialogue generation, character voice locking, adjacent-shot continuity, or
automatic acceptance.  The output was not imported, selected, or attached to
a Plotloom project.  Those claims remain subject to the P2-H3 adapter and the
later reviewed adjoining-shot checkpoint.
