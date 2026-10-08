import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ProductionBridgePanel } from "../src/pages/ProductionBridgePanel";
import type { ProductionBridgeState } from "../src/types";
import { bridgeState, replacementTarget } from "./production-bridge-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const button = (text: string) => Array.from(host.querySelectorAll("button")).find(item => item.textContent === text);
const current = (): ProductionBridgeState => bridgeState({
  intentGeneration: { status: "unavailable", reason: "not_configured" }, nativeIntentGeneration: { status: "available" },
  status: "ready", proposal: {
    revision: 1, contentHash: "a".repeat(64), inputs: {}, replacementTarget: replacementTarget(),
    scenes: [], cuts: [], conflicts: [], advisories: [], installable: false, preparedAt: "2026-10-08T00:00:00Z",
    presentation: { version: 1, reviewed: true, sourceHash: "b".repeat(64), sources: [], runtimeChoice: { choices: [] }, frozenEvidence: {} },
    intentPackage: { suggestionOrigin: "none", reviewState: "pending", entries: [{
      id: "target", targetKind: "scene_objective", targetId: "scene", sourceCoordinates: {}, sourceContentHash: "c".repeat(64),
      sourceExcerpt: "来源", suggestedText: null, text: "",
    }] },
  },
});
const withJob = (status: "queued" | "dispatched" | "outcome_unknown" | "ready" | "cancelled"): ProductionBridgeState => ({
  ...current(), intentJob: {
    id: "ch_" + "a".repeat(32), transport: "codex_native", status, proposalRevision: 1, proposalContentHash: "a".repeat(64),
    profileId: null, profileVersion: null, promptVersion: "native-intent.v1", createdAt: "now", updatedAt: "now",
    errorCode: null, errorMessage: null, resultProposalRevision: status === "ready" ? 2 : null, providerRequestId: null, responseHash: status === "ready" ? "d".repeat(64) : null,
  }, nativeIntentTask: { state: status === "queued" ? "prepared" : status === "ready" ? "completed" : status === "outcome_unknown" ? "outcome_unknown" : "queued", candidateStatus: status, reportAvailable: status === "ready", limitations: [] },
});
const render = async () => { await act(async () => root.render(createElement(ProductionBridgePanel, { projectId: "project", readOnly: false, onInstalled: async () => undefined }))); };
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

it("prepares a frozen native candidate without API generation or sending", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(current());
  const prepare = vi.spyOn(plotloomApi, "prepareNativeBridgeIntent").mockResolvedValue(withJob("queued"));
  const api = vi.spyOn(plotloomApi, "generateProductionBridgeIntent");
  const send = vi.spyOn(plotloomApi, "nativeBridgeIntentAction");
  await render();
  await act(async () => button("准备 Codex 戏剧意图任务")!.click());
  expect(prepare).toHaveBeenCalledWith("project", { expectedProposalRevision: 1, expectedContentHash: "a".repeat(64) });
  expect(api).not.toHaveBeenCalled(); expect(send).not.toHaveBeenCalled();
  expect(host.textContent).toContain("任务已冻结，尚未发送");
  expect(button("发送给 Codex 文字助手")?.disabled).toBe(false);
  expect(host.textContent).not.toContain("当前服务未配置戏剧意图推断");
});

it("refreshes native availability after assistant settings change without generation", async () => {
  const unavailable = current(); unavailable.nativeIntentGeneration = { status: "unavailable", reason: "not_configured" };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(unavailable).mockResolvedValue(current());
  const prepare = vi.spyOn(plotloomApi, "prepareNativeBridgeIntent");
  await render();
  expect(button("准备 Codex 戏剧意图任务")?.disabled).toBe(true);
  await act(async () => window.dispatchEvent(new Event("plotloom-specialists-changed")));
  expect(button("准备 Codex 戏剧意图任务")?.disabled).toBe(false);
  expect(prepare).not.toHaveBeenCalled();
});

it("sends the exact queued native job once, then offers inspection", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(withJob("queued"));
  const action = vi.spyOn(plotloomApi, "nativeBridgeIntentAction").mockResolvedValue(withJob("dispatched"));
  await render();
  await act(async () => button("发送给 Codex 文字助手")!.click());
  expect(action).toHaveBeenCalledWith("project", "ch_" + "a".repeat(32), "send");
  expect(button("发送给 Codex 文字助手")).toBeUndefined();
  expect(button("检查原任务交付")?.disabled).toBe(false);
  expect(button("继续排队任务")).toBeUndefined();
});

it.each(["outcome_unknown", "cancelled"] as const)("reopens %s for exact inspection without a send control", async status => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(withJob(status));
  const action = vi.spyOn(plotloomApi, "nativeBridgeIntentAction").mockResolvedValue(withJob(status));
  await render();
  expect(button("发送给 Codex 文字助手")).toBeUndefined();
  await act(async () => button("检查原任务交付")!.click());
  expect(action).toHaveBeenCalledWith("project", "ch_" + "a".repeat(32), "check");
  expect(host.textContent).toContain("取消不会中止助手执行或解除占用");
});

it("lets the author save unchanged complete suggestions while installation stays blocked", async () => {
  const inferred = withJob("ready");
  inferred.proposal!.revision = 2;
  inferred.proposal!.intentPackage = { suggestionOrigin: "codex_native.v1", reviewState: "model_suggested", provenance: { jobId: inferred.intentJob!.id }, entries: inferred.proposal!.intentPackage.entries.map(entry => ({ ...entry, text: "角色争取信任", suggestedText: "角色争取信任" })) };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(inferred);
  const save = vi.spyOn(plotloomApi, "updateProductionBridgeIntent").mockResolvedValue(inferred);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge");
  vi.spyOn(plotloomApi, "admitReportRead").mockResolvedValue({ cancel: vi.fn(), complete: vi.fn() } as never);
  await render();
  expect(button("保存戏剧意图整包")?.disabled).toBe(false);
  expect(button("确认投产提案")?.disabled).toBe(true);
  expect(accept).not.toHaveBeenCalled();
  expect(host.querySelector("iframe")?.getAttribute("sandbox")).toBe("");
  await act(async () => button("保存戏剧意图整包")!.click());
  expect(save).toHaveBeenCalledWith("project", { expectedProposalRevision: 2, expectedContentHash: "a".repeat(64), entries: [{ id: "target", text: "角色争取信任" }] });
});
