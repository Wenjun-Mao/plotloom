import { expect, saveBriefAndContinue, checkedStaticTest as test } from "./fixture";
import { demoProject } from "../src/demo";
import type { Page } from "@playwright/test";

async function teachingCopy(page: Page, origin: string) {
  await page.goto(`${origin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
  await expect(page.getByRole("button", { name: "创建编辑副本", exact: true })).toBeVisible();
  await expect(page.getByLabel("片名", { exact: true })).toBeDisabled();
  await saveBriefAndContinue(page);
  const id = new URL(page.url()).searchParams.get("project")!;
  await page.goto(`${origin}/v2/?project=${id}&stage=brief`);
  await expect(page.getByLabel("片名", { exact: true })).toBeEnabled();
  return id;
}
async function more(page: Page, id: string) {
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const row = page.locator(`.directory-item[data-project-id="${id}"]`);
  await row.getByRole("button", { name: /^更多/ }).click(); return row;
}

test("optional Freeze drains working input, permits readonly loads after restart, and Unfreeze never applies it", async ({ page, workbench }) => {
  const id = await teachingCopy(page, workbench.frontendOrigin);
  const canonicalTitle = await page.getByLabel("片名", { exact: true }).inputValue();
  await page.getByLabel("片名", { exact: true }).fill("working input before Freeze");
  const row = await more(page, id);
  const frozen = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/projects/${id}/freeze`));
  await row.getByRole("button", { name: "冻结项目", exact: true }).click();
  expect((await frozen).ok()).toBeTruthy();
  await expect(row).toContainText("已冻结 · 只读");
  await page.getByRole("button", { name: "关闭窗口", exact: true }).last().click();
  await expect(page.getByLabel("片名", { exact: true })).toBeDisabled();
  await workbench.restartBackend(); await page.reload();
  await expect(page.getByTestId("recommended-workflow")).toContainText("项目已冻结，可只读浏览和播放符合条件的已有视频");
  await expect(page.getByTestId("recommended-workflow")).not.toContainText("恢复项目");
  await expect(page.getByLabel("片名", { exact: true })).toHaveValue("working input before Freeze");
  await expect(page.getByLabel("片名", { exact: true })).toBeDisabled();
  const canonical = await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json();
  expect(canonical.brief.title).toBe(canonicalTitle);
  const refused = await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ editorScope: "brief", entityId: "root", baseCanonicalRevision: canonical.revision, expectedDraftRevision: 1, payload: { title: "late", synopsis: "" } }) });
  expect(refused.status).toBe(409);
  const frozenRow = await more(page, id);
  await frozenRow.getByRole("button", { name: "解除冻结", exact: true }).click();
  await page.getByRole("button", { name: "关闭窗口", exact: true }).last().click();
  await expect(page.getByLabel("片名", { exact: true })).toBeEnabled();
  expect((await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json()).brief.title).toBe(canonicalTitle);
  expect((await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}/runs`)).json()).runs).toEqual([]);
});

test("preview performs no creation; explicit editable copy creates once without run history", async ({ page, request, workbench }, info) => {
  const writes: string[] = [];
  const observe = (call: import("@playwright/test").Request) => { if (new URL(call.url()).pathname.startsWith("/api/") && !["GET", "HEAD", "OPTIONS"].includes(call.method())) writes.push(`${call.method()} ${new URL(call.url()).pathname}`); };
  page.on("request", observe);
  const creates: string[] = [];
  page.on("request", request => { if (request.method() === "POST" && new URL(request.url()).pathname === "/api/v2/projects") creates.push(request.url()); });
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
  await expect(page.getByRole("button", { name: "创建编辑副本", exact: true })).toBeVisible();
  const guide = page.getByTestId("recommended-workflow");
  await expect(guide).toContainText("这是只读示例预览");
  await expect(guide).toContainText("创建编辑副本");
  await expect(guide).not.toContainText("恢复项目");
  await expect(page.locator(".project-switcher small")).toHaveText("示例预览 · 只读，不会创建项目");
  await expect(page.getByRole("region", { name: "创作流程", exact: true })).toContainText("创建编辑副本");
  await expect(page.locator(".toolbar-prerequisite")).toContainText("创建编辑副本");
  await page.getByRole("button", { name: "专业工作台", exact: true }).click();
  await expect(page.locator(".page")).toContainText("选择「创建编辑副本」后，可从来源与大纲建立当前图草稿");
  for (const text of ["尚未保存的项目草稿", "保存项目后", "先保存项目", "只读快照"]) await expect(page.locator("body")).not.toContainText(text);
  await page.setViewportSize({ width: 1280, height: 460 });
  await page.screenshot({ path: info.outputPath("guidance-teaching-pro-1280x460.png") });
  expect(writes).toEqual([]);
  expect((await (await request.get(`${workbench.providerOrigin}/control/status`)).json()).totalRequests).toBe(0);
  page.off("request", observe);
  expect(creates).toHaveLength(0);
  await page.getByRole("button", { name: "创建编辑副本", exact: true }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  expect(creates).toHaveLength(1);
  const id = new URL(page.url()).searchParams.get("project")!;
  expect((await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}/runs`)).json()).runs).toEqual([]);
});


test("read-only guidance distinguishes Frozen, archive and archived Frozen without writing", async ({ page, request, workbench }, info) => {
  const writes: string[] = [];
  page.on("request", call => { if (new URL(call.url()).pathname.startsWith("/api/") && !["GET", "HEAD", "OPTIONS"].includes(call.method())) writes.push(`${call.method()} ${new URL(call.url()).pathname}`); });
  for (const [state, frozen, archived, viewport] of [
    ["frozen", true, false, { width: 1280, height: 768 }],
    ["archived", false, true, { width: 1280, height: 768 }],
    ["archived-frozen", true, true, { width: 1700, height: 900 }],
  ] as const) {
    const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title: `guidance-${state}` } } });
    expect(created.status()).toBe(201); const project = await created.json();
    const base = `${workbench.apiOrigin}/api/v2/projects/${project.id}`;
    if (frozen) expect((await request.post(`${base}/freeze`)).ok()).toBeTruthy();
    if (archived) expect((await request.post(`${base}/archive`, { data: { expectedLifecycleRevision: project.lifecycleRevision } })).ok()).toBeTruthy();
    const before = await (await request.get(base)).json();
    await page.setViewportSize(viewport);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=brief`);
    const guide = page.getByTestId("recommended-workflow");
    if (archived) {
      await expect(guide).toContainText("项目已归档");
      await expect(guide).toContainText("选择「恢复」");
      if (frozen) await expect(guide).toContainText("恢复后仍保持冻结");
      else await expect(guide).not.toContainText("解除冻结");
    } else {
      await expect(guide).toContainText("项目已冻结，可只读浏览和播放符合条件的已有视频");
      await expect(guide).toContainText("解除冻结");
      await expect(guide).not.toContainText("恢复");
    }
    await expect(guide).not.toContainText("只读快照");
    await expect(guide.getByRole("button")).toHaveCount(0);
    await expect(page.getByLabel("片名", { exact: true })).toBeDisabled();
    expect(await (await request.get(base)).json()).toEqual(before);
    expect(await (await request.get(`${base}/authoring-drafts`)).json()).toEqual([]);
    expect((await (await request.get(`${base}/runs`)).json()).runs).toEqual([]);
    expect(writes).toEqual([]);
    if (state !== "archived") await page.screenshot({ path: info.outputPath(`guidance-${state}-${viewport.width}x${viewport.height}.png`) });
  }
  expect((await (await request.get(`${workbench.providerOrigin}/control/status`)).json()).totalRequests).toBe(0);
});
