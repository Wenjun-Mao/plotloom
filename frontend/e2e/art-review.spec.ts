import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test } from "./fixture";
import { createAcceptedCastProject, createAcceptedArtProject, writeArtReferenceDelivery, prepareFromBrowser, refreshFromBrowser, writeArtDelivery, writeStageDelivery, mockedArtReferenceStudies, scriptFixture, withSummary, expectOnlySourceMapGraph, switchProject, getJson, fixturePng, type ArtPreparation, type ArtState, type ScriptPreparation } from "./art-review-fixture";

test.describe("F3A production art review", () => {
  test("F3B shows current reference bytes, restart persistence, stale art, and cancellation release", async ({ page, request, workbench }) => {
    test.setTimeout(75_000);
    const projectId = await createAcceptedArtProject(request, workbench.apiOrigin, "f3b-study");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#art`);
    const studies = page.getByTestId("art-reference-studies");
    const scene = page.getByTestId("art-reference-scene-S01");
    await expect(scene.getByTestId("art-reference-direction")).toHaveValue(/半写实厚涂/);
    await expect(scene).toContainText("未准备");
    const imageRequirements = "沿用半写实厚涂，保留冷色晨光，不添加人物。";
    await scene.getByTestId("art-reference-direction").fill(imageRequirements);
    const preparedResponse = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art-reference-proposals`);
    await scene.getByRole("button", { name: "准备图片生成任务" }).click();
    const prepared = await preparedResponse;
    expect(prepared.status()).toBe(201);
    const proposal = (await prepared.json() as { proposal: { id: string; request: { frozenSnapshot: { acceptedArt: { revision: number }; renderDirection: string } } } }).proposal;
    expect(proposal.request.frozenSnapshot.acceptedArt.revision).toBe(1);
    expect(proposal.request.frozenSnapshot.renderDirection).toBe(imageRequirements);
    await expect(scene.getByTestId("art-reference-direction")).toHaveAttribute("readonly", "");
    const copiedResponse = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art-reference-proposals/${proposal.id}/send`);
    await scene.getByRole("button", { name: "发送给图像生成助手" }).click();
    await writeArtReferenceDelivery(await copiedResponse);
    const refreshed = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art-reference-proposals/${proposal.id}/refresh`);
    await scene.getByRole("button", { name: "检查图像交付" }).click();
    const refreshResponse = await refreshed;
    expect(refreshResponse.ok(), await refreshResponse.text()).toBeTruthy();
    await expect(scene).toContainText("图片已返回");
    await expect(scene.getByRole("img", { name: "Beacon room 当前查看图片" })).toBeVisible();
    const decision = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art-reference-decisions`);
    await scene.getByRole("button", { name: "选用这张环境参考图" }).click();
    expect((await decision).status()).toBe(201);
    await expect(scene.getByRole("status")).toHaveText("当前参考图：正在查看的候选。");
    await expect(scene.locator("details.reference-decision-technical")).toContainText("参考版本r1");
    await workbench.restartBackend();
    await page.reload();
    await expect(scene).toContainText("图片已返回");
    await expect(scene.getByTestId("art-reference-direction")).toHaveValue(imageRequirements);
    await expect(scene.getByRole("status")).toHaveText("当前参考图：正在查看的候选。");
    await expect(scene.locator("details.reference-decision-technical")).toContainText("参考版本r1");

    const art = await getJson<any>(request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/art`));
    await getJson(request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/art/reopen`, { data: { expectedArtRevision: art.acceptedArt.revision } }));
    const changed = withSummary(art.acceptedArt.art, "Changed after the reference study was delivered.");
    await getJson(request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/art/save`, { data: { expectedArtRevision: art.acceptedArt.revision, binding: art.acceptedArt.binding, art: changed } }));
    await page.reload();
    await expect(scene).toContainText("设定已变更");
    await expect(scene).toContainText("此前的参考决定已过期");
    const newPrepared = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art-reference-proposals`);
    await scene.getByRole("button", { name: "准备图片生成任务" }).click();
    const active = (await newPrepared).json() as Promise<{ proposal: { id: string } }>;
    const activeId = (await active).proposal.id;
    // The API response alone does not establish that the browser callback has
    // completed its mandatory refresh. Wait for that mounted continuation
    // before exercising a competing lifecycle request.
    await expect(scene.getByRole("button", { name: "取消图片任务" })).toBeVisible();
    const blocked = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/close`);
    expect(blocked.status()).toBe(409);
    await scene.getByRole("button", { name: "取消图片任务" }).click();
    await expect(scene).toContainText("已取消");
    const released = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/close`);
    expect(released.ok(), await released.text()).toBeTruthy();
    expect(activeId).toBeTruthy();
  });

  test("reviews an isolated, explicitly mocked five-candidate F3B browser demonstration", async ({ page, request, workbench }, testInfo) => {
    const projectId = await createAcceptedArtProject(request, workbench.apiOrigin, "mocked-gallery");
    const proposalPath = `/api/v2/projects/${projectId}/art-reference-proposals`;
    await page.route(`**${proposalPath}`, async (route) => {
      if (route.request().method() !== "GET") return route.continue();
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockedArtReferenceStudies(projectId)) });
    });
    await page.route(`**/api/v2/projects/${projectId}/managed-assets/mock-f3b-*/display`, async (route) => {
      await route.fulfill({ contentType: "image/png", body: fixturePng() });
    });
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#art`);
    const studies = page.getByTestId("art-reference-studies");
    const scene = page.getByTestId("art-reference-scene-S01");
    await expect(studies.getByRole("note")).toContainText("已隔离的只读浏览器演示");
    await expect(scene.getByRole("img", { name: "Beacon room 当前查看图片" })).toBeVisible();
    await scene.getByRole("button", { name: "放大查看" }).click();
    await expect(page.getByRole("dialog", { name: "放大查看环境或道具图片" })).toBeVisible();
    await page.getByRole("dialog", { name: "放大查看环境或道具图片", exact: true }).getByRole("button", { name: "关闭", exact: true }).click();

    for (const index of [1, 3]) await studies.getByRole("button", { name: `加入 mock-candidate-${index}.png` }).click();
    await expect(studies.getByTestId("art-reference-comparison")).toContainText("并排比较 · 2 张");
    await studies.getByRole("button", { name: "加入 mock-candidate-0.png" }).click();
    await expect(studies.getByTestId("art-reference-comparison")).toContainText("并排比较 · 3 张");
    await studies.getByRole("button", { name: "加入 mock-candidate-4.png" }).click();
    await expect(studies.getByTestId("art-reference-comparison")).toContainText("并排比较 · 4 张");
    await expect(studies.getByRole("button", { name: "加入 mock-candidate-2.png" })).toBeDisabled();
    await studies.getByRole("button", { name: "移出 mock-candidate-3.png" }).click();
    await studies.getByRole("button", { name: "加入 mock-candidate-2.png" }).click();
    await expect(studies.getByTestId("art-reference-comparison")).toContainText("并排比较 · 4 张");
    const evidenceDirectory = process.env.PLOTLOOM_E2E_EVIDENCE_DIR;
    if (evidenceDirectory) await mkdir(evidenceDirectory, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.screenshot({ path: evidenceDirectory ? path.join(evidenceDirectory, "mocked-f3b-1440.png") : testInfo.outputPath("mocked-f3b-1440.png"), fullPage: true });
    await studies.screenshot({ path: evidenceDirectory ? path.join(evidenceDirectory, "mocked-f3b-panel-1440.png") : testInfo.outputPath("mocked-f3b-panel-1440.png") });
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.screenshot({ path: evidenceDirectory ? path.join(evidenceDirectory, "mocked-f3b-1920.png") : testInfo.outputPath("mocked-f3b-1920.png"), fullPage: true });
    await studies.screenshot({ path: evidenceDirectory ? path.join(evidenceDirectory, "mocked-f3b-panel-1920.png") : testInfo.outputPath("mocked-f3b-panel-1920.png") });
  });

  test("walks the local-only scene and prop reference-decision simulator without API traffic", async ({ page, workbench }, testInfo) => {
    const apiRequests: string[] = [];
    page.on("request", (request) => {
      if (new URL(request.url()).pathname.startsWith("/api/")) apiRequests.push(request.url());
    });
    await page.goto(`${workbench.frontendOrigin}/v2/e2e/f3b-reference-decision-demo.html`);
    const simulator = page.getByTestId("f3b-local-decision-simulator");
    await expect(simulator).toContainText("只更新此页面的 React state");
    const scene = page.getByTestId("art-reference-scene-S-DEMO");
    await scene.getByRole("button", { name: "选用这张环境参考图" }).click();
    await scene.getByRole("button", { name: /scene-B.svg 缩略图/ }).click();
    await scene.getByRole("button", { name: "改用这张环境参考图" }).click();
    await expect(scene.getByRole("status")).toHaveText("当前参考图：正在查看的候选。");
    await expect(scene.getByText("当前参考图", { exact: true })).toBeVisible();
    const sceneDecisionDetails = scene.locator("details.reference-decision-technical");
    await expect(sceneDecisionDetails).not.toHaveAttribute("open", "");
    await expect(sceneDecisionDetails).toContainText("参考版本r2");

    await simulator.getByRole("button", { name: /道具 · Prop · brass compass/ }).click();
    const prop = page.getByTestId("art-reference-prop-P-DEMO");
    await prop.getByRole("button", { name: "选用这张道具参考图" }).click();
    await prop.getByRole("button", { name: /prop-B.svg 缩略图/ }).click();
    await prop.getByRole("button", { name: "改用这张道具参考图" }).click();
    await simulator.getByRole("button", { name: "模拟道具美术变更 → 标记陈旧" }).click();
    await expect(prop).toContainText("此前的参考决定已过期");
    expect(apiRequests).toEqual([]);

    const evidenceDirectory = process.env.PLOTLOOM_E2E_EVIDENCE_DIR;
    if (evidenceDirectory) await mkdir(evidenceDirectory, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await simulator.screenshot({ path: evidenceDirectory ? path.join(evidenceDirectory, "simulated-f3b-decision-1440.png") : testInfo.outputPath("simulated-f3b-decision-1440.png") });
    await page.setViewportSize({ width: 1920, height: 1080 });
    await simulator.screenshot({ path: evidenceDirectory ? path.join(evidenceDirectory, "simulated-f3b-decision-1920.png") : testInfo.outputPath("simulated-f3b-decision-1920.png") });
  });

  test("re-copies a frozen handoff, rejects it, and replaces it through the browser", async ({ page, request, workbench }) => {
    const projectId = await createAcceptedCastProject(request, workbench.apiOrigin, "replace");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#art`);
    const panel = page.getByTestId("art-review");

    const first = await prepareFromBrowser(page, panel, projectId);
    await expect(panel.locator("textarea[readonly]")).toHaveValue(new RegExp(first.jobId));
    await page.reload();
    const recopy = page.waitForResponse((response) => response.request().method() === "GET"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art/candidates/${first.jobId}/handoff`);
    await panel.getByText("查看任务说明（手动方式）", { exact: true }).click();
    await panel.getByRole("button", { name: "查看美术任务说明" }).click();
    const recovered = await recopy;
    expect(recovered.ok(), await recovered.text()).toBeTruthy();
    const recoveredBody = await recovered.json() as ArtPreparation;
    expect(recoveredBody.jobId).toBe(first.jobId);
    expect(recoveredBody.packagePath).toBe(first.packagePath);
    expect(recoveredBody.deliveryPath).toBe(first.deliveryPath);

    await writeArtDelivery(first, "rejected-original");
    await refreshFromBrowser(page, panel, projectId, first.jobId);
    await expect(panel.getByRole("button", { name: "拒绝并取消此美术提案" })).toBeVisible();
    await panel.getByRole("button", { name: "拒绝并取消此美术提案" }).click();
    await expect(panel.getByRole("button", { name: "准备美术设定任务" })).toBeVisible();

    const replacement = await prepareFromBrowser(page, panel, projectId);
    expect(replacement.jobId).not.toBe(first.jobId);
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);
  });

  test("inspects the accepted revision without reopening and preserves it through restart", async ({ page, request, workbench }) => {
    test.setTimeout(75_000);
    const projectId = await createAcceptedCastProject(request, workbench.apiOrigin, "accept");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#art`);
    const panel = page.getByTestId("art-review");
    const prepared = await prepareFromBrowser(page, panel, projectId);
    await writeArtDelivery(prepared, "accepted-original");
    await refreshFromBrowser(page, panel, projectId, prepared.jobId);
    const preview = panel.locator("details.art-report-preview");
    const jsonDetails = panel.locator("details.art-json-editor");
    await expect(preview).toHaveAttribute("open", "");
    await expect(jsonDetails).not.toHaveAttribute("open", "");
    await expect(preview.frameLocator("iframe").locator("body")).toContainText("original specialist candidate");
    expect(await preview.evaluate((element) => !!(element.compareDocumentPosition(document.querySelector("details.art-json-editor")!) & Node.DOCUMENT_POSITION_FOLLOWING))).toBeTruthy();
    await panel.getByRole("button", { name: "放大阅读报告" }).click();
    const candidateReport = page.getByRole("dialog", { name: "美术设定报告（静态阅读）" });
    await expect(candidateReport).toBeVisible();
    await expect(candidateReport).toContainText("报告保留助手交付时的美术设定");
    await candidateReport.getByRole("button", { name: "关闭报告" }).click();
    await expect(candidateReport).not.toBeVisible();

    const editor = panel.locator("textarea.source-outline-json");
    await jsonDetails.locator("summary").click();
    const candidate = JSON.parse(await editor.inputValue()) as Record<string, unknown>;
    const acceptedCandidate = withSummary(candidate, "Author accepted wording, distinct from the original specialist candidate.");
    await editor.fill(JSON.stringify(acceptedCandidate, null, 2));
    await panel.getByRole("button", { name: "确认使用此美术提案" }).click();
    await expect(panel).toContainText("已确认美术设定 r1");

    // The editable candidate has become immutable canon. It must remain
    // inspectable here, without turning "reopen" into the only read surface.
    const current = panel.locator("textarea.source-outline-json");
    await expect(current).toBeDisabled();
    await expect(current).toHaveValue(/Author accepted wording/);
    await expect(preview).toHaveAttribute("open", "");
    await expect(jsonDetails).not.toHaveAttribute("open", "");
    const reportButton = panel.getByRole("button", { name: "放大阅读报告" });
    await reportButton.click();
    const reportDialog = page.getByRole("dialog", { name: "美术设定报告（静态阅读）" });
    await expect(reportDialog).toBeVisible();
    const dialogBox = await reportDialog.boundingBox();
    expect(dialogBox!.height).toBeGreaterThan(page.viewportSize()!.height * 0.8);
    const report = reportDialog.frameLocator('iframe[title="美术设定报告静态内容"]');
    await expect(report.locator("body")).toContainText("original specialist candidate");
    await reportDialog.getByRole("button", { name: "关闭报告" }).click();
    await expect(reportDialog).not.toBeVisible();
    await expect(reportButton).toBeFocused();

    await panel.getByRole("button", { name: "重新打开美术提案" }).click();
    await expect(current).toBeEditable();
    await expect(jsonDetails).not.toHaveAttribute("open", "");
    await jsonDetails.locator("summary").click();
    await expect(current).toBeVisible();
    const reopened = withSummary(JSON.parse(await current.inputValue()) as Record<string, unknown>, "Author saved r2 wording after reopen.");
    await current.fill(JSON.stringify(reopened, null, 2));
    await panel.getByRole("button", { name: "保存重新打开的美术" }).click();
    await expect(panel).toContainText("已确认美术设定 r2");
    await expect(current).toBeDisabled();
    await expect(current).toHaveValue(/Author saved r2 wording/);

    await page.reload();
    await expect(current).toHaveValue(/Author saved r2 wording/);
    await workbench.restartBackend();
    await page.reload();
    await expect(panel).toContainText("已确认美术设定 r2");
    await expect(current).toHaveValue(/Author saved r2 wording/);
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);

    // A replacement proposal must not relabel its report or JSON as accepted art.
    const replacement = await prepareFromBrowser(page, panel, projectId);
    await writeArtDelivery(replacement, "replacement-after-acceptance");
    await refreshFromBrowser(page, panel, projectId, replacement.jobId);
    const previews = panel.locator(".art-report-preview > iframe");
    await expect(previews).toHaveCount(2);
    await expect(previews.nth(0)).toHaveAttribute("src", new RegExp(`${replacement.jobId}/report\\?presentation=static$`));
    await expect(previews.nth(1)).toHaveAttribute("src", new RegExp(`${prepared.jobId}/report\\?presentation=static$`));
    await expect(panel.locator(".art-json-editor[open]")).toHaveCount(0);
    await expect(current.nth(0)).toHaveValue(/The keeper faces a power choice/);
    await expect(current.nth(1)).toHaveValue(/Author saved r2 wording/);
  });

  test("blocks lifecycle operations while a browser-prepared publication is active, then releases them on cancellation", async ({ page, request, workbench }) => {
    const projectId = await createAcceptedCastProject(request, workbench.apiOrigin, "lifecycle");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#art`);
    const panel = page.getByTestId("art-review");
    const prepared = await prepareFromBrowser(page, panel, projectId);
    await expect(panel.getByRole("button", { name: "取消此任务" })).toBeVisible();
    const snapshot = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/snapshots`);
    expect(snapshot.status()).toBe(409);
    const close = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/close`);
    expect(close.status()).toBe(409);
    const cancelled = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art/candidates/${prepared.jobId}/cancel`);
    await panel.getByRole("button", { name: "取消此任务" }).click();
    expect((await cancelled).ok()).toBeTruthy();
    await expect(panel.getByRole("button", { name: "准备美术设定任务" })).toBeEnabled();
    // Close through the requesting client so its pending status reads settle
    // before exclusive admission (ADR 0124), rather than racing a second client.
    const released = page.waitForResponse(response => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/close`);
    await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
    const closed = await released;
    expect(closed.ok(), await closed.text()).toBeTruthy();
    const row = page.locator(`.directory-item[data-project-id="${projectId}"]`);
    await expect(row).toContainText("已关闭 · 可安全复制");
    await row.getByRole("button", { name: "重新打开", exact: true }).click();
    await expect(page.getByRole("dialog", { name: "项目目录", exact: true })).toBeHidden();
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);
    expect(prepared.jobId).toBeTruthy();
  });

  test("does not let a held old-project response mutate the destination project UI", async ({ page, request, workbench }) => {
    const firstProjectId = await createAcceptedCastProject(request, workbench.apiOrigin, "held-first");
    const secondProjectId = await createAcceptedCastProject(request, workbench.apiOrigin, "held-second");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${firstProjectId}&stage=source#art`);
    const firstPanel = page.getByTestId("art-review");
    let release!: () => void;
    let markStarted!: () => void;
    const started = new Promise<void>((resolve) => { markStarted = resolve; });
    const held = new Promise<void>((resolve) => { release = resolve; });
    const heldRoute = async (route: import("@playwright/test").Route) => {
      if (route.request().method() !== "POST") return route.continue();
      markStarted();
      await held;
      try {
        await route.continue();
      } catch {
        // SPA navigation can abort the old request after ArtPanel captured it.
      }
    };
    await page.route(`**/api/v2/projects/${firstProjectId}/art/candidates`, heldRoute);
    try {
      await firstPanel.getByLabel("美术风格", { exact: true }).selectOption("realistic");
      await firstPanel.getByRole("button", { name: "准备美术设定任务" }).click();
      await started;
      await switchProject(page, secondProjectId);
      await page.getByRole("navigation", { name: "创作流程" }).getByRole("link", { name: "美术参考" }).click();
      const destination = page.getByTestId("art-review");
      await expect(destination).toContainText("尚无美术候选");
      await expect(destination.getByRole("button", { name: "准备美术设定任务" })).toBeDisabled();
      release();
      await expect(destination).toContainText("尚无美术候选");
      await expect(destination.getByRole("button", { name: "准备美术设定任务" })).toBeDisabled();
    } finally {
      release?.();
      await page.unroute(`**/api/v2/projects/${firstProjectId}/art/candidates`, heldRoute);
    }
  });

  test("contains a held F3B copy across A-to-B-to-A project ownership", async ({ page, request, workbench }) => {
    const firstProjectId = await createAcceptedArtProject(request, workbench.apiOrigin, "f3b-held-first");
    const secondProjectId = await createAcceptedArtProject(request, workbench.apiOrigin, "f3b-held-second");
    const prepared = await getJson<any>(request.post(`${workbench.apiOrigin}/api/v2/projects/${firstProjectId}/art-reference-proposals`, {
      data: { subjectType: "scene", subjectId: "S01", renderDirection: "Held copy fixture." },
    }));
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${firstProjectId}&stage=source#art`);
    const firstStudies = page.getByTestId("art-reference-studies");
    await expect(firstStudies.getByRole("button", { name: "发送给图像生成助手" })).toBeVisible();

    let release!: () => void;
    let markStarted!: () => void;
    const started = new Promise<void>((resolve) => { markStarted = resolve; });
    const held = new Promise<void>((resolve) => { release = resolve; });
    const heldRoute = async (route: import("@playwright/test").Route) => {
      if (route.request().method() !== "POST") return route.continue();
      markStarted();
      await held;
      try {
        await route.continue();
      } catch {
        // Navigation can abort an already-owned request after its response.
      }
    };
    await page.route(`**/api/v2/projects/${firstProjectId}/art-reference-proposals/${prepared.proposal.id}/send`, heldRoute);
    try {
      await firstStudies.getByRole("button", { name: "发送给图像生成助手" }).click();
      await started;
      await switchProject(page, secondProjectId);
      await switchProject(page, firstProjectId);
      await page.getByRole("navigation", { name: "创作流程" }).getByRole("link", { name: "美术参考" }).click();
      const returnedPanel = page.getByTestId("art-review");
      await expect(returnedPanel).toBeVisible();
      await expect(returnedPanel.getByLabel("复制给 specialist 的冻结任务")).toHaveCount(0);
      // Returning to a mounted owner now revalidates its server authority.
      // Settle that legitimate activation read before attributing later reads
      // to the held, obsolete send continuation.
      await expect(returnedPanel.getByTestId("art-reference-studies").getByRole("button", { name: "发送给图像生成助手" })).toBeEnabled();
      const copiedResponse = page.waitForResponse((response) => response.request().method() === "POST"
        && new URL(response.url()).pathname === `/api/v2/projects/${firstProjectId}/art-reference-proposals/${prepared.proposal.id}/send`);
      const postReleaseRefreshes: string[] = [];
      const recordPostReleaseRefresh = (request: import("@playwright/test").Request) => {
        if (request.method() === "GET" && new URL(request.url()).pathname === `/api/v2/projects/${firstProjectId}/art-reference-proposals`) {
          postReleaseRefreshes.push(request.url());
        }
      };
      page.on("request", recordPostReleaseRefresh);
      release();
      const copied = await copiedResponse;
      expect(copied.ok(), await copied.text()).toBeTruthy();
      // The held browser request has responded and the SPA has gone idle, so a
      // stale continuation cannot be hidden behind an immediate negative check.
      await page.waitForLoadState("networkidle");
      page.off("request", recordPostReleaseRefresh);
      await expect(returnedPanel.getByLabel("复制给 specialist 的冻结任务")).toHaveCount(0);
      await expect(returnedPanel.getByRole("alert")).toHaveCount(0);
      await expect(returnedPanel.getByTestId("art-reference-studies").getByRole("button", { name: "发送给图像生成助手" })).toBeEnabled();
      expect(postReleaseRefreshes).toEqual([]);
    } finally {
      release?.();
      await page.unroute(`**/api/v2/projects/${firstProjectId}/art-reference-proposals/${prepared.proposal.id}/send`, heldRoute);
    }
  });

  test("F4 accepts the three-section script, preserves a scoped edit, and survives backend restart", async ({ page, request, workbench }) => {
    test.setTimeout(75_000);
    const projectId = await createAcceptedArtProject(request, workbench.apiOrigin, "f4-script");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#script`);
    const panel = page.getByTestId("script-review");
    const preparedResponse = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/script/candidates`);
    await panel.getByRole("button", { name: "准备剧本任务" }).click();
    const prepared = await (await preparedResponse).json() as ScriptPreparation;
    const frozenRequest = await readFile(path.join(prepared.packagePath, "request.json"));
    // A deliberately opt-in capture makes an attended specialist handoff from
    // this exact production-browser project reproducible without retaining a
    // normal browser-test fixture or mutating product roots.
    const liveProofRoot = process.env.PLOTLOOM_F4_LIVE_PROOF_DIR;
    if (liveProofRoot) {
      await mkdir(liveProofRoot, { recursive: true });
      await cp(workbench.outputsRoot, path.join(liveProofRoot, "outputs"), { recursive: true });
      const projectFolder = path.basename(path.resolve(prepared.packagePath, "../../../../.."));
      const copiedJobRoot = path.join(liveProofRoot, "outputs", projectFolder, "outputs", "creative-handoff", "jobs", prepared.jobId);
      await writeFile(path.join(liveProofRoot, "proof.json"), JSON.stringify({
        projectId, packagePath: path.join(copiedJobRoot, "package"), deliveryPath: path.join(copiedJobRoot, "delivery"),
      }, null, 2));
    }
    await page.reload();
    const recopy = page.waitForResponse((response) => response.request().method() === "GET"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/script/candidates/${prepared.jobId}/handoff`);
    await panel.getByText("查看任务说明（手动方式）", { exact: true }).click();
    await panel.getByRole("button", { name: "恢复剧本任务" }).click();
    const recovered = await recopy;
    expect(recovered.ok(), await recovered.text()).toBeTruthy();
    const recoveredBody = await recovered.json() as ScriptPreparation;
    expect(recoveredBody.jobId).toBe(prepared.jobId);
    expect(recoveredBody.packagePath).toBe(prepared.packagePath);
    expect(recoveredBody.deliveryPath).toBe(prepared.deliveryPath);
    expect(await readFile(path.join(recoveredBody.packagePath, "request.json"))).toEqual(frozenRequest);
    await writeStageDelivery(prepared, "script.json", scriptFixture(), "f4-script", "script");
    const refreshed = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/specialist-tasks/script/${prepared.jobId}/check`);
    await panel.getByRole("button", { name: "立即检查" }).click();
    expect((await refreshed).ok()).toBeTruthy();
    await panel.getByRole("button", { name: "确认使用此剧本" }).click();
    await expect(panel).toContainText("已确认 r1");
    await panel.getByRole("button", { name: "重新打开剧本" }).click();
    await panel.getByRole("combobox").selectOption("opening");
    const editor = panel.locator("textarea.source-outline-json");
    const opening = JSON.parse(await editor.inputValue()) as Record<string, unknown>;
    await editor.fill(JSON.stringify({ ...opening, cliff: "Edited opening leaves its own consequence." }, null, 2));
    await panel.getByRole("button", { name: "保存此章节，不覆盖其他章节" }).click();
    await expect(panel).toContainText("已确认 r2");
    await workbench.restartBackend(); await page.reload();
    await expect(panel).toContainText("已确认 r2");
    const accepted = await getJson<any>(request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/script`));
    expect(accepted.acceptedScript.script.episodes[2].ep).toBe(3);
  });
});
