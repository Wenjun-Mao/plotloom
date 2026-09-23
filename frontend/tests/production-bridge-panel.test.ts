import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ProductionBridgePanel } from "../src/pages/ProductionBridgePanel";
import type { ProductionBridgeState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

const state = (label: string, revision = 1, contentHash = "a".repeat(64), text = "", reviewState: "pending" | "author_saved" | "model_suggested" = "pending", modelSuggestion?: string): ProductionBridgeState => ({
  status: "ready", staleReasons: [], installedStageRevisions: null,
  proposal: {
    revision, contentHash, inputs: {}, scenes: [{ sceneId: `scene-${label}`, sectionId: label, episode: 1, sceneIndex: 1, cutCount: 1 }], cuts: [], conflicts: [], installable: reviewState !== "pending", preparedAt: "2026-09-22T00:00:00Z",
    intentPackage: { suggestionOrigin: reviewState === "model_suggested" || modelSuggestion ? "model_inference.v1" : "none", reviewState, provenance: reviewState === "model_suggested" || modelSuggestion ? { jobId: "fake-job" } : null, entries: [{ id: `entry-${label}`, targetKind: "scene_objective", targetId: `scene-${label}`, sourceCoordinates: { sectionId: label, episode: 1, sceneIndex: 1 }, sourceContentHash: "b".repeat(64), sourceExcerpt: `excerpt-${label}`, suggestedText: reviewState === "model_suggested" ? text : modelSuggestion ?? null, text }] },
  },
});

const render = async (projectId: string) => { await act(async () => root.render(createElement(ProductionBridgePanel, { projectId, readOnly: false }))); };
const settle = async () => { await act(async () => { await Promise.resolve(); }); };
const button = (text: string) => Array.from(host.querySelectorAll("button")).find((item) => item.textContent === text) as HTMLButtonElement;
const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => { resolve = resolvePromise; reject = rejectPromise; });
  return { promise, resolve, reject };
};

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

it("requires the displayed dramatic-intent package to be saved before accepting its exact new revision", async () => {
  const first = state("first");
  const saved = state("first", 2, "c".repeat(64), "author-reviewed objective", "author_saved");
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(first);
  const save = vi.spyOn(plotloomApi, "updateProductionBridgeIntent").mockResolvedValue(saved);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge").mockResolvedValue({ ...saved, status: "accepted", installedStageRevisions: { story_bible: 1, scene_beats: 1, storyboard: 1 } });

  await render("first"); await settle();
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  const valueSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
  await act(async () => { valueSetter?.call(textarea, "author-reviewed objective"); textarea.dispatchEvent(new Event("input", { bubbles: true })); });

  expect(button("确认投产提案").disabled).toBe(true);
  expect(host.textContent).toContain("当前编辑未保存");
  await act(async () => button("确认投产提案").click());
  expect(accept).not.toHaveBeenCalled();

  await act(async () => button("保存戏剧意图整包").click()); await settle();
  expect(save).toHaveBeenCalledWith("first", { expectedProposalRevision: 1, expectedContentHash: "a".repeat(64), entries: [{ id: "entry-first", text: "author-reviewed objective" }] });
  expect(button("确认投产提案").disabled).toBe(false);
  await act(async () => button("确认投产提案").click()); await settle();
  expect(accept).toHaveBeenCalledWith("first", { expectedProposalRevision: 2, expectedContentHash: "c".repeat(64) });
  expect(host.textContent).toContain("投产提案已确认");
  expect(host.textContent).toContain("确认后，将建立后续制作使用的场景与镜头数据；不会自动生成图片或视频。");
  expect(host.textContent).not.toContain("安装");
});

it("uses confirmation wording for proposal conflicts without changing their installability", async () => {
  const blocked = state("blocked");
  blocked.proposal!.installable = false;
  blocked.proposal!.conflicts = [{ code: "dramatic_intent_required", message: "不能安装：请先审阅戏剧意图", sectionId: null, episode: null, sceneIndex: null }];
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(blocked);

  await render("blocked"); await settle();

  expect(host.textContent).toContain("暂不能确认投产提案：请先审阅戏剧意图");
  expect(host.textContent).not.toContain("不能安装");
  expect(button("确认投产提案").disabled).toBe(true);
});

it("ignores a late successful GET from the prior project in the same mounted root", async () => {
  const prior = deferred<ProductionBridgeState>(); const current = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockImplementation((projectId) => projectId === "prior" ? prior.promise : current.promise);

  await render("prior"); await render("current");
  await act(async () => prior.resolve(state("prior"))); await settle();
  expect(host.textContent).not.toContain("excerpt-prior");
  await act(async () => current.resolve(state("current"))); await settle();
  expect(host.textContent).toContain("excerpt-current");
  expect(host.textContent).not.toContain("excerpt-prior");
});

it("shows a failed initial load and dispatches a genuine retry", async () => {
  const retry = deferred<ProductionBridgeState>();
  const get = vi.spyOn(plotloomApi, "getProductionBridge").mockRejectedValueOnce(new Error("GET failed")).mockReturnValueOnce(retry.promise);
  await render("first"); await settle();
  expect(get).toHaveBeenCalledWith("first", expect.any(AbortSignal));
  expect(host.textContent).toContain("GET failed");
  expect(host.textContent).not.toContain("正在加载");
  await act(async () => button("重试加载").click());
  expect(get).toHaveBeenCalledTimes(2);
  await act(async () => retry.resolve(state("first"))); await settle();
  expect(host.textContent).toContain("excerpt-first");
});

it("ignores a genuinely late rejected GET from the prior project", async () => {
  const prior = deferred<ProductionBridgeState>(); const current = deferred<ProductionBridgeState>();
  const get = vi.spyOn(plotloomApi, "getProductionBridge").mockImplementation((projectId) => projectId === "prior" ? prior.promise : current.promise);
  await render("prior");
  expect(get).toHaveBeenCalledWith("prior", expect.any(AbortSignal));
  await render("current");
  expect(get).toHaveBeenCalledWith("current", expect.any(AbortSignal));
  await act(async () => prior.reject(new Error("late prior GET"))); await settle();
  await act(async () => current.resolve(state("current"))); await settle();
  expect(host.textContent).toContain("excerpt-current");
  expect(host.textContent).not.toContain("late prior GET");
});

it("ignores a late mutation from the prior project", async () => {
  const priorGet = deferred<ProductionBridgeState>(); const currentGet = deferred<ProductionBridgeState>(); const priorPrepare = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockImplementation((projectId) => projectId === "prior" ? priorGet.promise : currentGet.promise);
  vi.spyOn(plotloomApi, "prepareProductionBridge").mockReturnValue(priorPrepare.promise);

  await render("prior");
  await act(async () => priorGet.resolve({ status: "missing", staleReasons: [], installedStageRevisions: null, proposal: null })); await settle();
  await act(async () => button("准备投产提案").click());
  await render("current");
  await act(async () => { priorPrepare.resolve(state("prior")); currentGet.resolve(state("current")); }); await settle();

  expect(host.textContent).toContain("excerpt-current");
  expect(host.textContent).not.toContain("excerpt-prior");
});

it("invalidates a pending GET and mutation when unmounted", async () => {
  const get = deferred<ProductionBridgeState>();
  const getSpy = vi.spyOn(plotloomApi, "getProductionBridge").mockReturnValue(get.promise);
  await render("prior");
  expect(getSpy).toHaveBeenCalledWith("prior", expect.any(AbortSignal));
  await act(async () => root.unmount());
  await act(async () => get.reject(new Error("after unmount"))); await settle();
  expect(host.textContent).toBe("");

  root = createRoot(host);
  getSpy.mockResolvedValue(state("prior"));
  const save = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "updateProductionBridgeIntent").mockReturnValue(save.promise);
  await render("prior"); await settle();
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  const valueSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
  await act(async () => { valueSetter?.call(textarea, "edited"); textarea.dispatchEvent(new Event("input", { bubbles: true })); });
  await act(async () => button("保存戏剧意图整包").click());
  await act(async () => root.unmount());
  await act(async () => save.reject(new Error("mutation after unmount"))); await settle();
  expect(host.textContent).toBe("");
  root = createRoot(host);
});

it("preserves an unsaved draft when model completion arrives late", async () => {
  vi.useFakeTimers();
  try {
    const pending = state("prior");
    pending.intentJob = {
      id: "job-1", status: "dispatched", proposalRevision: 1, proposalContentHash: pending.proposal!.contentHash,
      profileId: "fake", profileVersion: 1, promptVersion: "1.0.0",
      createdAt: "2026-09-22T00:00:00Z", updatedAt: "2026-09-22T00:00:00Z",
      errorCode: null, errorMessage: null, resultProposalRevision: null, providerRequestId: null, responseHash: null,
    };
    const inferred = state("prior", 2, "c".repeat(64), "模型推断的目的", "model_suggested");
    inferred.intentJob = { ...pending.intentJob, status: "ready", resultProposalRevision: 2 };
    vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(pending).mockResolvedValueOnce(inferred);
    await render("prior"); await settle();
    const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
    const valueSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
    await act(async () => { valueSetter?.call(textarea, "我尚未保存的目的"); textarea.dispatchEvent(new Event("input", { bubbles: true })); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1600); }); await settle();
    expect((host.querySelector("textarea") as HTMLTextAreaElement).value).toBe("我尚未保存的目的");
    expect(host.textContent).toContain("未保存的本地编辑仍在此保留");
    expect(button("确认投产提案").disabled).toBe(true);
    await act(async () => button("载入新提案并放弃本地编辑").click());
    expect((host.querySelector("textarea") as HTMLTextAreaElement).value).toBe("模型推断的目的");
  } finally {
    vi.useRealTimers();
  }
});

it("keeps accepted model origin distinct from source evidence after author review", async () => {
  const accepted = state("first", 5, "d".repeat(64), "作者修订的目的", "author_saved", "模型原始目的");
  accepted.status = "accepted";
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(accepted);
  await render("first"); await settle();
  expect(host.textContent).toContain("来源摘录：excerpt-first");
  expect(host.textContent).toContain("模型原始建议：模型原始目的");
  expect(host.textContent).toContain("作者修订的目的");
  expect(host.textContent).not.toContain("来源摘录：模型原始目的");
});

it("shows the server-owned simulation warning without a URL flag", async () => {
  const preview = state("first");
  preview.simulationLabel = "模拟数据 · 假模型演示";
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(preview);
  await render("first"); await settle();
  expect(host.querySelector('[data-testid="bridge-fake-banner"]')?.textContent).toBe(preview.simulationLabel);
});
