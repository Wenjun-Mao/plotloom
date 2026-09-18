import { createHash } from "node:crypto";
import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";

import { demoProject } from "../src/demo";
import { expect, test } from "./fixture";

type Api = import("@playwright/test").APIRequestContext;

type ArtPreparation = {
  jobId: string;
  packagePath: string;
  deliveryPath: string;
  expectedArtRevision: number;
  binding: unknown;
};

type ArtState = {
  candidate: { jobId: string; status: string } | null;
  acceptedArt: { revision: number; art: Record<string, unknown> } | null;
  status: string;
};

type ScriptPreparation = { jobId: string; packagePath: string; deliveryPath: string; expectedScriptRevision: number; binding: unknown };

test.describe("F3A production art review", () => {
  test("F3B shows current reference bytes, restart persistence, stale art, and cancellation release", async ({ page, request, workbench }) => {
    test.setTimeout(75_000);
    const projectId = await createAcceptedArtProject(request, workbench.apiOrigin, "f3b-study");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
    const studies = page.getByTestId("art-reference-studies");
    const scene = page.getByTestId("art-reference-scene-S01");
    await expect(studies).toContainText("Cinematic realism");
    await expect(scene).toContainText("missing");
    const preparedResponse = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art-reference-proposals`);
    await scene.getByRole("button", { name: "准备研究" }).click();
    const prepared = await preparedResponse;
    expect(prepared.status()).toBe(201);
    const proposal = (await prepared.json() as { proposal: { id: string; request: { frozenSnapshot: { acceptedArt: { revision: number } } } } }).proposal;
    expect(proposal.request.frozenSnapshot.acceptedArt.revision).toBe(1);
    const copiedResponse = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art-reference-proposals/${proposal.id}/copy`);
    await scene.getByRole("button", { name: "复制 ImageGen 任务" }).click();
    await writeArtReferenceDelivery(await copiedResponse);
    const refreshed = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art-reference-proposals/${proposal.id}/refresh`);
    await scene.getByRole("button", { name: "刷新 delivery" }).click();
    const refreshResponse = await refreshed;
    expect(refreshResponse.ok(), await refreshResponse.text()).toBeTruthy();
    await expect(scene).toContainText("current");
    await expect(scene.locator("img")).toBeVisible();
    await workbench.restartBackend();
    await page.reload();
    await expect(scene).toContainText("current");

    const art = await getJson<any>(request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/art`));
    await getJson(request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/art/reopen`, { data: { expectedArtRevision: art.acceptedArt.revision } }));
    const changed = withSummary(art.acceptedArt.art, "Changed after the reference study was delivered.");
    await getJson(request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/art/save`, { data: { expectedArtRevision: art.acceptedArt.revision, binding: art.acceptedArt.binding, art: changed } }));
    await page.reload();
    await expect(scene).toContainText("changed / stale");
    const newPrepared = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art-reference-proposals`);
    await scene.getByRole("button", { name: "准备研究" }).click();
    const active = (await newPrepared).json() as Promise<{ proposal: { id: string } }>;
    const activeId = (await active).proposal.id;
    // The API response alone does not establish that the browser callback has
    // completed its mandatory refresh. Wait for that mounted continuation
    // before exercising a competing lifecycle request.
    await expect(scene.getByRole("button", { name: "取消 handoff" })).toBeVisible();
    const blocked = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/close`);
    expect(blocked.status()).toBe(409);
    await scene.getByRole("button", { name: "取消 handoff" }).click();
    await expect(scene).toContainText("cancelled");
    const released = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/close`);
    expect(released.ok(), await released.text()).toBeTruthy();
    expect(activeId).toBeTruthy();
  });

  test("re-copies a frozen handoff, rejects it, and replaces it through the browser", async ({ page, request, workbench }) => {
    const projectId = await createAcceptedCastProject(request, workbench.apiOrigin, "replace");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
    const panel = page.getByTestId("art-review");

    const first = await prepareFromBrowser(page, panel, projectId);
    await expect(panel.getByLabel("复制给 specialist 的冻结任务")).toContainText(first.jobId);
    await page.reload();
    const recopy = page.waitForResponse((response) => response.request().method() === "GET"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art/candidates/${first.jobId}/handoff`);
    await panel.getByRole("button", { name: "重新复制冻结 handoff" }).click();
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
    await expect(panel.getByRole("button", { name: "准备并复制 art specialist handoff" })).toBeVisible();

    const replacement = await prepareFromBrowser(page, panel, projectId);
    expect(replacement.jobId).not.toBe(first.jobId);
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);
  });

  test("inspects the accepted revision without reopening and preserves it through restart", async ({ page, request, workbench }) => {
    test.setTimeout(75_000);
    const projectId = await createAcceptedCastProject(request, workbench.apiOrigin, "accept");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
    const panel = page.getByTestId("art-review");
    const prepared = await prepareFromBrowser(page, panel, projectId);
    await writeArtDelivery(prepared, "accepted-original");
    await refreshFromBrowser(page, panel, projectId, prepared.jobId);

    const editor = panel.locator("textarea.source-outline-json");
    const candidate = JSON.parse(await editor.inputValue()) as Record<string, unknown>;
    const acceptedCandidate = withSummary(candidate, "Author accepted wording, distinct from the original specialist candidate.");
    await editor.fill(JSON.stringify(acceptedCandidate, null, 2));
    await panel.getByRole("button", { name: "显式接受此美术提案" }).click();
    await expect(panel).toContainText("已接受 r1");

    // The editable candidate has become immutable canon. It must remain
    // inspectable here, without turning "reopen" into the only read surface.
    const current = panel.locator("textarea.source-outline-json");
    await expect(current).toBeDisabled();
    await expect(current).toHaveValue(/Author accepted wording/);
    await panel.getByText("打开只读上游报告").click();
    const report = panel.frameLocator('iframe[title="derived upstream art report"]');
    await expect(report.locator("body")).toContainText("Original specialist report");
    await expect(report.locator("body")).toContainText("original specialist candidate");

    await panel.getByRole("button", { name: "重新打开美术提案" }).click();
    await expect(current).toBeEditable();
    const reopened = withSummary(JSON.parse(await current.inputValue()) as Record<string, unknown>, "Author saved r2 wording after reopen.");
    await current.fill(JSON.stringify(reopened, null, 2));
    await panel.getByRole("button", { name: "保存重新打开的美术" }).click();
    await expect(panel).toContainText("已接受 r2");
    await expect(current).toBeDisabled();
    await expect(current).toHaveValue(/Author saved r2 wording/);

    await page.reload();
    await expect(current).toHaveValue(/Author saved r2 wording/);
    await workbench.restartBackend();
    await page.reload();
    await expect(panel).toContainText("已接受 r2");
    await expect(current).toHaveValue(/Author saved r2 wording/);
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);
  });

  test("blocks lifecycle operations while a browser-prepared publication is active, then releases them on cancellation", async ({ page, request, workbench }) => {
    const projectId = await createAcceptedCastProject(request, workbench.apiOrigin, "lifecycle");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
    const panel = page.getByTestId("art-review");
    const prepared = await prepareFromBrowser(page, panel, projectId);
    await expect(panel.getByRole("button", { name: "取消 handoff" })).toBeVisible();
    const snapshot = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/snapshots`);
    expect(snapshot.status()).toBe(409);
    const close = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/close`);
    expect(close.status()).toBe(409);
    const cancelled = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art/candidates/${prepared.jobId}/cancel`);
    await panel.getByRole("button", { name: "取消 handoff" }).click();
    expect((await cancelled).ok()).toBeTruthy();
    await expect(panel.getByRole("button", { name: "准备并复制 art specialist handoff" })).toBeEnabled();
    const released = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/close`);
    expect(released.ok(), await released.text()).toBeTruthy();
    const reopened = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/open`);
    expect(reopened.ok(), await reopened.text()).toBeTruthy();
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);
    expect(prepared.jobId).toBeTruthy();
  });

  test("does not let a held old-project response mutate the destination project UI", async ({ page, request, workbench }) => {
    const firstProjectId = await createAcceptedCastProject(request, workbench.apiOrigin, "held-first");
    const secondProjectId = await createAcceptedCastProject(request, workbench.apiOrigin, "held-second");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${firstProjectId}&stage=source`);
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
      await firstPanel.getByRole("button", { name: "准备并复制 art specialist handoff" }).click();
      await started;
      await switchProject(page, secondProjectId);
      await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /^01 来源与大纲/ }).click();
      const destination = page.getByTestId("art-review");
      await expect(destination).toContainText("尚无美术候选");
      await expect(destination.getByRole("button", { name: "准备并复制 art specialist handoff" })).toBeEnabled();
      release();
      await expect(destination).toContainText("尚无美术候选");
      await expect(destination.getByRole("button", { name: "准备并复制 art specialist handoff" })).toBeEnabled();
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
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${firstProjectId}&stage=source`);
    const firstStudies = page.getByTestId("art-reference-studies");
    await expect(firstStudies.getByRole("button", { name: "复制 ImageGen 任务" })).toBeVisible();

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
    await page.route(`**/api/v2/projects/${firstProjectId}/art-reference-proposals/${prepared.proposal.id}/copy`, heldRoute);
    try {
      await firstStudies.getByRole("button", { name: "复制 ImageGen 任务" }).click();
      await started;
      await switchProject(page, secondProjectId);
      await switchProject(page, firstProjectId);
      await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /^01 来源与大纲/ }).click();
      const returnedPanel = page.getByTestId("art-review");
      await expect(returnedPanel).toBeVisible();
      await expect(returnedPanel.getByLabel("复制给 specialist 的冻结任务")).toHaveCount(0);
      const copiedResponse = page.waitForResponse((response) => response.request().method() === "POST"
        && new URL(response.url()).pathname === `/api/v2/projects/${firstProjectId}/art-reference-proposals/${prepared.proposal.id}/copy`);
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
      await expect(returnedPanel.getByTestId("art-reference-studies").getByRole("button", { name: "复制 ImageGen 任务" })).toBeEnabled();
      expect(postReleaseRefreshes).toEqual([]);
    } finally {
      release?.();
      await page.unroute(`**/api/v2/projects/${firstProjectId}/art-reference-proposals/${prepared.proposal.id}/copy`, heldRoute);
    }
  });

  test("F4 accepts the three-section script, preserves a scoped edit, and survives backend restart", async ({ page, request, workbench }) => {
    test.setTimeout(75_000);
    const projectId = await createAcceptedArtProject(request, workbench.apiOrigin, "f4-script");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
    const panel = page.getByTestId("script-review");
    const preparedResponse = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/script/candidates`);
    await panel.getByRole("button", { name: "准备并复制 script specialist handoff" }).click();
    const prepared = await (await preparedResponse).json() as ScriptPreparation;
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
    await writeStageDelivery(prepared, "script.json", scriptFixture(), "f4-script", "script");
    const refreshed = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/script/candidates/${prepared.jobId}/refresh`);
    await panel.getByRole("button", { name: "刷新 specialist delivery" }).click();
    expect((await refreshed).ok()).toBeTruthy();
    await panel.getByRole("button", { name: "显式接受完整 pilot 剧本" }).click();
    await expect(panel).toContainText("已接受 r1");
    await panel.getByRole("button", { name: "重新打开剧本" }).click();
    await panel.getByRole("combobox").selectOption("opening");
    const editor = panel.locator("textarea.source-outline-json");
    const opening = JSON.parse(await editor.inputValue()) as Record<string, unknown>;
    await editor.fill(JSON.stringify({ ...opening, cliff: "Edited opening leaves its own consequence." }, null, 2));
    await panel.getByRole("button", { name: "保存此章节，不覆盖其他章节" }).click();
    await expect(panel).toContainText("已接受 r2");
    await workbench.restartBackend(); await page.reload();
    await expect(panel).toContainText("已接受 r2");
    const accepted = await getJson<any>(request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/script`));
    expect(accepted.acceptedScript.script.episodes[2].ep).toBe(3);
  });
});

async function createAcceptedCastProject(request: Api, apiOrigin: string, label: string): Promise<string> {
  const created = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `f3a-art-${label}-${Date.now()}` },
    data: { brief: { ...demoProject.brief, title: `F3A browser ${label}` } },
  });
  const projectId = (await getJson<{ id: string }>(created)).id;
  const source = await getJson<any>(request.put(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/source`, {
    data: { expectedSourceRevision: 0, material: sourceMaterial(label) },
  }));
  const outline = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/candidates`));
  await writeStageDelivery(outline, "outline.json", { source: "F3A browser fixture", summary: "A bounded beacon choice.", sections: ["opening", "beacon", "dock"] }, "f3a-outline", "outline");
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/candidates/${outline.jobId}/refresh`));
  const acceptedOutline = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/accept`, { data: { jobId: outline.jobId, expectedSourceRevision: source.source.revision, expectedOutlineRevision: 0 } }));
  const map = await getJson<any>(request.put(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/section-map`, {
    data: { expectedSectionMapRevision: 0, expectedSourceRevision: acceptedOutline.source.revision, expectedOutlineRevision: acceptedOutline.acceptedOutline.revision, expectedOutlineContentHash: acceptedOutline.acceptedOutline.contentHash, mapping: sectionMap() },
  }));
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/section-map/install-graph`, {
    data: { expectedSourceRevision: map.source.revision, expectedSourceContentHash: map.source.contentHash, expectedOutlineRevision: map.acceptedOutline.revision, expectedOutlineContentHash: map.acceptedOutline.contentHash, expectedSectionMapRevision: map.acceptedSectionMap.revision, expectedSectionMapContentHash: map.acceptedSectionMap.contentHash, expectedGraphRevision: 0 },
  }));
  const cast = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/cast/candidates`));
  await writeStageDelivery(cast, "cast.json", castFixture(), "f3a-cast", "characters");
  const readyCast = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/cast/candidates/${cast.jobId}/refresh`));
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/cast/accept`, {
    data: { jobId: cast.jobId, expectedCastRevision: cast.expectedCastRevision, binding: cast.binding, cast: readyCast.cast, consumerMappings: readyCast.cast.characters.map((character: { id: string }) => ({ castCharacterId: character.id, consumerCharacterId: character.id })) },
  }));
  return projectId;
}

async function createAcceptedArtProject(request: Api, apiOrigin: string, label: string): Promise<string> {
  const projectId = await createAcceptedCastProject(request, apiOrigin, label);
  const prepared = await getJson<ArtPreparation>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/art/candidates`));
  await writeArtDelivery(prepared, `f3b-art-${label}`);
  const ready = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/art/candidates/${prepared.jobId}/refresh`));
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/art/accept`, {
    data: { jobId: prepared.jobId, expectedArtRevision: prepared.expectedArtRevision, binding: prepared.binding, art: ready.art },
  }));
  return projectId;
}

async function writeArtReferenceDelivery(response: import("@playwright/test").Response): Promise<void> {
  expect(response.ok(), await response.text()).toBeTruthy();
  const copied = await response.json() as { proposal: { id: string; requestHash: string }; packagePath: string; deliveryPath: string };
  const request = JSON.parse(await readFile(path.join(copied.packagePath, "request.json"), "utf8"));
  const content = fixturePng();
  const provenance = { codeRevision: "a".repeat(40), skillVersion: "plotloom-image-specialist.v3", skillHash: "b".repeat(64) };
  await mkdir(path.join(copied.deliveryPath, "outputs"), { recursive: true });
  await writeFile(path.join(copied.deliveryPath, "outputs", "study.png"), content);
  await writeFile(path.join(copied.deliveryPath, "executor-pin.json"), JSON.stringify({ jobId: copied.proposal.id, requestHash: request.requestHash, executionContract: "codex_specialist.v2", ...provenance }));
  await writeFile(path.join(copied.deliveryPath, "completion.json"), JSON.stringify({
    schemaVersion: 2, jobId: copied.proposal.id, requestHash: request.requestHash, deliveryId: "f3b-browser-study",
    actualPrompt: "Cinematic realism beacon room reference study, no people and no hands.",
    outputs: [{ filename: "study.png", sha256: hash(content), role: "art_reference" }],
    toolEvidence: { tool: "codex_imagegen", taskId: "f3b-browser-fixture", available: true }, executorProvenance: provenance,
    limitations: ["Browser fixture; no creative approval."],
  }));
}

async function prepareFromBrowser(page: import("@playwright/test").Page, panel: import("@playwright/test").Locator, projectId: string): Promise<ArtPreparation> {
  const prepared = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art/candidates`);
  await panel.getByRole("button", { name: "准备并复制 art specialist handoff" }).click();
  const response = await prepared;
  expect(response.status()).toBe(201);
  return response.json() as Promise<ArtPreparation>;
}

async function refreshFromBrowser(page: import("@playwright/test").Page, panel: import("@playwright/test").Locator, projectId: string, jobId: string): Promise<void> {
  const refreshed = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art/candidates/${jobId}/refresh`);
  await panel.getByRole("button", { name: "刷新 specialist delivery" }).click();
  expect((await refreshed).ok()).toBeTruthy();
}

async function writeArtDelivery(prepared: ArtPreparation, deliveryId: string): Promise<void> {
  const request = JSON.parse(await readFile(path.join(prepared.packagePath, "request.json"), "utf8"));
  const art = Buffer.from(JSON.stringify(artFixture()));
  const report = Buffer.from("<!doctype html><html><body><p>original specialist candidate</p></body></html>");
  await mkdir(prepared.deliveryPath, { recursive: true });
  await writeFile(path.join(prepared.deliveryPath, "art.json"), art);
  await writeFile(path.join(prepared.deliveryPath, "report.html"), report);
  await writeFile(path.join(prepared.deliveryPath, "completion.json"), JSON.stringify({
    schemaVersion: 1, jobId: prepared.jobId, requestHash: request.requestHash, deliveryId, stage: "art",
    candidate: { filename: "art.json", sha256: hash(art) }, report: { filename: "report.html", sha256: hash(report) },
    executorProvenance: { codeRevision: "abcdef0", skillVersion: "fixture", skillHash: request.executionPin.specialistSkillHash, upstreamRevision: request.executionPin.upstreamRevision, upstreamSkillHash: request.executionPin.upstreamSkillHash, model: "fixture", reasoningEffort: "high" },
    limitations: ["F3A production browser fixture; no creative approval or media."],
  }));
}

async function writeStageDelivery(prepared: any, filename: string, candidate: Record<string, unknown>, deliveryId: string, stage: string): Promise<void> {
  const request = JSON.parse(await readFile(path.join(prepared.packagePath, "request.json"), "utf8"));
  const content = Buffer.from(JSON.stringify(candidate));
  const report = Buffer.from("<!doctype html><html><body>fixture report</body></html>");
  await mkdir(prepared.deliveryPath, { recursive: true });
  await writeFile(path.join(prepared.deliveryPath, filename), content);
  await writeFile(path.join(prepared.deliveryPath, "report.html"), report);
  await writeFile(path.join(prepared.deliveryPath, "completion.json"), JSON.stringify({
    schemaVersion: 1, jobId: prepared.jobId, requestHash: request.requestHash, deliveryId, stage,
    candidate: { filename, sha256: hash(content) }, report: { filename: "report.html", sha256: hash(report) },
    executorProvenance: { codeRevision: "abcdef0", skillVersion: "fixture", skillHash: request.executionPin.specialistSkillHash, upstreamRevision: request.executionPin.upstreamRevision, upstreamSkillHash: request.executionPin.upstreamSkillHash, model: "fixture", reasoningEffort: "high" }, limitations: ["Fixture only."],
  }));
}

function sourceMaterial(label: string) { return { kind: "synopsis", title: `Beacon choice ${label}`, text: "A keeper must power the beacon or dock before the storm closes the channel.", attribution: "F3A production-browser fixture", rightsDeclaration: "Test fixture only; not a rights determination.", adaptationIntent: "Preserve one choice and two explicit endings." }; }
function sectionMap() { return { sections: [{ sectionId: "opening", title: "Storm warning", summary: "The keeper has one cable and two destinations.", ending: false }, { sectionId: "beacon", title: "Beacon lit", summary: "The beacon guides sailors through the storm.", ending: true }, { sectionId: "dock", title: "Dock lit", summary: "The dock welcomes boats while the beacon goes dark.", ending: true }], choice: { choiceId: "power-choice", sectionId: "opening", prompt: "Where should the keeper send the cable?", outcomes: [{ outcomeId: "beacon-path", label: "Light the beacon", consequence: "The dock loses power.", endingSectionId: "beacon" }, { outcomeId: "dock-path", label: "Light the dock", consequence: "The beacon goes dark.", endingSectionId: "dock" }] } }; }
function castFixture() { return { source: "F3A browser fixture", summary: "One beacon keeper.", characters: [{ id: "keeper", name: "Mira", persona: { motivation: "Guide sailors home", appearance: "Rain-dark hair and a weathered beacon coat", arc: "Chooses who to protect" }, voice: { timbre: "Steady under pressure" } }] }; }
function artFixture() { const render = "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth"; return { source: "F3A browser fixture", style: "realistic", scenes: [{ id: "S01", name: "Beacon room", primary: true, summary: "The keeper faces a power choice.", anchors: [{ name: "brass lamp", desc: "old brass" }, { name: "window", desc: "salted glass" }, { name: "desk", desc: "worn wood" }], lighting: [{ state: "dawn", prompt: "cold dawn through a window" }], image: { prompt: "empty beacon room", negativePrompt: "people, human figures", sheet: render, tags: [] } }], props: [], sectionUsage: [{ sectionId: "opening", sceneIds: ["S01"], propIds: [] }, { sectionId: "beacon", sceneIds: ["S01"], propIds: [] }, { sectionId: "dock", sceneIds: ["S01"], propIds: [] }] }; }
function scriptFixture() { const episode = (ep: number) => ({ ep, targetSeconds: 60, hook: `Section ${ep} begins in motion`, cliff: `Section ${ep} leaves a choice open`, hookBeat: [1, 1], beatsClaimed: [], scenes: [{ sceneId: "S01", lighting: "dawn", characters: [], props: [], flow: Array.from({ length: 24 }, (_, index) => ({ action: `Mira crosses the beacon room, action ${index}.` })) }] }); return { source: "F3A browser fixture", sectionBindings: [{ sectionId: "opening", episode: 1 }, { sectionId: "beacon", episode: 2 }, { sectionId: "dock", episode: 3 }], episodes: [episode(1), episode(2), episode(3)] }; }
function withSummary(art: Record<string, unknown>, summary: string): Record<string, unknown> { return { ...art, scenes: (art.scenes as Array<Record<string, unknown>>).map((scene, index) => index === 0 ? { ...scene, summary } : scene) }; }

async function expectOnlySourceMapGraph(request: Api, apiOrigin: string, projectId: string): Promise<void> {
  const stages = await getJson<{ stages: Array<{ head: { stage: string; revision: number }; payload: unknown }> }>(request.get(`${apiOrigin}/api/v2/projects/${projectId}/stages`));
  expect(stages.stages.filter((stage) => stage.payload).map((stage) => stage.head.stage)).toEqual(["story_graph"]);
  expect(stages.stages.filter((stage) => stage.head.stage !== "story_graph").every((stage) => stage.head.revision === 0)).toBeTruthy();
}

async function switchProject(page: import("@playwright/test").Page, projectId: string): Promise<void> {
  await page.getByRole("button", { name: /当前项目 · 切换/ }).click();
  const directory = page.getByRole("dialog", { name: "项目目录" });
  await directory.locator(`[data-project-id="${projectId}"] .directory-open`).click();
  await expect(directory).toBeHidden();
  await expect(page).toHaveURL(new RegExp(`project=${projectId}`));
}

async function getJson<T>(responseOrPromise: Awaited<ReturnType<Api["get"]>> | Promise<Awaited<ReturnType<Api["get"]>>>): Promise<T> {
  const response = await responseOrPromise;
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json() as Promise<T>;
}

function hash(value: Buffer): string { return createHash("sha256").update(value).digest("hex"); }

function fixturePng(): Buffer {
  const width = 32, height = 24;
  const rows = Buffer.alloc((width * 3 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    const offset = y * (width * 3 + 1);
    for (let x = 0; x < width; x += 1) rows.set([42 + x, 72 + y, 84], offset + 1 + x * 3);
  }
  const chunk = (type: string, value: Buffer) => {
    const name = Buffer.from(type);
    const length = Buffer.alloc(4); length.writeUInt32BE(value.length);
    const checksum = Buffer.alloc(4); checksum.writeUInt32BE(crc32(Buffer.concat([name, value])));
    return Buffer.concat([length, name, value, checksum]);
  };
  const header = Buffer.alloc(13); header.writeUInt32BE(width, 0); header.writeUInt32BE(height, 4); header.set([8, 2, 0, 0, 0], 8);
  return Buffer.concat([Buffer.from("89504e470d0a1a0a", "hex"), chunk("IHDR", header), chunk("IDAT", deflateSync(rows)), chunk("IEND", Buffer.alloc(0))]);
}

function crc32(value: Buffer): number {
  let crc = 0xffffffff;
  for (const byte of value) { crc ^= byte; for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1)); }
  return (crc ^ 0xffffffff) >>> 0;
}
