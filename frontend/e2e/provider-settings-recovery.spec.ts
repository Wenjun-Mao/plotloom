import { expect, test } from "./fixture";

test("keeps failed provider saves visible in the dialog and retries only explicitly", async ({ page, request, workbench }, info) => {
  const url = `${workbench.apiOrigin}/api/v2/text-provider-profiles/default`;
  const before = await (await request.get(url)).json();
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "供应商与会话密钥" }).click();
  const dialog = page.getByRole("dialog", { name: "供应商与会话密钥" });
  await expect(dialog.locator("header").getByRole("button", { name: "关闭", exact: true })).toBeFocused();
  await dialog.getByLabel("文本模型", { exact: true }).fill("qa-retained-model");
  let attempts = 0;
  await page.route("**/api/v2/text-provider-profiles/default", async route => {
    if (route.request().method() !== "PUT") return route.continue();
    attempts += 1;
    await route.fulfill({ status: 503, json: { message: "配置服务暂不可用，请稍后重试。" } });
  });
  await dialog.getByRole("button", { name: "保存设置", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "保存设置", exact: true })).toBeEnabled();
  // Capture the actual failure before asserting where feedback must be shown.
  await page.screenshot({ path: info.outputPath("failed-save.png") });
  await expect(dialog.getByRole("alert")).toContainText("配置服务暂不可用");
  await expect(dialog.getByLabel("文本模型", { exact: true })).toHaveValue("qa-retained-model");
  expect(attempts).toBe(1);
  expect(await (await request.get(url)).json()).toEqual(before);
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    await expect(dialog.getByRole("alert")).toBeInViewport();
    await expect(dialog.getByRole("button", { name: "保存设置", exact: true })).toBeInViewport();
    await page.screenshot({ path: info.outputPath(`failed-save-${width}x${height}.png`) });
  }
  await page.unroute("**/api/v2/text-provider-profiles/default");
  await dialog.getByRole("button", { name: "保存设置", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  expect((await (await request.get(url)).json()).configuration.textModel).toBe("qa-retained-model");
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("owns a pending provider save until its response without allowing dismissal or lost edits", async ({ page, workbench }, info) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "供应商与会话密钥" }).click();
  const dialog = page.getByRole("dialog", { name: "供应商与会话密钥" });
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let started!: () => void;
  const received = new Promise<void>(resolve => { started = resolve; });
  await page.route("**/api/v2/text-provider-profiles/default", async route => {
    if (route.request().method() !== "PUT") return route.continue();
    started(); await held;
    await route.fulfill({ status: 503, json: { message: "配置服务暂不可用，请稍后重试。" } });
  });
  try {
    await dialog.getByRole("button", { name: "保存设置", exact: true }).click();
    await received;
    for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
      await page.setViewportSize({ width, height });
      await expect(dialog.getByRole("button", { name: "取消", exact: true })).toBeInViewport();
      await page.screenshot({ path: info.outputPath(`pending-save-${width}x${height}.png`) });
    }
    await expect.soft(dialog.getByRole("button", { name: "取消", exact: true })).toBeDisabled();
    for (const close of await dialog.getByRole("button", { name: "关闭", exact: true }).all()) {
      await expect.soft(close).toBeDisabled();
    }
    await expect.soft(dialog.getByLabel("文本模型", { exact: true })).toBeDisabled();
    const escapedFocus: string[] = [];
    for (let i = 0; i < 8; i += 1) {
      await page.keyboard.press("Tab");
      const outside = await page.evaluate(() => {
        const active = document.activeElement;
        return active && active !== document.body && !active.closest('dialog, [role="dialog"]')
          ? active.getAttribute("aria-label") || active.textContent?.trim() || active.tagName : "";
      });
      if (outside) escapedFocus.push(outside);
    }
    expect(escapedFocus).toEqual([]);
    await page.keyboard.press("Escape");
    await expect(dialog).toBeVisible();
  } finally { release(); }
  await expect(dialog.getByRole("button", { name: "保存设置", exact: true })).toBeEnabled();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("button", { name: "供应商与会话密钥", exact: true })).toBeFocused();
});
