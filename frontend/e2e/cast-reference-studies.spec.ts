import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { demoProject } from "../src/demo";
import { expect, test } from "./fixture";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const retainedStill = path.join(repositoryRoot, "docs/verification/supporting/p0-generated/01-arrival.png");

type Api = import("@playwright/test").APIRequestContext;
type PackagePaths = { packagePath: string; deliveryPath: string };
type Proposal = {
  id: string;
  requestHash: string;
  parentCandidateAssetId: string | null;
  state: string;
  current: boolean;
  deliveries: Array<{ state: string; candidates: Array<{ id: string; assetId: string }> }>;
};

test.describe("F2B cast-owned reference studies", () => {
  test("synchronizes browser cast accept, reopen, and save with the same character-reference session", async ({ page, request, workbench }) => {
    const { projectId } = await createCastReadyProject(request, workbench.apiOrigin, "session-sync");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const cast = page.getByTestId("cast-review");
    await expect(cast.getByRole("button", { name: "显式接受此角色提案" })).toBeEnabled();

    const accepting = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/cast/accept`);
    await cast.getByRole("button", { name: "显式接受此角色提案" }).click();
    expect((await accepting).ok()).toBeTruthy();
    const gallery = page.getByTestId("character-reference-gallery");
    await expect(gallery).toContainText("已接受角色 r1");
    await expect(gallery.getByLabel("细化方向")).toBeEditable();

    const reopening = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/cast/reopen`);
    await cast.getByRole("button", { name: "重新打开角色提案" }).click();
    expect((await reopening).ok()).toBeTruthy();
    await expect(gallery).toContainText("已接受角色已过期");
    await expect(gallery.getByLabel("细化方向")).toBeDisabled();

    const saving = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/cast/save`);
    await cast.getByRole("button", { name: "保存重新打开的角色" }).click();
    expect((await saving).ok()).toBeTruthy();
    await expect(gallery).toContainText("已接受角色 r2");
    await expect(gallery.getByLabel("细化方向")).toBeEditable();
    await expect(gallery.getByLabel("细化方向")).toHaveValue("");
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);
  });

  test("uses a cast-only production fixture through original, refinement, and restart", async ({ page, request, workbench }, testInfo) => {
    test.setTimeout(75_000);
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "journey");
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);

    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const panel = page.getByTestId("character-reference-gallery");
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("不会自动调用 ImageGen");
    // U3 admits this cast-only project before it has any reference image. It
    // must not reach for a Bible, screenplay, or storyboard to fill the gap.
    const emptyGallery = page.getByTestId("character-reference-gallery");
    await expect(emptyGallery).toContainText("尚未选择身份参考");
    await expect(emptyGallery.getByTestId("reference-no-image")).toBeVisible();
    await panel.getByLabel("审阅者").fill("F2B browser fixture reviewer");
    await panel.getByLabel("选择说明").fill("Retained test-only raster fixture; this is a technical regression selection.");
    await panel.getByLabel("细化方向").fill("Three-quarter study at the storm beacon window.");
    const original = await prepareProposalFromBrowser(page, panel, projectId, request, workbench.apiOrigin);
    const originalPackage = await copyProposalFromBrowser(page, projectId, original.id);
    await writeProposalDelivery(originalPackage.deliveryPath, original, "f2b-original-browser", "original");
    await refreshProposalFromBrowser(page, projectId, original.id);
    const deliveredOriginal = await proposal(request, workbench.apiOrigin, projectId, original.id);
    const originalCandidate = deliveredOriginal.deliveries[0]!.candidates[0]!.assetId;
    const originalCandidateId = deliveredOriginal.deliveries[0]!.candidates[0]!.id;
    await panel.getByRole("button", { name: "选择身份参考" }).click();
    await expect(panel).toContainText("已选择身份参考 r1");

    await panel.getByRole("button", { name: "用作细化父图" }).click();
    await expect(panel.getByLabel("细化父图")).toHaveValue(originalCandidate);
    await panel.getByLabel("细化方向").fill("Keep the parent identity and clarify the rain-lit eyebrow anchor.");
    const refinement = await prepareProposalFromBrowser(page, panel, projectId, request, workbench.apiOrigin);
    expect(refinement.parentCandidateAssetId).toBe(originalCandidate);
    const refinementPackage = await copyProposalFromBrowser(page, projectId, refinement.id);
    await writeProposalDelivery(refinementPackage.deliveryPath, refinement, "f2b-refinement-browser", "refinement");
    await refreshProposalFromBrowser(page, projectId, refinement.id);
    await panel.getByLabel("选择说明").fill("Refinement fixture selected after explicit review.");
    await panel.getByRole("button", { name: "选择身份参考" }).last().click();
    await expect(panel).toContainText("已选择身份参考 r2");

    await page.reload();
    await expect(panel).toContainText("已选择身份参考 r2");
    await workbench.restartBackend();
    await page.reload();
    await expect(panel).toContainText("已选择身份参考 r2");
    const deliveredRefinement = await proposal(request, workbench.apiOrigin, projectId, refinement.id);
    const refinementCandidate = deliveredRefinement.deliveries[0]!.candidates[0]!.assetId;
    const viewingMethods: string[] = [];
    const recordGalleryRequest = (browserRequest: import("@playwright/test").Request) => {
      if (new URL(browserRequest.url()).pathname.includes(`/api/v2/projects/${projectId}/`)) viewingMethods.push(browserRequest.method());
    };
    page.on("request", recordGalleryRequest);
    try {
      await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
      const gallery = page.getByTestId("character-reference-gallery");
      await expect(gallery).toContainText("为未来镜头建立这个角色的外观");
      await expect(gallery.getByText("当前已选择的身份参考", { exact: true })).toBeVisible();
      await expect(gallery.getByRole("img").first()).toBeVisible();
      const selectedCard = gallery.getByTestId(`reference-candidate-${originalCandidate}`);
      await expect(selectedCard).toContainText("当前已选择");
      await selectedCard.getByText("查看生成说明", { exact: true }).click();
      await expect(selectedCard).toContainText("Three-quarter study at the storm beacon window.");
      await expect(gallery.getByText("来源父图", { exact: true })).toBeVisible();
      const parentLink = gallery.getByRole("link", { name: "原始候选" });
      await expect(parentLink).toBeVisible();
      await parentLink.click();
      await expect(page).toHaveURL(new RegExp(`#reference-candidate-${originalCandidateId}$`));
      await expect(page.locator(`#reference-candidate-${originalCandidateId}`)).toBeFocused();
      await selectedCard.getByText("技术详情", { exact: true }).click();
      await expect(selectedCard).toContainText("请求标识");
      await expect(selectedCard).toContainText("来源");
      await page.screenshot({ path: testInfo.outputPath("u3-character-reference-gallery-1440x900.png"), animations: "disabled" });
      await page.setViewportSize({ width: 768, height: 900 });
      await expect(gallery.getByRole("img").first()).toBeVisible();
      await page.screenshot({ path: testInfo.outputPath("u3-character-reference-gallery-768x900.png"), animations: "disabled" });
    } finally {
      page.off("request", recordGalleryRequest);
    }
    expect(viewingMethods).not.toHaveLength(0);
    expect(viewingMethods.every((method) => method === "GET")).toBeTruthy();

    // A current selection remains the hero if its bytes cannot load. The
    // other delivered candidate is still an explicit alternative, never a
    // silent replacement for that selection.
    await page.route(`**/api/v2/projects/${projectId}/managed-assets/${originalCandidate}/display`, async (route) => {
      await route.fulfill({ status: 503, contentType: "text/plain", body: "fixture image intentionally unavailable" });
    });
    try {
      await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
      const selectedHero = page.getByTestId("reference-selected-hero");
      await expect(selectedHero).toContainText("当前已选择的身份参考图像不可用");
      await expect(selectedHero.getByTestId(`reference-image-unavailable-${originalCandidate}`)).toBeVisible();
      await expect(page.getByTestId(`reference-candidate-${refinementCandidate}`).getByRole("img")).toBeVisible();
    } finally {
      await page.unroute(`**/api/v2/projects/${projectId}/managed-assets/${originalCandidate}/display`);
    }
    const sourceState = await getJson<any>(request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline`));
    await getJson(request.put(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline/source`, {
      data: { expectedSourceRevision: sourceState.source.revision, material: { ...sourceState.source.material, text: "A U3 stale-selection presentation check." } },
    }));
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    await expect(page.getByTestId("character-reference-gallery")).toContainText("已接受角色已过期");
    await expect(page.getByText("历史选择，当前不可用", { exact: true }).first()).toBeVisible();
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);
  });

  test("cancels prepared and exported handoffs, retaining late delivery as inapplicable across close/reopen", async ({ page, request, workbench }) => {
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "cancel");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const panel = page.getByTestId("character-reference-gallery");
    await expect(panel).toBeVisible();

    await panel.getByLabel("细化方向").fill("Prepared study cancelled before any copy.");
    await prepareProposalFromBrowser(page, panel, projectId, request, workbench.apiOrigin);
    await panel.getByRole("button", { name: "取消 handoff" }).click();
    await expect(panel).toContainText("已取消，未交付");

    await panel.getByLabel("细化方向").fill("Exported study whose late package must not publish.");
    const exported = await prepareProposalFromBrowser(page, panel, projectId, request, workbench.apiOrigin);
    const exportedPackage = await copyProposalFromBrowser(page, projectId, exported.id);
    await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, exported.id)).state).toBe("exported");
    await panel.getByRole("button", { name: "取消 handoff" }).first().click();
    await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, exported.id)).state).toBe("cancelled");
    await writeProposalDelivery(exportedPackage.deliveryPath, exported, "f2b-cancelled-late", "original");
    await getJson(request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-reference-proposals/${exported.id}/refresh`));
    const late = await proposal(request, workbench.apiOrigin, projectId, exported.id);
    expect(late.current).toBeFalsy();
    expect(late.deliveries).toMatchObject([{ state: "inapplicable", candidates: [] }]);
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);

    const closed = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/close`);
    expect(closed.ok(), await closed.text()).toBeTruthy();
    await workbench.restartBackend();
    const opened = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/open`);
    expect(opened.ok(), await opened.text()).toBeTruthy();
    await page.reload();
    await expect(panel).toContainText("已取消，未交付");
    await expect(page.getByTestId("character-reference-gallery")).toContainText("已过期 / 不适用交付");
    await expect(page.getByTestId("character-reference-gallery")).toContainText("已取消，未交付");
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);
  });

  test("marks stale cast context and contains held preparation to its original project session", async ({ page, request, workbench }) => {
    const staleProjectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "stale");
    const staleSource = await getJson<any>(request.get(`${workbench.apiOrigin}/api/v2/projects/${staleProjectId}/source-outline`));
    const changed = await request.put(`${workbench.apiOrigin}/api/v2/projects/${staleProjectId}/source-outline/source`, {
      data: {
        expectedSourceRevision: staleSource.source.revision,
        material: { ...staleSource.source.material, text: "A revised source makes the accepted cast stale." },
      },
    });
    expect(changed.ok(), await changed.text()).toBeTruthy();
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${staleProjectId}&stage=characters`);
    await expect(page.getByTestId("cast-review")).toContainText("上下文已过期");
    await expect(page.getByTestId("character-reference-gallery")).toContainText("重新接受角色前不能选择");
    const staleCast = await getJson<any>(request.get(`${workbench.apiOrigin}/api/v2/projects/${staleProjectId}/cast`));
    expect(staleCast.status).toBe("stale");
    await expect(page.getByTestId("character-reference-gallery")).toContainText("已接受角色已过期");

    const firstProjectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "held-first");
    const secondProjectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "held-second");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${firstProjectId}&stage=characters`);
    const firstPanel = page.getByTestId("character-reference-gallery");
    await expect(firstPanel).toBeVisible();
    await firstPanel.getByLabel("细化方向").fill("Held first-project study.");

    let releasePreparation: (() => void) | undefined;
    let signalPreparation: (() => void) | undefined;
    const preparationStarted = new Promise<void>((resolve) => { signalPreparation = resolve; });
    const preparationReleased = new Promise<void>((resolve) => { releasePreparation = resolve; });
    const heldRoute = async (route: import("@playwright/test").Route) => {
      if (route.request().method() !== "POST") return route.continue();
      signalPreparation?.();
      await preparationReleased;
      try {
        await route.continue();
      } catch {
        // Switching through the SPA can abort the old request after its
        // operation has already captured busy ownership.
      }
    };
    await page.route(`**/api/v2/projects/${firstProjectId}/character-reference-proposals`, heldRoute);
    try {
      await firstPanel.getByRole("button", { name: "准备手动细化 handoff" }).click();
      await preparationStarted;
      await switchProjectInDirectory(page, secondProjectId);
      await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /^02 角色/ }).click();
      const secondPanel = page.getByTestId("character-reference-gallery");
      const secondDirection = secondPanel.getByLabel("细化方向");
      await expect(secondDirection).toBeEditable();
      await secondDirection.fill("Second-project direction must survive the first request.");
      releasePreparation?.();
      await expect(secondDirection).toHaveValue("Second-project direction must survive the first request.");
    } finally {
      releasePreparation?.();
      await page.unroute(`**/api/v2/projects/${firstProjectId}/character-reference-proposals`, heldRoute);
    }
  });

  test("invalidates held gallery reads after a project change", async ({ page, request, workbench }) => {
    const firstProjectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "gallery-held-first");
    const secondProjectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "gallery-held-second");
    let release: (() => void) | undefined;
    let signal: (() => void) | undefined;
    const started = new Promise<void>((resolve) => { signal = resolve; });
    const released = new Promise<void>((resolve) => { release = resolve; });
    const heldProject = async (route: import("@playwright/test").Route) => {
      signal?.();
      await released;
      try {
        await route.continue();
      } catch {
        // The gallery's cleanup aborts the old project read after navigation.
      }
    };
    await page.route(`**/api/v2/projects/${firstProjectId}`, heldProject);
    try {
      await page.goto(`${workbench.frontendOrigin}/v2/?project=${firstProjectId}&stage=characters`);
      await started;
      await page.goto(`${workbench.frontendOrigin}/v2/?project=${secondProjectId}&stage=characters`);
      await expect(page.getByTestId("character-reference-gallery")).toContainText("F2B cast-only gallery-held-second");
      release?.();
      await expect(page.getByTestId("character-reference-gallery")).toContainText("F2B cast-only gallery-held-second");
      await expect(page.getByTestId("character-reference-gallery")).not.toContainText("gallery-held-first");
    } finally {
      release?.();
      await page.unroute(`**/api/v2/projects/${firstProjectId}`, heldProject);
    }
  });
});

async function createAcceptedCastOnlyProject(request: Api, apiOrigin: string, label: string): Promise<string> {
  const ready = await createCastReadyProject(request, apiOrigin, label);
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${ready.projectId}/cast/accept`, {
    data: {
      jobId: ready.castPrepared.jobId,
      expectedCastRevision: ready.castPrepared.expectedCastRevision,
      binding: ready.castPrepared.binding,
      cast: ready.readyCast.cast,
      consumerMappings: ready.readyCast.cast.characters.map((character: { id: string }) => ({ castCharacterId: character.id, consumerCharacterId: character.id })),
    },
  }));
  return ready.projectId;
}

async function createCastReadyProject(request: Api, apiOrigin: string, label: string): Promise<{ projectId: string; castPrepared: any; readyCast: any }> {
  const created = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `f2b-cast-only-${label}-${Date.now()}` },
    data: { brief: { ...demoProject.brief, title: `F2B cast-only ${label}` } },
  });
  const projectId = (await getJson<{ id: string }>(created)).id;
  const saved = await request.put(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/source`, {
    data: { expectedSourceRevision: 0, material: sourceMaterial(label) },
  });
  const sourceState = await getJson<any>(saved);
  const outlinePrepared = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/candidates`));
  await writeOutlineDelivery(outlinePrepared);
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/candidates/${outlinePrepared.jobId}/refresh`));
  const acceptedOutline = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/accept`, {
    data: { jobId: outlinePrepared.jobId, expectedSourceRevision: sourceState.source.revision, expectedOutlineRevision: 0 },
  }));
  const mapSaved = await getJson<any>(request.put(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/section-map`, {
    data: {
      expectedSectionMapRevision: 0,
      expectedSourceRevision: acceptedOutline.source.revision,
      expectedOutlineRevision: acceptedOutline.acceptedOutline.revision,
      expectedOutlineContentHash: acceptedOutline.acceptedOutline.contentHash,
      mapping: sectionMap(),
    },
  }));
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/section-map/install-graph`, {
    data: {
      expectedSourceRevision: mapSaved.source.revision,
      expectedSourceContentHash: mapSaved.source.contentHash,
      expectedOutlineRevision: mapSaved.acceptedOutline.revision,
      expectedOutlineContentHash: mapSaved.acceptedOutline.contentHash,
      expectedSectionMapRevision: mapSaved.acceptedSectionMap.revision,
      expectedSectionMapContentHash: mapSaved.acceptedSectionMap.contentHash,
      expectedGraphRevision: 0,
    },
  }));
  const castPrepared = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/cast/candidates`));
  await writeCastDelivery(castPrepared);
  const readyCast = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/cast/candidates/${castPrepared.jobId}/refresh`));
  return { projectId, castPrepared, readyCast };
}

function sourceMaterial(label: string) {
  return {
    kind: "synopsis",
    title: `Beacon choice ${label}`,
    text: "A keeper must power the beacon or the dock before the storm closes the channel.",
    attribution: "F2B production-browser fixture author",
    rightsDeclaration: "Test fixture only; not a rights determination.",
    adaptationIntent: "Preserve one choice and two explicit endings.",
  };
}

function sectionMap() {
  return {
    sections: [
      { sectionId: "opening", title: "Storm warning", summary: "The keeper has one cable and two destinations.", ending: false },
      { sectionId: "beacon", title: "Beacon lit", summary: "The beacon guides the sailors through the storm.", ending: true },
      { sectionId: "dock", title: "Dock lit", summary: "The dock welcomes the boats while the beacon goes dark.", ending: true },
    ],
    choice: {
      choiceId: "power-choice",
      sectionId: "opening",
      prompt: "Where should the keeper send the cable?",
      outcomes: [
        { outcomeId: "beacon-path", label: "Light the beacon", consequence: "The dock loses power.", endingSectionId: "beacon" },
        { outcomeId: "dock-path", label: "Light the dock", consequence: "The beacon goes dark.", endingSectionId: "dock" },
      ],
    },
  };
}

async function writeOutlineDelivery(prepared: any): Promise<void> {
  const request = JSON.parse(await readFile(path.join(prepared.packagePath, "request.json"), "utf8"));
  const outline = Buffer.from(JSON.stringify({ source: "F2B browser fixture", summary: "A bounded beacon choice.", sections: ["opening", "beacon", "dock"] }));
  const report = Buffer.from("<!doctype html><title>F2B fixture</title><p>Candidate only.</p>");
  await mkdir(prepared.deliveryPath, { recursive: true });
  await writeFile(path.join(prepared.deliveryPath, "outline.json"), outline);
  await writeFile(path.join(prepared.deliveryPath, "report.html"), report);
  await writeFile(path.join(prepared.deliveryPath, "completion.json"), JSON.stringify({
    schemaVersion: 1, jobId: prepared.jobId, requestHash: request.requestHash, deliveryId: "f2b-outline-fixture", stage: "outline",
    candidate: { filename: "outline.json", sha256: hash(outline) }, report: { filename: "report.html", sha256: hash(report) },
    executorProvenance: { codeRevision: "abcdef0", skillVersion: "fixture", skillHash: request.executionPin.specialistSkillHash, upstreamRevision: request.executionPin.upstreamRevision, upstreamSkillHash: request.executionPin.upstreamSkillHash, model: "fixture", reasoningEffort: "high" },
    limitations: ["F2B fixture; no creative approval."],
  }));
}

async function writeCastDelivery(prepared: any): Promise<void> {
  const request = JSON.parse(await readFile(path.join(prepared.packagePath, "request.json"), "utf8"));
  const cast = Buffer.from(JSON.stringify({ source: "F2B browser fixture", summary: "One beacon keeper requires an identity reference.", characters: [{ id: "keeper", name: "Mira", persona: { motivation: "Guide sailors home", appearance: "Rain-dark hair and a weathered beacon coat", arc: "Chooses who to protect" }, voice: { timbre: "Steady under pressure" } }] }));
  const report = Buffer.from("<!doctype html><title>F2B cast fixture</title><p>Candidate only.</p>");
  await mkdir(prepared.deliveryPath, { recursive: true });
  await writeFile(path.join(prepared.deliveryPath, "cast.json"), cast);
  await writeFile(path.join(prepared.deliveryPath, "report.html"), report);
  await writeFile(path.join(prepared.deliveryPath, "completion.json"), JSON.stringify({
    schemaVersion: 1, jobId: prepared.jobId, requestHash: request.requestHash, deliveryId: "f2b-cast-fixture", stage: "characters",
    candidate: { filename: "cast.json", sha256: hash(cast) }, report: { filename: "report.html", sha256: hash(report) },
    executorProvenance: { codeRevision: "abcdef0", skillVersion: "fixture", skillHash: request.executionPin.specialistSkillHash, upstreamRevision: request.executionPin.upstreamRevision, upstreamSkillHash: request.executionPin.upstreamSkillHash, model: "fixture", reasoningEffort: "high" },
    limitations: ["F2B fixture; no creative approval."],
  }));
}

async function copyProposalFromBrowser(page: import("@playwright/test").Page, projectId: string, proposalId: string): Promise<PackagePaths> {
  const proposalCard = page.locator(`[data-proposal-id="${proposalId}"]`);
  await expect(proposalCard.getByRole("button", { name: "复制 handoff" })).toBeEnabled();
  const copied = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/character-reference-proposals/${proposalId}/copy`);
  await proposalCard.getByRole("button", { name: "复制 handoff" }).click();
  const response = await copied;
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json() as Promise<PackagePaths>;
}

async function prepareProposalFromBrowser(
  page: import("@playwright/test").Page,
  panel: import("@playwright/test").Locator,
  projectId: string,
  request: Api,
  apiOrigin: string,
): Promise<Proposal> {
  const prepared = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/character-reference-proposals`);
  await panel.getByRole("button", { name: "准备手动细化 handoff" }).click();
  expect((await prepared).status()).toBe(201);
  const latest = await latestProposal(request, apiOrigin, projectId);
  await expect(panel.locator(`[data-proposal-id="${latest.id}"]`).getByRole("button", { name: "复制 handoff" })).toBeEnabled();
  return latest;
}

async function refreshProposalFromBrowser(page: import("@playwright/test").Page, projectId: string, proposalId: string): Promise<void> {
  const refreshed = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/character-reference-proposals/${proposalId}/refresh`);
  await page.locator(`[data-proposal-id="${proposalId}"]`).getByRole("button", { name: "刷新交付" }).click();
  expect((await refreshed).ok()).toBeTruthy();
}

async function latestProposal(request: Api, apiOrigin: string, projectId: string): Promise<Proposal> {
  const proposals = await getJson<{ proposals: Proposal[] }>(request.get(`${apiOrigin}/api/v2/projects/${projectId}/character-reference-proposals`));
  expect(proposals.proposals.length).toBeGreaterThan(0);
  return proposals.proposals[0]!;
}

async function proposal(request: Api, apiOrigin: string, projectId: string, proposalId: string): Promise<Proposal> {
  const proposals = await getJson<{ proposals: Proposal[] }>(request.get(`${apiOrigin}/api/v2/projects/${projectId}/character-reference-proposals`));
  const found = proposals.proposals.find((item) => item.id === proposalId);
  expect(found).toBeDefined();
  return found!;
}

async function writeProposalDelivery(deliveryPath: string, proposal: Proposal, deliveryId: string, role: "original" | "refinement"): Promise<void> {
  const content = await readFile(retainedStill);
  await mkdir(path.join(deliveryPath, "outputs"), { recursive: true });
  await writeFile(path.join(deliveryPath, "outputs", "candidate.png"), content);
  const provenance = { codeRevision: "a".repeat(40), skillVersion: "plotloom-image-specialist.v3", skillHash: "b".repeat(64) };
  await writeFile(path.join(deliveryPath, "executor-pin.json"), JSON.stringify({ jobId: proposal.id, requestHash: proposal.requestHash, executionContract: "codex_specialist.v2", ...provenance }));
  await writeFile(path.join(deliveryPath, "completion.json"), JSON.stringify({
    schemaVersion: 2, jobId: proposal.id, requestHash: proposal.requestHash, deliveryId,
    actualPrompt: "Retained P0 image fixture for F2B browser regression; no ImageGen call was made.",
    outputs: [{ filename: "candidate.png", sha256: hash(content), role }],
    toolEvidence: { tool: "codex_imagegen", taskId: "f2b-retained-fixture", available: true },
    executorProvenance: provenance,
    limitations: ["Retained test-only raster fixture; no image was generated."],
  }));
}

async function expectOnlySourceMapGraph(request: Api, apiOrigin: string, projectId: string): Promise<void> {
  const stages = await getJson<{ stages: Array<{ head: { stage: string; revision: number }; payload: unknown }> }>(request.get(`${apiOrigin}/api/v2/projects/${projectId}/stages`));
  expect(stages.stages.filter((stage) => stage.payload).map((stage) => stage.head.stage)).toEqual(["story_graph"]);
  expect(stages.stages.filter((stage) => stage.head.stage !== "story_graph").every((stage) => stage.head.revision === 0)).toBeTruthy();
}

async function switchProjectInDirectory(page: import("@playwright/test").Page, projectId: string): Promise<void> {
  await page.getByRole("button", { name: /当前项目 · 切换/ }).click();
  const directory = page.getByRole("dialog", { name: "项目目录" });
  await expect(directory).toBeVisible();
  await directory.locator(`[data-project-id="${projectId}"] .directory-open`).click();
  await expect(directory).toBeHidden();
  await expect(page).toHaveURL(new RegExp(`project=${projectId}`));
}

async function getJson<T>(responseOrPromise: Awaited<ReturnType<Api["get"]>> | Promise<Awaited<ReturnType<Api["get"]>>>): Promise<T> {
  const response = await responseOrPromise;
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json() as Promise<T>;
}

function hash(value: Buffer): string {
  return createHash("sha256").update(value).digest("hex");
}
