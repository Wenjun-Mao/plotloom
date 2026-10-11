import { expect, test } from "./fixture";
import { createScriptProject, writeDelivery, prepare } from "./f5a-fixture";

test("Storyboard guide follows current native review and independent production preparation", async ({ page, request, workbench }, info) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "storyboard-guide");
  let boardReads = 0, bridgeReads = 0;
  for (const [endpoint, count] of [["storyboard-source-review", () => boardReads++], ["production-bridge", () => bridgeReads++]] as const) {
    await page.route(`**/api/v2/projects/${id}/${endpoint}`, async route => { if (route.request().method() === "GET") count(); await route.continue(); });
  }
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const guide = page.getByTestId("recommended-workflow"), panel = page.getByTestId("storyboard-review");
  await expect(guide).toContainText("当前没有分镜候选。点击「准备分镜任务」");
  // Development StrictMode replays the owner's mount effect, not guide reads.
  expect(boardReads).toBe(2); expect(bridgeReads).toBe(0);
  const prepared = await prepare(page, panel, id);
  await expect(guide).toContainText("分镜任务已准备，尚未交付");
  await writeDelivery(prepared);
  await panel.getByRole("button", { name: "立即检查", exact: true }).click();
  await expect(guide).toContainText("点击「查看待审阅分镜」");
  await expect(guide).toContainText("点击「确认此分镜评审方案」");
  for (const size of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(size);
    await panel.getByRole("button", { name: "确认此分镜评审方案", exact: true }).scrollIntoViewIfNeeded();
    await expect(guide).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
    await page.screenshot({ path: info.outputPath(`storyboard-confirm-${size.width}x${size.height}.png`) });
  }
  await panel.getByRole("button", { name: "确认此分镜评审方案", exact: true }).click();
  await expect(guide).toContainText("点击下方「准备投产提案」");
  // The bridge's layout-effect replay aborts before the first request reaches the server.
  expect(bridgeReads).toBe(1);
  await expect(page.getByTestId("production-bridge").getByRole("button", { name: "准备投产提案", exact: true })).toBeEnabled();
  await page.screenshot({ path: info.outputPath("storyboard-production-next.png") });
  await page.getByTestId("production-bridge").getByRole("button", { name: "准备投产提案", exact: true }).click();
  await expect(guide).toContainText("保存戏剧意图整包");
  await expect(guide).not.toContainText("点击「确认投产提案」");
});

test("Storyboard guide stays unknown on held or failed reads and names the actual retry", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "storyboard-guide-retry");
  let mode: "held" | "failed" | "native" = "held", release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route(`**/api/v2/projects/${id}/storyboard-source-review`, async route => {
    if (mode === "held") await held;
    if (mode === "failed") await route.fulfill({ status: 503, json: { detail: "Temporary review read failure" } });
    else await route.continue();
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const guide = page.getByTestId("recommended-workflow");
  await expect(guide).toContainText("正在读取当前分镜评审状态");
  mode = "failed"; release();
  await expect(guide).toContainText("重试加载分镜评审");
  await expect(guide).not.toContainText("当前没有分镜候选");
  mode = "native";
  await page.getByRole("button", { name: "重试加载分镜评审", exact: true }).click();
  await expect(guide).toContainText("点击「准备分镜任务」");
});
