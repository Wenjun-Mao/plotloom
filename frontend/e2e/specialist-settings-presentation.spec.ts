import { expect, test } from "./fixture";
import type { Locator, Page, TestInfo } from "@playwright/test";

test("assistant settings retains pending operations and failed input, then persists an explicit retry", async ({ page, request, workbench }, testInfo) => {
  const endpoint = `${workbench.apiOrigin}/api/v2/specialists`;
  const pattern = "**/api/v2/specialists";
  const original = await (await request.get(endpoint)).json();
  const writes: string[] = [];
  page.on("request", r => { if (r.url().includes("/api/") && !["GET", "HEAD"].includes(r.method())) writes.push(`${r.method()} ${new URL(r.url()).pathname}`); });
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
  let releaseRead!: () => void;
  const heldRead = new Promise<void>(resolve => { releaseRead = resolve; });
  await page.route(pattern, async route => {
    await heldRead;
    await route.fulfill({ status: 503, json: { detail: "测试读取暂时不可用。" } });
  });
  const dialog = page.getByRole("dialog", { name: "生成助手设置", exact: true });
  try {
    await page.getByRole("button", { name: "生成助手设置", exact: true }).click();
    await expect(dialog.getByRole("status")).toHaveText("正在读取助手设置…");
    await expect(dialog.getByRole("button", { name: "保存助手设置", exact: true })).toBeDisabled();
    await capture(page, dialog, testInfo, "read-pending");
  } finally { releaseRead(); }
  await expect(dialog).toContainText("测试读取暂时不可用。");
  await expect(dialog).not.toContainText("Error:");
  await expect(dialog).not.toContainText("正在读取助手设置…");
  await capture(page, dialog, testInfo, "read-failed");
  await page.unroute(pattern);
  await dialog.getByRole("button", { name: "重试读取助手设置", exact: true }).click();
  const name = dialog.getByLabel("显示名称", { exact: true }).first();
  await expect(name).toHaveValue(original.text.name);
  await expect(dialog).not.toContainText("测试读取暂时不可用。");
  expect(writes).toEqual([]);
  await name.fill("QA 保留未保存的助手名称");

  let releaseSave!: () => void;
  const heldSave = new Promise<void>(resolve => { releaseSave = resolve; });
  await page.route(pattern, async route => {
    if (route.request().method() !== "PUT") return route.continue();
    await heldSave;
    await route.fulfill({ status: 503, json: { detail: "测试保存暂时不可用。" } });
  });
  try {
    await dialog.getByRole("button", { name: "保存助手设置", exact: true }).click();
    await expect(dialog.getByRole("button", { name: "正在保存…", exact: true })).toBeDisabled();
    await expect(name).toBeDisabled();
    await expect(dialog.getByRole("button", { name: "关闭", exact: true })).toBeDisabled();
    await expect(dialog.getByRole("button", { name: "关闭生成助手设置", exact: true })).toBeDisabled();
    await capture(page, dialog, testInfo, "save-pending");
  } finally { releaseSave(); }
  await expect(dialog).toContainText("测试保存暂时不可用。");
  await expect(name).toHaveValue("QA 保留未保存的助手名称");
  await expect(name).toBeEnabled();
  await expect(dialog.getByRole("button", { name: "保存助手设置", exact: true })).toBeEnabled();
  await expect(dialog.getByRole("button", { name: "关闭", exact: true })).toBeEnabled();
  await expect(dialog).not.toContainText("设置已保存");
  await capture(page, dialog, testInfo, "save-failed");
  expect(writes).toEqual(["PUT /api/v2/specialists"]);
  expect(await (await request.get(endpoint)).json()).toEqual(original);
  await page.unroute(pattern);
  await dialog.getByRole("button", { name: "保存助手设置", exact: true }).click();
  await expect(dialog).toContainText("设置已保存，即刻生效。");
  await expect(dialog.getByRole("button", { name: "关闭", exact: true })).toBeEnabled();
  const saved = await (await request.get(endpoint)).json();
  expect(saved).toEqual({ ...original, text: { ...original.text, name: "QA 保留未保存的助手名称" } });
  expect(writes).toEqual(["PUT /api/v2/specialists", "PUT /api/v2/specialists"]);
  await capture(page, dialog, testInfo, "save-succeeded");
  await dialog.getByRole("button", { name: "关闭", exact: true }).click();
  await page.getByRole("button", { name: "生成助手设置", exact: true }).click();
  await expect(dialog.getByLabel("显示名称", { exact: true }).first()).toHaveValue("QA 保留未保存的助手名称");
  await dialog.getByRole("button", { name: "关闭", exact: true }).click();
});

async function capture(page: Page, dialog: Locator, testInfo: TestInfo, state: string) {
  for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(viewport);
    await dialog.locator(".modal-body").evaluate(element => { element.scrollTop = element.scrollHeight; });
    expect(await dialog.locator(".modal-card").evaluate(element => {
      const bounds = element.getBoundingClientRect();
      return bounds.left >= 0 && bounds.top >= 0 && bounds.right <= innerWidth && bounds.bottom <= innerHeight;
    })).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`${state}-${viewport.width}x${viewport.height}.png`) });
  }
}
