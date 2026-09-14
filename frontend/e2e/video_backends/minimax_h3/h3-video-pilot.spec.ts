import { expect, test } from "../../fixture";
import { demoProject } from "../../../src/demo";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");
const still = path.join(root, "docs/verification/supporting/p0-generated/01-arrival.png");

test("H3 browser path freezes a selected no-stretch catalog profile", async ({ page, request, workbench }) => {
  const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: demoProject.brief, initialStages: [
    { stage: "story_bible", payload: demoProject.storyBible }, { stage: "story_graph", payload: demoProject.storyGraph },
    { stage: "scene_beats", payload: demoProject.sceneBeats }, { stage: "storyboard", payload: demoProject.storyboard },
  ] } });
  expect(created.ok()).toBeTruthy();
  const projectId = (await created.json()).id as string;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);

  await page.getByLabel("审核人标签").fill("H3 browser reviewer");
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  await page.getByLabel("来源声明").fill("H3 browser fixture");
  await page.getByTestId("managed-image-upload").setInputFiles(still);
  await page.getByRole("button", { name: "保留此候选" }).click();
  await page.getByTestId("visual-intent-source-refs").fill("H3 fixture source");
  await page.getByTestId("save-visual-intent").click();
  await page.getByLabel("审核兼容性说明").fill("Current approved H3 fixture keyframe.");
  const selectedPost = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/reviewed-keyframes`
  ));
  await page.getByTestId("select-reviewed-keyframe").click();
  const selectedResponse = await selectedPost;
  expect(selectedResponse.ok()).toBeTruthy();
  const selectedKeyframe = await selectedResponse.json() as { assetId: string };

  const visual = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(visual.ok()).toBeTruthy();
  const visualState = await visual.json() as {
    characterReferences: { states: Array<{ characterId: string; revision: number }> };
  };
  const characterId = demoProject.storyboard.shots[0].characterIds[0];
  const referenceState = visualState.characterReferences.states.find((state) => state.characterId === characterId);
  const reference = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-references`, { data: {
    characterId, primaryAssetId: selectedKeyframe.assetId, complementaryAssetIds: [],
    expectedReferenceRevision: referenceState?.revision ?? 0, reviewer: "H3 browser reviewer",
    notes: "Explicit fixture reference for the visible character.",
  } });
  expect(reference.ok()).toBeTruthy();

  const backend = await request.get(`${workbench.apiOrigin}/api/v2/video-backend`);
  expect(await backend.json()).toMatchObject({
    enabled: true, adapterId: "minimax_h3_gateway", width: 576, height: 1024,
    frameCount: 124, nativeAudio: true, requiresAspectPolicy: false,
    inputAspectPolicy: "reject_mismatch",
    defaultProfileId: "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
  });
  const panel = page.getByTestId("video-pilot-panel");
  await expect(panel.getByText("MiniMax H3 本地视频候选")).toBeVisible();
  const profile = panel.getByLabel("H3 输出 Profile（必选）");
  await expect(profile).toHaveValue("minimax_h3_fp8_turbo4_portrait_576x1024_v1");
  await expect(panel.getByRole("button", { name: "冻结当前审核关键帧" })).toBeDisabled();
  await expect(panel.getByTestId("h3-aspect-preparation")).toContainText("不会再以黑边或提交时裁切");

  // Letterboxing is an author decision made before the job is frozen. It is
  // not a storyboard Gate bypass and it remains explicit in the request.
  await panel.getByLabel("允许黑边画布（保留当前横幅构图）").check();
  await expect(panel.getByTestId("h3-letterbox-allowed")).toContainText("contain_pad");
  await expect(panel.getByRole("button", { name: "冻结当前审核关键帧" })).toBeEnabled();

  const preparedPost = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/video-jobs`
  ));
  await panel.getByRole("button", { name: "冻结当前审核关键帧" }).click();
  const preparedResponse = await preparedPost;
  expect(preparedResponse.ok()).toBeTruthy();
  expect(preparedResponse.request().postDataJSON()).toMatchObject({
    requestedDurationSeconds: 5, resolution: "576x1024", audio: true, aspectPolicy: "contain_pad", allowLetterbox: true,
    profileId: "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
  });
  const prepared = await preparedResponse.json() as { id: string; snapshot: { request: object } };
  expect(prepared.snapshot.request).toMatchObject({ aspectPolicy: "contain_pad", allowLetterbox: true });

  await panel.getByRole("button", { name: "提交一次" }).click();
  const reconcile = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/video-jobs/${prepared.id}/reconcile`
  ));
  await panel.getByRole("button", { name: "获取结果" }).click();
  expect((await reconcile).ok()).toBeTruthy();
  await expect(page.getByTestId(`video-job-player-${prepared.id}`)).toBeVisible();
  const review = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/video-jobs/${prepared.id}/review`
  ));
  await panel.getByRole("button", { name: "显式选择" }).click();
  expect((await review).ok()).toBeTruthy();

  await expect.poll(async () => {
    const jobs = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`);
    return ((await jobs.json()) as { jobs: Array<{ id: string; selected: boolean; observed: object }> }).jobs.find((job) => job.id === prepared.id);
  }).toMatchObject({
    selected: true,
    observed: { width: 576, height: 1024, videoCodec: "h264", audioCodec: "aac", frameRate: 24, frameCount: 124 },
  });
  expect(await request.get(`${workbench.apiOrigin}/api/v2/video-pilot-budget`).then((response) => response.json())).toMatchObject({ reservedSeconds: 0 });

  await workbench.restartBackend();
  await page.reload();
  await expect(page.getByTestId(`video-sequence-job-${prepared.id}`)).toBeVisible();
});
