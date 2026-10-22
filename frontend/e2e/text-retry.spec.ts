import { textRetryTest as test, expect } from "./fixture";

test("real validator failure details grant one directed correction and retain adopted readback", async ({ page, request, workbench }) => {
  test.setTimeout(90_000);
  const identity = await request.get(`${workbench.apiOrigin}/api/v2/fixture/text-retry`).then(response => response.json());
  const base = `${workbench.apiOrigin}/api/v2/projects/${identity.projectId}/autopilot`;
  const before = await request.get(base).then(response => response.json());
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/e2e/text-retry-fixture.html`);
  const card = page.getByRole("region", { name: "文字任务问题" });
  await expect(card).toContainText("自动修正已关闭");
  await expect(page.getByRole("button", { name: "继续原任务", exact: true })).toHaveCount(0);
  await card.getByRole("button", { name: "查看问题", exact: true }).click();
  await expect(card).toContainText("props[0].image.prompt");
  await expect(card).toContainText("handheld scale");
  await expect(card).toContainText("Brass key");
  await card.getByRole("button", { name: "修改要求后重试", exact: true }).click();
  await card.getByRole("textbox", { name: "补充修正要求（可选）" }).fill("保留原简报，明确钥匙是手持尺度。");
  await page.screenshot({ path: "../output/playwright/text-failure-card-1280.png", fullPage: true });
  const response = page.waitForResponse(response => response.url().endsWith("/text-retry") && response.request().method() === "POST");
  await card.getByRole("button", { name: "再修正一次", exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect.poll(async () => {
    const value = await request.get(base).then(response => response.json());
    return value.checkpoints.find((item: { operationKey: string }) => item.operationKey === "art:correction:1")?.state;
  }, { timeout: 40_000 }).toBe("adopted");
  await page.getByRole("button", { name: "读取已采用美术", exact: true }).click();
  await expect(page.getByTestId("adopted-readback")).toContainText("handheld scale");
  const resolved = page.getByRole("region", { name: "美术方向修正历史" });
  await expect(resolved).toContainText("已修正并采用");
  await resolved.getByRole("button", { name: "查看问题", exact: true }).click();
  await expect(resolved).toContainText("本次追加 1 · 已采用");
  await expect(resolved.getByRole("button", { name: "再修正一次", exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(1280);
  await page.screenshot({ path: "../output/playwright/text-correction-resolved-1280.png", fullPage: true });
  const after = await request.get(base).then(response => response.json());
  for (const stage of ["outline", "branches", "characters"]) {
    expect(after.checkpoints.find((item: { operationKey: string }) => item.operationKey === stage))
      .toEqual(before.checkpoints.find((item: { operationKey: string }) => item.operationKey === stage));
  }
});
