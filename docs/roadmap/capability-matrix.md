# Plotloom · 叙织能力吸收与完成度矩阵

> **用途：**这是 Plotloom “从两个来源学到了什么、决定怎么处理、现在完成到哪一层、下一项证据是什么”的唯一进度总表。
>
> **快照日期：**2026-09-02。产品结论以固定版本为基线，不随远端分支漂移。
>
> **决策依据：**能力追踪采用 [ADR 0008](../adr/0008-capability-based-adoption-tracking.md)，当前独立仓库与身份边界采用 [ADR 0010](../adr/0010-plotloom-clean-repository.md)。ADR 0003–0007 保留了重建阶段的历史架构证据。

## 一眼看懂当前状态

| 观察面 | 当前判断 | 它真正说明什么 |
|---|---:|---|
| 规范领域与“输入 → 分镜”后端核心 | **约 90%** | 稳定 ID、四阶段合同、DAG、场景/节拍、Shot/ShotBeatLink、revision、stale、原子安装与隔离修复已经实现并由替身测试覆盖。 |
| 可供创作者连续使用的本地 Alpha | **约 70–75%** | React 工作台和 API 已接通主要阶段，原子首次保存及真实浏览器回归已通过；项目管理、完整字段编辑和浏览器任务恢复仍不完整。 |
| 可独立发布的新仓库产品 | **约 60–65%** | Plotloom 已进入全新仓库，独立依赖、wheel、生产 UI、边界门和 CI workflow 已建立；首次远端 CI、干净机器安装/恢复与真实供应商 smoke 尚未完成。 |

这些百分比是路线规划估计，不是测试覆盖率，也不能相加。可复核的当前基线是：

- 已盘点 **31 项能力**：3 项达到 L5 本地产品/浏览器验证，17 项达到 L4 自动验证，4 项停在 L3 实现层，2 项只有 L1 决策，5 项是明确的 Defer/Reject；是否完成仍取决于该行目标是 L4、L5、L6 还是 L7；
- `uv run pytest -q`：**124 passed**，另有 1 条第三方 Starlette/httpx 弃用警告；
- `npm --prefix frontend test`：**33 passed**；
- Plotloom TypeScript、E2E TypeScript 与 Vite 生产构建通过；
- `npm --prefix frontend run test:e2e`：**3 passed**，覆盖 stage-first、Brief-first 和失败后同键重试；
- Plotloom-only wheel、模板、迁移树、静态 UI 与禁止 V1 依赖的提取演练包含在上述 Python gate 中；
- **当前发布阻断：**CI workflow 尚未在远端仓库实际运行；干净机器安装/升级/恢复与授权真实供应商 smoke 仍无收据。当前独立仓库是可验证基线，不是发布候选。

## 比较对象和证据边界

| 对象 | 固定版本 | 本矩阵能使用的证据 | 许可证/限制 |
|---|---|---|---|
| Narrative Forge 本地比较基线 | `24c3c47a6fb1e3fcd5a060d705f11bbffb9dbde9` | 本地源码、测试、样本和已有运行审计；比公开 fork 多本地端口选择修订 | Apache-2.0；不能把本地修复写成上游原有能力 |
| Narrative Forge 用户 fork | [`6b4972f`](https://github.com/Wenjun-Mao/Narrative-Forge/tree/6b4972f2b4d826c5944b7625bf95f447236532c4) | 公开 fork 冻结基线 | Apache-2.0 |
| Narrative Forge 原上游 | [`abebc29`](https://github.com/Zafer-Liu/Narrative-Forge/tree/abebc29fd98ff8c9153f8b566c85c7a0e7b1e7a9) | 原项目设计和实现归属 | Apache-2.0 |
| shuohao-skills | [`4322897`](https://github.com/eternityspring/shuohao-skills/tree/4322897e6d2bdaf66365534fd40194360c75a85f) | 公开仓库的静态源码、schema、SKILL、selftest 与迁移说明；未安装、未运行其脚本 | Apache-2.0；NOTICE 归属必须保留；私有 shot-recipes 未取得、未审计、未计入完成度 |

完整证据规则见[来源与冻结版本](../storyboard-handbook/SOURCES.md)，许可证与私有材料边界见[第三方声明](../storyboard-handbook/THIRD_PARTY_NOTICES.md)。本矩阵主要吸收**问题定义、用户价值与合同思想**；“Adopt/Adapt/Rebuild”不代表复制了第三方代码。若以后直接复用可版权化实现或素材，必须单独记录来源、修改和 NOTICE 处理。

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
| A01 | 项目简报与生成边界 | 表单直接表达片名、梗概、类型、画幅、视觉风格和生成规模，反馈短 | 从原文、集数、时长、题材和改编幅度开始，强调保留/删改取舍 | **Adapt** 两者输入，统一成严格 `ProjectBrief` | **L5/L5** | 合同与校验在 [`domain.py`](../../src/plotloom/domain.py)；Brief-first 与 stage-first 真实浏览器旅程均通过并验证刷新后的规范数据。 |
| A02 | 项目生命周期与工作区 | 本地项目保存、恢复快照、服务器备份和项目内素材形成连续工作区 | 独立工作目录和 JSON 便于审阅、Git diff 与交接 | **Rebuild** 为 Plotloom 项目服务 | **L3/L5** | 已有 create/get/patch 与 SQLite；缺 list/switch/delete/archive/duplicate、新建引导和未保存草稿保护。 |
| A03 | 故事圣经、角色、地点、道具 | 角色卡和场景卡贴近媒体生成工作台 | cast/art 分开建立 C/S/P 资产和视觉、声音、连续性规格 | **Adapt** 为稳定 ID 的 `StoryBible` | **L4/L5** | 后端合同、引用校验和生成阶段已测；[`StoryBiblePage.tsx`](../../frontend/src/pages/StoryBiblePage.tsx) 只编辑部分字段，地点/道具、traits 等尚无完整 UI。 |
| A04 | 互动剧情图、选择、汇流与结局 | `choices`/`next` 和播放器证明互动路线的产品价值 | 五阶段流程没有互动图，可作为明确反例边界 | **Rebuild** 为可达 DAG、state effects 和 join contracts | **L4/L5** | 图、环、可达、结局和汇流验证已测；[`GraphPage.tsx`](../../frontend/src/pages/GraphPage.tsx) 已有画布，但节点增删、边属性和 join contract 编辑不完整。 |
| A05 | 戏剧场次、节拍与连续性 | 暴露动作、对白、首尾状态，但 V1 的 `scene` 实际近似 shot | `script.flow` 明确保留 action/line beat、场次和时长 | **Rebuild** 为稳定 `DramaticScene` + `Beat` + `ContinuityState` | **L4/L5** | 规范模型与跨引用/连续覆盖测试通过；[`SceneBeatsPage.tsx`](../../frontend/src/pages/SceneBeatsPage.tsx) 只覆盖部分字段和操作。 |
| A06 | 分镜、镜头与节拍覆盖 | 单镜头编辑、媒体按钮和按路线预览形成短反馈回路 | segment/cut、时长和 exact-once coverage 提供清晰生产规格 | **Adapt** 为 `Shot` + many-to-many `ShotBeatLink`；主剪可另作派生投影 | **L4/L5** | Shot/coverage 合同和按路径分组已测；[`StoryboardPage.tsx`](../../frontend/src/pages/StoryboardPage.tsx) 尚不能完整增删重排、编辑全部镜头字段或可视化覆盖关系。 |
| A07 | 线性分集短剧 | V1 有独立 serial 模式与分集导出 | shuohao 的集/场/段/切/秒数链对线性 AI 短剧更完整 | **Defer** 为规范模型的线性投影，不成为第二套核心 | **D** | [ADR 0003](../adr/0003-v2-strangler-architecture.md) 首发只做互动项目。重新开启条件：互动 Alpha 稳定，且 episode/linear projection ADR 获批。 |
| A08 | 无 Key 教学样例与确定性 bootstrap | 本地模板无需供应商即可创建可操作草案，适合首次启动、演示和 E2E | 各阶段 deterministic seed 能复制已批准事实，但不会替 agent 创作语义 | **Adopt** 教学/测试价值，不把固定模板冒充生产生成器 | **L3/L5** | [`demo.ts`](../../frontend/src/demo.ts) 提供完整只读教学项目和 trace；缺可持久化的“从样例新建”或 Plotloom-owned local template 用户旅程。 |

### B. LLM Prompt、响应与可解释生成

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| B01 | 分阶段、版本化 Prompt 编译 | 当前表单到生成请求的短链路值得保留；V1 的前后端散落模板不保留 | SKILL/pass 文档把每阶段创作责任写清楚 | **Rebuild** 为包内唯一模板源、严格变量和内容哈希 | **L4/L4** | 七个文本/媒体模板位于 [`prompt_templates/`](../../src/plotloom/prompt_templates/)，确定性渲染、schema 和打包测试通过。 |
| B02 | 响应抽取、schema 与语义验证 | 安装器已有重复 key、目标和规模检查 | 每层 validator/selftest 体现“模型输出不能直接成为主数据” | **Adapt/Rebuild** 为同一条 parse → schema → semantic 链 | **L4/L4** | [`generation/responses.py`](../../src/plotloom/generation/responses.py) 与 [`generation/validation.py`](../../src/plotloom/generation/validation.py) 有严格测试；不静默补默认值。 |
| B03 | 四阶段原子流水线与 stale 传播 | V1 一键生成体验可保留，但整树响应和可变安装不可保留 | 显式阶段交接可保留，但手工重跑不可作为 runtime | **Rebuild** 为连续阶段范围、不可变 snapshot、事务安装 | **L4/L4** | [`pipeline.py`](../../src/plotloom/pipeline.py) 与 repository 测试覆盖原子四阶段提交、并发编辑和下游 stale。 |
| B04 | Revision、Prompt Inspector 与 provenance | V1 缺少“哪个输入/提示/响应生成此结果”的完整链 | 文件和 gate log 有局部来源，但没有统一 revision/hash 图 | **Rebuild** 为 Run/Attempt/Artifact/EntityRevision | **L4/L5** | 后端持久化完整 trace，前端 [`TracePage.tsx`](../../frontend/src/pages/TracePage.tsx) 可查看；下一步是浏览器 E2E 证明刷新后仍能完整追溯。 |
| B05 | 隔离、人工修复与 AI 修复血缘 | V1 失败多停在提示或宽容安装 | shuohao 门能拒绝，但批准/修复未绑定精确版本 | **Rebuild** 为 quarantine 和证据冻结的 child run | **L4/L5** | [ADR 0005](../adr/0005-generation-runs-and-quarantine.md) 及 pipeline/repository 测试覆盖多跳修复、旧快照拒绝和无部分安装；缺真实浏览器修复旅程。 |
| B06 | 确定性质量门与创作 eval | V1 测试覆盖运行路径，不能证明镜头好看 | 17 道门、逐门击穿 fixture 和 PASS/FAIL 思想很有价值 | **Adapt**：每道门归属一个 Plotloom 合同；艺术质量单独人工评审 | **L3/L5** | 已有 DAG、引用、覆盖、时长等结构门；尚未完成门清单/`SKIPPED` 语义、固定创作样例与叙事清楚度/节奏/连续性 rubric。 |
| B07 | 人工批准点 | V1 的“保存/生成”是操作，不是版本化批准 | 阶段文件天然形成审阅点，但批准不绑定 revision | **Rebuild** 为精确 revision 的 approval/decision | **L1/L5** | 路线已在[重建路线图](../storyboard-handbook/src/chapters/09-rebuild-roadmap.html)提出；当前领域没有一等 `Approval` 实体。需先写 ADR 和批准/撤销/stale 合同。 |

### C. Provider、媒体生产与输出

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| C01 | Provider 设置与秘密边界 | 文本/图像/视频可分别选 provider/model/base URL；服务器 key 与会话覆盖实用 | 供应商调用主要交给运行 agent，不适合作为产品秘密模型 | **Rebuild** 严格 public settings + server key/session lease | **L4/L6** | API、数据库、trace、日志与 sessionStorage 边界有后端/前端测试；缺经授权的真实文本/图像/视频 key smoke。 |
| C02 | 关键帧图像生成 | 多供应商、逐镜按钮、参考图和项目资产闭环 | 可选 imagegen 与 frame prompt/缺图占位体现“文本交付不被图片阻断” | **Adapt** 到冻结 Shot snapshot 的 `MediaTask` | **L4/L6** | OpenAI/AtlasCloud/DashScope adapters 和 UI 单镜任务由 fake 测试覆盖；缺真实调用、结果下载校验和本地入库。 |
| C03 | 视频生成 | V1 的 submit/poll 和逐镜视频是重要产品能力 | 不执行视频生成，反而清楚限定 storyboard 是生产规格 | **Adapt** 到同步/异步统一 adapter 和任务状态 | **L4/L6** | AtlasCloud/DashScope/Seedance adapters、关键帧前置和恢复轮询有 fake 测试；缺真实调用、播放质检和供应商取消语义。 |
| C04 | 持久任务、重启恢复与浏览器观察 | V1 能本地轮询/恢复等待，但停止观察不等于远端取消 | 没有一等在线任务/run | **Rebuild** 为数据库事实和安全 reconciliation | **L4/L5** | 服务器覆盖 queued resubmit、provider task ID 恢复 poll、歧义 submit 安全失败；浏览器刷新后媒体任务会重载，但不会重新开始非终态轮询。 |
| C05 | Artifact、媒体落地与内容寻址 | V1 把媒体保存进项目 assets | shuohao 把主数据、报告和投产包分层 | **Adapt/Rebuild** 为 content-addressed ArtifactStore | **L3/L5** | prompt/response/validation/canonical artifacts 已原子、去重落地；媒体成功目前主要保存远端 `outputUri`，缺 MIME/大小/哈希校验、下载、离线可用和垃圾回收。 |
| C06 | 互动预览与可播放导出 | 这是 V1 最应保留的优势之一：编辑后立即试玩并导出 | 不提供播放器或最终视频 | **Adopt outcome / Rebuild implementation** | **D** | 首个 Plotloom slice 明确未包含。重新开启条件：浏览器 Alpha 与本地媒体 ingest 达 L5。 |
| C07 | 批量生成、最终剪辑与成片交付 | V1 有批量媒体和互动/分集导出，可作为行为参考 | export pack/manifest 适合可审阅投产交接，但不生成最终视频 | **Defer**，以后基于 Plotloom task/artifact/export contracts 重建 | **D** | 批量队列、取消、全局 timecode、配音/口型、剪辑、QC、最终成片都不计入当前完成度。 |

### D. 平台、工作台与独立发行

| ID | 能力 | Narrative Forge 可取之处 | shuohao-skills 可取之处 | Plotloom 决定 | 成熟度/目标 | 当前证据与下一退出条件 |
|---|---|---|---|---|---|---|
| D01 | SQLite、迁移与并发写入 | 项目文件、原子保存和备份易理解，但缺细粒度事务 | 分层 JSON 易 diff，但依赖操作者管理一致性 | **Rebuild** 为 repository、Alembic、optimistic revision | **L4/L5** | SQLite/WAL/外键、迁移、原子 rollback、startup reconciliation 及跨 repository 并发幂等测试通过；写锁耗尽会返回带 `Retry-After` 的可控 503。仍需安装版数据恢复演练和用户可见备份/导出。 |
| D02 | React 工作台与完整用户旅程 | 浏览器内创作→媒体→预览的单一工作台是核心产品价值 | 分阶段操作和报告适合清晰导航 | **Adapt** 为七页 Plotloom 工作台 | **L4/L5** | 首次非 Brief 保存现以规范阶段前缀原子创建项目，并直接从权威响应 hydrate；单元测试与真实浏览器覆盖成功、失败重试和刷新持久化。仍缺项目选择器、草稿切页保护、友好 422 细节及完整生成/修复旅程。 |
| D03 | Plotloom 导入、导出、备份与可移植项目 | V1 project JSON/备份能带走作品 | 五层 JSON/Markdown/manifest 便于审阅交接 | **Rebuild** Plotloom canonical 格式；**Reject** 首发 legacy migration | **L1/L5** | [初始提取来源](../provenance/initial-extraction.md) 定义 Plotloom-only 数据边界，但 canonical export/import 尚未实现。任何 V1/shuohao 导入只能在未来另立迁移 ADR。 |
| D04 | 无 V1 依赖的提取、打包与新仓库 | V1 只作为比较和行为证据存在 | shuohao 的自包含边界提醒我们保持模块独立，但不复制其规则重复 | **Rebuild** 为单包、单 UI、可移动 roots | **L5/L7** | 全新 Plotloom 仓库、fresh history、依赖边界、独立 wheel/资源探测、生产 bundle 与 CI workflow 已建立；下一退出条件是首次远端 CI、干净安装/升级/卸载与恢复收据。 |
| D05 | E2E、真实供应商与创作质量验证 | V1 有浏览器/媒体/导出行为可作回归样例 | selftest 的击穿 fixture 纪律值得采用 | **Adapt** 为分层验证金字塔 | **L5/L6** | 124 个 Python、33 个前端单元测试及 3 条浏览器→Vite→真实 FastAPI→文件 SQLite 旅程通过；还缺 fake-provider 生成 E2E、授权 live smoke、媒体故障注入和固定故事人工盲评。 |
| D06 | 本地安全与远程部署边界 | loopback、URL 检查、secret-free config 和“远程必须私有”警告应保留 | 不是常驻 Web 服务，不能提供可直接采用的部署边界 | **Adopt local boundary / Defer public multi-user** | **L4/L4**（本地）/ **D**（公开部署） | `.env`、session lease、HTTPS provider root 和 secret rejection 已测；身份认证、TLS、RBAC、多租户和公开服务不在首发范围。未加外部认证的远程实例必须保持私有。 |
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

不保留：用 `sceneIndex` 或 `[start,end]` 数组位置充当身份；exact-once 规则限制安全覆盖；H3 长字符串进入规范主数据；靠操作者手工重跑文件来维持 runtime；重复规则漂移；把未运行的门当作通过。

## 当前优先队列

### P0：先保护现有成果和用户数据

- [x] **建立 Git checkpoint。**Plotloom 可移动 roots、ADR/文档、LICENSE/NOTICE 和必要构建元数据已进入专用分支的可恢复提交；它仍不是发布候选。
- [x] **修复首次 stage 保存丢失。**创建项目与规范阶段前缀在同一事务中完成，客户端从创建响应直接 hydrate。
- [x] 给上述路径增加真实 React + FastAPI E2E，并覆盖失败后保留草稿与同键重试。

### P1：完成可用本地 Alpha

- [ ] 项目 list/create/switch/archive/delete/duplicate 和空白新建引导。
- [ ] 切页/刷新前未保存草稿提示与恢复策略。
- [ ] StoryBible、Graph、SceneBeatPlan、Storyboard 全合同字段的可理解编辑；包括节点/场次/镜头增删重排和 ShotBeatLink。
- [ ] 提供无 Key 的“从样例新建/本地模板”入口，让 bootstrap 与 E2E 不依赖付费供应商。
- [ ] 解析 FastAPI 422 结构，显示字段路径和可行动错误。
- [ ] 刷新后恢复生成 run 与 media task 的浏览器观察轮询。
- [ ] 完成隔离→修复→重建→刷新复核的浏览器旅程。

### P2：证明真实生产闭环

- [ ] 在用户明确授权并设置小额预算后，分别做文本、图像、视频真实 provider smoke；保存脱敏请求能力、任务 ID、状态和产物收据。
- [ ] 将成功媒体下载到 ArtifactStore，验证协议、重定向、IP、MIME、大小、哈希和路径；UI 优先使用本地 artifact URL。
- [ ] 实现 Plotloom canonical export/import、备份和恢复演练。
- [ ] 决定并实现最小互动预览/可播放导出；批量/最终剪辑仍可留到后续。
- [ ] 建立固定故事的人工 eval：叙事清楚度、空间/人物连续性、表演可读、节奏与修改成本。

### P3：真正独立发行

- [x] 创建全新 Plotloom 仓库，只迁移 [初始提取来源](../provenance/initial-extraction.md) 声明的 roots 和 Plotloom 决策；不带任何 V1 runtime。
- [ ] 在远端 CI 中执行 Python、前端、边界、提取、打包、安装 smoke 和浏览器回归；workflow 已建立，等待首次运行收据。
- [ ] 验证干净机器安装、升级、数据目录、`.env` 边界、端口回退、备份恢复和卸载保留数据策略。
- [ ] 复核 LICENSE、NOTICE、文件级来源和发布包内容，签发 L7 收据。

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
