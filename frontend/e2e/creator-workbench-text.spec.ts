import type { Request, Route } from "@playwright/test";
import { expect, checkedStaticTest as test } from "./fixture";
import { createCreatorGraph } from "./fixtures/creator-graph";
import { json } from "./f5a-fixture";

test("native text stays literal and structural preview Escape writes nothing", async ({ page, request, workbench }, info) => {
  await page.setViewportSize({ width: 1280, height: 768 });
  const id = await createCreatorGraph(request, workbench.apiOrigin, "literal-text");
  const endpoint = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const read = () => json(request.get(`${endpoint}/graph-workbench`));
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  const before = await read();
  const node = page.locator('[data-creator-node="opening"]');
  const title = '中文  空格 <b>原文 & "引号"</b>';
  const summary = '<img src=x onerror="window.__graphTextExecuted=true">  保留原样';
  const inspector = page.getByRole("complementary", { name: "当前节点详情" });
  const draftPath = `**/api/v2/projects/${id}/authoring-drafts`;
  const isFinalPut = (request: Request) => {
    if (request.method() !== "PUT" || new URL(request.url()).pathname !== `/api/v2/projects/${id}/authoring-drafts`) return false;
    const draft = request.postDataJSON();
    return draft.editorScope === "story_graph" && draft.entityId === "root"
      && draft.payload.mapping.sections.some((section: { sectionId: string; title: string; summary: string }) =>
        section.sectionId === "opening" && section.title === title && section.summary === summary);
  };
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const flights = new Set<Promise<void>>();
  let finalPutSeen = false;
  const holdFinalPut = async (route: Route) => {
    if (!isFinalPut(route.request())) return route.continue();
    finalPutSeen = true;
    const flight = held.then(() => route.continue());
    flights.add(flight);
    try { await flight; } finally { flights.delete(flight); }
  };
  await page.route(draftPath, holdFinalPut);
  const finalPut = page.waitForRequest(isFinalPut);
  const receipt = page.waitForResponse(response => isFinalPut(response.request()));
  // Keep observers handled if an earlier assertion fails; cleanup still drains
  // any admitted real request before the page fixture disposes its context.
  void finalPut.catch(() => undefined); void receipt.catch(() => undefined);
  try {
    await inspector.getByRole("textbox", { name: "章节标题", exact: true }).fill("");
    await inspector.getByRole("textbox", { name: "剧情摘要", exact: true }).fill("");
    await expect(node).toContainText("待填写标题");
    await expect(node).toContainText("待填写剧情");
    await page.screenshot({ path: info.outputPath("blank-viewport.png") });
    await inspector.getByRole("textbox", { name: "章节标题", exact: true }).fill(title);
    await inspector.getByRole("textbox", { name: "剧情摘要", exact: true }).fill(summary);
    await expect(node.locator("strong")).toHaveText(title);
    await expect(node.locator("small")).toHaveText(summary);
    await expect(node.locator("img,b")).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__graphTextExecuted)).toBeUndefined();
    const save = page.getByRole("button", { name: "保存图草稿", exact: true });
    await save.click();
    await finalPut;
    await expect(save).toBeDisabled();
    release();
    const acknowledged = await json(await receipt);
    expect(acknowledged).toMatchObject({ projectId: id, editorScope: "story_graph", entityId: "root" });
    expect(acknowledged.payload.mapping.sections[0]).toMatchObject({ title, summary });
    await expect(save).toBeEnabled();
    const saved = await read();
    expect(saved.draft.draftRevision).toBe(acknowledged.draftRevision);
    expect(saved.draft.payload).toEqual(acknowledged.payload);
    expect(saved.draft.payload.mapping.topology).toEqual(before.draft.payload.mapping.topology);
    expect(saved.draft.payload.mapping.sections[0]).toMatchObject({ title, summary });
  } finally {
    release();
    try {
      await Promise.all(flights);
      if (finalPutSeen) await receipt.catch(() => undefined);
    } finally { await page.unroute(draftPath, holdFinalPut); }
  }
  await page.screenshot({ path: info.outputPath("literal-viewport.png") });
  const add = page.getByRole("button", { name: "向第 3 行添加节点", exact: true });
  await add.focus(); await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "准备修改预览", exact: true }).click();
  const preview = page.getByRole("dialog", { name: "确认结构修改" });
  await expect(preview).toBeVisible();
  const acknowledged = await read();
  let writes = 0;
  page.on("request", request => { if (new URL(request.url()).pathname.startsWith(`/api/v2/projects/${id}/`) && !["GET", "HEAD"].includes(request.method())) writes++; });
  await page.keyboard.press("Escape");
  await expect(preview).toHaveCount(0);
  expect(await read()).toEqual(acknowledged);
  expect(writes).toBe(0);
  expect((await json(request.get(`${endpoint}/runs`))).runs).toEqual([]);
});
