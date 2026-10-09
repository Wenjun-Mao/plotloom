import { expect, test } from "./fixture";

test("native composition exposes assistant controls without unsupported API profile requests", async ({ page, request, workbench }, info) => {
  await workbench.restartBackend({ PLOTLOOM_E2E_NATIVE_ONLY: "1" });
  const capabilities = await request.get(`${workbench.apiOrigin}/api/v2/runtime-capabilities`);
  expect(capabilities.ok()).toBe(true);
  expect((await capabilities.json()).textProviderProfiles).toBe(false);
  expect((await request.get(`${workbench.apiOrigin}/api/v2/text-provider-profiles`)).status()).toBe(404);
  const profileRequests: string[] = [];
  page.on("request", req => { if (req.url().includes("/text-provider-profiles")) profileRequests.push(req.method()); });
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await expect(page.locator(".sidebar-footer")).toContainText("API 文本供应商未启用");
  await expect(page.getByRole("button", { name: "供应商与会话密钥", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "生成助手设置", exact: true })).toBeVisible();
  await page.getByText("服务状态", { exact: true }).click();
  await expect(page.locator(".topbar-technical-status")).toContainText("API 文本供应商：未启用");
  await expect(page.locator(".topbar-technical-status")).not.toContainText("readiness.not_checked");
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    await page.locator(".sidebar-footer").scrollIntoViewIfNeeded();
    await expect(page.locator(".sidebar-footer")).toBeInViewport();
    await page.screenshot({ path: info.outputPath(`native-provider-${width}x${height}.png`) });
  }
  expect(profileRequests).toEqual([]);
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("failed capability reads stay unknown until explicit retry enables actual API controls", async ({ page, workbench }, info) => {
  let attempts = 0, profiles = 0, unavailable = true;
  await page.route("**/api/v2/runtime-capabilities", async route => {
    attempts += 1;
    if (unavailable) await route.fulfill({ status: 503, json: { message: "capability read unavailable" } });
    else await route.continue();
  });
  page.on("request", req => { if (req.url().includes("/text-provider-profiles")) profiles += 1; });
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await expect(page.locator(".sidebar-footer")).toContainText("暂时无法读取服务功能");
  await expect(page.locator(".sidebar-footer")).not.toContainText("API 文本供应商未启用");
  await expect(page.getByRole("button", { name: "供应商与会话密钥", exact: true })).toHaveCount(0);
  // Development StrictMode can replay the initial effect. Subsequent reading
  // and scrolling must not create another request without the explicit retry.
  const initialAttempts = attempts;
  expect(initialAttempts).toBeGreaterThan(0);
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    await page.getByRole("button", { name: "重新读取服务功能" }).scrollIntoViewIfNeeded();
    await expect(page.getByRole("button", { name: "重新读取服务功能" })).toBeInViewport();
    await page.screenshot({ path: info.outputPath(`failed-capability-${width}x${height}.png`) });
  }
  expect(attempts).toBe(initialAttempts); expect(profiles).toBe(0);
  unavailable = false;
  await page.getByRole("button", { name: "重新读取服务功能" }).click();
  await page.getByRole("button", { name: "供应商与会话密钥", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "供应商与会话密钥" })).toBeVisible();
  expect(attempts).toBe(initialAttempts + 1);
  expect(profiles).toBe(1);
});
