import { expect, test } from "./fixture";
import { createScriptProject, fixture, json, writeDelivery, type Preparation } from "./f5a-fixture";

test("Role guide follows style, preparation, candidate review and Art continuation", async ({ page, request, workbench }, info) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "cast-guide", {}, []);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`);
  const guide = page.getByTestId("recommended-workflow"), panel = page.getByTestId("cast-review");
  await expect(guide).toContainText("当前没有角色候选。先选择「角色图像风格」");
  const prepare = panel.getByRole("button", { name: "准备角色设定任务", exact: true });
  await expect(prepare).toBeDisabled();
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    await prepare.scrollIntoViewIfNeeded(); await expect(guide).toBeVisible();
    await page.screenshot({ path: info.outputPath(`cast-next-${width}x${height}.png`) });
  }
  await panel.getByLabel("角色图像风格", { exact: true }).selectOption("live-action");
  await expect(guide).toContainText("角色图像风格已选择。点击「准备角色设定任务」");
  const response = page.waitForResponse(r => r.request().method() === "POST" && new URL(r.url()).pathname === `/api/v2/projects/${id}/cast/candidates`);
  await prepare.click();
  const prepared = await json<Preparation>(await response);
  await expect(guide).toContainText("角色任务已准备，尚未交付");
  await writeDelivery(prepared, "characters", await fixture("cast.json"));
  await panel.getByRole("button", { name: "立即检查", exact: true }).click();
  await expect(guide).toContainText("确认使用此角色设定");
  await panel.getByRole("button", { name: "确认使用此角色设定", exact: true }).click();
  await expect(guide).toContainText("角色文字已确认。点击「继续：美术参考」");
  await page.getByRole("button", { name: "继续：美术参考", exact: true }).click();
  await expect(guide).toContainText("当前没有美术候选");
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/runs`))).runs).toEqual([]);
});

test("Role read failure names its actual retry instead of reviewing retained state", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "cast-guide-retry", {}, []);
  let failed = true;
  await page.route(`**/api/v2/projects/${id}/cast`, async route => failed ? route.fulfill({ status: 503, json: { detail: "Temporary Cast read failure" } }) : route.continue());
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`);
  const guide = page.getByTestId("recommended-workflow");
  await expect(guide).toContainText("重试加载角色设定");
  failed = false;
  await page.getByTestId("cast-review").getByRole("button", { name: "重试加载角色设定", exact: true }).click();
  await expect(guide).toContainText("先选择「角色图像风格」");
});

test("workspace refresh rechecks accepted Role authority before allowing continuation", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "cast-refresh", {}, ["cast"]);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`);
  const guide = page.getByTestId("recommended-workflow"), panel = page.getByTestId("cast-review");
  await expect(guide).toContainText("角色文字已确认");
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route(`**/api/v2/projects/${id}/cast`, async route => {
    await pending;
    await route.fulfill({ status: 503, json: { detail: "Temporary Cast refresh failure" } });
  });
  await page.getByRole("button", { name: "刷新服务器版本", exact: true }).click();
  await expect(guide).toContainText("正在读取当前角色设定");
  await expect(page.getByRole("button", { name: "继续：美术参考", exact: true })).toBeDisabled();
  await expect(panel.getByRole("button", { name: "编辑角色设定", exact: true })).toBeDisabled();
  release();
  await expect(guide).toContainText("重试加载角色设定");
  await expect(guide).not.toContainText("角色文字已确认");
  await page.unroute(`**/api/v2/projects/${id}/cast`);
  await panel.getByRole("button", { name: "重试加载角色设定", exact: true }).click();
  await expect(guide).toContainText("角色文字已确认");
  await expect(page.getByRole("button", { name: "继续：美术参考", exact: true })).toBeEnabled();
});
