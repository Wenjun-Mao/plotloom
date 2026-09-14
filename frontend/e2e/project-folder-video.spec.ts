import { expect, projectFolderTest as test } from "./fixture";
import { demoProject } from "../src/demo";
import { execFile } from "node:child_process";
import { mkdir, readdir, rm } from "node:fs/promises";
import { promisify } from "node:util";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const retainedStill = path.join(repositoryRoot, "docs/verification/supporting/p0-generated/01-arrival.png");
const runFile = promisify(execFile);

test("keeps a reviewed fake-H3 video playable after direct-folder restore", async ({ page, request, workbench }) => {
  const projectId = await createStoryboardProject(request, workbench.apiOrigin);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
  await page.getByLabel("审核人标签").fill("direct video fixture reviewer");
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  await page.getByLabel("来源声明").fill("Offline H3 keyframe fixture.");
  await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
  await page.getByLabel("候选图像比较").locator(".media-candidate").getByRole("button", { name: "保留此候选" }).click();
  await page.getByTestId("reference-primary-asset").selectOption({ index: 1 });
  await page.getByLabel("选择说明").fill("Use the reviewed fixture as this shot's explicit character reference.");
  await page.getByRole("button", { name: "选择身份参考" }).click();
  await page.getByTestId("visual-intent-source-refs").fill("direct video fixture source");
  await page.getByTestId("save-visual-intent").click();
  await page.getByLabel("审核兼容性说明").fill("Reviewed for the frozen direct H3 candidate.");
  await page.getByTestId("select-reviewed-keyframe").click();
  await expect(page.getByTestId("select-reviewed-keyframe")).toBeEnabled();

  const panel = page.getByTestId("video-pilot-panel");
  await expect(panel.getByText("MiniMax H3 本地视频候选", { exact: true })).toBeVisible();
  await panel.getByLabel("允许黑边画布（保留当前横幅构图）").check();
  const preparedResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/video-jobs`,
  );
  await panel.getByRole("button", { name: "冻结当前审核关键帧" }).click();
  const preparedRequest = await preparedResponse;
  expect(preparedRequest.ok(), await preparedRequest.text()).toBeTruthy();
  const prepared = await preparedRequest.json() as { id: string };
  const job = page.getByTestId(`video-job-${prepared.id}`);
  await job.getByRole("button", { name: "提交一次" }).click();
  await expect(job.getByRole("button", { name: "获取结果" })).toBeVisible();
  await job.getByRole("button", { name: "获取结果" }).click();
  await expect(page.getByTestId(`video-job-player-${prepared.id}`)).toBeVisible();
  await job.getByRole("button", { name: "显式选择" }).click();
  await expect(page.getByTestId(`video-sequence-job-${prepared.id}`)).toBeVisible();
  const localMedia = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${prepared.id}/media`, {
    headers: { Range: "bytes=0-15" },
  });
  expect(localMedia.status()).toBe(206);
  expect((await localMedia.body()).byteLength).toBe(16);

  const snapshotResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/snapshots`,
  );
  await page.getByRole("button", { name: "创建恢复快照" }).click();
  const snapshot = await (await snapshotResponse).json() as { location: string };
  const close = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/close`);
  expect(close.ok(), await close.text()).toBeTruthy();
  const sourceHome = path.join(
    workbench.outputsRoot!,
    (await readdir(workbench.outputsRoot!)).find((item) => item.endsWith(`__${projectId}`))!,
  );
  await rm(sourceHome, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
  const isolatedRoot = path.join(path.dirname(workbench.outputsRoot!), "direct-video-restored-installation");
  const restoredOutputs = path.join(isolatedRoot, "outputs");
  await mkdir(isolatedRoot, { recursive: true });
  await runFile("uv", ["run", "plotloom", "restore", "--source", snapshot.location, "--outputs-dir", restoredOutputs], { cwd: repositoryRoot });
  await workbench.restartBackend({
    PLOTLOOM_E2E_OUTPUTS_DIR: restoredOutputs,
    PLOTLOOM_E2E_APPLICATION_DATA_DIR: path.join(isolatedRoot, "application"),
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
  await expect(page.getByTestId(`video-sequence-job-${prepared.id}`)).toBeVisible();
  const restoredMedia = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${prepared.id}/media`);
  expect(restoredMedia.ok()).toBeTruthy();
  expect((await restoredMedia.body()).byteLength).toBeGreaterThan(100);
});

async function createStoryboardProject(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
): Promise<string> {
  const response = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `project-folder-video-${Date.now()}` },
    data: {
      brief: { ...demoProject.brief, title: "Direct H3 portable-video fixture" },
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
