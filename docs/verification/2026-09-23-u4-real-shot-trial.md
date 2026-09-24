# U4 lighthouse opening: one real shot trial

## Boundary and source

This bounded development trial uses a separate retained copy at
`.local/relay/real-shot-trial/{outputs,application}`. The original U4 project,
the accepted 27-cut installation on 8822, the read-only 8823 handoff, and the
user's accepted 8831 synthetic exercise were not changed. The copied project
keeps the accepted F5 bridge r2 and exact six-second cut `opening-s1-c1`.
There was no source retiming, whole-route generation, additional provider, or
second H3 submission.

The agent recorded a technical-only Storyboard Approval on the isolated copy
with its actual label, `Codex technical shot trial`, and a note explicitly
withholding director creative acceptance. The one built-in ImageGen keyframe
was imported through the managed asset API with rights `unknown` and SHA-256
`7c4c375db892b1b1cbc02136df59ab7fb627affbaf9437e2202b9fb939627d48`.
That same image was explicitly chosen as C01's current identity reference and
as this shot's reviewed keyframe; no identity continuity across other shots is
claimed. The keyframe is 1672×941, and the frozen H3 request explicitly asks
the gateway for a centered cover-crop to its 960×544 landscape profile.

## Prompt and one live dispatch

Preflight checked the current [MiniMax I2VA guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/.agents/skills/h3-prompt-writing/references/base-en.txt)
and the pinned Shuohao `h3-prompt.md`. The installed F5 cut retains an
upstream two-picture prompt spanning this and the next cut. It is preserved
as source provenance, but the single-image product adapter correctly consumes
the frozen canonical shot, resolved C01 context, and one exact dialogue cue,
`一枚，只够一边。`. The prior flat compiler omitted H3's I2VA alignment and
named sound fields. [ADR 0083](../adr/0083-h3-single-image-prompt-contract.md)
records the versioned source-owned correction. The actual submitted v1
payload used the first-frame instruction and three named fields, carried the
line once in `<d>[Chinese]...`, and requested no captions. Its SHA-256 was
`ba9efd21d166279254d9b6304a99ca5abf6c0e790ee7c4fb8b09a97b6fb87c89`.
Later independent review corrected general music, off-screen speaker, and
frozen-compiler cases as v2; the v1 formatter remains executable byte-for-byte
for this retained submitted job. The observed extra speech in old F6 output
has no proven single cause, and this trial does not reclassify it.

Prepared job `vj_54c2fd33002c4598b95dbe618129ab47` bound the accepted F5
source coordinates and six-second shot to a qualified eight-second, 192-frame,
24-fps, H.264/AAC H3 request; its request hash was
`7ac386d8374c7df59ce16b6470508997cbcfb11d79981c18f1f96486c522ef7e`.
Gateway health was `ok`, generation contract v6, zero queued/active jobs, and
the local product reported an enabled 5/8-second catalog. Exactly one submit
returned known prediction `h3_3fd897c232e74207b52175a6f4f652f9`. Only
that prediction was reconciled. It ingested current and unselected, SHA-256
`38aa919615253555b42babb56db200a25b8de0c1c4472283d21c99cfb71c5356`,
at 960×544, 8.000 seconds, 192 decoded frames, 24 fps, H.264/AAC.

## Six-second derivative and actual review limit

The first `[0,144)` preparation failed safely: the 32-kHz AAC derivative
reported occasional one-sample decoded PTS rounding, while the validator
required exact equality. The same failure reproduced with a synthetic 32-kHz
source. The fix compares each decoded timestamp with the first timestamp plus
its cumulative sample count, allowing at most one sample of local rounding;
larger gaps or drift remain blocked. [ADR 0082](../adr/0082-proposed-production-playback-timing.md)
records the decision and a true-gap regression. No provider call or quality
gate was bypassed to repair the local derivative.

After the fix, the public segment API prepared proposal
`3edc3c5e-4baa-42a7-b1e6-b51a46408d33` from original frames `[0,144)`.
The derivative SHA-256 is
`24b07ccd51c6a07b589ea54928d57c50d649f22cf0b72c60da063bc9be019b0f`.
Its trusted probe reports 144 frames at 24 fps, 6.000 seconds, 960×544,
H.264/AAC, audio start 0, audio end 6, and exactly 192,000 decoded samples
at 32 kHz. The original eight-second bytes and hash remain unchanged. Visual
frame inspection found one continuous keeper/switchboard shot with no visible
subtitles in sampled frames. By the end she pushes the fuse toward a small
contact between the two large route sockets; whether that image communicates
the intended undecided circuit state remains a director judgment.

The headed workbench at 1440×900 and 1920×1080 presents the original,
`[0,144)` pending segment, and explicit confirmation separately. Its unmuted
native preview reached `ended` at 6 seconds with media range responses.
Screenshots are retained in `output/playwright/real-shot-trial/`. This agent
could verify the AAC stream and browser playback, but could not hear the
Mandarin output: the available audio-content tool explicitly omitted audio
input. Therefore the required listened-with-sound audiovisual review is
unfinished. The derivative remains **unselected**; no director quality or
creative approval is claimed. The route player correctly reports missing
current selections for the other 26 cuts rather than implying a complete
story. The persistent, H3-disabled but writable workbench is available at:

`http://127.0.0.1:8832/v2/?project=fbb913c8-534b-4439-ba68-211e70ec743d&stage=storyboard&entity=shot%3Aopening-s1-c1#video-segment-review-vj_54c2fd33002c4598b95dbe618129ab47`

The isolated root README documents its LaunchAgent and teardown. This is a
reviewable real-media preview; director audition and explicit segment
selection/rejection are the remaining step for this one shot.

## Verification

### Subsequent director listening feedback and diagnostic follow-up

The director reported hearing `一枚，只够一边。` and additional unclear
speech before it. This is failed dialogue-quality qualification, not failed
delivery. No exact timestamp or transcription of the additional utterance is
established. A subsequent read-only API check confirmed the job and `[0,144)`
segment remain unselected; no review mutation accompanied this note.

The retained v1 snapshot reconstructs the submitted prompt hash
`ba9efd21d166279254d9b6304a99ca5abf6c0e790ee7c4fb8b09a97b6fb87c89`.
It contains exactly one dialogue block, `S1 says once`, an environmental
soundscape ending `no additional voices`, and music `N/A`. The frozen shot
has one dialogue cue and no audio-plan events. The upstream two-cut H3 prompt
contains another line, but that provenance field was not dispatched. Thus
duplicate dialogue in this submitted prompt is not supported as the cause.
Model-added speech remains a hypothesis, not a diagnosed mechanism.

The next experiment is design-only: retain the exact v1 baseline, keyframe,
seed, model/profile, crop, duration, and audio settings; change only the
soundscape instruction to explicitly disallow vocal utterances before or after
the single quoted line. Listen to both full eight-second takes and six-second
windows for extra utterances, intelligibility, and clipped speech. Retain
failures rather than trimming them away to claim success. One matched-seed
comparison is screening evidence, not proof of a reliable fix. Execution needs
an explicit versioned experiment path preserving the frozen baseline, not an
unrecorded raw-prompt override or a confounded switch to the current v2
compiler. No new generation, provider change, or project mutation was made
during this diagnostic follow-up. The available tools did not provide an
auditory transcript, so precise utterance localization remains open.

The user subsequently authorized the controlled execution. Its separate
[comparison receipt](2026-09-24-u4-h3-vocal-control-comparison.md) records the
one treatment request and retains both candidates for director A/B listening.

Focused prompt, H3 transport, project-video, and segment suites passed; the
complete backend suite passed with 737 tests and one third-party Starlette
deprecation warning. An independent
read-only reviewer found incorrect canonical music-kind mapping and missing
compiler-version dispatch routing. Both were corrected with regressions. The
reviewer's closure pass found one more valid off-screen-speaker case, which was
also corrected. No frontend source changed; the checked-in static build served
the 1440/1920 browser checks. The trial's retained preview LaunchAgent runs
without video credentials, so no additional dispatch is possible from it.
