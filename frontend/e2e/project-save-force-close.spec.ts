import { expect, saveBriefAndContinue, test } from "./fixture";
import { createScriptProject, json } from "./f5a-fixture";
import type { Page } from "@playwright/test";

async function newSourceProject(page: Page, origin: string) {
  await page.goto(`${origin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await saveBriefAndContinue(page);
  await expect(page.getByLabel("故事内容")).toBeEditable();
  return new URL(page.url()).searchParams.get("project")!;
}

test("autosave resumes incomplete source in a fresh browser after backend restart without confirming it", async ({ page, browser, request, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin);
  await page.getByLabel("来源类型").selectOption("imported_text");
  const text = "未完成的原作输入：先留在这里，明天继续。";
  await page.getByLabel("故事内容").fill(text); await page.getByLabel("改编目标").fill("");
  await page.locator(".brand-home").click();
  await expect.poll(async () => JSON.stringify(await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`)))).toContain(text);
  await workbench.restartBackend();
  const context = await browser.newContext(); const fresh = await context.newPage();
  try {
    await fresh.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source`);
    await expect(fresh.getByLabel("故事内容")).toHaveValue(text); await expect(fresh.getByLabel("改编目标")).toHaveValue("");
    await expect(fresh.getByRole("button", { name: "确认改编内容" })).toBeDisabled();
    expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`))).source).toBeNull();
    expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/runs`))).runs).toEqual([]);
  } finally { await context.close(); }
});

test("local-only input survives Home and synchronizes on reconnect while its editor is unmounted", async ({ page, request, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin), text = "网络中断期间的未确认编辑";
  const endpoint = `**/api/v2/projects/${id}/authoring-drafts`;
  await page.route(endpoint, route => route.request().method() === "PUT" ? route.fulfill({ status: 503, json: { message: "owned fixture offline" } }) : route.continue());
  await page.getByLabel("故事内容").fill(text); await page.locator(".brand-home").click();
  await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
  expect(await page.evaluate(() => JSON.stringify(localStorage))).toContain(text);
  await page.unroute(endpoint); await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect.poll(async () => JSON.stringify(await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`)))).toContain(text);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source`);
  await expect(page.getByLabel("故事内容")).toHaveValue(text);
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`))).source).toBeNull();
});

test("ordinary Home preserves a prepared task without Freeze or dispatch changes", async ({ page, request, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin);
  await page.getByRole("button", { name: "确认改编内容" }).click(); await page.getByRole("button", { name: "准备大纲任务" }).click();
  await expect(page.getByText(/^任务尚未交付 · 发送状态见下方 ·/)).toBeVisible();
  const before = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`));
  const writes: string[] = []; page.on("request", sent => { if (sent.method() !== "GET" && /\/(freeze|unfreeze|resume|send|cancel)$/.test(sent.url())) writes.push(sent.url()); });
  await page.locator(".brand-home").click(); await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`))).candidate).toEqual(before.candidate);
  expect(writes).toEqual([]);
});

test("one shared Root graph draft autosaves across leave and restart without confirmation", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "autosave-shared-graph"), endpoint = `${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`;
  const before = await json(request.get(endpoint)), text = "共享图正文保存为草稿，尚未确认。";
  const url = `${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`;
  await page.goto(url); await page.getByRole("textbox", { name: "剧情摘要", exact: true }).fill(text);
  await page.locator(".brand-home").click();
  await expect.poll(async () => JSON.stringify(await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`)))).toContain(text);
  await workbench.restartBackend(); await page.goto(url);
  await expect(page.getByRole("textbox", { name: "剧情摘要", exact: true })).toHaveValue(text);
  expect((await json(request.get(endpoint))).acceptedSectionMap).toEqual(before.acceptedSectionMap);
  const drafts = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`));
  expect(drafts.filter((draft: any) => draft.editorScope === "story_graph")).toHaveLength(1);
  expect(drafts.some((draft: any) => draft.editorScope === "section_map")).toBe(false);
});

for (const editor of ["cast", "art", "script"] as const) test(`Autosave resumes ${editor} input without changing accepted content`, async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, `autosave-${editor}`);
  const endpoint = `${workbench.apiOrigin}/api/v2/projects/${id}/${editor}`;
  const before = await json(request.get(endpoint));
  const url = editor === "cast" ? `${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`
    : `${workbench.frontendOrigin}/v2/?project=${id}&stage=source#${editor}`;
  await page.goto(url);
  const scope = page.getByTestId(`${editor}-review`);
  const text = `unfinished ${editor} author input`;
  if (editor === "cast") {
    await scope.getByRole("button", { name: "编辑角色设定", exact: true }).click();
    await scope.getByLabel("气质与举止", { exact: true }).fill(text);
  } else if (editor === "art") {
    await scope.getByRole("button", { name: "重新打开美术提案" }).click();
    await expect(scope.getByRole("button", { name: "保存重新打开的美术", exact: true })).toBeEnabled();
    await scope.locator(".art-json-editor summary").last().click();
    await scope.locator("textarea.source-outline-json:not([disabled])").fill(text);
  } else if (editor === "script") {
    await scope.getByRole("button", { name: "重新打开剧本" }).click();
    await scope.getByRole("combobox").selectOption({ label: "opening · episode 1" });
    await scope.locator("textarea.source-outline-json").fill(text);
  }
  await page.locator(".brand-home").click();
  await expect.poll(async () => (await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`))).some((draft: any) => draft.editorScope === "review_buffer" && draft.payload.editor === editor && draft.payload.text.includes(text))).toBe(true);
  await workbench.restartBackend();
  await page.goto(url);
  if (editor === "script") await scope.getByRole("combobox").selectOption({ label: "opening · episode 1" });
  if (editor === "cast") await expect(scope.getByLabel("气质与举止", { exact: true })).toHaveValue(text);
  else {
    if (editor === "art" && !await scope.locator("textarea.source-outline-json:not([disabled])").isVisible()) await scope.locator(".art-json-editor summary").last().click();
    await expect(scope.locator("textarea.source-outline-json:not([disabled])")).toHaveValue(text);
  }
  const after = await json(request.get(endpoint));
  const key = editor === "cast" ? "acceptedCast" : editor === "art" ? "acceptedArt" : "acceptedScript";
  expect(after[key]).toEqual(before[key]);
});
