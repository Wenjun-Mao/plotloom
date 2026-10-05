import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";
import type { APIRequestContext, Page } from "@playwright/test";

const row = (page: Page, id: string) => page.locator(`.directory-item[data-project-id="${id}"]`);
async function create(request: APIRequestContext, origin: string, title: string) {
  const response = await request.post(`${origin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title }, initialStages: [] } });
  expect(response.status()).toBe(201); return await response.json();
}
async function confirm(page: Page, id: string, title: string) {
  await row(page, id).getByRole("button", { name: "永久删除", exact: true }).click();
  const dialog = page.getByRole("alertdialog", { name: "永久删除项目" });
  await dialog.getByLabel("输入完整片名以确认删除").fill(title);
  await dialog.getByRole("button", { name: "确认永久删除项目" }).click();
}

for (const state of ["active", "archived", "closed"] as const) test(`deletes a ${state} project directly without archive or reopen`, async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, `直接删除-${state}`);
  if (state === "archived") expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${target.id}/archive`, { data: { expectedLifecycleRevision: 1 } })).ok()).toBeTruthy();
  if (state === "closed") expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${target.id}/close`)).ok()).toBeTruthy();
  const current = await create(request, workbench.apiOrigin, "另一个当前项目");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${current.id}&stage=brief`);
  await expect(page.getByLabel("片名")).toHaveValue("另一个当前项目");
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  if (state === "archived") await page.getByLabel("显示归档项目").check();
  let transitions = 0;
  page.on("request", request => { if (new RegExp(`/projects/${target.id}/(open|archive|restore|close)$`).test(request.url())) transitions += 1; });
  await confirm(page, target.id, target.brief.title);
  await expect(row(page, target.id)).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: "项目已永久删除" })).toBeVisible();
  expect(transitions).toBe(0);
  await expect(page).toHaveURL(new RegExp(`project=${current.id}`));
  await expect(page.getByLabel("片名")).toHaveValue("另一个当前项目");
  await workbench.restartBackend();
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`)).status()).toBe(404);
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${current.id}`)).ok()).toBeTruthy();
});

test("busy deletion retains partial source input and does not cancel a prepared job", async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, "保留任务和草稿");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=source`);
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await page.getByRole("button", { name: "准备大纲任务" }).click();
  await expect(page.getByText(/^等待助手交付 · 发送状态见下方 ·/)).toBeVisible();
  const before = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}/source-outline`)).json();
  await page.getByLabel("故事内容").fill("这段尚未确认的编辑必须保留。");
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  await confirm(page, target.id, target.brief.title);
  await expect(page.getByRole("alert")).toContainText("project_busy");
  await expect(page.getByLabel("故事内容")).toHaveValue("这段尚未确认的编辑必须保留。");
  const after = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}/source-outline`)).json();
  expect(after.candidate).toEqual(before.candidate);
});

test("stale Brief confirmation cannot erase another client's save", async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, "旧确认片名");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=brief`);
  await expect(page.getByLabel("片名")).toHaveValue(target.brief.title);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  await row(page, target.id).getByRole("button", { name: "永久删除" }).click();
  const changed = await request.patch(`${workbench.apiOrigin}/api/v2/projects/${target.id}`, { data: { expectedRevision: target.revision, brief: { ...target.brief, synopsis: "另一标签页已修改" } } });
  expect(changed.ok()).toBeTruthy();
  await page.getByRole("alertdialog").getByLabel("输入完整片名以确认删除").fill(target.brief.title);
  await page.getByRole("button", { name: "确认永久删除项目" }).click();
  await expect(page.getByRole("alert")).toContainText("revision");
  const retained = await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`);
  expect((await retained.json()).brief.synopsis).toBe("另一标签页已修改");
});

test("deletion waits for an admitted draft but never sends newer typing", async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, "删除传输中草稿");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=brief`);
  let release!: () => void, started!: () => void; let writes = 0;
  const held = new Promise<void>(resolve => { release = resolve; });
  const inFlight = new Promise<void>(resolve => { started = resolve; });
  await page.route(`**/api/v2/projects/${target.id}/authoring-drafts`, async route => {
    if (route.request().method() === "PUT") { writes += 1; started(); await held; }
    await route.continue();
  });
  try {
    await page.getByLabel("片名").fill("已发送的旧草稿"); await inFlight;
    await page.getByLabel("片名").fill("不要再发送的新草稿");
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    await confirm(page, target.id, target.brief.title);
    await expect(page.getByRole("status").filter({ hasText: "正在处理" })).toBeVisible();
    release();
    await expect(page.getByRole("alertdialog")).not.toBeVisible();
    await expect(row(page, target.id)).toHaveCount(0);
    await expect(page.getByLabel("片名")).toHaveValue("");
    expect(writes).toBe(1);
    expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`)).status()).toBe(404);
  } finally { release(); }
});
