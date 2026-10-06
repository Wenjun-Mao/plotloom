import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";
import type { Page } from "@playwright/test";
import { createScriptProject, json } from "./f5a-fixture";

async function newSourceProject(page: Page, origin: string) {
  await page.goto(`${origin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByLabel("故事内容")).toBeEditable();
  return new URL(page.url()).searchParams.get("project")!;
}
const row = (page: Page, id: string) => page.locator(`.directory-item[data-project-id="${id}"]`);

test("cached directory rows cannot close a project while directory inspection is held", async ({ page, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  await expect(row(page, id).getByRole("button", { name: "保存并关闭项目", exact: true })).toBeEnabled();
  await page.getByRole("dialog", { name: "项目目录", exact: true }).locator("footer").getByRole("button", { name: "关闭窗口", exact: true }).click();
  let release!: () => void; let readStarted!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const started = new Promise<void>(resolve => { readStarted = resolve; });
  await page.route("**/api/v2/projects?*", async route => { const response = await route.fetch(); readStarted(); await held; await route.fulfill({ response }); });
  try {
    await page.getByRole("button", { name: "当前项目 · 切换" }).click(); await started;
    await expect(row(page, id).getByRole("button", { name: "保存并关闭项目", exact: true })).toBeDisabled();
    await expect(row(page, id).getByRole("button", { name: "强制关闭", exact: true })).toBeDisabled();
    await expect(page.getByRole("button", { name: "新建空白项目", exact: true })).toBeEnabled();
    release();
    await expect(row(page, id).getByRole("button", { name: "保存并关闭项目", exact: true })).toBeEnabled();
    await row(page, id).getByRole("button", { name: "保存并关闭项目", exact: true }).click();
    await expect(row(page, id)).toContainText("已关闭 · 可安全复制");
  } finally { release(); }
});

test("workspace close waits for its directory read before requesting exclusive close", async ({ page, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin);
  let release!: () => void; let readStarted!: () => void; let closes = 0;
  const held = new Promise<void>(resolve => { release = resolve; });
  const started = new Promise<void>(resolve => { readStarted = resolve; });
  await page.route("**/api/v2/projects?*", async route => {
    const response = await route.fetch(); readStarted(); await held;
    await route.fulfill({ response });
  });
  await page.route("**/api/v2/projects/*/close", async route => { closes += 1; await route.continue(); });
  try {
    await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
    await started;
    await expect(page.getByRole("heading", { name: "项目目录", exact: true })).toBeVisible();
    expect(closes).toBe(0);
    release();
    await expect(row(page, id)).toContainText("已关闭 · 可安全复制");
    expect(closes).toBe(1);
  } finally { release(); }
});

test("leaving during directory inspection abandons the pending close without clearing the newer workspace", async ({ page, request, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin);
  let release!: () => void; let readStarted!: () => void; let closes = 0;
  const held = new Promise<void>(resolve => { release = resolve; });
  const started = new Promise<void>(resolve => { readStarted = resolve; });
  await page.route("**/api/v2/projects?*", async route => {
    const response = await route.fetch(); readStarted(); await held;
    await route.fulfill({ response });
  });
  await page.route("**/api/v2/projects/*/close", async route => { closes += 1; await route.continue(); });
  try {
    await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click(); await started;
    await page.getByRole("button", { name: "新建空白项目", exact: true }).click();
    await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
    await page.getByLabel("片名").fill("新的工作区不会被旧关闭清空");
    release();
    // Let the held inspection settle without another API read competing with
    // exclusive Close. A stale callback would have dispatched by this point.
    await page.waitForLoadState("networkidle");
    await expect(page.getByLabel("片名")).toHaveValue("新的工作区不会被旧关闭清空");
    expect(closes).toBe(0);
    expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).ok()).toBeTruthy();
  } finally { release(); }
});

test("Save-and-close recovers unfinished source after restart without confirming it", async ({ page, request, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin);
  await page.getByLabel("来源类型").selectOption("imported_text");
  await page.getByLabel("故事内容").fill("未完成的原作输入：先留在这里，明天继续。");
  await page.getByLabel("改编目标").fill("");
  await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
  await expect(row(page, id)).toContainText("已关闭 · 可安全复制");
  await page.evaluate(() => sessionStorage.clear());
  await workbench.restartBackend();
  await row(page, id).getByRole("button", { name: "重新打开" }).click();
  await page.getByRole("navigation", { name: "创作流程" }).getByRole("link", { name: "来源与大纲" }).click();
  await page.getByRole("button", { name: "恢复编辑草稿" }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue("未完成的原作输入：先留在这里，明天继续。");
  await expect(page.getByLabel("改编目标")).toHaveValue("");
  await expect(page.getByRole("button", { name: "确认改编内容" })).toBeDisabled();
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`)).json()).source).toBeNull();
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/runs`)).json()).runs).toEqual([]);
});

test("closes an untouched directory project without changing the current one", async ({ page, request, workbench }) => {
  const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": "unloaded-close-project" }, data: { brief: { ...demoProject.brief, title: "另一个尚未加载的项目" }, initialStages: [] },
  });
  expect(created.ok()).toBeTruthy(); const other = (await created.json()).id;
  const current = await newSourceProject(page, workbench.frontendOrigin);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  await row(page, other).getByRole("button", { name: "保存并关闭项目" }).click();
  await expect(row(page, other)).toContainText("已关闭 · 可安全复制");
  await expect(page).toHaveURL(new RegExp(`project=${current}`));
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${current}`)).ok()).toBeTruthy();
  await expect(page.getByText("编辑草稿未能保存", { exact: false })).not.toBeVisible();
});

test("failed draft save retains input; force consent discards only unsent edits", async ({ page, request, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin);
  const original = await page.getByLabel("故事内容").inputValue();
  await page.getByLabel("故事内容").fill("这段尚未发送的编辑将由明确强制关闭丢弃。");
  await page.route("**/api/v2/projects/*/authoring-drafts", async route => {
    if (route.request().method() === "PUT") await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "draft unavailable" }) });
    else await route.continue();
  });
  await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("编辑草稿未能保存");
  await expect(page.getByLabel("故事内容")).toHaveValue("这段尚未发送的编辑将由明确强制关闭丢弃。");
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).ok()).toBeTruthy();
  await row(page, id).getByRole("button", { name: "强制关闭", exact: true }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "取消", exact: true }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue("这段尚未发送的编辑将由明确强制关闭丢弃。");
  await row(page, id).getByRole("button", { name: "强制关闭", exact: true }).click();
  await page.getByRole("button", { name: "确认强制关闭项目", exact: true }).click();
  await expect(row(page, id)).toContainText("已关闭 · 可安全复制");
  await row(page, id).getByRole("button", { name: "重新打开" }).click();
  await page.getByRole("navigation", { name: "创作流程" }).getByRole("link", { name: "来源与大纲" }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue(original);
  expect(await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`)).json()).toEqual([]);
});

test("force exits while a prepared job remains owned and running-admissible", async ({ page, request, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin);
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await page.getByRole("button", { name: "准备大纲任务" }).click();
  await expect(page.getByText(/^等待助手交付 · 发送状态见下方 ·/)).toBeVisible();
  const before = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`)).json();
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  await row(page, id).getByRole("button", { name: "强制关闭", exact: true }).click();
  await expect(page.getByRole("alertdialog")).toContainText("后台任务继续运行");
  await page.getByRole("button", { name: "确认强制关闭项目", exact: true }).click();
  await expect(page.getByText("已退出工作区；后台任务继续运行。项目尚未安全关闭，可稍后重试。", { exact: true })).toBeVisible();
  await expect(row(page, id)).toContainText("可打开");
  await expect(row(page, id)).not.toContainText("已关闭");
  await expect(page).not.toHaveURL(new RegExp(`project=${id}`));
  const after = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`)).json();
  expect(after.candidate).toEqual(before.candidate);
  expect(after.candidate.status).toBe("prepared");
});

test("unknown force-close outcome is visibly unconfirmed, never inferred closed", async ({ page, workbench }) => {
  const id = await newSourceProject(page, workbench.frontendOrigin);
  await page.route("**/api/v2/projects/*/close", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "close unknown" }) }));
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  await row(page, id).getByRole("button", { name: "强制关闭", exact: true }).click();
  await page.getByRole("button", { name: "确认强制关闭项目", exact: true }).click();
  await expect(page.getByText(/已退出工作区，但未能确认安全关闭/)).toBeVisible();
  await expect(row(page, id)).not.toContainText("已关闭");
});

test("force closing another busy project keeps the current workspace and does not claim exit", async ({ page, request, workbench }) => {
  const other = await newSourceProject(page, workbench.frontendOrigin);
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await page.getByRole("button", { name: "准备大纲任务" }).click();
  await expect(page.getByText(/^等待助手交付 · 发送状态见下方 ·/)).toBeVisible();
  const before = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${other}/source-outline`));
  const current = await newSourceProject(page, workbench.frontendOrigin);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  await row(page, other).getByRole("button", { name: "强制关闭", exact: true }).click();
  await page.getByRole("button", { name: "确认强制关闭项目", exact: true }).click();
  await expect(page.getByText("后台任务继续运行；项目尚未安全关闭，可稍后重试。", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`project=${current}`));
  await expect(row(page, current)).toContainText("当前项目");
  await expect(row(page, other)).toContainText("可打开");
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${other}/source-outline`))).candidate).toEqual(before.candidate);
});

test("Save-and-close restores the shared Root graph draft without confirming it", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "close-shared-graph");
  const endpoint = `${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`;
  const before = await json(request.get(endpoint));
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  const text = "共享图正文保存为草稿，尚未确认。";
  await page.getByRole("textbox", { name: "剧情摘要", exact: true }).fill(text);
  await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
  await expect(row(page, id)).toContainText("已关闭 · 可安全复制");
  await page.evaluate(() => sessionStorage.clear());
  await workbench.restartBackend();
  await row(page, id).getByRole("button", { name: "重新打开" }).click();
  await expect(page.getByRole("textbox", { name: "剧情摘要", exact: true })).toHaveValue(text);
  expect((await json(request.get(endpoint))).acceptedSectionMap).toEqual(before.acceptedSectionMap);
  const drafts = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`));
  expect(drafts.filter((draft: any) => draft.editorScope === "story_graph")).toHaveLength(1);
  expect(drafts.some((draft: any) => draft.editorScope === "section_map")).toBe(false);
});

for (const editor of ["cast", "art", "script"] as const) test(`Save-and-close recovers ${editor} input without changing accepted content`, async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, `close-${editor}`);
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
  await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
  await expect(row(page, id)).toContainText("已关闭 · 可安全复制");
  await page.evaluate(() => sessionStorage.clear());
  await workbench.restartBackend();
  await row(page, id).getByRole("button", { name: "重新打开" }).click();
  await page.goto(url);
  await scope.getByRole("button", { name: "恢复编辑草稿" }).click();
  if (editor === "cast") await expect(scope.getByLabel("气质与举止", { exact: true })).toHaveValue(text);
  else {
    if (editor === "art") await scope.locator(".art-json-editor summary").last().click();
    await expect(scope.locator("textarea.source-outline-json:not([disabled])")).toHaveValue(text);
  }
  const after = await json(request.get(endpoint));
  const key = editor === "cast" ? "acceptedCast" : editor === "art" ? "acceptedArt" : "acceptedScript";
  expect(after[key]).toEqual(before[key]);
});
