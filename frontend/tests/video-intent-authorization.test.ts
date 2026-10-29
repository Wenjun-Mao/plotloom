import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { batchApi } from "../src/features/video-batch/api";
import { VideoBatchReview } from "../src/features/video-batch/VideoBatchReview";
import { VideoBatchPanel } from "../src/features/video-batch/VideoBatchPanel";
import { plotloomApi, type VideoJobPrepareBody } from "../src/api";
import { projectQaApi } from "../src/components/ProjectQaContext";
import { canAuthorizeBatch } from "../src/features/video-batch/production-review";
import { authorizedSingleDirections, matchesSingleRequest } from "../src/features/video-batch/single-request";
import { authorizeProductionBatch, readyProductionBatch, sourceHash } from "./h3-production-fixtures";
import type { Batch } from "../src/features/video-batch/contracts";

let root: Root, host: HTMLDivElement;
const request: VideoJobPrepareBody = { approvalId: "approval", shotId: "shot", storyboardRevision: 1, expectedSelectionRevision: 1,
  seed: 42, idempotencyKey: "exact-original-key", profileId: "h3_vertical_8", requestedDurationSeconds: 15,
  playbackIntent: "segment_required", aspectPolicy: "cover_center_crop", allowCenterCrop: true };
const button = (name: string) => [...host.querySelectorAll("button")].find(node => node.textContent === name)!;
beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(projectQaApi, "current").mockResolvedValue({ eligible: false, required: false, attribution: null });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false } as never);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });
const render = async (batch: Batch) => { vi.spyOn(batchApi, "current").mockResolvedValue(batch);
  await act(async () => root.render(createElement(VideoBatchPanel, { projectId: "project", disabled: false, dirty: false }))); };

it("batch Start authorizes complete production intent with truthful independent assistant checking", async () => {
  const batch = readyProductionBatch(request); delete batch.manifest.setup.singleRequest; delete batch.manifest.setup.shotIds;
  const send = vi.spyOn(batchApi, "command").mockResolvedValue(authorizeProductionBatch(batch)); await render(batch);
  const brief = host.querySelector('.production-brief-review')!;
  expect(brief.querySelectorAll("dl")).toHaveLength(6); expect(brief.textContent).toContain("独立助手保真检查已通过");
  expect([...brief.querySelectorAll("pre")].every(pre => !!pre.closest("details"))).toBe(true);
  expect(host.textContent).not.toContain("我已核对英文");
  await act(async () => button("授权全部制作意图并开始生成").click());
  expect(send).toHaveBeenCalledExactlyOnceWith("project", "start", { expectedRevision: 3, manifestHash: batch.manifestHash, basis: "production-intent.v2" });
  expect(host.querySelector("video")).toBeNull(); expect(host.textContent).not.toContain("全部视频已保存审阅确认");
});

it.each(["checking", "translation_rejected", "stale"])("keeps %s distinct from consent and media acceptance", async state => {
  const batch = readyProductionBatch(request); batch.state = state;
  batch.manifest.targets[0].fidelity = { verdict: "reject", checkedPaths: [], checkedDimensions: [], findings: [{ path: "directions.fields.0.english", code: "extra_speech", message: "新增了来源没有的对白。", sourcePath: "shot.action", sourceOwner: "镜头编辑" }] };
  await render(batch); expect(host.textContent).toContain("新增了来源没有的对白"); expect(host.textContent).toContain("镜头编辑");
  expect(button("授权全部制作意图并开始生成")).toBeUndefined(); expect(canAuthorizeBatch(batch)).toBe(false);
});

it("refuses a merely schema-valid candidate or incomplete readable brief", () => {
  const batch = readyProductionBatch(request);
  delete batch.manifest.targets[0].fidelity; expect(canAuthorizeBatch(batch)).toBe(false);
  const complete = readyProductionBatch(request); complete.manifest.targets[0].productionBrief!.sections.pop(); expect(canAuthorizeBatch(complete)).toBe(false);
  const conflict = readyProductionBatch(request); conflict.manifest.targets[0].productionBrief!.conflicts.push({ path: "shot.unrepresented", owner: "镜头编辑", message: "请回到镜头来源补充可读表达。" });
  expect(canAuthorizeBatch(conflict)).toBe(false);
});

it.each(["seed", "idempotencyKey", "playbackIntent", "requestedDurationSeconds", "aspectPolicy", "approvalId", "expectedSelectionRevision"] as const)(
  "never resumes a single scoped batch with changed %s", field => {
    const batch = readyProductionBatch(request); expect(matchesSingleRequest(batch, request, sourceHash)).toBe(true);
    const changed = { ...request, [field]: typeof request[field] === "number" ? Number(request[field]) + 1 : "different" };
    expect(matchesSingleRequest(batch, changed as VideoJobPrepareBody, sourceHash)).toBe(false);
  });

it("accepts explicit server defaults without dropping original identity or allowing another target", () => {
  const batch = readyProductionBatch(request);
  Object.assign(batch.manifest.setup.singleRequest!, { audio: null, resolution: null, allowLetterbox: false, reviewedDirections: null });
  expect(matchesSingleRequest(batch, request, sourceHash)).toBe(true);
  batch.manifest.scopeShotIds.push("other"); expect(matchesSingleRequest(batch, request, sourceHash)).toBe(false);
});

it("reads authority only from exact saved authorization, not from a fidelity pass alone", () => {
  const batch = readyProductionBatch(request); expect(authorizedSingleDirections(batch, request, sourceHash)).toBeNull();
  const authorized = authorizeProductionBatch(batch); expect(authorizedSingleDirections(authorized, request, sourceHash)).toBeTruthy();
  authorized.authorizedDirections!.shot.intentAuthorization.briefHash = "f".repeat(64); expect(authorizedSingleDirections(authorized, request, sourceHash)).toBeNull();
});


it("a whole-pack review cannot adopt a different current batch returned during a race", async () => {
  const batch = readyProductionBatch(request);
  vi.spyOn(batchApi, "review").mockResolvedValue({ batchId: "other", reviewHash: "f".repeat(64), ready: true, readyCount: 0, blockedCount: 0, kept: [], errors: [], proposals: [] });
  const save = vi.spyOn(batchApi, "confirmPack");
  await act(async () => root.render(createElement(VideoBatchReview, { projectId: "project", batch, disabled: false, onClose: vi.fn(), onSaved: vi.fn() })));
  expect(host.textContent).toContain("当前视频清单已变化");
  expect(button("确认全部视频并用于故事")).toBeUndefined(); expect(save).not.toHaveBeenCalled();
});

it("functional QA retains explicit quality limits and cannot present them as a quality pass", async () => {
  const batch = readyProductionBatch(request);
  vi.spyOn(batchApi, "review").mockResolvedValue({ batchId: batch.id, reviewHash: "f".repeat(64), ready: true,
    acceptanceBasis: "functional_workflow_only", readyCount: 0, blockedCount: 0, kept: [], errors: [], proposals: [] });
  const save = vi.spyOn(batchApi, "confirmPack").mockResolvedValue({ id: "functional-receipt" });
  const actor = { kind: "agent_operated_qa" as const, scopeId: "synthetic-functional-scope" };
  await act(async () => root.render(createElement(VideoBatchReview, { projectId: "project", batch, actor,
    disabled: false, onClose: vi.fn(), onSaved: vi.fn() })));
  expect(host.textContent).toContain("不代表画面、文字或媒体创作质量通过");
  expect(button("确认全部视频并用于故事")).toBeUndefined();
  expect(save).not.toHaveBeenCalled();
  const fields = host.querySelectorAll<HTMLTextAreaElement>('[aria-label="代理 QA 实际观察"] textarea');
  async function fill(index: number, text: string) {
    await act(async () => { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(fields[index], text);
      fields[index].dispatchEvent(new Event("input", { bubbles: true })); });
  }
  await fill(0, "实际片段可播放，画面文字不清晰。");
  await fill(1, "机器音轨与 ASR 检查；未直接聆听。");
  await fill(2, "retained-frame-and-asr-evidence");
  expect(button("确认功能流程并用于故事").disabled).toBe(true);
  await fill(3, "画面文字无法验证\n姿态保留问题");
  await act(async () => button("确认功能流程并用于故事").click());
  expect(save).toHaveBeenCalledExactlyOnceWith("project", expect.objectContaining({ attribution: actor,
    inspection: expect.objectContaining({ acceptanceBasis: "functional_workflow_only",
      qualityLimitations: ["画面文字无法验证", "姿态保留问题"] }) }));
});


it("keeps automatic retry authority in the exact single-request identity", () => {
  const batch = readyProductionBatch(request);
  batch.manifest.setup.shotIds = [request.shotId];
  batch.manifest.scopeShotIds = [request.shotId];
  batch.manifest.targets = [{ ...batch.manifest.targets[0], shotId: request.shotId }];
  batch.manifest.setup.singleRequest = { ...request, automaticRetryLimit: 1 };
  expect(matchesSingleRequest(batch, { ...request, automaticRetryLimit: 1 }, sourceHash)).toBe(true);
  expect(matchesSingleRequest(batch, { ...request, automaticRetryLimit: 0 }, sourceHash)).toBe(false);
  expect(matchesSingleRequest(batch, request, sourceHash)).toBe(false);
  delete batch.manifest.setup.singleRequest.automaticRetryLimit;
  expect(matchesSingleRequest(batch, { ...request, automaticRetryLimit: 1 }, sourceHash)).toBe(false);
});

it("batch manual retry uses the current batch revision and exact exhausted native attempt", async () => {
  const batch = readyProductionBatch(request); batch.state = "blocked";
  batch.execution.draft = { retry: { retryCount: 1, automaticRetriesUsed: 1, automaticRetryLimit: 1, currentJobId: "draft-failed", currentAttemptId: "draft-attempt", predecessorJobIds: [], state: "exhausted", possiblePriorCost: true } };
  const successor = { ...batch, revision: batch.revision + 1, execution: { ...batch.execution, draft: { retry: { ...batch.execution.draft.retry!, retryCount: 2, currentJobId: "draft-next", currentAttemptId: "attempt-next", state: "running" as const } } } };
  const post = vi.spyOn(batchApi, "command").mockResolvedValue(successor);
  await render(batch); expect(post).not.toHaveBeenCalled();
  await act(async () => button("手动重试此任务").click());
  expect(post).toHaveBeenCalledWith("project", "retry-execution", { commandId: expect.any(String), expectedRevision: batch.revision, failedJobId: "draft-failed", failedAttemptId: "draft-attempt" });
  expect(host.querySelectorAll('[aria-label="手动重试此失败任务"]')).toHaveLength(0);
  expect(host.textContent).toContain("另有 1 次手动重试");
});
