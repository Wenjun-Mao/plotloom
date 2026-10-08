import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ProductionBridgePanel } from "../src/pages/ProductionBridgePanel";
import type { ProductionBridgeState } from "../src/types";
import { bridgeState, installedProduction, prepareRequest, replacementTarget } from "./production-bridge-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

const state = (label: string, revision = 1, contentHash = "a".repeat(64), text = "", reviewState: "pending" | "author_saved" | "model_suggested" = "pending", modelSuggestion?: string): ProductionBridgeState => bridgeState({
  status: "ready", preparation: { status: "available", request: prepareRequest({ expectedProposalRevision: revision, expectedProposalContentHash: contentHash }) },
  proposal: {
    replacementTarget: replacementTarget(),
    presentation: { version: 1, reviewed: true, sourceHash: "f".repeat(64), sources: [], runtimeChoice: { choices: [] }, frozenEvidence: {} },
    revision, contentHash, inputs: {}, scenes: [{ sceneId: `scene-${label}`, sectionId: label, episode: 1, sceneIndex: 1, cutCount: 1 }], cuts: [], conflicts: [], advisories: [], installable: reviewState !== "pending", preparedAt: "2026-09-22T00:00:00Z",
    intentPackage: { suggestionOrigin: reviewState === "model_suggested" || modelSuggestion ? "model_inference.v1" : "none", reviewState, provenance: reviewState === "model_suggested" || modelSuggestion ? { jobId: "fake-job" } : null, entries: [{ id: `entry-${label}`, targetKind: "scene_objective", targetId: `scene-${label}`, sourceCoordinates: { sectionId: label, episode: 1, sceneIndex: 1 }, sourceContentHash: "b".repeat(64), sourceExcerpt: `excerpt-${label}`, suggestedText: reviewState === "model_suggested" ? text : modelSuggestion ?? null, text }] },
  },
});

const render = async (projectId: string, onOpenShot?: (shotId: string) => void, onInstalled: (projectId: string) => Promise<void> = async () => undefined) => { await act(async () => root.render(createElement(ProductionBridgePanel, { projectId, readOnly: false, onOpenShot, onInstalled }))); };
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

it("shows an advisory shot-count notice without a blocking conflict", async () => {
  const current = state("advisory", 2, "b".repeat(64), "reviewed intent", "author_saved");
  current.proposal!.advisories = [{ code: "shot_count_preference", message: "创作提示：9 个镜头超出偏好 2–4 个；此项不阻止确认", sectionId: "advisory", episode: 1, sceneIndex: 1 }];
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(current);
  await render("advisory"); await settle();
  expect(host.textContent).toContain("此项不阻止确认");
  expect(button("确认投产提案").disabled).toBe(false);
});

it.each([{ reasons: [] }, { reasons: ["the accepted F5 storyboard review is stale", "unknown <probe> changed"] }])("uses typed stale guidance and retains literal diagnostics: %j", async ({ reasons }) => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue({ ...state("stale"), status: "stale", staleReasons: reasons, installation: installedProduction({ status: "outdated" }), preparation: { status: "unavailable", reason: "current accepted source is required" } });
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge");
  const generate = vi.spyOn(plotloomApi, "generateProductionBridgeIntent");
  await render("stale"); await settle();
  const banner = host.querySelector(".notice.warning")!;
  expect(banner.textContent).toContain("故事来源或制作版本已变化");
  expect(banner.textContent).toContain("再准备新提案并重新审阅");
  expect(banner.textContent).toContain("旧提案与已有媒体仍保留");
  expect(banner.textContent).toContain("不会自动覆盖内容或生成媒体");
  const technical = Array.from(host.querySelectorAll("details")).find(item => item.querySelector("summary")?.textContent === "技术详情（版本、来源与冻结输入）")!;
  for (const reason of reasons) {
    expect(banner.textContent).not.toContain(reason);
    expect(technical.textContent).toContain(reason);
  }
  expect(technical.open).toBe(false); expect(technical.querySelector("probe")).toBeNull();
  expect(button("准备重建提案").disabled).toBe(true);
  expect((host.querySelector(".bridge-intent-field textarea") as HTMLTextAreaElement).disabled).toBe(true);
  expect(button("保存戏剧意图整包").disabled).toBe(true);
  expect(prepare).not.toHaveBeenCalled(); expect(generate).not.toHaveBeenCalled();
});

it.each(["ready", "accepted"] as const)("does not invent stale guidance for %s state", async status => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue({ ...state(status), status });
  await render(status); await settle();
  expect(host.textContent).not.toContain("故事来源或制作版本已变化");
  expect(host.textContent).not.toContain("来源过期诊断（原文）");
  expect(host.textContent).toContain(status === "accepted"
    ? "场景与镜头数据已建立；此次确认不会自动生成图片或视频。"
    : "确认投产后，会建立后续制作使用的场景与镜头数据；不会自动生成图片或视频。");
  expect(host.textContent).not.toContain("确认后，将建立后续制作使用的场景与镜头数据");
});

it("disables unavailable inference without dispatch while preserving authored intent save", async () => {
  const unavailable = state("author"); unavailable.intentGeneration = { status: "unavailable", reason: "not_configured" };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(unavailable);
  const generate = vi.spyOn(plotloomApi, "generateProductionBridgeIntent");
  const save = vi.spyOn(plotloomApi, "updateProductionBridgeIntent").mockResolvedValue({ ...state("author", 2, "b".repeat(64), "作者填写", "author_saved"), intentGeneration: unavailable.intentGeneration });
  await render("author"); await settle();
  expect(button("生成戏剧意图建议").disabled).toBe(true);
  await act(async () => button("生成戏剧意图建议").click());
  expect(generate).not.toHaveBeenCalled(); expect(host.textContent).toContain("可在下方逐项填写作者意图");
  const field = host.querySelector(".bridge-intent-field textarea") as HTMLTextAreaElement;
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(field, "作者填写"); field.dispatchEvent(new Event("input", { bubbles: true })); });
  expect(button("保存戏剧意图整包").disabled).toBe(false);
  await act(async () => button("保存戏剧意图整包").click()); await settle();
  expect(save).toHaveBeenCalledWith("author", expect.objectContaining({ entries: [{ id: "entry-author", text: "作者填写" }] }));
  expect(button("生成戏剧意图建议").disabled).toBe(true);
});

it("contains capability responses to their current project owner", async () => {
  const prior = deferred<ProductionBridgeState>();
  const unavailable = state("current"); unavailable.intentGeneration = { status: "unavailable", reason: "not_configured" };
  vi.spyOn(plotloomApi, "getProductionBridge").mockImplementation(id => id === "prior" ? prior.promise : Promise.resolve(unavailable));
  await render("prior"); await render("current"); await settle();
  await act(async () => prior.resolve(state("prior"))); await settle();
  expect(host.textContent).toContain("excerpt-current"); expect(button("生成戏剧意图建议").disabled).toBe(true);
});

it.each(["queued", "dispatched"] as const)("disables service-owned %s job controls when runtime inference is unavailable", async status => {
  const unavailable = state("held"); unavailable.intentGeneration = { status: "unavailable", reason: "not_configured" };
  unavailable.intentJob = { id: "held", transport: "text_api", status } as never;
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(unavailable);
  const resume = vi.spyOn(plotloomApi, "resumeProductionBridgeIntent"), cancel = vi.spyOn(plotloomApi, "cancelProductionBridgeIntent");
  await render("held"); await settle();
  expect(button("取消推断任务").disabled).toBe(true);
  await act(async () => button("取消推断任务").click());
  if (status === "queued") { expect(button("继续排队任务").disabled).toBe(true); await act(async () => button("继续排队任务").click()); }
  expect(resume).not.toHaveBeenCalled(); expect(cancel).not.toHaveBeenCalled();
});

it("refreshes the owning canonical project before enabling either installed-shot handoff", async () => {
  const first = state("install", 3, "c".repeat(64), "QA intent", "author_saved");
  first.proposal!.cuts = [{ shotId: "shot-1", sectionId: "install", episode: 1, sceneIndex: 1, seconds: 5, source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: 1 } }];
  const installed = { ...first, status: "accepted" as const, installation: installedProduction({ cuts: first.proposal!.cuts }) };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(first);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge").mockResolvedValue(installed);
  const refreshed = deferred<void>();
  const onInstalled = vi.fn(() => refreshed.promise), onOpenShot = vi.fn();
  await render("install", onOpenShot, onInstalled); await settle();
  await act(async () => button("确认投产提案").click()); await settle();
  expect(onInstalled).toHaveBeenCalledExactlyOnceWith("install");
  expect(button("继续：打开第一个镜头").disabled).toBe(true);
  expect(button("在分镜工作台打开 shot-1").disabled).toBe(true);
  await act(async () => button("继续：打开第一个镜头").click());
  expect(onOpenShot).not.toHaveBeenCalled();
  await act(async () => refreshed.resolve()); await settle();
  expect(button("继续：打开第一个镜头").disabled).toBe(false);
  await act(async () => button("继续：打开第一个镜头").click());
  expect(onOpenShot).toHaveBeenCalledExactlyOnceWith("shot-1");
  expect(accept).toHaveBeenCalledTimes(1);
});

it("keeps both shot handoffs blocked after a failed canonical reread without repeating installation", async () => {
  const first = state("reload-failure", 3, "c".repeat(64), "QA intent", "author_saved");
  first.proposal!.cuts = [{ shotId: "shot-1", sectionId: "reload-failure", episode: 1, sceneIndex: 1, seconds: 5, source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: 1 } }];
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(first);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge").mockResolvedValue({ ...first, status: "accepted", installation: installedProduction({ cuts: first.proposal!.cuts }) });
  const onOpenShot = vi.fn();
  const onInstalled = vi.fn().mockRejectedValueOnce(new Error("canonical read failed")).mockResolvedValue(undefined);
  await render("reload-failure", onOpenShot, onInstalled); await settle();
  await act(async () => button("确认投产提案").click()); await settle();
  expect(host.textContent).toContain("投产已确认；请刷新服务器版本读取当前镜头");
  expect(button("继续：打开第一个镜头").disabled).toBe(true);
  expect(button("在分镜工作台打开 shot-1").disabled).toBe(true);
  expect(accept).toHaveBeenCalledTimes(1);
  expect(onOpenShot).not.toHaveBeenCalled();
  await act(async () => button("重新读取投产镜头").click()); await settle();
  expect(button("继续：打开第一个镜头").disabled).toBe(false);
  expect(button("在分镜工作台打开 shot-1").disabled).toBe(false);
  expect(accept).toHaveBeenCalledTimes(1);
  expect(onInstalled).toHaveBeenCalledTimes(2);
});

it("does not refresh a replacement project for a late installation acknowledgement", async () => {
  const first = state("prior", 3, "c".repeat(64), "QA intent", "author_saved");
  const pending = deferred<ProductionBridgeState>(), onInstalled = vi.fn(async () => undefined);
  vi.spyOn(plotloomApi, "getProductionBridge").mockImplementation(async projectId => projectId === "prior" ? first : state("current"));
  vi.spyOn(plotloomApi, "acceptProductionBridge").mockReturnValue(pending.promise);
  await render("prior", undefined, onInstalled); await settle();
  await act(async () => button("确认投产提案").click());
  await render("current", undefined, onInstalled); await settle();
  await act(async () => pending.resolve({ ...first, status: "accepted", installation: installedProduction() })); await settle();
  expect(onInstalled).not.toHaveBeenCalled();
  expect(host.textContent).toContain("excerpt-current");
  expect(host.textContent).not.toContain("投产提案已确认");
});

it("requires the displayed dramatic-intent package to be saved before accepting its exact new revision", async () => {
  const first = state("first");
  const saved = state("first", 2, "c".repeat(64), "author-reviewed objective", "author_saved");
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(first);
  const save = vi.spyOn(plotloomApi, "updateProductionBridgeIntent").mockResolvedValue(saved);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge").mockResolvedValue({ ...saved, status: "accepted", installation: installedProduction() });

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
  expect(host.textContent).toContain("场景与镜头数据已建立；此次确认不会自动生成图片或视频。");
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
  await act(async () => priorGet.resolve(bridgeState())); await settle();
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
      id: "job-1", transport: "text_api", status: "dispatched", proposalRevision: 1, proposalContentHash: pending.proposal!.contentHash,
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

it("opens only a current installed bridge cut without writing project state", async () => {
  const accepted = state("opening", 2, "c".repeat(64), "reviewed", "author_saved");
  accepted.status = "accepted";
  accepted.proposal!.cuts = [{ shotId: "not-navigable" }, { shotId: "opening-s1-c1", sectionId: "opening", episode: 1, sceneIndex: 1, seconds: 6, source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: 1 } }];
  accepted.installation = installedProduction({ cuts: accepted.proposal!.cuts });
  const get = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(accepted);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge");
  const onOpenShot = vi.fn();
  await render("opening", onOpenShot); await settle();
  await act(async () => button("继续：打开第一个镜头").click());
  expect(onOpenShot).toHaveBeenCalledExactlyOnceWith("opening-s1-c1");
  await act(async () => button("在分镜工作台打开 opening-s1-c1").click());
  expect(onOpenShot).toHaveBeenCalledTimes(2);
  expect(get).toHaveBeenCalledTimes(1);
  expect(accept).not.toHaveBeenCalled();

  get.mockResolvedValue({ ...accepted, installation: installedProduction({ status: "outdated", cuts: accepted.proposal!.cuts }) });
  await render("drifted", onOpenShot); await settle();
  expect(button("在分镜工作台打开 opening-s1-c1")).toBeUndefined();
  expect(button("继续：打开第一个镜头")).toBeUndefined();
  expect(host.textContent).toContain("这里的镜头直达已暂停");

  get.mockResolvedValue({ ...accepted, status: "stale", staleReasons: ["source changed"], installation: installedProduction({ status: "outdated", cuts: accepted.proposal!.cuts }) });
  await render("other", onOpenShot); await settle();
  expect(button("在分镜工作台打开 opening-s1-c1")).toBeUndefined();
  expect(button("继续：打开第一个镜头")).toBeUndefined();
});

it("explicitly prepares a fresh stale pre-install proposal and renews semantic review", async () => {
  const stale = { ...state("stale", 4, "b".repeat(64), "old reviewed intent", "author_saved"), status: "stale" as const, staleReasons: ["Brief changed"] };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(stale);
  const fresh = state("fresh", 5, "c".repeat(64));
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge").mockResolvedValue(fresh);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge");
  await render("project"); await settle();
  expect(button("确认投产提案").disabled).toBe(true);
  expect(button("重新准备投产提案").disabled).toBe(false);
  await act(async () => button("重新准备投产提案").click());
  expect(prepare).toHaveBeenCalledExactlyOnceWith("project", stale.preparation.status === "available" ? stale.preparation.request : undefined);
  expect(host.textContent).toContain("提案 r5");
  expect(button("确认投产提案").disabled).toBe(true);
  expect(accept).not.toHaveBeenCalled();
});

it("retains edits when a proposal becomes stale and blocks saving obsolete intent", async () => {
  vi.useFakeTimers();
  try {
  const pending = { ...state("local"), intentJob: { id: "job", status: "dispatched" } as never };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(pending).mockResolvedValueOnce({ ...pending, status: "stale", staleReasons: ["replacement target changed"], intentJob: { id: "job", status: "stale" } as never });
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge").mockRejectedValue(new Error("preparation refused"));
  await render("project"); await settle();
  const textarea = host.querySelector("textarea")!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(textarea, "retained local edit");
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () => { await vi.advanceTimersByTimeAsync(1600); }); await settle();
  expect(textarea.disabled).toBe(true);
  expect(button("保存戏剧意图整包").disabled).toBe(true);
  expect(button("重新准备投产提案").disabled).toBe(true);
  expect(textarea.value).toBe("retained local edit");
  await act(async () => button("放弃本地编辑，保留已保存提案").click());
  expect(button("重新准备投产提案").disabled).toBe(false);
  await act(async () => button("重新准备投产提案").click());
  expect(host.textContent).toContain("preparation refused");
  expect(host.textContent).toContain("提案 r1");
  expect(prepare).toHaveBeenCalledTimes(1);
  } finally { vi.useRealTimers(); }
});

it.each(["queued", "dispatched", "outcome_unknown"] as const)("does not prepare over unresolved %s intent execution", async status => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue({ ...state("blocked"), status: "stale", intentJob: { id: "job", status } as never });
  await render("project"); await settle();
  expect(button("重新准备投产提案").disabled).toBe(true);
});

it("prepares an installed-story rebuild only with the exact server-qualified replacement target", async () => {
  const stale = { ...state("installed"), status: "stale" as const, installation: installedProduction({ status: "outdated" }) };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(stale);
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge").mockResolvedValue({ ...state("rebuilt", 2), installation: stale.installation });
  await render("project"); await settle();
  expect(button("确认投产提案").disabled).toBe(true);
  expect(button("准备重建提案").disabled).toBe(false);
  await act(async () => button("准备重建提案").click()); await settle();
  expect(prepare).toHaveBeenCalledExactlyOnceWith("project", stale.preparation.status === "available" ? stale.preparation.request : undefined);
  expect(host.textContent).toContain("需要重建");
  expect(button("确认投产提案").disabled).toBe(true);
});

it("keeps installed shot navigation independent of a newer candidate", async () => {
  const next = state("candidate", 3);
  const oldCut = { shotId: "installed-shot", sectionId: "old", episode: 1, sceneIndex: 1, seconds: 5, source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: 1 } };
  next.installation = installedProduction({ cuts: [oldCut] });
  next.proposal!.cuts = [{ ...oldCut, shotId: "candidate-shot" }];
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(next);
  const onOpenShot = vi.fn();
  await render("project", onOpenShot); await settle();
  expect(button("在分镜工作台打开 candidate-shot")).toBeUndefined();
  await act(async () => button("在分镜工作台打开 installed-shot").click());
  expect(onOpenShot).toHaveBeenCalledExactlyOnceWith("installed-shot");
});
