# Keep spoken dialogue out of H3 picture text

## Current status

Use Quality 8 for new final H3 production. Plotloom already defaults to this
profile. The directions skill owns prompt writing and checking. Generation
continues on technical success. Investigate rendered media when an issue is
reported, as described in [ADR 0226](../adr/0226-optional-generated-media-quality-review.md).

| Claim | Required evidence | Fresh media | Status |
|---|---|---|---|
| The production instructions reach both final-direction roles | Exact pinned skill at native draft and fidelity-check handoff, stale pin refused | None | Passed both assignment checks and mismatched-hash refusals |
| A normal Plotloom request uses Quality 8 and preserves authored dialogue | Existing backend-default and offline final-request capture tests | None | Passed catalog default and complete Quality 8 request capture |

Five focused cases passed locally using the existing disposable fixtures.
Root verified the source-checkout handoff. The installed checkout is still
on `543df21c`.

## Historical trials and qualification

The lower-quality investigation is complete. Tone-marked Pinyin eliminated
visible subtitles in the two-speaker test at Qualities 1, 2 and 3. Both
Mandarin lines were recognized in order. On a longer Quality 1 line the
picture also cleared, but the exact-speech check failed. Pinyin remains a
shot-specific experimental technique. The workbench offers Qualities 1 and
8. Qualities 2 and 3 are available through the gateway.

The earlier Quality 8 investigation is complete. Both previously failing shots
have Quality 8 replacements with clean sampled pictures and all three intended
Mandarin cues recovered by unprompted speech recognition. The operator-tested
comparison game places both before the first choice. The other 13 clips match
the original game. The first Quality 1 trial remains a recorded failure.
Root owned the three serial debug renders (29 requested seconds), local
evidence and comparison delivery. The original H3 specialist independently
reviewed the diagnosis and operator guidance. At that point the investigation
recommended Quality 8 as an operator-selected remedy.

| Claim | Evidence required | Fresh media | Status |
|---|---|---|---|
| Lower-quality subtitle suppression | Fixed-shot comparison on Qualities 1, 2 and 3 with visual inspection and spoken-cue check, plus a second-shot test | Yes, six new takes | Picture passed on both shots. Short-line ASR supported both cues at all three levels. The longer Quality 1 line failed exact-speech confirmation. |
| Debug the failure | Same-shot controlled renders with decoded picture and spoken-cue comparison | Yes, existing outputs could not predict a changed prompt or recipe's effect | Both fixed-seed pairs passed the scoped picture and speech criteria on Quality 8 |
| Final video workers receive the repo skill | Both draft and independent check use the exact hash-verified skill in native task input | No | Passed through the real supervisor assignment boundary |
| Submitted prompt matches the policy | Offline multipart capture for dialogue, silent shots, intentional lettering, message treatment and reference bindings | No | Passed golden capture, omission controls and 15 retained request replays |
| Existing story remains usable | Retained request audit and selected project restore/export with no regeneration | No | Passed supported restore and byte-identical export of all 15 selected clips |
| Frozen dispatch and provenance remain valid | Stale new dispatch refusal and known-prediction reconciliation | No | Passed focused authority and fidelity regressions |
| Local qualification | Full local gate on the stable source candidate | No | Passed `full` on `543df21c` |
| Installed runtime applies the rule | Quiescence, exact revision and protected-state comparison | No | Passed both installed worker roles, all 15 compiler comparisons and data preservation |
| Initial Quality 1 generation | Two checked single-shot requests through the installed workbench and owner's H3 gateway | Yes | Passed, two successful jobs and 20 requested seconds |
| Initial Quality 1 picture and dialogue | Compare original and new MP4 frames and verify spoken cue content | Yes | Both failed visual inspection. Local speech recognition recovered all three lines. |
| Playable Quality 8 replacements | Play both new takes in context and verify the other 13 media hashes | Reuse debug outputs | Passed in the separate comparison game in WebKit and Chromium |

## Lower-quality investigation

The 13 original Quality 1 dialogue clips provide an in-project baseline.
They used the production compiler before the new skill. Scanning the lower
45% of all 3,754 decoded frames found text in eight clips. A full-frame
sample from each confirmed visible subtitles. The other five had no
detections, and no subtitles were visible in full-frame samples taken
twice a second. All five came from ending scenes.

For two of those five, `e01-s1-c1` and `e02-s1-c1`, unprompted Mandarin
ASR recovered the complete authored line after normalizing punctuation and
simplified/traditional spelling. The transcripts for the other three had
differences or omissions. The examples prove that Quality 1 can render
subtitle-free dialogue in this game. The shots have different actions,
lines, keyframes and seeds, so their differences cannot identify a fix.

The specialist then tested the spoken representation on `n00-s3-c4`.
Each comparison held the complete recipe, keyframe, seed, geometry, duration
and other prompt bytes fixed. Only the two dialogue strings changed. For
example, `我知道。你能先听我解释吗？` became
`Wǒ zhīdào。Nǐ néng xiān tīng wǒ jiěshì ma？`. The model still generated
the speech itself. No dubbing, cropping or subtitle removal was applied.
Root checked the frozen gateway settings, bound image, prompt and downloaded
MP4 digests. The original Quality 1 Hanzi control was reused.

| Gateway recipe | Frames with lower-frame OCR hits, Hanzi | Frames with lower-frame OCR hits, Pinyin | Unprompted Mandarin ASR on Pinyin take |
|---|---:|---:|---|
| Quality 1, V1.2 four-step Euler | 117/226 | 0/226 | Both cues in order, with homophonic 纪录 for 记录 |
| Quality 2, V1.0 four-step res_multistep | 111/226 | 0/226 | Both cues in order, transcribed in traditional characters |
| Quality 3, V1.0 eight-step Euler | 105/226 | 0/226 | Both cues in order, with homophonic 纪录 for 记录 |

The full-frame samples at four frames per second show dialogue-derived
lettering in the Hanzi controls and clean pictures in the three Pinyin
takes. The OCR scan covered the bottom 45% of every decoded frame.
The tests establish a representation effect on this shot at this seed.
ASR cannot establish voice identity, prosody or performance quality.

On `n00-s3-c3`, the specialist replaced only the spoken string inside the
existing `<d>[Chinese]` tag in the failed production prompt. The Quality 1
Hanzi control showed subtitles and 154/277 lower-frame detections. Pinyin
produced clean samples and 0/277 detections. The control's transcript
contained both 交接袋 and 知道真相. For the Pinyin take, the recognizer
returned 夾奧接待 and 自鬥真相. Whether the difference came from pronunciation
or recognition remains unresolved. The take also shows A Lan lifting her
hand despite the hold direction.

The specialist stopped after six serial renders and 56 requested seconds.
Root independently verified the gateway records and reviewed the original
dialogue corpus. The normal compiler continues to insert verbatim authored
dialogue. At the time, the repo skill recorded the finding for operators.
Private receipts are in `.local/h3-final-skill/lower-quality/` and
`.local/h3-final-skill/q1-corpus/`. No deployment was needed for this study.
[Matched controls, prompt substitutions, transcripts and corpus results](../verification/supporting/2026-10-31-h3-lower-quality-subtitles.json).

## Controlled debugging on the two-speaker shot

The original H3 specialist compared the failed requests, reference frames,
historical prompts and installed encoder. Both reference frames are free of
subtitles. In the failed `n00-s3-c4` take, part of the lower line resembles
the English performance note “Point out responsibility”. The gateway passes
one prompt to the H3 image-to-video node and one conditioning stream to
`BasicGuider`. The encoder recognizes the dialogue tag. Neither the tag nor
the headings provide a separate negative prompt or an isolated audio input.

The historical landscape success used a much shorter Visual/Audio/Sound
prompt and the same V1.2 Turbo four-step Euler recipe as Quality 1 here.
For an operator experiment, root used the supported owner gateway transport
outside the production batch. The compact prompt removed both dialogue tags,
the English performance note, the visual paraphrase of the lines and the
duplicate exclusions. It kept both Mandarin lines in order, with a pictured
speaker for each. The actual gateway start-image digest, seed, aspect policy,
832×480 resolution, 9 requested seconds and 226 frames matched the failing
take. The gateway's stored text and downloaded MP4 digest were checked.

| Input on `n00-s3-c4` | Picture evidence | Speech evidence |
|---|---|---|
| Installed production prompt, Quality 1 | Burned-in two-line subtitles. Lower-frame OCR returned text on 123 of 226 frames. | Local ASR recovered both lines. |
| Compact historical prompt shape, Quality 1 | Burned-in two-line subtitles again. Lower-frame OCR returned text on 117 of 226 frames. | Local ASR again recovered both lines. |
| Identical compact prompt, Quality 8 | No subtitles visible in samples taken four times per second. Lower-frame OCR found text on zero of 226 frames. | Local ASR recovered both lines in order. |

The compact test shows that the long prompt and the quoted English direction
are unnecessary for the defect to occur on this shot. It cannot establish
whether any single wording change altered the risk. The OCR count records
frames with detections in the lower 45% of the picture. Visual inspection
establishes that the marks are baked into the video.

For the last pair, the gateway's frozen execution snapshots differ only in
quality and recipe. Quality 8 is the Base-20 recipe with no Turbo LoRA. The
result isolates the complete recipe difference for this pair. It does not
isolate step count, sampler or any other individual setting. The specialist
independently checked both requests, transcripts, OCR results and the two
Quality 8 contact sheets. Quality 1 took 97 seconds of gateway generation
time and Quality 8 took 380 seconds. Queue waits are excluded.

### Confirmation on the handover shot

For `n00-s3-c3`, root used the exact production prompt that had failed on
Quality 1, including its dialogue tag. The input image and all controls
apart from quality/recipe matched. The Quality 1 video had visible subtitles
and OCR detections on 154 of 277 frames. The Quality 8 video had clean
full-frame samples and zero lower-frame detections across all 277 frames.
Unprompted Mandarin ASR recovered the complete handover line in each.
Generation took 138 seconds and 504 seconds, respectively. No direct listening,
voice-quality or general creative acceptance is claimed. The two-speaker
shot's original long production prompt was not tried at Quality 8.
[Paired prompt, input and output hashes, compact prompt and transcripts](../verification/supporting/2026-10-31-h3-subtitle-debug.json).

The comparison build at `Downloads/plotloom-the-last-projection-2026-10-31/h3-subtitle-debug/`
contains the two Quality 8 MP4s. The other 13 videos, player code and
branching choices matched the original. Both new takes played to completion
in WebKit and Chromium, then the first choice led into the next branch.
Project selections stayed intact. Root stopped after the second shot
confirmed the practical recipe choice. No pronunciation change was needed.

At this checkpoint the repo skill added operator troubleshooting advice. The author, model,
compiler and operator retain their existing responsibilities. The 15 retained
multipart comparisons reproduced the prior receipt byte for byte. The skill
structure validator and 34 focused native-assignment, request and I2VA
regressions passed. Full qualification on the executable implementation
remains the earlier `543df21c` result. Exact debug receipts, all-frame
OCR observations and browser logs are in `.local/h3-final-skill/debug/`.
The new operator note is on local main. The installed workbench still uses
`543df21c` and already offers Quality 8. At closeout its database recorded
a submitted video in a running batch and another batch awaiting review.
The operator left that checkout and its active execution pins in place.

## Two-shot live replacement trial

The installed Last Projection home came from a portable restore. Before
generation the operator inspected its recovery record and used the supported
acknowledgement operation. All 17 historical operation records were preserved.
Each shot went through a new native draft, a separate fidelity check and an
explicit single-shot Start under Codex task attribution. All four native
attempts used the pinned skill. The original per-shot seed, first frame,
Quality 1 profile, 832×480 resolution, duration, aspect policy and native
audio setting matched. The original MP4s already exhibited subtitles.

| Shot | Actual output | Observation |
|---|---|---|
| `n00-s3-c3`, A Lan explains the handover | 277 frames at 24 fps, 11 seconds requested | Two lines of distorted writing appear across the worktable. The four-second comparison shows the defect in both versions. |
| `n00-s3-c4`, Xu Wei responds and A Lan asks to explain | 226 frames at 24 fps, 9 seconds requested | The new take renders Chinese-like and English-like subtitles, visible at 1.5 seconds. |

The gateway's stored prompt bytes, scalar controls, start-image digest and
output digest matched each checked job. Four visual samples per second were
inspected across each new clip. Offline Mandarin speech recognition recovered
the authored words in order without supplying the target transcript.
This two-shot result concerns the installed skill and compiler together at
the original settings. It does not isolate a sampler, seed, or wording cause.

The operator ended each completed batch without selecting the failed take.
All 15 production selections were verified. For comparison, a separate copy of
the installed standalone export received the two exact new MP4s, their actual
durations and its own save namespace. The other 13 media files and the player
code matched the delivered choices edition byte for byte. Both test takes
decoded and ended naturally at accelerated playback in WebKit and Chromium,
and the first choice led into the next branch. No third job was dispatched.

The playable test copy, ZIP and side-by-side frame comparison are in the
Downloads game directory under `h3-subtitle-trial/`. Private gateway receipts,
contact sheets, machine transcripts and browser results are in
`.local/h3-final-skill/live-two/`.

## Scope and method

Use the locked local environment, retained Last Projection media and existing
offline H3 fixtures. Root owns disposable checks. The author owns spoken and
visible content, the native model supplies derived directions, and trusted
code owns the explicit visual/audio separation and original dialogue tags.
The independently authored sign “出口” can also be read aloud. The skill and
compiler preserve both sources. The existing gateway catalog, selected profile,
settings, source, grant and UNKNOWN evidence remain protected.

The implementation's full gate covered the changed prompt and native-worker runtime contracts.
The stable candidate received one full local qualification after independent
review. Provider qualification here used offline captures and test doubles.

## Evidence

- The original `plotloom with H3` specialist reviewed the retained recipes,
  proposed wording and the sign/read-aloud correction. Independent source
  review used GPT-6.1 Sol / Medium and found no material issue in the stable
  candidate. Root retains execution ownership.
- All 15 frozen Last Projection requests lacked an explicit subtitle/audio-only
  rule. The clean input image and generated frame at three seconds for
  `n00-s3-c3` were inspected. The frame contains malformed lettering. This
  observation establishes the defect but does not isolate its cause.
- Offline replay sent all 15 prospective requests through the existing transport
  capture. It preserved 19 spoken cues, reference hashes and request controls.
  Original frozen requests were retained. Receipt is
  `.local/h3-final-skill/replay.json`.
- Focused policy selection passed 83 tests. The subsequent native supervisor,
  frozen-authority, final-request and fidelity selection passed 44 tests.
  Exact selectors and commands are retained in
  `.local/h3-final-skill/policy.log` and `contract-native.log`.
- `quick` passed the unfiltered frontend tests and both type checks.
  The repo skill passed the skill-creator structure validator.
- `uv run --locked --no-sync python scripts/verify.py full` passed on
  `543df21c` in 3,881 seconds. All 1,716 frontend tests, 5,091 Python tests
  and 366 browser tests passed. Deterministic frontend build and parity,
  wheel build and installed-wheel smoke also passed. The full log is
  `.local/h3-final-skill/full.log`.
- Supported restore/export produced the same selected-game ZIP SHA-256,
  `14839aa6e9ea5c548fc0134c1721cf65c67fe3ff5650c191502d2849f76711b0`.
  Receipt is `.local/h3-final-skill/retained-export.log`.
- The approximately 400-line source-resource and process modules gained narrow
  additions to their existing pinned-resource and assignment responsibilities.
  Those changes fit their existing ownership without a new abstraction.
- Before activation, all 71 video jobs across the 18 installed homes were
  ingested. The native queue, execution slots and validator-process table
  were empty. The workbench and native bridge restarted on `543df21c`. In
  the installed checkout, ordinary pin discovery and both assignment builders
  produced the expected skill bytes. The installed container reproduced all
  15 prospective prompt hashes and 19 dialogue cues from retained project
  state. Neither readback admitted a job or dispatched a provider request.
- Pre/post comparison found zero changes across 1,836 file digests, 27
  databases and six protected files, including both native UNKNOWN outcomes.
  The installed readback and preservation receipts live under
  `.local/h3-final-skill/`.

Historical media trials and their limits are linked in the
[H3 playbook](../operations/h3-prompt-writing-playbook.md#current-final-h3-skill).
The live replacement trial above extends the original provider-free check.
Hosted CI was not requested.
