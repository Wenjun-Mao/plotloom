import { expect, test, type Workbench } from "./fixture";
import { demoProject } from "../src/demo";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { APIRequestContext, Page } from "@playwright/test";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const still = path.join(root, "docs/verification/supporting/p0-generated/01-arrival.png");

function openingWalkthroughProject() {
  const project = structuredClone(demoProject);
  project.brief = {
    ...project.brief, title: "合成镜头片段互动检查", decisionPointsPerPath: 0,
    endingCount: 1, nodeBudget: 2, maxOutDegree: 1, desiredJoinCount: 0,
  };
  project.storyGraph = {
    startNodeId: "start",
    nodes: [
      { id: "start", title: "开场", kind: "start", summary: "合成媒体检查镜头。" },
      { id: "ending", title: "完成", kind: "ending", summary: "片段检查完成。" },
    ],
    edges: [{ id: "finish", sourceNodeId: "start", targetNodeId: "ending", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] }],
    joinContracts: [],
  };
  project.sceneBeats = {
    ...project.sceneBeats,
    scenes: project.sceneBeats.scenes
      .filter((scene) => ["scene_arrival", "scene_ending_city"].includes(scene.id))
      .map((scene, index) => ({ ...scene, storyNodeId: index === 0 ? "start" : "ending", order: 1, beatIds: [index === 0 ? "b1" : "b9"] })),
    beats: project.sceneBeats.beats.filter((beat) => ["b1", "b9"].includes(beat.id)),
    dialogueCues: project.sceneBeats.dialogueCues.filter((cue) => cue.beatId === "b1"),
  };
  project.storyboard = {
    ...project.storyboard,
    shots: project.storyboard.shots.filter((shot) => ["shot_01", "shot_09"].includes(shot.id)),
    shotBeatLinks: project.storyboard.shotBeatLinks.filter((link) => ["shot_01", "shot_09"].includes(link.shotId)),
  };
  return project;
}

async function createAndApprove(page: Page, request: APIRequestContext, workbench: Workbench): Promise<string> {
  const project = openingWalkthroughProject();
  const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: {
    brief: project.brief,
    initialStages: [
      { stage: "story_bible", payload: project.storyBible },
      { stage: "story_graph", payload: project.storyGraph },
      { stage: "scene_beats", payload: project.sceneBeats },
      { stage: "storyboard", payload: project.storyboard },
    ],
  } });
  expect(created.ok(), await created.text()).toBeTruthy();
  const projectId = (await created.json() as { id: string }).id;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard&entity=shot%3Ashot_01#shot-keyframe-review`);
  await page.getByLabel("审核人标签").fill("Synthetic fixture setup");
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  await expect(page.getByTestId("video-pilot-panel")).toBeVisible();

  await page.getByLabel("来源声明").fill("Synthetic offline browser fixture; not creator-approved source media.");
  await page.getByTestId("managed-image-upload").setInputFiles(still);
  await page.getByRole("button", { name: "保留此候选" }).click();
  await page.getByTestId("visual-intent-source-refs").fill("Synthetic test-only opening still.");
  await page.getByTestId("save-visual-intent").click();
  await page.getByLabel("审核兼容性说明").fill("Technical fixture prerequisite for segment UI; not creative acceptance.");
  const selectedKeyframe = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/reviewed-keyframes`);
  await page.getByTestId("select-reviewed-keyframe").click();
  const keyframeResponse = await selectedKeyframe;
  expect(keyframeResponse.ok()).toBeTruthy();
  const { assetId } = await keyframeResponse.json() as { assetId: string };
  const stateResponse = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(stateResponse.ok()).toBeTruthy();
  const state = await stateResponse.json() as { characterReferences: { states: Array<{ characterId: string; revision: number }> } };
  for (const characterId of project.storyboard.shots[0].characterIds) {
    const current = state.characterReferences.states.find((item) => item.characterId === characterId);
    const reference = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-references`, { data: {
      characterId, authority: "story_bible", primaryAssetId: assetId, complementaryAssetIds: [],
      expectedReferenceRevision: current?.revision ?? 0, reviewer: "Synthetic fixture setup",
      notes: "Technical prerequisite only; synthetic isolated data.",
    } });
    expect(reference.ok(), await reference.text()).toBeTruthy();
  }
  return projectId;
}

async function selectEndingKeyframe(page: Page, request: APIRequestContext, workbench: Workbench, projectId: string) {
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard&entity=shot%3Ashot_09#shot-keyframe-review`);
  await page.getByLabel("来源声明").fill("Synthetic offline ending still; isolated fixture data only.");
  const importResponse = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/managed-assets`);
  await page.getByTestId("managed-image-upload").setInputFiles(still);
  const imported = await importResponse;
  expect(imported.ok(), await imported.text()).toBeTruthy();
  const assetId = (await imported.json() as { id: string }).id;
  await page.getByRole("button", { name: new RegExp(`Imported candidate ${assetId}`) }).click();
  await page.getByTestId(`keep-candidate-${assetId}`).click();
  await page.getByTestId("visual-intent-source-refs").fill("Synthetic test-only ending still.");
  const intentResponse = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/managed-assets/${assetId}/visual-intents`);
  await page.getByTestId("save-visual-intent").click();
  const intent = await intentResponse;
  expect(intent.ok(), await intent.text()).toBeTruthy();
  await page.getByLabel("审核兼容性说明").fill("Technical fixture prerequisite; synthetic ending shot only.");
  const selected = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/reviewed-keyframes`);
  await page.getByTestId("select-reviewed-keyframe").click();
  const selectedResponse = await selected;
  expect(selectedResponse.ok(), await selectedResponse.text()).toBeTruthy();
  expect(await selectedResponse.json()).toMatchObject({ assetId, shotId: "shot_09" });
  const workbenchState = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(workbenchState.ok()).toBeTruthy();
  const keyframes = (await workbenchState.json() as { reviewedKeyframes: Array<{ shotId: string }> }).reviewedKeyframes;
  expect(keyframes.map((keyframe) => keyframe.shotId).sort()).toEqual(["shot_01", "shot_09"]);
}

async function openShotForReview(page: Page, workbench: Workbench, projectId: string, shotId: string) {
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard&entity=shot%3A${shotId}#shot-keyframe-review`);
  await expect(page.getByTestId("video-pilot-panel")).toBeVisible();
}

async function ingestEightSecondOriginal(page: Page, request: APIRequestContext, workbench: Workbench, projectId: string): Promise<string> {
  const panel = page.getByTestId("video-pilot-panel");
  const letterbox = panel.getByLabel("允许黑边画布（保留当前横幅构图）");
  if (!await letterbox.isChecked()) await letterbox.check();
  await panel.getByLabel("H3 时长（已审核）").selectOption("8");
  await panel.getByRole("button", { name: "生成另一候选（冻结当前审核关键帧）" }).click();
  await panel.getByRole("button", { name: "提交一次" }).click();
  const reconcile = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname.startsWith(`/api/v2/projects/${projectId}/video-jobs/`)
    && new URL(response.url()).pathname.endsWith("/reconcile"));
  await panel.getByRole("button", { name: "获取结果" }).click();
  const response = await reconcile;
  expect(response.ok(), await response.text()).toBeTruthy();
  const job = await response.json() as { id: string; requestedSeconds: number; state: string; observed: { durationSeconds: number; frameCount: number } };
  expect(job).toMatchObject({ requestedSeconds: 8, state: "ingested", observed: { durationSeconds: 8, frameCount: 192 } });
  const jobsResponse = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`);
  expect(jobsResponse.ok()).toBeTruthy();
  return job.id;
}

async function prepareAndChoose(page: Page, jobId: string, inFrame: number, expectedOutFrame: number) {
  const review = page.getByTestId(`video-segment-review-${jobId}`);
  await review.getByLabel("片段入点（帧）").fill(String(inFrame));
  await review.getByRole("button", { name: "准备此连续片段（不选择）" }).click();
  const preview = review.locator('video[data-testid^="video-segment-preview-"]');
  await expect(preview).toBeVisible();
  await expect.poll(() => preview.evaluate((video) => (video as HTMLVideoElement).duration)).toBe((expectedOutFrame - inFrame) / 24);
  await expect(review).toContainText(`${inFrame}–${expectedOutFrame} 帧`);
  await preview.evaluate((video) => { (video as HTMLVideoElement).currentTime = 1; });
  await preview.evaluate((video) => (video as HTMLVideoElement).play());
  await expect.poll(() => preview.evaluate((video) => (video as HTMLVideoElement).currentTime)).toBeGreaterThan(1);
  await preview.evaluate((video) => (video as HTMLVideoElement).pause());
  await review.getByLabel("选择人").fill("Synthetic technical reviewer");
  const frameCount = expectedOutFrame - inFrame;
  await review.getByLabel("片段审核说明").fill(`Test-only validation of the ${frameCount}-frame derivative and its audio.`);
  const selection = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname.includes(`/video-segments/`)
    && new URL(response.url()).pathname.endsWith("/select"));
  await review.getByRole("button", { name: "确认选择此播放片段" }).click();
  const response = await selection;
  expect(response.ok(), await response.text()).toBeTruthy();
  await expect(review).toContainText("当前已明确选择");
}

test("retains separate exercise and ready-to-use synthetic segment walkthrough projects", async ({ page, request, workbench }) => {
  test.setTimeout(360_000);
  const exerciseProject = await createAndApprove(page, request, workbench);
  await selectEndingKeyframe(page, request, workbench, exerciseProject);
  await openShotForReview(page, workbench, exerciseProject, "shot_01");
  const exerciseJob = await ingestEightSecondOriginal(page, request, workbench, exerciseProject);
  await openShotForReview(page, workbench, exerciseProject, "shot_09");
  const exerciseEndingJob = await ingestEightSecondOriginal(page, request, workbench, exerciseProject);
  await openShotForReview(page, workbench, exerciseProject, "shot_01");
  await prepareAndChoose(page, exerciseJob, 24, 168);
  await openShotForReview(page, workbench, exerciseProject, "shot_09");
  await prepareAndChoose(page, exerciseEndingJob, 0, 192);

  const exerciseState = await request.get(`${workbench.apiOrigin}/api/v2/projects/${exerciseProject}/video-jobs`);
  expect(exerciseState.ok()).toBeTruthy();
  const exerciseJobs = (await exerciseState.json() as { jobs: Array<{ id: string; requestedSeconds: number; current: boolean; selected: boolean; outputHash: string; playbackSegment?: { inFrame: number; outFrame: number; derivativeHash: string; selected: boolean } }> }).jobs;
  const chosen = exerciseJobs.find((job) => job.id === exerciseJob)!;
  expect(chosen).toMatchObject({ requestedSeconds: 8, current: true, selected: true, playbackSegment: { inFrame: 24, outFrame: 168, selected: true } });
  expect(chosen.playbackSegment!.derivativeHash).not.toEqual(chosen.outputHash);
  const chosenEnding = exerciseJobs.find((job) => job.id === exerciseEndingJob)!;
  expect(chosenEnding).toMatchObject({ requestedSeconds: 8, current: true, selected: true, playbackSegment: { inFrame: 0, outFrame: 192, selected: true } });
  expect(chosenEnding.playbackSegment!.derivativeHash).not.toEqual(chosenEnding.outputHash);
  await workbench.restartBackend();
  const persisted = await request.get(`${workbench.apiOrigin}/api/v2/projects/${exerciseProject}/video-jobs`);
  expect(persisted.ok()).toBeTruthy();
  const persistedJobs = (await persisted.json() as { jobs: typeof exerciseJobs }).jobs;
  expect(persistedJobs.find((job) => job.id === exerciseJob)).toMatchObject({
    requestedSeconds: 8, current: true, selected: true, playbackSegment: { inFrame: 24, outFrame: 168, selected: true },
  });
  expect(persistedJobs.find((job) => job.id === exerciseEndingJob)).toMatchObject({
    requestedSeconds: 8, current: true, selected: true, playbackSegment: { inFrame: 0, outFrame: 192, selected: true },
  });
  await page.goto(`${workbench.apiOrigin}/v2/?project=${exerciseProject}&view=play`);
  const player = page.getByTestId(`branching-video-job-${exerciseJob}`);
  await expect(player).toBeVisible();
  expect(await player.getAttribute("src")).toContain(`/video-jobs/${exerciseJob}/playback`);
  await expect.poll(() => player.evaluate((video) => (video as HTMLVideoElement).readyState)).toBeGreaterThan(0);
  await page.getByRole("button", { name: "播放当前" }).click();
  const endingPlayer = page.getByTestId(`branching-video-job-${exerciseEndingJob}`);
  await expect(endingPlayer).toBeVisible({ timeout: 15_000 });
  await expect.poll(() => endingPlayer.evaluate((video) => (video as HTMLVideoElement).currentTime)).toBeGreaterThan(0);
  await expect(page.getByRole("button", { name: "从头开始" })).toBeVisible({ timeout: 15_000 });

  const readyProject = await createAndApprove(page, request, workbench);
  await selectEndingKeyframe(page, request, workbench, readyProject);
  await openShotForReview(page, workbench, readyProject, "shot_01");
  const readyJob = await ingestEightSecondOriginal(page, request, workbench, readyProject);
  await openShotForReview(page, workbench, readyProject, "shot_09");
  const readyEndingJob = await ingestEightSecondOriginal(page, request, workbench, readyProject);
  await prepareAndChoose(page, readyEndingJob, 0, 192);
  const openingJobsResponse = await request.get(`${workbench.apiOrigin}/api/v2/projects/${readyProject}/video-jobs`);
  expect(openingJobsResponse.ok()).toBeTruthy();
  const readyOpening = (await openingJobsResponse.json() as { jobs: Array<{ id: string; current: boolean }> }).jobs.find((job) => job.id === readyJob)!;
  expect(readyOpening.current).toBe(true);
  const readyJobsResponse = await request.get(`${workbench.apiOrigin}/api/v2/projects/${readyProject}/video-jobs`);
  expect(readyJobsResponse.ok()).toBeTruthy();
  const readyJobs = (await readyJobsResponse.json() as { jobs: Array<{ id: string; requestedSeconds: number; state: string; current: boolean; selected: boolean; playbackSegment: { selected: boolean } | null; outputHash: string; observed: { frameCount: number } }> }).jobs;
  const readyJobState = readyJobs.find((job) => job.id === readyJob)!;
  expect(readyJobState).toMatchObject({ requestedSeconds: 8, state: "ingested", current: true, selected: false, playbackSegment: null, observed: { frameCount: 192 } });
  expect(readyJobs.find((job) => job.id === readyEndingJob)).toMatchObject({ current: true, selected: true, playbackSegment: { selected: true } });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${readyProject}&stage=storyboard&entity=shot%3Ashot_01#video-segment-review-${readyJob}`);
  const directReview = page.getByTestId(`video-segment-review-${readyJob}`);
  await expect(directReview).toBeVisible();
  await expect.poll(() => directReview.evaluate((element) => Math.abs(element.getBoundingClientRect().top))).toBeLessThan(8);
  console.log(`INTERACTIVE_EXERCISE_PROJECT=${exerciseProject}`);
  console.log(`INTERACTIVE_READY_PROJECT=${readyProject}`);
});
