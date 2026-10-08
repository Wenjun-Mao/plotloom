import type { Locator, Page, Route, TestInfo } from "@playwright/test";
import path from "node:path";
import { readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { expect, test } from "./fixture";
import { navigateToSecondaryTool, openMediaPreparation } from "./workbench-controls";

const retainedStill = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../docs/verification/supporting/p0-generated/01-arrival.png");

test.describe("M1-B0 real project journeys", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("requires explicit onboarding, creates two projects, and restores the selected project through browser history", async ({ page, workbench }, testInfo) => {
    await page.goto(`${workbench.frontendOrigin}/v2/?stage=brief`);
    await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
    await expect(page.getByText("教学草案", { exact: true })).toHaveCount(0);
    await expect(page.getByText("示例不会在未选择时自动加载", { exact: false })).toBeVisible();

    const firstTitle = uniqueTitle("E2E project one");
    const firstProjectId = await createProject(page, workbench.frontendOrigin, firstTitle);
    await page.screenshot({
      path: testInfo.outputPath("workbench-1440x900.png"),
      animations: "disabled",
    });

    await openDirectory(page);
    await page.getByRole("button", { name: "新建空白项目" }).click();
    const secondTitle = uniqueTitle("E2E project two");
    await page.getByLabel("片名").fill(secondTitle);
    await page.getByLabel("故事梗概").fill(`A canonical synopsis for ${secondTitle}.`);
    const secondProjectId = await saveBrief(page);
    await returnToBrief(page, workbench.frontendOrigin, secondProjectId);
    await expect(page.getByLabel("片名")).toHaveValue(secondTitle);
    expect(secondProjectId).not.toBe(firstProjectId);

    await openDirectory(page);
    await openProject(page, firstTitle);
    await expect(page).toHaveURL(new RegExp(`project=${firstProjectId}`));
    await expectCreatorProject(page, firstTitle);

    await page.goBack();
    await expect(page).toHaveURL(new RegExp(`project=${secondProjectId}`));
    await expect(page.getByLabel("片名")).toHaveValue(secondTitle);

    await page.goForward();
    await expect(page).toHaveURL(new RegExp(`project=${firstProjectId}`));
    await expectCreatorProject(page, firstTitle);
  });

  test("persists a durable draft and installs it only on explicit save", async ({ page, request, workbench }) => {
    const initialTitle = uniqueTitle("E2E draft initial");
    const projectId = await createProject(page, workbench.frontendOrigin, initialTitle);
    await page.locator(".topbar-technical-status > summary").click();

    const durableTitle = uniqueTitle("E2E durable navigation draft");
    await page.getByLabel("片名").fill(durableTitle);
    await expect(page.getByText("草稿：已保存", { exact: true })).toBeVisible();
    const drafts = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/authoring-drafts`);
    expect(drafts.ok(), await drafts.text()).toBeTruthy();
    expect((await drafts.json()) as Array<{ payload: { title: string } }>).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          payload: expect.objectContaining({ title: durableTitle }),
        }),
      ]),
    );

    const beforeSave = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}`);
    expect((await beforeSave.json() as { brief: { title: string } }).brief.title).toBe(initialTitle);

    let releaseSavePatch: (() => void) | undefined;
    let saveAcknowledged = false;
    let signalSavePatch: (() => void) | undefined;
    const savePatchStarted = new Promise<void>((resolve) => { signalSavePatch = resolve; });
    const releasePatch = new Promise<void>((release) => { releaseSavePatch = release; });
    await page.route(`**/api/v2/projects/${projectId}`, async (route) => {
      if (route.request().method() !== "PATCH") return route.continue();
      signalSavePatch?.();
      await releasePatch;
      await route.continue();
    });
    try {
      const save = saveExistingBrief(page, projectId).then(() => { saveAcknowledged = true; });
      await savePatchStarted;
      expect(saveAcknowledged).toBe(false);
      releaseSavePatch?.();
      await save;
    } finally {
      releaseSavePatch?.();
      await page.unroute(`**/api/v2/projects/${projectId}`);
    }
    const afterSave = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}`);
    expect((await afterSave.json() as { brief: { title: string } }).brief.title).toBe(durableTitle);
    await page.getByText("编辑与工具", { exact: true }).click();
    await page.getByRole("button", { name: "故事圣经" }).first().click();
    await expect(page.getByRole("heading", { name: "故事圣经" })).toBeVisible();
    await page.getByRole("button", { name: "项目简报" }).first().click();
    await expect(page.getByLabel("片名")).toHaveValue(durableTitle);
  });

  test("offers session draft recovery after a refresh", async ({ page, workbench }) => {
    const initialTitle = uniqueTitle("E2E recovery initial");
    await createProject(page, workbench.frontendOrigin, initialTitle);
    const recoveredTitle = uniqueTitle("E2E recovery draft");
    await page.getByLabel("片名").fill(recoveredTitle);

    page.once("dialog", (dialog) => dialog.accept());
    await page.reload();
    const recovery = page.getByRole("dialog", { name: "发现可恢复草稿" });
    await expect(recovery).toBeVisible();
    await recovery.getByRole("button", { name: "恢复草稿" }).click();
    await expect(page.getByLabel("片名")).toHaveValue(recoveredTitle);
  });

  test("archives, restores, and permanently deletes only after exact-title confirmation", async ({ page, request, workbench }) => {
    const title = uniqueTitle("E2E lifecycle");
    const projectId = await createProject(page, workbench.frontendOrigin, title);
    await navigateToSecondaryTool(page, "分镜工作台");
    await openMediaPreparation(page);
    await page.getByLabel("来源声明").fill("Offline lifecycle fixture; not provider generation or creative acceptance.");
    const imported = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/managed-assets`);
    await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
    expect((await imported).ok()).toBeTruthy();
    const candidate = page.getByLabel("候选图像比较").locator(".media-candidate");
    await expect(candidate).toHaveCount(1);
    await expect(candidate.getByRole("img")).toBeVisible();
    const assetEvidence = async () => {
      const response = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
      expect(response.ok()).toBeTruthy();
      const assets = (await response.json() as { assets: Array<{ id: string }> }).assets;
      expect(assets).toHaveLength(1);
      const original = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/managed-assets/${assets[0].id}/original`);
      const display = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/managed-assets/${assets[0].id}/display`);
      expect(original.ok()).toBeTruthy();
      expect(display.ok()).toBeTruthy();
      return { assets, originalBytes: (await original.body()).toString("base64"), displayBytes: (await display.body()).toString("base64") };
    };
    const retained = await assetEvidence();

    await openDirectory(page);
    await projectItem(page, title).getByRole("button", { name: "归档" }).click();
    await expect(projectItem(page, title)).toHaveCount(0);
    await page.getByLabel("显示归档项目").check();
    await expect(projectItem(page, title)).toContainText("已归档 · 只读");
    await openProject(page, title);
    await expect(page.getByText("归档只读", { exact: true })).toBeVisible();
    for (const [view, save] of [
      ["故事圣经", "保存故事圣经"],
      ["场景节拍", "保存节拍计划"],
      ["分镜工作台", "保存分镜"],
    ]) {
      await navigateToSecondaryTool(page, view);
      await expect(page.getByRole("button", { name: save, exact: true })).toBeDisabled();
      await expect(page.getByRole("button", { name: "正在保存…", exact: true })).toHaveCount(0);
    }
    await openMediaPreparation(page);
    await expect(page.getByTestId("managed-image-upload")).toBeDisabled();
    await expect(candidate.getByRole("img")).toBeVisible();
    expect(await assetEvidence()).toEqual(retained);
    await expect(page.getByRole("button", { name: "创建恢复快照", exact: true })).toBeDisabled();
    await openDirectory(page);
    await projectItem(page, title).getByRole("button", { name: "恢复" }).click();
    await expect(projectItem(page, title)).toContainText("当前项目");
    expect(await assetEvidence()).toEqual(retained);

    const archived = page.waitForResponse(response => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/archive`);
    await projectItem(page, title).getByRole("button", { name: "归档" }).click();
    expect((await archived).ok()).toBeTruthy();
    // Delete exists on both active and archived rows; visibility is not an archive receipt.
    await expect(projectItem(page, title)).toContainText("已归档 · 只读");
    await expect(page.getByRole("status").filter({ hasText: "正在读取项目目录" })).toHaveCount(0);
    await expect(projectItem(page, title).getByRole("button", { name: "永久删除" })).toBeEnabled();

    let permanentDeleteRequests = 0;
    page.on("request", (request) => {
      if (new URL(request.url()).pathname.endsWith("/permanent-delete")) permanentDeleteRequests += 1;
    });
    await projectItem(page, title).getByRole("button", { name: "永久删除" }).click();
    const consent = page.getByRole("alertdialog", { name: "永久删除项目" });
    await consent.getByLabel("输入完整片名以确认删除").fill(`${title} wrong`);
    await expect(consent.getByRole("button", { name: "确认永久删除项目" })).toBeDisabled();
    expect(permanentDeleteRequests).toBe(0);
    await consent.getByRole("button", { name: "取消" }).click();
    await projectItem(page, title).getByRole("button", { name: "永久删除" }).click();
    await expect(consent.getByLabel("输入完整片名以确认删除")).toHaveValue("");
    await consent.getByLabel("输入完整片名以确认删除").fill(title);
    const deleted = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/permanent-delete`);
    await consent.getByRole("button", { name: "确认永久删除项目" }).click();
    expect((await deleted).ok()).toBeTruthy();
    await expect(consent).not.toBeVisible();
    await expect(projectItem(page, title)).toHaveCount(0);
    await expect(page.getByRole("status").filter({ hasText: "项目已永久删除" })).toBeVisible();
    expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}`)).status()).toBe(404);
    expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/managed-assets/${retained.assets[0].id}/original`)).status()).toBe(404);
    expect((await readdir(workbench.outputsRoot)).some((name) => name.endsWith(`__${projectId}`))).toBe(false);
    // Deletion clears the selected project but keeps the current tool route.
    // New Blank also keeps that route; return to Brief through its named control.
    await page.getByRole("button", { name: "新建空白项目", exact: true }).click();
    await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
    await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();
    await expect(page.getByLabel("片名")).toHaveValue("");
    expect(permanentDeleteRequests).toBe(1);
  });

  test("replays a duplicate after a lost response without creating a second visible copy", async ({ page, workbench }) => {
    const title = uniqueTitle("E2E duplicate source");
    const sourceId = await createProject(page, workbench.frontendOrigin, title);
    const idempotencyKeys: string[] = [];
    let hidSuccessfulResponse = false;
    const duplicateRoute = async (route: Route) => {
      const key = route.request().headers()["idempotency-key"];
      if (key) idempotencyKeys.push(key);
      const response = await route.fetch();
      if (!hidSuccessfulResponse) {
        hidSuccessfulResponse = true;
        await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "E2E lost duplicate response" }) });
        return;
      }
      await route.fulfill({ response });
    };
    await page.route("**/api/v2/projects/*/duplicate", duplicateRoute);
    try {
      await openDirectory(page);
      await projectItem(page, title).getByRole("button", { name: "复制简报与规范内容" }).click();
      await expect(page.getByRole("alertdialog")).toContainText("不复制来源与大纲");
      await page.getByRole("button", { name: "确认复制简报与规范内容", exact: true }).click();
      await expect(page.getByRole("alert")).toContainText("E2E lost duplicate response");
      await expect(projectItem(page, title)).toBeVisible();

      await projectItem(page, title).getByRole("button", { name: "复制简报与规范内容" }).click();
      await expect(page.getByRole("alertdialog")).toContainText("不复制来源与大纲");
      await page.getByRole("button", { name: "确认复制简报与规范内容", exact: true }).click();
      await expect.poll(() => projectIdFromPage(page)).not.toBe(sourceId);
      await expectCreatorProject(page, title);
      await expect(page.getByRole("status").filter({ hasText: "已创建" })).toContainText("仅项目简报");
      await expect(page.getByRole("status").filter({ hasText: "已创建" })).toContainText("原项目保持不变");
      const copyNotice = page.getByRole("status").filter({ hasText: "已创建" });
      const acknowledge = copyNotice.getByRole("button", { name: "知道了", exact: true });
      const noticeBounds = await acknowledge.boundingBox();
      const sidebarBounds = await page.locator(".sidebar").boundingBox();
      const fullNoticeBounds = await copyNotice.boundingBox();
      expect(fullNoticeBounds!.x).toBeGreaterThanOrEqual(sidebarBounds!.x + sidebarBounds!.width);
      expect(fullNoticeBounds!.x + fullNoticeBounds!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
      expect(noticeBounds!.x).toBeGreaterThanOrEqual(sidebarBounds!.x + sidebarBounds!.width);
      expect(noticeBounds!.x + noticeBounds!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
      await acknowledge.click();
      await expect(copyNotice).toHaveCount(0);

      await openDirectory(page);
      const directory = page.getByRole("dialog", { name: "项目目录" });
      await expect(directory.locator(".directory-item").filter({ hasText: title })).toHaveCount(2);
      expect(idempotencyKeys).toHaveLength(2);
      expect(idempotencyKeys[1]).toBe(idempotencyKeys[0]);
    } finally {
      await page.unroute("**/api/v2/projects/*/duplicate", duplicateRoute);
    }
  });

  test("does not let a delayed project response overwrite the newer selection", async ({ page, workbench }) => {
    const firstTitle = uniqueTitle("E2E delayed first");
    const firstProjectId = await createProject(page, workbench.frontendOrigin, firstTitle);
    await openDirectory(page);
    await page.getByRole("button", { name: "新建空白项目" }).click();
    const secondTitle = uniqueTitle("E2E delayed second");
    await page.getByLabel("片名").fill(secondTitle);
    await page.getByLabel("故事梗概").fill(`A canonical synopsis for ${secondTitle}.`);
    const secondProjectId = await saveBrief(page);
    await returnToBrief(page, workbench.frontendOrigin, secondProjectId);
    await expect(page.getByLabel("片名")).toHaveValue(secondTitle);

    let signalFirstLoad: (() => void) | undefined;
    let releaseFirstResponse: (() => void) | undefined;
    const firstLoadStarted = new Promise<void>((resolve) => { signalFirstLoad = resolve; });
    const firstResponseReleased = new Promise<void>((resolve) => { releaseFirstResponse = resolve; });
    const delayedProjectRoute = async (route: Route) => {
      if (route.request().method() !== "GET") return route.continue();
      signalFirstLoad?.();
      await firstResponseReleased;
      await route.continue();
    };
    await page.route(`**/api/v2/projects/${firstProjectId}`, delayedProjectRoute);
    try {
      await openDirectory(page);
      await openProject(page, firstTitle);
      await firstLoadStarted;

      await openDirectory(page);
      await openProject(page, secondTitle);
      await expectCreatorProject(page, secondTitle);
      releaseFirstResponse?.();
      await expectCreatorProject(page, secondTitle);
    } finally {
      releaseFirstResponse?.();
      await page.unroute(`**/api/v2/projects/${firstProjectId}`, delayedProjectRoute);
    }
  });
});

let titleSequence = 0;

async function createProject(page: Page, frontendOrigin: string, title: string): Promise<string> {
  await page.goto(`${frontendOrigin}/v2/?stage=brief`);
  await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("片名").fill(title);
  await page.getByLabel("故事梗概").fill(`A canonical synopsis for ${title}.`);
  const projectId = await saveBrief(page);
  await returnToBrief(page, frontendOrigin, projectId);
  await expect(page.getByLabel("片名")).toHaveValue(title);
  return projectId;
}

async function saveBrief(page: Page): Promise<string> {
  const creation = page.waitForResponse((response) => {
    const request = response.request();
    return request.method() === "POST" && new URL(request.url()).pathname === "/api/v2/projects";
  });
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  expect((await creation).ok()).toBeTruthy();
  await expect.poll(() => projectIdFromPage(page)).not.toBe("");
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  return projectIdFromPage(page);
}

async function returnToBrief(page: Page, frontendOrigin: string, projectId: string): Promise<void> {
  await page.goto(`${frontendOrigin}/v2/?project=${projectId}&stage=brief`);
  await expect(page.getByRole("button", { name: "保存修改" })).toBeVisible();
}

async function saveExistingBrief(page: Page, projectId: string): Promise<void> {
  const saved = page.waitForResponse((response) => {
    const request = response.request();
    return request.method() === "PATCH"
      && new URL(request.url()).pathname === `/api/v2/projects/${projectId}`;
  });
  await page.getByRole("button", { name: "保存修改" }).click();
  expect((await saved).ok()).toBeTruthy();
  await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();
}

async function expectCreatorProject(page: Page, title: string): Promise<void> {
  await expect(page.getByRole("heading", { name: "创作工作台", exact: true })).toBeVisible();
  await expect(page.locator(".project-switcher")).toContainText(title);
}

async function openDirectory(page: Page): Promise<void> {
  await page.getByRole("button", { name: /当前项目 · 切换/ }).click();
  await expect(page.getByRole("dialog", { name: "项目目录" })).toBeVisible();
}

async function openProject(page: Page, title: string): Promise<void> {
  const directory = page.getByRole("dialog", { name: "项目目录" });
  await projectItem(page, title).locator(".directory-open").click();
  await expect(directory).toBeHidden();
}

function projectItem(page: Page, title: string): Locator {
  return page.getByRole("dialog", { name: "项目目录" }).locator(".directory-item").filter({ hasText: title });
}

function projectIdFromPage(page: Page): string {
  return new URL(page.url()).searchParams.get("project") || "";
}

function uniqueTitle(label: string): string {
  titleSequence += 1;
  return `${label} ${Date.now()}-${titleSequence}`;
}
