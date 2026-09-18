import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { APIRequestContext, APIResponse, Page, Locator } from "@playwright/test";
import { demoProject } from "../src/demo";
import { expect } from "./fixture";

const directory = path.dirname(fileURLToPath(import.meta.url));
export const fixtureDirectory = path.join(directory, "fixtures/f5a");
const validator = path.resolve(directory, "../../third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs");
export type Preparation = { jobId: string; packagePath: string; deliveryPath: string; assignment: string; binding: any; expectedReviewRevision: number };
export async function json<T = any>(pending: Pick<APIResponse, "ok" | "text" | "json"> | Promise<Pick<APIResponse, "ok" | "text" | "json">>): Promise<T> {
  const response = await pending;
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json() as Promise<T>;
}
export async function fixture(name: string): Promise<any> {
  return JSON.parse(await readFile(path.join(fixtureDirectory, name), "utf8"));
}
export function endpoint(origin: string, projectId: string): string {
  return `${origin}/api/v2/projects/${projectId}/storyboard-source-review`;
}
export async function createScriptProject(request: APIRequestContext, origin: string, label: string): Promise<string> {
  const root = `${origin}/api/v2/projects`;
  const created = await json(request.post(root, { headers: { "Idempotency-Key": `f5a-${label}-${Date.now()}` }, data: { brief: { ...demoProject.brief, title: `F5A ${label}`, targetPlaythroughSeconds: 180 } } }));
  const id = created.id;
  const url = `${root}/${id}`;
  const source = await json(request.put(`${url}/source-outline/source`, { data: { expectedSourceRevision: 0, material: {
    kind: "synopsis", title: "Beacon choice — current F4 proof", text: "A keeper must power the beacon or dock before the storm closes the channel.",
    attribution: "Deterministic integration fixture", rightsDeclaration: "Technical test only", adaptationIntent: "Preserve one choice and two explicit endings.",
  } } }));
  const outline = await json(request.post(`${url}/source-outline/candidates`));
  await writeDelivery(outline, "outline", await fixture("outline.json"));
  await json(request.post(`${url}/source-outline/candidates/${outline.jobId}/refresh`));
  const accepted = await json(request.post(`${url}/source-outline/accept`, { data: { jobId: outline.jobId, expectedSourceRevision: source.source.revision, expectedOutlineRevision: 0 } }));
  const map = await json(request.put(`${url}/source-outline/section-map`, { data: { expectedSectionMapRevision: 0, expectedSourceRevision: 1, expectedOutlineRevision: 1, expectedOutlineContentHash: accepted.acceptedOutline.contentHash, mapping: await fixture("section-map.json") } }));
  await json(request.post(`${url}/source-outline/section-map/install-graph`, { data: {
    expectedSourceRevision: 1, expectedSourceContentHash: map.source.contentHash, expectedOutlineRevision: 1, expectedOutlineContentHash: map.acceptedOutline.contentHash,
    expectedSectionMapRevision: 1, expectedSectionMapContentHash: map.acceptedSectionMap.contentHash, expectedGraphRevision: 0,
  } }));
  for (const stage of ["cast", "art", "script"]) {
    const prepared = await json(request.post(`${url}/${stage}/candidates`));
    await writeDelivery(prepared, stage === "cast" ? "characters" : stage, await fixture(`${stage}.json`));
    const ready = await json(request.post(`${url}/${stage}/candidates/${prepared.jobId}/refresh`));
    const body: Record<string, unknown> = { jobId: prepared.jobId, binding: prepared.binding, [`expected${stage[0].toUpperCase()}${stage.slice(1)}Revision`]: 0 };
    if (stage === "cast") body.consumerMappings = ready.cast.characters.map((character: { id: string }) => ({ castCharacterId: character.id, consumerCharacterId: character.id }));
    await json(request.post(`${url}/${stage}/accept`, { data: body }));
  }
  return id;
}
export async function writeDelivery(prepared: Preparation, stage = "storyboard", candidate?: any): Promise<void> {
  const request = JSON.parse(await readFile(path.join(prepared.packagePath, "request.json"), "utf8"));
  const filename = `${stage === "characters" ? "cast" : stage}.json`;
  const content = candidate ? Buffer.from(JSON.stringify(candidate)) : await readFile(path.join(fixtureDirectory, filename));
  await mkdir(prepared.deliveryPath, { recursive: true });
  const candidatePath = path.join(prepared.deliveryPath, filename);
  await writeFile(candidatePath, content);
  let report = Buffer.from("<!doctype html><html><body>Deterministic upstream-context fixture report</body></html>");
  if (stage === "storyboard") {
    const inputs = path.join(prepared.packagePath, "inputs");
    const args = [candidatePath, "--script", path.join(inputs, "script.json"), "--outline", path.join(inputs, "outline.json"), "--cast", path.join(inputs, "cast.json")];
    execFileSync(process.execPath, [validator, "validate", ...args, "--no-log"]);
    report = execFileSync(process.execPath, [validator, "render", ...args, "--art", path.join(inputs, "art.json"), "--html"]);
  }
  await writeFile(path.join(prepared.deliveryPath, "report.html"), report);
  await writeFile(path.join(prepared.deliveryPath, "completion.json"), JSON.stringify({
    schemaVersion: 1, jobId: prepared.jobId, requestHash: request.requestHash, deliveryId: `deterministic-${prepared.jobId}`, stage,
    candidate: { filename, sha256: hash(content) }, report: { filename: "report.html", sha256: hash(report) },
    executorProvenance: { codeRevision: "abcdef0", skillVersion: "deterministic-fixture", skillHash: request.executionPin.specialistSkillHash, upstreamRevision: request.executionPin.upstreamRevision, upstreamSkillHash: request.executionPin.upstreamSkillHash, model: "deterministic-fixture", reasoningEffort: "high" },
    limitations: ["Portable deterministic integration fixture; no specialist execution or creative approval."],
  }));
}
export async function prepare(page: Page, panel: Locator, id: string): Promise<Preparation> {
  const response = page.waitForResponse(r => r.request().method() === "POST" && new URL(r.url()).pathname === `/api/v2/projects/${id}/storyboard-source-review/candidates`);
  await panel.getByRole("button", { name: "准备并复制 storyboard specialist handoff" }).click();
  return json(await response);
}
export async function refresh(page: Page, panel: Locator, id: string, jobId: string): Promise<void> {
  const response = page.waitForResponse(r => r.request().method() === "POST" && new URL(r.url()).pathname === `/api/v2/projects/${id}/storyboard-source-review/candidates/${jobId}/refresh`);
  await panel.getByRole("button", { name: "刷新 specialist delivery" }).click();
  await json(await response);
  await expect(panel.getByRole("button", { name: "显式接受 review revision" })).toBeEnabled();
}
export async function changeScript(request: APIRequestContext, origin: string, id: string): Promise<void> {
  const url = `${origin}/api/v2/projects/${id}/script`;
  const state = await json(request.get(url));
  await json(request.post(`${url}/reopen`, { data: { expectedScriptRevision: state.acceptedScript.revision } }));
  const episode = { ...state.acceptedScript.script.episodes[0], cliff: "Deterministic edited route status; choice remains pending." };
  await json(request.post(`${url}/sections/save`, { data: { sectionId: "opening", expectedScriptRevision: state.acceptedScript.revision, binding: state.acceptedScript.binding, episode } }));
}
export function hash(content: Buffer): string { return createHash("sha256").update(content).digest("hex"); }
