import { openMediaPreparation } from "../../workbench-controls";
import { expect, checkedStaticTest as test } from "../../fixture";
import { demoProject } from "../../../src/demo";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");
const still = path.join(root, "docs/verification/supporting/p0-generated/01-arrival.png");

test("shipped H3 UI reviews an end frame and selects a seven-and-half-second playback window", async ({ page, request, workbench }, testInfo) => {
  test.setTimeout(180_000);
  const storyboard = structuredClone(demoProject.storyboard);
  storyboard.shots[0].durationUnits = 7_500;
  const sceneBeats = structuredClone(demoProject.sceneBeats);
  sceneBeats.scenes.find((scene) => scene.id === "scene_arrival")!.durationBudgetUnits = 11_500;
  const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: {
    brief: demoProject.brief,
    initialStages: [
      { stage: "story_bible", payload: demoProject.storyBible },
      { stage: "story_graph", payload: demoProject.storyGraph },
      { stage: "scene_beats", payload: sceneBeats },
      { stage: "storyboard", payload: storyboard },
    ],
  } });
  expect(created.ok(), await created.text()).toBeTruthy();
  const projectId = (await created.json() as { id: string }).id;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard&entity=shot%3Ashot_01#shot-keyframe-review`);
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  await openMediaPreparation(page);
  await page.getByLabel("来源声明").fill("Synthetic offline image fixture; not creative approval.");
  await page.getByTestId("managed-image-upload").setInputFiles(still);
  await page.getByTestId(/^keep-candidate-/).click();
  await page.getByTestId("visual-intent-source-refs").fill("Synthetic browser fixture source.");
  await page.getByTestId("save-visual-intent").click();
  await page.getByLabel("兼容性备注（可选）").fill("Technical fixture prerequisite only.");
  const selection = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/reviewed-keyframes`);
  await page.getByTestId("select-reviewed-keyframe").click();
  const selected = await selection;
  expect(selected.ok(), await selected.text()).toBeTruthy();
  const assetId = (await selected.json() as { assetId: string }).assetId;

  const visual = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(visual.ok()).toBeTruthy();
  const characterStates = (await visual.json() as { characterReferences: { states: Array<{ characterId: string; revision: number }> } }).characterReferences.states;
  for (const characterId of storyboard.shots[0].characterIds) {
    const state = characterStates.find((item) => item.characterId === characterId);
    const response = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-references`, { data: {
      characterId, authority: "story_bible", primaryAssetId: assetId, complementaryAssetIds: [],
      expectedReferenceRevision: state?.revision ?? 0, reviewer: "Synthetic browser fixture",
      notes: "Technical fixture prerequisite only.",
    } });
    expect(response.ok(), await response.text()).toBeTruthy();
  }

  const panel = page.getByTestId("video-pilot-panel");
  await panel.locator("#video-production").evaluate((element) => { (element as HTMLDetailsElement).open = true; });
  await panel.getByLabel("H3 质量用途（必选）").selectOption("1");
  await panel.getByLabel("H3 时长（已审核）").selectOption("8");
  await panel.getByLabel("允许网关居中裁切（保留原审核关键帧）").check();
  const endFrame = panel.getByTestId("h3-end-frame-choice");
  await endFrame.getByRole("button", { name: "刷新末帧与图片列表" }).click();
  await endFrame.getByLabel("项目内已管理图片").selectOption(assetId);
  await endFrame.getByLabel("统一输入比例处理").selectOption("cover_center_crop");
  const directions = panel.getByTestId("h3-directions-review");
  await directions.locator("summary").click();
  await expect(directions.getByRole("button", { name: "读取当前来源" })).toBeDisabled();
  await endFrame.getByRole("button", { name: "保存当前镜头末帧决定" }).click();
  await expect(endFrame).toContainText("当前已保存：末帧");
  await expect(panel.getByTestId("h3-authored-timing")).toContainText("原稿镜头时长 7.500 秒");

  await directions.getByRole("button", { name: "读取当前来源" }).click();
  await directions.getByRole("button", { name: "准备本镜头制作简报", exact: true }).click();
  await directions.getByRole("button", { name: "用助手起草并独立检查指令", exact: true }).click();
  await expect(directions.getByRole("button", { name: "授权本镜头制作意图并开始生成", exact: true })).toBeEnabled({ timeout: 30000 });
  await directions.getByText("来源、完整供应商指令与检查记录（技术详情）", { exact: true }).click();
  await expect(directions.locator(".production-brief-review pre").first()).toContainText("Picture 2 (from Shot 1) aligns with the 8.00-second mark");
  await expect(directions.getByTestId("h3-frozen-review-inputs")).toContainText("末帧 SHA-256");
  for (const width of [1440, 1920]) {
    await page.setViewportSize({ width, height: 1080 });
    await expect(endFrame).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    await endFrame.screenshot({ path: testInfo.outputPath(`h3-end-frame-${width}.png`) });
    await page.screenshot({ path: testInfo.outputPath(`h3-workbench-${width}.png`) });
  }
  const preparedPost = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/video-jobs`);
  await directions.getByRole("button", { name: "授权本镜头制作意图并开始生成" }).click();
  const preparedResponse = await preparedPost;
  expect(preparedResponse.ok(), await preparedResponse.text()).toBeTruthy();
  const jobsResponse = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`);
  expect(jobsResponse.ok()).toBeTruthy();
  const jobs = (await jobsResponse.json() as { jobs: Array<{ id: string; snapshot: { endFrame: { assetId: string } } }> }).jobs;
  expect(jobs).toHaveLength(1);
  expect(jobs[0].snapshot.endFrame.assetId).toBe(assetId);
  const jobId = jobs[0].id;
  await expect.poll(async () => {
    const read = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`);
    return (await read.json()).jobs.find((job: { id: string }) => job.id === jobId)?.state;
  }, { timeout: 30000 }).toBe("ingested");
  const review = panel.getByTestId(`video-segment-review-${jobId}`);
  await expect(review).toBeVisible();
  await review.getByRole("checkbox", { name: "手动截取目标时长" }).check();
  await review.getByLabel("片段入点（帧）").fill("6");
  await review.getByRole("button", { name: "准备播放片段" }).click();
  await expect(review).toContainText("6–186 帧");
  await expect(review.locator('video[data-testid^="video-segment-preview-"]')).toBeVisible();
  await review.getByRole("button", { name: "选择用于故事" }).click();
  await expect(review).toContainText("已选择片段 · 正用于故事");
  const playback = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs/${jobId}/playback`);
  expect(playback.ok()).toBeTruthy();
});
