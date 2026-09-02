import { readFile, readdir, writeFile } from "node:fs/promises";
import { dirname, extname, join, parse, relative } from "node:path";
import { fileURLToPath } from "node:url";

const handbookRoot = dirname(fileURLToPath(import.meta.url));
const chaptersRoot = join(handbookRoot, "src", "chapters");
const outputPath = join(handbookRoot, "index.html");
const chapterCollator = new Intl.Collator("zh-Hans-CN", {
  numeric: true,
  sensitivity: "base",
});

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function decodeAttribute(value) {
  const namedEntities = {
    amp: "&",
    apos: "'",
    gt: ">",
    lt: "<",
    quot: '"',
  };

  return value.replace(
    /&(#(?:x[0-9a-f]+|\d+)|amp|apos|gt|lt|quot);/gi,
    (entity, body) => {
      if (body.startsWith("#x") || body.startsWith("#X")) {
        return String.fromCodePoint(Number.parseInt(body.slice(2), 16));
      }
      if (body.startsWith("#")) {
        return String.fromCodePoint(Number.parseInt(body.slice(1), 10));
      }
      return namedEntities[body.toLowerCase()];
    },
  );
}

function readAttribute(attributes, attributeName) {
  const pattern = new RegExp(
    `(?:^|\\s)${attributeName}\\s*=\\s*(?:"([^"]*)"|'([^']*)')`,
    "i",
  );
  const match = attributes.match(pattern);
  return match ? decodeAttribute(match[1] ?? match[2]) : null;
}

function chapterSlug(fileName) {
  const baseName = parse(fileName).name
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
  return `chapter-${baseName || "untitled"}`;
}

function enrichChapter(source, fileName, index) {
  const openingTag = source.match(/<article\b([^>]*)>/i);
  if (!openingTag) {
    throw new Error(`${fileName}: 根元素必须是 <article>。`);
  }
  if (!/<\/article>\s*$/i.test(source.trim())) {
    throw new Error(`${fileName}: 章节必须以 </article> 结束。`);
  }

  const attributes = openingTag[1];
  const title = readAttribute(attributes, "data-title");
  const kicker = readAttribute(attributes, "data-kicker");
  if (!title || !kicker) {
    throw new Error(`${fileName}: <article> 必须同时提供 data-title 和 data-kicker。`);
  }

  const sourceId = readAttribute(attributes, "id");
  const id = sourceId || chapterSlug(fileName);
  const extraAttributes = [
    sourceId ? "" : ` id="${escapeHtml(id)}"`,
    /(?:^|\s)tabindex\s*=/i.test(attributes) ? "" : ' tabindex="-1"',
    /(?:^|\s)aria-(?:label|labelledby)\s*=/i.test(attributes)
      ? ""
      : ` aria-label="${escapeHtml(title)}"`,
    ` data-chapter-index="${index + 1}"`,
  ].join("");

  const html = source.replace(
    openingTag[0],
    `<article${attributes}${extraAttributes}>`,
  );

  return { fileName, html, id, kicker, title };
}

function chapterPager(chapters, index) {
  const previous = chapters[index - 1];
  const next = chapters[index + 1];
  const previousLink = previous
    ? `<a class="pager-link pager-link--previous" href="#${escapeHtml(previous.id)}">
        <span aria-hidden="true">←</span>
        <span><small>上一章</small>${escapeHtml(previous.title)}</span>
      </a>`
    : '<span class="pager-spacer" aria-hidden="true"></span>';
  const nextLink = next
    ? `<a class="pager-link pager-link--next" href="#${escapeHtml(next.id)}">
        <span><small>下一章</small>${escapeHtml(next.title)}</span>
        <span aria-hidden="true">→</span>
      </a>`
    : '<a class="pager-link pager-link--next" href="#page-top"><span><small>读完了</small>返回封面</span><span aria-hidden="true">↑</span></a>';

  return `<nav class="chapter-pager" aria-label="章节翻页">${previousLink}${nextLink}</nav>`;
}

function renderEmptyState() {
  return `<article id="chapter-empty" class="chapter-empty" tabindex="-1">
    <p class="chapter-kicker">构建提示</p>
    <h1>章节内容尚未加入</h1>
    <p>在 <code>src/chapters/</code> 中加入符合约定的 HTML 章节片段，再重新运行构建器。</p>
  </article>`;
}

function renderDocument(chapters) {
  const toc = chapters.length
    ? chapters
        .map(
          (chapter, index) => `<li>
            <a href="#${escapeHtml(chapter.id)}" data-chapter-link="${escapeHtml(chapter.id)}">
              <span class="toc-number">${String(index + 1).padStart(2, "0")}</span>
              <span class="toc-copy"><small>${escapeHtml(chapter.kicker)}</small>${escapeHtml(chapter.title)}</span>
            </a>
          </li>`,
        )
        .join("\n")
    : '<li class="toc-empty">等待章节源文件</li>';

  const body = chapters.length
    ? chapters
        .map(
          (chapter, index) => `${chapter.html}\n${chapterPager(chapters, index)}`,
        )
        .join("\n")
    : renderEmptyState();

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="theme-color" content="#f1b949">
  <meta name="description" content="从粗梗概到分镜投产：通用方法、Narrative Forge 与 shuohao-skills 源码解剖。">
  <title>从梗概到分镜｜实用手册</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='3' fill='%23e8aa2f'/%3E%3Ctext x='16' y='23' text-anchor='middle' font-size='21'%3E%E5%88%86%3C/text%3E%3C/svg%3E">
  <link rel="stylesheet" href="assets/handbook.css">
  <link rel="stylesheet" href="assets/mobile-pdf.css" media="print">
  <script src="assets/handbook.js" defer></script>
</head>
<body id="page-top">
  <a class="skip-link" href="#handbook-content">跳到正文</a>
  <div class="reading-progress" aria-hidden="true"><span></span></div>
  <header class="site-header">
    <button class="toc-toggle" type="button" aria-expanded="false" aria-controls="handbook-toc">
      <span aria-hidden="true">☰</span><span>目录</span>
    </button>
    <a class="wordmark" href="#page-top" aria-label="返回手册封面">
      <span class="wordmark-mark" aria-hidden="true">分</span>
      <span><strong>从梗概到分镜</strong><small>创作逻辑 · 源码解剖 · 系统重构</small></span>
    </a>
    <div class="progress-copy" role="progressbar" aria-label="阅读进度" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
      <span class="progress-chapter">封面</span><strong>0%</strong>
    </div>
  </header>

  <div class="handbook-shell">
    <aside class="toc-panel" id="handbook-toc" aria-label="手册目录">
      <div class="toc-heading">
        <p>实践型电子手册</p>
        <h2>章节目录</h2>
      </div>
      <nav aria-label="章节">
        <ol>${toc}</ol>
      </nav>
      <div class="toc-meta">
        <p><span class="pencil-swatch" aria-hidden="true"></span>草图为主，完成帧为辅</p>
        <a href="SOURCES.md">来源与证据</a>
        <a href="THIRD_PARTY_NOTICES.md">第三方声明</a>
        <a href="assets/storyboards/PROMPTS.md">插图生成记录</a>
      </div>
    </aside>
    <button class="toc-scrim" type="button" aria-label="关闭目录" tabindex="-1"></button>

    <main id="handbook-content" class="handbook-content">
      <section class="book-cover" aria-labelledby="book-title">
        <div class="cover-copy">
          <p class="eyebrow">Storyboard Systems Handbook</p>
          <h1 id="book-title">从梗概<br>到<span>分镜</span></h1>
          <p class="cover-deck">理解故事如何经过场、节拍、镜头和关键帧，最终成为可编程、可校验、可投产的视觉叙事系统。</p>
          <dl class="cover-facts">
            <div><dt>方法</dt><dd>通用影视基础</dd></div>
            <div><dt>解剖</dt><dd>Narrative Forge</dd></div>
            <div><dt>对照</dt><dd>shuohao-skills</dd></div>
            <div><dt>范围</dt><dd>11 章完整学习版</dd></div>
          </dl>
        </div>
        <div class="cover-sketch" aria-hidden="true">
          <div class="sketch-frame sketch-frame--wide"><span>ESTABLISHING</span><i></i></div>
          <div class="sketch-row">
            <div class="sketch-frame"><span>REACTION</span><i></i></div>
            <div class="sketch-frame sketch-frame--accent"><span>DETAIL</span><i></i></div>
          </div>
          <p>SCENE → BEAT → SHOT → FRAME</p>
        </div>
      </section>

      <section class="reading-key" aria-labelledby="reading-key-title">
        <div>
          <p class="chapter-kicker">阅读方法</p>
          <h2 id="reading-key-title">事实、判断与建议分开阅读</h2>
        </div>
        <p>正文用证据标签区分仓库声明、代码实现、测试约束、实际验证和作者推论。点击左侧目录跳转；按 <kbd>Alt</kbd> + <kbd>←</kbd>/<kbd>→</kbd> 切换章节。</p>
      </section>

      ${body}

      <footer class="site-footer">
        <p>本手册基于固定版本的只读源码审计制作。方法性结论与第三方项目声明分别标注。</p>
        <nav aria-label="文档治理">
          <a href="SOURCES.md">来源与证据等级</a>
          <a href="THIRD_PARTY_NOTICES.md">第三方声明</a>
          <a href="assets/storyboards/PROMPTS.md">插图生成记录</a>
          <a href="#page-top">返回顶部 ↑</a>
        </nav>
      </footer>
    </main>
  </div>
</body>
</html>`;
}

async function loadChapters() {
  const entries = await readdir(chaptersRoot, { withFileTypes: true });
  const chapterFiles = entries
    .filter((entry) => entry.isFile() && extname(entry.name).toLowerCase() === ".html")
    .map((entry) => entry.name)
    .sort(chapterCollator.compare);

  const chapters = [];
  const seenIds = new Set();
  for (const [index, fileName] of chapterFiles.entries()) {
    const source = await readFile(join(chaptersRoot, fileName), "utf8");
    const chapter = enrichChapter(source, fileName, index);
    if (seenIds.has(chapter.id)) {
      throw new Error(`${fileName}: 章节 id “${chapter.id}” 重复。`);
    }
    seenIds.add(chapter.id);
    chapters.push(chapter);
  }
  return chapters;
}

const chapters = await loadChapters();
await writeFile(outputPath, renderDocument(chapters), "utf8");

const relativeOutput = relative(process.cwd(), outputPath) || outputPath;
process.stdout.write(
  `Built ${relativeOutput} from ${chapters.length} chapter${chapters.length === 1 ? "" : "s"}.\n`,
);
