import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import type { H3PromptPreview, H3ReviewedDirections, VideoJobPrepareBody } from "../src/api";
import { H3DirectionsReview } from "../src/h3-directions-review";
import { batchApi } from "../src/features/video-batch/api";
import { projectQaApi } from "../src/components/ProjectQaContext";
import type { Batch } from "../src/features/video-batch/contracts";
import { authorizeProductionBatch, productionBatch, readyProductionBatch, sourceHash } from "./h3-production-fixtures";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root, host: HTMLDivElement, current: Batch | null;
const pending = <T,>() => { let resolve!: (value: T) => void; let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const source = (hash = sourceHash): H3PromptPreview => ({ sourceHash: hash, compiledPrompt: null,
  sources: [{ path: "shot.action", text: "守灯人把保险丝放回原处。", label: "动作" }] });
const button = (name: string) => [...host.querySelectorAll("button")].find(item => item.textContent === name)!;
const seedInput = () => host.querySelector('input[aria-label="H3 随机种子"]') as HTMLInputElement;
const input = async (element: HTMLInputElement | HTMLTextAreaElement, value: string) => { await act(async () => {
  Object.getOwnPropertyDescriptor(element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, "value")!.set!.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
}); };
const buildRequest = (seed: number, idempotencyKey: string): VideoJobPrepareBody => ({ approvalId: "approval", shotId: "shot", storyboardRevision: 1,
  expectedSelectionRevision: 1, idempotencyKey, seed, profileId: "h3_vertical_8", requestedDurationSeconds: 15,
  playbackIntent: "segment_required", resolution: "576x1024", audio: true, aspectPolicy: "cover_center_crop", allowCenterCrop: true });
const render = async (identity = "shot", onFreeze: (value: H3ReviewedDirections, seed: number, key: string) => Promise<void> = async () => {}, sourceReady = true, disabled = false) => {
  await act(async () => root.render(createElement(H3DirectionsReview, { projectId: "project", shotId: "shot", sourceIdentity: identity,
    sourceReady, disabled, buildRequest, onFreeze, keyframeHash: "a".repeat(64), quality: 8, requestedSeconds: 15, frameCount: 362 })));
};
beforeEach(() => {
  current = null; host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(projectQaApi, "current").mockResolvedValue({ eligible: false, required: false, attribution: null });
  vi.spyOn(plotloomApi, "previewH3Prompt").mockResolvedValue(source());
  vi.spyOn(batchApi, "current").mockImplementation(async () => current);
  vi.spyOn(batchApi, "command").mockImplementation(async (_project, name, body) => {
    if (name === "setup") current = productionBatch((body as { singleRequest: VideoJobPrepareBody }).singleRequest);
    if (name === "draft" || name === "check" || name === "directions") current = { ...current!, revision: current!.revision + 1, state: "checking" };
    if (name === "start") current = authorizeProductionBatch(current!);
    return current!;
  });
});
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });
const load = async () => { await act(async () => button("读取当前来源").click()); };
const setup = async () => { await load(); await act(async () => button("准备本镜头制作简报").click()); };
const ready = async () => { await setup(); current = readyProductionBatch(current!.manifest.setup.singleRequest!); await load(); };

it("binds single setup to every original setting and authorizes the complete brief after independent checking", async () => {
  const freeze = vi.fn(async () => {}); await render("shot", freeze); await input(seedInput(), "2325339575976657"); await setup();
  const body = vi.mocked(batchApi.command).mock.calls[0][2] as { singleRequest: VideoJobPrepareBody; shotIds: string[] };
  expect(body.shotIds).toEqual(["shot"]); expect(body.singleRequest).toEqual({ ...buildRequest(2325339575976657, body.singleRequest.idempotencyKey), automaticRetryLimit: 1 });
  expect(body.singleRequest).not.toHaveProperty("reviewedDirections");
  expect(button("授权本镜头制作意图并开始生成").disabled).toBe(true);
  await act(async () => button("用助手起草并独立检查指令").click());
  expect(current?.state).toBe("checking"); expect(freeze).not.toHaveBeenCalled();
  current = readyProductionBatch(body.singleRequest); await load();
  expect(host.querySelector(".production-brief-review")?.textContent).toContain("守灯人把保险丝放回原处");
  expect(host.textContent).toContain("独立助手保真检查已通过");
  expect(host.textContent).not.toContain("我已核对英文");
  expect(host.querySelector("pre")?.closest("details")?.open).toBe(false);
  await act(async () => button("授权本镜头制作意图并开始生成").click());
  expect(batchApi.command).toHaveBeenLastCalledWith("project", "start", { expectedRevision: 3, manifestHash: current!.manifestHash, basis: "production-intent.v2" });
  expect(freeze).toHaveBeenCalledExactlyOnceWith(current!.authorizedDirections!.shot, 2325339575976657, body.singleRequest.idempotencyKey);
});

it("refuses an unrelated active batch without changing its setup or request identity", async () => {
  current = productionBatch(buildRequest(100, "unrelated-request"));
  await render(); await load();
  expect(host.textContent).toContain("另一个批次尚未结束"); expect(button("准备本镜头制作简报").disabled).toBe(true);
  expect(batchApi.command).not.toHaveBeenCalled();
});

it("preserves the exact request key through safe rereads and changes it only for an explicit changed seed", async () => {
  await render(); await input(seedInput(), "00042"); await load(); const first = vi.mocked(plotloomApi.previewH3Prompt).mock.calls[0][1];
  await load(); expect(vi.mocked(plotloomApi.previewH3Prompt).mock.calls[1][1]).toEqual(first);
  await input(seedInput(), "43"); await load(); const changed = vi.mocked(plotloomApi.previewH3Prompt).mock.calls[2][1];
  expect(changed.seed).toBe(43); expect(changed.idempotencyKey).not.toBe(first.idempotencyKey);
});

it("a rejected translation is actionable; editing invalidates authorization and queues a fresh checker", async () => {
  await render(); await ready(); current!.state = "translation_rejected";
  current!.manifest.targets[0].fidelity = { verdict: "reject", checkedPaths: [], checkedDimensions: [], findings: [{ code: "negation", path: "shot.action", message: "遗漏了不得新增对白的约束。" }] };
  await load(); expect(host.textContent).toContain("遗漏了不得新增对白"); expect(button("授权本镜头制作意图并开始生成").disabled).toBe(true);
  await input(host.querySelector("textarea")!, "The keeper carefully puts the fuse back. Add no speech.");
  await act(async () => button("保存候选并由助手重新检查").click());
  expect(batchApi.command).toHaveBeenLastCalledWith("project", "directions", expect.objectContaining({ expectedRevision: 3 }));
  expect(current?.state).toBe("checking"); expect(button("授权本镜头制作意图并开始生成").disabled).toBe(true);
});

it.each(["", "-1", "1.5", "1e3", "9007199254740992", " 42 "])("rejects invalid or lossy seed %j before any source read", async value => {
  await render(); await input(seedInput(), value); expect(seedInput().getAttribute("aria-invalid")).toBe("true");
  expect(button("读取当前来源").disabled).toBe(true); expect(plotloomApi.previewH3Prompt).not.toHaveBeenCalled();
});
it.each(["0", "9007199254740991"])("preserves valid seed boundary %s", async value => {
  await render(); await input(seedInput(), value); await load(); expect(vi.mocked(plotloomApi.previewH3Prompt).mock.calls[0][1].seed).toBe(Number(value));
});

it("discards late source success and failure across identity changes", async () => {
  const old = pending<H3PromptPreview>(); vi.mocked(plotloomApi.previewH3Prompt).mockReturnValueOnce(old.promise);
  await render("old"); await act(async () => button("读取当前来源").click()); expect(seedInput().disabled).toBe(true);
  await render("new"); await act(async () => old.resolve(source("f".repeat(64))));
  expect(host.querySelector('[data-testid="h3-frozen-review-inputs"]')).toBeNull(); expect(seedInput().disabled).toBe(false);
  const rejection = pending<H3PromptPreview>(); vi.mocked(plotloomApi.previewH3Prompt).mockReturnValueOnce(rejection.promise);
  await act(async () => button("读取当前来源").click()); await render("third"); await act(async () => rejection.reject(new Error("obsolete")));
  expect(host.textContent).not.toContain("obsolete");
});

it("unknown media withdraws authorization while preserving seed and edited candidate", async () => {
  const freeze = vi.fn(); await render("shot", freeze); await input(seedInput(), "42"); await ready();
  await input(host.querySelector("textarea")!, "unfinished faithful candidate"); await render("shot", freeze, false);
  expect(seedInput().value).toBe("42"); expect((host.querySelector("textarea") as HTMLTextAreaElement).value).toBe("unfinished faithful candidate");
  expect(button("授权本镜头制作意图并开始生成").disabled).toBe(true); expect(freeze).not.toHaveBeenCalled();
});

it("a lost start response requires readback and never automatically resubmits authorization", async () => {
  const freeze = vi.fn(); await render("shot", freeze); await ready();
  vi.mocked(batchApi.command).mockImplementationOnce(async () => { current = authorizeProductionBatch(current!); throw new Error("response lost"); });
  await act(async () => button("授权本镜头制作意图并开始生成").click());
  expect(host.textContent).toContain("不会重放请求"); expect(freeze).not.toHaveBeenCalled();
  const calls = vi.mocked(batchApi.command).mock.calls.length; await load();
  await act(async () => button("读取本次已授权原任务").click());
  expect(batchApi.command).toHaveBeenCalledTimes(calls); expect(freeze).toHaveBeenCalledOnce();
});

it("never falls back to creator authorization when required QA context is unavailable", async () => {
  vi.mocked(projectQaApi.current).mockResolvedValue({ required: true, eligible: false, attribution: null });
  const freeze = vi.fn(); await render("shot", freeze); await ready();
  expect(button("授权本镜头制作意图并开始生成").disabled).toBe(true); expect(host.textContent).toContain("不能改为创作者确认"); expect(freeze).not.toHaveBeenCalled();
});

it("persists raw seed, exact original key and unfinished English without restoring authorization", async () => {
  const { ReviewDraftContext } = await import("../src/features/authoring/ReviewDraftContext");
  const { createReviewDraftStore } = await import("../src/features/authoring/reviewDraftStore");
  const { createProjectDraftQuiescence } = await import("../src/features/authoring/projectDraftQuiescence");
  const q = createProjectDraftQuiescence(), store = createReviewDraftStore(q, localStorage), freeze = vi.fn();
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockImplementation(async (_project, request) => ({ projectId: "project", ...request, draftRevision: request.expectedDraftRevision + 1, updatedAt: "now" }));
  const mount = async () => act(async () => root.render(createElement(ReviewDraftContext.Provider, { value: { store, quiescence: q, projectId: "project", revision: 1, enabled: true },
    children: createElement(H3DirectionsReview, { projectId: "project", shotId: "shot", sourceIdentity: "exact-source", sourceReady: true, disabled: false, buildRequest, onFreeze: freeze,
      keyframeHash: "a".repeat(64), quality: 8, requestedSeconds: 15, frameCount: 362 }) })));
  await mount(); await input(seedInput(), "00042"); await ready();
  const key = current!.manifest.setup.singleRequest!.idempotencyKey;
  await input(host.querySelector("textarea")!, "unfinished English {\n");
  await act(async () => { expect(await q.flush("project")).toBe(true); });
  await act(async () => root.render(null)); await mount();
  expect(seedInput().value).toBe("00042"); await load();
  expect((host.querySelector("textarea") as HTMLTextAreaElement).value).toBe("unfinished English {\n");
  expect(vi.mocked(plotloomApi.previewH3Prompt).mock.calls.at(-1)?.[1].idempotencyKey).toBe(key);
  expect(button("授权本镜头制作意图并开始生成").disabled).toBe(true); expect(freeze).not.toHaveBeenCalled();
});

it("keeps stale draft input protected across changed source ownership", async () => {
  const { ReviewDraftContext } = await import("../src/features/authoring/ReviewDraftContext");
  const { createReviewDraftStore } = await import("../src/features/authoring/reviewDraftStore");
  const { createProjectDraftQuiescence } = await import("../src/features/authoring/projectDraftQuiescence");
  const q = createProjectDraftQuiescence(), store = createReviewDraftStore(q, localStorage);
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockImplementation(async (_project, request) => ({ projectId: "project", ...request, draftRevision: request.expectedDraftRevision + 1, updatedAt: "now" }));
  const mount = async (identity: string) => act(async () => root.render(createElement(ReviewDraftContext.Provider, { value: { store, quiescence: q, projectId: "project", revision: 1, enabled: true },
    children: createElement(H3DirectionsReview, { projectId: "project", shotId: "shot", sourceIdentity: identity, sourceReady: true, disabled: false, buildRequest, onFreeze: async () => {},
      keyframeHash: "a".repeat(64), quality: 8, requestedSeconds: 15, frameCount: 362 }) })));
  await mount("source A"); await input(seedInput(), "00042"); await act(async () => { expect(await q.flush("project")).toBe(true); });
  const original = store.get("project", "h3_directions", "shot")!.payload;
  await mount("source B"); expect(seedInput().disabled).toBe(true); expect(button("读取当前来源").disabled).toBe(true);
  await act(async () => { expect(store.update("project", "h3_directions", 1, "source B", "visible race input B", "shot")).toBe(false); });
  expect(store.get("project", "h3_directions", "shot")!.payload).toEqual(original);
  await act(async () => { expect(await q.preserve("project")).toBe(false); }); expect(host.textContent).toContain("visible race input B");
});

it("late authorization after an owner change cannot freeze a different shot", async () => {
  const freeze = vi.fn(); await render("old", freeze); await ready();
  const late = pending<Batch>(); vi.mocked(batchApi.command).mockReturnValueOnce(late.promise);
  await act(async () => button("授权本镜头制作意图并开始生成").click());
  await render("new", freeze); await act(async () => late.resolve(authorizeProductionBatch(current!)));
  expect(freeze).not.toHaveBeenCalled(); expect(seedInput().disabled).toBe(false);
});


it("withdraws a late authorization callback when authoring becomes disabled", async () => {
  const freeze = vi.fn(); await render("shot", freeze); await ready();
  const late = pending<Batch>(); vi.mocked(batchApi.command).mockReturnValueOnce(late.promise);
  await act(async () => button("授权本镜头制作意图并开始生成").click());
  await render("shot", freeze, true, true); await act(async () => late.resolve(authorizeProductionBatch(current!)));
  expect(freeze).not.toHaveBeenCalled(); expect(button("读取当前来源").disabled).toBe(true);
});

it("a new take requires an explicit settled predecessor and preserves seed/settings with a fresh request key", async () => {
  await render(); await input(seedInput(), "42"); await ready();
  const original = current!.manifest.setup.singleRequest!; current!.state = "cancelled"; await load();
  await act(async () => button("保留设置并准备新的原片候选").click());
  expect(seedInput().value).toBe("42"); await load(); await act(async () => button("准备本镜头制作简报").click());
  const next = current!.manifest.setup.singleRequest!;
  expect(next).toEqual({ ...original, idempotencyKey: expect.any(String) }); expect(next.idempotencyKey).not.toBe(original.idempotencyKey);
});

it("changing automatic retry authority invalidates the old single-shot authorization", async () => {
  const freeze = vi.fn(async () => {}); await render("shot", freeze); await ready();
  const original = current!.manifest.setup.singleRequest!;
  await input(host.querySelector<HTMLInputElement>('input[type="number"]')!, "0");
  expect(host.textContent).toContain("请重新读取并核验当前来源");
  expect(freeze).not.toHaveBeenCalled();
  await load();
  const changed = vi.mocked(plotloomApi.previewH3Prompt).mock.calls.at(-1)![1];
  expect(changed.automaticRetryLimit).toBe(0);
  expect(changed.seed).toBe(original.seed);
  expect(changed.idempotencyKey).not.toBe(original.idempotencyKey);
  expect(button("授权本镜头制作意图并开始生成")).toBeUndefined();
  expect(vi.mocked(batchApi.command).mock.calls.filter(call => call[1] === "start")).toHaveLength(0);
});

it("manually retries only the exact exhausted native child of the current single-shot request", async () => {
  await render(); await setup();
  const original = current!.manifest.setup.singleRequest!;
  current = { ...current!, state: "blocked", revision: 5, execution: { ...current!.execution, draft: { retry: {
    retryCount: 1, automaticRetriesUsed: 1, automaticRetryLimit: 1, currentJobId: "failed-native", currentAttemptId: "failed-attempt",
    predecessorJobIds: ["initial-native"], state: "exhausted", possiblePriorCost: true,
  } } } };
  await load(); const before = vi.mocked(batchApi.command).mock.calls.length;
  const prior = vi.mocked(batchApi.command).getMockImplementation()!;
  vi.mocked(batchApi.command).mockImplementation(async (project, name, body) => {
    if (name !== "retry-execution") return prior(project, name, body);
    current = { ...current!, state: "drafting", revision: 6, execution: { ...current!.execution, draft: { retry: {
      ...current!.execution.draft!.retry!, retryCount: 2, currentJobId: "manual-successor", currentAttemptId: "manual-attempt", state: "running",
    } } } }; return current;
  });
  await act(async () => button("手动重试此任务").click());
  expect(batchApi.command).toHaveBeenLastCalledWith("project", "retry-execution", { commandId: expect.any(String), expectedRevision: 5, failedJobId: "failed-native", failedAttemptId: "failed-attempt" });
  expect(vi.mocked(batchApi.command).mock.calls).toHaveLength(before + 1);
  expect(current!.manifest.setup.singleRequest).toEqual(original);
  expect(current!.execution.draft!.retry!.automaticRetriesUsed).toBe(1);
  expect(current!.execution.draft!.retry!.automaticRetryLimit).toBe(1);
});
