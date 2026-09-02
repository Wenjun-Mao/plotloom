# 插图生成记录

本目录中的三张位图插图由 Codex 内置图像生成工具制作，用于《从梗概到分镜》手册的“月城记忆控制室”贯穿案例。它们是教学示意图，不是两个参考仓库的原始资产或运行输出。

## `moon-control-room-board.png`

生成模式：内置参考图生图。参考对象是同目录草图的早期版本；只继承石墨质感和人物设计，镜头内容按下列定稿提示全部重绘。

最终提示词：

> Use case: illustration-story, storyboard continuity sheet for a Chinese practical textbook.
>
> Redraw the supplied reference completely. Preserve only its loose graphite-and-charcoal storyboard style, warm off-white paper, clean 4-by-2 grid, and the protagonist design. Do NOT preserve the old drone/hologram shot content.
>
> Create one landscape storyboard sheet with exactly eight equal panels in a 4 columns × 2 rows layout. No gutters outside the eight-panel grid. Cinematic, highly readable blocking. Keep the same geography in every panel: a circular lunar-city memory control room; central console; on SCREEN LEFT a gold-glowing city memory core; on SCREEN RIGHT a cyan-lit transparent life-support pod containing Ruan Xing’s younger brother; rear-left pressure door; an overhead mechanical emergency lever above the console. Keep screen direction consistent.
>
> Character continuity: Ruan Xing is an East Asian woman in her early twenties, short dark hair, practical lunar-maintenance jumpsuit, orange utility strap, gloves and tool bag. Her younger brother is a teenage East Asian boy in simple maintenance clothing, inside the right-side pod.
>
> Panel order, left-to-right then top row to bottom row:
>
> 1. Extreme wide, slightly low fixed view: rear-left pressure door opens and Ruan Xing rushes to a stop at the center console; gold memory core clearly on screen left, cyan life-support pod and unconscious brother clearly on screen right.
> 2. Medium close tracking-right composition: Ruan Xing presses one hand to the pod glass; condensation from her brother’s breath proves he is alive; a simple red lock symbol glows near her eye; a worn copper memory key is visible in her other hand.
> 3. Extreme close-up insert: her gloved hand inserts the copper memory key from left to right into the console slot; mechanical lock engaged; an abstract gold waveform begins spreading across the display. No words or digits.
> 4. Over-the-shoulder close shot: Ruan Xing’s frozen shoulder in foreground, focus on the gold waveform; warm gold light catches half her profile as she hears her mother’s signal. Do not show the mother or any human hologram.
> 5. Emotional face close-up: Ruan Xing’s eyes shift toward screen right; one eye reflects the gold waveform, the other picks up cyan pod light, clearly expressing conflict.
> 6. Fixed top-down insert of the console: one small remaining power cell in the center feeds two mutually exclusive paths, gold path on left and cyan path on right; Ruan Xing’s hand reaches out of frame toward the overhead emergency lever. No text labels.
> 7. Medium dynamic shot with slight handheld energy: Ruan Xing pulls the emergency lever down with both hands; it jams halfway; sparks burst at its base; her body recoils but she refuses to let go. The right-side pod remains geographically consistent in the background.
> 8. Layered close composition: Ruan Xing’s side face and right hand in foreground at the console; her hand hovers exactly between one gold button and one cyan button; in the right background her brother is now awake inside the pod, looking toward screen left at her. Both his gaze and her indecision must be readable.
>
> Visual style: rough professional storyboard sketch, expressive graphite and charcoal, restrained pale gold and pale cyan pencil accents only where needed for story logic, readable grayscale values, arrows only if essential. Exactly eight panels. No captions, dialogue, panel numbers, UI text, title, watermark, logo, decorative border, security drone, extra people, mother hologram, or finished painting.

最终连续性修订提示词：

> Use case: precise continuity correction to an existing storyboard sheet.
>
> Edit the supplied image in place conceptually. Preserve the exact eight-panel 4×2 layout, all gutters, the graphite-and-charcoal drawing style, character designs, camera compositions, room geography, gold-left/cyan-right color logic, and panels 1 through 6 exactly as they are. Make no global restyle and do not add any text.
>
> Change only these two continuity details:
>
> • Panel 7, bottom row third panel: Ruan Xing is still pulling the jammed emergency lever with both hands and sparks still burst at its base. The younger brother visible in the cyan life-support pod in the background must be unmistakably unconscious at this moment: both eyes fully closed, relaxed head and face, no active gaze, no raised hand, no awakened posture. Keep him subtle and in the background.
>
> • Panel 8, bottom-right panel: the younger brother is now awake and looking toward screen left at Ruan Xing. Ruan Xing’s gloved right hand must be unmistakably UNDECIDED: raise the entire hand several centimeters above the console with a visible band of empty air beneath the fingertips and palm; center the palm over the neutral divider exactly between the warm-gold button on the left and the cool-cyan button on the right. No fingertip may touch, overlap, hover directly over, or favor either button. Both buttons remain unpressed at equal height. Preserve her side profile and the brother’s readable gaze.
>
> No captions, panel numbers, dialogue, UI words, watermark, logo, drone, mother hologram, new character, pressed button, or extra hand.

连续性审校后发现，整张 sprite 的第 7 格仍可能被读成弟弟已经苏醒。网页不再使用该格，而由下面的独立 `moon-control-room-shot-07.png` 覆盖；`moon-control-room-board.png` 只为第 1–6、8 格提供裁切。这个例子也说明：提示词声明不是验收证据，最终资产仍须逐格检查。

## `moon-control-room-shot-07.png`

生成模式：内置参考图生图；参考整张故事板的造型、场景和镜头七构图，单独重绘为可独立修订的方形面板。

最终提示词：

> Use case: one replacement storyboard panel for a continuity-controlled textbook.
>
> Use the supplied sheet only as style, character, costume, room-geography, and camera-composition reference. Do NOT output a sheet or grid. Redraw ONLY shot 7 (the bottom-row third panel) as one self-contained near-square 1:1 storyboard panel with a clean full-bleed image and no border.
>
> Composition: medium dynamic shot with slight handheld energy in the same lunar memory control room. Ruan Xing, the short-haired East Asian maintenance apprentice in the same jumpsuit and orange utility strap, strains backward while pulling a tall mechanical emergency lever down with both hands. The lever is jammed halfway and bright sparks burst from its base. Her effort and the lever’s diagonal must dominate the foreground.
>
> Continuity-critical background on screen right: the cyan life-support pod is visible, but her teenage younger brother is still unmistakably unconscious. Both eyelids fully closed; face, jaw, neck and shoulders slack; head tilted gently down; arms and hands relaxed; no gaze, knocking or reaching. The pod mechanically supports him. A light band of cold condensation crosses the pod glass without hiding his visibly closed eyelids. He does not wake until the next shot.
>
> Match the source sheet’s rough professional graphite-and-charcoal drawing on warm off-white paper, restrained pale cyan pod accent and pale orange-white spark accent, realistic anatomy, consistent screen direction. No text, caption, panel number, dialogue, UI words, watermark, logo, drone, mother hologram, extra person, extra hand, awake eyes, or finished-painting style.

## `moon-control-room-finished-frame.png`

生成模式：内置参考图生图；参考图为上面的八格故事板，仅取第 8 格的构图意图。

最终提示词：

> Use case: sketch-to-render educational comparison.
>
> Use only panel 8, the bottom-right panel, of the supplied eight-panel storyboard as the composition and narrative reference. Produce one single polished 16:9 cinematic finished frame—no storyboard grid.
>
> Preserve the exact shot logic and screen geography. In the left foreground, Ruan Xing is shown in side-profile close view, an East Asian woman in her early twenties with short dark hair and a worn practical lunar-maintenance jumpsuit with an orange utility strap and gloves. Her right hand hovers indecisively over two physical console controls: a restrained warm-gold control on screen left and a cool-cyan control on screen right. In the right background, through a cyan-lit transparent life-support pod, her teenage younger brother has just awakened and looks toward screen left at her. His gaze, her profile, her hovering hand, and both mutually exclusive controls must all be readable in one composition. The worn copper memory key remains inserted in the authorization slot along the console’s upper edge. Do not add a drone, mother hologram, or other person.
>
> Grounded realistic science-fiction production design, not glossy fantasy: scratched dark metal, fine lunar dust, worn fabric, subtle condensation on the pod glass, restrained atmospheric haze. Lighting expresses the moral conflict: warm gold light from the city memory core touches one side of her face and fingers; cold cyan light from the brother’s pod touches the other; a very subtle red emergency rim light may appear. Strong cinematic depth, natural human proportions, emotionally restrained performance, photorealistic concept-art finish suitable as a color-and-light target for production.
>
> No text, captions, subtitles, interface words, logos, watermark, split screen, comic border, extra hands, or extra characters.

最终连续性修订提示词：

> Use case: precise continuity correction to a finished cinematic frame.
>
> Edit the supplied single 16:9 image. Preserve the exact composition, Ruan Xing’s face and costume, the awakened younger brother in the cyan life-support pod, the console, the inserted copper memory key, the grounded realistic science-fiction materials, depth of field, and warm-gold versus cool-cyan lighting. Do not restyle or crop.
>
> Correct only the decision gesture so the story still reads as unresolved: raise Ruan Xing’s entire gloved right hand several centimeters above the console. Show a clear band of empty air between every fingertip/palm and the console surface. Center her palm precisely over the neutral divider midway between the warm-gold control on the left and the cool-cyan control on the right. The hand must not overlap, touch, point directly at, or favor either control. Both physical controls remain unpressed and at equal height. Keep the brother awake and looking toward her.
>
> No text, captions, subtitles, UI words, logos, watermark, extra fingers, extra hands, pressed button, drone, mother hologram, or new character.
