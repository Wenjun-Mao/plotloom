import { test, expect } from "./fixture";
import { createScriptProject, json } from "./f5a-fixture";
import { createAcceptedArtProject } from "./art-review-fixture";
import { fixtureRun } from "../tests/autopilot-fixture";

test("cancelled partial work requires fresh explicit continuation consent and shows exact unknown blockers", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "explicit-continuation");
  const stopped = { ...fixtureRun, projectId: id, state: "cancelled", bundle: null };
  await page.route(`**/api/v2/projects/${id}/autopilot`, route => route.fulfill({ json: stopped }));
  let eligible = false;
  await page.route(`**/api/v2/projects/${id}/autopilot/continuation-context`, route => route.fulfill({ json: {
    runId: stopped.id, runRevision: stopped.revision, materialClosure: "a".repeat(64), eligible,
    blockers: eligible ? [] : ["原任务 ij_exact_unknown 尚未核对；不会重复发送。"],
    inheritedOperations: 8, lifetimeJobs: 10, lifetimeImages: 2,
  } }));
  const submissions: Record<string, unknown>[] = [];
  await page.route(`**/api/v2/projects/${id}/autopilot/continue`, route => {
    submissions.push(route.request().postDataJSON());
    return route.fulfill({ json: { ...stopped, id: "successor", state: "running" } });
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source`);
  await page.getByRole("button", { name: "继续剩余素材", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "ij_exact_unknown" })).toBeVisible();
  await page.screenshot({ path: "../output/playwright/continuation-blocked.png" });
  expect(submissions).toEqual([]);
  eligible = true;
  await page.getByRole("button", { name: "继续剩余素材", exact: true }).click();
  const dialog = page.getByRole("alertdialog", { name: "继续剩余素材" });
  await expect(dialog).toContainText("继承 8 项已采用工作");
  await page.screenshot({ path: "../output/playwright/continuation-consent.png" });
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  expect(submissions).toEqual([]);
  await page.getByRole("button", { name: "继续剩余素材", exact: true }).click();
  await page.getByRole("button", { name: "确认继续剩余素材", exact: true }).click();
  await expect.poll(() => submissions.length).toBe(1);
  expect(submissions[0].expectedRunId).toBe(stopped.id);
  expect(submissions[0].expectedRunRevision).toBe(stopped.revision);
  expect(submissions[0].expectedMaterialClosure).toBe("a".repeat(64));
  expect(submissions[0]).not.toHaveProperty("executionPins");
});

test("actual stage workspaces distinguish automatic ownership while keeping manual controls and read-only reports", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "automatic-guidance");
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const [source, cast, art, script] = await Promise.all([json(request.get(`${root}/source-outline`)), json(request.get(`${root}/cast`)), json(request.get(`${root}/art`)), json(request.get(`${root}/script`))]);
  // Presentation-only actor fixture: real retained stage reads/report routes,
  // no synthetic canonical mutation or native dispatch from the browser.
  await page.route(`**/api/v2/projects/${id}/autopilot`, route => route.fulfill({ json: {
    ...fixtureRun, projectId: id, state: "running", phase: "art", checkpoints: [
      ["outline", source.acceptedOutline], ["characters", cast.acceptedCast], ["art", art.acceptedArt], ["script", script.acceptedScript],
    ].map(([operationKey, value]) => ({ operationKey, state: "adopted", evidence: { owner: operationKey,
      result: { revision: value.revision, contentHash: value.contentHash } } })),
  } }));
  const writes: string[] = [];
  page.on("request", req => { if (["POST", "PUT", "PATCH", "DELETE"].includes(req.method())) writes.push(req.url()); });
  const guide = page.getByTestId("recommended-workflow").locator(".recommended-workflow-next");
  for (const target of ["source#source", "characters", "source#art", "source#script"]) {
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=${target}`);
    await expect(guide).toContainText("当前自动阶段：美术设定");
    await expect(guide).toContainText("保存手动修改将接管自动运行");
    const stageGuide = page.locator(".stage-guide-content:visible").first();
    await expect(stageGuide).toContainText("一次完整人工审阅");
    await expect(stageGuide).not.toContainText("下一步准备");
    if (target === "source#source") {
      const open = page.getByRole("button", { name: "阅读AI 已采用大纲", exact: true });
      await expect(open).toBeEnabled(); await open.click();
      const report = page.getByRole("dialog");
      await expect(report.getByRole("heading")).toContainText(`AI 已采用大纲 r${source.acceptedOutline.revision}`);
      await expect(report).toContainText("阅读与关闭不会确认、接管");
      await page.getByRole("button", { name: "关闭阅读" }).click();
      await expect(page.getByRole("button", { name: "确认改编内容", exact: true })).toBeEnabled();
    }
    if (target === "characters") {
      await expect(page.getByRole("button", { name: "编辑角色设定", exact: true })).toBeEnabled();
      const gallery = page.getByTestId("character-reference-gallery");
      await expect(gallery.locator(".reference-gallery-cast-state strong")).toHaveText(`AI 已采用角色设定 r${cast.acceptedCast.revision}`);
      await expect(gallery.getByRole("navigation", { name: "角色主体" })).toContainText("设定中的角色");
      await expect(gallery.getByRole("navigation", { name: "角色主体" })).not.toContainText("已确认角色");
      for (const height of [900, 600]) {
        await page.setViewportSize({ width: 1440, height });
        await gallery.locator(".reference-gallery-intro").scrollIntoViewIfNeeded();
        await page.screenshot({ path: `../.local/native927-caption/pixels/native927-caption-character-${height}.png` });
      }
      await page.setViewportSize({ width: 1440, height: 900 });
    }
    if (target === "source#art") {
      const preparation = page.locator('section[aria-label="准备美术设定候选"]');
      await expect(preparation.getByRole("heading", { name: "准备新的美术候选（可选）" })).toBeVisible();
      await expect(preparation).toContainText("AI 已采用的美术设定");
      await expect(preparation).toContainText("此选择用于新的美术任务，不会修改角色设定或图片。");
      await expect(preparation).not.toContainText("已确认的角色设定");
      await preparation.scrollIntoViewIfNeeded();
      await page.screenshot({ path: "../.local/native927-caption/pixels/native927-caption-art-preparation-1440x900.png" });
      const gallery = page.getByTestId("art-reference-studies");
      await expect(gallery.locator("header strong").first()).toHaveText("按AI 已采用的美术设定生成图片");
      await gallery.locator("header").first().scrollIntoViewIfNeeded();
      await page.screenshot({ path: "../.local/native927-caption/pixels/native927-caption-art-gallery-1440x900.png" });
    }
  }
  // Observe admitted first-frame work before selection; this is an actor fixture,
  // with actual retained stage reads and no preparation or dispatch from navigation.
  await page.unroute(`**/api/v2/projects/${id}/autopilot`);
  await page.route(`**/api/v2/projects/${id}/autopilot`, route => route.fulfill({ json: { ...fixtureRun, projectId: id, state: "waiting", phase: "first-frames", frames: [], checkpoints: [] } }));
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`);
  await expect(guide).toContainText("当前自动阶段：镜头首帧");
  await expect(page.getByTestId("character-reference-gallery").locator(".reference-gallery-cast-state strong")).toContainText("来源待核实");
  await page.screenshot({ path: "../.local/native927-caption/pixels/native927-caption-phase-1440x900.png", fullPage: false });
  expect(writes).toEqual([]);
  expect(await json(request.get(`${root}/autopilot`))).toBeNull();
});

test("saved-Brief style bindings survive Art and Characters navigation without generation", async ({ page, request, workbench }, testInfo) => {
  const id = await createAcceptedArtProject(request, workbench.apiOrigin, "saved-brief-render-contract");
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const [cast, art] = await Promise.all([json(request.get(`${root}/cast`)), json(request.get(`${root}/art`))]);
  await page.route(`**/api/v2/projects/${id}/autopilot`, route => route.fulfill({ json: {
    ...fixtureRun, projectId: id, state: "cancelled", phase: "art", checkpoints: [
      ["characters", cast.acceptedCast], ["art", art.acceptedArt],
    ].map(([operationKey, value]) => ({ operationKey, state: "adopted", evidence: { owner: operationKey,
      result: { revision: value.revision, contentHash: value.contentHash } } })),
  } }));
  const savedBriefRenderContract = {
    version: 1, authority: "saved_brief", stageInstructionContract: "plotloom.autopilot.saved-brief-receiving-contract.v2",
    direction: "A rainy old harbor with restrained blue-green light.", emptyDirectionRule: null,
    validatorHashes: Object.fromEntries(["policy", "artAdapter", "artUpstream", "artGateSummary", "castAdapter", "castUpstream"].map(name => [name, "a".repeat(64)])),
    contentHash: "b".repeat(64),
  };
  await page.route(`**/api/v2/projects/${id}/cast`, async route => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const state = await response.json();
    state.acceptedCast.binding.renderContract = savedBriefRenderContract;
    await route.fulfill({ response, body: JSON.stringify(state) });
  });
  await page.route(`**/api/v2/projects/${id}/art`, async route => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const state = await response.json();
    state.acceptedArt.binding.renderContract = savedBriefRenderContract;
    await route.fulfill({ response, body: JSON.stringify(state) });
  });
  const browserWrites: string[] = [];
  page.on("request", browserRequest => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(browserRequest.method())) browserWrites.push(browserRequest.url());
  });

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#art`);
  const artPanel = page.getByTestId("art-review");
  await expect(artPanel).toContainText("美术风格：项目简报视觉方向");
  await expect(artPanel).toContainText("项目视觉要求：A rainy old harbor with restrained blue-green light.");
  await page.getByRole("link", { name: "角色", exact: true }).click();
  const castPanel = page.getByTestId("cast-review");
  await expect(castPanel).toContainText("AI 已采用角色图像风格：项目简报视觉方向");
  await expect(castPanel.getByTestId("render-style-presentation")).not.toContainText("已确认");
  await expect(castPanel).toContainText("项目视觉要求：A rainy old harbor with restrained blue-green light.");
  await page.getByRole("link", { name: "美术参考", exact: true }).click();
  await expect(artPanel).toContainText("项目简报视觉方向");

  for (const viewport of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(viewport);
    const suffix = `${viewport.width}x${viewport.height}`;
    for (const [label, panel, name] of [["美术参考", artPanel, "art"], ["角色", castPanel, "cast"]] as const) {
      await page.getByRole("link", { name: label, exact: true }).click();
      const presentation = panel.getByTestId("render-style-presentation");
      await presentation.scrollIntoViewIfNeeded();
      await expect(presentation).toBeVisible();
      await expect(presentation).toContainText("项目视觉要求：A rainy old harbor with restrained blue-green light.");
      await page.screenshot({ path: testInfo.outputPath(`saved-brief-${name}-${suffix}.png`) });
    }
  }

  expect(browserWrites).toEqual([]);
  expect(await json<{ totalRequests: number }>(request.get(`${workbench.providerOrigin}/control/status`))).toMatchObject({ totalRequests: 0 });
});
