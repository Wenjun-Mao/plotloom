# Creator-facing wording audit — 2026-09-26

Status: source-backed audit and proposed copy; not an implemented UI change.
Requested during the 雨停以后 manual walkthrough. Preserve the running page,
unsaved branch form and all creative decisions. No provider calls are needed.

## Diagnosis and scope

The recurring issue is implementation vocabulary escaping into creator UI,
not simply poor translation. Handlers distinguish preparation, dispatch,
technical validation, saving, creative confirmation and applying content;
labels often obscure those distinctions. Fix copy in its owning UI component,
with tests against the actual action. Do not rename schemas or loosen guards.

Source scan covered creator pages, workspace/navigation/settings, media panels,
video preparation/review, playback, advanced graph/run tools, and API error
examples. Focused handler inspection covered source/branch, script and review
actions. This is not an exhaustive rendered-state or Safari audit; dynamically
returned errors and generated upstream reports need separate runtime coverage.

## Wording rules proposed for adoption

- Use verb + creator-visible object: 保存故事分支, 确认使用此剧本.
- 保存 persists edits; 确认使用 adopts reviewed content; 应用 changes the
  downstream working structure. Never collapse these into one generic 确认.
- 准备任务, 复制任务 and 发送任务 are different actions. Only say 生成 when
  the action actually starts generation, not when it creates a manual brief.
- Use 已确认 for creative adoption, 已选用 for a selected media asset, and
  检查通过 for technical validation. Neither validation nor queued dispatch
  means creative acceptance or usable playback.
- Prefer 待审阅 / 已确认 / 需要重新检查 over raw ready / accepted / stale.
  Explain what changed and the next action; retain exact codes in details.
- Keep API, JSON, IDs, hashes, revision bindings, provider/model names and
  diagnostic vocabulary available in technical details. Do not globally
  replace domain identifiers or original user/generated content.
- Remove 显式 from ordinary instructions; the deliberate button action and
  clear consequences already express the requirement.
- Preserve deletion, replacement, unsaved-work and uncertain-dispatch warnings.
  Shorter copy must not hide effects or encourage duplicate submissions.

## Findings and proposed replacements

Paths below are relative to `frontend/src/`. P1 = action/comprehension risk;
P2 = readability/consistency. All rows remain open unless noted otherwise.

| Priority / owner | Current example | Proposed creator wording / required distinction |
| --- | --- | --- |
| P1 `pages/SectionMapPanel.tsx` | 保存明确分支映射 | **保存故事分支** (user agreed); helper: 保存章节、选项和对应结局，不会自动生成剧本或视频。 |
| P1 same | 安装到规范路由图 / 重新安装路由图 | 应用到故事路线 / 更新故事路线; explain that this creates/updates the working route graph, and show replacement effects before action. Saving and applying remain distinct. |
| P2 same | 分支章节映射 / 唯一明确选择 / 选择标签 / 后果 / 抵达结局 | 故事分支 / 观众选择 / 选项文字 / 选择后的发展 / 对应结局. Show 当前支持一个选择、两个结局. |
| P2 same | 稳定章节 ID / 结局 0 | Move IDs to technical details in a separately scoped layout change; display endings from 1 or A, not 0. Do not change stored IDs. |
| P1 `pages/SourceOutlinePage.tsx`, `pages/BriefPage.tsx`, navigation | 来源与大纲 / 来源正文或 treatment / 已接受的来源 | Proposed: 故事与大纲 / 故事内容 / 已确认的改编内容. Keep 原作来源 for actual provenance. Coordinate navigation and Brief destinations, not a global 来源 replacement. |
| P2 source, cast, art, script | 已接受 / 尚未接受 / 候选 | 已确认 / 尚未确认; use 待审阅大纲、待审阅剧本 for the object. 候选图片 remains useful when comparing alternatives. |
| P1 source/art/script/storyboard review | 准备 specialist handoff / 刷新 specialist delivery / 取消 handoff | 准备大纲任务 (or named stage) / 检查任务结果 / 取消此任务. Say where to execute manual tasks and that preparation does not dispatch them. |
| P1 `pages/ScriptPanel.tsx`, `pages/StoryboardReviewPanel.tsx` | 准备并复制 … handoff | Handler inspection: prepare sets displayed assignment without copying. Use 准备剧本任务 / 准备分镜任务 unless clipboard behavior is separately implemented and verified. |
| P1 `pages/ScriptPanel.tsx` | 重新复制冻结 handoff | Recovery handler returns data through generic run without setting assignment or clipboard. Record as behavior mismatch; merely renaming to 复制 is insufficient. Verify/fix task recovery separately. |
| P1 `pages/ScriptPanel.tsx` | 显式接受完整 pilot 剧本 | 确认使用此剧本; explain that it confirms all three chapters, not just the displayed one. |
| P1 `pages/StoryboardReviewPanel.tsx` | 显式接受 review revision | 确认此分镜评审方案; this confirms review evidence, not production shots, media or later production storyboard approval. |
| P2 `pages/CastPanel.tsx`, `pages/ArtPanel.tsx` | 接受这份角色设定 / 显式接受此美术提案 / 保存重新打开的角色 | 确认使用角色设定 / 确认使用美术设定 / 保存角色修改. |
| P1 `pages/CastPanel.tsx` | 创建新角色提案 | 准备角色设定任务: current helper explicitly says it only prepares a manual task. Do not imply a proposal already exists. |
| P1 `pages/ScriptPanel.tsx` explanatory paragraphs | pilot / seam / episode / hook/cliff / aggregate duration | Lead with: 根据已确认的故事分支编写开场和两个结局；每次观看只经过其中一个结局。 Put upstream-format caveats in technical details; preserve route-duration limits. |
| P1 `pages/ProductionBridgePanel.tsx` | 准备投产提案 / 保存戏剧意图整包 / 确认投产提案 | Proposed: 准备镜头制作方案 / 保存镜头意图 / 确认并应用制作方案. Verify installed objects and replacement effects; explicitly state whether generation starts (do not imply it does). |
| P2 media image-job/reference panels | Send to specialist / 检查 delivery / Approval / primary / complementary | 发送图片任务 / 检查生成结果 / 分镜审核 / 主参考 / 辅助参考. Describe manual-copy vs actual dispatch accurately for each path. |
| P2 `features/media/keyframes/KeyframeAndPreviewPanel.tsx` | 创建连续 still animatic / 冻结预览历史 | 创建关键帧预览 / 已保存的预览; explain this is still-image sequencing, not generated video. |
| P1 `video-pilot.tsx`, `h3-directions-review.tsx` | 冻结此说明并准备原片 / 生成另一候选（冻结当前审核关键帧） | UI handler calls prepareVideoJob; submitVideoJob has a separate 提交一次 button. Proposed: 确认说明并准备视频任务 / 准备新视频任务; submit: 提交视频生成. Keep input version locking in helper/details and verify API semantics before implementation. |
| P1 `features/media/ShotPreparationSummary.tsx` | 当前播放片段合同 / 当前性 / 已安装 F5 来源 | State which shot/reference changed and what the creator must review. The six-second-specific explanation needs contract review, not cosmetic simplification. |
| P1 `app/workspace/WorkspaceViews.tsx` draft dialog | CAS 回执 / 规范保存 / 当前标签页草稿 | Explain which edits are saved/discarded and where the user returns. Preserve distinct close-project vs navigation semantics. |
| P2 same settings | 供应商 Profile 与会话 Key / 设为活动 | 模型服务设置 / 设为当前配置; API 密钥 is appropriate. Keep adapters/protocol options in advanced settings. |
| P2 advanced `TracePage`, `QuarantinePage`, graph tools | work unit / sibling / 合同 / required gate | 子任务 / 同批已完成任务 / 数据规则 / 必需检查 in summaries; exact technical terms may remain in expanded diagnostics. |
| P1 API error presentation | Load failed / raw English detail / status code alone | Explain failure and safe next action; retain code/details. Never suggest retrying uncertain generation without checking job state. Requires error-code mapping, not text replacement alone. |
| P2 upstream report | 集 / 爽点 / 雨戏 / unexplained colored blocks | Report-specific issue already recorded in walkthrough notes. Do not rewrite immutable delivery HTML. Provide accurate legend/context or update future report templates under their own contract. |

## Delivery order and verification

1. Next scoped copy pass: source, branch-map and manual-task screens (the
   current walkthrough and its immediate next steps). No automatic generation,
   branch redesign or schema changes.
2. Character/art/script/storyboard consistency; distinguish review-plan
   confirmation from production approval and media selection.
3. Media preparation, playback blockers, settings and recovery/error messages.
   Resolve action mismatches before promising corrected behavior.
4. Future generated reports: legends and story-format-aware terminology.

For each implementation slice, inspect handler effects, update accessible
names and tests, build checked static, and test prepare/copy/send separately.
Cover empty, pending, ready, confirmed, changed-input, error and destructive
states. Review Chinese in context and manually check Safari on representative
screens. A keyword scan cannot certify all copy as natural or all actions as
correct. No blanket translation replacement is proposed.

Current evidence: source inspection and screenshot-backed walkthrough findings;
no runtime changes, browser replay or product acceptance claimed by this audit.

Independent GPT-5.6 Terra review verified the prepare and script-recovery
findings. Its wording findings are incorporated above: name the destination
of branch application and avoid implying production approval for review-only
storyboards. Storyboard task recovery, unlike script recovery, restores the
assignment and attempts clipboard copying. Its current swallowed clipboard
failure must not be reported as successful copying. Displayed task text should
be labelled 完整任务（可复制）; only show 已复制 after clipboard success.

## First implementation slice — completed 2026-09-26

The status above describes the initial audit. This bounded follow-up implements
source form/status and outline task labels, branch save/apply labels and the
one-choice/two-ending explanation, script and storyboard-review task labels,
and explicit manual copying. Script recovery now restores its assignment;
storyboard recovery no longer silently attempts clipboard copying. Both offer
a separate copy button, successful-copy feedback only after resolution, and
selectable text on failure. Task UI is restricted to prepared candidates and
scoped to project/job/assignment so late results cannot mark a new task copied.
Script confirmation explains that it covers opening and both endings;
storyboard confirmation remains review-only. Save/apply and API guards remain
unchanged. The wording guide is now in
[creator UI wording](../operations/creator-ui-wording.md).

Still open: navigation/Brief “来源与大纲” naming, cast/art/media/settings copy,
general error messages, generated reports, and other detailed audit rows not
named above. This is not a project-wide completion claim.

Verification: app and E2E typechecks; 229 unit tests; deterministic frontend
build; independent GPT-5.6 Terra review with no blocking findings. Browser
coverage totals 14 unique passing journeys: six manual-entry, one branch
save/apply/restart, six storyboard-review and one script acceptance/edit/restart.
The first storyboard run was interrupted after identifying obsolete test
navigation to a hidden panel; tests now target the actual review route. The
13-case rerun passed 12 and exposed one old source-status assertion; that
assertion was updated and its focused rerun passed alongside the script test.
No persistence/validation assertions were removed. Earlier failure artifacts
remain in ignored test output. Build retains the existing large-chunk warning.

No full browser-suite or Safari replay performed. No live creator project,
unsaved browser form, backend service, provider job or creative selection was
modified by this slice. Shipped static assets were rebuilt; the already-open
page remains on its loaded version until the user safely reloads.
