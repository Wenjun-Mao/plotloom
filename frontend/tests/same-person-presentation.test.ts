import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SamePersonReviewPanel } from "../src/features/media/references/SamePersonReviewPanel";
import type { ReviewedKeyframe, VisualWorkbench } from "../src/types";

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
  expect(host.textContent).toContain("完成复核后才能纳入连续静帧预览");
  expect(host.querySelector("select")?.value).toBe("pass");
  expect(host.querySelector('option[value="pass"]')?.textContent).toBe("通过");
  expect(host.querySelector('option[value="fail"]')?.textContent).toBe("不通过");
  expect(host.querySelectorAll('[aria-required="true"]')).toHaveLength(4);
  const record = host.querySelector("button")!;
  expect(record.disabled).toBe(false);
  await act(async () => record.click());
  expect(props.onRecord).toHaveBeenCalledOnce();
});

it("does not let localized required markers bypass incomplete review notes", async () => {
  await act(async () => root.render(createElement(SamePersonReviewPanel, { ...props, comparisons: [{ ...props.comparisons[0], identityNotes: "" }] })));
  expect(host.querySelector("button")?.disabled).toBe(true);
  await act(async () => host.querySelector("button")!.click());
  expect(props.onRecord).not.toHaveBeenCalled();
});
