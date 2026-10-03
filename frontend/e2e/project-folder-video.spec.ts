import { expect, checkedStaticTest as test } from "./fixture";
import { demoProject } from "../src/demo";
import { execFile } from "node:child_process";
import { mkdir, readdir, rm } from "node:fs/promises";
import { promisify } from "node:util";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Locator, Page } from "@playwright/test";
import { freezeReviewedFixtureDirections } from "./video_backends/minimax_h3/review-directions";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const retainedStill = path.join(repositoryRoot, "docs/verification/supporting/p0-generated/01-arrival.png");
const runFile = promisify(execFile);

test("keeps a reviewed fake-H3 video playable after direct-folder restore", async ({ page, request, workbench }) => {
  test.setTimeout(120_000);
  const nativeDialogs: string[] = [];
  page.on("dialog", async dialog => { nativeDialogs.push(dialog.type()); await dialog.dismiss(); });
  const projectId = await createStoryboardProject(request, workbench.apiOrigin);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
  await page.getByLabel("审核人标签").fill("direct video fixture reviewer");
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  await page.locator("details.workbench-support > summary").filter({ hasText: "准备与参考" }).click();
  await page.locator("details.workbench-support > summary").filter({ hasText: "关键帧与静帧预览" }).click();
  await page.getByLabel("来源声明").fill("Offline H3 keyframe fixture.");
  await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
  await page.getByLabel("候选图像比较").locator(".media-candidate").getByTestId(/^keep-candidate-/).click();
  await page.getByTestId("visual-intent-source-refs").fill("direct video fixture source");
  await page.getByTestId("save-visual-intent").click();
  await page.getByLabel("审核兼容性说明").fill("Reviewed for the frozen direct H3 candidate.");
  const keyframePost = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/reviewed-keyframes`);
  await page.getByTestId("select-reviewed-keyframe").click();
  const keyframeResponse = await keyframePost;
  expect(keyframeResponse.ok(), await keyframeResponse.text()).toBeTruthy();
  const { assetId } = await keyframeResponse.json() as { assetId: string };
  // API-only prerequisite setup, not character-reference UI coverage.
  const visualResponse = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(visualResponse.ok()).toBeTruthy();
  const visual = await visualResponse.json() as { characterReferences: { states: Array<{ characterId: string; revision: number }> } };
  for (const characterId of demoProject.storyboard.shots[0].characterIds) {
    const reference = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-references`, { data: {
      characterId, authority: "story_bible", primaryAssetId: assetId, complementaryAssetIds: [],
      expectedReferenceRevision: visual.characterReferences.states.find(state => state.characterId === characterId)?.revision ?? 0,
      reviewer: "direct video fixture reviewer", notes: "Explicit synthetic fixture prerequisite.",
    } });
    expect(reference.ok(), await reference.text()).toBeTruthy();
  }

  const panel = page.getByTestId("video-pilot-panel");
  await panel.locator("#video-production > summary").click();
  await panel.getByLabel("允许黑边画布（保留当前横幅构图）").check();
  await panel.getByLabel("H3 时长（已审核）").selectOption("8");
  const prepared = await prepareOfflineCandidate(page, panel, projectId);
  await selectPlaybackSegment(panel, prepared.id);
  const selectedPlaybackUrl = `${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${prepared.id}/playback`;
  expect((await request.get(selectedPlaybackUrl)).ok()).toBeTruthy();
  // A second deliberate generation uses a new client idempotency key.  It
  // must leave the first selected candidate playable until the reviewer makes
  // a fresh, explicit selection.
  const alternative = await prepareOfflineCandidate(page, panel, projectId);
  expect(alternative.id).not.toBe(prepared.id);
  await expect(panel.getByTestId(`video-segment-review-${prepared.id}`)).toContainText("已选择片段 · 正用于故事");
  expect((await request.get(selectedPlaybackUrl)).ok()).toBeTruthy();
  await selectPlaybackSegment(panel, alternative.id);
  await expect(panel.getByTestId(`video-segment-review-${prepared.id}`)).not.toContainText("已选择片段 · 正用于故事");
  await expect(panel.getByTestId(`video-job-${prepared.id}`)).toContainText("此原片已有保留片段，不能永久删除");
  await expect(panel.getByTestId(`video-job-${prepared.id}`).getByRole("button", { name: "永久删除", exact: true })).toHaveCount(0);
  // Retained proposals protect their originals even after selection changes.
  // Only this third, segment-free synthetic take is a disposable candidate.
  const disposable = await prepareOfflineCandidate(page, panel, projectId);
  await page.getByLabel("路径过滤").selectOption({ index: 1 });
  await expect(page.getByTestId("video-route-sequence-status")).toContainText("路径尚不完整");
  await expect(page.getByTestId("video-sequence-player")).toHaveCount(0);
  const alternativePlaybackUrl = `${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${alternative.id}/playback`;
  const beforeRestore = await request.get(alternativePlaybackUrl);
  expect(beforeRestore.ok()).toBeTruthy();
  const playbackBytes = await beforeRestore.body();
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
    PLOTLOOM_OUTPUTS_DIR: restoredOutputs,
    PLOTLOOM_APPLICATION_DATA_DIR: path.join(isolatedRoot, "application"),
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
  await page.getByLabel("路径过滤").selectOption({ index: 1 });
  await expect(page.getByTestId(`video-segment-review-${alternative.id}`)).toContainText("已选择片段 · 正用于故事");
  await expectAuthoredDuration(page.getByTestId(`video-segment-review-${alternative.id}`).locator('video[data-testid^="video-segment-preview-"]'));
  await expect(page.getByTestId("video-sequence-player")).toHaveCount(0);
  const restoredPlayback = await request.get(alternativePlaybackUrl);
  expect(restoredPlayback.ok()).toBeTruthy();
  expect(await restoredPlayback.body()).toEqual(playbackBytes);
  const restoredMedia = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${alternative.id}/media`);
  expect(restoredMedia.ok()).toBeTruthy();
  expect((await restoredMedia.body()).byteLength).toBeGreaterThan(100);
  await expect(page.getByTestId(`video-job-${prepared.id}`)).toContainText("此原片已有保留片段，不能永久删除");
  await page.getByTestId(`video-job-${disposable.id}`).getByRole("button", { name: "永久删除" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "取消", exact: true }).click();
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${disposable.id}/media`)).ok()).toBeTruthy();
  await page.getByTestId(`video-job-${disposable.id}`).getByRole("button", { name: "永久删除" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "确认永久删除", exact: true }).click();
  await expect(page.getByTestId(`video-job-${disposable.id}`)).toContainText("已永久删除候选媒体");
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${disposable.id}/media`)).status()).toBe(404);
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${prepared.id}/media`)).ok()).toBeTruthy();
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${alternative.id}/media`)).ok()).toBeTruthy();
  expect(await (await request.get(alternativePlaybackUrl)).body()).toEqual(playbackBytes);
  expect(nativeDialogs).toEqual([]);
  // Do not leak this isolated restore root into a later worker-scoped browser
  // journey; the fixture's default restart returns to its original paths.
  await workbench.restartBackend();
});

async function prepareOfflineCandidate(page: Page, panel: Locator, projectId: string): Promise<{ id: string }> {
  const preparedPost = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/video-jobs`);
  // All three deliberate candidates reuse one exact seed, while each new
  // review still has its own idempotency key and explicit submission.
  await freezeReviewedFixtureDirections(panel, "2325339575976657");
  const response = await preparedPost;
  expect(response.ok(), await response.text()).toBeTruthy();
  expect(response.request().postDataJSON()).toMatchObject({ seed: 2325339575976657 });
  const prepared = await response.json() as { id: string; snapshot: { request: { seed: number } } };
  expect(prepared.snapshot.request.seed).toBe(2325339575976657);
  const job = panel.getByTestId(`video-job-${prepared.id}`);
  await job.getByRole("button", { name: "提交一次" }).click();
  await job.getByRole("button", { name: "获取结果" }).click();
  await expect(panel.getByTestId(`video-job-player-${prepared.id}`)).toBeVisible();
  return prepared;
}

async function selectPlaybackSegment(panel: Locator, jobId: string) {
  const review = panel.getByTestId(`video-segment-review-${jobId}`);
  await review.getByRole("button", { name: "生成待审片段" }).click();
  const preview = review.locator('video[data-testid^="video-segment-preview-"]');
  await expect(preview).toBeVisible();
  await expectAuthoredDuration(preview);
  await review.getByRole("button", { name: "确认用于故事" }).click();
  await expect(review).toContainText("已选择片段 · 正用于故事");
}

async function expectAuthoredDuration(video: Locator) {
  const expectedSeconds = demoProject.storyboard.shots[0].durationUnits / 1000;
  await expect.poll(async () => Math.abs(await video.evaluate(element => (element as HTMLVideoElement).duration) - expectedSeconds)).toBeLessThanOrEqual(1 / 24);
}

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
