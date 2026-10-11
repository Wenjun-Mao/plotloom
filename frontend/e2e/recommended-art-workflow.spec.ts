import { expect, test } from "./fixture";
import { createScriptProject, fixture, json, writeDelivery, type Preparation } from "./f5a-fixture";

test("blocked Script preparation names Art, then Art guide follows its real controls", async ({ page, request, workbench }, info) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "art-guide-prerequisite", {}, ["cast"]);
  const base = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#script`);
  const guide = page.getByTestId("recommended-workflow");
  await page.getByTestId("script-review").getByRole("button", { name: "准备剧本任务", exact: true }).click();
  await expect(guide).toContainText("点击左侧「美术参考」");
  await expect(guide).not.toContainText("点击「准备剧本任务」");
  expect((await json(request.get(`${base}/script`))).candidate).toBeNull();
  await page.getByRole("link", { name: "美术参考", exact: true }).click();
  const panel = page.getByTestId("art-review");
  await expect(guide).toContainText("当前没有美术候选。先选择「美术风格」");
  await expect(panel.getByRole("button", { name: "准备美术设定任务", exact: true })).toBeDisabled();
  await page.setViewportSize({ width: 1280, height: 460 });
  await panel.getByLabel("美术风格", { exact: true }).scrollIntoViewIfNeeded();
  await expect(guide).toBeVisible();
  await page.screenshot({ path: info.outputPath("art-style-next-1280x460.png") });
  await panel.getByLabel("美术风格", { exact: true }).selectOption("realistic");
  await expect(guide).toContainText("美术风格已选择。点击「准备美术设定任务」");
  const response = page.waitForResponse(r => r.request().method() === "POST" && new URL(r.url()).pathname === `/api/v2/projects/${id}/art/candidates`);
  await panel.getByRole("button", { name: "准备美术设定任务", exact: true }).click();
  const prepared = await json<Preparation>(await response);
  await expect(guide).toContainText("美术任务已准备，尚未交付");
  await writeDelivery(prepared, "art", await fixture("art.json"));
  await panel.getByRole("button", { name: "立即检查", exact: true }).click();
  await expect(guide).toContainText("确认使用此美术提案");
  await panel.getByRole("button", { name: "确认使用此美术提案", exact: true }).click();
  await expect(guide).toContainText("地点与道具设定已确认。点击「继续：剧本」");
  await panel.getByRole("button", { name: "继续：剧本", exact: true }).click();
  await expect(guide).toContainText("当前没有剧本候选");
  await expect(guide).not.toContainText("点击左侧「美术参考」");
  expect((await json(request.get(`${base}/runs`))).runs).toEqual([]);
});

test("Art read failure and retry supersede missing-candidate advice", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "art-guide-retry", {}, ["cast"]);
  let failed = true;
  await page.route(`**/api/v2/projects/${id}/art`, async route => {
    if (failed) await route.fulfill({ status: 503, json: { detail: "Temporary Art read failure" } });
    else await route.continue();
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#art`);
  const guide = page.getByTestId("recommended-workflow"), panel = page.getByTestId("art-review");
  await expect(guide).toContainText("重试加载美术参考");
  await expect(guide).not.toContainText("当前没有美术候选");
  failed = false;
  await panel.getByRole("button", { name: "重试加载美术参考", exact: true }).click();
  await expect(guide).toContainText("先选择「美术风格」");
});
