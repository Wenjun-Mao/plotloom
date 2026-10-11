import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixture";
import { json } from "./f5a-fixture";

test.use({ actionTimeout: 10_000 });

for (const view of ["创作", "专业"] as const) {
  test(`${view} graph confirmation and application share current review without reload`, async ({ page, request, workbench }) => {
    await page.setViewportSize({ width: 1700, height: 900 });
    // Confirmation requires accepted source/outline, not just an editable graph.
    const id = execFileSync("uv", ["run", "python", "-m", "frontend.e2e.fixtures.bridge_handoff_project", "--outputs", workbench.outputsRoot, "--application", workbench.applicationDataRoot], { cwd: path.resolve(".."), encoding: "utf8" }).trim();
    const base = `${workbench.apiOrigin}/api/v2/projects/${id}`;
    const before = await json(request.get(`${base}/graph-workbench`));
    const viewSwitch = page.getByRole("group", { name: "同一剧情图的两种视图" });
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
    await page.locator('[data-creator-node="choose"] .creator-node-select').click();
    await viewSwitch.getByRole("button", { name: `${view}工作台`, exact: true }).click();
    await page.getByRole("checkbox", { name: "此节点需要拍摄", exact: true }).check();
    // Confirm drains the current draft itself; explicit Save is not a prerequisite.
    const confirm = page.getByRole("button", { name: "确认图内容", exact: true });
    await expect(confirm).toBeEnabled();
    const confirmedResponse = page.waitForResponse(response => response.url().endsWith("/source-outline/section-map") && response.request().method() === "PUT");
    await confirm.click();
    const confirmed = await json(await confirmedResponse);
    expect(confirmed.acceptedSectionMap.mapping.sections.find((section: { sectionId: string }) => section.sectionId === "choose").footageMode).toBe("footage");
    expect(confirmed.graphAdmission.status).toBe("stale");
    expect(confirmed.graphAdmission.graphRevision).toBe(before.baseCanonicalRevision);
    expect((await json(request.get(`${base}/graph-workbench`))).baseCanonicalRevision).toBe(before.baseCanonicalRevision);
    // The other view consumes the same write receipt, not a reload or a new GET.
    await viewSwitch.getByRole("button", { name: `${view === "创作" ? "专业" : "创作"}工作台`, exact: true }).click();
    await expect(page.getByRole("checkbox", { name: "此节点需要拍摄", exact: true })).toBeChecked();
    const apply = page.getByRole("button", { name: "应用到故事路线", exact: true });
    await expect(apply).toBeEnabled();
    const installedResponse = page.waitForResponse(response => response.url().endsWith("/source-outline/section-map/install-graph") && response.request().method() === "POST");
    await apply.click();
    const installed = await json(await installedResponse);
    expect(installed.graphAdmission.status).toBe("current");
    expect(installed.graphAdmission.sectionMapRevision).toBe(confirmed.acceptedSectionMap.revision);
    await viewSwitch.getByRole("button", { name: "创作工作台", exact: true }).click();
    await expect(page.getByRole("region", { name: "整张剧情图 · 保存与应用", exact: true })).toContainText("当前图内容已应用到故事路线");
    await expect(page.getByRole("button", { name: "应用到故事路线", exact: true })).toBeDisabled();
    expect((await json(request.get(`${base}/runs`))).runs).toEqual([]);
  });
}

test("creator Production shows every repeated scene and exact cut, guards drafts and preserves installed media", async ({ page, request, workbench }, info) => {
  test.setTimeout(120_000);
  const id = execFileSync("uv", ["run", "python", "-m", "frontend.e2e.fixtures.bridge_handoff_project", "--outputs", workbench.outputsRoot, "--application", workbench.applicationDataRoot, "--seconds", "2.5", "--repeat-scenes"], { cwd: path.resolve(".."), encoding: "utf8" }).trim();
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const retained = await json(request.get(`${root}/stages`));
  const bridge = await json(request.get(`${root}/production-bridge`));
  const controlId = (await json(request.get(`${root}/script`))).acceptedScript.binding.routeOnlySectionIds[0];
  const secondScene = bridge.proposal.scenes.find((scene: { sectionId: string; sceneIndex: number }) => scene.sectionId === "opening" && scene.sceneIndex === 2);
  const exact = bridge.proposal.cuts.filter((cut: { sectionId: string; sceneIndex: number }) => cut.sectionId === "opening" && cut.sceneIndex === 2).at(-1);
  const writes: string[] = [], errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => { if (request.url().includes("/api/v2/") && request.method() !== "GET") writes.push(request.url()); });
  await page.setViewportSize({ width: 1700, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await page.getByRole("tab", { name: "制作", exact: true }).click();
  const production = page.getByTestId("creator-production");
  await expect(production.locator("[data-production-scene]")).toHaveCount(2);
  await expect(production.locator("[data-production-shot]")).toHaveCount(9);
  await expect(production.locator(`[data-production-scene="${secondScene.sceneId}"]`)).toContainText("场次 2 · S01 · 5 个镜头");
  await expect(page.getByRole("button", { name: "应用到故事路线", exact: true })).toBeDisabled();
  await expect(page.getByRole("region", { name: "整张剧情图 · 保存与应用", exact: true })).toContainText("当前图内容已应用到故事路线");
  await page.screenshot({ path: info.outputPath("production-1700-viewport.png") });
  await page.locator(`[data-creator-node="${controlId}"] .creator-node-select`).click();
  await expect(production).toContainText("没有剧本场次、镜头或节点视频");
  await expect(production.locator("[data-production-shot]")).toHaveCount(0);
  await page.locator('[data-creator-node="opening"] .creator-node-select').click();
  const shot = production.locator(`[data-production-shot="${exact.shotId}"]`);
  await expect(shot.getByRole("button", { name: "镜头审核与媒体", exact: true })).toBeEnabled();
  await shot.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("second-scene-exact-shot-viewport.png") });
  await shot.getByRole("button", { name: "镜头审核与媒体", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`stage=storyboard&entity=shot%3A${exact.shotId}`));
  const summary = page.getByTestId("shot-preparation-summary");
  await expect(summary).toContainText(`当前镜头准备状态 · ${exact.shotId}`);
  await expect(summary).toContainText("精确来源时长 2.5 秒 · 当前绑定");
  await expect(summary).toContainText("缺少当前批准");
  expect(writes).toEqual([]);
  await page.getByRole("button", { name: "创作工作台", exact: true }).click();
  const title = page.getByLabel("章节标题", { exact: true }), original = await title.inputValue();
  await title.fill(`${original} · local unsaved meaning`);
  await page.getByRole("tab", { name: "制作", exact: true }).click();
  await expect(production).toContainText("图草稿与当前已应用路线不同");
  await expect(production.locator(`[data-production-shot="${exact.shotId}"]`).getByRole("button", { name: "镜头审核与媒体", exact: true })).toBeDisabled();
  expect(await json(request.get(`${root}/stages`))).toEqual(retained);
  expect(await json(request.get(`${root}/production-bridge`))).toEqual(bridge);
  await page.getByRole("tab", { name: "故事", exact: true }).click();
  await title.fill(original);
  await page.getByRole("tab", { name: "制作", exact: true }).click();
  await expect(production.locator(`[data-production-shot="${exact.shotId}"]`).getByRole("button", { name: "镜头审核与媒体", exact: true })).toBeEnabled();
  await page.locator(`[data-creator-node="${controlId}"] .creator-node-select`).click();
  await page.getByRole("tab", { name: "故事", exact: true }).click();
  await page.getByLabel("此节点需要拍摄", { exact: true }).check();
  await page.getByRole("button", { name: "保存图草稿", exact: true }).click();
  await expect(page.getByRole("button", { name: "确认图内容", exact: true })).toBeEnabled();
  const restoredGraphAck = page.waitForResponse(response => {
    if (response.request().method() !== "PUT" || new URL(response.url()).pathname !== `/api/v2/projects/${id}/authoring-drafts`) return false;
    const draft = response.request().postDataJSON();
    return draft.editorScope === "story_graph" && draft.payload.selectedNodeId === controlId
      && draft.payload.mapping.sections.some((section: { sectionId: string; footageMode: string }) => section.sectionId === controlId && section.footageMode === "route_only");
  });
  await page.getByLabel("此节点需要拍摄", { exact: true }).uncheck();
  // Drain and acknowledge the restored graph before external board drift and
  // reload; interrupting autosave would correctly protect an older local receipt.
  const graphSave = page.getByRole("button", { name: "保存图草稿", exact: true });
  await graphSave.click();
  const restoredGraph = await json(await restoredGraphAck);
  await expect(graphSave).toBeEnabled();
  expect((await json(request.get(`${root}/graph-workbench`))).draft.payload).toEqual(restoredGraph.payload);
  // Drift only this disposable installed board. Old production remains readable.
  const board = retained.stages.find((stage: { head: { stage: string } }) => stage.head.stage === "storyboard");
  await json(request.patch(`${root}/stages/storyboard`, { data: { expectedRevision: board.head.revision, payload: { ...board.payload, shots: board.payload.shots.map((shot: { id: string; title: string }) => shot.id === exact.shotId ? { ...shot, title: `${shot.title} revised` } : shot) } } }));
  await page.reload();
  await expect(page.getByRole("dialog", { name: "草稿版本已过期", exact: true })).toHaveCount(0);
  await page.locator('[data-creator-node="opening"] .creator-node-select').click();
  await page.getByRole("tab", { name: "制作", exact: true }).click();
  await expect(production.locator(`[data-production-shot="${exact.shotId}"]`)).toContainText("镜头版本不同");
  await expect(production.locator(`[data-production-shot="${exact.shotId}"]`).getByRole("button", { name: "镜头审核与媒体", exact: true })).toBeDisabled();
  expect((await json(request.get(`${root}/production-bridge`))).proposal).toEqual(bridge.proposal);
  expect((await json(request.get(`${root}/runs`))).runs).toEqual([]);
  expect(errors).toEqual([]);
});
