import { batchApi } from "../src/features/video-batch/api";
import { projectQaApi } from "../src/components/ProjectQaContext";
import { readyProductionBatch } from "./h3-production-fixtures";
import type { Batch } from "../src/features/video-batch/contracts";
import type { VideoJobPrepareBody } from "../src/api";
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi, type H3PromptPreview } from "../src/api";
import { demoProject } from "../src/demo";
import { ManagedMediaWorkbench } from "../src/features/media/ManagedMediaWorkbench";
import { bridgeState } from "./production-bridge-fixture";
import type { ImageJob, ManagedAsset, ReviewedKeyframe, StoryboardReview, VideoBackend, VisualWorkbench } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const shot = { ...demoProject.storyboard.shots[0], durationUnits: 5_000 };
const keyframe: ManagedAsset = {
  id: "a1-frame", projectId: "project", originalHash: "a".repeat(64), displayHash: "b".repeat(64),
  mimeType: "image/png", byteSize: 1, width: 832, height: 480, createdAt: "2026-10-02T00:00:00Z", provenance: null,
};
const binding: ReviewedKeyframe = {
  id: "a1-binding", assetId: keyframe.id, shotId: shot.id, sceneId: shot.sceneId,
  selectionRevision: 7, visualIntentId: "a1-intent", visualIntentRevision: 1, compatibilityNote: "matches",
};
const snapshot = (selected = binding, selectionRevision = 7, reviewId = "a1-review"): VisualWorkbench => ({
  assets: [keyframe], selectionRevision, visualIntents: [], reviewedKeyframes: [selected],
  characterReferences: { states: [], decisions: [] }, previews: [],
  samePersonReviews: { revision: 1, reviews: [{
    id: reviewId, projectId: "project", bindingId: selected.id, reviewRevision: 1,
    referenceBindings: [], comparisons: [], reviewer: "creator", notes: "matches", current: true, latest: true, productionEligible: true,
    createdAt: "2026-10-02T00:00:00Z",
  }] },
});
const exported: ImageJob = {
  id: "b2-export", projectId: "project", productionUnitId: "b2-unit", parentJobId: null,
  parentCandidateAssetId: null, request: { kind: "original" }, requestHash: "hash",
  state: "exported", current: true, exportedAt: "2026-10-02T00:00:00Z", cancelledAt: null,
  cancellationReason: null, createdAt: "2026-10-02T00:00:00Z", deliveries: [],
};
const backend: VideoBackend = {
  enabled: true, adapterId: "minimax_h3_gateway", nativeAudio: true, tracksPaidWanPilot: false,
  qualifiedDurationSeconds: [5, 8], defaultProfileId: "landscape",
  profiles: [{ id: "landscape", version: 2, label: "Landscape", quality: 8, orientation: "landscape",
    tier: "fast", width: 832, height: 480, durationSeconds: 5, fps: 24, frameCount: 124, nativeAudio: true }],
};
const review: StoryboardReview = {
  head: {} as StoryboardReview["head"], gateEvaluation: null, decisions: [],
  activeApproval: {
    id: "approval", projectId: "project", entityRevisionId: "head", subjectType: "storyboard",
    subjectId: "storyboard", subjectRevision: 1, contentHash: "hash", canonicalInputRevisions: {},
    gateSetVersion: "gates", decision: "approve", reviewer: "creator", note: null, createdAt: "2026-10-02T00:00:00Z",
  },
};
const source = (hash = "c"): H3PromptPreview => ({
  sourceHash: hash.repeat(64), compiledPrompt: null,
  sources: [{ path: "shot.action", text: "A1 authored action", label: "动作" }],
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const button = (name: string) => Array.from(host.querySelectorAll<HTMLButtonElement>("button")).find((item) => item.textContent === name)!;
const editor = () => host.querySelector<HTMLTextAreaElement>('.h3-directions-review textarea')!;
const seed = () => host.querySelector<HTMLInputElement>('[aria-label="H3 随机种子"]')!;
const authorityDisabled = () => !button("授权本镜头制作意图并开始生成") || button("授权本镜头制作意图并开始生成").disabled;
async function settle() { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); }
async function click(name: string) { await act(async () => button(name).click()); await settle(); }
async function edit(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
  await act(async () => {
    const prototype = element instanceof HTMLInputElement ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function render(lifecycleRevision?: number, readOnly = false) {
  await act(async () => root.render(createElement(ManagedMediaWorkbench, {
    projectId: "project", lifecycleRevision, storyboard: { ...demoProject.storyboard, shots: [shot] },
    bible: demoProject.storyBible, graph: demoProject.storyGraph, sceneBeats: demoProject.sceneBeats,
    selectedShot: shot, storyboardRevision: 1, mediaDraftsEnabled: false,
    review, readOnly,
  })));
  await settle();
}
async function beginReview() {
  await render(); await edit(seed(), "4215546708741480"); await click("读取当前来源");
  await edit(editor(), "The keeper crosses the doorway.");
}
async function poll() { await act(async () => vi.advanceTimersByTimeAsync(3_000)); await settle(); }

beforeEach(() => {
  vi.spyOn(batchApi, "current").mockResolvedValue(null);
  vi.spyOn(projectQaApi, "current").mockResolvedValue({ eligible: false, required: false, attribution: null });
  vi.useFakeTimers(); sessionStorage.clear(); localStorage.clear();
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getImageJobs").mockResolvedValueOnce({ configured: true, jobs: [exported] })
    .mockResolvedValue({ configured: true, jobs: [] });
  vi.spyOn(plotloomApi, "refreshImageJob").mockResolvedValue({ state: "accepted", candidates: [] });
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockResolvedValue({ configured: false, proposals: [] });
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridgeState({ intentGeneration: { status: "unavailable", reason: "not_configured" } }));
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue(backend);
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValue({ revision: 0, assetId: null });
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [keyframe] });
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.useRealTimers(); });

it.each(["c", "e"])("retains seed through unrelated polling and reuses English only for exact hash %s", async (hash) => {
  const pending = deferred<VisualWorkbench>();
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValueOnce(snapshot()).mockReturnValueOnce(pending.promise);
  const preview = vi.spyOn(plotloomApi, "previewH3Prompt").mockResolvedValueOnce(source())
    .mockResolvedValueOnce(source(hash));
  const freeze = vi.spyOn(plotloomApi, "prepareVideoJob").mockResolvedValue({} as never);
  await beginReview();
  expect(authorityDisabled()).toBe(true);
  await poll();
  expect(vi.mocked(plotloomApi.refreshImageJob)).toHaveBeenCalledWith("project", exported.id);
  expect(seed().value).toBe("4215546708741480"); expect(editor().value).toBe("The keeper crosses the doorway.");
  expect(editor().disabled).toBe(true); expect(authorityDisabled()).toBe(true);
  expect(button("读取当前来源").disabled).toBe(true); expect(authorityDisabled()).toBe(true);
  await click("读取当前来源"); expect(preview).toHaveBeenCalledTimes(1); expect(freeze).not.toHaveBeenCalled();
  await act(async () => pending.resolve(snapshot(binding, 8))); await settle();
  expect(seed().value).toBe("4215546708741480"); expect(editor().disabled).toBe(true);
  expect(authorityDisabled()).toBe(true);
  await click("读取当前来源");
  expect(preview.mock.calls[1][1]).toMatchObject({ seed: 4215546708741480, expectedSelectionRevision: 8 });
  expect(editor().value).toBe(hash === "c" ? "The keeper crosses the doorway." : "");
  expect(authorityDisabled()).toBe(true); expect(freeze).not.toHaveBeenCalled();
  // Preserved prose is only an editable candidate. The new request must still
  // acquire a complete brief and independent check before generation authority.
  expect(button("准备本镜头制作简报")).toBeDefined(); expect(freeze).not.toHaveBeenCalled();
});

it.each([["read", "resolve"], ["read", "reject"], ["setup", "resolve"], ["setup", "reject"]])("ignores late %s/%s callbacks withdrawn by polling and retains buffer through read failure/retry", async (operation, disposition) => {
  const pendingMedia = deferred<VisualWorkbench>();
  const reconciliationRetry = deferred<VisualWorkbench>();
  const pendingPrompt = deferred<H3PromptPreview>();
  const pendingSetup = deferred<Batch>();
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValueOnce(snapshot())
    .mockReturnValueOnce(pendingMedia.promise).mockReturnValueOnce(reconciliationRetry.promise).mockResolvedValueOnce(snapshot());
  const preview = vi.spyOn(plotloomApi, "previewH3Prompt").mockResolvedValueOnce(source()).mockResolvedValue(source());
  const freeze = vi.spyOn(plotloomApi, "prepareVideoJob");
  await beginReview();
  if (operation === "read") preview.mockReturnValueOnce(pendingPrompt.promise);
  else vi.spyOn(batchApi, "command").mockReturnValueOnce(pendingSetup.promise);
  await click(operation === "read" ? "读取当前来源" : "准备本镜头制作简报");
  await poll();
  await act(async () => pendingMedia.reject(new Error("offline"))); await settle();
  await act(async () => reconciliationRetry.reject(new Error("still offline"))); await settle();
  expect(editor().value).toBe("The keeper crosses the doorway."); expect(seed().value).toBe("4215546708741480");
  expect(button("读取当前来源").disabled).toBe(true);
  await act(async () => {
    if (operation === "read") disposition === "resolve" ? pendingPrompt.resolve(source("e")) : pendingPrompt.reject(new Error("late prompt failure"));
    else disposition === "resolve" ? pendingSetup.resolve(readyProductionBatch({ approvalId: "approval", shotId: shot.id, storyboardRevision: 1, expectedSelectionRevision: 7, seed: 4215546708741480, idempotencyKey: "late-old-key", profileId: "landscape" } as VideoJobPrepareBody)) : pendingSetup.reject(new Error("late prompt failure"));
  }); await settle();
  expect(editor().value).toBe("The keeper crosses the doorway."); expect(host.textContent).not.toContain("Exact reviewed prompt");
  expect(host.textContent).not.toContain("late prompt failure");
  await act(async () => Array.from(host.querySelectorAll("button")).find((item) => item.textContent?.includes("重试媒体读取"))!.click());
  await settle(); expect(editor().disabled).toBe(true); expect(authorityDisabled()).toBe(true);
  await click("读取当前来源");
  expect(editor().value).toBe("The keeper crosses the doorway."); expect(editor().disabled).toBe(false);
  expect(preview).toHaveBeenCalledTimes(operation === "read" ? 3 : 2); expect(freeze).not.toHaveBeenCalled();
});

it.each(["binding", "intent", "review"])("invalidates the buffer for a genuine ready %s change", async (change) => {
  const pending = deferred<VisualWorkbench>();
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValueOnce(snapshot()).mockReturnValueOnce(pending.promise);
  vi.spyOn(plotloomApi, "previewH3Prompt").mockResolvedValue(source());
  await beginReview(); await poll();
  const nextBinding = change === "binding" ? { ...binding, id: "new-binding" }
    : change === "intent" ? { ...binding, visualIntentId: "new-intent", visualIntentRevision: 2 } : binding;
  await act(async () => pending.resolve(snapshot(nextBinding, 8, change === "review" ? "new-review" : "a1-review"))); await settle();
  if (change === "review") {
    expect(editor().value).toBe("The keeper crosses the doorway.");
    expect(editor().disabled).toBe(true); // Still needs an explicit fresh source read.
  } else {
    expect(editor()).toBeNull(); expect(authorityDisabled()).toBe(true);
    expect(host.textContent).not.toContain("来源绑定：");
  }
});

it("retains English and seed through archive/restore reads while withdrawing consent and freeze authority", async () => {
  const archivedMedia = deferred<VisualWorkbench>();
  const archivedVideos = deferred<Awaited<ReturnType<typeof plotloomApi.getVideoJobs>>>();
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValueOnce(snapshot())
    .mockReturnValueOnce(archivedMedia.promise).mockResolvedValueOnce(snapshot());
  vi.mocked(plotloomApi.getVideoJobs).mockResolvedValueOnce({ jobs: [] })
    .mockReturnValueOnce(archivedVideos.promise).mockResolvedValueOnce({ jobs: [] });
  vi.spyOn(plotloomApi, "previewH3Prompt").mockResolvedValueOnce(source()).mockResolvedValue(source());
  const freeze = vi.spyOn(plotloomApi, "prepareVideoJob");
  await render(1); await edit(seed(), "4215546708741480"); await click("读取当前来源");
  await edit(editor(), "The keeper crosses the doorway.");
  const originalEditor = editor();
  await render(2, true);
  expect(editor()).toBe(originalEditor);
  expect(editor().value).toBe("The keeper crosses the doorway.");
  expect(seed().value).toBe("4215546708741480"); expect(authorityDisabled()).toBe(true);
  expect(button("读取当前来源").disabled).toBe(true);
  expect(authorityDisabled()).toBe(true);
  expect(host.querySelector(".video-workflow-nav")).toBeNull();
  await act(async () => { archivedMedia.resolve(snapshot()); archivedVideos.resolve({ jobs: [] }); }); await settle();
  expect(editor()).toBe(originalEditor); expect(editor().value).toBe("The keeper crosses the doorway.");
  await render(3);
  expect(editor()).toBe(originalEditor); expect(seed().value).toBe("4215546708741480");
  await click("读取当前来源");
  expect(editor().value).toBe("The keeper crosses the doorway."); expect(authorityDisabled()).toBe(true);
  expect(freeze).not.toHaveBeenCalled();
  expect(plotloomApi.getVideoJobs).toHaveBeenCalledTimes(3);
});
