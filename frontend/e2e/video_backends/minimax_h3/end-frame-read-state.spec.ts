import path from "node:path";
import { fileURLToPath } from "node:url";
import { openMediaPreparation } from "../../workbench-controls";
import { expect, checkedStaticTest as test } from "../../fixture";
import { demoProject } from "../../../src/demo";

const repository = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");
const still = path.join(repository, "docs/verification/supporting/p0-generated/01-arrival.png");

for (const [width, height] of [[1280, 768], [1280, 460], [1700, 900]]) {
  test(`end-frame read-only qualification and truthful guidance at ${width}x${height}`, async ({ page, request, workbench }, testInfo) => {
    await page.setViewportSize({ width, height });
    const storyboard = structuredClone(demoProject.storyboard);
    storyboard.shots[0].durationUnits = 7_500;
    const sceneBeats = structuredClone(demoProject.sceneBeats);
    sceneBeats.scenes.find(scene => scene.id === "scene_arrival")!.durationBudgetUnits = 11_500;
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
    await page.getByLabel("审核人标签").fill("Synthetic read-state fixture");
    await page.getByRole("button", { name: "批准当前分镜" }).click();
    await openMediaPreparation(page);
    await page.getByLabel("来源声明").fill("Synthetic offline read-state fixture; not creative acceptance.");
    await page.getByTestId("managed-image-upload").setInputFiles(still);
    await page.getByTestId(/^keep-candidate-/).click();
    await page.getByTestId("visual-intent-source-refs").fill("Synthetic fixture source.");
    await page.getByTestId("save-visual-intent").click();
    await page.getByLabel("审核兼容性说明").fill("Technical fixture prerequisite only.");
    await page.getByTestId("select-reviewed-keyframe").click();

    const panel = page.getByTestId("video-pilot-panel");
    await panel.locator("#video-production").evaluate(element => { (element as HTMLDetailsElement).open = true; });
    await panel.getByLabel("H3 质量用途（必选）").selectOption("8");
    await panel.getByLabel("H3 时长（已审核）").selectOption("8");
    await panel.getByLabel("允许网关居中裁切（保留原审核关键帧）").check();
    const endFrame = panel.getByTestId("h3-end-frame-choice");
    const directions = panel.getByTestId("h3-directions-review");
    await directions.locator("summary").click();
    const readSource = directions.getByRole("button", { name: "读取当前来源", exact: true });
    await expect(readSource).toBeEnabled();
    const writes: string[] = [];
    page.on("request", call => { if (!["GET", "HEAD", "OPTIONS"].includes(call.method())) writes.push(`${call.method()} ${new URL(call.url()).pathname}`); });

    const endFramePath = `**/api/v2/projects/${projectId}/shots/shot_01/video-end-frame`;
    let release!: () => void;
    const held = new Promise<void>(resolve => { release = resolve; });
    await page.route(endFramePath, async route => {
      await held;
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "Synthetic setting read failure", reason: "read_busy", requestIdentity: "unbroken-identity-".repeat(40) }) });
    });
    await endFrame.getByRole("button", { name: "刷新末帧与图片列表" }).click();
    await expect(endFrame.getByRole("status")).toContainText("正在读取末帧设置与图片列表");
    await expect(readSource).toBeDisabled();
    await endFrame.scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath("read-pending-viewport.png") });
    release();
    await expect(endFrame.getByRole("alert")).toContainText("无法读取末帧设置与图片列表");
    await expect(endFrame.getByRole("status")).toContainText("当前末帧设置尚未核实");
    await expect(endFrame).not.toContainText("当前已保存");
    await expect(endFrame.getByRole("button", { name: "保存当前镜头末帧决定" })).toBeDisabled();
    await expect(readSource).toBeDisabled();
    await endFrame.getByText("读取错误详情", { exact: true }).click();
    await expect(endFrame.locator("pre")).toContainText("HTTP 503");
    await endFrame.scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath("read-error-viewport.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);

    await page.unroute(endFramePath);
    await endFrame.getByRole("button", { name: "刷新末帧与图片列表" }).click();
    await expect(endFrame.getByRole("status")).toContainText("当前设置：不使用末帧画面");
    await expect(endFrame.getByRole("alert")).toHaveCount(0);
    await expect(readSource).toBeEnabled();
    await endFrame.scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath("read-recovered-viewport.png") });
    expect(writes).toEqual([]);
    const jobs = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`);
    expect((await jobs.json() as { jobs: unknown[] }).jobs).toEqual([]);
  });
}
