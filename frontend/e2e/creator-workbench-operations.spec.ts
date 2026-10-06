import type { Page } from "@playwright/test";
import { expect, test } from "./fixture";
import { createCreatorGraph } from "./fixtures/creator-graph";
import { json } from "./f5a-fixture";
import type { GraphAuthoringDraft } from "../src/features/graph/contracts";

const preview = (page: Page) => page.getByRole("dialog", { name: "确认结构修改" });
async function confirm(page: Page) { await preview(page).getByRole("button", { name: "确认修改", exact: true }).click(); await expect(preview(page)).toHaveCount(0); }
async function prepare(page: Page) { await page.getByRole("button", { name: "准备修改预览", exact: true }).click(); await expect(preview(page)).toBeVisible(); }
async function undo(page: Page) {
  const receipt = page.waitForResponse(response => response.request().method() === "PUT" && new URL(response.url()).pathname.endsWith("/authoring-drafts"));
  await page.getByRole("button", { name: "撤销结构修改", exact: true }).click();
  expect((await receipt).ok()).toBeTruthy();
  await expect(page.getByRole("button", { name: "保存图草稿", exact: true })).toBeEnabled();
}
async function select(page: Page, title: string) { await page.getByRole("button", { name: `选择节点 ${title}`, exact: true }).click(); await expect(page.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue(title); }
async function nameNode(page: Page, title: string) { await page.getByRole("textbox", { name: "章节标题", exact: true }).fill(title); await page.getByRole("textbox", { name: "剧情摘要", exact: true }).fill(`${title} 的正文完整保留。`); await page.getByRole("button", { name: "保存图草稿", exact: true }).click(); }

test("creator exact operations 123 → 222 → 333, drag, deletion, Undo and reload", async ({ page, request, workbench }, info) => {
  test.setTimeout(150_000); await page.setViewportSize({ width: 1700, height: 900 });
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  const id = await createCreatorGraph(request, workbench.apiOrigin, "operations");
  const url = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const read = async (): Promise<GraphAuthoringDraft> => (await json(request.get(`${url}/graph-workbench`))).draft.payload;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await expect(page.locator("[data-creator-node]")).toHaveCount(9);
  const baseline = await read();
  const add = async (title: string) => {
    await page.getByRole("button", { name: "向第 3 行添加节点", exact: true }).click();
    await expect(page.getByLabel("并行选项来自", { exact: true })).toHaveValue("choose");
    await expect(page.getByLabel("新增节点的后续", { exact: true })).toHaveValue("merge");
    await prepare(page); await expect(preview(page).getByRole("table")).toContainText("choose →"); await expect(preview(page).getByRole("table")).toContainText("→ 汇合：");
    if (title === "123") {
      const beforeCancel = await read();
      await preview(page).getByRole("button", { name: "取消", exact: true }).click(); expect((await read()).mapping).toEqual(beforeCancel.mapping);
      await page.getByRole("button", { name: "向第 3 行添加节点", exact: true }).click(); await prepare(page);
      await page.screenshot({ path: info.outputPath("row-preview.png") });
    }
    await confirm(page); await nameNode(page, title);
    const draft = await read(), node = draft.mapping.sections.find(section => section.title === title)!;
    return node.sectionId;
  };
  const a = await add("123"), b = await add("222");
  let draft = await read();
  const aInput = draft.mapping.topology.edges.find(edge => edge.targetNodeId === a)!.id, aOutput = draft.mapping.topology.edges.find(edge => edge.sourceNodeId === a)!.id;
  const bInput = draft.mapping.topology.edges.find(edge => edge.targetNodeId === b)!.id, bOutput = draft.mapping.topology.edges.find(edge => edge.sourceNodeId === b)!.id;
  await select(page, "123");
  const input = page.locator(`[data-edge-id="${aInput}"]`);
  await input.getByRole("textbox", { name: "保留的选项文字", exact: true }).fill("第三个选项，保留身份与文字");
  await input.getByRole("textbox", { name: "保留的后续剧情", exact: true }).fill("选择 123 的后果保留。");
  await page.getByRole("button", { name: "在第 3 行后插入新一行", exact: true }).click();
  await page.getByLabel("拆分的精确连接", { exact: true }).selectOption(aOutput); await prepare(page);
  await expect(preview(page).getByRole("table")).toContainText("123 → 新建故事发展");
  await page.screenshot({ path: info.outputPath("insert-preview.png") });
  await confirm(page); await nameNode(page, "333");
  draft = await read(); const c = draft.mapping.sections.find(section => section.title === "333")!.sectionId;
  const cOutput = draft.mapping.topology.edges.find(edge => edge.sourceNodeId === c)!.id;
  expect(draft.mapping.topology.edges.find(edge => edge.id === aOutput)?.targetNodeId).toBe(c);
  await page.screenshot({ path: info.outputPath("inserted.png") });
  await page.getByRole("button", { name: "修改 222 的输入", exact: true }).click();
  await page.getByLabel("精确选项或后续", { exact: true }).selectOption(bInput);
  await page.getByLabel("选择新的精确输入", { exact: true }).selectOption(aOutput); await prepare(page);
  await expect(preview(page).getByRole("table")).toContainText("123 → 222"); await confirm(page);
  draft = await read(); expect(draft.mapping.topology.edges.find(edge => edge.id === bInput)?.targetNodeId).toBeNull();
  expect(draft.mapping.sections.some(section => section.sectionId === c)).toBe(true);
  await page.getByRole("button", { name: "修改 333 的输入", exact: true }).click();
  await page.getByLabel("选择新的精确输入", { exact: true }).selectOption(bOutput); await prepare(page); await confirm(page);
  draft = await read(); expect(draft.mapping.topology.edges.find(edge => edge.id === bOutput)?.targetNodeId).toBe(c);
  await select(page, "333");
  await page.getByRole("button", { name: "连接 333 的后续", exact: true }).click();
  await page.getByLabel("更改连接端点", { exact: true }).selectOption(""); await prepare(page); await confirm(page);
  expect((await read()).mapping.topology.edges.find(edge => edge.id === cOutput)?.targetNodeId).toBeNull();
  await undo(page);
  expect((await read()).mapping.topology.edges.find(edge => edge.id === cOutput)?.targetNodeId).toBe("merge");
  // Self-link and cycle refusal apply nothing and preserve the exact saved state.
  const beforeInvalid = await read();
  await page.getByRole("button", { name: "连接 333 的后续", exact: true }).click();
  await page.getByLabel("更改连接端点", { exact: true }).selectOption(a); await page.getByRole("button", { name: "准备修改预览", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("cycle"); expect((await read()).mapping).toEqual(beforeInvalid.mapping);
  // Both deletion methods explicitly preview, each restores the whole transaction.
  for (const method of ["预览安全绕过", "仅删除，保留待连接"]) {
    await select(page, "333"); await page.getByRole("button", { name: "删除节点…", exact: true }).click();
    await page.getByRole("button", { name: method, exact: true }).click(); await expect(preview(page)).toContainText("333");
    await confirm(page); expect((await read()).mapping.topology.nodes.some(node => node.id === c)).toBe(false);
    if (method === "预览安全绕过") expect((await read()).mapping.topology.edges.find(edge => edge.id === bOutput)?.targetNodeId).toBe("merge");
    await undo(page);
    expect((await read()).mapping).toEqual(beforeInvalid.mapping);
  }
  await page.screenshot({ path: info.outputPath("undo.png") });
  // A detached target at the current row allows a separate real pointer-drag exercise.
  await page.getByRole("button", { name: "向第 4 行添加节点", exact: true }).click();
  await page.getByLabel("并行选项来自", { exact: true }).selectOption(""); await page.getByLabel("新增节点的后续", { exact: true }).selectOption("");
  await prepare(page); await confirm(page); await nameNode(page, "拖动目标");
  const target = (await read()).mapping.sections.find(section => section.title === "拖动目标")!.sectionId;
  const from = page.getByRole("button", { name: "连接 333 的后续", exact: true }), to = page.getByRole("button", { name: "选择节点 拖动目标", exact: true });
  await from.scrollIntoViewIfNeeded(); await to.scrollIntoViewIfNeeded();
  const fromBox = (await from.boundingBox())!, toBox = (await to.boundingBox())!;
  await page.mouse.move(fromBox.x + fromBox.width / 2, fromBox.y + fromBox.height / 2); await page.mouse.down();
  await page.mouse.move(toBox.x + toBox.width / 2, toBox.y + toBox.height / 2, { steps: 12 }); await page.mouse.up();
  await expect(page.getByLabel("更改连接端点", { exact: true })).toHaveValue(target); await prepare(page); await confirm(page);
  expect((await read()).mapping.topology.edges.find(edge => edge.id === cOutput)?.targetNodeId).toBe(target);
  let releaseUndo!: () => void, startedUndo!: () => void;
  const heldUndo = new Promise<void>(resolve => { releaseUndo = resolve; });
  const undoStarted = new Promise<void>(resolve => { startedUndo = resolve; });
  const draftPath = `**/api/v2/projects/${id}/authoring-drafts`;
  await page.route(draftPath, async route => {
    if (route.request().method() !== "PUT") return route.continue();
    const response = await route.fetch(); startedUndo(); await heldUndo; await route.fulfill({ response });
  });
  await page.getByRole("button", { name: "撤销结构修改", exact: true }).click();
  try {
    await undoStarted;
    await select(page, "choose");
    releaseUndo();
    await expect(page.getByRole("button", { name: "保存图草稿", exact: true })).toBeEnabled();
    await expect(page.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("choose");
  } finally { releaseUndo(); await page.unroute(draftPath); }
  // Cancel applies nothing. Explicit deletion covers every supported kind without cascades.
  for (const title of ["choose", "汇合：各条路线回到同一座气象站", "结局 A", "拖动目标"]) {
    await select(page, title); const before = await read();
    await page.getByRole("button", { name: "删除节点…", exact: true }).click(); await page.getByRole("button", { name: "仅删除，保留待连接", exact: true }).click();
    await preview(page).getByRole("button", { name: "取消", exact: true }).click(); expect((await read()).mapping).toEqual(before.mapping);
    await page.getByRole("button", { name: "删除节点…", exact: true }).click(); await page.getByRole("button", { name: "仅删除，保留待连接", exact: true }).click(); await confirm(page);
    expect((await read()).mapping.topology.nodes).toHaveLength(before.mapping.topology.nodes.length - 1);
    await undo(page); expect((await read()).mapping).toEqual(before.mapping);
  }
  await select(page, "风暴前的共同开场"); await expect(page.getByRole("button", { name: "删除节点…", exact: true })).toBeDisabled();
  // Fresh decision scaffolding is explicit and stays pending, never invented footage.
  await page.getByRole("button", { name: "向第 4 行添加节点", exact: true }).click();
  await page.getByLabel("新增节点类型", { exact: true }).selectOption("decision"); await page.getByLabel("并行选项来自", { exact: true }).selectOption("");
  await expect(page.getByRole("checkbox", { name: "建立两个待连接选项（恢复保留选项时可取消）" })).toBeChecked();
  await prepare(page); await confirm(page); await nameNode(page, "新选择点");
  draft = await read(); const fresh = draft.mapping.sections.find(section => section.title === "新选择点")!;
  expect(fresh.footageMode).toBe("route_only"); expect(draft.mapping.topology.edges.filter(edge => edge.sourceNodeId === fresh.sectionId && edge.targetNodeId === null)).toHaveLength(2);
  await select(page, "123"); await page.getByRole("button", { name: "保存图草稿", exact: true }).click(); const saved = await read();
  await page.getByRole("button", { name: "专业工作台", exact: true }).click();
  await expect(page.getByRole("heading", { name: "剧情图与精确合同" })).toBeVisible();
  await page.getByRole("button", { name: "创作工作台", exact: true }).click(); await expect(page.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("123");
  await page.reload(); await expect(page.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("123"); expect((await read()).mapping).toEqual(saved.mapping);
  expect(saved.mapping.choices.find(choice => choice.sectionId === "choose")!.outcomes.find(option => option.outcomeId === aInput)!.label).toBe("第三个选项，保留身份与文字");
  for (const section of baseline.mapping.sections) expect(saved.mapping.sections.find(value => value.sectionId === section.sectionId)).toEqual(section);
  expect((await json(request.get(`${url}/runs`))).runs).toEqual([]); expect(errors).toEqual([]);
  await page.screenshot({ path: info.outputPath("reopened.png") });
});

test("creator capacity, retained-node reuse and explicit decision restoration", async ({ page, request, workbench }) => {
  test.setTimeout(100_000); await page.setViewportSize({ width: 1700, height: 900 });
  const id = await createCreatorGraph(request, workbench.apiOrigin, "capacity-restoration", 6), url = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const read = async (): Promise<GraphAuthoringDraft> => (await json(request.get(`${url}/graph-workbench`))).draft.payload;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await expect(page.locator("[data-creator-node]")).toHaveCount(13);
  const full = await read();
  await page.getByRole("button", { name: "向第 3 行添加节点", exact: true }).click(); await page.getByRole("button", { name: "准备修改预览", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("out_degree:choose"); expect((await read()).mapping).toEqual(full.mapping);
  await select(page, "choose");
  await page.getByRole("button", { name: "新增待连接输出", exact: true }).click(); await expect(page.getByRole("alert")).toContainText("out_degree:choose");
  await page.getByRole("button", { name: "向第 3 行添加节点", exact: true }).click();
  await page.getByLabel("并行选项来自", { exact: true }).selectOption(""); await page.getByLabel("新增节点的后续", { exact: true }).selectOption("");
  await prepare(page); await confirm(page); await nameNode(page, "同排未接入节点");
  await page.getByRole("button", { name: "向第 3 行添加节点", exact: true }).click();
  await expect(page.getByLabel("并行选项来自", { exact: true })).toHaveValue("");
  await page.getByRole("dialog", { name: "向此行添加节点" }).getByRole("button", { name: "取消", exact: true }).click();
  await select(page, "choose");
  const removal = page.locator('[data-edge-id="option-6"]'); await removal.getByRole("button", { name: "删除这条连接", exact: true }).click(); await confirm(page);
  await page.getByRole("button", { name: "向第 3 行添加节点", exact: true }).click();
  await page.getByLabel("新建或复用", { exact: true }).selectOption("branch-6"); await expect(page.getByLabel("新增节点的后续", { exact: true })).toHaveValue("");
  await page.getByLabel("并行选项来自", { exact: true }).selectOption("choose");
  await prepare(page); await confirm(page);
  let draft = await read(); expect(draft.mapping.topology.nodes).toHaveLength(14);
  expect(draft.mapping.sections.find(section => section.sectionId === "branch-6")).toEqual(full.mapping.sections.find(section => section.sectionId === "branch-6"));
  expect(draft.mapping.topology.edges.find(edge => edge.id === "branch-output-6")).toEqual(full.mapping.topology.edges.find(edge => edge.id === "branch-output-6"));
  expect(draft.mapping.topology.edges.filter(edge => edge.sourceNodeId === "choose")).toHaveLength(6);
  await page.getByRole("button", { name: "向第 4 行添加节点", exact: true }).click();
  await page.getByLabel("新增节点类型", { exact: true }).selectOption("decision"); await page.getByLabel("并行选项来自", { exact: true }).selectOption("");
  await prepare(page); await confirm(page); await nameNode(page, "待连接选择");
  draft = await read(); const removedId = draft.mapping.sections.find(section => section.title === "待连接选择")!.sectionId;
  const retained = draft.mapping.topology.edges.filter(edge => edge.sourceNodeId === removedId); expect(retained).toHaveLength(2);
  await page.getByRole("textbox", { name: "选项文字", exact: true }).nth(0).fill("恢复文字甲");
  await page.getByRole("textbox", { name: "选项文字", exact: true }).nth(1).fill("恢复文字乙");
  await page.getByRole("button", { name: "删除节点…", exact: true }).click(); await page.getByRole("button", { name: "仅删除，保留待连接", exact: true }).click(); await confirm(page);
  await page.getByRole("button", { name: "向第 4 行添加节点", exact: true }).click();
  await page.getByLabel("新增节点类型", { exact: true }).selectOption("decision"); await page.getByLabel("并行选项来自", { exact: true }).selectOption("");
  await page.getByRole("checkbox", { name: "建立两个待连接选项（恢复保留选项时可取消）" }).uncheck(); await prepare(page); await confirm(page); await nameNode(page, "恢复选择点");
  draft = await read(); const restoredId = draft.mapping.sections.find(section => section.title === "恢复选择点")!.sectionId;
  expect(draft.mapping.topology.edges.filter(edge => edge.sourceNodeId === restoredId)).toHaveLength(0);
  await page.getByRole("button", { name: "专业工作台", exact: true }).click();
  await page.getByText("全部稳定身份与待连接关系", { exact: true }).click();
  for (const edge of retained) {
    const control = page.locator(`details > [data-edge-id="${edge.id}"]`);
    await control.getByLabel(`${edge.id} 起点`, { exact: true }).selectOption(restoredId); await confirm(page);
  }
  draft = await read(); expect(draft.mapping.topology.edges.filter(edge => edge.sourceNodeId === restoredId).map(edge => edge.id)).toEqual(retained.map(edge => edge.id));
  expect(draft.mapping.choices.find(choice => choice.sectionId === restoredId)!.outcomes.map(option => option.label)).toEqual(["恢复文字甲", "恢复文字乙"]);
  await page.getByRole("button", { name: "创作工作台", exact: true }).click(); await select(page, "恢复选择点");
  await expect(page.getByRole("textbox", { name: "选项文字", exact: true })).toHaveCount(2);
});

test("Brief target preview distinguishes actual structure and preserves the graph", async ({ page, request, workbench }) => {
  const id = await createCreatorGraph(request, workbench.apiOrigin, "target-preview"), url = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  await page.setViewportSize({ width: 1700, height: 900 }); await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await expect(page.locator("[data-creator-node]")).toHaveCount(9);
  const before = await json(request.get(`${url}/graph-workbench`));
  await page.getByRole("button", { name: "项目简报与结构设置", exact: true }).click();
  await page.getByLabel("剧情节点数量上限", { exact: true }).fill("40"); await page.getByRole("button", { name: "保存修改", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "确认结构目标调整" });
  await expect(dialog).toContainText("当前实际图：9 节点"); await expect(dialog).toContainText("不会自动改图");
  await dialog.getByRole("button", { name: "取消调整", exact: true }).click();
  expect((await json(request.get(url))).brief.nodeBudget).toBe(30);
  await page.getByRole("button", { name: "保存修改", exact: true }).click(); await dialog.getByRole("button", { name: "确认并保存目标", exact: true }).click();
  await expect.poll(async () => (await json(request.get(url))).brief.nodeBudget).toBe(40);
  expect((await json(request.get(`${url}/graph-workbench`))).draft.payload.mapping).toEqual(before.draft.payload.mapping);
});

test("project directory opens the graph-first creator workspace", async ({ page, request, workbench }) => {
  const id = await createCreatorGraph(request, workbench.apiOrigin, "directory-entry");
  await page.setViewportSize({ width: 1700, height: 900 }); await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开项目目录", exact: true }).click();
  await page.locator(`[data-project-id="${id}"] .directory-open`).click();
  await expect(page).toHaveURL(new RegExp(`project=${id}&stage=creator$`));
  await expect(page.getByRole("heading", { name: "创作工作台", exact: true })).toBeVisible();
});
