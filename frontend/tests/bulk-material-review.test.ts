import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { MaterialReview } from "../src/features/autopilot/MaterialReview";
import { autopilotApi } from "../src/features/autopilot/api";
import { fixtureMaterial, fixtureRun } from "./autopilot-fixture";
import { bulkHandoff, galleryDraft, galleryFrameReady } from "../src/features/autopilot/bulkMaterialReview";
import { evidenceReadsFixture } from "./autopilot-delivery-fixture";
import { projectQaApi } from "../src/components/ProjectQaContext";

vi.mock("../src/features/autopilot/useDeliveryEvidence", () => ({ useDeliveryEvidence: () => ({ state: { status: "ready", value: evidenceReadsFixture() }, retry: vi.fn() }) }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement; let root: Root;
const props = { projectId: "disposable", onClose: vi.fn(), onAccepted: vi.fn(), onUncertain: vi.fn() };
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); vi.spyOn(autopilotApi, "review").mockResolvedValue(fixtureMaterial); vi.spyOn(projectQaApi, "current").mockResolvedValue({ eligible: false, attribution: null }); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.clearAllMocks(); });
const confirm = () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "确认全部素材并继续")!;
async function render(extra = {}) { await act(async () => root.render(createElement(MaterialReview, { ...props, ...extra }))); }
async function pixels(event = "load") { await act(async () => { for (const img of host.querySelectorAll("img")) img.dispatchEvent(new Event(event)); }); }

it("one explicit final action submits exact saved context with no typing or per-frame approval", async () => {
  const submit = vi.spyOn(autopilotApi, "handoff").mockResolvedValue(fixtureRun);
  await render(); expect(submit).not.toHaveBeenCalled(); expect(confirm().disabled).toBe(true);
  await pixels(); expect(confirm().disabled).toBe(false);
  expect(host.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
  expect(host.querySelectorAll("details[open]")).toHaveLength(0);
  await act(async () => { confirm().click(); confirm().click(); });
  expect(submit).toHaveBeenCalledOnce();
  const body = submit.mock.calls[0][1];
  expect(body).toEqual(bulkHandoff(fixtureMaterial, fixtureMaterial.bundle.frames.map(galleryDraft), ""));
  expect(body.frames[0].comparisons[0]).toEqual({ characterId: "hero", judgment: "pass" });
  expect(body.frames[1].comparisons).toEqual([]);
  expect(body).not.toHaveProperty("reviewer"); expect(body).not.toHaveProperty("notes");
});

it("granted QA is an explicit visible per-project choice and never falls back on context failure", async () => {
  const actor = { kind: "agent_operated_qa", scopeId: "native-qa" } as const;
  vi.mocked(projectQaApi.current).mockResolvedValueOnce({ eligible: true, attribution: actor });
  const submit = vi.spyOn(autopilotApi, "handoff").mockResolvedValue(fixtureRun);
  await render(); await pixels(); expect(confirm().disabled).toBe(true);
  expect(host.textContent).toContain("明确使用代理 QA 审阅");
  await act(async () => host.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click());
  expect(confirm().disabled).toBe(false);
  await act(async () => confirm().click());
  expect(submit.mock.calls[0][1]).toHaveProperty("attribution", actor);
  vi.mocked(projectQaApi.current).mockRejectedValueOnce(new Error("Grant lookup unavailable"));
  await render({ projectId: "other-project" }); await pixels();
  expect(confirm().disabled).toBe(true); expect(host.textContent).toContain("不会改为创作者确认");
  expect(submit).toHaveBeenCalledOnce();
});

it("known QA projects with unavailable copied or stale grants cannot fall back to creator confirmation", async () => {
  vi.mocked(projectQaApi.current).mockResolvedValueOnce({ eligible: false, attribution: null, required: true, reason: "原始运行时授权不可用；不能改为创作者确认。" });
  const submit = vi.spyOn(autopilotApi, "handoff");
  await render(); await pixels(); expect(confirm().disabled).toBe(true);
  expect(host.textContent).toContain("原始运行时授权不可用");
  expect(host.querySelector('input[type="checkbox"]')).toBeNull();
  await act(async () => confirm().click()); expect(submit).not.toHaveBeenCalled();
});

it("known broken pixels block; retry retains authored state and needs a fresh image read", async () => {
  const submit = vi.spyOn(autopilotApi, "handoff");
  await render(); await pixels(); expect(confirm().disabled).toBe(false);
  await act(async () => host.querySelector("img")!.dispatchEvent(new Event("error")));
  expect(confirm().disabled).toBe(true); expect(host.textContent).toContain("保留原图无法读取");
  await act(async () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "重试读取图片")!.click());
  expect(confirm().disabled).toBe(true); await pixels(); expect(confirm().disabled).toBe(false);
  expect(submit).not.toHaveBeenCalled();
});

it("open review loses write admission immediately and cancels without facts", async () => {
  const submit = vi.spyOn(autopilotApi, "handoff"); await render(); await pixels();
  await render({ readOnly: true }); expect(confirm().disabled).toBe(true);
  await act(async () => host.querySelector<HTMLButtonElement>("header button")!.click());
  expect(props.onClose).toHaveBeenCalledOnce(); expect(submit).not.toHaveBeenCalled();
});

it("a failed current-bundle read is retryable and cannot retain the previous project's consent", async () => {
  await render(); await pixels(); expect(confirm().disabled).toBe(false);
  vi.mocked(autopilotApi.review).mockRejectedValueOnce(new Error("Read unavailable"));
  await render({ projectId: "other" }); expect(host.textContent).toContain("Read unavailable");
  expect(host.querySelector("footer")).toBeNull();
  await act(async () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "重新读取当前素材")!.click());
  expect(confirm().disabled).toBe(true); await pixels(); expect(confirm().disabled).toBe(true);
  expect(host.textContent).toContain("素材来源说明尚待核实");
});

it("every exception blocks the whole pack until separately resolved; uncertainty never becomes pass", () => {
  const draft = galleryDraft(fixtureMaterial.bundle.frames[0]);
  for (const compatibility of ["fail", "hold"] as const) expect(galleryFrameReady({ ...draft, compatibility, comment: "Problem" })).toBe(false);
  draft.comparisons[0] = { characterId: "hero", judgment: "unassessable" };
  expect(galleryFrameReady(draft)).toBe(false);
  draft.comparisons[0].uncertaintyReason = "Intentional back view";
  draft.comparisons[0].productionDecision = "hold"; expect(galleryFrameReady(draft)).toBe(false);
  draft.comparisons[0].productionDecision = "authorize"; expect(galleryFrameReady(draft)).toBe(true);
  expect(bulkHandoff(fixtureMaterial, [draft, galleryDraft(fixtureMaterial.bundle.frames[1])], "  Exact comment\n").frames[0].comparisons[0].judgment).toBe("unassessable");
});

it("long saved source stays exact; intentional edits retain ordinary authored bounds", () => {
  const frame = structuredClone(fixtureMaterial.bundle.frames[0]);
  frame.intentContext.intent.compositionIntent = "saved source ".repeat(200);
  frame.intentContext.intent.sourceEndorsement = { kind: "saved_storyboard", entityRevisionId: "source", revision: 1, contentHash: "f".repeat(64), shotId: frame.shotId };
  const draft = galleryDraft(frame); expect(galleryFrameReady(draft)).toBe(true);
  expect(draft.intent.compositionIntent).toBe(frame.intentContext.intent.compositionIntent);
  delete draft.intent.sourceEndorsement; expect(galleryFrameReady(draft)).toBe(false);
  draft.intent.compositionIntent = "Actual authored edit"; expect(galleryFrameReady(draft)).toBe(true);
});
