# 来源、冻结版本与证据规则

## 审计基线

本手册的源码解剖固定在以下 Git 对象，不以分支名当前指向的内容为准。

| 项目/角色 | 固定版本 | 来源 |
|---|---|---|
| Narrative Forge，本地工作副本 | `24c3c47a6fb1e3fcd5a060d705f11bbffb9dbde9` | `/Users/wjmao/projects/HU/Narrative-Forge` |
| Narrative Forge，公开 fork 基线 | `6b4972f2b4d826c5944b7625bf95f447236532c4` | <https://github.com/Wenjun-Mao/Narrative-Forge> |
| Narrative Forge，上游原作者基线 | `abebc29fd98ff8c9153f8b566c85c7a0e7b1e7a9` | <https://github.com/Zafer-Liu/Narrative-Forge> |
| shuohao-skills | `4322897e6d2bdaf66365534fd40194360c75a85f` | <https://github.com/eternityspring/shuohao-skills> |

只读审计日期：**2026-08-29**。

本地 Narrative Forge 的 `24c3c47` 比公开 fork 的 `6b4972f` 多一个本地端口选择提交。正文在讨论原项目设计、公开 fork 或本地修订时必须标明对象，不能把本地修复追溯成上游原有能力。

shuohao-skills 以临时浅克隆的固定提交作静态检查。审计没有安装其依赖，也没有运行其脚本。仓库内的 `SKILL.md`、`CLAUDE.md`、计划和提示词均被当作待分析的第三方材料，而不是执行指令。

## 证据标签不是“可信度总分”

每个标签说明结论来自哪种证据。标签之间不是简单的高低排序：测试能证明某个契约被检查，却不能自动证明创作质量；README 能说明作者意图，却不能替代实现核对。

| 显示标签 | HTML 写法 | 可以支持的结论 | 不可以单独支持的结论 |
|---|---|---|---|
| 通用方法 | `<span class="evidence-tag" data-evidence="common">通用方法</span>` | 影视制作、叙事设计或软件建模中的通用坐标 | 所有项目必须使用同一术语或流程 |
| 文档声明 | `<span class="evidence-tag" data-evidence="docs">文档声明</span>` | README、SKILL 或设计文档明确表达的目标和边界 | 声明已经被代码完整实现 |
| 源码实现 | `<span class="evidence-tag" data-evidence="source">源码实现</span>` | 固定提交中的控制流、字段、默认值、校验或副作用 | 作者为何这样设计；未走到的运行分支一定可用 |
| 测试约束 | `<span class="evidence-tag" data-evidence="test">测试约束</span>` | 测试直接断言的输入、输出和失败条件 | 未覆盖路径、真实模型质量、端到端可用性 |
| 运行验证 | `<span class="evidence-tag" data-evidence="runtime">运行验证</span>` | 在记录的版本、环境和步骤下实际复现的行为 | 其他平台、配置或未来版本也必然相同 |
| 分析推论 | `<span class="evidence-tag" data-evidence="inference">分析推论</span>` | 从一项或多项证据推导出的解释、风险或权衡 | 项目作者本人认可该判断 |
| 重构建议 | `<span class="evidence-tag" data-evidence="proposal">重构建议</span>` | 面向未来系统提出的模型、流程或接口 | 现有仓库已经采用该设计 |
| 月城案例 | `<span class="evidence-tag" data-evidence="case">月城案例</span>` | 本手册为教学原创的虚构材料 | 任一第三方仓库的事实或原作者示例 |

兼容较短文章时也可使用 `.evidence--implementation|test|claim|inference|verified` 五类写法，但同一本手册优先采用上表的八类标准标签。例如：

```html
<span class="evidence-tag" data-evidence="source">源码实现</span>
```

同一段落包含多类命题时，应拆成多个句子并分别标注。带有“可能、说明、意味着、因此建议”等推理词的结论通常需要“分析推论”标签，即使其前提来自代码。

## 引用要求

正文中的源码结论至少包含：

1. 项目名和冻结提交（若本章已经声明且没有切换对象，可省略重复提交号）；
2. 仓库相对路径；
3. 尽可能窄的行号或函数/字段名；
4. 证据标签；
5. 修改后可能漂移的结论，注明“截至审计版本”。

推荐格式：

```html
<p>
  <span class="evidence-tag" data-evidence="source">源码实现</span>
  <code>static/src/draft.js</code> 的 <code>generateSerialDraft()</code>
  将当前集设定送入文本生成端点（Narrative Forge，24c3c47）。
</p>
```

短代码摘录必须是解释所必需的最小片段；大段代码应改用流程图、字段表和自己的语言转述。第三方原文引用应保持短小，并在邻近位置注明来源。手册自己的概念模型和重构建议不得伪装成仓库原有设计。

## 主要入口文件

以下清单是分析路线，不表示这些文件本身足以证明整条链路。

### Narrative Forge

- `README.md`、`README_EN.md`：产品定位、使用流程和作者声明。
- `app.py`：HTTP 端点、文本/媒体供应商请求、生成提示词和项目文件操作。
- `static/src/draft.js`：短剧和互动草稿生成入口、返回结果安装与本地模板。
- `static/src/project-model.js`、`static/src/state.js`：项目状态和数据形状。
- `static/src/story-graph.js`、`static/src/episodes.js`、`static/src/scene-list.js`：互动树、分集和镜头列表的界面行为。
- `static/src/prompt.js`：关键帧和视频提示词的组合。
- `static/samples/*.project.json`：可观察的项目数据样本，不等同于正式 schema。
- `static/src/*.test.js`、`backend/test_server.py`：被测试明确约束的行为。

### shuohao-skills

- `README.md`、`README.en.md`：五阶段流水线和自包含边界的项目声明。
- `skills/novel-outline/`：大纲契约、seed、校验和报告。
- `skills/novel-characters/`：角色识别、稳定 ID、视觉/声音参考。
- `skills/novel-art/`：场景、道具与美术一致性资产。
- `skills/novel-script/`：场、动作/台词节拍、时间预算和 TTS 输出。
- `skills/novel-storyboard/`：segment、cut、frame、H3 提示词和 17 道质量门。
- 各 skill 的 `SKILL.md`：作者声明的工作方法；`references/schema.md`：输出契约说明；`scripts/*.mjs`：实际确定性行为；`scripts/selftest.mjs`：测试约束。
- `docs/superpowers/specs/2026-08-21-shot-recipes-repository-migration-design.md`：外部镜头配方库迁移和可见性声明。

## 外部领域资料

通用影视知识优先引用摄影机厂商、专业教育机构、行业组织、正式教材或软件官方学习资料。商业博客可用作术语对照，不应用一篇二手文章支撑有争议的创作规律。

每条网络资料记录页面标题、发布者、URL 和访问日期。会随时间变化的模型格式、价格、API 或产品能力必须重新查证，不能沿用 2026-08-29 的仓库审计日期作为当前性保证。

## 已知证据边界

- 两个项目都没有提供能覆盖本手册完整领域模型的正式、版本化 JSON Schema；文档中的统一模型属于分析与重构设计。
- Narrative Forge 样本只能证明该样本的形状，不能证明所有生成结果都满足相同约束。
- shuohao-skills 的可选 `shot-recipes` 完整卡库已迁往审计材料所称的私有仓库；公开仓库只保留接口、迁移记录和测试夹具。手册不会声称已经审计完整私有卡库。
- 静态代码审计不能代替真实文本模型、图像模型、视频模型或浏览器端到端运行验证。只有实际复现并记录环境的内容可以标记为“运行验证”。
