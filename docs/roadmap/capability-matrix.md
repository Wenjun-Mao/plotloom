# Plotloom · 叙织能力吸收与完成度矩阵

> **用途：**这是 Plotloom “从两个来源学到了什么、决定怎么处理、现在完成到哪一层、下一项证据是什么”的唯一进度总表。
>
> **快照日期：**2026-09-11。产品结论以固定版本为基线，不随远端分支漂移。
>
> **决策依据：**能力追踪采用 [ADR 0008](../adr/0008-capability-based-adoption-tracking.md)，当前独立仓库与身份边界采用 [ADR 0010](../adr/0010-plotloom-clean-repository.md)，运行与生产边界采用 [ADR 0011](../adr/0011-provider-profiles-and-generation-work-units.md)、[ADR 0012](../adr/0012-approved-storyboards-and-production-units.md)、[ADR 0013](../adr/0013-model-neutral-reliable-generation.md)、[ADR 0014](../adr/0014-project-lifecycle-and-workbench.md)、[ADR 0015](../adr/0015-exact-work-unit-repair.md)、[ADR 0016](../adr/0016-versioned-authoring-quality-gates-and-approval.md)、[ADR 0017](../adr/0017-alpha-validation-and-correction-boundaries.md)、[ADR 0018](../adr/0018-trusted-story-timing-allocation.md) 和 [ADR 0019](../adr/0019-exact-fragment-and-join-state-contracts.md)。ADR 0003–0007 保留了重建阶段的历史架构证据。

> **Next execution (2026-09-10):** the join correction, usable `default` storyboard canary, explicit adapter/V3 snapshot boundary, two-plane readiness UI, and definite-failure admission guard are integrated locally through `96de4e3`. A one-shot non-generative live probe verified `qwen3527b` through `openai_compatible@1`; the user asked to defer another interactive trial. [ADR 0024](../adr/0024-pluggable-text-backends-and-independent-qualification.md) still requires the supported backend to pass 9/9 runs, at least 30/36 first-pass stages and three blinded reviews, plus core/CI gates for Alpha. vLLM remains deferred; old 18-run/six-review evidence is not relabelled. See the [completion plan](m1c-completion-plan.md) and [readiness receipt](../verification/2026-09-10-provider-readiness-offline-candidate.md). [ADR 0023](../adr/0023-bounded-delivery-and-evidence.md) continues to govern bounded delivery.

## 一眼看懂当前状态

**Next product direction (amended 2026-09-11):** [Story to playable Alpha](story-to-playable-alpha.md)
records the agreed cinematic-realism, proposal/refinement, imported-reference,
native-audio and in-app pause-and-choose direction. P0 and the bounded P1 manual
Codex-image-job workflow are integrated on pushed `main` through `05f73b6`.
[P1.5 character references and cross-shot identity](p15-character-reference-consistency-plan.md)
is implemented as an incomplete checkpoint through `09f0397` on local main;
[director-review corrections](../verification/2026-09-12-p15-director-review.md)
remain before acceptance/video. Flow recovery is suspended pending its replacement;
the next work starts clean from main. P2–P4 remain planned. ADR 0026
now authorizes the non-generative imported/still-preview boundary as a design;
the [P0 implementation plan](p0-imported-still-preview-plan.md) revision 2 is
Approved and implemented as a locally verified correction candidate.
No M1-C qualification gate or provider-production hard stop is waived.

**P0 checkpoint (2026-09-11):** managed JPEG/PNG imports with configured
decode bounds and lifecycle admission, independent provenance, exact
intent-revision reviewed bindings, immutable contiguous still previews, and
derived current/stale/revoked/missing/corrupt states are implemented under
[ADR 0027](../adr/0027-managed-imported-still-preview-contract.md). The four
image/three shot scenario is acceptance evidence rather than a product limit;
unrelated selections do not stale a preview. A real file-SQLite browser journey
now covers import/compare/intent/select/play/seek/reload/restart/replacement,
reapproval blocking and media-bearing delete refusal. This remains a
non-generative local preview only; provider-production hard stops are unchanged.

**P1 checkpoint (2026-09-11):** a narrowly scoped, same-host manual exchange
binds an approved single-shot `ProductionUnit`/frozen snapshot to an opaque
Codex image job, confined package/reference files, and an untrusted versioned
delivery manifest. The initial pilot observed one original and one
reference-based refinement, but its copied refinement brief was not wholly
self-contained. The correction freezes creator direction, resolved shot context
and selected intent revision; a real FastAPI/file-SQLite browser regression uses
retained assets to prove Copy/Refresh and post-Copy invalidation without claiming
a new generation. Candidate publication remains hash-validated, idempotent and
explicit-review-only. **P1 and its brief/usability corrections are accepted and
integrated through `05f73b6`; cross-shot identity is not yet implemented or
qualified.** This does not revive
legacy `MediaTask` provider dispatch, expose credentials, or qualify external
image/video providers. See the [initial receipt](../verification/2026-09-11-p1-codex-image-jobs.md)
and [correction receipt](../verification/2026-09-11-p1-self-contained-brief-correction.md).

| 观察面 | 当前判断 | 它真正说明什么 |
|---|---:|---|
| 规范领域与“输入 → 分镜”后端核心 | **约 97%** | 稳定 ID、四阶段 V2 合同、确定性 DAG 骨架、结构化对白/声音/实体状态、确定性时间线、版本化 Gate/Approval、内容绑定、命名 profile、显式有限纠错、领域分片、精确 work-unit repair、封存聚合和原子安装均已实现。M1 剩余出口主要是真实创作质量验收；P1 已有单镜头受控 `ProductionUnit`/Snapshot，广义多媒体生产层仍属 M2。 |
| 可供创作者连续使用的本地 Alpha | **约 92%（M1-B1 本地完成）** | 四阶段的当前 V2 字段已有类型化编辑、稳定 ID 增删重排、显式关系迁移、字段级 issue 定位、项目目录/草稿/URL/生命周期、逐 unit 进度、冻结 Profile Key gate、精确修复和 Gate/Approval；完整本地 checkpoint、真实 FastAPI 旅程和一条可编辑、刷新后持久的真实 llama 分镜已通过。显式 adapter/V3 snapshot 与两平面 readiness/admission 已实现；M1-C 当前出口是受支持 backend 的独立 9-run/3-review 验收与新远端 CI。 |
| 可独立发布的新仓库产品 | **约 65–70%** | Plotloom 已进入全新仓库，独立依赖、wheel、生产 UI、边界门和远端 CI 已建立；本地 E2E 竞态已修复，仍缺新远端收据、干净机器升级/恢复与图像/视频真实供应商 smoke。 |

这些百分比是路线规划估计，不是测试覆盖率，也不能相加。可复核的当前基线是：

- 已盘点 **35 项能力**：2 项达到 L6 真实运行验收，4 项达到 L5 本地产品/浏览器验证，16 项达到 L4 自动验证，3 项停在 L3 实现层，4 项已到 L2 合同层，1 项只有 L1 决策，5 项是明确的 Defer/Reject；是否完成仍取决于该行目标是 L4、L5、L6 还是 L7；
- `uv run pytest -q`：provider-readiness 最终候选为 **524 passed / 9 skipped / 272 warnings**，无 deselection 或 waiver；
- `npm --prefix frontend test`：**115 passed**；
- M1-B1 已通过完整编辑器/应用 suite，以及真实 FastAPI、公开 HTTP fake-provider 的精确 repair → 原子安装 → Approval → 刷新旅程；加载态、URL hydrate 竞态、SceneBeat 下游引用披露和 secret-free `422` 都有回归；
- Plotloom TypeScript、E2E TypeScript、Vite 生产构建与 wheel 安装 smoke 通过；
- 浏览器回归现有 **23/23 个场景通过**：首次保存、命名 profile/session key、受信任 adapter 选择、两平面 readiness、项目生命周期与导航、四阶段编辑、结构删除影响、冻结 profile 恢复、精确 repair、Approval 和刷新 lineage 均通过。测试连接真实 FastAPI；自动生成旅程只联系进程内公开 HTTP fake-provider。最新远端收据仍待 M1-C 统一推送后取得；
- 经用户授权的[隔离 live smoke 收据](../verification/2026-09-02-local-text-smoke.md)使用服务公布的 `gemma4`：127.4 秒完成 6 次调用/6 个 work units，四阶段全部封存并一次安装，零验证失败；`.env` 中的配置名仍是未被服务公布的 `gemma-4-26B-A4B-it-Q4_K_M.gguf`，需另行对齐，且该收据不代表 Qwen、图像或视频已验收；
- [M1.5 严格验收收据](../verification/2026-09-03-m15-conformance.jsonl)记录两个已保存真实 profile 各 3 次固定中文 Brief：6/6 run 原子成功，双方均为 12/12 阶段首次通过、最大 attempt 1、零 issue 与零 unknown outcome；profile、workload、run 与 topology 均以 hash/稳定 ID 存证，不保存 endpoint、模型名、IP、prompt、response 或密钥；
- Plotloom-only wheel、模板、迁移树、静态 UI 与禁止 V1 依赖的提取演练包含在上述 Python gate 中；
- [远端 CI run 33671097019](https://github.com/Wenjun-Mao/plotloom/actions/runs/33671097019) 已在 `3bf4551` 成功完成前端、Python、wheel、安装 smoke 和浏览器步骤；
- **当前发布阻断：**完成至少一个受支持 backend 的 9-run/3-review 验收，补新远端无 flaky 收据，以及干净机器安装/升级/恢复。ADR 0024 的当前 adapter/readiness/admission 模块已落地，但单次 live probe 和单次 usable canary 都不等于正式资格。旧双 backend 验收不再是主机可用性的共同前置条件；尚无新的合格收据。图片/视频生产已按 ADR 0016 硬停，必须等 M2 的 ProductionSnapshot/ProductionUnit 合同完成后再做真实供应商 smoke；当前独立仓库仍不是发布候选。

## 比较对象和证据边界

| 对象 | 固定版本 | 本矩阵能使用的证据 | 许可证/限制 |
|---|---|---|---|
| Narrative Forge 本地比较基线 | `24c3c47a6fb1e3fcd5a060d705f11bbffb9dbde9` | 本地源码、测试、样本和已有运行审计；比公开 fork 多本地端口选择修订 | Apache-2.0；当前未提交的 `backend/media_service.py` 等 WIP 不属于固定证据，不能计入能力或来源归属 |
| Narrative Forge 用户 fork | [`6b4972f`](https://github.com/Wenjun-Mao/Narrative-Forge/tree/6b4972f2b4d826c5944b7625bf95f447236532c4) | 公开 fork 冻结基线 | Apache-2.0 |
| Narrative Forge 原上游 | [`abebc29`](https://github.com/Zafer-Liu/Narrative-Forge/tree/abebc29fd98ff8c9153f8b566c85c7a0e7b1e7a9) | 原项目设计和实现归属 | Apache-2.0 |
| shuohao-skills | [`4322897`](https://github.com/eternityspring/shuohao-skills/tree/4322897e6d2bdaf66365534fd40194360c75a85f) | 干净本地副本 `/Users/wjmao/projects/HU/reference-repos/shuohao-skills` 的静态源码、schema、SKILL、selftest 与迁移说明；未安装、未运行其脚本 | Apache-2.0；NOTICE 归属必须保留；私有 shot-recipes 未取得、未审计、未计入完成度 |

两个远端 HEAD 已于 2026-09-02 复核，仍等于表中的上游冻结提交。Plotloom 本身的初始提取来源另见[提取 provenance](../provenance/initial-extraction.md)，不能和参考仓版本混为一谈。完整证据规则见[来源与冻结版本](../storyboard-handbook/SOURCES.md)，许可证与私有材料边界见[第三方声明](../storyboard-handbook/THIRD_PARTY_NOTICES.md)。本矩阵主要吸收**问题定义、用户价值与合同思想**；“Adopt/Adapt/Rebuild”不代表复制了第三方代码。若以后直接复用可版权化实现或素材，必须单独记录来源、修改和 NOTICE 处理。

## 决策词和成熟度

### 来源处理决定

| 决定 | 含义 |
|---|---|
| **Adopt（采用）** | 保留该用户结果或方法，仍由 Plotloom 自己拥有合同与实现。 |
| **Adapt（改造）** | 保留意图，但改变数据模型、身份、边界或交付形式。 |
| **Rebuild（重建）** | 同一需求值得保留，但必须在 Plotloom 的规范模型上重新实现。 |
| **Defer（延后）** | 有价值，但不属于当前首发路径；写明重新开启条件。 |
| **Reject（拒绝）** | 明确不继承；这也是一种完成的架构决定。 |

### 成熟度证据梯

| 等级 | 所需证据 |
|---|---|
| **L0** | 尚未分析或没有决定。 |
| **L1** | 决定和范围已记录。 |
| **L2** | Plotloom 合同、schema、端口或验收规则已定义。 |
| **L3** | 实现存在，但尚未达到所需验证。 |
| **L4** | 自动化测试通过；涉及模型/媒体时只证明 fake/fixture 路径。 |
| **L5** | 真实浏览器连接真实本地 FastAPI 的用户旅程通过。 |
| **L6** | 经明确授权的真实供应商小额 smoke 通过并留存脱敏收据。 |
| **L7** | 已进入干净的新仓库，CI、打包、安装、恢复和发行门全部通过。 |
| **D** | 按记录范围延后；不计作当前缺陷，也不计作已实现。 |
| **R** | 按记录范围明确拒绝，并有防回归边界。 |

`L4/L4` 表示已达到该能力的目标；`L4/L6` 表示实现和替身测试已完成，但还缺浏览器与真实供应商证明。等级不是线性百分比，每项的目标由风险决定。

## 统一能力矩阵

### A. 创作输入与规范领域

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| A01 | 项目简报与生成边界 | 表单直接表达片名、梗概、类型、画幅、视觉风格和生成规模，反馈短 | 从原文、集数、时长、题材和改编幅度开始，强调保留/删改取舍 | **Adapt** 两者输入，统一成严格 `ProjectBrief` | **L5/L5** | 合同与校验在 [`domain.py`](../../src/plotloom/domain.py)；stage-first 创建、hydrate 与刷新恢复稳定通过。Brief-first E2E 已改为等待 PATCH 成功响应，本地连续 30 次通过；最新远端收据仍是修复前 flaky，等待新 CI 收据。 |
| A02 | 项目生命周期与工作区 | 本地项目保存、恢复快照、服务器备份和项目内素材形成连续工作区 | 独立工作目录和 JSON 便于审阅、Git diff 与交接 | **Rebuild** 为 Plotloom 项目服务 | **L5/L5** | [ADR 0014](../adr/0014-project-lifecycle-and-workbench.md) 固定并实现 active/archive 独立 lifecycle revision、跨进程原子 busy guard、安全永久删除、连续 READY 前缀 duplicate、显式保存与 sessionStorage 草稿恢复、URL/epoch 隔离及原创三栏工作台。真实 FastAPI 浏览器旅程覆盖 list/create/switch/archive/restore/delete/duplicate、草稿恢复、历史导航和 delayed-response 隔离。 |
| A03 | 故事圣经、角色、地点、道具 | 角色卡和场景卡贴近媒体生成工作台 | cast/art 分开建立 C/S/P 资产和视觉、声音、连续性规格 | **Adapt** 为稳定 ID 的 `StoryBible` | **L4/L5** | 当前 M1-B1 工作树的 [`StoryBiblePage.tsx`](../../frontend/src/pages/StoryBiblePage.tsx) 已编辑角色、地点、道具、traits、事实、问题、来源、状态和视觉/声音锚点；删除先呈现下游影响，`issues[].path` 可定位字段。focused editor tests 已通过；退出条件是完整 checkpoint gate。 |
| A04 | 互动剧情图、选择、汇流与结局 | `choices`/`next` 和播放器证明互动路线的产品价值 | 五阶段流程没有互动图，可作为明确反例边界 | **Rebuild** 为可达 DAG、state effects 和 join contracts | **L4/L5** | 当前 [`GraphPage.tsx`](../../frontend/src/pages/GraphPage.tsx) 支持节点、边与汇流合同的增删和字段编辑；边重连、节点 kind 改动及删除先说明影响，稳定 ID 不因编辑丢失。ID/数组路径的 issue 会定位到对应实体/字段；退出条件是完整 checkpoint gate。 |
| A05 | 戏剧场次、节拍与连续性 | 暴露动作、对白、首尾状态，但 V1 的 `scene` 实际近似 shot | `script.flow` 明确保留 action/line beat、场次和时长 | **Rebuild** 为稳定 `DramaticScene` + `Beat` + `ContinuityState` | **L4/L5** | 当前 [`SceneBeatsPage.tsx`](../../frontend/src/pages/SceneBeatsPage.tsx) 支持场景、Beat、DialogueCue 的增删重排和全部当前 V2 编辑字段；`Beat.sceneId` 与 `DialogueCue.beatId` 是先显示影响再确认的稳定-ID 迁移，而不是隐藏重建。focused editor tests 已通过；退出条件是完整 checkpoint gate。 |
| A06 | 分镜、镜头与节拍覆盖 | 单镜头编辑、媒体按钮和按路线预览形成短反馈回路 | segment/cut、时长和 exact-once coverage 提供清晰生产规格 | **Adapt** 为 `Shot` + many-to-many `ShotBeatLink`；主剪可另作派生投影 | **L4/L5** | 当前 [`StoryboardPage.tsx`](../../frontend/src/pages/StoryboardPage.tsx) 支持镜头、AudioPlan、DialogueCue 调度、实体连续性状态和 `ShotBeatLink` 的编辑、增删与重排；Shot 跨场景移动明确列出 cue/link 影响并保持 ID。媒体仍是 ADR 0016 的明确占位，未伪造生产完成；退出条件是完整 checkpoint gate。 |
| A07 | 线性分集短剧 | V1 有独立 serial 模式与分集导出 | shuohao 的集/场/段/切/秒数链对线性 AI 短剧更完整 | **Defer** 为规范模型的线性投影，不成为第二套核心 | **D** | [ADR 0003](../adr/0003-v2-strangler-architecture.md) 首发只做互动项目。重新开启条件：互动 Alpha 稳定，且 episode/linear projection ADR 获批。 |
| A08 | 无 Key 教学样例与确定性 bootstrap | 本地模板无需供应商即可创建可操作草案，适合首次启动、演示和 E2E | 各阶段 deterministic seed 能复制已批准事实，但不会替 agent 创作语义 | **Adopt** 教学/测试价值，不把固定模板冒充生产生成器 | **L5/L5** | [`demo.ts`](../../frontend/src/demo.ts) 提供完整教学项目和 trace；真实浏览器已从无项目教学工作区保存完整四阶段前缀，并在刷新后恢复、呈现和继续编辑分镜。 |
| A09 | 结构化对白、声音、时间线与资产状态 | V1 的镜头表单、角色/场景卡和媒体预览证明这些信息必须在同一工作流可见，但自由字符串与可变场景对象不可保留 | script/storyboard 的 speaker、动作/台词估时、声音、连续性、角色/地点/道具状态提供生产规格 | **Adapt** 为 `DialogueCue`、`AudioPlan`、场次顺序/时间线和稳定实体状态引用 | **L4/L5** | [ADR 0016](../adr/0016-versioned-authoring-quality-gates-and-approval.md)、[ADR 0018](../adr/0018-trusted-story-timing-allocation.md) 与迁移 0010 已实现 V2-only 当前作者合同、毫秒整数时长、结构化声音/实体状态和确定性时间线。Brief 的播放时长是路径硬上限；`scene_timing_allocation.v1` 按封存 Story Graph 确定性分配 node cap，binder 从版本化语言规则派生 cue 时长并按模型相对权重分配 scene budget。Prompt、binder、手工保存验证与全局 Gate 已对齐；退出条件是 M1-C 固定故事 rubric。 |

### B. LLM Prompt、响应与可解释生成

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| B01 | 分阶段、版本化 Prompt 编译 | 当前表单到生成请求的短链路值得保留；V1 的前后端散落模板不保留 | SKILL/pass 文档把每阶段创作责任写清楚 | **Rebuild** 为包内唯一模板源、严格变量和内容哈希 | **L4/L4** | 十一个文本/媒体模板位于 [`prompt_templates/`](../../src/plotloom/prompt_templates/)，其中 Story Graph content-fill 和 correction 合同绑定冻结骨架/错误码；Scene Beats Prompt 只接收冻结 node cap 并输出相对 `durationWeight`，绝对 scene/cue timing 全由 trusted binder 派生。确定性渲染、schema 和 wheel 打包测试通过。 |
| B02 | 响应抽取、schema 与语义验证 | 安装器已有重复 key、目标和规模检查 | 每层 validator/selftest 体现“模型输出不能直接成为主数据” | **Adapt/Rebuild** 为同一条 parse → schema → semantic 链 | **L4/L4** | [`generation/responses.py`](../../src/plotloom/generation/responses.py) 与 [`generation/validation.py`](../../src/plotloom/generation/validation.py) 有严格测试；只有 `message.content` 的字符串或显式 `text`/`output_text` part 可进入抽取，reasoning/未知 part 只作原始证据，且不会从任意说明文字截取 JSON。[ADR 0017](../adr/0017-alpha-validation-and-correction-boundaries.md) 要求预期错误形成稳定 issue，且只有窄化、带 discriminator 的可信事实可以进入纠错；程序、存储、畸形事实或未知交付错误继续 fail closed。 |
| B03 | 四阶段原子流水线与 stale 传播 | V1 一键生成体验可保留，但整树响应和可变安装不可保留 | 显式阶段交接可保留，但手工重跑不可作为 runtime | **Rebuild** 为连续阶段范围、不可变 snapshot、事务安装 | **L4/L4** | [`pipeline.py`](../../src/plotloom/pipeline.py) 与 repository 测试覆盖原子四阶段提交、并发编辑和下游 stale。 |
| B04 | Revision、Prompt Inspector 与 provenance | V1 缺少“哪个输入/提示/响应生成此结果”的完整链 | 文件和 gate log 有局部来源，但没有统一 revision/hash 图 | **Rebuild** 为 Run/Attempt/Artifact/EntityRevision | **L4/L5** | 后端持久化完整 trace，前端 [`TracePage.tsx`](../../frontend/src/pages/TracePage.tsx) 可查看；下一步是浏览器 E2E 证明刷新后仍能完整追溯。 |
| B05 | 隔离、人工修复与 AI 修复血缘 | V1 失败多停在提示或宽容安装 | shuohao 门能拒绝，但批准/修复未绑定精确版本 | **Rebuild** 为 quarantine 和证据冻结的 child run | **L5/L5** | [ADR 0015](../adr/0015-exact-work-unit-repair.md) 已实现不可变 child scope、服务端资格判定、成功 sibling/upstream fragment binding、仅目标 unit 重试、重新聚合、下游重规划和全范围原子安装；stale、cross-run、unknown、cancel、restart、篡改及永久删除均有对抗测试。M1-B1 精确 repair Playwright 旅程以真实 FastAPI 与公开 HTTP fake-provider 证明：只有隔离 shard 重发、sibling hash 不变、四阶段原子安装、Approval 与刷新 lineage 均保持。完整 checkpoint 已通过。 |
| B06 | 确定性质量门与创作 eval | V1 测试覆盖运行路径，不能证明镜头好看 | 17 道门、逐门击穿 fixture 和失败统计思想很有价值 | **Adapt** 为带版本和证据的 `GateResult`；艺术质量单独人工评审 | **L4/L5** | `storyboard.v2` GateResult 由服务端从精确规范 revision 重算并与安装原子持久化，覆盖顺序、Brief 路径/node/scene 预算、对白归属/可信估时/调度、声音时间、实体引用/状态、PRIMARY/SUPPORTING coverage 及 beat/shot 连续性；required skipped 明确失败，伪造 receipt 被拒绝。编辑器能按 `issues[].path` 选择并聚焦可编辑字段；退出条件是 M1-C 固定故事 rubric。 |
| B07 | 人工批准点 | V1 的“保存/生成”是操作，不是版本化批准 | 阶段文件天然形成审阅点，但批准不绑定 revision | **Rebuild** 为精确 revision/hash 的 approval/decision；保存不等于批准 | **L5/L5** | 迁移 0010、repository 与 API 已实现不可变 approve/revoke ledger，绑定精确 storyboard revision、content hash、上游 revisions 与 gate-set；上游/head 变化自动使旧批准 stale，归档项目不可追加决定。工作台能读取 Gate/Approval、创建决定并在真实 exact-repair 浏览器旅程中刷新复核。Reviewer 当前是单机/私有 tailnet 工作台中的用户标签，不是认证身份。 |
| B08 | Provider Profile、生成计划、分片工作单元与封存聚合 | V1 有用户可见规模限制和单次调用，但取消主要只是停止前端观察 | 五阶段按文件/批次控制规模，但没有在线、可恢复的 shard lifecycle | **Rebuild** 为冻结 `ProviderProfile` 的 `GenerationPlan → StagePlan → GenerationWorkUnit → SealedStageAggregate`，显式定义超时、未知结果、纠错和取消 | **L6/L6** | 命名且 revisioned 的**文本** profile、三个版本化预设、确定性最小 Story Graph 骨架、V2-bound content-only schema/binder、fragment local alias→selector/order UUIDv5、selector-owned parent 注入、封闭 PRIMARY beat→shot 映射、显式 join continuity keys、最多两次可见 correction、response-after-crash 本地续跑、0007 稳定 run failure code 和 secret-free conformance 收据均通过自动测试。已持久化的失败 attempt 只能在其原始 base/correction 合同未变时继续纠错，部署后合同漂移会稳定地 fail closed。planner 的输入数值是 byte estimate，精确 context 由 provider tokenizer 判定；0006 已安全终止旧非终态 run 并要求重提。[严格 3×2 收据](../verification/2026-09-03-m15-conformance.jsonl)证明两个指定 profile 各 3/3、固定 `workloadHash` 下各 `sampleOrdinal` 唯一，且双方均 12/12 阶段首次通过。M1-R 进一步证明 repair child 继承冻结 profile、只重试目标 unit、复用绑定经 hash 验证且下游 seal 不跨 dependency 复用。 |

### C. Provider、媒体生产与输出

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| C01 | Provider 设置与秘密边界 | 文本/图像/视频可分别选 provider/model/base URL；服务器 key 与会话覆盖实用 | 供应商调用主要交给运行 agent，不适合作为产品秘密模型 | **Rebuild** 严格 public settings + server key/session lease | **L6/L6** | API、数据库、trace、日志、URL root 与按 profile 分区的 sessionStorage 边界均有测试；`authMode=none` 不读取/发送 key，rebuild/repair/resume 不会串用 profile key。两个当前文本 profile 已通过真实 3× conformance，receipt 只含稳定 ID/hash、状态、issue、耗时与 token；图像/视频 smoke 不属于 M1.5。 |
| C02 | 关键帧图像生成 | 多供应商、逐镜按钮、参考图和项目资产闭环 | 可选 imagegen 与 frame prompt/缺图占位体现“文本交付不被图片阻断” | **Adapt** 到冻结 ProductionSnapshot 的 manual `ImageJob` | **L6 candidate / acceptance pending (P1 manual Codex route)** | P1 has an approved one-shot ProductionUnit/Snapshot, same-host package/reference exchange, declared Codex built-in-imagegen pilot delivery, validation and explicit selection. The current candidate also freezes creator direction, resolved shot context and exact refinement intent; retained-asset browser regression verifies the correction. Legacy provider `MediaTask` execution remains blocked; M2 is required for automatic or external-provider image generation. |
| C03 | 视频生成 | V1 的 submit/poll 和逐镜视频是重要产品能力 | 不执行视频生成，反而清楚限定 storyboard 是生产规格 | **Adapt** 到同步/异步统一 adapter 和任务状态 | **L3/L6** | 异步 adapter 与历史测试规格保留，但与图片相同被 ProductionSnapshot 硬边界隔离；不存在从 raw Shot 到 provider 的临时绕路。M2 恢复条件包括冻结输入、关键帧 lineage、供应商取消/unknown 语义和播放质检。 |
| C04 | 持久任务、重启恢复与浏览器观察 | V1 能本地轮询/恢复等待，但停止观察不等于远端取消 | 没有一等在线任务/run | **Rebuild** 为数据库事实和安全 reconciliation | **L5/L5 (P1 manual route)** | Text-run guarantees remain as before. P1 stores copy/cancel/delivery/candidate history and on refresh/restart reopens delivered jobs, current candidates and stale/current previews without resubmitting a specialist task; late, revoked and cancelled delivery is retained but inapplicable. Legacy asynchronous media tasks remain safely stopped. |
| C05 | Artifact、媒体落地与内容寻址 | V1 把媒体保存进项目 assets | shuohao 把主数据、报告和投产包分层 | **Adapt/Rebuild** 为 content-addressed ArtifactStore | **L5/L5 (P1 still outputs)** | P1 validates bounded decoded JPEG/PNG bytes, stores content-addressed originals plus display derivatives, and records output/manifest hashes, prompt/tool evidence and limitations before publishing selectable candidates. Remote URI trust, video and lifecycle deletion semantics remain M2 work. |
| C06 | 互动预览与可播放导出 | 这是 V1 最应保留的优势之一：编辑后立即试玩并导出 | 不提供播放器或最终视频 | **Adopt outcome / Rebuild implementation** | **L4/L5** | P0 已有非生成式、已审核 imported-still animatic：创作者可冻结一场景的任意非空连续子集，并按 authored duration 播放、暂停、seek、刷新/重启后读取；旧 receipt 保留且会显式 current/stale/revoked/missing/corrupt。它不包含分支 session、音频、视频、最终剪辑或导出；这些仍是 L5 前置。 |
| C07 | 批量生成、最终剪辑与成片交付 | V1 有批量媒体和互动/分集导出，可作为行为参考 | export pack/manifest 适合可审阅投产交接，但不生成最终视频 | **Defer**，以后基于 Plotloom task/artifact/export contracts 重建 | **D** | 批量队列、取消、全局 timecode、配音/口型、剪辑、QC、最终成片都不计入当前完成度。 |
| C08 | 已批准分镜到 ProductionUnit 与供应商编译 | V1 的单镜生成回路反馈短，但 Shot/Prompt/Task 边界不稳定 | segment/cut/frame 与 H3 投产包说明需要独立生产层，但线性位置和供应商字符串不能成为主数据 | **Adapt/Rebuild**：从 approved Storyboard 确定性派生 provider-neutral `ProductionUnit`，再由 adapter 编译 | **L5 candidate / acceptance pending (P1 single-shot)** | P1 freezes an active Approval, exact storyboard entity/revision, one canonical Shot, creator-reviewed direction, narrow resolved context, references and hash before packaging a `codex_specialist.v1` assignment. Refinement freezes and rechecks the current reviewed VisualIntent revision; raw-Shot/browser-prompt bypasses are rejected. Multi-shot planning and general adapter compilation remain M2. |
| C09 | 资产角色、参考血缘与受控人工导入 | V1 有角色设定图、场景参考、逐镜素材和本地保存，但任意路径/URL 边界过宽 | 角色/地点/道具锚点、状态变体及小样先审提供清晰的一致性方法 | **Adapt/Rebuild** 为稳定 asset role、`ShotReferencePlan` 和内容寻址 Artifact；人工导入走受控入口 | **L4/L5** | P0 提供 project-scoped JPEG/PNG byte ingest、hash/MIME/dimension/provenance、独立 display derivative、版本化 identity/composition/style/source-ref intent，以及绑定精确 Approval 的 reviewed Shot selection；跨项目读/绑定、动画/损坏输入、归档/未找到项目 admission 和媒体项目永久删除均拒绝。仍缺角色/地点资产计划、受控下载、ProductionUnit 引用解析、媒体擦除与离线发布验收。 |

### D. 平台、工作台与独立发行

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| D01 | SQLite、迁移与并发写入 | 项目文件、原子保存和备份易理解，但缺细粒度事务 | 分层 JSON 易 diff，但依赖操作者管理一致性 | **Rebuild** 为 repository、Alembic、optimistic revision | **L4/L5** | SQLite/WAL/外键、迁移、原子 rollback、startup reconciliation 及跨 repository 并发幂等测试通过；写锁耗尽会返回带 `Retry-After` 的可控 503。仍需安装版数据恢复演练和用户可见备份/导出。 |
| D02 | React 工作台与完整用户旅程 | 浏览器内创作→媒体→预览的单一工作台是核心产品价值 | 分阶段操作和报告适合清晰导航 | **Adapt** 为七页 Plotloom 工作台 | **L5/L5**（M1-B0/M1-B1） | [ADR 0014](../adr/0014-project-lifecycle-and-workbench.md) 的项目目录、URL/epoch 导航、显式保存、sessionStorage 草稿恢复、生命周期操作和 Plotloom 原创三栏布局均已实现；M1-B1 补齐四阶段编辑、关系影响确认、issue 路径聚焦、逐 unit Inspector、冻结 profile key gate 与 Gate/Approval。真实 FastAPI exact-repair→Approval→刷新旅程及整套 checkpoint gate 均通过。 |
| D03 | Plotloom 导入、导出、备份与可移植项目 | V1 project JSON/备份能带走作品，但直接安装 JSON、标题目录和无保留策略不安全 | 五层 JSON/Markdown/manifest 便于审阅交接 | **Rebuild** Plotloom canonical 格式；**Reject** 首发 legacy migration | **L1/L5** | [初始提取来源](../provenance/initial-extraction.md) 定义 Plotloom-only 数据边界；退出条件还必须覆盖格式版本、预检、hash/manifest、冲突策略、原子导入、稳定 project ID、备份保留/清理和空 data-dir 恢复。任何 V1/shuohao 导入只能在未来另立迁移 ADR。 |
| D04 | 无 V1 依赖的提取、打包与新仓库 | V1 只作为比较和行为证据存在 | shuohao 的自包含边界提醒我们保持模块独立，但不复制其规则重复 | **Rebuild** 为单包、单 UI、可移动 roots | **L5/L7** | 全新 Plotloom 仓库、fresh history、依赖边界、独立 wheel/资源探测和生产 bundle 已建立；[远端 CI](https://github.com/Wenjun-Mao/plotloom/actions/runs/33671097019) 已成功，但应先消除浏览器 flaky，再完成干净安装/升级/卸载数据策略与恢复收据。 |
| D05 | E2E、真实供应商与创作质量验证 | V1 有浏览器/媒体/导出行为可作回归样例 | selftest 的击穿 fixture 纪律值得采用 | **Adapt** 为分层验证金字塔 | **L5/L6** | 当前候选有 531 个 Python 测试、115 个前端单元测试和 24 个真实 FastAPI 浏览器场景通过；9 个 pre-ProductionSnapshot provider-execution 规格明确冻结到 M2。单次 usable llama canary 与非生成 readiness probe 已通过，但新远端 CI 和 M1-C 三故事真实生成/独立盲评仍未完成；媒体 smoke 属于 M2。 |
| D06 | 本地安全与远程部署边界 | loopback、URL 检查、secret-free config 和“远程必须私有”警告应保留 | 不是常驻 Web 服务，不能提供可直接采用的部署边界 | **Adapt local/Tailnet boundary / Defer public multi-user** | **L4/L4**（本地/Tailnet）/ **D**（公开部署） | 已实现并测试可信 HTTP(S) root、loopback/LAN/Tailnet、URL 凭据/query/fragment/非法端口拒绝、无重定向、`authMode=none` 不发送 Authorization、session/server key 边界和禁止媒体请求级 profile 覆盖。未加外部认证的远程实例必须保持私有。 |
| D07 | 来源、许可证与可解释吸收 | 上游/fork/本地修订必须分开归属 | Apache NOTICE 和私有 shot-recipes 边界必须明确 | **Adopt** 固定版本与第三方治理 | **L4/L7** | [`SOURCES.md`](../storyboard-handbook/SOURCES.md)、[`THIRD_PARTY_NOTICES.md`](../storyboard-handbook/THIRD_PARTY_NOTICES.md)、根 `LICENSE`/`NOTICE` 已建立；新仓库发行前再做一次文件级 provenance 扫描。 |
| D08 | 可插拔 shot recipe/镜头语汇 | V1 没有独立、版本化配方合同 | 公开 repo 有 `--shots` 接口、解析器和最小 fixture；完整卡库是私有材料 | **Defer interface / Reject private content as evidence** | **D/R** | 只可将自研或明确授权的卡作为未来 adapter 输入。私有库的内容、质量和覆盖永远不计入“已吸收”。 |
| D09 | V1 runtime 导入、双写与自动 legacy migration | 保留旧应用供比较和读取现有项目 | 五层文件也只作为方法证据，不成为 Plotloom runtime | **Reject** | **R** | [ADR 0003](../adr/0003-v2-strangler-architecture.md)、dependency-boundary 测试和提取演练共同守门：不 import V1、不双写、不把旧项目静默升级为规范实体。 |

## 两个来源到底“吸收了什么”

### 从 Narrative Forge 保留

- 浏览器工作台内从编辑、逐镜媒体到预览/导出的**短反馈回路**；
- 互动选择图、路线试玩和逐镜操作的**产品形态**；
- 文本、图像、视频 provider 可分开配置及本地私有部署的**实用边界**；
- 项目素材本地化、任务状态可见和失败可恢复的**操作者体验**。

不保留：把 story node、scene、beat、shot、prompt 和 task 挤进可变 `scene` 对象；前后端散落 Prompt；模型响应直接安装；派生 Prompt 冒充规范创作字段；V1 runtime 依赖或双写。

### 从 shuohao-skills 保留

- 显式阶段合同、`seed → 创作 → validate → render/export` 和“**搬事实、留设计**”的纪律；
- 角色/地点/道具身份、场次/动作/台词节拍、分镜覆盖和时长预算的**生产规格意识**；
- 每道确定性质量门必须可击穿、主数据/评审报告/投产包分层的**可审计交接方式**；
- provider-specific 生产格式应该由确定性编译器产生，而不是靠人工复制的**编译思想**。

不保留：用 `sceneIndex` 或 `[start,end]` 数组位置充当身份；把 exact-once 强加给全部覆盖关系（Plotloom 只要求每个 Beat 有且仅有一个 `PRIMARY`，并保留多条 `SUPPORTING`）；H3 长字符串进入规范主数据；靠操作者手工重跑文件来维持 runtime；重复规则漂移；把未运行的门当作通过。

## 当前里程碑与执行顺序

### M0：独立基线（已完成）

- [x] 创建无 V1 runtime 的 Plotloom 仓库、fresh history、独立 wheel、生产 UI、LICENSE/NOTICE 和提取边界。
- [x] 修复首次 stage 保存丢失：项目与规范阶段前缀在同一事务中创建，客户端从权威响应 hydrate。
- [x] 建立 React → Vite → FastAPI → 文件 SQLite 的浏览器回归，并保留失败后草稿与同键重试保护。
- [x] 远端 CI 已在 [`3bf4551`](https://github.com/Wenjun-Mao/plotloom/actions/runs/33671097019) 完成首次成功运行。

### M1-P0：先收口运行与领域合同

- [x] 修复 Brief-first E2E 的请求/响应同步竞态：等待匹配 PATCH 的成功响应后再读 canonical stage；本地两组 `repeat-each=5` 共 30/30 场景通过，尚待新远端 CI 收据。
- [x] 实现 [ADR 0011](../adr/0011-provider-profiles-and-generation-work-units.md) 的可信 Provider Profile：HTTP(S)、loopback/LAN/Tailnet、`authMode=none|bearer`、无自动重定向、冻结能力/预算/hash、禁止请求级 endpoint 覆盖。
- [x] 实现 `GenerationPlan → StagePlan → GenerationWorkUnit → SealedStageAggregate` 核心：入队冻结有效全局上限，阶段在上游 aggregate 后冻结精确 selectors，完成领域感知分片、持久 evidence、全局验证和全阶段原子安装。
- [x] 实现失败单元的**精确** repair：冻结目标 unit、StagePlan、上游 seals 和 sibling fragments，只调用目标 unit，修复后重建受影响 aggregate 与全部下游；父证据不可变且任何失败均不产生部分安装。
- [x] 实现 [ADR 0012](../adr/0012-approved-storyboards-and-production-units.md) 的 M1 规范部分，并由 [ADR 0016](../adr/0016-versioned-authoring-quality-gates-and-approval.md) 固定场次顺序/时间、`DialogueCue`、`AudioPlan`、实体状态、Approval 和 `GateResult` 的可执行边界。
- [x] 每个 Beat 恰好一条 `PRIMARY` 覆盖并允许多条 `SUPPORTING`；aggregate 拒绝跨 shard 的缺失、重复、乱序和越界引用。
- [x] 补场次顺序/时间、结构化对白/声音、实体状态，以及对白 fit/实体状态/覆盖/连续性等 ADR 0012 全局门；required skipped 不得冒充通过。
- [x] 删除 storyboard Prompt 中无法由输出 schema 表达的“选择挂在最后一镜”，并建立 Prompt/schema consistency 测试。

### M1-A：真实本地 LLM 分片流水线

- [x] Story Bible/Graph 采用有界单元；Scene Beats/Storyboard 按稳定 node/scene 身份分片，禁止任意文本切块。
- [ ] UI 在调用前显示全局预算/上限；运行中已用 secret-free progress 投影显示各阶段与精确 work unit，仍需补齐并发、时限和超限时的可行动拒绝原因。
- [x] 后端可追溯工作单元状态、dispatch、timeout/outcome-unknown、取消和安全恢复；不盲目重放可能已提交的调用。
- [x] 精确 work-unit repair、逐 unit 轻量进度、attempt `n/max`、稳定失败码和服务端授权动作展示；预算编辑/预估另由上一项跟踪。
- [x] 有效片段只封存为候选；所有 aggregate 和全局门通过后才一次安装请求的完整阶段范围。
- [x] 使用服务公布的 `gemma4` 完成一次隔离的真实本地 LLM 最小全链路；后续两个命名 profile 已完成 M1.5 严格 3× 基线，M1-C 的 18 条三故事验收仍未完成。

### M1.5：模型无关的可靠生成闭环

- [x] 命名 text-provider profiles、独立 revision/active selection、完整公开快照和按 profile 分区的 server/session key。
- [x] `compatible_v1`、`quality_reasoning_v1`、`final_only_v1` 三个版本化预设及可验证的自定义执行合同。
- [x] 入队前用有界动态规划冻结 `story_graph_topology.v1`；模型只填写固定 node/edge/join ID 的内容，binder 后仍走完整 Story Graph validator。
- [x] 分片输出只使用 response-local alias；trusted binder 注入 selector-owned parent，并按 frozen selector 与局部顺序派生 canonical UUIDv5；Storyboard 以封闭 beat→shot 映射生成 PRIMARY links，join continuity keys 在入站/汇流 state 合同中显式约束。
- [x] primary 后最多两次显式 correction；每次保留 lineage、完整 evidence、稳定 outcome code、耗时/token，并在耗尽后隔离，绝不降低 validator 或改拓扑。
- [x] planner 只执行 byte-budget 和 output-alone 的可证明检查，provider tokenizer 保有精确 context check；0006 安全终止旧非终态 run 并要求重提，0007 持久化 stable run failure codes。
- [x] [ADR 0018](../adr/0018-trusted-story-timing-allocation.md) 将 `targetPlaythroughSeconds` 固定为路径硬上限：封存 graph 后冻结/hash `scene_timing_allocation.v1`，trusted binder 派生 cue 时长和 scene budget，模型不再承担 Unicode 计数或绝对时长算术，correction 也不能扩大预算。
- [x] 安全重启、session-only key 重新授权、无重放的 outcome unknown，以及带固定 `workloadHash`/`sampleOrdinal` 的 stage-level secret-free conformance runner 均有自动回归；生产静态 UI 和 wheel smoke 已更新。
- [x] 使用同一锁定中文 Brief，让两个指定的已保存文本 profile 各跑 3 次；[secret-free receipts](../verification/2026-09-03-m15-conformance.jsonl)记录每个 profile 3/3 原子安装、12/12 阶段首次通过、最大 attempt 1、零 issue/unknown outcome。验收身份来自 `profileId`，未触发任何模型名、alias 或供应商特例。

### M1-B：截图级连续创作工作台

- [x] **M1-B0：**按 [ADR 0014](../adr/0014-project-lifecycle-and-workbench.md) 实现项目 list/create/switch/archive/restore/永久 delete/duplicate、空白/样例新建、显式保存与 `sessionStorage` 草稿恢复；URL 是导航事实源，异步请求按 epoch 隔离。跨进程 lifecycle revision、archive 只读/busy guard、永久删除确认、最大连续 READY 前缀复制及 delayed-response 浏览器旅程均有自动验证，并保留 1440×900 工作台视觉基线。
- [x] **M1-B1 编辑合同：**StoryBible、Graph、SceneBeatPlan、Storyboard 的当前 V2 字段都有可理解的编辑器；稳定 ID 的节点/边、场次/节拍/DialogueCue、镜头/ShotBeatLink 支持增删重排。跨记录关系迁移先显示影响并确认，不隐藏级联。
- [x] **M1-B1 工作台反馈：**左侧资产/项目上下文、中间 stage 编辑和右侧 Inspector 连成一个工作区；Inspector 显示 stage/work-unit、attempt、token、seal、失败码、Gate/Approval 与服务端授权动作。无媒体仍是明确占位。
- [x] **M1-B1 可行动恢复：**server schema/domain `422` 保留草稿和 `issues[].path`，编辑器可选择并聚焦对应字段；刷新保留 URL entity/run。bearer run 缺其冻结 Profile 的 server/session key 时不自动恢复、不换 profile。
- [x] **M1-B1 精确 repair 旅程：**真实 FastAPI + 公开 HTTP fake-provider 浏览器测试证明隔离 shard 经“修复这个 work unit”重试，成功 sibling hash 不变，四阶段重新封存并原子安装，Approval 后刷新仍可追溯。
- [x] **M1-B1 checkpoint：**全量 Python、前端、类型、Vite/静态 bundle、Prompt Lab、wheel 安装和 9-worker 浏览器 gate 已通过；Approval hydrate 竞态在全量 gate 暴露后以 canonical loading contract 修复，并经并行重复验证。

### M1-C：Alpha 验收

- [x] fake-provider 与确定性后端矩阵覆盖分片缺失/重复/聚合冲突、并发编辑、取消竞态、未知提交结果、重启、精确 repair 和无部分安装；真实浏览器 repair 旅程进一步证明 sibling reuse 与全范围原子安装。
- [x] ADR 0024 当前模块：精确 `adapterId`/`adapterVersion` registry 与 profile control plane、V3 新运行快照、profile-scoped secret-free readiness、非生成 preflight 和 admission guard 已实现，并保持 V1/V2 hash/resolver 不变。`default` 的单次 live probe 已返回 `readiness.models_verified`；这仍不等于独立真实验收。详见 [provider-readiness verification ledger](../verification/2026-09-10-provider-readiness-offline-candidate.md)。
- [ ] 对每个拟支持 backend 独立运行三份固定中文故事、每份重复三次，共 9 条真实全流水线；9/9 原子安装、至少 30/36 阶段首次通过，记录独立版本与脱敏证据。先验收 `default`，`qwen36_35b` 延后。
- [ ] 对该 backend 每个故事固定抽取一条，共 3 份盲评，使用原 `codex_external_review` rubric 与分数门槛；结果绑定准确来源与 snapshot，不冒充人类评审或产品 Approval。旧双 profile 18-run/6-review 模式保留原义，尚未通过。

### M2：ProductionUnit 与媒体 Artifact 闭环

- [ ] 从已批准 Storyboard 确定性派生 provider-neutral `ProductionUnit`、时间线、cut/frame、Dialogue/Audio 安排和 `ShotReferencePlan`；它不是第五个 canonical stage。
- [ ] adapter 从冻结 `ProductionSnapshot` 编译供应商 Prompt/request/manifest；供应商限制只产生显式 capability 决定，不改写 Shot。
- [ ] 建立角色设定、地点/光照状态、道具状态、style、keyframe、video 和人工导入的 asset roles/reference lineage。
- [ ] 媒体下载与人工导入验证 URL 每跳、DNS/IP、MIME/魔数、大小、尺寸/时长、hash、许可证和路径；UI 优先使用本地 Artifact。
- [ ] 先生成小样并批准 style/reference，再允许扩大批次；图片区分 candidate、selected 和 approved，最新结果不会自动成为视频参考。
- [ ] 精确定义停止观察、请求取消、供应商确认取消和 outcome unknown；不得重复提交可能产生费用的媒体任务。

### M3：可移植项目、审阅与恢复

- [ ] canonical export/import 带格式版本、完整 revision/approval/run/gate/artifact hash 和 production manifest。
- [ ] 导入先预检，再按明确冲突策略原子执行；拒绝标题充当项目身份、静默覆盖、坏 hash 和不支持的迁移。
- [ ] 提供只读 HTML/Markdown 审阅报告和 checkup 模式，使现有规范数据可诊断而不自动安装或改写。
- [ ] 完成备份保留/清理、空 data-dir 恢复和缺失/损坏 Artifact 演练。

### M4：互动预览与离线交付

- [ ] 把自由 `stateEffects` 收口为 typed initial state、choice guard、effect operation、join reconciliation/reducer。
- [ ] 预览和导出绑定已批准 snapshot，支持至少两条分支路线回放；无媒体时仍显示 timing、对白和分镜。
- [ ] 离线包 manifest 带 schema/runtime 版本、canonical revision、asset hash 和缺媒体政策；执行结构与资产完整性检查并验证离线启动。

### M5：Release Candidate

- [ ] CI 浏览器门无 flaky；完成干净环境安装、升级、数据目录、`.env`、端口回退、备份恢复和卸载保留数据演练。
- [ ] 经用户授权后完成文本、图像和视频真实 provider smoke，保存脱敏能力、任务、状态和本地产物收据。
- [ ] 把 Approval stale、required gate 的 `SKIPPED`、Production manifest 和媒体本地可用性纳入 release gates。
- [ ] 复核 LICENSE、NOTICE、SBOM、文件级 provenance 和发布包内容，签发 L7 收据。

### 明确延后，不计作当前缺陷

- 线性分集/长篇原文改编、完整 TTS/配音/口型、批量最终剪辑与 FFmpeg 成片。
- AI Copilot/Agent 项目改写；只能在 Approval、revision、trace 和 stale 合同稳定后单列里程碑。
- 公开多用户部署、RBAC 和协作；当前无外部认证的远程实例必须保持私有。
- 私有 shot-recipes 内容永不计入完成度；未来只可使用自研或明确授权的版本化接口。

## 维护规则

1. 合并任何 Plotloom 能力时，更新相应行的“成熟度/目标”和“下一退出条件”，不要只勾任务。
2. 提升等级必须附新证据；测试名、运行收据、ADR 或实际产物至少有一项。
3. 真实供应商测试必须先获得用户授权并限制预算；不得为追求 L6 自动花费额度。
4. 远端仓库变化不会自动改变本表。要采用新上游事实，先固定新 commit、更新来源审计，再讨论 Plotloom 决策。
5. Defer/Reject 若被重新打开，必须说明范围为何变化，并把状态退回 L1；不得直接跳到实现。
6. 每次发布候选至少更新快照日期、验证命令结果、Git/CI 基线和 P0 队列。

## 证据导航

- 两套系统逐层比较：[第七章](../storyboard-handbook/src/chapters/07-two-systems-comparison.html)
- 统一领域模型：[第八章](../storyboard-handbook/src/chapters/08-unified-domain-model.html)
- 重建路线、ProviderAdapter、测试与里程碑：[第九章](../storyboard-handbook/src/chapters/09-rebuild-roadmap.html)
- Plotloom 开发入口：[开发指南](../development.md)
- 干净仓库边界：[初始提取来源](../provenance/initial-extraction.md)
- V1/Plotloom 架构、输入到分镜 workflow、血缘与修复图：[架构文档入口](../architecture/README.md)
