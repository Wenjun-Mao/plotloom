import { expect, test } from "./fixture";
import { createScriptProject, fixture, json, writeDelivery, type Preparation } from "./f5a-fixture";

test("Script guide follows native preparation, delivery, confirmation and chapter drafts", async ({ page, request, workbench }, info) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "script-guide", {}, ["cast", "art"]);
  const base = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#script`);
  const guide = page.getByTestId("recommended-workflow"), panel = page.getByTestId("script-review");
  await expect(guide).toContainText("当前没有剧本候选。点击「准备剧本任务」");
  await expect(guide).not.toContainText("审阅当前剧本");
  for (const size of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(size);
    await panel.getByRole("button", { name: "准备剧本任务", exact: true }).scrollIntoViewIfNeeded();
    await expect(guide).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
    await page.screenshot({ path: info.outputPath(`script-prepare-${size.width}x${size.height}.png`) });
  }
  const preparation = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${id}/script/candidates`);
  await panel.getByRole("button", { name: "准备剧本任务", exact: true }).click();
  const prepared = await json<Preparation>(await preparation);
  await expect(guide).toContainText("剧本任务已准备，尚未交付");
  await expect(guide).not.toContainText("查看待审阅剧本");
  // Deterministic technical delivery; no specialist dispatch or media generation.
  await writeDelivery(prepared, "script", await fixture("script.json"));
  await panel.getByRole("button", { name: "立即检查", exact: true }).click();
  await expect(guide).toContainText("点击「查看待审阅剧本」");
  await expect(guide).toContainText("点击「确认使用此剧本」");
  await panel.getByText("查看待审阅剧本", { exact: true }).click();
  await panel.getByRole("button", { name: "确认使用此剧本", exact: true }).click();
  await expect(guide).toContainText("完整剧本已确认。点击「继续：分镜评审」");
  await expect(panel.getByRole("button", { name: "继续：分镜评审", exact: true })).toBeEnabled();
  const replacement = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${id}/script/candidates`);
  await panel.getByRole("button", { name: "准备剧本任务", exact: true }).click();
  const replacementPrepared = await json<Preparation>(await replacement);
  await expect(guide).toContainText("剧本任务已准备，尚未交付");
  await expect(guide).not.toContainText("剧本依据已变化");
  await writeDelivery(replacementPrepared, "script", await fixture("script.json"));
  await panel.getByRole("button", { name: "立即检查", exact: true }).click();
  await expect(guide).toContainText("点击「确认使用此剧本」");
  await expect(guide).not.toContainText("剧本依据已变化");
  await panel.getByRole("button", { name: "确认使用此剧本", exact: true }).click();
  await expect(guide).toContainText("完整剧本已确认");
  await panel.getByRole("button", { name: "重新打开剧本", exact: true }).click();
  await expect(guide).toContainText("剧本修订已打开。选择「编辑章节」");
  await panel.getByRole("combobox", { name: "编辑章节", exact: true }).selectOption("opening");
  const chapter = panel.getByLabel("opening 章节剧本 JSON", { exact: true });
  const original = await chapter.inputValue();
  await chapter.fill(`${original}\n `);
  await expect(guide).toContainText("章节有未保存修改");
  await expect(guide).not.toContainText("继续：分镜评审");
  await panel.getByRole("button", { name: "舍弃当前章节修改", exact: true }).click();
  await expect(guide).toContainText("剧本修订已打开");
  expect((await json(request.get(`${base}/runs`))).runs).toEqual([]);
});

test("Script guide stays unknown on held or failed reads and names the real retry", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "script-guide-retry", {}, ["cast", "art"]);
  let mode: "held" | "failed" | "native" = "held", release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route(`**/api/v2/projects/${id}/script`, async route => {
    if (mode === "held") await held;
    if (mode === "failed") await route.fulfill({ status: 503, json: { detail: "Temporary script read failure" } });
    else await route.continue();
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#script`);
  const guide = page.getByTestId("recommended-workflow"), panel = page.getByTestId("script-review");
  await expect(guide).toContainText("正在读取当前剧本状态");
  await expect(guide).not.toContainText("当前没有剧本候选");
  mode = "failed"; release();
  await expect(guide).toContainText("点击本页「重试加载剧本」");
  await expect(guide).not.toContainText("准备剧本任务");
  mode = "native";
  await panel.getByRole("button", { name: "重试加载剧本", exact: true }).click();
  await expect(guide).toContainText("当前没有剧本候选。点击「准备剧本任务」");
  await expect(panel.getByRole("button", { name: "准备剧本任务", exact: true })).toBeEnabled();
});
