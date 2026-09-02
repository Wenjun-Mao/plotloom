import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  access,
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, dirname, extname, join, parse, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

const handbookRoot = dirname(fileURLToPath(import.meta.url));
const chaptersRoot = join(handbookRoot, "src", "chapters");
const imagesRoot = join(handbookRoot, "assets", "storyboards");
const epubCssPath = join(handbookRoot, "assets", "epub.css");
const distRoot = join(handbookRoot, "dist");
const outputPath = join(distRoot, "从梗概到分镜-手机阅读版.epub");
const chapterCollator = new Intl.Collator("zh-Hans-CN", {
  numeric: true,
  sensitivity: "base",
});

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function chapterSlug(fileName) {
  return parse(fileName).name
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
}

function xhtmlDocument(title, body, extraHead = "") {
  return `<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN" lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>${escapeXml(title)}</title>
  <link rel="stylesheet" type="text/css" href="../styles/epub.css" />
  ${extraHead}
</head>
<body>${body}</body>
</html>`;
}

async function loadChapters() {
  const entries = await readdir(chaptersRoot, { withFileTypes: true });
  const files = entries
    .filter((entry) => entry.isFile() && extname(entry.name).toLowerCase() === ".html")
    .map((entry) => entry.name)
    .sort(chapterCollator.compare);

  const chapters = [];
  const idToChapter = new Map();
  for (const [index, fileName] of files.entries()) {
    const source = await readFile(join(chaptersRoot, fileName), "utf8");
    const dom = new JSDOM(source);
    const article = dom.window.document.querySelector("article");
    if (!article) throw new Error(`${fileName}: 缺少 article 根元素。`);
    const title = article.getAttribute("data-title")?.trim();
    const kicker = article.getAttribute("data-kicker")?.trim();
    if (!title || !kicker) throw new Error(`${fileName}: 缺少 data-title 或 data-kicker。`);
    const slug = chapterSlug(fileName);
    const outputFile = `${slug}.xhtml`;
    const chapter = { article, dom, fileName, index, kicker, outputFile, source, title };
    chapters.push(chapter);
    for (const element of article.querySelectorAll("[id]")) {
      const id = element.id;
      if (idToChapter.has(id)) throw new Error(`${fileName}: EPUB 全局 id 重复 ${id}。`);
      idToChapter.set(id, outputFile);
    }
  }
  return { chapters, idToChapter };
}

function rewriteChapter(chapter, idToChapter) {
  const { article, dom, outputFile } = chapter;
  article.removeAttribute("tabindex");
  article.setAttribute("epub:type", "chapter");

  for (const image of article.querySelectorAll("img[src]")) {
    const imageName = basename(image.getAttribute("src"));
    image.setAttribute("src", `../images/${imageName}`);
    image.removeAttribute("loading");
  }

  for (const link of article.querySelectorAll("a[href]")) {
    const href = link.getAttribute("href");
    if (!href?.startsWith("#")) continue;
    const targetId = href.slice(1);
    const targetChapter = idToChapter.get(targetId);
    if (!targetChapter) throw new Error(`${chapter.fileName}: 锚点目标不存在 ${href}。`);
    if (targetChapter !== outputFile) link.setAttribute("href", `${targetChapter}${href}`);
  }

  const serializer = new dom.window.XMLSerializer();
  return serializer.serializeToString(article);
}

function mediaType(fileName) {
  if (fileName.endsWith(".png")) return "image/png";
  if (fileName.endsWith(".jpg") || fileName.endsWith(".jpeg")) return "image/jpeg";
  throw new Error(`不支持的 EPUB 图片类型: ${fileName}`);
}

async function latestSourceTimestamp(files) {
  const stats = await Promise.all(files.map((file) => stat(file)));
  const latest = new Date(Math.max(...stats.map((entry) => entry.mtimeMs)));
  return latest.toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function main() {
  const { chapters, idToChapter } = await loadChapters();
  const epubCss = await readFile(epubCssPath, "utf8");
  const imageFiles = (await readdir(imagesRoot))
    .filter((fileName) => /\.(?:png|jpe?g)$/i.test(fileName))
    .sort(chapterCollator.compare);
  if (!imageFiles.includes("moon-control-room-finished-frame.png")) {
    throw new Error("EPUB 封面图不存在。");
  }

  const contentHash = createHash("sha256");
  for (const chapter of chapters) contentHash.update(chapter.source);
  contentHash.update(epubCss);
  for (const imageFile of imageFiles) contentHash.update(await readFile(join(imagesRoot, imageFile)));
  const identifier = `urn:sha256:${contentHash.digest("hex")}`;
  const modified = await latestSourceTimestamp([
    epubCssPath,
    ...chapters.map((chapter) => join(chaptersRoot, chapter.fileName)),
    ...imageFiles.map((fileName) => join(imagesRoot, fileName)),
  ]);

  await mkdir(distRoot, { recursive: true });
  const tempRoot = await mkdtemp(join(tmpdir(), "storyboard-handbook-epub-"));
  const metaInfRoot = join(tempRoot, "META-INF");
  const epubRoot = join(tempRoot, "EPUB");
  const textRoot = join(epubRoot, "text");
  const stylesRoot = join(epubRoot, "styles");
  const epubImagesRoot = join(epubRoot, "images");

  try {
    await Promise.all([
      mkdir(metaInfRoot, { recursive: true }),
      mkdir(textRoot, { recursive: true }),
      mkdir(stylesRoot, { recursive: true }),
      mkdir(epubImagesRoot, { recursive: true }),
    ]);
    await writeFile(join(tempRoot, "mimetype"), "application/epub+zip", "utf8");
    await writeFile(
      join(metaInfRoot, "container.xml"),
      `<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml" />
  </rootfiles>
</container>`,
      "utf8",
    );
    await writeFile(join(stylesRoot, "epub.css"), epubCss, "utf8");
    for (const imageFile of imageFiles) {
      await copyFile(join(imagesRoot, imageFile), join(epubImagesRoot, imageFile));
    }

    const coverBody = `<section epub:type="cover" class="epub-cover">
  <p class="eyebrow">分镜系统实用手册</p>
  <h1>从梗概到分镜</h1>
  <p class="chapter-deck">创作逻辑 · 源码解剖 · 系统重构</p>
  <figure class="finished-frame">
    <img src="../images/moon-control-room-finished-frame.png" alt="月城控制室完成帧：阮星的手悬在金色与青色控制键之间" />
  </figure>
  <p>共 11 章 · 手机可调字号版</p>
</section>`;
    await writeFile(join(textRoot, "cover.xhtml"), xhtmlDocument("从梗概到分镜", coverBody), "utf8");

    for (const chapter of chapters) {
      const article = rewriteChapter(chapter, idToChapter);
      await writeFile(join(textRoot, chapter.outputFile), xhtmlDocument(chapter.title, article), "utf8");
    }

    const tocItems = chapters
      .map(
        (chapter) => `      <li><a href="text/${escapeXml(chapter.outputFile)}"><span>${String(chapter.index + 1).padStart(2, "0")}</span> ${escapeXml(chapter.title)}</a></li>`,
      )
      .join("\n");
    const navDocument = `<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN" lang="zh-CN">
<head><meta charset="utf-8" /><title>目录</title><link rel="stylesheet" type="text/css" href="styles/epub.css" /></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>目录</h1>
    <ol>
${tocItems}
    </ol>
  </nav>
  <nav epub:type="landmarks" hidden="hidden">
    <ol>
      <li><a epub:type="cover" href="text/cover.xhtml">封面</a></li>
      <li><a epub:type="bodymatter" href="text/${escapeXml(chapters[0].outputFile)}">正文</a></li>
    </ol>
  </nav>
</body>
</html>`;
    await writeFile(join(epubRoot, "nav.xhtml"), navDocument, "utf8");

    const ncxPoints = chapters
      .map(
        (chapter) => `    <navPoint id="navPoint-${chapter.index + 1}" playOrder="${chapter.index + 1}">
      <navLabel><text>${escapeXml(chapter.title)}</text></navLabel>
      <content src="text/${escapeXml(chapter.outputFile)}" />
    </navPoint>`,
      )
      .join("\n");
    const ncxDocument = `<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head><meta name="dtb:uid" content="${escapeXml(identifier)}" /></head>
  <docTitle><text>从梗概到分镜</text></docTitle>
  <navMap>
${ncxPoints}
  </navMap>
</ncx>`;
    await writeFile(join(epubRoot, "toc.ncx"), ncxDocument, "utf8");

    const manifestChapters = chapters
      .map((chapter) => {
        const properties = chapter.source.includes("<svg") ? ' properties="svg"' : "";
        return `    <item id="chapter-${chapter.index + 1}" href="text/${escapeXml(chapter.outputFile)}" media-type="application/xhtml+xml"${properties} />`;
      })
      .join("\n");
    const manifestImages = imageFiles
      .map((fileName, index) => {
        const coverProperty = fileName === "moon-control-room-finished-frame.png" ? ' properties="cover-image"' : "";
        return `    <item id="image-${index + 1}" href="images/${escapeXml(fileName)}" media-type="${mediaType(fileName)}"${coverProperty} />`;
      })
      .join("\n");
    const spineChapters = chapters
      .map((chapter) => `    <itemref idref="chapter-${chapter.index + 1}" />`)
      .join("\n");
    const packageDocument = `<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="zh-CN" prefix="rendition: http://www.idpf.org/vocab/rendition/# ibooks: http://vocabulary.itunes.apple.com/rdf/ibooks/vocabulary-extensions-1.0/">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">${escapeXml(identifier)}</dc:identifier>
    <dc:title>从梗概到分镜</dc:title>
    <dc:language>zh-CN</dc:language>
    <dc:creator>Wenjun Mao 与 Codex</dc:creator>
    <dc:description>从粗梗概到分镜投产：通用方法、Narrative Forge 与 shuohao-skills 源码解剖。</dc:description>
    <meta property="dcterms:modified">${escapeXml(modified)}</meta>
    <meta property="rendition:layout">reflowable</meta>
    <meta property="rendition:orientation">auto</meta>
    <meta property="rendition:spread">auto</meta>
    <meta property="ibooks:scroll-axis">vertical</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav" />
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />
    <item id="style" href="styles/epub.css" media-type="text/css" />
    <item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml" />
${manifestChapters}
${manifestImages}
  </manifest>
  <spine toc="ncx" page-progression-direction="ltr">
    <itemref idref="cover" linear="no" />
${spineChapters}
  </spine>
</package>`;
    await writeFile(join(epubRoot, "package.opf"), packageDocument, "utf8");

    await rm(outputPath, { force: true });
    execFileSync("zip", ["-X0", outputPath, "mimetype"], { cwd: tempRoot, stdio: "inherit" });
    execFileSync("zip", ["-Xr9", outputPath, "META-INF", "EPUB"], { cwd: tempRoot, stdio: "inherit" });
    execFileSync("unzip", ["-t", outputPath], { stdio: "inherit" });
    await access(outputPath);
    console.log(`Built ${relative(handbookRoot, outputPath)} from ${chapters.length} chapters.`);
  } finally {
    await rm(tempRoot, { recursive: true, force: true });
  }
}

await main();
