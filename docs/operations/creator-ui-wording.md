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
