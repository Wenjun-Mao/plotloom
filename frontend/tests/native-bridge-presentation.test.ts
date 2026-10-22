import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ProductionPresentationReview } from "../src/pages/ProductionPresentationReview";
import { ProductionBridgePanel } from "../src/pages/ProductionBridgePanel";
import type { PresentationCandidate, ProductionBridgeProposal, ProductionBridgeState } from "../src/types";
import { bridgeState, replacementTarget } from "./production-bridge-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root;
const button = (text: string) => Array.from(host.querySelectorAll("button")).find(item => item.textContent === text)!;
const proposal = (): ProductionBridgeProposal => ({ revision: 3, contentHash: "a".repeat(64), inputs: {}, replacementTarget: replacementTarget(),
  scenes: [], cuts: [], conflicts: [], advisories: [], installable: false, preparedAt: "now",
  intentPackage: { suggestionOrigin: "none", reviewState: "author_saved", entries: [] },
  presentation: { version: 1, reviewed: false, sourceHash: "b".repeat(64), frozenEvidence: {}, runtimeChoice: { choices: [] }, sources: [
    { id: "action:one", targetId: "opaque-one", kind: "action", coordinates: { episode: 1, sceneIndex: 1, flowIndex: 1 }, sourceHash: "c".repeat(64), sourceText: "她🙂停步。", spans: [] },
    { id: "composition:two", targetId: "opaque-two", kind: "composition", coordinates: { episode: 2, sceneIndex: 1, cutIndex: 1 }, sourceHash: "d".repeat(64), sourceText: "Portrait frame.", spans: [] },
  ] },
});
const candidate = (value = proposal()): PresentationCandidate => ({ jobId: "ch_" + "p".repeat(32), proposalRevision: value.revision,
  proposalContentHash: value.contentHash, sourceHash: value.presentation.sourceHash, provenance: { responseHash: "e".repeat(64) },
  entries: value.presentation.sources.map(source => ({ id: source.id, spans: [{ start: 0, end: [...source.sourceText].length, role: "physical", rendering: source.sourceText, reason: "" }] })),
});
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });
const fill = async (field: HTMLTextAreaElement, value: string) => act(async () => {
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(field, value);
  field.dispatchEvent(new Event("input", { bubbles: true }));
});

it("prefills complete labeled advice and saves unchanged spans with no checkbox", async () => {
  const value = proposal(), advice = candidate(value), save = vi.fn().mockResolvedValue(true);
  await act(async () => root.render(createElement(ProductionPresentationReview, { projectId: "project", proposal: value, candidate: advice,
    disabled: false, accepted: false, onSave: save, onDirty: vi.fn() })));
  expect(host.textContent).toContain("助手建议 · 已填入下方");
  expect(host.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
  expect(host.querySelectorAll(".presentation-scene")).toHaveLength(2);
  expect(host.querySelectorAll(".presentation-scene[open]")).toHaveLength(1);
  expect(host.querySelector(".presentation-raw")?.hasAttribute("open")).toBe(false);
  expect(host.querySelector("legend")?.textContent).not.toContain("opaque");
  expect([...host.querySelectorAll("blockquote")].map(item => item.textContent)).toEqual(value.presentation.sources.map(source => source.sourceText));
  expect(button("确认并保存呈现方式").disabled).toBe(false);
  await act(async () => button("确认并保存呈现方式").click());
  expect(save).toHaveBeenCalledWith(advice.entries);
  expect(host.textContent).toContain("不会确认投产或生成图片、视频");
});

it.each(["revision", "contentHash", "sourceHash"])("does not prefill advice with changed %s", async field => {
  const value = proposal(), advice = candidate(value);
  if (field === "revision") advice.proposalRevision++;
  else if (field === "contentHash") advice.proposalContentHash = "f".repeat(64);
  else advice.sourceHash = "f".repeat(64);
  await act(async () => root.render(createElement(ProductionPresentationReview, { projectId: "project", proposal: value, candidate: advice,
    disabled: false, accepted: false, onSave: vi.fn(), onDirty: vi.fn() })));
  expect(host.textContent).not.toContain("助手建议 · 已填入下方");
  expect(button("确认并保存呈现方式").disabled).toBe(true);
  expect(host.querySelector<HTMLSelectElement>("select")?.value).toBe("unassigned");
});

it("preserves authored rendering when fresh advice arrives until explicit replacement", async () => {
  const value = proposal(), first = candidate(value), next = candidate(value), edited = vi.fn();
  next.jobId = "ch_" + "q".repeat(32); next.entries[0].spans[0].rendering = "新的助手建议";
  const render = (advice: PresentationCandidate) => act(async () => root.render(createElement(ProductionPresentationReview,
    { projectId: "project", proposal: value, candidate: advice, disabled: false, accepted: false, onSave: vi.fn(), onDirty: vi.fn(), onEdited: edited })));
  await render(first);
  await fill(host.querySelector<HTMLTextAreaElement>('[aria-label="画面描述 action:one 1"]')!, "作者自己的画面描述");
  await render(next);
  expect(host.querySelector<HTMLTextAreaElement>('[aria-label="画面描述 action:one 1"]')?.value).toBe("作者自己的画面描述");
  expect(host.textContent).toContain("你的本地编辑保留，未被覆盖");
  await act(async () => button("使用助手建议替换本地呈现编辑").click());
  expect(host.querySelector<HTMLTextAreaElement>('[aria-label="画面描述 action:one 1"]')?.value).toBe("新的助手建议");
  expect(edited).toHaveBeenCalledTimes(2);
});

it("does not replace previously reviewed authored spans automatically", async () => {
  const value = proposal(), advice = candidate(value);
  value.presentation.reviewed = true;
  value.presentation.sources = value.presentation.sources.map((source, index) => ({ ...source, spans: advice.entries[index].spans.map(span => ({ ...span, rendering: "作者已保存的呈现" })) }));
  await act(async () => root.render(createElement(ProductionPresentationReview, { projectId: "project", proposal: value, candidate: advice,
    disabled: false, accepted: false, onSave: vi.fn(), onDirty: vi.fn() })));
  expect(host.querySelector<HTMLTextAreaElement>('[aria-label="画面描述 action:one 1"]')?.value).toBe("作者已保存的呈现");
  expect(button("使用助手建议替换本地呈现编辑")).toBeDefined();
});

it("requires complete faithful rendering even after advice prefill", async () => {
  const value = proposal(), advice = candidate(value), save = vi.fn();
  await act(async () => root.render(createElement(ProductionPresentationReview, { projectId: "project", proposal: value, candidate: advice,
    disabled: false, accepted: false, onSave: save, onDirty: vi.fn() })));
  await fill(host.querySelector<HTMLTextAreaElement>('[aria-label="画面描述 action:one 1"]')!, " ");
  expect(button("确认并保存呈现方式").disabled).toBe(true);
  await act(async () => button("确认并保存呈现方式").click());
  expect(save).not.toHaveBeenCalled();
  expect(host.textContent).toContain("还有 1 项待完善");
});

it("prepares, sends and checks one presentation task without intent or approval calls", async () => {
  const state = bridgeState({ status: "ready", proposal: proposal(), nativePresentationGeneration: { status: "available" } });
  const job: NonNullable<ProductionBridgeState["presentationJob"]> = { id: "ch_" + "p".repeat(32), transport: "codex_native", status: "queued", proposalRevision: 3,
    proposalContentHash: "a".repeat(64), profileId: null, profileVersion: null, promptVersion: "native-presentation.v1", createdAt: "now", updatedAt: "now",
    errorCode: null, errorMessage: null, resultProposalRevision: null, providerRequestId: null, responseHash: null };
  const prepared: ProductionBridgeState = { ...state, presentationJob: job, nativePresentationTask: { state: "prepared", candidateStatus: "queued", reportAvailable: false, limitations: [] } };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(state);
  const prepare = vi.spyOn(plotloomApi, "prepareNativeBridgePresentation").mockResolvedValue(prepared);
  const actions = vi.spyOn(plotloomApi, "nativeBridgePresentationAction").mockResolvedValueOnce({ ...prepared, presentationJob: { ...job, status: "dispatched" } })
    .mockResolvedValueOnce({ ...prepared, presentationJob: { ...job, status: "ready", responseHash: "d".repeat(64) }, presentationCandidate: candidate(state.proposal!) });
  const intent = vi.spyOn(plotloomApi, "prepareNativeBridgeIntent"), save = vi.spyOn(plotloomApi, "updateProductionBridgePresentation"), accept = vi.spyOn(plotloomApi, "acceptProductionBridge");
  await act(async () => root.render(createElement(ProductionBridgePanel, { projectId: "project", reviewBasis: { revision: 1, contentHash: "f".repeat(64), status: "current" }, readOnly: false, onInstalled: async () => undefined })));
  await act(async () => button("准备呈现方式建议").click());
  expect(prepare).toHaveBeenCalledWith("project", { expectedProposalRevision: 3, expectedContentHash: "a".repeat(64) });
  expect(actions).not.toHaveBeenCalled();
  await act(async () => button("发送呈现方式任务").click());
  await act(async () => button("检查呈现方式交付").click());
  expect(actions.mock.calls.map(call => call[2])).toEqual(["send", "check"]);
  expect(intent).not.toHaveBeenCalled(); expect(save).not.toHaveBeenCalled(); expect(accept).not.toHaveBeenCalled();
  expect(button("确认并保存呈现方式").disabled).toBe(false);
  expect(button("确认投产提案").disabled).toBe(true);
});
