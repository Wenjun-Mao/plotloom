---
name: plotloom-video-directions-specialist
description: Draft or independently check source-bound final H3 video directions for Plotloom, including spoken dialogue, intentional in-scene writing and prevention of burned-in subtitles.
---

# Final H3 video directions

Use the frozen request and `docs/creative-workflow/native-video-directions.md`.
For `draft`, adapt each source field to faithful English directions. For
`fidelity-check`, compare the original sources, candidate and **complete compiled
prompt**. Return only the requested `directions.json` with its frozen identities
and complete coverage. The host runs validation and renders the report.

## Keep speech out of the picture

- Start from the actual pictured scene. Give the visual directions their own
  no-writing instruction covering captions, subtitles, titles, lower thirds,
  signage, interface text and typography. When the source calls for writing,
  name its carrier and location. For example, a sign reading “出口” above the
  door may stay there. An explicitly chosen message presentation may also show
  its exact text. Neither licenses a transcription of anyone's speech.
- Treat every spoken cue as audio only. Keep speaker identity, delivery and
  performance in English outside the dialogue tag. Trusted code inserts the
  original words and language once, such as `<d>[Chinese] 我们回家吧。</d>`.
  Never copy a line into directions for picture text, ambience or music merely
  because it is spoken. If someone reads the “出口” sign aloud, keep “出口” on
  the sign and in that speaker's tagged cue. Each appearance has its own source.
  In the compiled prompt, look for the explicit instruction to keep speech in
  the audio track and prohibit dialogue-derived overlays. Preserve on-screen and
  off-screen speakers, cue order and intentional silence.
- The first frame and any selected end frame condition the picture. If an
  available reference visibly contains unwanted lettering, identify the exact
  input for correction. A negative prompt cannot reliably erase it. If only
  reference identities are available, record the limit of that evidence.
  Player captions, choice labels and controls belong to the player.
- In a fidelity check, reject contradictions at their source path or at
  `compiledPrompt`. A line correctly wrapped in `<d>` still fails if another
  instruction asks for it as a subtitle. Check the image-alignment line and
  all three H3 fields. Keep physical sounds in `overall_soundscape` and
  non-diegetic music in `non_diegetic_music`. Report findings in the project
  language. A prompt check concerns instructions; actual generated frames are
  separate evidence.

Keep the authorized profile, references, seed and audio settings. This role
drafts or checks instructions only. It cannot submit jobs, change canon or
selections, approve media, or turn a finding into an automatic reroll.

## When a rendered take still has subtitles

In a Last Projection dialogue shot, Quality 1 burned in two lines of writing
even with the compact Visual/Audio/Sound prompt from the earlier successful
study. The same prompt, image and seed gave a clean picture and retained
both Mandarin lines on Quality 8 (Base-20). If the operator is debugging
this defect, point them to that paired comparison. They can select Quality 8
for a separately authorized take and compare decoded frames and speech.
Keep the current assignment's frozen profile and authored dialogue intact.
See the [trial record](../../../docs/roadmap/2026-10-31-h3-final-video-skill.md#controlled-debugging-on-the-two-speaker-shot).

For Mandarin, an operator experiment on the same two-speaker shot replaced
only the two spoken strings with tone-marked Pinyin. Qualities 1, 2 and 3
then produced subtitle-free samples with both lines recognized in order.
Their matched Hanzi controls all produced subtitles. On a longer Quality 1
line, Pinyin also cleared the picture, but ASR missed words recovered from
the Hanzi control. This experiment used the gateway directly.
In a normal draft or fidelity check, keep the original
dialogue for the trusted compiler. Keep authored signs, messages and player
text in their original script. See the [lower-quality findings](../../../docs/roadmap/2026-10-31-h3-final-video-skill.md#lower-quality-investigation)
for the speech checks and limits of transfer to another shot.
