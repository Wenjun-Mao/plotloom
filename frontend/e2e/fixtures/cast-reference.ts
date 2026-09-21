import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { demoProject } from "../../src/demo";
import { expect } from "../fixture";

const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const retainedStill = path.join(
  repositoryRoot,
  "docs/verification/supporting/p0-generated/01-arrival.png",
);

type Api = import("@playwright/test").APIRequestContext;

export type PackagePaths = { packagePath: string; deliveryPath: string };
export type Proposal = {
  id: string;
  requestHash: string;
  parentCandidateAssetId: string | null;
  state: string;
  current: boolean;
  deliveries: Array<{
    state: string;
    diagnosticCode?: string;
    publicationPhase?: string | null;
    candidates: Array<{ id: string; assetId: string }>;
  }>;
};

export async function createAcceptedCastOnlyProject(
  request: Api,
  apiOrigin: string,
  label: string,
): Promise<string> {
  const ready = await createCastReadyProject(request, apiOrigin, label);
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${ready.projectId}/cast/accept`, {
    data: {
      jobId: ready.castPrepared.jobId,
      expectedCastRevision: ready.castPrepared.expectedCastRevision,
      binding: ready.castPrepared.binding,
      cast: ready.readyCast.cast,
      consumerMappings: ready.readyCast.cast.characters.map(
        (character: { id: string }) => ({
          castCharacterId: character.id,
          consumerCharacterId: character.id,
        }),
      ),
    },
  }));
  return ready.projectId;
}

export async function createCastReadyProject(
  request: Api,
  apiOrigin: string,
  label: string,
): Promise<{ projectId: string; castPrepared: any; readyCast: any }> {
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

export async function sendProposalFromBrowser(
  page: import("@playwright/test").Page,
  projectId: string,
  proposalId: string,
): Promise<PackagePaths> {
  const proposalCard = page.locator(`[data-proposal-id="${proposalId}"]`);
  await expect(proposalCard.getByRole("button", { name: "发送给 specialist" })).toBeEnabled();
  const sent = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/character-reference-proposals/${proposalId}/send`);
  await proposalCard.getByRole("button", { name: "发送给 specialist" }).click();
  const response = await sent;
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json() as Promise<PackagePaths>;
}

export async function prepareProposalFromBrowser(
  page: import("@playwright/test").Page,
  panel: import("@playwright/test").Locator,
  projectId: string,
  request: Api,
  apiOrigin: string,
): Promise<Proposal> {
  const prepared = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/character-reference-proposals`);
  await panel.getByRole("button", { name: "创建提案" }).click();
  expect((await prepared).status()).toBe(201);
  const latest = await latestProposal(request, apiOrigin, projectId);
  await expect(panel.locator(`[data-proposal-id="${latest.id}"]`).getByRole("button", { name: "发送给 specialist" })).toBeEnabled();
  return latest;
}

export async function refreshProposalFromBrowser(
  page: import("@playwright/test").Page,
  projectId: string,
  proposalId: string,
): Promise<void> {
  const refreshed = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/character-reference-proposals/${proposalId}/refresh`);
  await page.locator(`[data-proposal-id="${proposalId}"]`).getByRole("button", { name: "立即检查交付" }).click();
  expect((await refreshed).ok()).toBeTruthy();
}

export async function latestProposal(request: Api, apiOrigin: string, projectId: string): Promise<Proposal> {
  const proposals = await getJson<{ proposals: Proposal[] }>(request.get(`${apiOrigin}/api/v2/projects/${projectId}/character-reference-proposals`));
  expect(proposals.proposals.length).toBeGreaterThan(0);
  return proposals.proposals[0]!;
}

export async function proposal(
  request: Api,
  apiOrigin: string,
  projectId: string,
  proposalId: string,
): Promise<Proposal> {
  const proposals = await getJson<{ proposals: Proposal[] }>(request.get(`${apiOrigin}/api/v2/projects/${projectId}/character-reference-proposals`));
  const found = proposals.proposals.find((item) => item.id === proposalId);
  expect(found).toBeDefined();
  return found!;
}

export async function writeProposalDelivery(
  deliveryPath: string,
  proposal: Proposal,
  deliveryId: string,
  role: "original" | "refinement",
): Promise<void> {
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

export async function writeProposalPartialDelivery(deliveryPath: string): Promise<void> {
  const content = await readFile(retainedStill);
  await mkdir(path.join(deliveryPath, "outputs"), { recursive: true });
  await writeFile(path.join(deliveryPath, "outputs", "candidate.png"), content);
}

export async function makeProposalManifestInvalid(deliveryPath: string): Promise<void> {
  const completionPath = path.join(deliveryPath, "completion.json");
  const manifest = JSON.parse(await readFile(completionPath, "utf8"));
  manifest.toolEvidence.available = false;
  await writeFile(completionPath, JSON.stringify(manifest));
}

export async function makeProposalOutputSetPartial(deliveryPath: string): Promise<void> {
  const completionPath = path.join(deliveryPath, "completion.json");
  const manifest = JSON.parse(await readFile(completionPath, "utf8"));
  manifest.outputs.push({ filename: "missing.png", sha256: "0".repeat(64), role: "original" });
  await writeFile(completionPath, JSON.stringify(manifest));
}

export async function makeProposalPackageConflict(packagePath: string): Promise<void> {
  const requestPath = path.join(packagePath, "request.json");
  const frozenRequest = JSON.parse(await readFile(requestPath, "utf8"));
  frozenRequest.visualDirection = "Tampered fixture package must not be admitted.";
  await writeFile(requestPath, JSON.stringify(frozenRequest));
}

export async function expectOnlySourceMapGraph(request: Api, apiOrigin: string, projectId: string): Promise<void> {
  const stages = await getJson<{ stages: Array<{ head: { stage: string; revision: number }; payload: unknown }> }>(request.get(`${apiOrigin}/api/v2/projects/${projectId}/stages`));
  expect(stages.stages.filter((stage) => stage.payload).map((stage) => stage.head.stage)).toEqual(["story_graph"]);
  expect(stages.stages.filter((stage) => stage.head.stage !== "story_graph").every((stage) => stage.head.revision === 0)).toBeTruthy();
}

export async function switchProjectInDirectory(page: import("@playwright/test").Page, projectId: string): Promise<void> {
  await page.getByRole("button", { name: /当前项目 · 切换/ }).click();
  const directory = page.getByRole("dialog", { name: "项目目录" });
  await expect(directory).toBeVisible();
  await directory.locator(`[data-project-id="${projectId}"] .directory-open`).click();
  await expect(directory).toBeHidden();
  await expect(page).toHaveURL(new RegExp(`project=${projectId}`));
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

async function getJson<T>(responseOrPromise: Awaited<ReturnType<Api["get"]>> | Promise<Awaited<ReturnType<Api["get"]>>>): Promise<T> {
  const response = await responseOrPromise;
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json() as Promise<T>;
}

function hash(value: Buffer): string {
  return createHash("sha256").update(value).digest("hex");
}
