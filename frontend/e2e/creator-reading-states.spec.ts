import type { Locator, Page, TestInfo } from "@playwright/test";
import { expect, test } from "./fixture";
import { createAcceptedCastOnlyProject } from "./fixtures/cast-reference";
import { json } from "./f5a-fixture";
import { demoProject } from "../src/demo";

const desktopSizes = [[1700, 900], [1280, 768], [1280, 460]] as const;

async function captureControl(page: Page, testInfo: TestInfo, name: string, control: Locator) {
  for (const [width, height] of desktopSizes) {
    await page.setViewportSize({ width, height });
    await control.evaluate(element => element.scrollIntoView({ block: "center" }));
    const bounds = await control.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.y).toBeGreaterThanOrEqual(58);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height - 12);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`${name}-${width}x${height}.png`) });
  }
}

test("gallery read failure has read-only local retry, distinct from an empty image collection", async ({ page, request, workbench }, testInfo) => {
  const id = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "ui-gallery-recovery");
  let failRead = true;
  await page.route(`**/api/v2/projects/${id}/character-references`, async route => {
    if (failRead) await route.fulfill({ status: 503, json: { message: "角色参考读取暂时不可用" } });
    else await route.continue();
  });
  const writes: string[] = [];
  page.on("request", pending => { if (pending.url().includes("/api/v2/") && pending.method() !== "GET") writes.push(pending.method()); });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`);
  const failed = page.locator(".character-reference-review").filter({ has: page.getByRole("alert") });
  await expect(failed).toContainText("角色参考读取暂时不可用");
  await expect(page.getByTestId("reference-no-image")).toHaveCount(0);
  await captureControl(page, testInfo, "gallery-initial-read-failure", failed);
  failRead = false;
  await failed.getByRole("button", { name: "重新读取角色参考" }).click();
  const gallery = page.getByTestId("character-reference-gallery");
  await expect(gallery).toContainText("已确认角色设定 r1");
  await expect(gallery.getByTestId("reference-no-image")).toBeVisible();
  await expect(gallery).toContainText("这个角色还没有候选图片或已选用的参考图片");
  await expect(gallery.locator(".appearance-viewer-heading")).toContainText("尚无参考图片");
  await expect(gallery.locator(".appearance-viewer-heading")).not.toContainText("当前身份参考");
  await captureControl(page, testInfo, "gallery-confirmed-no-images", gallery.getByTestId("reference-no-image"));
  await captureControl(page, testInfo, "gallery-no-reference-heading", gallery.locator(".appearance-viewer-heading"));
  expect(writes).toEqual([]);
});

test("archived gallery offers reading rather than disabled mutation instructions", async ({ page, request, workbench }, testInfo) => {
  const id = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "ui-gallery-archived");
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const project = await json(request.get(root));
  await json(request.post(`${root}/archive`, { data: { expectedLifecycleRevision: project.lifecycleRevision } }));
  const writes: string[] = [];
  page.on("request", pending => { if (pending.url().includes("/api/v2/") && pending.method() !== "GET") writes.push(pending.method()); });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`);
  const gallery = page.getByTestId("character-reference-gallery");
  await expect(gallery).toContainText("已确认角色设定 r1");
  await expect(gallery.getByLabel("想法")).toBeDisabled();
  await expect(page.locator(".cast-next-action")).toContainText("此项目为只读，不能准备或发送角色设定任务");
  await captureControl(page, testInfo, "gallery-archived-guidance", gallery.locator(".reference-gallery-intro"));
  await expect(gallery).toContainText("此项目为只读");
  await expect(gallery).not.toContainText("可以审阅、选择、准备并发送新提案");
  expect(writes).toEqual([]);
});

test("Bible entity forms and archived deep link remain readable without writing content", async ({ page, request, workbench }, testInfo) => {
  const created = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `ui-bible-reading-${Date.now()}` },
    data: { brief: { ...demoProject.brief, title: "UI Bible reading fixture" }, initialStages: [{ stage: "story_bible", payload: demoProject.storyBible }] },
  }));
  const id = created.id;
  const writes: string[] = [];
  page.on("request", pending => { if (pending.url().includes("/api/v2/") && pending.method() !== "GET") writes.push(pending.method()); });
  for (const [type, entity, name] of [["character", "char_ruanxing", "阮星"], ["location", "loc_control", "记忆控制室"], ["prop", "prop_lever", "应急杆"]] as const) {
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=bible&entity=${encodeURIComponent(`bible:${type}:${entity}`)}`);
    const inspector = page.getByTestId(`${type}-inspector`);
    await expect(inspector.getByTestId(`${type}-name`)).toHaveValue(name);
    await expect(inspector.getByLabel("固定标识（ID）")).toHaveValue(entity);
    await captureControl(page, testInfo, `bible-${type}-top`, inspector.locator(".field").first());
    await captureControl(page, testInfo, `bible-${type}-bottom`, inspector.locator(".field").last());
  }
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const beforeArchive = await json(request.get(root));
  await json(request.post(`${root}/archive`, { data: { expectedLifecycleRevision: beforeArchive.lifecycleRevision } }));
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=bible&entity=${encodeURIComponent("bible:character:char_ruanxing")}`);
  const inspector = page.getByTestId("character-inspector");
  await expect(inspector.getByTestId("character-name")).toHaveValue("阮星");
  await expect(inspector.getByTestId("character-name")).toBeDisabled();
  await expect(page.getByRole("button", { name: "保存故事圣经", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "正在保存…", exact: true })).toHaveCount(0);
  await captureControl(page, testInfo, "bible-archived-entity", inspector.locator(".field").first());
  expect(writes).toEqual([]);
});
