# Plotloom · 叙织能力吸收与完成度矩阵

> **用途：**这是 Plotloom “从两个来源学到了什么、决定怎么处理、现在完成到哪一层、下一项证据是什么”的唯一进度总表。
>
> **快照日期：**2026-09-03。产品结论以固定版本为基线，不随远端分支漂移。
>
> **决策依据：**能力追踪采用 [ADR 0008](../adr/0008-capability-based-adoption-tracking.md)，当前独立仓库与身份边界采用 [ADR 0010](../adr/0010-plotloom-clean-repository.md)，运行与生产边界采用 [ADR 0011](../adr/0011-provider-profiles-and-generation-work-units.md)、[ADR 0012](../adr/0012-approved-storyboards-and-production-units.md)、[ADR 0013](../adr/0013-model-neutral-reliable-generation.md) 和 [ADR 0014](../adr/0014-project-lifecycle-and-workbench.md)。ADR 0003–0007 保留了重建阶段的历史架构证据。

## 一眼看懂当前状态

| 观察面 | 当前判断 | 它真正说明什么 |
|---|---:|---|
| 规范领域与“输入 → 分镜”后端核心 | **约 90%** | 稳定 ID、四阶段合同、确定性 DAG 骨架、内容绑定、命名 profile、显式有限纠错、领域分片、封存聚合和原子安装均已实现；fixture 全链路与双 profile M1.5 真实验收均通过。仍需精确 work-unit repair，以及 ADR 0012 的时间、对白/声音、批准和生产投影合同。 |
| 可供创作者连续使用的本地 Alpha | **约 75%** | React 工作台已支持命名 profile、session-only key、预设、测试、生成、冻结 topology、项目目录、草稿保护、生命周期操作、URL 导航与 attempt 进度；原子首次保存和双 profile 3× 验收均已通过。完整字段编辑和精确修复旅程仍未完成。 |
| 可独立发布的新仓库产品 | **约 65–70%** | Plotloom 已进入全新仓库，独立依赖、wheel、生产 UI、边界门和远端 CI 已建立；本地 E2E 竞态已修复，仍缺新远端收据、干净机器升级/恢复与图像/视频真实供应商 smoke。 |

这些百分比是路线规划估计，不是测试覆盖率，也不能相加。可复核的当前基线是：

- 已盘点 **35 项能力**：2 项达到 L6 真实运行验收，4 项达到 L5 本地产品/浏览器验证，16 项达到 L4 自动验证，3 项停在 L3 实现层，4 项已到 L2 合同层，1 项只有 L1 决策，5 项是明确的 Defer/Reject；是否完成仍取决于该行目标是 L4、L5、L6 还是 L7；
- `uv run pytest -q`：M1-B0 工作树为 **264 passed / 75 warnings**；
- `npm --prefix frontend test`：**68 passed**；
- Plotloom TypeScript、E2E TypeScript、Vite 生产构建与 wheel 安装 smoke 通过；
- 浏览器回归现有 **14/14 个场景通过**：4 个首次保存、2 个 provider，以及 8 个项目目录/导航场景；后者覆盖显式 onboarding、双项目切换、前进/后退、草稿三向保护与刷新恢复、归档/恢复/安全永久删除、duplicate 幂等重放、entity/run URL 状态和延迟响应隔离。测试连接真实 FastAPI，但不会联系真实 provider。最新远端收据仍待 M1-C 统一推送后取得；
- 经用户授权的[隔离 live smoke 收据](../verification/2026-09-02-local-text-smoke.md)使用服务公布的 `gemma4`：127.4 秒完成 6 次调用/6 个 work units，四阶段全部封存并一次安装，零验证失败；`.env` 中的配置名仍是未被服务公布的 `gemma-4-26B-A4B-it-Q4_K_M.gguf`，需另行对齐，且该收据不代表 Qwen、图像或视频已验收；
- [M1.5 严格验收收据](../verification/2026-09-03-m15-conformance.jsonl)记录两个已保存真实 profile 各 3 次固定中文 Brief：6/6 run 原子成功，双方均为 12/12 阶段首次通过、最大 attempt 1、零 issue 与零 unknown outcome；profile、workload、run 与 topology 均以 hash/稳定 ID 存证，不保存 endpoint、模型名、IP、prompt、response 或密钥；
- Plotloom-only wheel、模板、迁移树、静态 UI 与禁止 V1 依赖的提取演练包含在上述 Python gate 中；
- [远端 CI run 33671097019](https://github.com/Wenjun-Mao/plotloom/actions/runs/33671097019) 已在 `3bf4551` 成功完成前端、Python、wheel、安装 smoke 和浏览器步骤；
- **当前发布阻断：**补新远端无 flaky 收据、精确 work-unit repair、干净机器安装/升级/恢复和真实图像/视频供应商 smoke。M1.5 双 profile 严格资格测试已经通过；当前独立仓库仍是可验证基线，不是发布候选。

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
| A03 | 故事圣经、角色、地点、道具 | 角色卡和场景卡贴近媒体生成工作台 | cast/art 分开建立 C/S/P 资产和视觉、声音、连续性规格 | **Adapt** 为稳定 ID 的 `StoryBible` | **L4/L5** | 后端合同、引用校验和生成阶段已测；[`StoryBiblePage.tsx`](../../frontend/src/pages/StoryBiblePage.tsx) 只编辑部分字段，地点/道具、traits 等尚无完整 UI。 |
| A04 | 互动剧情图、选择、汇流与结局 | `choices`/`next` 和播放器证明互动路线的产品价值 | 五阶段流程没有互动图，可作为明确反例边界 | **Rebuild** 为可达 DAG、state effects 和 join contracts | **L4/L5** | 图、环、可达、结局和汇流验证已测；[`GraphPage.tsx`](../../frontend/src/pages/GraphPage.tsx) 已有画布，但节点增删、边属性和 join contract 编辑不完整。 |
| A05 | 戏剧场次、节拍与连续性 | 暴露动作、对白、首尾状态，但 V1 的 `scene` 实际近似 shot | `script.flow` 明确保留 action/line beat、场次和时长 | **Rebuild** 为稳定 `DramaticScene` + `Beat` + `ContinuityState` | **L4/L5** | 规范模型与跨引用/连续覆盖测试通过；[`SceneBeatsPage.tsx`](../../frontend/src/pages/SceneBeatsPage.tsx) 只覆盖部分字段和操作。 |
| A06 | 分镜、镜头与节拍覆盖 | 单镜头编辑、媒体按钮和按路线预览形成短反馈回路 | segment/cut、时长和 exact-once coverage 提供清晰生产规格 | **Adapt** 为 `Shot` + many-to-many `ShotBeatLink`；主剪可另作派生投影 | **L4/L5** | Shot/coverage 合同和按路径分组已测；[`StoryboardPage.tsx`](../../frontend/src/pages/StoryboardPage.tsx) 尚不能完整增删重排、编辑全部镜头字段或可视化覆盖关系。 |
| A07 | 线性分集短剧 | V1 有独立 serial 模式与分集导出 | shuohao 的集/场/段/切/秒数链对线性 AI 短剧更完整 | **Defer** 为规范模型的线性投影，不成为第二套核心 | **D** | [ADR 0003](../adr/0003-v2-strangler-architecture.md) 首发只做互动项目。重新开启条件：互动 Alpha 稳定，且 episode/linear projection ADR 获批。 |
| A08 | 无 Key 教学样例与确定性 bootstrap | 本地模板无需供应商即可创建可操作草案，适合首次启动、演示和 E2E | 各阶段 deterministic seed 能复制已批准事实，但不会替 agent 创作语义 | **Adopt** 教学/测试价值，不把固定模板冒充生产生成器 | **L5/L5** | [`demo.ts`](../../frontend/src/demo.ts) 提供完整教学项目和 trace；真实浏览器已从无项目教学工作区保存完整四阶段前缀，并在刷新后恢复、呈现和继续编辑分镜。 |
| A09 | 结构化对白、声音、时间线与资产状态 | V1 的镜头表单、角色/场景卡和媒体预览证明这些信息必须在同一工作流可见，但自由字符串与可变场景对象不可保留 | script/storyboard 的 speaker、动作/台词估时、声音、连续性、角色/地点/道具状态提供生产规格 | **Adapt** 为 `DialogueCue`、`AudioPlan`、场次顺序/时间线和稳定实体状态引用 | **L2/L5** | [ADR 0012](../adr/0012-approved-storyboards-and-production-units.md) 已定义合同；尚缺 schema/迁移、Prompt、验证器、完整 UI 和浏览器验收。 |

### B. LLM Prompt、响应与可解释生成

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| B01 | 分阶段、版本化 Prompt 编译 | 当前表单到生成请求的短链路值得保留；V1 的前后端散落模板不保留 | SKILL/pass 文档把每阶段创作责任写清楚 | **Rebuild** 为包内唯一模板源、严格变量和内容哈希 | **L4/L4** | 十一个文本/媒体模板位于 [`prompt_templates/`](../../src/plotloom/prompt_templates/)，其中 Story Graph content-fill 和 correction 合同绑定冻结骨架/错误码；确定性渲染、schema 和 wheel 打包测试通过。 |
| B02 | 响应抽取、schema 与语义验证 | 安装器已有重复 key、目标和规模检查 | 每层 validator/selftest 体现“模型输出不能直接成为主数据” | **Adapt/Rebuild** 为同一条 parse → schema → semantic 链 | **L4/L4** | [`generation/responses.py`](../../src/plotloom/generation/responses.py) 与 [`generation/validation.py`](../../src/plotloom/generation/validation.py) 有严格测试；只有 `message.content` 的字符串或显式 `text`/`output_text` part 可进入抽取，reasoning/未知 part 只作原始证据，且不会从任意说明文字截取 JSON。 |
| B03 | 四阶段原子流水线与 stale 传播 | V1 一键生成体验可保留，但整树响应和可变安装不可保留 | 显式阶段交接可保留，但手工重跑不可作为 runtime | **Rebuild** 为连续阶段范围、不可变 snapshot、事务安装 | **L4/L4** | [`pipeline.py`](../../src/plotloom/pipeline.py) 与 repository 测试覆盖原子四阶段提交、并发编辑和下游 stale。 |
| B04 | Revision、Prompt Inspector 与 provenance | V1 缺少“哪个输入/提示/响应生成此结果”的完整链 | 文件和 gate log 有局部来源，但没有统一 revision/hash 图 | **Rebuild** 为 Run/Attempt/Artifact/EntityRevision | **L4/L5** | 后端持久化完整 trace，前端 [`TracePage.tsx`](../../frontend/src/pages/TracePage.tsx) 可查看；下一步是浏览器 E2E 证明刷新后仍能完整追溯。 |
| B05 | 隔离、人工修复与 AI 修复血缘 | V1 失败多停在提示或宽容安装 | shuohao 门能拒绝，但批准/修复未绑定精确版本 | **Rebuild** 为 quarantine 和证据冻结的 child run | **L4/L5** | 旧 whole-stage 证据修复、旧快照拒绝和无部分安装已有测试；新版 work-unit 失败会明确 fail-closed 并要求 rebuild，避免误用单个 fragment 或先花费模型调用。退出条件是实现精确 work-unit/sibling/aggregate repair 及真实浏览器旅程。 |
| B06 | 确定性质量门与创作 eval | V1 测试覆盖运行路径，不能证明镜头好看 | 17 道门、逐门击穿 fixture 和失败统计思想很有价值 | **Adapt** 为带版本和证据的 `GateResult`；艺术质量单独人工评审 | **L3/L5** | 已有 DAG、引用、覆盖、时长等结构门；[ADR 0012](../adr/0012-approved-storyboards-and-production-units.md) 已定义 `PASS/FAIL/SKIPPED/NOT_APPLICABLE` 边界。尚缺统一实现、逐门击穿 fixture、固定故事和叙事清楚度/节奏/连续性 rubric。 |
| B07 | 人工批准点 | V1 的“保存/生成”是操作，不是版本化批准 | 阶段文件天然形成审阅点，但批准不绑定 revision | **Rebuild** 为精确 revision/hash 的 approval/decision；保存不等于批准 | **L2/L5** | [ADR 0012](../adr/0012-approved-storyboards-and-production-units.md) 已定义批准、撤销、上游变更后 stale 及媒体前置条件；尚缺实体、API、UI 和浏览器旅程。 |
| B08 | Provider Profile、生成计划、分片工作单元与封存聚合 | V1 有用户可见规模限制和单次调用，但取消主要只是停止前端观察 | 五阶段按文件/批次控制规模，但没有在线、可恢复的 shard lifecycle | **Rebuild** 为冻结 `ProviderProfile` 的 `GenerationPlan → StagePlan → GenerationWorkUnit → SealedStageAggregate`，显式定义超时、未知结果、纠错和取消 | **L6/L6** | 命名且 revisioned 的**文本** profile、三个版本化预设、确定性最小 Story Graph 骨架、content-only binder、fragment local alias→selector/order UUIDv5、selector-owned parent 注入、封闭 PRIMARY beat→shot 映射、显式 join continuity keys、最多两次可见 correction、response-after-crash 本地续跑、0007 稳定 run failure code 和 secret-free conformance 收据均通过自动测试。planner 的输入数值是 byte estimate，精确 context 由 provider tokenizer 判定；0006 已安全终止旧非终态 run 并要求重提。[严格 3×2 收据](../verification/2026-09-03-m15-conformance.jsonl)证明两个指定 profile 各 3/3、固定 `workloadHash` 下各 `sampleOrdinal` 唯一，且双方均 12/12 阶段首次通过。精确 work-unit repair 仍 fail-closed 且需 rebuild。 |

### C. Provider、媒体生产与输出

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| C01 | Provider 设置与秘密边界 | 文本/图像/视频可分别选 provider/model/base URL；服务器 key 与会话覆盖实用 | 供应商调用主要交给运行 agent，不适合作为产品秘密模型 | **Rebuild** 严格 public settings + server key/session lease | **L6/L6** | API、数据库、trace、日志、URL root 与按 profile 分区的 sessionStorage 边界均有测试；`authMode=none` 不读取/发送 key，rebuild/repair/resume 不会串用 profile key。两个当前文本 profile 已通过真实 3× conformance，receipt 只含稳定 ID/hash、状态、issue、耗时与 token；图像/视频 smoke 不属于 M1.5。 |
| C02 | 关键帧图像生成 | 多供应商、逐镜按钮、参考图和项目资产闭环 | 可选 imagegen 与 frame prompt/缺图占位体现“文本交付不被图片阻断” | **Adapt** 到冻结 Shot snapshot 的 `MediaTask` | **L4/L6** | OpenAI/AtlasCloud/DashScope adapters 和 UI 单镜任务由 fake 测试覆盖；缺真实调用、结果下载校验和本地入库。 |
| C03 | 视频生成 | V1 的 submit/poll 和逐镜视频是重要产品能力 | 不执行视频生成，反而清楚限定 storyboard 是生产规格 | **Adapt** 到同步/异步统一 adapter 和任务状态 | **L4/L6** | AtlasCloud/DashScope/Seedance adapters、关键帧前置和恢复轮询有 fake 测试；缺真实调用、播放质检和供应商取消语义。 |
| C04 | 持久任务、重启恢复与浏览器观察 | V1 能本地轮询/恢复等待，但停止观察不等于远端取消 | 没有一等在线任务/run | **Rebuild** 为数据库事实和安全 reconciliation | **L4/L5** | 文本运行可继续同一未 dispatch attempt 或仅从持久 response 做本地验证，dispatched-without-response 保持 outcome unknown；仅靠 browser key 的安全运行重启后保持 queued，并由同一 profile 的 session key 显式 resume。媒体覆盖 queued resubmit 和 provider task ID poll；浏览器媒体轮询仍待补。 |
| C05 | Artifact、媒体落地与内容寻址 | V1 把媒体保存进项目 assets | shuohao 把主数据、报告和投产包分层 | **Adapt/Rebuild** 为 content-addressed ArtifactStore | **L3/L5** | prompt/response/validation/canonical artifacts 已原子、去重落地；媒体成功目前主要保存远端 `outputUri`，缺 MIME/大小/哈希校验、下载、离线可用和垃圾回收。 |
| C06 | 互动预览与可播放导出 | 这是 V1 最应保留的优势之一：编辑后立即试玩并导出 | 不提供播放器或最终视频 | **Adopt outcome / Rebuild implementation** | **D** | 首个 Plotloom slice 明确未包含。重新开启条件：浏览器 Alpha 与本地媒体 ingest 达 L5。 |
| C07 | 批量生成、最终剪辑与成片交付 | V1 有批量媒体和互动/分集导出，可作为行为参考 | export pack/manifest 适合可审阅投产交接，但不生成最终视频 | **Defer**，以后基于 Plotloom task/artifact/export contracts 重建 | **D** | 批量队列、取消、全局 timecode、配音/口型、剪辑、QC、最终成片都不计入当前完成度。 |
| C08 | 已批准分镜到 ProductionUnit 与供应商编译 | V1 的单镜生成回路反馈短，但 Shot/Prompt/Task 边界不稳定 | segment/cut/frame 与 H3 投产包说明需要独立生产层，但线性位置和供应商字符串不能成为主数据 | **Adapt/Rebuild**：从 approved Storyboard 确定性派生 provider-neutral `ProductionUnit`，再由 adapter 编译 | **L2/L5** | [ADR 0012](../adr/0012-approved-storyboards-and-production-units.md) 已定义 canonical/derived 边界、时长/切点/帧计划和 stale；尚缺 planner、compiler、manifest、UI 及媒体前置验证。 |
| C09 | 资产角色、参考血缘与受控人工导入 | V1 有角色设定图、场景参考、逐镜素材和本地保存，但任意路径/URL 边界过宽 | 角色/地点/道具锚点、状态变体及小样先审提供清晰的一致性方法 | **Adapt/Rebuild** 为稳定 asset role、`ShotReferencePlan` 和内容寻址 Artifact；人工导入走受控入口 | **L2/L5** | [ADR 0012](../adr/0012-approved-storyboards-and-production-units.md) 定义最小角色、hash/MIME/尺寸/时长、来源和 revision 绑定；尚缺实体、导入/下载安全、引用解析、小样批准和离线可用验收。 |

### D. 平台、工作台与独立发行

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| D01 | SQLite、迁移与并发写入 | 项目文件、原子保存和备份易理解，但缺细粒度事务 | 分层 JSON 易 diff，但依赖操作者管理一致性 | **Rebuild** 为 repository、Alembic、optimistic revision | **L4/L5** | SQLite/WAL/外键、迁移、原子 rollback、startup reconciliation 及跨 repository 并发幂等测试通过；写锁耗尽会返回带 `Retry-After` 的可控 503。仍需安装版数据恢复演练和用户可见备份/导出。 |
| D02 | React 工作台与完整用户旅程 | 浏览器内创作→媒体→预览的单一工作台是核心产品价值 | 分阶段操作和报告适合清晰导航 | **Adapt** 为七页 Plotloom 工作台 | **L5/L5**（M1-B0） | [ADR 0014](../adr/0014-project-lifecycle-and-workbench.md) 的项目目录、URL/epoch 导航、显式保存、sessionStorage 草稿恢复、生命周期操作和 Plotloom 原创三栏布局均已实现；真实 FastAPI 浏览器旅程覆盖项目切换、历史导航、冲突、归档/恢复/复制/删除和延迟响应隔离。完整字段编辑、精确修复、Gate/Approval 属于后续 M1-B1。 |
| D03 | Plotloom 导入、导出、备份与可移植项目 | V1 project JSON/备份能带走作品，但直接安装 JSON、标题目录和无保留策略不安全 | 五层 JSON/Markdown/manifest 便于审阅交接 | **Rebuild** Plotloom canonical 格式；**Reject** 首发 legacy migration | **L1/L5** | [初始提取来源](../provenance/initial-extraction.md) 定义 Plotloom-only 数据边界；退出条件还必须覆盖格式版本、预检、hash/manifest、冲突策略、原子导入、稳定 project ID、备份保留/清理和空 data-dir 恢复。任何 V1/shuohao 导入只能在未来另立迁移 ADR。 |
| D04 | 无 V1 依赖的提取、打包与新仓库 | V1 只作为比较和行为证据存在 | shuohao 的自包含边界提醒我们保持模块独立，但不复制其规则重复 | **Rebuild** 为单包、单 UI、可移动 roots | **L5/L7** | 全新 Plotloom 仓库、fresh history、依赖边界、独立 wheel/资源探测和生产 bundle 已建立；[远端 CI](https://github.com/Wenjun-Mao/plotloom/actions/runs/33671097019) 已成功，但应先消除浏览器 flaky，再完成干净安装/升级/卸载数据策略与恢复收据。 |
| D05 | E2E、真实供应商与创作质量验证 | V1 有浏览器/媒体/导出行为可作回归样例 | selftest 的击穿 fixture 纪律值得采用 | **Adapt** 为分层验证金字塔 | **L5/L6** | M1-B0 工作树已有 264 个 Python、68 个前端单元测试和 14 个真实 FastAPI 浏览器场景通过；首次保存竞态另有 30/30 与锁文件重装后 15/15 的重复证据。M1.5 双 profile 3× 固定故事验收为 6/6 run、双方 12/12 阶段首次通过。仍待新远端 CI、媒体 smoke 和 M1-C 固定故事独立盲评。 |
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
- [ ] 实现失败单元的**精确** repair：冻结目标 unit、StagePlan、上游 seals 和 sibling fragments，修复后重建受影响 aggregate 与下游。当前明确 fail-closed 并要求 rebuild，不会误走旧路径。
- [ ] 实现 [ADR 0012](../adr/0012-approved-storyboards-and-production-units.md) 的 M1 规范部分：场次顺序/时间、`DialogueCue`、`AudioPlan`、实体状态、Approval 和 `GateResult`。
- [x] 每个 Beat 恰好一条 `PRIMARY` 覆盖并允许多条 `SUPPORTING`；aggregate 拒绝跨 shard 的缺失、重复、乱序和越界引用。
- [ ] 补场次顺序/时间、结构化对白/声音、实体状态，以及对白 fit/资产状态等 ADR 0012 全局门。
- [x] 删除 storyboard Prompt 中无法由输出 schema 表达的“选择挂在最后一镜”，并建立 Prompt/schema consistency 测试。

### M1-A：真实本地 LLM 分片流水线

- [x] Story Bible/Graph 采用有界单元；Scene Beats/Storyboard 按稳定 node/scene 身份分片，禁止任意文本切块。
- [ ] UI 在调用前显示全局预算/上限；运行中随着上游 aggregate 完成，显示各阶段封存后的精确工作单元、并发和时限；超限时给出可行动拒绝原因。
- [x] 后端可追溯工作单元状态、dispatch、timeout/outcome-unknown、取消和安全恢复；不盲目重放可能已提交的调用。
- [ ] 精确 work-unit repair 与 UI 进度/预算/可行动错误展示。
- [x] 有效片段只封存为候选；所有 aggregate 和全局门通过后才一次安装请求的完整阶段范围。
- [x] 使用服务公布的 `gemma4` 完成一次隔离的真实本地 LLM 最小全链路；配置名对齐和 M1-C 的 30 条固定故事仍未完成。

### M1.5：模型无关的可靠生成闭环

- [x] 命名 text-provider profiles、独立 revision/active selection、完整公开快照和按 profile 分区的 server/session key。
- [x] `compatible_v1`、`quality_reasoning_v1`、`final_only_v1` 三个版本化预设及可验证的自定义执行合同。
- [x] 入队前用有界动态规划冻结 `story_graph_topology.v1`；模型只填写固定 node/edge/join ID 的内容，binder 后仍走完整 Story Graph validator。
- [x] 分片输出只使用 response-local alias；trusted binder 注入 selector-owned parent，并按 frozen selector 与局部顺序派生 canonical UUIDv5；Storyboard 以封闭 beat→shot 映射生成 PRIMARY links，join continuity keys 在入站/汇流 state 合同中显式约束。
- [x] primary 后最多两次显式 correction；每次保留 lineage、完整 evidence、稳定 outcome code、耗时/token，并在耗尽后隔离，绝不降低 validator 或改拓扑。
- [x] planner 只执行 byte-budget 和 output-alone 的可证明检查，provider tokenizer 保有精确 context check；0006 安全终止旧非终态 run 并要求重提，0007 持久化 stable run failure codes。
- [x] 安全重启、session-only key 重新授权、无重放的 outcome unknown，以及带固定 `workloadHash`/`sampleOrdinal` 的 stage-level secret-free conformance runner 均有自动回归；生产静态 UI 和 wheel smoke 已更新。
- [x] 使用同一锁定中文 Brief，让两个指定的已保存文本 profile 各跑 3 次；[secret-free receipts](../verification/2026-09-03-m15-conformance.jsonl)记录每个 profile 3/3 原子安装、12/12 阶段首次通过、最大 attempt 1、零 issue/unknown outcome。验收身份来自 `profileId`，未触发任何模型名、alias 或供应商特例。

### M1-B：截图级连续创作工作台

- [x] **M1-B0：**按 [ADR 0014](../adr/0014-project-lifecycle-and-workbench.md) 实现项目 list/create/switch/archive/restore/永久 delete/duplicate、空白/样例新建、显式保存与 `sessionStorage` 草稿恢复；URL 是导航事实源，异步请求按 epoch 隔离。跨进程 lifecycle revision、archive 只读/busy guard、永久删除确认、最大连续 READY 前缀复制及 delayed-response 浏览器旅程均有自动验证，并保留 1440×900 工作台视觉基线。
- [ ] StoryBible、Graph、SceneBeatPlan、Storyboard 全合同字段的可理解编辑，包括节点/边、场次/节拍、镜头/ShotBeatLink 的增删重排。
- [ ] 左侧资产上下文、中间场景/镜头列表和右侧完整 Inspector 连成一个工作区；无媒体明确显示占位。
- [ ] 展示 stage/work-unit 进度、GateResult、失败路径和可行动的 422/provider 错误；刷新后恢复 run/task 观察。
- [ ] 完成隔离 → 修复 → 聚合 → 原子安装 → 刷新复核的浏览器旅程。

### M1-C：Alpha 验收

- [ ] fake-provider 覆盖分片缺失/重复/冲突、并发编辑、取消竞态、未知提交结果、重启、repair 和无部分安装。
- [ ] 用三份固定中文故事完成 30 条真实 Gemma 全流水线；记录模型/profile/prompt/schema hash、成功率、耗时和脱敏失败分布。
- [ ] 人工评审叙事清楚度、人物/空间/道具连续性、表演可读性、节奏与修改成本；主观结果绑定准确 snapshot，不由模型自评替代。

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
