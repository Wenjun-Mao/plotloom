import { acknowledgeGraphMapping, graphDraftRevision, currentFixtureMapping, beaconMap } from "./fixtures/graph-authoring";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { deflateSync } from "node:zlib";
import { demoProject } from "../src/demo";
import { styledCastFixture } from "./fixtures/cast-style";
import { expect } from "@playwright/test";

export type Api = import("@playwright/test").APIRequestContext;

export type ArtPreparation = {
  jobId: string;
  packagePath: string;
  deliveryPath: string;
  expectedArtRevision: number;
  binding: unknown;
};

export type ArtState = {
  candidate: { jobId: string; status: string } | null;
  acceptedArt: { revision: number; art: Record<string, unknown> } | null;
  status: string;
};

export type ScriptPreparation = { jobId: string; packagePath: string; deliveryPath: string; expectedScriptRevision: number; binding: unknown };

export async function createAcceptedCastProject(request: Api, apiOrigin: string, label: string): Promise<string> {
  const created = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `f3a-art-${label}-${Date.now()}` },
    data: { brief: { ...demoProject.brief, decisionPointsPerPath: 1, endingCount: 2, desiredJoinCount: 0, title: `F3A browser ${label}` } },
  });
  const projectId = (await getJson<{ id: string }>(created)).id;
  const source = await getJson<any>(request.put(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/source`, {
    data: { expectedSourceRevision: 0, material: sourceMaterial(label) },
  }));
  const outline = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/candidates`));
  await writeStageDelivery(outline, "outline.json", { source: "F3A browser fixture", summary: "A bounded beacon choice.", sections: ["opening", "beacon", "dock"] }, "f3a-outline", "outline");
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/candidates/${outline.jobId}/refresh`));
  const acceptedOutline = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/accept`, { data: { jobId: outline.jobId, expectedSourceRevision: source.source.revision, expectedOutlineRevision: 0 } }));
  const projectUrl = `${apiOrigin}/api/v2/projects/${projectId}`;
  const mapping = await currentFixtureMapping(request, projectUrl, beaconMap());
  const draftRevision = await acknowledgeGraphMapping(request, projectUrl, mapping);
  const map = await getJson<any>(request.put(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/section-map`, {
    data: { expectedSectionMapRevision: 0, expectedSourceRevision: acceptedOutline.source.revision, expectedOutlineRevision: acceptedOutline.acceptedOutline.revision, expectedOutlineContentHash: acceptedOutline.acceptedOutline.contentHash, mapping, expectedGraphDraftRevision: draftRevision },
  }));
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/source-outline/section-map/install-graph`, {
    data: { expectedSourceRevision: map.source.revision, expectedSourceContentHash: map.source.contentHash, expectedOutlineRevision: map.acceptedOutline.revision, expectedOutlineContentHash: map.acceptedOutline.contentHash, expectedSectionMapRevision: map.acceptedSectionMap.revision, expectedSectionMapContentHash: map.acceptedSectionMap.contentHash, expectedGraphRevision: 0, expectedGraphDraftRevision: await graphDraftRevision(request, projectUrl) },
  }));
  const cast = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/cast/candidates`, { data: { renderStyle: "realistic" } }));
  await writeStageDelivery(cast, "cast.json", castFixture(), "f3a-cast", "characters");
  const readyCast = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/cast/candidates/${cast.jobId}/refresh`));
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/cast/accept`, {
    data: { jobId: cast.jobId, expectedCastRevision: cast.expectedCastRevision, binding: cast.binding, cast: readyCast.cast, consumerMappings: readyCast.cast.characters.map((character: { id: string }) => ({ castCharacterId: character.id, consumerCharacterId: character.id })) },
  }));
  return projectId;
}

export async function createAcceptedArtProject(request: Api, apiOrigin: string, label: string): Promise<string> {
  const projectId = await createAcceptedCastProject(request, apiOrigin, label);
  const prepared = await getJson<ArtPreparation>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/art/candidates`, { data: { renderStyle: "realistic" } }));
  await writeArtDelivery(prepared, `f3b-art-${label}`);
  const ready = await getJson<any>(request.post(`${apiOrigin}/api/v2/projects/${projectId}/art/candidates/${prepared.jobId}/refresh`));
  await getJson(request.post(`${apiOrigin}/api/v2/projects/${projectId}/art/accept`, {
    data: { jobId: prepared.jobId, expectedArtRevision: prepared.expectedArtRevision, binding: prepared.binding, art: ready.art },
  }));
  return projectId;
}

export async function writeArtReferenceDelivery(response: import("@playwright/test").Response): Promise<void> {
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

export async function prepareFromBrowser(page: import("@playwright/test").Page, panel: import("@playwright/test").Locator, projectId: string): Promise<ArtPreparation> {
  await panel.getByLabel("美术风格", { exact: true }).selectOption("realistic");
  const prepared = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/art/candidates`);
  await panel.getByRole("button", { name: "准备美术设定任务" }).click();
  const response = await prepared;
  expect(response.status()).toBe(201);
  return response.json() as Promise<ArtPreparation>;
}

export async function refreshFromBrowser(page: import("@playwright/test").Page, panel: import("@playwright/test").Locator, projectId: string, jobId: string): Promise<void> {
  const refreshed = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/specialist-tasks/art/${jobId}/check`);
  await panel.getByRole("button", { name: "立即检查" }).click();
  expect((await refreshed).ok()).toBeTruthy();
}

export async function writeArtDelivery(prepared: ArtPreparation, deliveryId: string): Promise<void> {
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

export async function writeStageDelivery(prepared: any, filename: string, candidate: Record<string, unknown>, deliveryId: string, stage: string): Promise<void> {
  const request = JSON.parse(await readFile(path.join(prepared.packagePath, "request.json"), "utf8"));
  const content = Buffer.from(JSON.stringify(stage === "characters" ? styledCastFixture(candidate, request.inputArtifacts["cast-style-contract.json"]) : candidate));
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

export function sourceMaterial(label: string) { return { kind: "synopsis", title: `Beacon choice ${label}`, text: "A keeper must power the beacon or dock before the storm closes the channel.", attribution: "F3A production-browser fixture", rightsDeclaration: "Test fixture only; not a rights determination.", adaptationIntent: "Preserve one choice and two explicit endings." }; }
export function castFixture() { return { source: "F3A browser fixture", summary: "One beacon keeper.", characters: [{ id: "keeper", name: "Mira", reviewNotes: { sourceNotes: "Appearance is proposed", performanceGuidance: "" }, persona: { personality: ["Careful"],  motivation: "Guide sailors home", appearance: "Rain-dark hair and a weathered beacon coat", arc: "Chooses who to protect" }, voice: { timbre: "Steady under pressure" } }] }; }
export function artFixture() { const render = "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth"; return { source: "F3A browser fixture", style: "realistic", scenes: [{ id: "S01", name: "Beacon room", primary: true, summary: "The keeper faces a power choice.", anchors: [{ name: "brass lamp", desc: "old brass" }, { name: "window", desc: "salted glass" }, { name: "desk", desc: "worn wood" }], lighting: [{ state: "dawn", prompt: "cold dawn through a window" }], image: { prompt: render + ", empty beacon room", negativePrompt: "people, human figures", sheet: render, tags: [] } }], props: [], sectionUsage: beaconMap().sections.map(section => ({ sectionId: section.sectionId, sceneIds: ["S01"], propIds: [] })) }; }
export function mockedArtReferenceStudies(projectId: string) {
  const createdAt = "2026-09-21T00:00:00Z";
  const candidates = Array.from({ length: 5 }, (_, index) => {
    const assetId = `mock-f3b-${index}`;
    return {
      id: `mock-candidate-${index}`, assetId, proposalId: "mock-f3b-read-only", outputFilename: `mock-candidate-${index}.png`, outputHash: `mock-output-${index}`, role: "art_reference", createdAt,
      asset: { id: assetId, projectId, originalHash: `mock-original-${index}`, displayHash: `mock-display-${index}`, mimeType: "image/png", byteSize: 68, width: 1, height: 1, createdAt, provenance: { origin: "已隔离的只读浏览器演示（明确 mock）", rights: "unknown", rightsNote: "No ImageGen or provider output; test-only response.", declaredAdditions: [] } },
    };
  });
  return { configured: true, proposals: [{ id: "mock-f3b-read-only", projectId, subjectType: "scene", subjectId: "S01", request: { demonstration: "已隔离的只读浏览器演示（明确 mock）" }, requestHash: "mocked-read-only", state: "delivered", current: true, exportedAt: createdAt, cancelledAt: null, cancellationReason: null, createdAt, deliveries: [{ id: "mock-delivery", deliveryId: "mocked-read-only-browser-demo", state: "accepted", diagnosticCode: null, manifestHash: "mocked-read-only", createdAt, candidates }] }] };
}
export function scriptFixture() { const episode = (ep: number) => ({ ep, targetSeconds: 60, hook: `Section ${ep} begins in motion`, cliff: `Section ${ep} leaves a choice open`, hookBeat: [1, 1], beatsClaimed: [], scenes: [{ sceneId: "S01", lighting: "dawn", characters: [], props: [], flow: Array.from({ length: 24 }, (_, index) => ({ action: `Mira crosses the beacon room, action ${index}.` })) }] }); return { source: "F3A browser fixture", sectionBindings: [{ sectionId: "opening", episode: 1 }, { sectionId: "beacon", episode: 2 }, { sectionId: "dock", episode: 3 }], episodes: [episode(1), episode(2), episode(3)] }; }
export function withSummary(art: Record<string, unknown>, summary: string): Record<string, unknown> { return { ...art, scenes: (art.scenes as Array<Record<string, unknown>>).map((scene, index) => index === 0 ? { ...scene, summary } : scene) }; }

export async function expectOnlySourceMapGraph(request: Api, apiOrigin: string, projectId: string): Promise<void> {
  const stages = await getJson<{ stages: Array<{ head: { stage: string; revision: number }; payload: unknown }> }>(request.get(`${apiOrigin}/api/v2/projects/${projectId}/stages`));
  expect(stages.stages.filter((stage) => stage.payload).map((stage) => stage.head.stage)).toEqual(["story_graph"]);
  expect(stages.stages.filter((stage) => stage.head.stage !== "story_graph").every((stage) => stage.head.revision === 0)).toBeTruthy();
}

export async function switchProject(page: import("@playwright/test").Page, projectId: string): Promise<void> {
  await page.getByRole("button", { name: /当前项目 · 切换/ }).click();
  const directory = page.getByRole("dialog", { name: "项目目录" });
  await directory.locator(`[data-project-id="${projectId}"] .directory-open`).click();
  await expect(directory).toBeHidden();
  await expect(page).toHaveURL(new RegExp(`project=${projectId}`));
}

export async function getJson<T>(responseOrPromise: Awaited<ReturnType<Api["get"]>> | Promise<Awaited<ReturnType<Api["get"]>>>): Promise<T> {
  const response = await responseOrPromise;
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json() as Promise<T>;
}

export function hash(value: Buffer): string { return createHash("sha256").update(value).digest("hex"); }

export function fixturePng(): Buffer {
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

export function crc32(value: Buffer): number {
  let crc = 0xffffffff;
  for (const byte of value) { crc ^= byte; for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1)); }
  return (crc ^ 0xffffffff) >>> 0;
}
