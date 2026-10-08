# Creator UI wording

Use this guide when writing Plotloom's Chinese creator interface. The
[2026-09-26 audit](../verification/2026-09-26-creator-wording-audit.md) records
the examples and open cleanup work. This guide does not rename stored data,
change approval requirements or prescribe the wording of creative content.

## Name the action, not the implementation

| Intent | Preferred wording | Boundary |
| --- | --- | --- |
| Persist edits | 保存 + object | Does not imply acceptance, application or generation. |
| Adopt reviewed creative content | 确认使用 + object | State whether the whole document or one part is confirmed. |
| Adopt review-only evidence | 确认 + named 评审方案 | Not production approval or media acceptance. |
| Apply to a downstream structure | 应用到 + destination | Explain replacements and affected content. |
| Create a manual assignment | 准备 + object + 任务 | Does not send, copy or execute it. |
| Write task text to clipboard | 复制完整任务 | Show success only after clipboard success; offer manual copy on failure. |
| Dispatch | 发送任务 / 提交视频生成 | May start work; preserve uncertain-dispatch safety. |
| Check an existing result | 检查任务结果 | Must not imply another submission. |
| Select media | 选用 + object | Not merely technical validation. |

Prefer 待审阅, 已确认, 已选用 and 检查通过 for their respective states.
When inputs change, explain what changed and what needs reviewing. Do not
translate every `accepted` status as 已确认: a delivery accepted by a validator
is not a creative decision.

## Progressive detail

Avoid 显式, 规范 Graph, handoff, delivery, seam, receipt and CAS in ordinary
instructions. Put exact IDs, version bindings, hashes and diagnostic codes
in technical details where they remain available for troubleshooting.
API and JSON are appropriate in developer settings; provider/model names need
not be translated. Keep original author text and immutable reports intact.

Write a short verb-and-object button. Use adjacent help for prerequisites,
effects and limitations, rather than a paragraph in the button. Preserve
warnings about deletion, replacement, unsaved edits and unknown outcomes.
Do not hide unsupported workflows behind inviting but inaccurate wording.

## Review checklist

Character design review presents **性格与气质** from `persona.personality`
(individual editable traits) and `persona.temperament` (气质与举止), alongside
appearance and voice. Story motivation is a different concept: preserve
`persona.motivation` in the cast payload, but do not relabel it as personality
or use it as a fallback. Missing design fields stay empty; inferred details
retain their annotations. Character names are prominent card headings, not
technical metadata.

For character review, explicit trailing inference markers appear in expandable
“查看推断说明”; the editor preserves the original qualifier when saving edits.
Do not rewrite free-form qualifications or claim unmarked traits are verified.
See [ADR 0089](../adr/0089-cast-review-text-presentation.md). Labels must remain
selectable while ordinary clicks still focus their associated controls.

New character tasks follow [ADR 0090](../adr/0090-cast-description-and-notes.md):
descriptions describe the character; **设定依据与补充说明** records which details
are source-backed, inferred or proposed; **表演提示** records scene-specific acting
guidance. Neither note field implies acceptance. Do not silently rewrite old
candidate prose to fit this distinction.

Required fields use `*` beside the label; optional fields have no marker. Put
“带 * 的为必填项，其余可留空。” near the beginning of the form. Markers must match
actual submit validation, not recommendations or generation-schema key presence.
Use native required semantics and adjacent error explanations when a field is
mandatory; explain conditional requirements where they apply. Do not introduce
new requirements as a copy-only change. Under
[ADR 0091](../adr/0091-minimum-character-design.md), character confirmation
requires at least one nonblank personality trait and a nonblank appearance.
Mark the trait group and appearance with `*`; temperament, voice direction and
note content remain optional. Show adjacent errors and block confirmation until
the design is complete. This supersedes the earlier all-optional character note.

For adjacent actions, place each explanation beside its own button, not in
shared fine print. Choose one primary action for the current state. A completed
step should state what is ready and offer a clear next destination; it must not
silently save, apply or generate content. See the bounded
[branch flow decision](../adr/0087-branch-save-apply-continue.md).

1. Trace the handler: what is saved, confirmed, applied, copied or dispatched?
2. Check empty, busy, success, changed-input and failure states.
3. Does the user know what happens next without an assistant explaining it?
4. Keep labels consistent across navigation, buttons and accessible names.
5. Update tests without removing behavioral assertions. Copy failure and late
   responses must not claim success or affect another project/task.
6. Rebuild shipped assets and inspect representative rendered screens;
   source searches alone do not establish visual or usability acceptance.

## Whole-product visual and text pass

Run [E22.1–E22.7](../creative-workflow/graph-workbench-acceptance.md#e22-全产品视觉与文案专门检查)
after major UI iterations, adapting the view/state matrix to the actual run.
Include awkward translations, unexplained implementation terms, mixed-language
primary guidance and labels that imply a different action. Follow the handler,
not the API field name: a manually confirmed Cast design can say 已确认, whereas
validator acceptance or an ingested delivery must not imply creator approval.

Separate saved draft, confirmed content, applied story routes and selected media.
Preparing a preview from an original video is not a new video-generation request.
Keep exact codes, IDs, contracts and original creative/report text available;
do not rewrite those as a cosmetic cleanup. Use natural guidance for the primary
title, explanation and next action, including in Professional views.

Record a rendered before/after, action-semantic check and regression result for
each fix. A loading screen or captured screenshot alone is not a visual PASS:
wait for the intended content, inspect actual viewport pixels and scroll it.
Use the supported desktop matrix only (1280×768,1280×460,1700×900).

Help belongs in a field's accessible description, not its control name. Workspace
dialogs must actually paint above sticky surfaces: bounds and `isVisible` alone
are not enough. Recovery links identify the story position as well as retaining
the exact shot target; identical creative descriptions must not make separate
actions indistinguishable. “查看” actions must reveal their owning disclosure,
not just scroll to hidden content; share that behavior with deep links without
generation or selection writes. See [ADR0132](../adr/0132-creator-ui-reading-boundaries.md).

Unknown media reads are not empty collections. Say 正在读取镜头视频状态 while
loading; on an initial failure offer a named read-only retry. Only a successful
owned read may say 当前镜头尚无冻结的视频请求. Keep unbounded Brief form columns
in document flow so their lower help and controls remain reachable on short desktops.

A successful playback read with missing production stages says 故事尚未准备好,
names the missing content and links to its preparation owner. It is not a failed
request and does not offer a transport retry. Optional new Art candidates are
labelled separately from the confirmed revision. Generic service failures use a
Chinese fallback with the HTTP status; explicit server messages and raw evidence
remain unchanged. Directory times use Chinese 24-hour display with the original
timestamp retained. Scene-card layout must not style text-only action buttons.

The Brief help dock intentionally reserves space to avoid shifting later fields
when help opens. Settings-dialog captures must include both its initial body and
scrolled lower fields; a body scrolled to image settings is not missing text settings.

Reader prerequisites name their preparation owner instead of suggesting that
reloading creates missing content. An optional Storyboard read failure keeps the
current Script/route available and offers only a Storyboard read retry. Gallery
read failure, no images and no selected reference are different facts; headings
and badges must agree. Archived guidance must not invite a disabled prepare/send
or selection action. Known content and local inputs remain visible after a failed
refresh, without claiming they authorize current edits. Cast cancellation explains
that restoring confirmed status depends on unchanged story/route bindings.
Bible locations are 地点设定, not scene beats; unnamed cards identify their type.

Run, subtask and attempt outcomes are distinct. Display Chinese state labels,
keep exact codes and original attempt data in the event details, and present an
unknown request result as uncertain even when its persisted attempt is failed.
Pending cancellation says 已请求取消，等待运行结束; the server-authorized re-signal
action is 再次请求取消. No execution record means 执行来源未记录, not 首次执行.
Status and failure explanations must not compete for one cramped flex row.
The zero-event progress helper must not invite selecting an event that does not
exist. Pending events use an in-progress label and accent tone, not success green.
For an unknown result, explain that a full rebuild can submit fresh requests and
duplicate work; checking the original result is not merely an exact-repair concern.
