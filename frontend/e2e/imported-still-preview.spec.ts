import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const developmentStillPaths = ["01-arrival.png", "02-keys.png", "03-pressure.png", "04-establishing.png"]
  .map((name) => path.join(repositoryRoot, "docs/verification/supporting/p0-generated", name));

test.describe("P0 imported still preview journey", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("persists an explicit reviewed intent, refreshes applicability, and refuses deletion", async ({ page, request, workbench }, testInfo) => {
    const projectId = await createCanonicalProject(request, workbench.apiOrigin);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /05 分镜工作台/ }).click();

    await page.getByLabel("审核人标签").fill("P0 file-SQLite browser reviewer");
    await page.getByRole("button", { name: "批准当前分镜" }).click();
    await expect(page.getByText("当前批准：P0 file-SQLite browser reviewer", { exact: true })).toBeVisible();

    // Four independent provenance records make the comparison surface real;
    // the production contract itself has no fixed import-count limit.
    await page.getByLabel("来源声明").fill("Direct development-session images generated with imagegen on 2026-09-11");
    for (let index = 0; index < 4; index += 1) {
      await page.getByTestId("managed-image-upload").setInputFiles(developmentStillPaths[index]);
      await expect(page.locator(".media-candidate")).toHaveCount(index + 1);
    }
    const cards = page.locator(".media-candidate");
    // Keeping each real image is an explicit comparison action; it adds the
    // candidate without treating the last imported file as a hidden default.
    await cards.nth(0).getByRole("button", { name: "保留此候选" }).click();
    await cards.nth(1).getByRole("button", { name: "保留此候选" }).click();
    await expect(page.getByText("正在比较两个候选", { exact: false })).toBeVisible();
    await cards.nth(0).getByRole("button", { name: "保留此候选" }).click();
    await page.getByTestId("visual-intent-source-refs").fill("development session image · fixture A");
    await page.getByTestId("save-visual-intent").click();
    await expect(page.getByText(/已保存 r1/)).toBeVisible();
    await page.getByLabel("审核兼容性说明").fill("The retained still matches the approved first-shot composition.");
    await page.getByTestId("select-reviewed-keyframe").click();

    await page.getByRole("button", { name: "编辑镜头 压力下坠" }).click();
    await page.getByTestId("select-reviewed-keyframe").click();
    await page.getByRole("button", { name: "编辑镜头 P0 静止余波" }).click();
    await page.getByTestId("select-reviewed-keyframe").click();
    await expect(page.getByText("所有镜头已有当前审核关键帧", { exact: false })).toBeVisible();
    await page.getByRole("button", { name: "编辑镜头 门开" }).click();
    await page.getByTestId("preview-subset-length").selectOption("3");
    await page.getByTestId("create-still-preview").click();
    await expect(page.getByTestId("still-animatic")).toBeVisible();
    await page.getByTestId("animatic-play-pause").click();
    await page.getByTestId("animatic-seek").fill("2");
    await expect(page.getByText("shot_p0_03 · 2000ms", { exact: false })).toBeVisible();

    await page.reload();
    await expect(page.getByTestId("still-animatic")).toBeVisible();
    const restarted = await page.context().newPage();
    await restarted.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    await expect(restarted.getByTestId("still-animatic")).toBeVisible();
    await restarted.close();

    // A replacement is explicit, makes the former receipt stale, and permits
    // a new current receipt after the creator freezes the replacement.
    await page.getByRole("button", { name: "编辑镜头 门开" }).click();
    await cards.nth(1).getByRole("button", { name: "保留此候选" }).click();
    await page.getByTestId("visual-intent-source-refs").fill("development session image · fixture B");
    await page.getByTestId("save-visual-intent").click();
    await page.getByLabel("审核兼容性说明").fill("The replacement still matches the approved first-shot composition.");
    await page.getByTestId("select-reviewed-keyframe").click();
    await expect(page.getByText("STALE", { exact: true }).first()).toBeVisible();
    await page.getByTestId("create-still-preview").click();
    await expect(page.getByText("CURRENT", { exact: true }).first()).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("p0-imported-still-preview-1440x900.png"), animations: "disabled" });

    // A real authored-board edit removes the approval; the workbench must
    // repaint and block a reviewed selection until the normal reapproval.
    await page.getByLabel("标题").fill("门开（P0 reapproval check）");
    await page.getByRole("button", { name: "保存分镜" }).click();
    await expect(page.getByTestId("select-reviewed-keyframe")).toBeDisabled();
    await expect(page.getByText("需要当前 storyboard Approval", { exact: false })).toBeVisible();
    await page.getByLabel("审核人标签").fill("P0 reapproval reviewer");
    await page.getByRole("button", { name: "批准当前分镜" }).click();
    await expect(page.getByText("当前批准：P0 reapproval reviewer", { exact: true })).toBeVisible();
    await expect(page.getByText(/已保存 r1/)).toBeVisible();
    await page.getByLabel("审核兼容性说明").fill("Reapproved board compatibility is explicit, not inherited.");
    await expect(page.getByTestId("select-reviewed-keyframe")).toBeEnabled();

    const project = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}`);
    const projectBody = await project.json() as { lifecycleRevision: number; brief: { title: string } };
    const archived = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/archive`, {
      data: { expectedLifecycleRevision: projectBody.lifecycleRevision },
    });
    expect(archived.ok()).toBeTruthy();
    const deletion = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/permanent-delete`, {
      data: { expectedLifecycleRevision: projectBody.lifecycleRevision + 1, confirmationTitle: projectBody.brief.title },
    });
    expect(deletion.status()).toBe(409);
    expect((await deletion.json()) as { code: string }).toMatchObject({ code: "project_managed_assets_present" });
  });
});

async function createCanonicalProject(request: import("@playwright/test").APIRequestContext, apiOrigin: string): Promise<string> {
  const storyboard = structuredClone(demoProject.storyboard);
  const sceneBeats = structuredClone(demoProject.sceneBeats);
  const first = storyboard.shots.find((shot) => shot.id === "shot_01")!;
  storyboard.shots.push({
    ...first, id: "shot_p0_03", order: 3, title: "P0 静止余波", durationUnits: 2000, cueIds: [],
    audioPlan: { events: first.audioPlan.events.map((event) => ({ ...event, durationUnits: 2000 })) },
  });
  storyboard.shotBeatLinks.push({ shotId: "shot_p0_03", beatId: "b1", role: "supporting", coverageWeight: 1 });
  sceneBeats.scenes = sceneBeats.scenes.map((scene) => scene.id === "scene_arrival"
    ? { ...scene, durationBudgetUnits: 12000 } : scene);
  const response = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `p0-still-${Date.now()}` },
    data: {
      brief: demoProject.brief,
      initialStages: [
        { stage: "story_bible", payload: demoProject.storyBible },
        { stage: "story_graph", payload: demoProject.storyGraph },
        { stage: "scene_beats", payload: sceneBeats },
        { stage: "storyboard", payload: storyboard },
      ],
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json() as { id: string }).id;
}
