# External Deep Research: unwanted H3 subtitles

Status: owner-authorized GitHub evidence packet. This branch publishes only the research brief and two experiment receipts. No external session has been dispatched.

Mode recommendation: one Deep Research consultant. The remaining need is external discovery and evidence synthesis, not another review of our own experiment design. Pro is deferred unless research exposes a consequential source/runtime discrepancy needing exact implementation analysis.

## Copyable consultant assignment — Deep Research / external evidence discovery

Research how to reduce unwanted burned-in subtitles in locally hosted MiniMax-H3 while preserving exact audible Mandarin dialogue, speaker order, visual action, identity and useful generation speed. We need an evidence-ranked practical approach for our actual setup, not generic video-prompt advice. Determine whether others reproduce this defect, which fixes have supporting evidence, and which are anecdotes, runtime corrections, or mitigation after generation.

### Access and authority

You can browse public web sources and GitHub. You cannot access our Mac/Spark, local files, services, credentials or prior chat. Treat the observations below as owner-supplied experimental summaries, not media you have independently inspected. Do not claim to have watched them. The two linked GitHub receipts supplement this complete brief; if inaccessible, report that limit and still perform external research using the supplied observations. Do not substitute a different revision or infer unavailable artifacts. No code changes, model downloads, API calls or generation are requested.

Purpose: identify the best next bounded action. It is acceptable to conclude that no reliable prompt-only cure is established. Do not require a new architecture or more tests just to fill the report.

### System under investigation

This is the local open-weight MiniMax-H3 FL2VA path, NOT Hailuo 2.x, Wan, or an opaque hosted video endpoint.

- Single NVIDIA GB10 / DGX Spark, Linux ARM64; serialized generation.
- Pinned ComfyUI 0.38.0, commit 6b747c0428c343e1417219641db93a4fb7cb69ae; SageAttention. Do not assume latest source changes are installed.
- Diffusion: minimax_h3_fl2va_pruned_fp8_scaled.safetensors.
- Encoder: qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors, CLIPLoader type minimax.
- Video VAE: minimax_h3_video_vae_int8_convrot.safetensors, maintained video-only FP16 compute; fp16_accumulation enabled. Audio: minimax_h3_audio_vae_fp32.safetensors, BF16 compute. No VAE or runtime change between our matched tests.
- One positive prompt through MiniMaxH3ImageToVideo -> BasicGuider -> SamplerCustomAdvanced. No negative-conditioning input or separate negative encoder/CFGGuider in the graph. A prose heading 'Negative:' would still enter positive conditioning.
- Installed tokenizer registers <d> / </d> as special tokens; prepends raw picture reference blocks; no dedicated Pinyin-to-phoneme input mode was found. Visual/Audio/Sound labels are text, not separately wired modalities.
- Quality 1: LightX2V V1.2 Turbo-4 768p LoRA, strength 1, Euler/simple, denoise 1, explicit video/audio shifts 6/3.
- Quality 2: LightX2V V1.0 Turbo-4 768p LoRA, strength 1, res_multistep/simple, denoise 1, explicit shifts 6/3.
- Quality 3: LightX2V V1.0 Turbo-8 768p LoRA, strength 1, Euler/simple, denoise 1, explicit shifts 6/3.
- Quality 8: original Base-20, res_multistep/simple, denoise 1, NO Turbo LoRA and NO sigma-shift override node; native shifts 12/3.
- Six admitted dimensions: 832x480, 960x544, 1280x704, 576x1024, 608x1088, 704x1280. 24 fps, native joint audio, 17k+5 frame grid.
- Current defect controls: first-frame-only I2V, no image subtitles, no end frame, 832x480, contain_pad, no input/seed changes.

### What we already did

1. September 19: compact Visual/Audio/Sound wording plus V1.2 Turbo-4/Euler produced three clean landscape dialogue observations. Later portrait screens also had clean dialogue observations. V1.0 Turbo-4 nevertheless burned subtitles into all six portrait dialogue clips under similar audio-only/no-text wording. These were narrow screens, not a general cure.
2. October 31: official-format production prompts (English directions, speaker IDs, verbatim Mandarin inside <d>[Chinese] ...</d>, explicit prohibitions on subtitles) still produced Chinese and pseudo-English overlays. One overlay resembled the English direction 'Point out responsibility'. That supports leakage as a hypothesis, not proof of mechanism.
3. Shortening one failed prompt to the following exact compact form did NOT fix Q1:

Visual: A static medium two-shot in the lamplit cinema projection room. The bob-haired woman holds the memory card beside the open handover bag. The woman in the olive jacket rests her hand over hers. They stay at the table throughout. The frame contains no written language, captions, subtitles, titles, lower thirds, signage, interface text, or typography.
Audio: The bob-haired woman says the following line aloud in Mandarin in a clear, slightly dry voice: “你的名字也会留在记录里。” The woman in the olive jacket then replies aloud in a warm, slightly husky Mandarin voice: “我知道。你能先听我解释吗？” The dialogue exists only in the audio track; do not render the words visually.
Sound: N/A.

For this c4 shot, seed 4433825919846515280 (preserve as a decimal string), 9 requested seconds / 226 frames:
- Same compact Hanzi prompt: Q1 117/226 text-detected frames; Q2 111/226; Q3 105/226.
- Q8, identical compact prompt/image/seed/other controls: 0/226 detections, visually clean samples, both exact Mandarin utterances recovered in order.
- Replacing ONLY the two quoted Mandarin strings with tone-marked Pinyin gave 0/226 detections for EACH of Q1/Q2/Q3, with all sampled pictures clean:
  Nǐ de míngzi yě huì liú zài jìlù lǐ。
  Wǒ zhīdào。Nǐ néng xiān tīng wǒ jiěshì ma？
- Unprompted ASR recovered both utterances. Q1/Q3 ASR wrote homophonic 纪录 rather than authored 记录; Q2 emitted traditional Chinese glyphs. No extra speech recovered. No independent listening/voice/naturalness/lip-sync verdict.

4. Second-shot c3: seed 5980719615687449394, 11 requested seconds / 277 frames. The full tagged production prompt with original Hanzi failed Q1 visually (154/277 detections), but passed Q8 visually and on ASR when ONLY quality/whole recipe changed. Authored speech:
明早新馆主就来接收了。你把卡和更正说明放进交接袋，他们就会知道真相。

A Q1 confirmation retained that full failed production prompt, tags and all controls, changing only that cue to:
Míngzǎo xīn guǎnzhǔ jiù lái jiēshōu le。Nǐ bǎ kǎ hé gēngzhèng shuōmíng fàng jìn jiāojiē dài，tāmen jiù huì zhīdào zhēnxiàng。

Picture became clean (0/277 detections), BUT ASR returned 夹奧接待 for 交接袋 and 自鬥真相 for 知道真相. This might be pronunciation error or recognition error; exact audible dialogue is NOT established. It fails our speech-confirmation criterion. Later frames also violate the sustained hand-contact direction. Pinyin is therefore experimental, not a production solution.

5. Separate retained Q1 corpus: 8/13 original dialogue clips had visible subtitles; five had clean sampled pictures/zero lower-frame OCR. Two clean endings had exact authored speech via ASR. Different shots/settings confound inference. Q1 is not inevitably defective.

Measurements: 4fps full-frame contact sheets plus Apple Vision OCR of the lower 45% of EVERY frame; Whisper small with Mandarin language, no target transcript supplied. OCR can miss malformed lettering; ASR does not certify pronunciation, voice or speaker assignment. No human listening acceptance of the new Pinyin renders. Do not convert these samples into population failure rates.

We have already read MiniMax's official writing guidance. Simply recommending <d>, English directions or 'no subtitles' repeats tested advice. We have NOT isolated removing every prohibition/quotation from an otherwise matched prompt, nor shown that a higher resolution, a different encoder precision, newer tokenizer/runtime, or reference audio prevents this defect. Our single-speaker Ref2VA successes do not qualify two-speaker routing or establish subtitle prevention.

### Research questions

1. Find first-hand reproductions from official issues, ComfyUI discussions, Hugging Face model discussions, Chinese/English practitioner reports and identifiable workflows. Separate original FL2VA from Ref2VA, hybrid/fine-tuned/Singularity models, official API and acceleration LoRAs. Retrieve full prompts, versions/settings and before/after evidence where available. Preserve contradictions and missing controls.
2. What does official guidance and implementation actually support for dialogue vs visible text? Investigate <d>, quotes, speaker IDs, field labels, language tags, raw camera wording, negative-list priming, prompt length, multi-speaker dialogue, line length and temporal density. Do not treat a semantic label or keyword as a real API/control without source evidence.
3. Are there relevant tokenizer/special-token, reference formatting or runtime fixes newer than our pinned commit? Identify exact commits, affected behavior, and whether our installed path already includes them. Do not label every artifact a prompt error or recommend an upgrade without a relevant change.
4. Evaluate phonetic representations (Pinyin, IPA etc.) against preservation of exact Mandarin. Clearly separate official support, first-hand demonstrations and conjecture. Do not suggest removing speech, switching to English or silently rewriting authored dialogue to get clean pictures.
5. Investigate checkpoint/LoRA/steps/sampler/resolution/encoder-precision effects only where there is supporting evidence. Our Q1-to-Q8 comparisons changed a complete recipe, so they do not isolate step count, LoRA or sampler alone. Rank whether any setting change is worth its time/memory cost on Spark.
6. If no reliable prevention exists, separately evaluate practical fallback: original-Hanzi Q8, reviewed reference performance/audio approaches, or post-generation text removal. Distinguish genuine prevention from cropping/inpainting/replacement audio, noting composition, hands/faces, identity, lip-sync, ambience and cost consequences. No automatic rerolls or default change.

### Initial discovery leads — unverified advice, not conclusions

- Official pinned prompt skill:
  https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/.agents/skills/h3-prompt-writing/SKILL.md
  https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/.agents/skills/h3-prompt-writing/references/base-en.txt
- Actual ComfyUI encoder/node baseline:
  https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/comfy/text_encoders/minimax.py
  https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/comfy_extras/nodes_minimax_h3.py
- First-hand conflicting subtitle report, but for a DIFFERENT Singularity/hybrid model:
  https://huggingface.co/WarmBloodAban/Minimax-h3_Singularity/discussions/24
  A commenter advertises Justlora/MinimaxH3-Subtitle-Control-LoRA; our unauthenticated check returned 401 and another commenter reports a broken link. Verify availability, provenance, weights, compatibility and evidence before treating this as a usable option.
- Community first-hand report and claims about tags/negative wording:
  https://www.reddit.com/r/aivideomaking/comments/1xbk6li/made_a_7_part_ai_micro_drama_with_minimax_h3/
  Claims conflict and most lack controlled follow-up; do not repeat '100% fixed' as fact.
- Broader reports:
  https://www.reddit.com/r/StableDiffusion/comments/1vg65hr/what_problems_have_you_found_with_minimax_h3/
- A third-party workflow's implementation/claims, not official validation:
  https://huggingface.co/Smite79/MiniMax-H3-Longvideos

Search beyond these leads. Prefer original developer sources/commits and first-hand experiment artifacts over SEO tutorials, reposts, guessed mechanisms or unsupported 'best practices'. For version-sensitive claims, include dates and immutable commits where possible. Do not imply all advice concerns our checkpoint.

### Requested report

Lead with what is established, what is promising and what remains unsupported. Provide:
- A source/evidence table: date, exact model/task/runtime, prompt/graph access, observed issue, proposed fix, actual before/after evidence, confounders and applicability to our setup.
- A concise prompt-writing playbook with concrete Mandarin examples, each labelled documented rule, externally demonstrated technique, or hypothesis. Preserve allowed authored signage/messages rather than banning all visible writing.
- An evidence-ranked recommendation that may favor retaining Q8 or no change. If another experiment is justified, propose at most TWO small causal comparisons, fixed controls and combined picture-plus-speech criteria; explain what decision each result would change. Do not manufacture tests if research adds no actionable evidence.
- Clear separation of prevention, output detection and postprocessing. Include speed/quality/complexity tradeoffs rather than treating subtitle removal alone as success.
- Ordinary clickable URLs for relied-upon claims, precise code/commit references for runtime claims, and explicit access/verification limits. No model-generated citations that require our prior chat.

Further consultation is not required merely because uncertainty remains. End with the cheapest useful next action and what evidence would justify reopening the inquiry. This report informs a decision; it is not generation, product acceptance or deployment evidence.

## Published evidence and revision boundaries

Repository: https://github.com/Wenjun-Mao/plotloom
Discovery branch: `codex/h3-subtitle-research-20261031`.

- [Matched Q1/Q8 subtitle evidence](../verification/supporting/2026-10-31-h3-subtitle-debug.json)
- [Lower-quality Hanzi/Pinyin evidence, including c3 speech-confirmation limit](../verification/supporting/2026-10-31-h3-lower-quality-subtitles.json)

Use the immutable packet commit supplied in the handoff. The branch is based on previously published main `9de44e189a4295ce763afe514aab3f300434fc3f` and contains only this brief and the two copied receipts. Experimental summaries were captured in local source revision `698fa1e4e8bc307e0688db93d7352cc0354ef9b6`; that implementation revision is not published by this packet. Do not treat the branch's older application source as the tested implementation or claim to have reviewed that unavailable revision. This assignment is external research, not a Plotloom implementation audit.

No credentials, provider job IDs, private endpoints, raw databases or bulk media are provided. Full render media and complete c3 prompt are unavailable to this consultant. Facts about those inputs are bounded owner-supplied observations, not independently inspected media. The full c4 control and phonetic representations are included above.
