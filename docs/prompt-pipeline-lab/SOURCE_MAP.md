# 源码证据地图

审计基线：`24c3c47a6fb1e3fcd5a060d705f11bbffb9dbde9`（2026-08-28）。

| 主题 | 文件与行号 | 手册采用的事实 |
|---|---|---|
| 首次启动与默认项目 | `static/src/main.js:20-49` | 无本地项目时读取当前表单，创建空的互动容器；随后应用项目、绑定事件和渲染。 |
| 页面默认值 | `static/index.html:62-180` | 片名、梗概、类型、画幅、视觉风格、树深度、分支数、每节点分镜数和模型均有 DOM 默认值。 |
| 表单读取契约 | `static/src/project-model.js:219-238` | 生成前以当前 DOM 为准，形成 `meta`；供应商配置不属于项目元数据。 |
| 项目恢复优先级 | `static/src/project-model.js:321-336` | 已保存项目来自 `localStorage`，会覆盖初始页面默认值。 |
| 生成按钮 | `static/src/events.js:33-38` | 文本模型与本地模板是两个独立入口。 |
| 互动请求前检查 | `static/src/draft.js:24-46` | 梗概必填；树规模和分镜规模有上限。 |
| 本地模板 | `static/src/draft.js:146-264` | 本地模板不调用 LLM，直接创建镜头并合成媒体提示词。 |
| 互动前端请求 | `static/src/draft.js:488-525` | 前端只发送结构化项目字段到 `/api/generate-story`。 |
| 互动后端 prompt | `app.py:481-543` | 后端校验规模、构造 `story`、拼接 system/user prompt，并设定温度、token 上限与非流式调用。 |
| 互动返回示例瑕疵 | `app.py:523-527` | prompt 示例把 `"shotsInNode":shots_per_node` 写成未加引号的 literal，因此示例自身不是合法 JSON；页面组装器按源码保留这一事实。 |
| 短剧前端 prompt | `static/src/draft.js:302-403` | 前端拼接项目级、本集、前后集、JSON 结构和九项约束。 |
| 短剧后端包装 | `app.py:1081-1101` | 后端添加固定 system prompt，保留前端 prompt 为 user 消息。 |
| 文本供应商调用 | `app.py:198-328` | Chat Completions 请求使用 Bearer 鉴权、超时、错误分类和受控重试。 |
| API Key 优先级 | `app.py:448-457` | 请求体的会话密钥优先，否则回退到专用环境变量，再回退 Atlas key。 |
| 响应清洗与 JSON 解析 | `static/src/utils.js:85-123` | 读取 `choices[0].message.content`，去除 `<think>`、代码围栏，提取首个平衡 JSON 对象，再 `JSON.parse`。 |
| 互动导入 | `static/src/draft.js:577-650` | 校验数组、数量上限、key 与 target；白名单化镜别/时长，映射内部 ID，补合成提示词并渲染。 |
| 短剧导入 | `static/src/draft.js:413-482` | 规范镜头字段、调整对白时长、映射 nextKey，建立连续性并渲染。 |
| 镜头默认对象 | `static/src/project-model.js:421-435` | 内部 scene 还包含媒体状态、引用镜头、连续性、角色/场景关联等非 LLM 字段。 |
| 角色/场景自动关联 | `static/src/project-model.js:126-151` | 以镜头标题、动作、对白中的名称匹配卡片，单卡时可自动回退。 |
| 图像与视频提示词 | `static/src/prompt.js:52-175` | 分镜导入后由前端确定性合成角色连续性、场景连续性、关键帧和动态提示词。 |
| 分镜列表渲染 | `static/src/scene-list.js:20-84` | UI 读取规范化后的项目 scene，不直接渲染模型原始 JSON。 |
| 项目持久化边界 | `static/src/project-model.js:321-324` | 保存的是规范化项目状态；完整 messages、供应商 envelope、assistant 原文、解析报告和临时 key→ID 映射没有成为项目字段。 |
| 后端契约测试 | `backend/test_server.py:303-317,904-940` | 测试覆盖互动 payload 基本参数、Chat Completions 路由和短剧 prompt 透传。 |

## 已知边界

1. 内置 `star-sea-echo.project.json` 是保存后的项目样例，但仓库没有保存它当时对应的文本模型原始响应，因此不能用它反推某次完整 LLM 对话。
2. 用户截图可以证明界面显示了七个分镜及其标签，但不能证明这些标题来自哪个 prompt、模型或版本。本文采用的附件逻辑名为 `codex-clipboard-66fdec39-d209-457e-8b82-1f7ac1a8be98.png`，SHA-256 为 `c9dba7ef50d94224c189e50a0f1805a4c0a8e0207ebd9e263cab92944d270223`；仓库只保留文字转述，不把该临时附件冒充运行记录。
3. `parseStoryJson()` 做清洗和首次 JSON 对象提取，但没有自动修复畸形 JSON，也没有通用 JSON Schema 校验器。
4. 互动导入会提示实际镜头数与期望值不一致，但并不因“不完全相等”自动拒绝；短剧导入也没有强制等于 prompt 中请求的镜头数。
5. 在互动模式且“每剧情节点分镜数”大于 1 时，二次确认文案中的 `totalShots` 会再次乘以该值；请求 payload 与最终导入仍使用第一次计算的 `nodeCount`。这是展示层计数问题，不是后端 prompt 的规模值。
6. 页面中的响应 envelope、七节点 JSON、内部 `scene_docs_*` ID 和六节点宽松接受案例都是明确标注的教学构造，用来执行冻结源码的解析/安装规则；它们不是已捕获的供应商原始响应。
7. 互动与短剧的 user prompt 所有权不同：前者在 `app.py` 形成，后者在浏览器 `draft.js` 形成。后端短剧端点仍负责校验传输字段、补 system message、设置模型参数并调用供应商，所以“透传 user prompt”不等于“后端没有其他逻辑”。
8. 当前项目没有保存可完整复盘一次文本模型运行的 provenance。手册中的“信息损失漏斗”是由保存字段与调用链对照得到的分析结论，不是仓库作者声明。
