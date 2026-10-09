import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SamePersonReviewPanel } from "../src/features/media/references/SamePersonReviewPanel";
import type { ReviewedKeyframe, VisualWorkbench } from "../src/types";
import { newSamePersonComparisons } from "../src/features/media/references/same-person-draft";
import { completeSamePersonComparisons, latestCurrentReviewsByBinding } from "../src/features/media/references/same-person-draft";
import type { SamePersonComparisonDraft, SamePersonReview } from "../src/same-person-review-types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const binding: ReviewedKeyframe = { id: "binding", assetId: "candidate", shotId: "shot", sceneId: "scene", selectionRevision: 1, visualIntentId: "intent", visualIntentRevision: 1, compatibilityNote: "matches" };
const workbench: VisualWorkbench = { assets: [], selectionRevision: 1, visualIntents: [], reviewedKeyframes: [binding], characterReferences: { states: [], decisions: [] }, samePersonReviews: { revision: 0, reviews: [] }, previews: [] };
const props = {
  projectId: "project", selectedBinding: binding, selectedIdentityMapping: [{ characterId: "lin", referenceDecisionId: "reference", referenceRevision: 1, assets: [{ assetId: "primary", originalHash: "a".repeat(64) }] }],
  assetById: new Map(), currentReviewByBinding: new Map(), workbench, reviewer: "Codex", notes: "检查记录",
  comparisons: [{ characterId: "lin", judgment: "pass" as const, identityNotes: "同一人物", stateNotes: "当前服装" }],
  setReviewer: vi.fn(), setNotes: vi.fn(), setComparisons: vi.fn(), readOnly: false, busy: false, onRecord: vi.fn(),
};
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); vi.clearAllMocks(); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

it("uses Chinese review instructions while retaining the actual reviewer and judgment values", async () => {
  await act(async () => root.render(createElement(SamePersonReviewPanel, props)));
  expect(host.textContent).toContain("由 Codex 完成的技术或视觉检查，审阅者须写为 Codex");
  expect(host.textContent).toContain("每位角色通过，或无法判断且明确授权投产后");
  expect(host.textContent).toContain("无法确认身份时不要标记通过");
  expect(host.querySelector("select")?.value).toBe("pass");
  expect(host.querySelector('option[value="pass"]')?.textContent).toBe("通过");
  expect(host.querySelector('option[value="fail"]')?.textContent).toBe("不通过");
  expect(host.querySelectorAll('[aria-required="true"]')).toHaveLength(4);
  const record = host.querySelector("button")!;
  expect(record.disabled).toBe(false);
  await act(async () => record.click());
  expect(props.onRecord).toHaveBeenCalledOnce();
});

it("requires an explicit judgment even when all observations are filled", async () => {
  const comparisons = [{ ...props.comparisons[0], judgment: "" as const }];
  await act(async () => root.render(createElement(SamePersonReviewPanel, { ...props, comparisons })));
  expect(host.querySelector("button")?.disabled).toBe(true);
  expect(completeSamePersonComparisons(comparisons)).toBeNull();
});

it.each([undefined, "", "hold", "authorize"] as const)("keeps uncertainty separate from %s production choice", async productionDecision => {
  const comparison: SamePersonComparisonDraft = { ...props.comparisons[0], judgment: "unassessable", productionDecision };
  await act(async () => root.render(createElement(SamePersonReviewPanel, { ...props, comparisons: [comparison] })));
  expect(host.querySelector('[data-testid="same-person-production-lin"]')).not.toBeNull();
  expect(host.querySelector("button")?.disabled).toBe(true);
  await act(async () => root.render(createElement(SamePersonReviewPanel, { ...props, comparisons: [{ ...comparison, uncertaintyReason: "有意只展示双手；接受身份无法辨认的不确定性。" }] })));
  expect(host.querySelector("button")?.disabled).toBe(!productionDecision);
  expect(host.textContent).toContain("接受身份不确定性，明确授权投产");
});

it("labels an authorized unassessable review truthfully and a later refusal blocks the older PASS", async () => {
  const passed: SamePersonReview = { id: "old-pass", projectId: "project", bindingId: "binding", reviewRevision: 1,
    referenceBindings: [], comparisons: props.comparisons, reviewer: "Human", notes: "match", current: true,
    latest: false, productionEligible: false, createdAt: "2026-10-09T00:00:00Z" };
  const latest: SamePersonReview = { ...passed, id: "uncertain", reviewRevision: 2, latest: true, productionEligible: true,
    comparisons: [{ ...passed.comparisons[0], judgment: "unassessable", productionDecision: "authorize", uncertaintyReason: "有意只展示双手，接受身份不确定性。" }] };
  const state = { ...workbench, samePersonReviews: { revision: 2, reviews: [latest, passed] } };
  await act(async () => root.render(createElement(SamePersonReviewPanel, { ...props, workbench: state, currentReviewByBinding: latestCurrentReviewsByBinding(state.samePersonReviews.reviews) })));
  expect(host.textContent).toContain("无法判断 · 已明确授权投产（接受身份不确定性）");
  expect(host.textContent).toContain("已被较新决定取代的复核 old-pass");
  const failed = { ...latest, id: "failed", productionEligible: false, comparisons: [{ ...passed.comparisons[0], judgment: "fail" as const }] };
  const map = latestCurrentReviewsByBinding([failed, passed]);
  expect(map.get("binding")?.id).toBe("failed");
  await act(async () => root.render(createElement(SamePersonReviewPanel, { ...props, currentReviewByBinding: map })));
  expect(host.textContent).toContain("此决定阻止生成视频或创建连续静帧预览");
});

it("does not let localized required markers bypass incomplete review notes", async () => {
  await act(async () => root.render(createElement(SamePersonReviewPanel, { ...props, comparisons: [{ ...props.comparisons[0], identityNotes: "" }] })));
  expect(host.querySelector("button")?.disabled).toBe(true);
  await act(async () => host.querySelector("button")!.click());
  expect(props.onRecord).not.toHaveBeenCalled();
});

it("starts new identity reviews without fabricated findings and requires both observations", async () => {
  const comparisons = newSamePersonComparisons([{ characterId: "lin" }]);
  expect(comparisons).toEqual([{ characterId: "lin", judgment: "", identityNotes: "", stateNotes: "" }]);
  await act(async () => root.render(createElement(SamePersonReviewPanel, { ...props, comparisons })));
  expect(host.querySelector("button")?.disabled).toBe(true);
  expect(host.querySelector('input[placeholder^="比较面貌"]')?.getAttribute("value")).toBe("");
  await act(async () => root.render(createElement(SamePersonReviewPanel, { ...props, comparisons: [{ ...comparisons[0], identityNotes: "面貌一致" }] })));
  expect(host.querySelector("button")?.disabled).toBe(true);
  expect(props.onRecord).not.toHaveBeenCalled();
});
