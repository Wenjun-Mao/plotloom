# U4 H3 vocal-control comparison: one retained treatment

## Authority and boundary

After the director [reported additional unclear speech](2026-09-23-u4-real-shot-trial.md)
before the intended line, the user authorized one controlled H3 follow-up.
This is a development comparison, not creative acceptance or a diagnosis of
the model's mechanism. A separate retained copy at
`.local/relay/real-shot-comparison/{outputs,application}` contains both takes;
the original 8832 trial and all U4/source/synthetic project roots were not
changed. No ImageGen call, additional provider, retry, selection, or rejection
was made. [ADR 0084](../adr/0084-h3-v1-vocal-control-comparison.md) records
the deliberately narrow versioned preparation path.

## Frozen comparison and dispatch

Baseline job `vj_54c2fd33002c4598b95dbe618129ab47` remained current,
ingested, and unselected. Its exact v1 submitted prompt reconstructs to
SHA-256 `ba9efd21d166279254d9b6304a99ca5abf6c0e790ee7c4fb8b09a97b6fb87c89`.
Treatment job `vj_83dc62e692f24ca3a95e9c1a524fcec0` froze compiler
`plotloom.h3-i2va.v1-vocal-control.v1`, baseline lineage, and exact prompt
SHA-256 `90885d11d90e2cd0d9fe58692993685d6d1d1f6dbf29a71193fc6b6a489a5d61`.
All other snapshot fields matched the baseline, including canonical action
and dialogue, reviewed keyframe SHA-256
`7c4c375db892b1b1cbc02136df59ab7fb627affbaf9437e2202b9fb939627d48`,
provider adapter 5 / capability 6 / endpoint fingerprint
`2a2a8dfc62e5be12fb81ae400b215b7d9dbb39060679c26e4a84319762d1fcdb`,
quality-1 landscape `960x544` profile v1, 8 seconds / 192 frames / 24 fps,
native audio, centered cover-crop, and seed `20260923`.

The entire provider-text diff was one `overall_soundscape` sentence:

```diff
-overall_soundscape: Only environmental and physical sounds of the depicted scene; no additional voices.
+overall_soundscape: Only environmental and physical sounds of the depicted scene; S1's single quoted line is the only vocal utterance in the entire clip, with no speech, murmurs, or other vocal sounds before or after it.
```

Before the sole POST, gateway health was `ok`, contract v6, queue 0, active
dispatches 0, and the exact profile remained in its catalog. The prepared
request hash was
`40d03844d576a37e259ece2df80866fdddc30efe50835136290844021d3dd960`.
One normal submission returned known prediction
`h3_928d2081fe594979b8beb6f390a676a3`; only that ID was reconciled.

## Media and review boundary

The treatment original ingested current and unselected with SHA-256
`890de05d3f7181bdd5bd5dab99a9d461fc354387a404295b3c80f73201fd8a76`.
The trusted probe and independent `ffprobe` report 8.000 seconds, 192 frames
at 24 fps, 960×544, H.264/AAC. The public segment API prepared a proposed
`[0,144)` derivative, ID `0d79718c-ec64-4632-a4e6-c9973abb2407`, SHA-256
`795f8309572780875d97bb1040b7ac74dca8f828888f261492b1f884e54d251e`.
It is 6.000 seconds, 144 frames at 24 fps, with 192,000 decoded 32-kHz
audio samples and exact audio bounds 0–6 seconds. Both source originals retain
their hashes; the baseline derivative remains ID
`3edc3c5e-4baa-42a7-b1e6-b51a46408d33`, also unselected.

The headed workbench was checked at 1440×900 and 1920×1080. It shows two
current original candidates and both proposed segments. The treatment's
unmuted native six-second player reached `ended` at exactly 6 seconds;
screenshots are in `output/playwright/real-shot-comparison/`. The agent could
not hear or transcribe the output, so there is no claim that the extra speech
disappeared or that the intended line remains clear. The director should
listen to both full eight-second originals and both six-second derivatives,
including clip boundaries, and explicitly assess extra vocalizations,
intelligibility, and visual/story suitability. A single same-seed pair screens
the instruction; it cannot prove a reliable causal fix. Neither candidate is
selected, and the other 26 route cuts remain missing.

The credential-free retained comparison workbench is:

`http://127.0.0.1:8833/v2/?project=fbb913c8-534b-4439-ba68-211e70ec743d&stage=storyboard&entity=shot%3Aopening-s1-c1#video-segment-review-vj_83dc62e692f24ca3a95e9c1a524fcec0`

## Verification

An independent read-only reviewer confirmed the single provider-text change
and no predispatch blocker. Their API-level regression and typed-error
recommendations were implemented. Focused prompt/project-video tests passed
35 tests; the complete backend suite passed 740 tests with one third-party
Starlette deprecation warning. No frontend source changed.

## Subsequent director listening and disposition

The director listened to B and identified the preceding utterance as the
canonical action sentence `沈岚把铜质熔断器放在两条并列插槽之间。`, followed by the
intended `一枚，只够一边。`. The stronger “only vocal utterance” instruction failed
this listening criterion. This is an observation about the generated audio,
not proof of H3's internal mechanism. The earlier A feedback established
extra unclear speech, not this exact transcription.

The treatment remains an immutable failed comparison, and its original and
derivative remain unselected. New preparation no longer offers this condition.
The official H3 writing skill requires English rewritten directions while
preserving original-language dialogue. Both frozen prompts had Chinese action
and voice directions outside `<d>`; see the [current rendering decision](../adr/0083-h3-single-image-prompt-contract.md)
and [working playbook](../operations/h3-prompt-writing-playbook.md). A new
guide-compliant take has not been generated or evaluated.
