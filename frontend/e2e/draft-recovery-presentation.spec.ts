import { expect, test } from "./fixture";
import type { Locator, Page, TestInfo } from "@playwright/test";
import { demoProject } from "../src/demo";

test("matching server working input resumes automatically; explicit Apply alone changes confirmed Brief", async ({ page, request, workbench }) => {
  const endpoint = `${workbench.apiOrigin}/api/v2/projects`;
  const project = await (await request.post(endpoint, { data: { brief: demoProject.brief, initialStages: [] } })).json();
  const url = `${workbench.frontendOrigin}/v2/?project=${project.id}&stage=brief`, title = "自动继续的编辑输入";
  await page.goto(url); await page.getByLabel("片名", { exact: true }).fill(title);
  await expect.poll(async () => (await (await request.get(`${endpoint}/${project.id}/authoring-drafts`)).json())[0]?.payload.title).toBe(title);
  await page.reload(); await expect(page.getByLabel("片名", { exact: true })).toHaveValue(title);
  await expect(page.getByRole("dialog", { name: "发现可恢复草稿" })).toHaveCount(0);
  expect((await (await request.get(`${endpoint}/${project.id}`)).json()).brief).toEqual(project.brief);
  const saved = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().endsWith(`/projects/${project.id}`));
  await page.getByRole("button", { name: "应用修改", exact: true }).click(); expect((await saved).ok()).toBe(true);
  expect((await (await request.get(`${endpoint}/${project.id}`)).json()).brief.title).toBe(title);
});

for (const source of ["local-only", "server-plus-local"] as const) test(`a fresh document retains ${source} competing input for exact copy or discard`, async ({ page, request, workbench }, info) => {
  const endpoint = `${workbench.apiOrigin}/api/v2/projects`;
  const created = await (await request.post(endpoint, { data: { brief: demoProject.brief, initialStages: [] } })).json();
  const root = `${endpoint}/${created.id}`, url = `${workbench.frontendOrigin}/v2/?project=${created.id}&stage=brief`;
  await page.goto(url);
  if (source === "server-plus-local") {
    await page.getByLabel("片名", { exact: true }).fill("服务器已确认收到的工作输入 A");
    await expect.poll(async () => (await (await request.get(`${root}/authoring-drafts`)).json())[0]?.payload.title).toBe("服务器已确认收到的工作输入 A");
  }
  const original = await (await request.get(`${root}/authoring-drafts`)).json();
  const pattern = `**/api/v2/projects/${created.id}/authoring-drafts`;
  await page.route(pattern, route => route.request().method() === "PUT" ? route.fulfill({ status: 503, json: { message: "owned fixture offline" } }) : route.continue());
  const title = `未同步输入 B · ${source}`;
  const failed = page.waitForResponse(response => response.request().method() === "PUT" && response.url().endsWith(`/${created.id}/authoring-drafts`));
  await page.getByLabel("片名", { exact: true }).fill(title); expect((await failed).status()).toBe(503);
  await expect.poll(() => page.evaluate(() => JSON.stringify(localStorage))).toContain(title);
  await page.reload();
  const conflict = page.getByRole("dialog", { name: "草稿版本已过期", exact: true }); await expect(conflict).toBeVisible();
  await captureDialog(page, conflict, info, `retained-${source}`);
  expect(await (await request.get(`${root}/authoring-drafts`)).json()).toEqual(original);
  expect((await (await request.get(root)).json()).brief).toEqual(created.brief);
  if (source === "local-only") {
    await page.unroute(pattern); await conflict.getByRole("button", { name: "复制草稿为新项目", exact: true }).click();
    await expect(page).not.toHaveURL(new RegExp(`project=${created.id}(?:&|$)`));
    await expect(page.getByLabel("片名", { exact: true })).toHaveValue(title);
    const copy = new URL(page.url()).searchParams.get("project")!;
    expect((await (await request.get(`${endpoint}/${copy}`)).json()).brief).toBeNull();
  } else {
    await conflict.getByRole("button", { name: "丢弃冲突草稿", exact: true }).click();
    await expect(page.getByLabel("片名", { exact: true })).toHaveValue("服务器已确认收到的工作输入 A");
    expect(await (await request.get(`${root}/authoring-drafts`)).json()).toEqual(original);
  }
  expect((await (await request.get(`${workbench.providerOrigin}/control/status`)).json()).totalRequests).toBe(0);
});

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

test("English manual defaults survive durable draft recovery inside Chinese chrome", async ({ page, request, workbench }, info) => {
  test.setTimeout(90_000);
  const endpoint = `${workbench.apiOrigin}/api/v2/projects`;
  const brief = { ...demoProject.brief, language: "en-US", title: "English manual fixture" };
  const response = await request.post(endpoint, { data: { brief, initialStages: [
    { stage: "story_bible", payload: demoProject.storyBible }, { stage: "story_graph", payload: demoProject.storyGraph },
    { stage: "scene_beats", payload: demoProject.sceneBeats }, { stage: "storyboard", payload: demoProject.storyboard },
  ] } });
  expect(response.ok()).toBe(true);
  const project = await response.json(), root = `${endpoint}/${project.id}`;
  const drafts = async () => (await (await request.get(`${root}/authoring-drafts`)).json()) as Array<{ editorScope: string; payload: Record<string, unknown> }>;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=brief`);
  await page.getByLabel("片名", { exact: true }).fill("");
  await page.getByRole("button", { name: "科幻", exact: true }).click();
  await expect.poll(async () => (await drafts()).find(draft => draft.editorScope === "brief")?.payload.title).toBe("");
  await page.reload();
  await expect(page.getByLabel("语言", { exact: true })).toHaveValue("en-US");
  await expect(page.getByLabel("片名", { exact: true })).toHaveValue("");
  await page.getByRole("button", { name: "应用修改", exact: true }).click();
  await expect.poll(async () => (await (await request.get(root)).json()).brief.title).toBe("Untitled story");
  const savedBrief = (await (await request.get(root)).json()).brief;
  expect(savedBrief.genreSelections).toContainEqual({ group: "subject", value: "科幻" });
  await page.reload();
  await expect(page.getByLabel("片名", { exact: true })).toHaveValue("Untitled story");
  await expect(page.getByRole("button", { name: "移除科幻", exact: true })).toBeVisible();

  expect((await (await request.get(`${workbench.providerOrigin}/control/status`)).json()).totalRequests).toBe(0);
});

test("English manual entity scene narrator and shot defaults recover without changing originals", async ({ page, request, workbench }, info) => {
  test.setTimeout(90_000);
  const endpoint = `${workbench.apiOrigin}/api/v2/projects`;
  const brief = { ...demoProject.brief, language: "en-US", title: "English manual fixture" };
  const response = await request.post(endpoint, { data: { brief, initialStages: [
    { stage: "story_bible", payload: demoProject.storyBible }, { stage: "story_graph", payload: demoProject.storyGraph },
    { stage: "scene_beats", payload: demoProject.sceneBeats }, { stage: "storyboard", payload: demoProject.storyboard },
  ] } });
  expect(response.ok()).toBe(true);
  const project = await response.json(), root = `${endpoint}/${project.id}`;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=bible`);
  await page.getByTestId("add-character").click();
  await expect(page.getByTestId("character-name")).toHaveValue("Unnamed entity");
  await expect(page.locator(".draft-save-status")).toHaveText("已自动保存");
  await page.reload();
  await expect(page.getByTestId("character-name")).toHaveValue("Unnamed entity");

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=beats`);
  await page.getByTestId("beat-card-b1").getByRole("button", { name: "添加对白条目", exact: false }).click();
  const narrator = page.getByLabel("画外音身份", { exact: true });
  await expect(narrator).toHaveValue("Narrator");
  await expect(page.getByLabel("语言", { exact: true }).last()).toHaveValue("en-US");
  await expect(page.locator(".draft-save-status")).toHaveText("已自动保存");
  await page.reload();
  await expect(page.getByLabel("画外音身份", { exact: true })).toHaveValue("Narrator");
  await page.getByRole("button", { name: "添加场景", exact: false }).click();
  await page.getByTestId("scene-list").getByText("New scene", { exact: true }).click();
  await expect(page.getByLabel("场景标题", { exact: true })).toHaveValue("New scene");
  await expect(page.locator(".draft-save-status")).toHaveText("已自动保存");
  await page.reload();
  await expect(page.getByTestId("scene-list")).toContainText("New scene");

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=storyboard`);
  await page.getByTestId("add-shot-scene_arrival").click();
  await expect(page.getByLabel("标题", { exact: true })).toHaveValue("New shot");
  await expect(page.getByLabel("机位角度", { exact: true })).toHaveValue("Eye level");
  await expect(page.locator(".draft-save-status")).toHaveText("已自动保存");
  await page.reload();
  await expect(page.getByLabel("标题", { exact: true })).toHaveValue("New shot");
  for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }]) {
    await page.setViewportSize(viewport);
    await page.getByLabel("标题", { exact: true }).scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
    await page.screenshot({ path: info.outputPath(`english-manual-chinese-ui-${viewport.width}.png`) });
  }
  // Existing authored Chinese content is source evidence and remains untouched.
  const after = await (await request.get(root)).json();
  expect(after.brief.language).toBe("en-US");
  const stages = await (await request.get(`${root}/stages`)).json();
  expect(stages.stages.find((entry: { head: { stage: string } }) => entry.head.stage === "story_bible").payload).toEqual(demoProject.storyBible);
  expect(stages.stages.find((entry: { head: { stage: string } }) => entry.head.stage === "scene_beats").payload).toEqual(demoProject.sceneBeats);
  expect(stages.stages.find((entry: { head: { stage: string } }) => entry.head.stage === "storyboard").payload).toEqual(demoProject.storyboard);
  expect((await (await request.get(`${workbench.providerOrigin}/control/status`)).json()).totalRequests).toBe(0);
});
