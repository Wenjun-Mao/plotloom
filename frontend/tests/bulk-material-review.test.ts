import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { MaterialReview } from "../src/features/autopilot/MaterialReview";
import { autopilotApi } from "../src/features/autopilot/api";
import { fixtureMaterial, fixtureRun } from "./autopilot-fixture";
import { galleryDraft, materialSelectionHandoff } from "../src/features/autopilot/bulkMaterialReview";
import { evidenceReadsFixture } from "./autopilot-delivery-fixture";
import { projectQaApi } from "../src/components/ProjectQaContext";

vi.mock("../src/features/autopilot/useDeliveryEvidence", () => ({ useDeliveryEvidence: () => ({ state: { status: "ready", value: evidenceReadsFixture() }, retry: vi.fn() }) }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement; let root: Root;
const props = { projectId: "disposable", onClose: vi.fn(), onAccepted: vi.fn(), onUncertain: vi.fn() };
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); vi.spyOn(autopilotApi, "review").mockResolvedValue(fixtureMaterial); vi.spyOn(projectQaApi, "current").mockResolvedValue({ eligible: false, attribution: null }); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.clearAllMocks(); });
const confirm = () => [...host.querySelectorAll<HTMLButtonElement>("footer button")].at(-1)!;
async function render(extra = {}) { await act(async () => root.render(createElement(MaterialReview, { ...props, ...extra }))); }
async function openObservations() { await act(async () => host.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click()); }

it("selects the exact current inventory without loading images or inventing observations", async () => {
  const submit = vi.spyOn(autopilotApi, "handoff").mockResolvedValue(fixtureRun);
  await render();
  expect(host.querySelectorAll("img")).toHaveLength(0);
  expect(confirm().disabled).toBe(false);
  await act(async () => confirm().click());
  const body = submit.mock.calls[0][1];
  expect(body).toEqual(materialSelectionHandoff(fixtureMaterial));
  for (const frame of body.frames) {
    expect(frame).not.toHaveProperty("comparisons"); expect(frame).not.toHaveProperty("qualityObservation");
  }
  expect(body).not.toHaveProperty("reviewer"); expect(body).not.toHaveProperty("notes");
});

it("requires the exact QA actor when the project is scoped and never falls back", async () => {
  const actor = { kind: "agent_operated_qa", scopeId: "native-qa" } as const;
  vi.mocked(projectQaApi.current).mockResolvedValueOnce({ eligible: true, attribution: actor });
  const submit = vi.spyOn(autopilotApi, "handoff").mockResolvedValue(fixtureRun);
  await render(); expect(confirm().disabled).toBe(true);
  await act(async () => host.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click());
  expect(confirm().disabled).toBe(false);
  await act(async () => confirm().click());
  expect(submit.mock.calls[0][1]).toHaveProperty("attribution", actor);
  vi.mocked(projectQaApi.current).mockRejectedValueOnce(new Error("Grant lookup unavailable"));
  await render({ projectId: "other-project" });
  expect(confirm().disabled).toBe(true); expect(host.textContent).toContain("不会改为创作者确认");
  expect(submit).toHaveBeenCalledOnce();
});

it("refuses copied or stale QA scope without manufacturing creator authority", async () => {
  vi.mocked(projectQaApi.current).mockResolvedValueOnce({ eligible: false, attribution: null, required: true, reason: "原始运行时授权不可用" });
  const submit = vi.spyOn(autopilotApi, "handoff"); await render();
  expect(confirm().disabled).toBe(true); expect(host.textContent).toContain("原始运行时授权不可用");
  await act(async () => confirm().click()); expect(submit).not.toHaveBeenCalled();
});

it("keeps selection available when optional browser image display fails", async () => {
  await render(); await openObservations();
  await act(async () => host.querySelector("img")!.dispatchEvent(new Event("error")));
  expect(confirm().disabled).toBe(false);
  expect(host.textContent).toContain("可按需重试查看");
});

it("records explicit failed and uncertain observations without promoting defaults or production authority", () => {
  const drafts = fixtureMaterial.bundle.frames.map(galleryDraft);
  const unobserved = materialSelectionHandoff(fixtureMaterial, drafts);
  expect(unobserved.frames.every(frame => !frame.qualityObservation)).toBe(true);
  drafts[0].observedCompatibility = true; drafts[0].compatibility = "fail"; drafts[0].comment = "Visible mismatch";
  drafts[0].observedCharacters = ["hero"];
  drafts[0].comparisons[0] = { characterId: "hero", judgment: "unassessable", uncertaintyReason: "Back view", productionDecision: "hold" };
  const selected = materialSelectionHandoff(fixtureMaterial, drafts, "  Exact note\n");
  expect(selected.frames[0].qualityObservation).toEqual({ compatibility: "fail", comment: "Visible mismatch", comparisons: [{ characterId: "hero", judgment: "unassessable", uncertaintyReason: "Back view" }] });
  expect(selected.frames[1]).not.toHaveProperty("qualityObservation"); expect(selected.notes).toBe("  Exact note\n");
});

it("revokes write admission immediately and cannot keep another project's inventory", async () => {
  const submit = vi.spyOn(autopilotApi, "handoff"); await render();
  await render({ readOnly: true }); expect(confirm().disabled).toBe(true);
  vi.mocked(autopilotApi.review).mockRejectedValueOnce(new Error("Read unavailable"));
  await render({ projectId: "other" }); expect(host.textContent).toContain("Read unavailable");
  expect(host.querySelector("footer")).toBeNull(); expect(submit).not.toHaveBeenCalled();
});

it("retains raw material text with exact frame ownership and never restores judgments or authorization", async () => {
  const { materialWorkingInput, resumeMaterialWorkingInput } = await import("../src/features/autopilot/materialWorkingInput");
  const original = fixtureMaterial.bundle.frames.map(galleryDraft), authored = structuredClone(original);
  authored[0].intent.compositionIntent = "unfinished {\n"; authored[0].intent.sourceRefs = ["first", ""];
  authored[0].compatibility = "hold";
  authored[0].comparisons[0] = { ...authored[0].comparisons[0], judgment: "unassessable", productionDecision: "authorize", uncertaintyReason: "author uncertainty" };
  const text = materialWorkingInput(fixtureMaterial, authored, "author notes");
  expect(text).not.toContain('"judgment"'); expect(text).not.toContain('"productionDecision"');
  const resumed = resumeMaterialWorkingInput(text, fixtureMaterial, original);
  expect(resumed.notes).toBe("author notes"); expect(resumed.drafts[0].intent.compositionIntent).toBe("unfinished {\n"); expect(resumed.drafts[0].intent.sourceRefs).toEqual(["first", ""]);
  expect(resumed.drafts[0].comparisons[0].judgment).toBe("unassessable"); expect(resumed.drafts[0].comparisons[0].productionDecision).toBe("hold"); expect(resumed.drafts[0].comparisons[0].uncertaintyReason).toBe("author uncertainty");
  const selected = materialSelectionHandoff(fixtureMaterial, resumed.drafts, resumed.notes);
  expect(selected.frames[0].qualityObservation).toEqual({ comparisons: [{ characterId: "hero", uncertaintyReason: "author uncertainty" }] });
  expect(() => resumeMaterialWorkingInput(text.replace(fixtureMaterial.bundle.frames[0].shotId, "foreign-shot"), fixtureMaterial, original)).toThrow("当前素材");
});
