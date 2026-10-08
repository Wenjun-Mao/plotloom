import type { Locator, Page, TestInfo } from "@playwright/test";
import { expect, test } from "./fixture";
import { json } from "./f5a-fixture";
import { demoProject, demoRun } from "../src/demo";
import type { PipelineRun, RunProgress, RunProgressWorkUnit, RunTrace } from "../src/types";

const desktopSizes = [[1700, 900], [1280, 768], [1280, 460]] as const;
async function capture(page: Page, info: TestInfo, name: string, target: Locator) {
  for (const [width, height] of desktopSizes) {
    await page.setViewportSize({ width, height });
    await target.evaluate(element => element.scrollIntoView({ block: "center" }));
    const bounds = await target.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.y).toBeGreaterThanOrEqual(58);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height - 12);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    for (const event of await page.locator(".trace-event").all()) {
      const timestamp = await event.locator("time").boundingBox();
      const content = await event.locator("div").boundingBox();
      expect(timestamp!.y + timestamp!.height).toBeLessThanOrEqual(content!.y);
    }
    await page.screenshot({ path: info.outputPath(`${name}-${width}x${height}.png`) });
  }
}
function progress(run: PipelineRun, units: RunProgressWorkUnit[] = []): RunProgress {
  return { runId: run.id, status: run.status, failureCode: run.failureCode, failedStage: run.failedStage,
    stageProgress: [], workUnits: units,
    actions: { canResume: false, canCancel: ["queued", "running", "cancel_requested"].includes(run.status), canRebuildStage: run.status === "quarantined", repairEligible: false } };
}
async function installReads(page: Page, projectId: string, getRun: () => PipelineRun | undefined, getProgress: () => RunProgress | undefined, getAttempts: () => RunTrace["attempts"] = () => []) {
  await page.route(`**/api/v2/projects/${projectId}/runs`, route => route.fulfill({ json: { runs: getRun() ? [getRun()] : [] } }));
  await page.route("**/api/v2/runs/ui-reading-run/**", route => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname.endsWith("/progress")) return route.fulfill({ json: getProgress() });
    if (pathname.endsWith("/trace")) return route.fulfill({ json: { run: getRun(), attempts: getAttempts(), artifacts: [], snapshotIsCurrent: true } });
    if (pathname.endsWith("/execution-trace")) return route.fulfill({ json: {
      generationPlan: null, storyGraphTopology: null, stagePlans: [], workUnits: [], sealedAggregates: [],
    } });
    return route.abort();
  });
}

test("Trace distinguishes true idle, retained failure, and pending cancellation without writes", async ({ page, request, workbench }, info) => {
  const project = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, {
    data: { brief: { ...demoProject.brief, title: "UI运行记录读取夹具" }, initialStages: [] },
  }));
  let run: PipelineRun | undefined;
  let attempts: RunTrace["attempts"] = [];
  await installReads(page, project.id, () => run, () => run ? progress(run) : undefined, () => attempts);
  const writes: string[] = [];
  page.on("request", request => { if (request.url().includes("/api/v2/") && request.method() !== "GET") writes.push(request.method()); });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=trace`);
  await expect(page.getByText("还没有运行记录", { exact: true })).toBeVisible();
  await expect(page.locator(".prompt-inspector")).toContainText("任务启动后，运行详情会显示在这里");
  await expect(page.locator(".prompt-inspector")).not.toContainText("选择一个事件");
  await capture(page, info, "trace-idle", page.locator(".trace-list .empty-state"));
  run = { ...demoRun, id: "ui-reading-run", projectId: project.id, status: "failed", error: "读取模型响应失败；未保存新内容。",
    failureCode: "provider.response_unavailable", providerSnapshot: { textAuthMode: "none" } };
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=trace&run=${run.id}`);
  await expect(page.locator(".run-state")).toContainText("运行失败");
  await expect(page.locator(".run-console")).toContainText(run.failureCode!);
  await expect(page.locator(".run-progress-panel")).not.toContainText("选择事件");
  await capture(page, info, "trace-failed-run", page.locator(".run-console"));
  expect((await page.locator(".run-state .badge").boundingBox())!.height).toBeLessThan(34);
  await capture(page, info, "trace-failed-no-events", page.locator(".trace-list .empty-state"));
  await capture(page, info, "trace-failed-no-detail", page.locator(".prompt-inspector .empty-state"));
  run = { ...run, status: "cancel_requested", error: null, failureCode: null, failedStage: null, finishedAt: null };
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=trace&run=${run.id}`);
  await expect(page.locator(".run-state")).toContainText("已请求取消，等待运行结束");
  await expect(page.getByRole("button", { name: "再次请求取消", exact: true }).first()).toBeEnabled();
  await expect(page.getByRole("button", { name: "取消运行", exact: true })).toHaveCount(0);
  await capture(page, info, "trace-cancel-requested", page.locator(".run-console"));
  await capture(page, info, "trace-cancel-action", page.locator(".page-header"));
  await page.getByText("查看技术详情", { exact: true }).click();
  await capture(page, info, "trace-cancel-inspector", page.locator(".inspector-run"));
  await capture(page, info, "trace-cancel-inspector-action", page.locator(".inspector-actions"));
  // Loading an active no-auth run normally resumes its owned execution. This
  // reading-only fixture uses the real frozen-key refusal, not a hidden bypass.
  run = { ...run, status: "running", providerSnapshot: { textAuthMode: "bearer", profileId: "default" } };
  attempts = [{ id: "ui-running-attempt", runId: run.id, workUnitId: "ui-unit", stage: "story_graph", attemptNumber: 1,
    attemptKind: "primary", sourceAttemptId: null, status: "running", provider: null, model: null, error: null,
    dispatchedAt: null, responsePersistedAt: null, providerRequestId: null, outcomeUnknown: false, outcomeCode: null,
    startedAt: "2026-10-08T00:00:00Z", finishedAt: null }];
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=trace&run=${run.id}`);
  await expect(page.getByRole("alert")).toContainText("补充当前标签页 Key");
  await expect(page.locator(".inspector-meta .badge.accent")).toHaveText("进行中");
  await expect(page.locator(".run-progress-panel")).toContainText("选择事件");
  await capture(page, info, "trace-running-key-blocked-event", page.locator(".inspector-meta"));
  expect(writes).toEqual([]);
});

test("repair refusal and unknown result preserve exact evidence without suggesting automatic retries", async ({ page, request, workbench }, info) => {
  const project = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, {
    data: { brief: { ...demoProject.brief, title: "UI修复状态读取夹具" }, initialStages: [] },
  }));
  const run: PipelineRun = { ...demoRun, id: "ui-reading-run", projectId: project.id, failedStage: "scene_beats",
    failureCode: "validation.unit_quarantined", providerSnapshot: { textAuthMode: "none" } };
  let unit: RunProgressWorkUnit = { workUnitId: "ui-unit", stage: "scene_beats", sequence: 1, maxAttempts: 3,
    status: "quarantined", latestAttempt: null, sealed: false, repairEligible: false, repairReasonCode: "repair.snapshot_stale" };
  await installReads(page, project.id, () => run, () => progress(run, [unit]));
  const writes: string[] = [];
  page.on("request", request => { if (request.url().includes("/api/v2/") && request.method() !== "GET") writes.push(request.method()); });
  for (const [state, status, reason] of [["refused", "quarantined", "repair.snapshot_stale"], ["unknown", "outcome_unknown", "repair.target_outcome_unknown"]] as const) {
    const outcomeUnknown = status === "outcome_unknown";
    unit = { ...unit, status, repairReasonCode: reason, latestAttempt: {
      attemptId: "ui-attempt", attemptNumber: 1, attemptKind: "primary", sourceAttemptId: null, status: "failed",
      outcomeCode: outcomeUnknown ? "transport.outcome_unknown" : "validation.schema_invalid", outcomeUnknown,
      startedAt: "2026-10-08T00:00:00Z", finishedAt: "2026-10-08T00:00:02Z", durationMs: 2000, inputTokens: null, outputTokens: null,
    } };
    run.failureCode = unit.latestAttempt!.outcomeCode;
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=quarantine&run=${run.id}`);
    await expect(page.locator(".repair-panel .notice")).toContainText(reason);
    if (outcomeUnknown) await expect(page.locator(".repair-rebuild-separator")).toContainText("也可能重复生成");
    await expect(page.getByRole("button", { name: "重新执行此子任务", exact: true })).toHaveCount(0);
    await expect(page.locator(".quarantine-list")).toContainText(status === "outcome_unknown" ? "请求结果不确定" : "输出未通过校验（已隔离）");
    await capture(page, info, `repair-${state}-list`, page.locator(".quarantine-list > button").first());
    await capture(page, info, `repair-${state}-refusal`, page.locator(".repair-panel .notice"));
    await capture(page, info, `repair-${state}-rebuild`, page.locator(".repair-rebuild-separator"));
  }
  expect(writes).toEqual([]);
});
