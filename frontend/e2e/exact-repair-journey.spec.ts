import type { APIRequestContext, Page, Response as PlaywrightResponse } from "@playwright/test";
import { expect, test } from "./fixture";

type StageName = "story_bible" | "story_graph" | "scene_beats" | "storyboard";
type ProviderStatus = {
  totalRequests: number;
  sceneTargets: string[];
  failedSceneTarget: string | null;
  failedSceneAttempts: number;
  requests: Array<{ type: string; target: string | null; failed: boolean; contentHash: string }>;
};

test("repairs exactly one late scene-beats shard through the real browser and public contracts", async ({ page, request, workbench }) => {
  await configurePublicNoAuthProfile(request, workbench.apiOrigin, workbench.providerOrigin);
  const projectId = await createDemoProject(page, workbench.frontendOrigin);

  await navigateToStage(page, "06 运行轨迹");
  const startedResponse = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/pipeline-runs`);
  await page.getByRole("button", { name: "运行所选阶段" }).click();
  const sourceRun = await json<{ id: string }>(await startedResponse);

  const quarantined = await pollProgress(request, workbench.apiOrigin, sourceRun.id, "quarantined");
  const failedUnit = quarantined.workUnits.find((unit) => unit.stage === "scene_beats" && unit.status === "quarantined");
  expect(failedUnit).toBeTruthy();
  expect(failedUnit).toMatchObject({ maxAttempts: 3, latestAttempt: { attemptNumber: 3, attemptKind: "correction", status: "failed" } });

  const headsBeforeRepair = await stages(request, workbench.apiOrigin, projectId);
  expect(headsBeforeRepair.every((head) => head.revision === 1 && head.status === "ready")).toBeTruthy();
  const parentTraceBefore = await trace(request, workbench.apiOrigin, sourceRun.id);
  const successfulSiblingResponse = parentTraceBefore.artifacts.find((artifact) => artifact.kind === "response"
    && artifact.stage === "scene_beats" && artifact.workUnitId !== failedUnit!.workUnitId);
  expect(successfulSiblingResponse).toBeTruthy();
  const providerBeforeRepair = await providerStatus(request, workbench.providerOrigin);
  expect(providerBeforeRepair.failedSceneAttempts).toBe(3);
  expect(providerBeforeRepair.sceneTargets).toHaveLength(9);
  expect(providerBeforeRepair.requests.filter((entry) => entry.type === "scene_beats" && !entry.failed)).toHaveLength(8);

  await navigateToStage(page, "07 隔离修复");
  const exactRepair = page.locator("#workspace-main").getByRole("button", { name: "修复这个 work unit" });
  await expect(exactRepair).toBeVisible();
  const repairResponse = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/runs/${sourceRun.id}/work-units/${failedUnit!.workUnitId}/repairs`);
  await exactRepair.click();
  const repairRun = await json<{ id: string; parentRunId: string | null; kind: string }>(await repairResponse);
  expect(repairRun).toMatchObject({ parentRunId: sourceRun.id, kind: "repair" });

  const repaired = await pollProgress(request, workbench.apiOrigin, repairRun.id, "succeeded");
  expect(repaired.workUnits.filter((unit) => unit.stage === "scene_beats" && unit.status === "succeeded")).toHaveLength(9);
  const providerAfterRepair = await providerStatus(request, workbench.providerOrigin);
  const callsDuringRepair = providerAfterRepair.requests.slice(providerBeforeRepair.totalRequests);
  const repairedSceneCalls = callsDuringRepair.filter((entry) => entry.type === "scene_beats");
  expect(repairedSceneCalls).toEqual([expect.objectContaining({ target: providerBeforeRepair.failedSceneTarget, failed: false })]);

  const parentTraceAfter = await trace(request, workbench.apiOrigin, sourceRun.id);
  expect(parentTraceAfter.artifacts.find((artifact) => artifact.id === successfulSiblingResponse!.id)).toMatchObject({
    contentHash: successfulSiblingResponse!.contentHash,
    workUnitId: successfulSiblingResponse!.workUnitId,
  });
  const childExecution = await executionTrace(request, workbench.apiOrigin, repairRun.id);
  expect(childExecution.sealedAggregates.map((aggregate) => aggregate.stage)).toEqual([
    "story_bible", "story_graph", "scene_beats", "storyboard",
  ]);
  const headsAfterRepair = await stages(request, workbench.apiOrigin, projectId);
  expect(headsAfterRepair.every((head) => head.revision === 2 && head.status === "ready")).toBeTruthy();

  await page.reload();
  await navigateToStage(page, "05 分镜工作台");
  await page.getByLabel("审核人标签").fill("Exact repair browser reviewer");
  const approvalResponse = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/storyboard-approval`);
  await expect(page.getByRole("button", { name: "批准当前分镜" })).toBeEnabled();
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  expect((await approvalResponse).status()).toBe(201);

  await page.reload();
  await expect(page.getByText("当前批准：Exact repair browser reviewer", { exact: true })).toBeVisible();
  const persistedRepair = await json<{ parentRunId: string | null; kind: string }>(await request.get(`${workbench.apiOrigin}/api/v2/runs/${repairRun.id}`));
  expect(persistedRepair).toMatchObject({ parentRunId: sourceRun.id, kind: "repair" });
  const review = await json<{ activeApproval: { reviewer: string; decision: string } | null }>(await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/storyboard-review`));
  expect(review.activeApproval).toMatchObject({ reviewer: "Exact repair browser reviewer", decision: "approve" });
});

async function configurePublicNoAuthProfile(request: APIRequestContext, apiOrigin: string, providerOrigin: string): Promise<void> {
  const catalog = await json<{ profiles: Array<{ profileId: string; displayName: string; revision: number; configuration: Record<string, unknown> }> }>(await request.get(`${apiOrigin}/api/v2/text-provider-profiles`));
  const profile = catalog.profiles.find((candidate) => candidate.profileId === "default");
  expect(profile).toBeTruthy();
  const configuration = {
    ...profile!.configuration,
    textProvider: "external-openai-fake",
    textBaseUrl: `${providerOrigin}/v1`,
    textModel: "external-fake-v1",
    textAuthMode: "none",
    textCapabilities: { chatCompletions: true, jsonObject: false, jsonSchema: true, chatTemplateKwargs: false },
    presetId: "custom",
    profileHash: "",
  };
  const response = await request.put(`${apiOrigin}/api/v2/text-provider-profiles/default`, {
    data: { expectedRevision: profile!.revision, displayName: "External E2E fake", configuration },
  });
  expect(response.ok()).toBeTruthy();
}

async function createDemoProject(page: Page, frontendOrigin: string): Promise<string> {
  await page.goto(`${frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await navigateToStage(page, "05 分镜工作台");
  const created = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === "/api/v2/projects");
  await page.getByRole("button", { name: "保存分镜" }).click();
  expect((await created).ok()).toBeTruthy();
  await expect(page).toHaveURL(/[?&]project=/);
  const projectId = new URL(page.url()).searchParams.get("project");
  expect(projectId).toBeTruthy();
  return projectId!;
}

async function navigateToStage(page: Page, name: string): Promise<void> {
  await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", {
    name: new RegExp(`^${escapeRegex(name)}`),
  }).click();
}

async function pollProgress(request: APIRequestContext, apiOrigin: string, runId: string, status: string): Promise<{ workUnits: Array<{ workUnitId: string; stage: string; status: string; maxAttempts: number; latestAttempt: Record<string, unknown> | null }> }> {
  const deadline = Date.now() + 30_000;
  let latest: { status: string; workUnits: Array<{ workUnitId: string; stage: string; status: string; maxAttempts: number; latestAttempt: Record<string, unknown> | null }> } | undefined;
  while (Date.now() < deadline) {
    const response = await request.get(`${apiOrigin}/api/v2/runs/${runId}/progress`);
    latest = await json<typeof latest>(response);
    if (latest?.status === status) return latest;
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`run ${runId} did not reach ${status}: ${JSON.stringify(latest)}`);
}

async function providerStatus(request: APIRequestContext, providerOrigin: string): Promise<ProviderStatus> {
  return json<ProviderStatus>(await request.get(`${providerOrigin}/control/status`));
}

async function trace(request: APIRequestContext, apiOrigin: string, runId: string): Promise<{ artifacts: Array<{ id: string; kind: string; stage: string | null; workUnitId: string | null; contentHash: string }> }> {
  return json(await request.get(`${apiOrigin}/api/v2/runs/${runId}/trace`));
}

async function executionTrace(request: APIRequestContext, apiOrigin: string, runId: string): Promise<{ sealedAggregates: Array<{ stage: StageName }> }> {
  return json(await request.get(`${apiOrigin}/api/v2/runs/${runId}/execution-trace`));
}

async function stages(request: APIRequestContext, apiOrigin: string, projectId: string): Promise<Array<{ stage: StageName; revision: number; status: string }>> {
  const result = await json<{ stages: Array<{ head: { stage: StageName; revision: number; status: string } }> }>(await request.get(`${apiOrigin}/api/v2/projects/${projectId}/stages`));
  return result.stages.map((item) => item.head);
}

async function json<T>(response: PlaywrightResponse | Awaited<ReturnType<APIRequestContext["get"]>>): Promise<T> {
  expect(response.ok(), `${response.status()} ${await response.text()}`).toBeTruthy();
  return response.json() as Promise<T>;
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
