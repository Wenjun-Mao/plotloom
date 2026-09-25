import { expect, test } from "../../fixture";
import { demoProject } from "../../../src/demo";

test("H3 browser exposes quality and duration without granting playback eligibility", async ({ page, request, workbench }) => {
  const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: demoProject.brief, initialStages: [
    { stage: "story_bible", payload: demoProject.storyBible }, { stage: "story_graph", payload: demoProject.storyGraph },
    { stage: "scene_beats", payload: demoProject.sceneBeats }, { stage: "storyboard", payload: demoProject.storyboard },
  ] } });
  expect(created.ok()).toBeTruthy();
  const projectId = (await created.json()).id as string;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);

  const backend = await request.get(`${workbench.apiOrigin}/api/v2/video-backend`);
  expect(await backend.json()).toMatchObject({
    enabled: true, adapterId: "minimax_h3_gateway", defaultQuality: 8,
    defaultProfileId: "minimax_h3_quality8_portrait_576x1024_v2",
    qualifiedDurationSeconds: Array.from({ length: 11 }, (_, index) => index + 5),
  });
  const panel = page.getByTestId("video-pilot-panel");
  await panel.locator("#video-production").evaluate((element) => { (element as HTMLDetailsElement).open = true; });
  const quality = panel.getByLabel("H3 质量用途（必选）");
  const resolution = panel.getByLabel("H3 输出尺寸（必选）");
  const duration = panel.getByLabel("H3 时长（已审核）");
  await expect(quality).toHaveValue("8");
  await expect(resolution).toHaveValue("minimax_h3_quality8_portrait_576x1024_v2");
  await expect(duration).toHaveValue("5");
  await expect(panel.getByText("先为当前镜头审核选择一张关键帧")).toBeVisible();
  await quality.selectOption("1");
  await expect(resolution).toHaveValue("minimax_h3_quality1_portrait_576x1024_v2");
  await quality.selectOption("8");
  await duration.selectOption("15");
  await expect(panel.getByTestId("h3-authored-timing")).toContainText("362 帧");
  await expect(panel.getByTestId("h3-authored-timing")).toContainText("当前六秒原稿仅可请求八秒原片");
  await expect(panel.getByTestId("h3-directions-review").locator("button").first()).toBeDisabled();
  for (const width of [1440, 1920]) {
    await page.setViewportSize({ width, height: 1080 });
    await expect(quality).toBeVisible();
    await expect(duration).toBeVisible();
  }
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`).then((response) => response.json())).jobs).toEqual([]);
});
