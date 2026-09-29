# MOSS D Stage-1 reference refinement

**Status:** Four new recordings generated and technically verified on Spark;
owner listening and creative acceptance pending. No Voice Lab provider,
published Voice ID, H3 workflow, or Plotloom integration was changed.

## Why this trial

In the preceding blind shortlist, the owner preferred MOSS D, then MOSS A,
but said even D was not perfect. This bounded trial tests whether variation in
seed or a modestly more conversational direction produces a more natural
Stage-1 reference. It does **not** test same-person identity across lines.

## Fixed and varied inputs

- Same Mandarin audition line as the prior shortlist:
  `雨还没有停。主灯，或者码头，我们只能先保住一边。`
- Same pinned MOSS VoiceGenerator and tokenizer revisions and decoding values
  as the [initial isolated trial](2026-09-28-moss-voicegenerator-isolated-trial.md).
- Original D instruction versus a revised D instruction that retains the
  approximate age, lower textured register, and restrained character, but
  asks for speech directed to someone nearby rather than recitation.
- Seeds `20261001` and `20261002` are paired across the two instructions.
  Identical numeric seeds are a controlled input here, not a guarantee of
  comparable phonemes, timing, or voice identity.
- The original D recording at seed `20260929` is an unchanged control.

The [bounded runner](supporting/moss_d_reference_refinement.py) was executed
in Spark's existing isolated MOSS ARM64 environment. ComfyUI's queue was
empty before dispatch. Neither Qwen Image nor Voice Lab was stopped.
The Spark copy of this runner and its imported original runner are in
`/home/wjmao/services/moss-voicegenerator-trial/tools/`. Reproduction requires
a new, empty output directory; the runner refuses to overwrite evidence:

```sh
/home/wjmao/services/moss-voicegenerator-trial/.venv-arm64/bin/python \
  /home/wjmao/services/moss-voicegenerator-trial/tools/moss_d_reference_refinement.py \
  --model-dir /home/wjmao/models/moss-voicegenerator \
  --codec-dir /home/wjmao/models/moss-audio-tokenizer \
  --output-dir /home/wjmao/services/moss-voicegenerator-trial/experiments/NEW-EMPTY-DIRECTORY
```

| Case | Duration | Raw peak | Generation after load |
| --- | ---: | ---: | ---: |
| Original D, seed 20261001 | 8.24 s | 0.6453 | 5.96 s |
| Original D, seed 20261002 | 5.60 s | 1.1057 | 2.58 s |
| Conversational D, seed 20261001 | 11.52 s | 0.7503 | 4.76 s |
| Conversational D, seed 20261002 | 9.60 s | 0.7826 | 4.07 s |

The raw float WAVs and hash manifest are retained on Spark at
`/home/wjmao/services/moss-voicegenerator-trial/experiments/2026-09-29-d-reference-refinement/`.
Copied raw WAVs were checked against that manifest. The old D control copy
still matches its prior SHA-256
`da061210b3e8360c20be8546089d42382f36a8ada64d953b0c151c64fd6088ae`.

For browser audition, each recording received the **same 0.8 gain**, then
16-bit PCM conversion (`ffmpeg -af volume=0.8 -c:a pcm_s16le`). This prevents clipping of the one raw peak above 1.0
without individually normalizing loudness. Raw evidence was not modified.
All five listening copies passed `ffprobe` duration inspection. The stable
blind audition is at
`/Users/wjmao/Downloads/moss-d-refinement-2026-09-29/listen.html`.
Its reveal mapping is fixed across reloads:

| Blind position | Source |
| ---: | --- |
| 1 | Conversational D, seed 20261002 |
| 2 | Original D, seed 20261001 |
| 3 | Unchanged original D control, seed 20260929 |
| 4 | Conversational D, seed 20261001 |
| 5 | Original D, seed 20261002 |

Owner review should compare naturalness, character fit, intelligibility, and
pauses. A winner here would still need new-line reference-reuse testing and
separate voice-identity review before publication. No model-wide quality
claim follows from these five clips.
