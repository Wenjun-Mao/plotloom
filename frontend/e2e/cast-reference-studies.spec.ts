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
  deliveries: Array<{ state: string; candidates: Array<{ assetId: string }> }>;
};

test.describe("F2B cast-owned reference studies", () => {
  test("uses a cast-only production fixture through original, refinement, and restart", async ({ page, request, workbench }) => {
    test.setTimeout(75_000);
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "journey");
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);

    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
    const panel = page.getByTestId("cast-reference-studies");
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("no Story Bible, Shot, Approval");
    await panel.getByLabel("Reference decision reviewer").fill("F2B browser fixture reviewer");
    await panel.getByLabel("Selection notes").fill("Retained test-only raster fixture; this is a technical regression selection.");
    await panel.getByLabel("Pose / composition direction").fill("Three-quarter study at the storm beacon window.");
    const original = await prepareProposalFromBrowser(page, panel, projectId, request, workbench.apiOrigin);
    const originalPackage = await copyProposalFromBrowser(page, projectId, original.id);
    await writeProposalDelivery(originalPackage.deliveryPath, original, "f2b-original-browser", "original");
    await refreshProposalFromBrowser(page, projectId, original.id);
    const deliveredOriginal = await proposal(request, workbench.apiOrigin, projectId, original.id);
    const originalCandidate = deliveredOriginal.deliveries[0]!.candidates[0]!.assetId;
    await panel.getByRole("button", { name: "Select identity reference" }).click();
    await expect(panel.getByTestId("cast-current-reference")).toContainText("current r1");

    await panel.getByRole("button", { name: "Use for refinement" }).click();
    await expect(panel.getByLabel("Refinement parent")).toHaveValue(originalCandidate);
    await panel.getByLabel("Pose / composition direction").fill("Keep the parent identity and clarify the rain-lit eyebrow anchor.");
    const refinement = await prepareProposalFromBrowser(page, panel, projectId, request, workbench.apiOrigin);
    expect(refinement.parentCandidateAssetId).toBe(originalCandidate);
    const refinementPackage = await copyProposalFromBrowser(page, projectId, refinement.id);
    await writeProposalDelivery(refinementPackage.deliveryPath, refinement, "f2b-refinement-browser", "refinement");
    await refreshProposalFromBrowser(page, projectId, refinement.id);
    await panel.getByRole("button", { name: "Select identity reference" }).first().click();
    await expect(panel.getByTestId("cast-current-reference")).toContainText("current r2");

    await page.reload();
    await expect(panel.getByTestId("cast-current-reference")).toContainText("current r2");
    await workbench.restartBackend();
    await page.reload();
    await expect(panel.getByTestId("cast-current-reference")).toContainText("current r2");
    await expectOnlySourceMapGraph(request, workbench.apiOrigin, projectId);
  });

  test("cancels prepared and exported handoffs, retaining late delivery as inapplicable across close/reopen", async ({ page, request, workbench }) => {
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "cancel");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
    const panel = page.getByTestId("cast-reference-studies");
    await expect(panel).toBeVisible();

    await panel.getByLabel("Pose / composition direction").fill("Prepared study cancelled before any copy.");
    await prepareProposalFromBrowser(page, panel, projectId, request, workbench.apiOrigin);
    await panel.getByRole("button", { name: "Cancel handoff" }).click();
    await expect(panel).toContainText("Cancelled: Operator cancelled the exploratory reference handoff.");

    await panel.getByLabel("Pose / composition direction").fill("Exported study whose late package must not publish.");
    const exported = await prepareProposalFromBrowser(page, panel, projectId, request, workbench.apiOrigin);
    const exportedPackage = await copyProposalFromBrowser(page, projectId, exported.id);
    await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, exported.id)).state).toBe("exported");
    await panel.getByRole("button", { name: "Cancel handoff" }).first().click();
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
    await expect(panel).toContainText("Cancelled: Operator cancelled the exploratory reference handoff.");
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
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${staleProjectId}&stage=source`);
    await expect(page.getByTestId("cast-review")).toContainText("上下文已过期");
    await expect(page.getByTestId("cast-reference-studies")).toHaveCount(0);
    const staleCast = await getJson<any>(request.get(`${workbench.apiOrigin}/api/v2/projects/${staleProjectId}/cast`));
    expect(staleCast.status).toBe("stale");

    const firstProjectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "held-first");
    const secondProjectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "held-second");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${firstProjectId}&stage=source`);
    const firstPanel = page.getByTestId("cast-reference-studies");
    await expect(firstPanel).toBeVisible();
    await firstPanel.getByLabel("Pose / composition direction").fill("Held first-project study.");

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
      await firstPanel.getByRole("button", { name: "Prepare study assignment" }).click();
      await preparationStarted;
      await switchProjectInDirectory(page, secondProjectId);
      await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /^01 来源与大纲/ }).click();
      const secondPanel = page.getByTestId("cast-reference-studies");
      const secondDirection = secondPanel.getByLabel("Pose / composition direction");
      await expect(secondDirection).toBeEditable();
      await secondDirection.fill("Second-project direction must survive the first request.");
      releasePreparation?.();
      await expect(secondDirection).toHaveValue("Second-project direction must survive the first request.");
    } finally {
      releasePreparation?.();
      await page.unroute(`**/api/v2/projects/${firstProjectId}/character-reference-proposals`, heldRoute);
    }
  });
});

async function createAcceptedCastOnlyProject(request: Api, apiOrigin: string, label: string): Promise<string> {
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
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/cast/accept`, {
    data: {
      jobId: castPrepared.jobId,
      expectedCastRevision: castPrepared.expectedCastRevision,
      binding: castPrepared.binding,
      cast: readyCast.cast,
      consumerMappings: readyCast.cast.characters.map((character: { id: string }) => ({ castCharacterId: character.id, consumerCharacterId: character.id })),
    },
  }));
  return projectId;
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
  await expect(page.getByRole("button", { name: "Copy assignment" }).first()).toBeEnabled();
  const copied = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/character-reference-proposals/${proposalId}/copy`);
  await page.getByRole("button", { name: "Copy assignment" }).first().click();
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
  await panel.getByRole("button", { name: "Prepare study assignment" }).click();
  expect((await prepared).status()).toBe(201);
  await expect(panel.getByRole("button", { name: "Copy assignment" }).first()).toBeEnabled();
  return latestProposal(request, apiOrigin, projectId);
}

async function refreshProposalFromBrowser(page: import("@playwright/test").Page, projectId: string, proposalId: string): Promise<void> {
  const refreshed = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/character-reference-proposals/${proposalId}/refresh`);
  await page.getByRole("button", { name: "Refresh delivery" }).first().click();
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
