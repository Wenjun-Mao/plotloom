import { expect, test } from "./fixture";
import type { Locator, Page, TestInfo } from "@playwright/test";
import { demoProject } from "../src/demo";

test("manual-save Brief recovery restores tab input without automatic draft or canonical writes", async ({ page, request, workbench }, info) => {
  await page.route("**/api/v2/runtime-capabilities", async route => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...await response.json(), durableProjectDrafts: false } });
  });
  const endpoint = `${workbench.apiOrigin}/api/v2/projects`;
  const created = await (await request.post(endpoint, { data: { brief: demoProject.brief, initialStages: [] } })).json();
  const root = `${endpoint}/${created.id}`;
  const projectPath = `/api/v2/projects/${created.id}`;
  const canonical = await (await request.get(root)).json();
  const writes: string[] = [];
  page.on("request", req => { if (["PUT", "PATCH"].includes(req.method()) && new URL(req.url()).pathname.startsWith(projectPath)) writes.push(`${req.method()} ${new URL(req.url()).pathname}`); });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${created.id}&stage=brief`);
  await expect(page.getByLabel("片名", { exact: true })).toHaveValue(canonical.brief.title);
  const title = "仅标签页保留的手动保存草稿";
  await page.getByLabel("片名", { exact: true }).fill(title);
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("plotloom:workbench-drafts:v1"))).toContain(title);
  await page.reload();
  const dialog = page.getByRole("dialog", { name: "发现可恢复草稿", exact: true });
  await expect(dialog).toContainText("请手动保存");
  await captureDialog(page, dialog, info, "manual-session-ready");
  await dialog.getByRole("button", { name: "恢复草稿", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByLabel("片名", { exact: true })).toHaveValue(title);
  expect(writes).toEqual([]);
  expect(await (await request.get(root)).json()).toEqual(canonical);
  const saved = page.waitForResponse(r => r.request().method() === "PATCH" && new URL(r.url()).pathname === projectPath);
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  expect((await saved).ok()).toBe(true);
  expect((await (await request.get(root)).json()).brief.title).toBe(title);
  expect(writes).toEqual([`PATCH ${projectPath}`]);
});

for (const source of ["session", "reconcile"] as const) {
  test(`draft recovery explains ${source} ownership and keeps held restore readable`, async ({ page, request, workbench }, testInfo) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
    await page.getByRole("button", { name: "保存并继续到来源", exact: true }).click();
    await expect(page).toHaveURL(/[?&]project=/);
    const id = new URL(page.url()).searchParams.get("project")!;
    const endpoint = `${workbench.apiOrigin}/api/v2/projects/${id}`;
    const draftPattern = `**/api/v2/projects/${id}/authoring-drafts`;
    await page.getByRole("button", { name: /项目简报与创作设置/ }).click();
    await expect(page.getByRole("heading", { name: "项目简报", exact: true })).toBeVisible();
    const canonical = await (await request.get(endpoint)).json();
    if (source === "reconcile") {
      const saved = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/authoring-drafts"));
      await page.getByLabel("片名", { exact: true }).fill("项目中已保存的草稿");
      expect((await saved).ok()).toBe(true);
    }
    const serverDrafts = await (await request.get(`${endpoint}/authoring-drafts`)).json();
    // A failed save produces a genuine tab-only buffer; do not seed an invented
    // recovery state or bypass the production draft owner.
    await page.route(draftPattern, route => route.request().method() === "PUT"
      ? route.fulfill({ status: 503, json: { message: "Controlled unavailable draft storage" } })
      : route.continue());
    const failed = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/authoring-drafts"));
    const title = `当前标签页保留输入 · ${source}`;
    await page.getByLabel("片名", { exact: true }).fill(title);
    expect((await failed).status()).toBe(503);
    await page.reload();
    const dialog = page.getByRole("dialog", { name: "发现可恢复草稿", exact: true });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(source === "session"
      ? "此草稿只保留在当前标签页。恢复后会自动保存到项目中，不会修改已确认内容。"
      : "当前标签页与项目中各有一份草稿。恢复后会自动保存本标签页的输入，替换项目中这份草稿；已确认内容保持不变。");
    await captureDialog(page, dialog, testInfo, `${source}-ready`);
    expect(await (await request.get(`${endpoint}/authoring-drafts`)).json()).toEqual(serverDrafts);

    let release!: () => void;
    const held = new Promise<void>(resolve => { release = resolve; });
    let started!: () => void;
    const requested = new Promise<void>(resolve => { started = resolve; });
    const projectPattern = `**/api/v2/projects/${id}`;
    await page.route(projectPattern, async route => {
      if (route.request().method() === "GET") { started(); await held; }
      await route.continue();
    });
    try {
      await dialog.getByRole("button", { name: "恢复草稿", exact: true }).click();
      await requested;
      await expect(dialog.getByRole("button", { name: "正在核实…", exact: true })).toBeDisabled();
      await expect(dialog.getByRole("button", { name: "丢弃草稿", exact: true })).toBeDisabled();
      await captureDialog(page, dialog, testInfo, `${source}-verifying`);
      expect(await (await request.get(endpoint)).json()).toEqual(canonical);
      expect(await (await request.get(`${endpoint}/authoring-drafts`)).json()).toEqual(serverDrafts);
      await page.unroute(draftPattern);
    } finally { release(); }
    await expect(dialog).toBeHidden();
    await expect(page.getByLabel("片名", { exact: true })).toHaveValue(title);
    await expect.poll(async () => (await (await request.get(`${endpoint}/authoring-drafts`)).json())[0]?.payload.title).toBe(title);
    expect(await (await request.get(endpoint)).json()).toEqual(canonical);
    await page.unroute(projectPattern);
  });
}

async function captureDialog(page: Page, dialog: Locator, testInfo: TestInfo, state: string) {
  for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(viewport);
    await expect(dialog.locator(".modal-card")).toBeVisible();
    expect(await dialog.locator(".modal-card").evaluate(element => {
      const b = element.getBoundingClientRect();
      return b.left >= 0 && b.top >= 0 && b.right <= innerWidth && b.bottom <= innerHeight;
    })).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`${state}-${viewport.width}x${viewport.height}.png`) });
  }
}
