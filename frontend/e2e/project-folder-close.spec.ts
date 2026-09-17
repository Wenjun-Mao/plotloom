import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const retainedStill = path.join(repositoryRoot, "docs/verification/supporting/p0-generated/01-arrival.png");

test.describe("project-folder Close", () => {
  test("cancels a prepared source-outline handoff before Close, then reopens", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await page.getByRole("button", { name: "保存简报" }).click();
    await expect(page).toHaveURL(/[?&]project=/);
    await expect(page.getByText("草稿：等待编辑", { exact: true })).toBeVisible();
    const projectId = new URL(page.url()).searchParams.get("project")!;
    await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /^01 来源与大纲/ }).click();
    await page.getByLabel("标题").fill("E2E：取消 handoff 后关闭");
    await page.getByLabel("来源正文或 treatment").fill("作者必须先取消正在等待 specialist 的候选，才能关闭项目。");
    await page.getByLabel("归属 / 署名声明").fill("E2E 测试作者");
    await page.getByLabel("使用权或许可声明").fill("仅用于 E2E 测试；不构成法律确认。");
    await page.getByLabel("改编意图").fill("验证取消、关闭和重新打开的持久化边界。");
    await page.getByRole("button", { name: "保存接受的来源" }).click();
    await page.getByRole("button", { name: "准备 specialist handoff" }).click();
    await expect(page.getByText("等待 specialist")).toBeVisible();
    await page.getByRole("button", { name: "取消并废弃此 handoff" }).click();
    await expect(page.getByText("已取消")).toBeVisible();

    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    const closeResponse = waitForCloseResponse(page, projectId);
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "关闭项目" }).click();
    expect((await closeResponse).ok()).toBeTruthy();
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "重新打开" }).click();
    await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /^01 来源与大纲/ }).click();
    await expect(page.getByRole("heading", { name: "来源与小说大纲" })).toBeVisible();
    await expect(page.getByText("已取消")).toBeVisible();
  });

  test("immediately drains an authoring draft, closes, reopens, and recovers after a file-SQLite restart", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await page.getByRole("button", { name: "保存简报" }).click();
    await expect(page).toHaveURL(/[?&]project=/);
    await expect(page.getByText("草稿：等待编辑", { exact: true })).toBeVisible();
    const projectId = new URL(page.url()).searchParams.get("project")!;
    const canonicalTitle = await page.getByLabel("片名").inputValue();
    const draftTitle = "E2E：关闭期间继续输入的最终草稿";
    let releaseDraft!: () => void;
    const heldDraft = new Promise<void>((resolve) => { releaseDraft = resolve; });
    let markDraftStarted!: () => void;
    const draftStarted = new Promise<void>((resolve) => { markDraftStarted = resolve; });
    let held = false;
    await page.route("**/api/v2/projects/*/authoring-drafts", async (route) => {
      if (!held && route.request().method() === "PUT") {
        held = true;
        markDraftStarted();
        await heldDraft;
      }
      await route.continue();
    });

    // Do not wait for the idle timer. Close must drain this queued local
    // authoring buffer without treating a durable receipt as canonical Save.
    await page.getByLabel("片名").fill("E2E：传输中的较早草稿");
    await draftStarted;
    await page.getByLabel("片名").fill(draftTitle);
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "关闭项目" }).click();
    await expect(page.getByRole("heading", { name: "保存草稿并关闭项目？" })).toBeVisible();
    const closeResponse = waitForCloseResponse(page, projectId);
    await page.getByRole("button", { name: "保存草稿并关闭" }).click();
    releaseDraft();
    expect((await closeResponse).ok()).toBeTruthy();
    await page.unroute("**/api/v2/projects/*/authoring-drafts");

    await workbench.restartBackend();
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "重新打开" }).click();
    await expect(page.getByText("发现未保存草稿", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "恢复草稿" }).click();
    await expect(page.getByLabel("片名")).toHaveValue(draftTitle);

    const canonical = await fetch(`${workbench.apiOrigin}/api/v2/projects/${projectId}`);
    expect(canonical.ok).toBeTruthy();
    expect((await canonical.json()).brief.title).toBe(canonicalTitle);
  });

  test("freezes edits and navigation until a held Close response resolves", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await page.getByRole("button", { name: "保存简报" }).click();
    await expect(page).toHaveURL(/[?&]project=/);
    await expect(page.getByText("草稿：等待编辑", { exact: true })).toBeVisible();
    const projectId = new URL(page.url()).searchParams.get("project")!;

    let releaseClose!: () => void;
    const heldClose = new Promise<void>((resolve) => { releaseClose = resolve; });
    let markCloseStarted!: () => void;
    const closeStarted = new Promise<void>((resolve) => { markCloseStarted = resolve; });
    await page.route("**/api/v2/projects/*/close", async (route) => {
      markCloseStarted();
      await heldClose;
      await route.continue();
    });

    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "关闭项目" }).click();
    await closeStarted;

    await expect(page.getByText("正在关闭项目", { exact: true })).toBeVisible();
    await expect(page.getByLabel("片名")).toBeDisabled();
    const stageNavigation = page.getByRole("navigation", { name: "工作台阶段" }).locator("button").nth(1);
    await expect(stageNavigation).toBeDisabled();

    releaseClose();
    await expect(page.getByText("正在关闭项目", { exact: true })).not.toBeVisible();
    await page.unroute("**/api/v2/projects/*/close");
  });

  test("discards only the current authoring draft durably before Close", async ({ page, request, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await page.getByRole("button", { name: "保存简报" }).click();
    await expect(page).toHaveURL(/[?&]project=/);
    await expect(page.getByText("草稿：等待编辑", { exact: true })).toBeVisible();
    const projectId = new URL(page.url()).searchParams.get("project")!;
    const canonicalTitle = await page.getByLabel("片名").inputValue();
    const draftHold = await holdFirstAuthoringDraft(page);
    await page.getByLabel("片名").fill("earlier draft before discard");
    await draftHold.started;
    await page.getByLabel("片名").fill("this draft must be discarded from project storage");

    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "关闭项目" }).click();
    const closeResponse = waitForCloseResponse(page, projectId);
    await page.getByRole("button", { name: "丢弃" }).click();
    draftHold.release();
    expect((await closeResponse).ok()).toBeTruthy();
    await page.unroute("**/api/v2/projects/*/authoring-drafts");
    await page.evaluate(() => sessionStorage.clear());

    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "重新打开" }).click();
    await expect(page.getByLabel("片名")).toHaveValue(canonicalTitle);
    const drafts = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/authoring-drafts`);
    expect(drafts.ok()).toBeTruthy();
    expect(await drafts.json()).toEqual([]);
  });

  test("keeps a durable draft and the project open when Close fails", async ({ page, request, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await page.getByRole("button", { name: "保存简报" }).click();
    await expect(page).toHaveURL(/[?&]project=/);
    await expect(page.getByText("草稿：等待编辑", { exact: true })).toBeVisible();
    const projectId = new URL(page.url()).searchParams.get("project")!;
    const draftTitle = "Close failure keeps this durable draft";
    const draftHold = await holdFirstAuthoringDraft(page);
    await page.getByLabel("片名").fill("earlier draft before Close failure");
    await draftHold.started;
    await page.getByLabel("片名").fill(draftTitle);
    let markCloseFailed!: () => void;
    const closeFailed = new Promise<void>((resolve) => { markCloseFailed = resolve; });
    await page.route("**/api/v2/projects/*/close", async (route) => {
      markCloseFailed();
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "close transport unavailable" }) });
    });

    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "关闭项目" }).click();
    await page.getByRole("button", { name: "保存草稿并关闭" }).click();
    draftHold.release();
    await closeFailed;
    await expect(page.getByLabel("片名")).toHaveValue(draftTitle);
    await expect.poll(async () => (await fetch(`${workbench.apiOrigin}/api/v2/projects/${projectId}`)).status).toBe(200);
    await expect.poll(async () => {
      const drafts = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/authoring-drafts`);
      return (await drafts.json() as Array<{ payload: { title: string } }>).some((draft) => draft.payload.title === draftTitle);
    }).toBe(true);
    await page.unroute("**/api/v2/projects/*/close");
    await page.unroute("**/api/v2/projects/*/authoring-drafts");
  });

  test("drains a queued visual-intent draft before Close and restores it after Open and restart", async ({ page, request, workbench }) => {
    const projectId = await createStoryboardProject(request, workbench.apiOrigin, "Close media draft fixture");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    await page.getByLabel("审核人标签").fill("close-media reviewer");
    await page.getByRole("button", { name: "批准当前分镜" }).click();
    await page.getByLabel("来源声明").fill("Close/reopen durable media-draft fixture.");
    await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
    await page.getByLabel("候选图像比较").locator(".media-candidate").getByRole("button", { name: "保留此候选" }).click();
    await page.getByTestId("visual-intent-source-refs").fill("canonical visual intent source");
    await page.getByTestId("save-visual-intent").click();
    await page.getByLabel("审核兼容性说明").fill("Reviewed source asset for close draft recovery.");
    await page.getByTestId("select-reviewed-keyframe").click();

    let releaseDraft!: () => void;
    const heldDraft = new Promise<void>((resolve) => { releaseDraft = resolve; });
    let markDraftStarted!: () => void;
    const draftStarted = new Promise<void>((resolve) => { markDraftStarted = resolve; });
    let held = false;
    await page.route("**/api/v2/projects/*/authoring-drafts", async (route) => {
      if (!held && route.request().method() === "PUT") {
        held = true;
        markDraftStarted();
        await heldDraft;
      }
      await route.continue();
    });
    const durableSource = "queued media direction survives Close";
    await page.getByTestId("visual-intent-source-refs").fill(durableSource);
    await draftStarted;
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    const closeResponse = waitForCloseResponse(page, projectId);
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "关闭项目" }).click();
    releaseDraft();
    expect((await closeResponse).ok()).toBeTruthy();
    await page.unroute("**/api/v2/projects/*/authoring-drafts");
    await page.evaluate(() => sessionStorage.clear());

    await workbench.restartBackend();
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "重新打开" }).click();
    await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /分镜工作台/ }).click();
    await expect(page.getByTestId("visual-intent-source-refs")).toHaveValue(durableSource);
  });

  test("drains an acknowledged image direction after switching away from its shot", async ({ page, request, workbench }) => {
    const projectId = await createStoryboardProject(request, workbench.apiOrigin, "Close switched direction fixture");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    const direction = page.getByTestId("image-job-presentation-change");
    const originalDirection = "keep this acknowledged direction after switching shots";
    await direction.fill(originalDirection);
    await expect.poll(async () => {
      const drafts = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/authoring-drafts`);
      return (await drafts.json() as Array<{ editorScope: string; payload: { presentationChange?: string } }>).some(
        (draft) => draft.editorScope === "image_direction" && draft.payload.presentationChange === originalDirection,
      );
    }).toBe(true);

    const shotSelector = page.getByLabel("当前媒体镜头");
    const shotIds = await shotSelector.locator("option").evaluateAll((options) => options.map((option) => (option as HTMLOptionElement).value));
    expect(shotIds.length).toBeGreaterThan(1);
    await shotSelector.selectOption(shotIds[1]);
    await expect(direction).toHaveValue("");

    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    const closeResponse = waitForCloseResponse(page, projectId);
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "关闭项目" }).click();
    expect((await closeResponse).ok()).toBeTruthy();
    await page.evaluate(() => sessionStorage.clear());

    await workbench.restartBackend();
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "重新打开" }).click();
    await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /分镜工作台/ }).click();
    await page.getByLabel("当前媒体镜头").selectOption(shotIds[0]);
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue(originalDirection);
  });

  test("drains a cleared image direction after a media switch so reopening cannot resurrect it", async ({ page, request, workbench }) => {
    const projectId = await createStoryboardProject(request, workbench.apiOrigin, "Close cleared direction fixture");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    const direction = page.getByTestId("image-job-presentation-change");
    await direction.fill("remove this server-backed image direction");
    await expect.poll(async () => {
      const drafts = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/authoring-drafts`);
      return (await drafts.json() as Array<{ editorScope: string }>).some((draft) => draft.editorScope === "image_direction");
    }).toBe(true);

    const shotSelector = page.getByLabel("当前媒体镜头");
    const shotIds = await shotSelector.locator("option").evaluateAll((options) => options.map((option) => (option as HTMLOptionElement).value));
    if (shotIds.length > 1) {
      await shotSelector.selectOption(shotIds[1]);
      await shotSelector.selectOption(shotIds[0]);
    }
    await direction.fill("");
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    const closeResponse = waitForCloseResponse(page, projectId);
    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "关闭项目" }).click();
    expect((await closeResponse).ok()).toBeTruthy();
    await page.evaluate(() => sessionStorage.clear());

    await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "重新打开" }).click();
    await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /分镜工作台/ }).click();
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue("");
    const drafts = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/authoring-drafts`);
    expect(await drafts.json()).toEqual([]);
  });
});

async function createStoryboardProject(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
  title = demoProject.brief.title,
): Promise<string> {
  const response = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `project-folder-close-media-${Date.now()}` },
    data: {
      brief: { ...demoProject.brief, title },
      initialStages: [
        { stage: "story_bible", payload: demoProject.storyBible },
        { stage: "story_graph", payload: demoProject.storyGraph },
        { stage: "scene_beats", payload: demoProject.sceneBeats },
        { stage: "storyboard", payload: demoProject.storyboard },
      ],
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json() as { id: string }).id;
}

async function holdFirstAuthoringDraft(page: import("@playwright/test").Page) {
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  let markStarted!: () => void;
  const started = new Promise<void>((resolve) => { markStarted = resolve; });
  let first = true;
  await page.route("**/api/v2/projects/*/authoring-drafts", async (route) => {
    if (first && route.request().method() === "PUT") {
      first = false;
      markStarted();
      await held;
    }
    await route.continue();
  });
  return { release, started };
}

function waitForCloseResponse(page: import("@playwright/test").Page, projectId: string) {
  return page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/close`,
  );
}
