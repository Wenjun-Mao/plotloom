import { expect, projectFolderTest as test } from "./fixture";
import { demoProject } from "../src/demo";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const retainedStill = path.join(repositoryRoot, "docs/verification/supporting/p0-generated/01-arrival.png");

test.describe("project-folder Close", () => {
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
    await page.locator(".directory-item").filter({ hasText: "活动中" }).getByRole("button", { name: "关闭项目" }).click();
    await expect(page.getByRole("heading", { name: "保存草稿并关闭项目？" })).toBeVisible();
    await page.getByRole("button", { name: "保存草稿并关闭" }).click();
    releaseDraft();
    await expect.poll(async () => (await fetch(`${workbench.apiOrigin}/api/v2/projects/${projectId}`)).status).toBe(409);
    await page.unroute("**/api/v2/projects/*/authoring-drafts");

    await workbench.restartBackend();
    await page.getByRole("button", { name: "重新打开" }).click();
    await expect(page.getByText("发现未保存草稿", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "恢复草稿" }).click();
    await expect(page.getByLabel("片名")).toHaveValue(draftTitle);

    const canonical = await fetch(`${workbench.apiOrigin}/api/v2/projects/${projectId}`);
    expect(canonical.ok).toBeTruthy();
    expect((await canonical.json()).brief.title).toBe(canonicalTitle);
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
    await page.locator(".directory-item").filter({ hasText: "Close media draft fixture" }).getByRole("button", { name: "关闭项目" }).click();
    releaseDraft();
    await expect.poll(async () => (await fetch(`${workbench.apiOrigin}/api/v2/projects/${projectId}`)).status).toBe(409);
    await page.unroute("**/api/v2/projects/*/authoring-drafts");
    await page.evaluate(() => sessionStorage.clear());

    await workbench.restartBackend();
    await page.getByRole("button", { name: "重新打开" }).click();
    await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /05 分镜工作台/ }).click();
    await expect(page.getByTestId("visual-intent-source-refs")).toHaveValue(durableSource);
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
