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

1. Trace the handler: what is saved, confirmed, applied, copied or dispatched?
2. Check empty, busy, success, changed-input and failure states.
3. Does the user know what happens next without an assistant explaining it?
4. Keep labels consistent across navigation, buttons and accessible names.
5. Update tests without removing behavioral assertions. Copy failure and late
   responses must not claim success or affect another project/task.
6. Rebuild shipped assets and inspect representative rendered screens;
   source searches alone do not establish visual or usability acceptance.
