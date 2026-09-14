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

test("snapshots an open project then restores its draft, reviewed media, and lineage into a fresh installation", async ({ page, request, workbench }) => {
  expect(workbench.outputsRoot).toBeTruthy();
  const projectId = await createStoryboardProject(request, workbench.apiOrigin);
  const durableTitle = "E2E snapshot retains this server draft";
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=brief`);
  await page.getByLabel("片名").fill(durableTitle);
  await expect(page.getByText("草稿：已保存", { exact: true })).toBeVisible();

  await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /05 分镜工作台/ }).click();
  await page.getByLabel("审核人标签").fill("snapshot fixture reviewer");
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  await page.getByLabel("来源声明").fill("Offline reviewed still retained by the portable snapshot.");
  await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
  await page.getByLabel("候选图像比较").locator(".media-candidate").getByRole("button", { name: "保留此候选" }).click();
  await page.getByTestId("visual-intent-source-refs").fill("snapshot media lineage fixture");
  await page.getByTestId("save-visual-intent").click();
  await page.getByLabel("审核兼容性说明").fill("The stored fixture is reviewed for this exact shot.");
  const selectionResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/reviewed-keyframes`,
  );
  const selectionButton = page.getByTestId("select-reviewed-keyframe");
  await selectionButton.click();
  expect((await selectionResponse).ok()).toBeTruthy();
  // The mutation response precedes the workbench refresh that releases its
  // local writer. Snapshotting must begin after that refresh, not alongside it.
  await expect(selectionButton).toBeEnabled();

  const snapshotResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/snapshots`,
  );
  await page.getByRole("button", { name: "创建恢复快照" }).click();
  const snapshot = await (await snapshotResponse).json() as { location: string; snapshotId: string };
  await expect(page.getByText("恢复快照已完成：", { exact: false })).toContainText(snapshot.location);

  // The snapshot was captured while this project remained open. Close only
  // afterward, then remove the old live folder before any fresh installation
  // receives the selected snapshot.
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const closeResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/close`,
  );
  await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "关闭项目" }).click();
  expect((await closeResponse).ok()).toBeTruthy();
  const sourceHome = path.join(workbench.outputsRoot!, (await readdir(workbench.outputsRoot!)).find((item) => item.endsWith(`__${projectId}`))!);
  // The closed folder is deliberately lost before restore. macOS can report an
  // `ENOTEMPTY` rmdir race while SQLite releases its final sidecar entry.
  await rm(sourceHome, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });

  const isolatedRoot = path.join(path.dirname(workbench.outputsRoot!), "isolated-restored-installation");
  const restoredOutputs = path.join(isolatedRoot, "outputs");
  const restoredApplication = path.join(isolatedRoot, "application");
  await mkdir(isolatedRoot, { recursive: true });
  await runFile("uv", ["run", "plotloom", "restore", "--source", snapshot.location, "--outputs-dir", restoredOutputs], { cwd: repositoryRoot });
  await workbench.restartBackend({
    PLOTLOOM_OUTPUTS_DIR: restoredOutputs,
    PLOTLOOM_APPLICATION_DATA_DIR: restoredApplication,
  });

  await page.evaluate(() => sessionStorage.clear());
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=brief`);
  await expect(page.getByText("发现未保存草稿", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "恢复草稿" }).click();
  await expect(page.getByLabel("片名")).toHaveValue(durableTitle);

  const restoredWorkbench = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(restoredWorkbench.ok(), await restoredWorkbench.text()).toBeTruthy();
  expect((await restoredWorkbench.json() as { reviewedKeyframes: unknown[] }).reviewedKeyframes).toHaveLength(1);
  await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /05 分镜工作台/ }).click();
  await expect(page.getByAltText(/Imported candidate/)).toBeVisible();
  // The worker-scoped fixture can serve later project-folder tests. Its public
  // restart helper intentionally defaults to these original paths, so restore
  // that baseline after proving the isolated installation.
  await workbench.restartBackend();
});

async function createStoryboardProject(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
): Promise<string> {
  const response = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `project-folder-snapshot-${Date.now()}` },
    data: {
      brief: { ...demoProject.brief, title: "Portable snapshot browser fixture" },
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
