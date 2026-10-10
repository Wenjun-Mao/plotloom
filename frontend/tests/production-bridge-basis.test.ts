import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ProductionBridgePanel } from "../src/pages/ProductionBridgePanel";
import { useProductionBridgeReview, type BridgeReviewBasis } from "../src/pages/useProductionBridgeReview";
import { ReviewDraftContext } from "../src/features/authoring/ReviewDraftContext";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import { createReviewDraftStore } from "../src/features/authoring/reviewDraftStore";
import type { ProductionBridgeState } from "../src/types";
import { bridgeState, installedProduction, prepareRequest, replacementTarget } from "./production-bridge-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
let quiescence: ReturnType<typeof createProjectDraftQuiescence>;
let store: ReturnType<typeof createReviewDraftStore>;
const basis = (revision = 1, status: BridgeReviewBasis["status"] = "current"): BridgeReviewBasis => ({ revision, contentHash: String(revision).repeat(64), status });
const state = (revision = 1): ProductionBridgeState => bridgeState({ status: "ready", proposal: {
  revision, contentHash: String(revision).repeat(64), inputs: {}, replacementTarget: replacementTarget(), scenes: [], cuts: [], conflicts: [], advisories: [], installable: true, preparedAt: "now",
  intentPackage: { suggestionOrigin: "none", reviewState: "author_saved", entries: [{ id: "intent", targetId: "scene", targetKind: "scene_objective", sourceCoordinates: {}, sourceContentHash: "a".repeat(64), sourceExcerpt: `evidence-${revision}`, text: `intent-${revision}`, suggestedText: null }] },
  presentation: { version: 1, reviewed: true, sourceHash: String(revision).repeat(64), sources: [{ id: `source-${revision}`, kind: "action", targetId: "shot", coordinates: {}, sourceHash: "b".repeat(64), sourceText: `physical-${revision}`, spans: [{ start: 0, end: 10, role: "physical", rendering: `rendering-${revision}`, reason: "" }] }], runtimeChoice: { choices: [] }, frozenEvidence: {} },
} });
const missing = () => bridgeState({ preparation: { status: "available", request: prepareRequest() } });
const render = async (reviewBasis = basis(), projectId = "project") => { await act(async () => root.render(createElement(ReviewDraftContext.Provider, {
  value: { store, quiescence, projectId, revision: 1, enabled: true },
  children: createElement(ProductionBridgePanel, { projectId, reviewBasis, readOnly: false, onInstalled: async () => undefined }),
}))); };
const settle = async () => { await act(async () => { await Promise.resolve(); }); };
const button = (name: string) => [...host.querySelectorAll("button")].find(item => item.textContent === name)!;
const field = (selector: string) => host.querySelector(selector) as HTMLTextAreaElement;
const fill = async (element: HTMLTextAreaElement, value: string) => { await act(async () => {
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
}); };
const deferred = <T,>() => {
  let resolve!: (value: T) => void, reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const refresh = async () => { await act(async () => window.dispatchEvent(new Event("plotloom-specialists-changed"))); };
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); quiescence = createProjectDraftQuiescence(); store = createReviewDraftStore(quiescence, sessionStorage); });
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

it("blocks the first changed-basis render and prepares only the freshly read replacement contract", async () => {
  const next = deferred<ProductionBridgeState>();
  const get = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(missing()).mockReturnValueOnce(next.promise);
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge").mockResolvedValue(state(2));
  await render(); expect(button("准备投产提案").disabled).toBe(false);
  await render(basis(2)); expect(button("准备投产提案").disabled).toBe(true);
  await act(async () => button("准备投产提案").click()); expect(prepare).not.toHaveBeenCalled();
  const available = missing();
  available.preparation = { status: "available", request: prepareRequest({ expectedSourceInputsHash: "c".repeat(64) }) };
  await act(async () => next.resolve(available));
  await act(async () => button("准备投产提案").click());
  expect(get).toHaveBeenCalledTimes(2);
  expect(prepare).toHaveBeenCalledExactlyOnceWith("project", available.preparation.request);
});

it("rechecks status as well as revision/hash and cannot enable retained evidence", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(state());
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge");
  await render(); expect(button("确认投产提案").disabled).toBe(false);
  await render(basis(1, "retained"));
  expect(button("确认投产提案").disabled).toBe(true);
  await act(async () => button("确认投产提案").click()); expect(accept).not.toHaveBeenCalled();
  expect(plotloomApi.getProductionBridge).toHaveBeenCalledTimes(2);
});

it.each(["success", "error"])("does not present cached production as current during a retained-basis %s", async outcome => {
  const current = { ...state(), installation: installedProduction() };
  const next = deferred<ProductionBridgeState>();
  const get = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(current).mockReturnValueOnce(next.promise).mockResolvedValue(current);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge");
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge");
  await render();
  expect(host.querySelector('[data-testid="installed-production"]')!.textContent).toContain("当前有效");
  await fill(field('[aria-label="画面描述 source-1 1"]'), "retained local rendering");
  await render(basis(1, "retained"));
  const installed = host.querySelector('[data-testid="installed-production"]')!;
  expect(installed.textContent).toContain("制作依据尚未核实");
  expect(installed.textContent).not.toContain("当前有效");
  expect(installed.textContent).not.toContain("需要重建");
  await act(async () => {
    if (outcome === "error") next.reject(new Error("refresh failed"));
    else next.resolve({ ...current, status: "stale", installation: installedProduction({ status: "outdated" }) });
  });
  expect(installed.textContent).toContain(outcome === "error" ? "制作依据尚未核实" : "分镜评审待确认");
  expect(host.querySelector('[data-testid="production-bridge"] > header strong')!.textContent).toBe("分镜评审待确认");
  expect(host.textContent).not.toContain("故事来源或制作版本已变化");
  expect(installed.textContent).not.toContain("需要重建");
  expect(field('[aria-label="画面描述 source-1 1"]').value).toBe("retained local rendering");
  expect(button("确认投产提案").disabled).toBe(true);
  await render(basis());
  expect(installed.textContent).toContain("当前有效");
  expect(field('[aria-label="画面描述 source-1 1"]').value).toBe("retained local rendering");
  expect(get).toHaveBeenCalledTimes(3);
  expect(accept).not.toHaveBeenCalled(); expect(prepare).not.toHaveBeenCalled();
});

it.each(["success", "error"])("contains an old %s across A-B-A and an older same-basis read", async outcome => {
  const a = deferred<ProductionBridgeState>(), b = deferred<ProductionBridgeState>(), last = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise).mockReturnValueOnce(last.promise).mockResolvedValue(state(4));
  await render(); await render(basis(2)); await render();
  await act(async () => { if (outcome === "success") a.resolve(state(1)); else a.reject(new Error("obsolete A")); b.resolve(state(2)); });
  expect(host.textContent).not.toContain("evidence-1"); expect(host.textContent).not.toContain("evidence-2"); expect(host.textContent).not.toContain("obsolete A");
  await act(async () => last.resolve(state(3)));
  expect(host.textContent).toContain("evidence-3");
  await refresh(); expect(host.textContent).toContain("evidence-4");
});

it("preserves both actual presentation and intent text until explicit atomic adoption", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(state()).mockResolvedValue(state(2));
  await render();
  await fill(field('[aria-label="画面描述 source-1 1"]'), "unsaved physical detail");
  await fill(field(".bridge-intent-field textarea"), "unsaved dramatic intent");
  await render(basis(2));
  expect(field('[aria-label="画面描述 source-1 1"]').value).toBe("unsaved physical detail");
  expect(field(".bridge-intent-field textarea").value).toBe("unsaved dramatic intent");
  expect(host.textContent).toContain("未保存的本地编辑仍在此保留");
  expect(button("保存戏剧意图整包").disabled).toBe(true); expect(button("保存呈现方式审阅").disabled).toBe(true);
  await act(async () => button("载入新提案并放弃本地编辑").click()); await settle();
  expect(field('[aria-label="画面描述 source-2 1"]').value).toBe("rendering-2");
  expect(field(".bridge-intent-field textarea").value).toBe("intent-2");
  expect(host.textContent).not.toContain("未保存的本地编辑仍在此保留");
});

it("retains readable buffers on refresh failure and retries only the GET", async () => {
  const get = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(state()).mockRejectedValueOnce(new Error("refresh failed")).mockResolvedValue(state(2));
  const save = vi.spyOn(plotloomApi, "updateProductionBridgeIntent");
  await render(); await fill(field('[aria-label="画面描述 source-1 1"]'), "retained physical text");
  await render(basis(2));
  expect(host.textContent).toContain("refresh failed");
  expect(field('[aria-label="画面描述 source-1 1"]').value).toBe("retained physical text");
  expect(button("确认投产提案").disabled).toBe(true);
  await act(async () => button("重试加载").click());
  expect(get).toHaveBeenCalledTimes(3); expect(save).not.toHaveBeenCalled();
  expect(field('[aria-label="画面描述 source-1 1"]').value).toBe("retained physical text");
});

it("settles presentation busy after its own save changes the editor proposal revision", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(state());
  const saved = state(); saved.proposal!.revision = 2; saved.proposal!.contentHash = "c".repeat(64);
  saved.proposal!.presentation.sources[0].spans[0].rendering = "reviewed correction";
  vi.spyOn(plotloomApi, "updateProductionBridgePresentation").mockResolvedValue(saved);
  await render(); await fill(field('[aria-label="画面描述 source-1 1"]'), "reviewed correction");
  const confirm = host.querySelector('[data-testid="production-presentation-review"] input[type="checkbox"]') as HTMLInputElement;
  await act(async () => confirm.click());
  await act(async () => button("保存呈现方式审阅").click()); await settle();
  expect(host.textContent).toContain("提案 r2"); expect(button("确认投产提案").disabled).toBe(false);
});

it("keeps the project busy across a changed basis until the obsolete mutation settles", async () => {
  const oldPrepare = deferred<ProductionBridgeState>(), newPrepare = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(missing());
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge").mockReturnValueOnce(oldPrepare.promise).mockReturnValueOnce(newPrepare.promise);
  await render(); await act(async () => button("准备投产提案").click());
  await render(basis(2)); expect(button("准备投产提案").disabled).toBe(true);
  await act(async () => button("准备投产提案").click()); expect(prepare).toHaveBeenCalledTimes(1);
  const close = quiescence.beginClose("project");
  await expect(close.drain()).rejects.toThrow("操作未完成"); close.finish();
  await act(async () => oldPrepare.resolve(state(8))); await settle();
  expect(host.textContent).not.toContain("evidence-8"); expect(button("准备投产提案").disabled).toBe(false);
  await act(async () => button("准备投产提案").click()); expect(prepare).toHaveBeenCalledTimes(2);
  await act(async () => newPrepare.resolve(state(2))); await settle();
  expect(host.textContent).toContain("evidence-2"); expect(button("确认投产提案").disabled).toBe(false);
});

it("serializes slow poll reads instead of repeatedly superseding their acknowledgement", async () => {
  vi.useFakeTimers();
  try {
    const pending = state(); pending.intentJob = { id: "pending", transport: "text_api", status: "dispatched" } as never;
    const next = deferred<ProductionBridgeState>();
    const get = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(pending).mockReturnValueOnce(next.promise);
    await render(); await act(async () => { await vi.advanceTimersByTimeAsync(1600); });
    expect(button("确认投产提案").disabled).toBe(true);
    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
    expect(get).toHaveBeenCalledTimes(2);
    await act(async () => next.resolve(state(2))); await settle();
    expect(button("确认投产提案").disabled).toBe(false);
  } finally { vi.useRealTimers(); }
});

it("cannot adopt a child save from an obsolete basis or clear the newer mutation busy state", async () => {
  const oldSave = deferred<ProductionBridgeState>(), newPrepare = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(state()).mockResolvedValue(missing());
  vi.spyOn(plotloomApi, "updateProductionBridgePresentation").mockReturnValue(oldSave.promise);
  vi.spyOn(plotloomApi, "prepareProductionBridge").mockReturnValue(newPrepare.promise);
  await render(); await fill(field('[aria-label="画面描述 source-1 1"]'), "saved old basis");
  await act(async () => (host.querySelector('[data-testid="production-presentation-review"] input[type="checkbox"]') as HTMLInputElement).click());
  await act(async () => button("保存呈现方式审阅").click());
  await render(basis(2));
  // The in-flight editor is retained, not rebased by the new acknowledgement.
  expect(button("载入新提案并放弃本地编辑").disabled).toBe(true);
  await act(async () => oldSave.resolve(state(9))); await settle();
  expect(host.textContent).not.toContain("evidence-9");
  await act(async () => button("载入新提案并放弃本地编辑").click()); await settle();
  await act(async () => button("准备投产提案").click());
  expect(button("准备投产提案").disabled).toBe(true);
  await act(async () => newPrepare.resolve(state(2))); await settle();
  expect(host.textContent).toContain("evidence-2"); expect(button("确认投产提案").disabled).toBe(false);
});

it("protects presentation-only edits when another reader accepts the same proposal key", async () => {
  const accepted = { ...state(), status: "accepted" as const };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(state()).mockResolvedValue(accepted);
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge");
  await render(); await fill(field('[aria-label="画面描述 source-1 1"]'), "unsaved presentation only");
  await refresh();
  expect(field('[aria-label="画面描述 source-1 1"]').value).toBe("unsaved presentation only");
  expect(field('[aria-label="画面描述 source-1 1"]').disabled).toBe(false); // Disabled by its fieldset, not by erasing the buffer.
  expect(field('[aria-label="画面描述 source-1 1"]').closest("fieldset")!.disabled).toBe(true);
  expect(host.textContent).toContain("审阅状态已变化");
  expect(button("重新准备投产提案").disabled).toBe(true);
  await act(async () => button("重新准备投产提案").click()); expect(prepare).not.toHaveBeenCalled();
  const close = quiescence.beginClose("project");
  await expect(close.drain()).rejects.toThrow("尚有未保存修改"); close.finish();
  await act(async () => button("载入新提案并放弃本地编辑").click()); await settle();
  expect(field('[aria-label="画面描述 source-1 1"]').value).toBe("rendering-1");
  expect(button("重新准备投产提案").disabled).toBe(false);
  const clean = quiescence.beginClose("project"); await expect(clean.drain()).resolves.toBe(true); clean.finish();
});

it("rejects retained admission callbacks during refresh and after replacement acknowledgement", async () => {
  const next = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(state()).mockReturnValueOnce(next.promise);
  let review!: ReturnType<typeof useProductionBridgeReview>;
  function Probe() { review = useProductionBridgeReview("project", basis(), false, async () => undefined); return null; }
  await act(async () => root.render(createElement(Probe)));
  const retained = review.run;
  const operation = vi.fn().mockResolvedValue(state(3));
  await act(async () => { review.retryLoad(); void retained(operation); });
  expect(operation).not.toHaveBeenCalled(); expect(review.acknowledged).toBe(false);
  await act(async () => next.resolve(state(2)));
  await act(async () => { void retained(operation); }); expect(operation).not.toHaveBeenCalled();
  await act(async () => { void review.run(operation); }); expect(operation).toHaveBeenCalledTimes(1);
});

it("checks pending occupancy synchronously before a render can admit a duplicate callback", async () => {
  const pending = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(state());
  let review!: ReturnType<typeof useProductionBridgeReview>;
  function Probe() { review = useProductionBridgeReview("project", basis(), false, async () => undefined); return null; }
  await act(async () => root.render(createElement(Probe)));
  const run = review.run, operation = vi.fn().mockReturnValue(pending.promise);
  await act(async () => { void run(operation); void run(operation); });
  expect(operation).toHaveBeenCalledTimes(1); expect(review.busy).toBe(true);
  await act(async () => pending.resolve(state(2))); expect(review.busy).toBe(false);
});

it("keeps occupancy separate for projects and cannot clear A with B's settlement", async () => {
  const a = deferred<ProductionBridgeState>(), b = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(missing());
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge").mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise);
  await render(basis(), "a"); await act(async () => button("准备投产提案").click());
  await render(basis(), "b"); expect(button("准备投产提案").disabled).toBe(false);
  await act(async () => button("准备投产提案").click());
  await render(basis(), "a"); expect(button("准备投产提案").disabled).toBe(true);
  await act(async () => b.resolve(state(8))); expect(button("准备投产提案").disabled).toBe(true);
  await act(async () => a.resolve(state(9))); expect(button("准备投产提案").disabled).toBe(false);
  expect(prepare).toHaveBeenCalledTimes(2); expect(host.textContent).not.toContain("evidence-8"); expect(host.textContent).not.toContain("evidence-9");
});

it("retires old presentation callbacks after explicit disposal even with the same proposal key", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(state());
  let review!: ReturnType<typeof useProductionBridgeReview>;
  function Probe() { review = useProductionBridgeReview("project", basis(), false, async () => undefined); return null; }
  await act(async () => root.render(createElement(Probe)));
  const obsolete = review.setPresentationDirty;
  await act(async () => { review.presentationEdited(); review.setPresentationDirty(true); });
  await act(async () => review.discard());
  await act(async () => { review.presentationEdited(); review.setPresentationDirty(true); obsolete(false); });
  expect(review.presentationDirty).toBe(true); expect(review.presentationTouched).toBe(true);
});

it.each(["resolve", "reject"])("settles the admitted Close writer after actual unmount and %s", async outcome => {
  const pending = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(missing());
  vi.spyOn(plotloomApi, "prepareProductionBridge").mockReturnValue(pending.promise);
  await render(); await act(async () => button("准备投产提案").click());
  await act(async () => root.render(null));
  const held = quiescence.beginClose("project"); await expect(held.drain()).rejects.toThrow("操作未完成"); held.finish();
  await act(async () => { if (outcome === "resolve") pending.resolve(state(2)); else pending.reject(new Error("unmounted failure")); });
  const settled = quiescence.beginClose("project"); await expect(settled.drain()).resolves.toBe(true); settled.finish();
});

it("remount cannot overwrite pending occupancy or admit a duplicate before settlement", async () => {
  const pending = deferred<ProductionBridgeState>();
  const fresh = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(missing()).mockResolvedValueOnce(missing()).mockReturnValue(fresh.promise);
  const prepare = vi.spyOn(plotloomApi, "prepareProductionBridge").mockReturnValue(pending.promise);
  await render(); await act(async () => button("准备投产提案").click());
  await act(async () => root.render(null)); await render();
  expect(button("准备投产提案").disabled).toBe(true);
  await act(async () => button("准备投产提案").click()); expect(prepare).toHaveBeenCalledTimes(1);
  const held = quiescence.beginClose("project"); await expect(held.drain()).rejects.toThrow("操作未完成"); held.finish();
  await act(async () => pending.resolve(state(9)));
  expect(button("准备投产提案").disabled).toBe(true); expect(host.textContent).not.toContain("evidence-9");
  await act(async () => fresh.resolve(state(2))); expect(button("确认投产提案").disabled).toBe(false);
  const settled = quiescence.beginClose("project"); await expect(settled.drain()).resolves.toBe(true); settled.finish();
});

it.each(["success", "error"].flatMap(outcome => ["before", "after"].map(timing => ({ outcome, timing }))))("retires a pre-completion remount GET: $outcome resolving $timing settlement", async ({ outcome, timing }) => {
  const pending = deferred<ProductionBridgeState>(), early = deferred<ProductionBridgeState>(), fresh = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(state()).mockReturnValueOnce(early.promise).mockReturnValueOnce(fresh.promise);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge").mockReturnValue(pending.promise);
  await render(); await act(async () => button("确认投产提案").click());
  await act(async () => root.render(null)); await render();
  if (timing === "before") { await act(async () => early.resolve(state())); expect(button("确认投产提案").disabled).toBe(true); }
  await act(async () => { if (outcome === "success") pending.resolve({ ...state(), status: "accepted" }); else pending.reject(new Error("obsolete unknown result")); });
  if (timing === "after") await act(async () => early.resolve(state(8)));
  expect(host.textContent).not.toContain("evidence-8"); expect(accept).toHaveBeenCalledTimes(1);
  await act(async () => fresh.resolve({ ...state(), status: "accepted" }));
  expect(host.textContent).toContain("投产提案已确认"); expect(host.textContent).not.toContain("obsolete unknown result");
});

it("does not admit a mutation behind an already-started project Close", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(state());
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge");
  await render(); const close = quiescence.beginClose("project");
  await act(async () => button("确认投产提案").click()); expect(accept).not.toHaveBeenCalled(); close.finish();
});

it("cannot strand a fresh epoch GET with a retained retry callback from before settlement", async () => {
  const operation = deferred<ProductionBridgeState>(), fresh = deferred<ProductionBridgeState>();
  const get = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(state()).mockResolvedValueOnce(state()).mockReturnValueOnce(fresh.promise);
  let review!: ReturnType<typeof useProductionBridgeReview>;
  function Probe() { review = useProductionBridgeReview("project", basis(), false, async () => undefined); return null; }
  const mount = async () => { await act(async () => root.render(createElement(ReviewDraftContext.Provider, {
    value: { store, quiescence, projectId: "project", revision: 1, enabled: true }, children: createElement(Probe),
  }))); };
  await mount(); await act(async () => { void review.run(() => operation.promise); });
  await act(async () => root.render(null)); await mount();
  const retainedRetry = review.retryLoad;
  await act(async () => operation.resolve(state(9))); expect(get).toHaveBeenCalledTimes(3);
  await act(async () => retainedRetry()); expect(get).toHaveBeenCalledTimes(3);
  await act(async () => fresh.resolve(state(2))); expect(review.acknowledged).toBe(true); expect(review.proposal!.revision).toBe(2);
});
