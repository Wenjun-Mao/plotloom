import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { ManagedMediaWorkbench } from "../src/features/media/ManagedMediaWorkbench";
import type { ManagedAsset, ReviewedKeyframe, Shot, StoryboardReview, VisualIntent, VisualWorkbench } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const shot = demoProject.storyboard.shots[0];
const otherShot = { ...shot, id: "other-shot" };
const storyboard = { ...demoProject.storyboard, shots: [shot, otherShot] };
const assets: ManagedAsset[] = ["old-asset", "new-asset", "other-asset"].map((id) => ({
  id, projectId: "project", originalHash: "a".repeat(64), displayHash: "b".repeat(64),
  mimeType: "image/png", byteSize: 1024, width: 832, height: 480, createdAt: "2026-10-02T00:00:00Z",
  provenance: { origin: "manual", rights: "unknown", rightsNote: null, declaredAdditions: [] },
}));
const intent = (assetId: string): VisualIntent => ({
  id: `${assetId}-intent`, assetId, revision: 1,
  intent: { role: "shot_keyframe", sourceRefs: [`${assetId}-source`] },
});
const binding = (assetId = "old-asset", selectedShot = shot, id = `${assetId}-binding`): ReviewedKeyframe => ({
  id, assetId, shotId: selectedShot.id, sceneId: selectedShot.sceneId,
  selectionRevision: 9, visualIntentId: intent(assetId).id, visualIntentRevision: 1,
  compatibilityNote: "reviewed framing",
});
const snapshot = (bindings = [binding()], intents = [intent("old-asset")]): VisualWorkbench => ({
  assets, selectionRevision: 9, visualIntents: intents, reviewedKeyframes: bindings,
  characterReferences: { states: [], decisions: [] },
  samePersonReviews: { revision: 0, reviews: [] }, previews: [],
});
const review: StoryboardReview = {
  head: {} as StoryboardReview["head"], gateEvaluation: null, decisions: [],
  activeApproval: {
    id: "approval", projectId: "project", entityRevisionId: "storyboard-head",
    subjectType: "storyboard", subjectId: "storyboard", subjectRevision: 1,
    contentHash: "hash", canonicalInputRevisions: {}, gateSetVersion: "gates",
    decision: "approve", reviewer: "creator", note: null, createdAt: "2026-10-02T00:00:00Z",
  },
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function render(selectedShot: Shot = shot, projectId = "project", mediaDraftsEnabled = false) {
  await act(async () => root.render(createElement(ManagedMediaWorkbench, {
    projectId, storyboard, bible: demoProject.storyBible, graph: demoProject.storyGraph,
    sceneBeats: demoProject.sceneBeats, selectedShot, storyboardRevision: 1,
    storyBibleRevision: 1, mediaDraftsEnabled, review, readOnly: false,
  })));
  await settle();
}
async function settle() { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); }
function control<T extends HTMLElement>(testId: string) { return host.querySelector<T>(`[data-testid="${testId}"]`)!; }
function kept(assetId: string) { return control(`keep-candidate-${assetId}`).getAttribute("aria-pressed"); }
async function click(testId: string) { await act(async () => control<HTMLButtonElement>(testId).click()); await settle(); }
async function edit(element: HTMLTextAreaElement, value: string) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function refreshThroughImport() {
  await act(async () => {
    const upload = control<HTMLInputElement>("managed-image-upload");
    Object.defineProperty(upload, "files", { configurable: true, value: [new File(["image"], "image.png")] });
    upload.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await settle();
}

beforeEach(() => {
  sessionStorage.clear(); localStorage.clear();
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getImageJobs").mockResolvedValue({ configured: false, jobs: [] });
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockResolvedValue({ configured: false, proposals: [] });
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue({ status: "missing", staleReasons: [], installedStageRevisions: null, installedStoryboardCurrent: false, proposal: null });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, qualifiedDurationSeconds: [5, 8] });
  vi.spyOn(plotloomApi, "importManagedAsset").mockResolvedValue(assets[0]);
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.useRealTimers(); });

it("reviews the explicitly retained replacement after intent save withdraws and restores the old binding", async () => {
  vi.useFakeTimers();
  const pending = deferred<VisualWorkbench>();
  const get = vi.spyOn(plotloomApi, "getVisualWorkbench")
    .mockResolvedValueOnce(snapshot())
    .mockImplementationOnce(() => pending.promise)
    .mockResolvedValueOnce(snapshot([binding("new-asset")], [intent("old-asset"), intent("new-asset")]));
  const save = vi.spyOn(plotloomApi, "createVisualIntent").mockResolvedValue(intent("new-asset"));
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockResolvedValue({ draftRevision: 1 } as never);
  const select = vi.spyOn(plotloomApi, "selectReviewedKeyframe").mockResolvedValue({ id: "new-asset-binding", selectionRevision: 10 });
  await render(shot, "project", true);
  expect(kept("old-asset")).toBe("true");
  await click("keep-candidate-new-asset");
  await edit(control<HTMLTextAreaElement>("visual-intent-source-refs"), "new-asset-source");
  await act(async () => vi.advanceTimersByTimeAsync(750));
  expect(control<HTMLButtonElement>("save-visual-intent").disabled).toBe(false);
  await click("save-visual-intent");
  expect(save).toHaveBeenCalledWith("project", "new-asset", expect.objectContaining({
    sourceRefs: ["new-asset-source"],
    consumedDraft: { editorScope: "visual_intent", entityId: `${shot.id}:new-asset`, draftRevision: 1 },
  }));
  expect(get).toHaveBeenCalledTimes(2);
  expect(control<HTMLInputElement>("managed-image-upload").disabled).toBe(true);
  expect(host.querySelector('[data-testid="current-reviewed-keyframe"]')).toBeNull();
  expect(control<HTMLTextAreaElement>("visual-intent-source-refs").value).toBe("new-asset-source");
  await act(async () => pending.resolve(snapshot([binding()], [intent("old-asset"), intent("new-asset")])));
  await settle();
  expect(kept("new-asset")).toBe("true");
  expect(kept("old-asset")).toBe("false");
  expect(control<HTMLTextAreaElement>("visual-intent-source-refs").value).toBe("new-asset-source");
  const compatibility = Array.from(host.querySelectorAll("label")).find((label) => label.textContent?.includes("审核兼容性说明"))!.querySelector("textarea")!;
  await edit(compatibility, "Replacement matches the approved shot.");
  expect(control<HTMLButtonElement>("select-reviewed-keyframe").disabled).toBe(false);
  await click("select-reviewed-keyframe");
  expect(select).toHaveBeenCalledWith("project", expect.objectContaining({
    assetId: "new-asset", visualIntentId: "new-asset-intent", visualIntentRevision: 1,
    shotId: shot.id, expectedSelectionRevision: 9,
  }));
});

it("preserves explicit retention through failure and retry of an unchanged binding", async () => {
  const pending = deferred<VisualWorkbench>();
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValueOnce(snapshot())
    .mockImplementationOnce(() => pending.promise).mockResolvedValueOnce(snapshot());
  await render(); await click("keep-candidate-new-asset");
  await refreshThroughImport();
  await act(async () => pending.reject(new Error("offline"))); await settle();
  expect(control<HTMLInputElement>("managed-image-upload").disabled).toBe(true);
  expect(host.querySelector('[data-testid="current-reviewed-keyframe"]')).toBeNull();
  await act(async () => Array.from(host.querySelectorAll("button")).find((button) => button.textContent?.includes("重试媒体读取"))!.click());
  await settle();
  expect(kept("new-asset")).toBe("true");
});

it("restores genuine binding changes and clears authoritative removal", async () => {
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValueOnce(snapshot())
    .mockResolvedValueOnce(snapshot([binding("other-asset")]))
    .mockResolvedValueOnce(snapshot([]));
  await render(); await click("keep-candidate-new-asset");
  await refreshThroughImport(); expect(kept("other-asset")).toBe("true");
  await refreshThroughImport(); expect(kept("other-asset")).toBe("false");
  expect(host.querySelector('[data-testid="visual-intent-source-refs"]')).toBeNull();
});

it("initializes each project and Shot independently, including unbound Shots and reload", async () => {
  const pending = deferred<VisualWorkbench>();
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValueOnce(snapshot())
    .mockImplementationOnce(() => pending.promise)
    .mockResolvedValueOnce(snapshot())
    .mockResolvedValueOnce(snapshot([binding("other-asset")]))
    .mockResolvedValueOnce(snapshot([binding("other-asset")]));
  await render(); await click("keep-candidate-new-asset");
  await render(otherShot);
  expect(host.querySelector('[data-testid="visual-intent-source-refs"]')).toBeNull();
  await act(async () => pending.resolve(snapshot())); await settle();
  expect(kept("new-asset")).toBe("false"); expect(kept("old-asset")).toBe("false");
  await render(shot); expect(kept("old-asset")).toBe("true");
  await click("keep-candidate-new-asset");
  await render(shot, "other-project"); expect(kept("other-asset")).toBe("true");
  await click("keep-candidate-new-asset");
  await act(async () => root.unmount()); root = createRoot(host);
  await render(shot, "other-project"); expect(kept("other-asset")).toBe("true");
});
