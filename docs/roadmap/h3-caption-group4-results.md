# Group 4 · Template format and shortening

**Completed.** All 48 scheduled first outcomes were generated on native H3 arm A and independently reviewed with GPT-6.1 Terra selected at high reasoning. Seven contained unwanted dialogue subtitles and 41 were visually clear. [Open the playable comparison](http://127.0.0.1:50831/group4-report/index.html). The [execution plan](h3-caption-group4-execution-plan.md) retains all literal prompts, matched seeds and controls.

| Prompt | Captioned | Visually clear | Clear + words verified | Uncertain | Technical failure |
|---|---:|---:|---:|---:|---:|
| Current full | 2/12 | 10/12 | 8/12 | 0 | 0 |
| Creator template full | 1/12 | 11/12 | 10/12 | 0 | 0 |
| Current short | 2/12 | 10/12 | 10/12 | 0 | 0 |
| Creator template short | 2/12 | 10/12 | 10/12 | 0 | 0 |

The template has one matched visual benefit on one confession seed. Shortening has no observed caption-removal benefit in these samples. Template short also introduces captions on one masked-scene seed. Both clear template versions in that confession set retained the intended words in qualified audio evidence. These are descriptive findings on selected scenes.

## What changed within matched sets

Each row covers the same 12 scene–seed sets. A captioned-to-clear change is counted separately from a clear-to-captioned reversal.

| Change | Captioned → clear | With words verified | Clear → captioned | Both clear | Both captioned |
|---|---:|---:|---:|---:|---:|
| Current full → Template full | 1 | 1 | 0 | 10 | 1 |
| Current short → Template short | 1 | 1 | 1 | 9 | 1 |
| Current full → Current short | 0 | 0 | 0 | 10 | 2 |
| Template full → Template short | 0 | 0 | 1 | 10 | 1 |

The two apparent template gains are the full and short comparisons on the **same third confession seed**, not two independent successful seeds. Both pass the intended-word checks. The gain therefore recurs at both detail levels within one seed; it has not recurred across independent seeds here.

## Where captions occurred

Each cell is captioned clips out of three fresh seeds.

| Scene | Current full | Template full | Current short | Template short |
|---|---:|---:|---:|---:|
| Unmasked confession | 2/3 | 1/3 | 2/3 | 1/3 |
| Masked dialogue | 0/3 | 0/3 | 0/3 | 1/3 |
| Realistic phone | 0/3 | 0/3 | 0/3 | 0/3 |
| Illustrated exchange | 0/3 | 0/3 | 0/3 | 0/3 |

For confession, all four versions were captioned on seed `2800242269852570`, all four were clear on `1313521207232448`, and only the current-format versions were captioned on `2205374283373774`. The last set supplies the visual template benefit. The first set shows that the template does not consistently remove this defect.

For masked dialogue, only template short was captioned on seed `1642821163400470`. All four versions were clear on each of `2324315853370889` and `242714137204921`. Thus the first caption introduction did not recur on either later seed.

The phone and illustrated exchange supplied clean controls on every sampled seed. They reveal no caption-removal benefit because their current-format controls were already clear. No speech bubbles or other substitute text were recorded as a replacement for dialogue subtitles.

## Word preservation and interpretation

The audio-only speech/silence readiness pair passed on the retained, pinned local Qwen model. It transcribed the known Mandarin line from the spoken recording and reported no audible speech for the zero-waveform control. Both responses ended on EOS; neither received pictures or the source words. This qualifies the planned audio evidence path, not the new clips themselves.

All 48 unhinted audio observations were fixed before source comparison. Fresh Terra contexts then compared the intended Mandarin clauses in order, accepting the genuine homophones 路/陆 (lù) and 浩/昊 (hào). Forty-five clips have full-word evidence, three were reported as containing no audible speech, and none remains uncertain. These are qualified audio AI observations followed by textual adjudication, not human listening.

The three no-speech observations are all visually clear masked clips: current full on rounds 1 and 2, and template full on round 3. Their images remain caption-clear, but they are excluded from dialogue-preserving clear counts. This leaves 38 caption-clear clips with verified source words. No new generation or speech repair was attempted.

Some Qwen onset/end estimates exceed native clip duration. Those estimates are retained and unused; this check concerns transcribed words. Acting, voice identity, timing and synchronization are ungraded.

The four prompt packages include scene-specific detail removals. Template formatting also adds words, so the result does not isolate token count as a single cause. These selected scenes and seeds do not establish general H3 caption rates or a production default. Earlier Groups 1–3 remain contextual evidence and are not pooled into this sample.

## Evidence and completion state

All 48 actual requests and terminal native graphs match the frozen inputs, with 20 native evaluations per clip. Every retained original passed complete 960×544, 24 fps AV decode and stereo checks. Native first-outcome accounting found no technical failures.

Fresh review contexts inspected all 8,400 native frames through 1,608 full-frame and lower-region contact pages. Raw observations were fixed before common source words and guide images were disclosed; prompt versions, seeds and history remained hidden. Source-aware judgments and proof intervals are retained. Tiny physical-label transcription limits were recorded separately from coverage gaps.

Every original played through in the real browser at rate 1, from zero to native ended events, with no media errors; playback was muted for the functional check. Both windows exited successfully and their shared-service restorations were verified against the original identities. Fresh readback found no running study GPU resources and confirmed RDP service and port availability. Final reopening passed with 48 unique ready players and 48 word-evidence links. All 2,102 served media and review-evidence bodies matched their retained pins. Exact Mac/Spark preservation passed for 13,350 files (44,659,217,053 logical bytes), including all 48 originals and 960 hardlink groups. A fresh Terra/high outcome audit found no substantive findings and independently checked every preserved original against the native, caption and audio records. The [preservation receipt](../../.local/ref2va/caption-factorial-group4-20261113/preservation-receipts/group4-final-01.json) retains the exact archive and snapshot pins.

Evidence roots: `/Users/wjmao/projects/HU/plotloom/.local/ref2va/caption-factorial-group4-20261113` and `/home/wjmao/h3-caption-factorial-group4-20261113`. Native accounting and caption coverage receipts are under `delivery-final-01/`. The first-round and two-round previews remain retained alongside the live comparison. No intervention has been selected for production and no next group has been started.
