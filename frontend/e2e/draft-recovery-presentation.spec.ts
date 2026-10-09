import { expect, test } from "./fixture";
import type { Locator, Page, TestInfo } from "@playwright/test";

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
