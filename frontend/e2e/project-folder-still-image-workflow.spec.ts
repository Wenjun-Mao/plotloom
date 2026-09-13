import { expect, projectFolderTest as test } from "./fixture";
import { demoProject } from "../src/demo";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const retainedStill = path.join(
  repositoryRoot,
  "docs/verification/supporting/p0-generated/01-arrival.png",
);

test.describe("project-folder still-image workflow", () => {
  test("keeps imported bytes and reviewed still selection through a real backend restart", async ({
    page,
    request,
    workbench,
  }) => {
    const projectId = await createStoryboardProject(request, workbench.apiOrigin);
    await page.goto(
      `${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`,
    );
    await page
      .getByRole("navigation", { name: "工作台阶段" })
      .getByRole("button", { name: /05 分镜工作台/ })
      .click();
    await page.getByLabel("审核人标签").fill("project-folder browser reviewer");
    await page.getByRole("button", { name: "批准当前分镜" }).click();

    await page
      .getByLabel("来源声明")
      .fill("Retained fixture used only for project-folder still-image evidence.");
    await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
    const candidates = page.getByLabel("候选图像比较").locator(".media-candidate");
    await expect(candidates).toHaveCount(1);
    await candidates.getByRole("button", { name: "保留此候选" }).click();
    await page
      .getByTestId("visual-intent-source-refs")
      .fill("project-folder retained fixture");
    await page.getByTestId("save-visual-intent").click();
    await page
      .getByLabel("审核兼容性说明")
      .fill("The retained still is an explicit review choice for this fixture shot.");
    await page.getByTestId("select-reviewed-keyframe").click();
    await expect.poll(async () => {
      const response = await request.get(
        `${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`,
      );
      return ((await response.json()) as { reviewedKeyframes: unknown[] })
        .reviewedKeyframes.length;
    }).toBe(1);

    const before = await visualEvidence(request, workbench.apiOrigin, projectId);
    await workbench.restartBackend();
    await page.reload();
    const after = await visualEvidence(request, workbench.apiOrigin, projectId);
    expect(after).toEqual(before);
    await expect(candidates).toHaveCount(1);
    await expect(candidates.getByRole("img")).toHaveAttribute("src", /managed-assets/);
  });
});

async function createStoryboardProject(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
): Promise<string> {
  const response = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `project-folder-still-${Date.now()}` },
    data: {
      brief: demoProject.brief,
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

async function visualEvidence(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
  projectId: string,
): Promise<unknown> {
  const response = await request.get(
    `${apiOrigin}/api/v2/projects/${projectId}/visual-workbench`,
  );
  expect(response.ok(), await response.text()).toBeTruthy();
  const workbench = await response.json() as {
    assets: Array<{ id: string }>;
    visualIntents: unknown[];
    reviewedKeyframes: unknown[];
  };
  expect(workbench.assets).toHaveLength(1);
  const original = await request.get(
    `${apiOrigin}/api/v2/projects/${projectId}/managed-assets/${workbench.assets[0]!.id}/original`,
  );
  expect(original.ok(), await original.text()).toBeTruthy();
  return {
    originalBytes: (await original.body()).toString("base64"),
    visualIntents: workbench.visualIntents,
    reviewedKeyframes: workbench.reviewedKeyframes,
  };
}
