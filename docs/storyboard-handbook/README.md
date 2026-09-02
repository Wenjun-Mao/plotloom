# 《从梗概到分镜》网页手册

这是一本以屏幕阅读为目标的实践型电子手册。它同时解释通用分镜方法，并以固定版本的 Narrative Forge 与 shuohao-skills 为实例，追踪“粗梗概 → 结构 → 场 → 节拍 → 镜头 → 关键帧 → 生成任务”的完整数据链。

当前目录是手册的**完整学习版**，共 11 章，分成五组：

1. 阅读地图与共同基础：建立证据标签、叙事／导演／生产三层坐标，以及从粗梗概到投产包的完整交接链。
2. “月城控制室”贯穿案例：把一场戏实际拆成节拍、镜头、故事板、连续性账本，并分别映射到两套系统。
3. 两个仓库的独立解剖：Narrative Forge 的浏览器应用、项目状态、线性／互动工作流与供应商调用；shuohao-skills 的五阶段接力、agent／确定性脚本分工和 storyboard 的 17 道质量门。
4. 比较与重构：逐层比较两套系统，提出供应商无关的统一领域模型，并给出从局部适配到完全重写的实施路线。
5. 随身参考：用四遍阅读法、产物验收阶梯、跨系统术语表和十二问审计卡，把整本手册压成可反复查询的工作方法。

这里的“完整”指上述学习范围已经全部写入，并不表示两个第三方仓库已经拥有手册建议的统一模型，也不表示未公开的资料或真实模型调用已经经过运行验证；这些证据边界会在正文与 `SOURCES.md` 中持续明示。

## Narrative Forge 提示词专题

若要继续追踪 Narrative Forge 怎样把“页面默认值或用户输入”编译成 system/user prompt，并将 Chat Completions 响应清洗、安装和渲染为“分镜列表”，请打开独立的交互式专题：[《从输入到分镜列表：Prompt Pipeline Lab》](../prompt-pipeline-lab/index.html)。它与本手册共享审计方法，但不占用原有 11 章结构。

本目录只包含静态 HTML、CSS、JavaScript 和一个零依赖构建器。运行手册构建不需要 `npm install`，也不会执行两个被分析项目中的脚本。

## 构建与阅读

需要 Node.js 18 或更高版本：

```sh
node docs/storyboard-handbook/build.mjs
```

构建器按文件名的自然顺序读取 `src/chapters/*.html`，并生成 `index.html`。随后可直接双击 `index.html`，或用浏览器打开它的 `file://` 地址；不需要启动 Narrative Forge 后端。

`index.html` 是生成文件。正文修改应发生在章节片段中，再重新构建，不应直接编辑生成文件。

## iPhone 阅读版

`dist/` 中提供两种手机阅读格式：

- `从梗概到分镜-手机阅读版.epub`：推荐在 iPhone 的“图书”App 中阅读；文字可重排，也可调整字号、主题和滚动方式。
- `从梗概到分镜-手机阅读版.pdf`：固定为 6 × 9 英寸页面，适合保留表格、流程图和故事板的确定版面。

EPUB 与网页共享同一组章节源。重新构建时运行：

```sh
node docs/storyboard-handbook/build-epub.mjs
```

构建器会生成 EPUB 3、检查 ZIP 容器，并在本机安装了 EPUBCheck 时执行规范校验。PDF 使用 `index.html` 和 `assets/mobile-pdf.css` 的打印版式生成；先运行网页构建，再用 Chromium 打印为 PDF，并启用背景图形与 CSS 页面尺寸。

传到 iPhone 时，可以将文件放入 iCloud Drive 或通过 AirDrop 发送；在 iPhone 上点“共享”后选择“图书”即可加入书库。

## 章节片段契约

每个章节文件必须满足以下最小结构：

```html
<article data-kicker="第一部分 · 通用基础" data-title="分镜列表究竟是什么">
  <p class="chapter-kicker">第一章</p>
  <h1>分镜列表究竟是什么</h1>
  <p class="chapter-lede">本章的导读。</p>
  <!-- 本章正文 -->
</article>
```

规则如下：

1. 根元素必须是 `<article>`，文件必须以 `</article>` 结束。
2. `data-title` 和 `data-kicker` 都是必填项；构建器用它们生成目录和当前章节提示。
3. 文件名决定章节顺序，推荐使用 `01-...html`、`02-...html` 的形式。
4. 构建器会根据文件名生成章节 `id`；确有需要时可在 `<article>` 上显式提供唯一的 `id`。
5. 每章使用一个一级标题。后续层级按 `h2 → h3 → h4` 顺序组织，不跳级。

构建器会在缺失必要元数据、缺少闭合标签或章节 `id` 重复时失败，而不是生成无法导航的页面。章节目录为空时会生成一个明确的占位页，便于先独立验证站点外壳。

## 可复用的视觉结构

样式表为正文预留了以下语义类：

- `.chapter-kicker`、`.chapter-lede`：章节编号/分部和导读。
- `.evidence-tag[data-evidence="common|docs|source|test|runtime|inference|proposal|case"]`：通用方法、项目文档、源码、测试、运行验证、分析推论、重构建议和原创案例标签。
- `.evidence` 加 `.evidence--implementation|test|claim|inference|verified`：兼容较短文章使用的五类证据标签写法。
- `.callout`、`.note`、`.warning`、`.principle`：说明、警告和核心原则。
- `.table-wrap`：普通宽表格的横向滚动容器；`.table-scroll`：需要键盘聚焦并横向滚动的宽表格区域。
- `.storyboard-grid`、`.storyboard-panel`、`.panel-sketch`：以铅笔草图为主的故事板网格。
- `.finished-frame`：少量彩色完成帧，不自动应用灰度滤镜。
- `.comparison-grid`、`.comparison-card`：两套实现或两种工作流的对照。
- `.pipeline-grid`、`.pipeline-step`：小型流程图。

图片必须有准确的 `alt`；纯装饰图使用空的 `alt`。表格应有 `<caption>`，并按交互需要包在 `.table-wrap` 或带可访问名称的 `.table-scroll` 中。链接文字应描述目标，不使用孤立的“点击这里”。

## 交互与无障碍

生成页面包含跳到正文链接、语义化目录、当前位置、阅读进度和章节前后导航。窄屏目录以按钮打开，`Escape` 可关闭。`Alt + ←` 与 `Alt + →` 可切换章节。关闭 JavaScript 后正文和普通锚点导航仍然可读。

视觉采用纸张、石墨和小面积暖黄色，故事板草图是主要图像语言；彩色只用于完成帧或少量状态强调。它不是 Narrative Forge 产品界面的仿制品。

## 来源治理

- [SOURCES.md](SOURCES.md) 冻结审计版本、定义证据标签和引用规则。
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 记录第三方许可证、NOTICE 和已知资料缺口。
- [assets/storyboards/PROMPTS.md](assets/storyboards/PROMPTS.md) 记录原创故事板与彩色完成帧所用的内置图像生成模式、最终提示词和连续性修订提示词。

凡是“项目自己声称什么”“代码实际做了什么”“测试约束了什么”“作者据此做出的判断”，均应在正文中明确分开。未获得的私有资料不得由公开接口或文件名反推并写成既成事实。
