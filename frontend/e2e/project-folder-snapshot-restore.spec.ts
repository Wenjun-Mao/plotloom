import { navigateToSecondaryTool, openMediaPreparation, openMediaKeyframes, openServiceStatus } from "./workbench-controls";
import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";
import { execFile } from "node:child_process";
import { mkdir, readdir, rm } from "node:fs/promises";
import { promisify } from "node:util";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const retainedStill = path.join(repositoryRoot, "docs/verification/supporting/p0-generated/01-arrival.png");
const runFile = promisify(execFile);

test("snapshot receipt remains owned by its project through directory A-B-A navigation", async ({ page, request, workbench }) => {
  const firstId = await createStoryboardProject(request, workbench.apiOrigin, "Snapshot receipt A");
  const secondId = await createStoryboardProject(request, workbench.apiOrigin, "Snapshot receipt B");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${firstId}&stage=brief`);
  await expect(page.getByRole("heading", { name: "项目简报", exact: true })).toBeVisible();
  const snapshotResponse = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${firstId}/snapshots`);
  await page.getByRole("button", { name: "创建恢复快照", exact: true }).click();
  const response = await snapshotResponse;
  expect(response.ok(), await response.text()).toBeTruthy();
  const snapshot = await response.json() as { location: string };
  const receipt = page.locator("details.topbar-snapshot-receipt");
  await expect(receipt.getByRole("status")).toHaveText("恢复快照已完成");
  await receipt.locator("summary").click();
  await expect(receipt.locator("code")).toHaveText(snapshot.location);
  await receipt.locator("summary").click();

  const snapshotWrites: string[] = [];
  page.on("request", request => {
    if (request.method() === "POST" && new URL(request.url()).pathname.endsWith("/snapshots")) {
      snapshotWrites.push(request.url());
    }
  });
  // Stay in the same mounted app: a full-page navigation would discard the
  // receipt and could hide a cross-project ownership regression.
  for (const id of [secondId, firstId]) {
    await page.getByRole("button", { name: /当前项目 · 切换/ }).click();
    const directory = page.getByRole("dialog", { name: "项目目录", exact: true });
    await directory.locator(`.directory-item[data-project-id="${id}"] .directory-open`).click();
    await expect(directory).toBeHidden();
    await expect(page).toHaveURL(new RegExp(`project=${id}`));
    if (id === secondId) {
      await expect(receipt).toHaveCount(0);
      await expect(page.getByText(snapshot.location, { exact: true })).toHaveCount(0);
    } else {
      await expect(receipt.getByRole("status")).toHaveText("恢复快照已完成");
      await receipt.locator("summary").click();
      await expect(receipt.locator("code")).toHaveText(snapshot.location);
      await expect(receipt.locator("code")).toBeVisible();
    }
  }
  expect(snapshotWrites).toEqual([]);
});

for (const viewport of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) {
  test(`status disclosure reveals its reading entrance from a scrolled page ${viewport.width}x${viewport.height}`, async ({ page, request, workbench }) => {
    await page.setViewportSize(viewport);
    const projectId = await createStoryboardProject(request, workbench.apiOrigin);
    // Stress the actual catalog-owned diagnostic surface, not a replacement
    // toolbar or a viewport-specific CSS fixture.
    const longReason = Array(2000).fill("诊断详情").join(" · ");
    await page.route("**/api/v2/text-provider-profiles", async route => {
      const response = await route.fetch();
      const catalog = await response.json();
      for (const profile of catalog.profiles) profile.readiness.reasonCode = longReason;
      await route.fulfill({ response, json: catalog });
    });
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=brief`);
    await expect(page.getByRole("heading", { name: "项目简报", exact: true })).toBeVisible();
    // A project with no run does not eagerly load its model catalog. Read it
    // through the real settings owner, then close without saving anything.
    await page.getByRole("button", { name: "供应商与会话密钥", exact: true }).click();
    const settings = page.getByRole("dialog", { name: "供应商与会话密钥", exact: true });
    await expect(settings).toBeVisible();
    await settings.getByRole("button", { name: "取消", exact: true }).click();
    await expect(page.locator(".topbar-technical-status")).toContainText(longReason);
    await page.evaluate(() => window.scrollTo(0, 500));
    const snapshotResponse = page.waitForResponse(response => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/snapshots`);
    await page.getByRole("button", { name: "创建恢复快照", exact: true }).click();
    const response = await snapshotResponse;
    expect(response.ok(), await response.text()).toBeTruthy();
    const snapshot = await response.json() as { location: string };
    const receipt = page.locator("details.topbar-snapshot-receipt");
    await expect(receipt.getByRole("status")).toHaveText("恢复快照已完成");
    await expect(receipt.getByRole("status")).toBeVisible();
    expect(await receipt.locator("summary").evaluate(element => {
      const bounds = element.getBoundingClientRect();
      return bounds.top >= 0 && bounds.bottom <= innerHeight;
    })).toBe(true);
    await page.screenshot({ path: test.info().outputPath(`snapshot-complete-${viewport.width}x${viewport.height}.png`) });
    await expect(page.locator("details.topbar-technical-status")).not.toHaveAttribute("open");
    await receipt.locator("summary").click();
    await expect(receipt.locator("code")).toHaveText(snapshot.location);
    await expect(receipt.locator("code")).toBeVisible();
    await expect.poll(() => receipt.locator("code").evaluate(element => {
      const bounds = element.getBoundingClientRect();
      return bounds.top >= 0 && bounds.bottom <= innerHeight;
    })).toBe(true);
    await page.screenshot({ path: test.info().outputPath(`snapshot-location-${viewport.width}x${viewport.height}.png`) });
    await receipt.locator("summary").click();
    const writes: string[] = [];
    page.on("request", request => {
      if (new URL(request.url()).pathname.startsWith("/api/v2/") && !["GET", "HEAD"].includes(request.method())) writes.push(`${request.method()} ${request.url()}`);
    });
    const status = page.locator("details.topbar-technical-status");
    const summary = status.locator("summary");
    await page.evaluate(() => window.scrollTo(0, 500));
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(100);
    expect(await page.locator(".topbar").evaluate(element => getComputedStyle(element).position)).toBe("sticky");
    await summary.click();
    await expect.poll(() => summary.evaluate(element => {
      const bounds = element.getBoundingClientRect();
      return bounds.top >= 0 && bounds.bottom <= innerHeight;
    })).toBe(true);
    expect(await page.locator(".topbar").evaluate(element => getComputedStyle(element).position)).toBe("relative");
    expect(await status.evaluate(element => element.getBoundingClientRect().height)).toBeGreaterThan(viewport.height);
    const diagnostic = status.getByText(longReason, { exact: false });
    await diagnostic.scrollIntoViewIfNeeded();
    expect(await diagnostic.evaluate(element => {
      const bounds = element.getBoundingClientRect();
      return bounds.bottom > 0 && bounds.top < innerHeight;
    })).toBe(true);
    const title = page.getByLabel("片名", { exact: true });
    await title.scrollIntoViewIfNeeded();
    expect(await title.evaluate(element => {
      const bounds = element.getBoundingClientRect();
      return document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2) === element;
    })).toBe(true);
    await summary.click();
    await expect(status).not.toHaveAttribute("open");
    await page.evaluate(() => window.scrollTo(0, 500));
    await summary.click();
    await expect.poll(() => summary.evaluate(element => element.getBoundingClientRect().top >= 0)).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(viewport.width);
    expect(writes).toEqual([]);
  });
}

test("snapshots an open project then restores its draft, reviewed media, and lineage into a fresh installation", async ({ page, request, workbench }) => {
  expect(workbench.outputsRoot).toBeTruthy();
  const projectId = await createStoryboardProject(request, workbench.apiOrigin);
  const durableTitle = "E2E snapshot retains this server draft";
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=brief`);
  await page.getByLabel("片名").fill(durableTitle);
  await openServiceStatus(page);
  await expect(page.getByText("草稿：已保存", { exact: true })).toBeVisible();

  await navigateToSecondaryTool(page, "分镜工作台");
  await openMediaPreparation(page);
  await openMediaKeyframes(page);
  await page.getByLabel("审核人标签").fill("snapshot fixture reviewer");
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  await page.getByLabel("来源声明").fill("Offline reviewed still retained by the portable snapshot.");
  await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
  await page.getByLabel("候选图像比较").locator(".media-candidate").getByTestId(/^keep-candidate-/).click();
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
  // Leave the media owner before the exclusive snapshot: its newly mounted
  // draft forms still rehydrate after the mutation refresh. A prior navigation
  // networkidle state does not prove those later requests have settled.
  await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
  await expect(page.getByRole("heading", { name: "项目简报", exact: true })).toBeVisible();
  const recovery = page.getByRole("dialog", { name: "发现可恢复草稿" });
  await expect(recovery).toBeVisible();
  await recovery.getByRole("button", { name: "恢复草稿", exact: true }).click();
  await expect(page.getByLabel("片名")).toHaveValue(durableTitle);

  const snapshotResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/snapshots`,
  );
  await page.getByRole("button", { name: "创建恢复快照" }).click();
  const snapshotResult = await snapshotResponse;
  expect(snapshotResult.ok(), await snapshotResult.text()).toBeTruthy();
  const snapshot = await snapshotResult.json() as { location: string; snapshotId: string };
  const receipt = page.locator("details.topbar-snapshot-receipt");
  await expect(receipt.getByRole("status")).toBeVisible();
  await receipt.locator("summary").click();
  await expect(receipt.locator("code")).toHaveText(snapshot.location);
  await expect(receipt.locator("code")).toBeVisible();
  await receipt.locator("summary").click();

  // The snapshot was captured while this project remained open. Close only
  // afterward, then remove the old live folder before any fresh installation
  // receives the selected snapshot.
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const closeResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/close`,
  );
  await page.locator(`.directory-item[data-project-id="${projectId}"]`).getByRole("button", { name: "保存并关闭项目", exact: true }).click();
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
  await expect(page.getByText("发现可恢复草稿", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "恢复草稿" }).click();
  await expect(page.getByLabel("片名")).toHaveValue(durableTitle);

  const restoredWorkbench = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(restoredWorkbench.ok(), await restoredWorkbench.text()).toBeTruthy();
  expect((await restoredWorkbench.json() as { reviewedKeyframes: unknown[] }).reviewedKeyframes).toHaveLength(1);
  await navigateToSecondaryTool(page, "分镜工作台");
  await openMediaPreparation(page);
  await expect(page.getByAltText(/候选图片/)).toBeVisible();
  // The explicit restart helper still returns this journey to its original
  // installation after proving the isolated restore.
  await workbench.restartBackend();
});

async function createStoryboardProject(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
  title = "Portable snapshot browser fixture",
): Promise<string> {
  const response = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `project-folder-snapshot-${Date.now()}` },
    data: {
      brief: { ...demoProject.brief, title },
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
