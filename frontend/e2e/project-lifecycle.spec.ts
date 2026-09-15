import type { Locator, Page, Route, TestInfo } from "@playwright/test";
import { expect, test } from "./fixture";

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
    await expect(page.getByLabel("片名")).toHaveValue(secondTitle);
    expect(secondProjectId).not.toBe(firstProjectId);

    await openDirectory(page);
    await openProject(page, firstTitle);
    await expect(page).toHaveURL(new RegExp(`project=${firstProjectId}`));
    await expect(page.getByLabel("片名")).toHaveValue(firstTitle);

    await page.goBack();
    await expect(page).toHaveURL(new RegExp(`project=${secondProjectId}`));
    await expect(page.getByLabel("片名")).toHaveValue(secondTitle);

    await page.goForward();
    await expect(page).toHaveURL(new RegExp(`project=${firstProjectId}`));
    await expect(page.getByLabel("片名")).toHaveValue(firstTitle);
  });

  test("persists a durable draft and installs it only on explicit save", async ({ page, request, workbench }) => {
    const initialTitle = uniqueTitle("E2E draft initial");
    const projectId = await createProject(page, workbench.frontendOrigin, initialTitle);

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
    const recovery = page.getByRole("dialog", { name: "发现未保存草稿" });
    await expect(recovery).toBeVisible();
    await recovery.getByRole("button", { name: "恢复草稿" }).click();
    await expect(page.getByLabel("片名")).toHaveValue(recoveredTitle);
  });

  test("archives, restores, and permanently deletes only after exact-title confirmation", async ({ page, workbench }) => {
    const title = uniqueTitle("E2E lifecycle");
    await createProject(page, workbench.frontendOrigin, title);

    await openDirectory(page);
    await projectItem(page, title).getByRole("button", { name: "归档" }).click();
    await expect(projectItem(page, title)).toHaveCount(0);
    await page.getByLabel("显示归档项目").check();
    await expect(projectItem(page, title)).toContainText("已归档 · 只读");
    await projectItem(page, title).getByRole("button", { name: "恢复" }).click();
    await expect(projectItem(page, title)).toContainText("活动中");

    await projectItem(page, title).getByRole("button", { name: "归档" }).click();
    await expect(projectItem(page, title).getByRole("button", { name: "永久删除" })).toBeVisible();

    let permanentDeleteRequests = 0;
    page.on("request", (request) => {
      if (new URL(request.url()).pathname.endsWith("/permanent-delete")) permanentDeleteRequests += 1;
    });
    page.once("dialog", async (dialog) => {
      expect(dialog.type()).toBe("prompt");
      expect(dialog.message()).toContain(title);
      await dialog.accept(`${title} wrong`);
    });
    await projectItem(page, title).getByRole("button", { name: "永久删除" }).click();
    await expect(page.getByRole("alert")).toContainText("片名不匹配");
    expect(permanentDeleteRequests).toBe(0);

    page.once("dialog", (dialog) => dialog.accept(title));
    await projectItem(page, title).getByRole("button", { name: "永久删除" }).click();
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
      await projectItem(page, title).getByRole("button", { name: "复制" }).click();
      await expect(page.getByRole("alert")).toContainText("E2E lost duplicate response");
      await expect(projectItem(page, title)).toBeVisible();

      await projectItem(page, title).getByRole("button", { name: "复制" }).click();
      await expect.poll(() => projectIdFromPage(page)).not.toBe(sourceId);
      await expect(page.getByLabel("片名")).toHaveValue(title);

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
    await saveBrief(page);
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
      await expect(page.getByLabel("片名")).toHaveValue(secondTitle);
      releaseFirstResponse?.();
      await expect(page.getByLabel("片名")).toHaveValue(secondTitle);
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
  await expect(page.getByLabel("片名")).toHaveValue(title);
  return projectId;
}

async function saveBrief(page: Page): Promise<string> {
  const creation = page.waitForResponse((response) => {
    const request = response.request();
    return request.method() === "POST" && new URL(request.url()).pathname === "/api/v2/projects";
  });
  await page.getByRole("button", { name: "保存简报" }).click();
  expect((await creation).ok()).toBeTruthy();
  await expect.poll(() => projectIdFromPage(page)).not.toBe("");
  return projectIdFromPage(page);
}

async function saveExistingBrief(page: Page, projectId: string): Promise<void> {
  const saved = page.waitForResponse((response) => {
    const request = response.request();
    return request.method() === "PATCH"
      && new URL(request.url()).pathname === `/api/v2/projects/${projectId}`;
  });
  await page.getByRole("button", { name: "保存简报" }).click();
  expect((await saved).ok()).toBeTruthy();
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
