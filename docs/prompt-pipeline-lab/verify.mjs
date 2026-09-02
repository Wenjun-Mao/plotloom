import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";
import { JSDOM } from "jsdom";

const here = dirname(fileURLToPath(import.meta.url));
const indexPath = join(here, "index.html");
const fixturePath = join(here, "assets/prompt-fixtures.js");
const controllerPath = join(here, "assets/lab.js");
const revision = "24c3c47a6fb1e3fcd5a060d705f11bbffb9dbde9";

function checkSyntax(path) {
  const result = spawnSync(process.execPath, ["--check", path], { encoding: "utf8" });
  assert.equal(result.status, 0, `脚本语法检查失败：${path}\n${result.stderr}`);
}

const html = readFileSync(indexPath, "utf8");
const fixtures = readFileSync(fixturePath, "utf8");
const controller = readFileSync(controllerPath, "utf8");
const sourceMap = readFileSync(join(here, "SOURCE_MAP.md"), "utf8");

checkSyntax(fixturePath);
checkSyntax(controllerPath);

const historicalSourcePaths = [
  "app.py",
  "backend/test_server.py",
  "static/index.html",
  "static/src/main.js",
  "static/src/events.js",
  "static/src/project-model.js",
  "static/src/draft.js",
  "static/src/utils.js",
  "static/src/prompt.js",
  "static/src/scene-list.js",
];
for (const relativePath of historicalSourcePaths) {
  assert.ok(
    sourceMap.includes(relativePath),
    `历史源码证据地图缺少路径：${relativePath}`,
  );
}

assert.ok(html.includes(revision), "页面没有完整冻结提交标记。");
assert.ok(fixtures.includes(revision), "fixture 没有完整冻结提交标记。");
assert.ok(sourceMap.includes(revision), "SOURCE_MAP 没有完整冻结提交标记。");

const staticDom = new JSDOM(html);
const staticDocument = staticDom.window.document;
const ids = Array.from(staticDocument.querySelectorAll("[id]"), (element) => element.id);
const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
assert.deepEqual(duplicates, [], `页面存在重复 id：${duplicates.join(", ")}`);

for (const anchor of staticDocument.querySelectorAll('a[href^="#"]')) {
  const targetId = decodeURIComponent(anchor.getAttribute("href").slice(1));
  assert.ok(targetId && staticDocument.getElementById(targetId), `页内链接目标不存在：#${targetId}`);
}

for (const sectionId of [
  "pipeline",
  "prompt-lab",
  "response-lab",
  "contract-gap",
  "media-prompts",
  "field-mapping",
  "provenance-loss",
  "local-template",
  "rebuild-guide",
  "sources",
]) assert.ok(staticDocument.getElementById(sectionId), `必要章节缺失：#${sectionId}`);

for (const element of staticDocument.querySelectorAll("script[src], link[rel='stylesheet'][href]")) {
  const relativePath = element.getAttribute("src") || element.getAttribute("href");
  assert.ok(existsSync(join(here, relativePath)), `页面资源不存在：${relativePath}`);
}

const dom = new JSDOM(html, {
  runScripts: "outside-only",
  url: pathToFileURL(indexPath).href,
  pretendToBeVisual: true,
});
const { window } = dom;
window.eval(fixtures);
window.eval(controller);

assert.equal(window.document.body.dataset.labReady, "true", "交互控制器没有完成初始化。");
assert.equal(window.document.querySelectorAll(".pipeline-node").length, 8, "流水线应有八个阶段。");
assert.match(window.document.getElementById("promptCode").textContent, /"tree_depth": 3/);
assert.match(window.document.getElementById("promptCode").textContent, /"text_api_key": ""/);
assert.match(window.document.getElementById("mediaPromptCode").textContent, /电影关键帧/);

window.document.querySelector('[data-mode="serial"]').click();
assert.equal(window.document.getElementById("serialControls").hidden, false, "短剧字段没有显示。");
window.document.querySelector('[data-prompt-tab="user"]').click();
assert.match(window.document.getElementById("promptCode").textContent, /九条|要求：[\s\S]*9\./);
assert.match(window.document.getElementById("promptCode").textContent, /你是一名专业短剧编剧/);

const scenario = window.document.getElementById("responseScenario");
scenario.value = "badTarget";
scenario.dispatchEvent(new window.Event("change", { bubbles: true }));
window.document.querySelector('[data-response-step="installed"]').click();
assert.match(window.document.getElementById("responseStatus").textContent, /安装停止/);
assert.match(window.document.getElementById("responseView").textContent, /missing_scene/);

scenario.value = "softMismatch";
scenario.dispatchEvent(new window.Event("change", { bubbles: true }));
window.document.querySelector('[data-response-step="ui"]').click();
assert.match(window.document.getElementById("responseStatus").textContent, /分镜列表已重绘/);
assert.equal(window.document.querySelectorAll(".ui-scene-item").length, 6, "宽松接受场景应呈现六张教学卡片。");

console.log("Prompt Pipeline Lab verification passed:");
console.log("- static structure, fragments, IDs and assets");
console.log("- frozen revision and historical source-map coverage");
console.log("- JavaScript syntax and clean initialization");
console.log("- interactive/serial prompt switching");
console.log("- response rejection and soft-acceptance scenarios");
