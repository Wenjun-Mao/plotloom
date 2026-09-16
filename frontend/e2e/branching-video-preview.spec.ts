import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Locator, Page } from "@playwright/test";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const still = path.join(root, "docs/verification/supporting/p0-generated/01-arrival.png");

function branchingFixture() {
  const project = structuredClone(demoProject);
  project.brief = {
    ...project.brief, title: "离线分支播放夹具", decisionPointsPerPath: 1, endingCount: 2, nodeBudget: 4, maxOutDegree: 2, desiredJoinCount: 0,
  };
  project.storyGraph = {
    startNodeId: "start",
    nodes: [
      { id: "start", title: "开始", kind: "start", summary: "离线夹具的第一镜。" },
      { id: "decision", title: "选择", kind: "decision", summary: "必须明确选择。" },
      { id: "left", title: "左结局", kind: "ending", summary: "左侧结束。" },
      { id: "right", title: "右结局", kind: "ending", summary: "右侧结束。" },
    ],
    edges: [
      { id: "to-decision", sourceNodeId: "start", targetNodeId: "decision", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      { id: "to-left", sourceNodeId: "decision", targetNodeId: "left", kind: "choice", choiceText: "选择左侧", stateEffects: {}, entityStateEffects: [] },
      { id: "to-right", sourceNodeId: "decision", targetNodeId: "right", kind: "choice", choiceText: "选择右侧", stateEffects: {}, entityStateEffects: [] },
    ],
    joinContracts: [],
  };
  const sourceScenes = ["scene_arrival", "scene_diagnose", "scene_ending_city", "scene_ending_brother"];
  const nodeIds = ["start", "decision", "left", "right"];
  const retainedBeatIds = ["b1", "b3", "b9", "b10"];
  project.sceneBeats = {
    ...project.sceneBeats,
    scenes: project.sceneBeats.scenes
      .filter((scene) => sourceScenes.includes(scene.id))
      .map((scene) => ({ ...scene, storyNodeId: nodeIds[sourceScenes.indexOf(scene.id)], order: 1, beatIds: scene.beatIds.filter((id) => retainedBeatIds.includes(id)) })),
    beats: project.sceneBeats.beats.filter((beat) => retainedBeatIds.includes(beat.id)),
    dialogueCues: project.sceneBeats.dialogueCues.filter((cue) => ["b1", "b3", "b10"].includes(cue.beatId)),
  };
  project.storyboard = {
    ...project.storyboard,
    shots: project.storyboard.shots.filter((shot) => ["shot_01", "shot_03", "shot_09", "shot_10"].includes(shot.id)),
    shotBeatLinks: project.storyboard.shotBeatLinks.filter((link) => ["shot_01", "shot_03", "shot_09", "shot_10"].includes(link.shotId)),
  };
  return project;
}

async function ingestAndSelectOfflineCandidate(page: Page, panel: Locator, projectId: string): Promise<string> {
  const allowLetterbox = panel.getByLabel("允许黑边画布（保留当前横幅构图）");
  if (!await allowLetterbox.isChecked()) await allowLetterbox.check();
  await panel.getByRole("button", { name: "冻结当前审核关键帧" }).click();
  await panel.getByRole("button", { name: "提交一次" }).click();
  const reconciled = page.waitForResponse((response) => {
    const pathname = new URL(response.url()).pathname;
    return response.request().method() === "POST"
      && pathname.startsWith(`/api/v2/projects/${projectId}/video-jobs/`)
      && pathname.endsWith("/reconcile");
  });
  await panel.getByRole("button", { name: "获取结果" }).click();
  const reconciledResponse = await reconciled;
  expect(reconciledResponse.ok()).toBeTruthy();
  const job = await reconciledResponse.json() as { id: string };
  const selected = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && new URL(response.url()).pathname.startsWith(`/api/v2/projects/${projectId}/video-jobs/`)
    && new URL(response.url()).pathname.endsWith("/review")
  ));
  await panel.getByRole("button", { name: "显式选择" }).click();
  const response = await selected;
  expect(response.ok()).toBeTruthy();
  return job.id;
}

test("production FastAPI fixture plays both native-ended branches and resets an episode", async ({ page, request, workbench }) => {
  test.setTimeout(120_000);
  const project = branchingFixture();
  const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: {
    brief: project.brief,
    initialStages: [
      { stage: "story_bible", payload: project.storyBible }, { stage: "story_graph", payload: project.storyGraph },
      { stage: "scene_beats", payload: project.sceneBeats }, { stage: "storyboard", payload: project.storyboard },
    ],
  } });
  expect(created.ok(), await created.text()).toBeTruthy();
  const projectId = (await created.json() as { id: string }).id;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
  await page.getByLabel("审核人标签").fill("Step 5 browser reviewer");
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  await page.getByLabel("来源声明").fill("Step 5 local fixture");
  await page.getByTestId("managed-image-upload").setInputFiles(still);
  await page.getByRole("button", { name: "保留此候选" }).click();
  await page.getByTestId("visual-intent-source-refs").fill("Step 5 fixture source");
  await page.getByTestId("save-visual-intent").click();

  const panel = page.getByTestId("video-pilot-panel");
  const shotNames = ["门开", "双键升起", "城市醒来", "舱门开启"];
  const jobIds: string[] = [];
  for (const [index, shotName] of shotNames.entries()) {
    if (index > 0) await page.getByLabel(`编辑镜头 ${shotName}`).click();
    await page.getByLabel("审核兼容性说明").fill(`Current approved ${shotName} fixture keyframe.`);
    const selectedKeyframeResponse = page.waitForResponse((response) => (
      response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/reviewed-keyframes`
    ));
    await page.getByTestId("select-reviewed-keyframe").click();
    if (index === 0) {
      const selectedKeyframe = await selectedKeyframeResponse.then((response) => response.json() as Promise<{ assetId: string }>);
      const visual = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
      expect(visual.ok()).toBeTruthy();
      const referenceState = await visual.json() as { characterReferences: { states: Array<{ characterId: string; revision: number }> } };
      for (const characterId of ["char_ruanxing", "char_andi"]) {
        const state = referenceState.characterReferences.states.find((item) => item.characterId === characterId);
        const reference = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-references`, { data: {
          characterId, primaryAssetId: selectedKeyframe.assetId, complementaryAssetIds: [], expectedReferenceRevision: state?.revision ?? 0,
          reviewer: "Step 5 browser reviewer", notes: "Offline fixture reference for visible characters.",
        } });
        expect(reference.ok()).toBeTruthy();
      }
    }
    jobIds.push(await ingestAndSelectOfflineCandidate(page, panel, projectId));
  }

  const preview = page.getByTestId("branching-video-preview");
  const start = page.getByTestId(`branching-video-job-${jobIds[0]}`);
  const startSource = await start.getAttribute("src");
  expect(startSource).toContain(`/video-jobs/${jobIds[0]}/media`);
  expect((await request.get(`${workbench.apiOrigin}${startSource}`, { headers: { Range: "bytes=0-15" } })).status()).toBe(206);
  await expect.poll(() => start.evaluate((video) => (video as HTMLVideoElement).readyState), { timeout: 9_000 }).toBeGreaterThan(0);
  await preview.getByRole("button", { name: "播放当前" }).click();
  await expect.poll(() => start.evaluate((video) => {
    const media = video as HTMLVideoElement;
    return media.currentTime > 0 ? "playing" : JSON.stringify({
      currentTime: media.currentTime, duration: media.duration, paused: media.paused, readyState: media.readyState,
      networkState: media.networkState, error: media.error?.code ?? null, src: media.currentSrc,
    });
  }), { timeout: 9_000 }).toBe("playing");

  const decision = page.getByTestId(`branching-video-job-${jobIds[1]}`);
  await expect(decision).toBeVisible({ timeout: 9_000 });
  await expect(preview.getByTestId("branching-choices")).toHaveCount(0);
  await expect.poll(() => decision.evaluate((video) => (video as HTMLVideoElement).currentTime), { timeout: 9_000 }).toBeGreaterThan(0);
  await expect.poll(() => decision.evaluate((video) => (video as HTMLVideoElement).ended), { timeout: 9_000 }).toBeTruthy();
  await expect(preview.getByTestId("branching-choices")).toBeVisible();

  await preview.getByRole("button", { name: "选择左侧" }).click();
  const left = page.getByTestId(`branching-video-job-${jobIds[2]}`);
  await expect(left).toBeVisible();
  await expect.poll(() => left.evaluate((video) => (video as HTMLVideoElement).currentTime), { timeout: 9_000 }).toBeGreaterThan(0);
  await expect.poll(() => left.evaluate((video) => (video as HTMLVideoElement).ended), { timeout: 9_000 }).toBeTruthy();
  await expect(preview.getByRole("button", { name: "重新开始分支预览" })).toBeVisible();

  const firstEpisode = await left.getAttribute("data-playback-identity");
  await preview.getByRole("button", { name: "重新开始分支预览" }).click();
  const restartedStart = page.getByTestId(`branching-video-job-${jobIds[0]}`);
  expect(await restartedStart.getAttribute("data-playback-identity")).not.toBe(firstEpisode);
  await expect(restartedStart.evaluate((video) => (video as HTMLVideoElement).paused)).resolves.toBeTruthy();
  await preview.getByRole("button", { name: "播放当前" }).click();
  await expect.poll(() => restartedStart.evaluate((video) => (video as HTMLVideoElement).currentTime), { timeout: 9_000 }).toBeGreaterThan(0);
  await expect(decision).toBeVisible({ timeout: 9_000 });
  await expect.poll(() => decision.evaluate((video) => (video as HTMLVideoElement).ended), { timeout: 9_000 }).toBeTruthy();

  await preview.getByRole("button", { name: "选择右侧" }).click();
  const right = page.getByTestId(`branching-video-job-${jobIds[3]}`);
  await expect(right).toBeVisible();
  await expect.poll(() => right.evaluate((video) => (video as HTMLVideoElement).currentTime), { timeout: 9_000 }).toBeGreaterThan(0);
  await expect.poll(() => right.evaluate((video) => (video as HTMLVideoElement).ended), { timeout: 9_000 }).toBeTruthy();
  await expect(preview.getByRole("button", { name: "重新开始分支预览" })).toBeVisible();
  await page.screenshot({ path: test.info().outputPath("step-5-branching-native-browser.png"), fullPage: true });
});
