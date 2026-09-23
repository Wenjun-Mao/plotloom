import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { ManagedMediaWorkbench } from "../src/features/media/ManagedMediaWorkbench";
import type { ImageJob, VisualWorkbench } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const emptyWorkbench: VisualWorkbench = {
  assets: [], selectionRevision: 1, visualIntents: [], reviewedKeyframes: [],
  characterReferences: { states: [], decisions: [] },
  samePersonReviews: { revision: 0, reviews: [] }, previews: [],
};
const exportedJob: ImageJob = {
  id: "job-1", projectId: "project-1", productionUnitId: "unit-1",
  parentJobId: null, parentCandidateAssetId: null,
  request: { kind: "original" }, requestHash: "hash", state: "exported", current: true,
  exportedAt: "2026-09-23T00:00:00Z", cancelledAt: null,
  cancellationReason: null, createdAt: "2026-09-23T00:00:00Z", deliveries: [],
};

beforeEach(() => {
  vi.useFakeTimers();
  window.sessionStorage.clear();
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getImageJobs").mockResolvedValue({ configured: false, jobs: [exportedJob] });
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockResolvedValue({ configured: false, proposals: [] });
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue({ status: "missing", staleReasons: [], installedStageRevisions: null, installedStoryboardCurrent: false, proposal: null });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, qualifiedDurationSeconds: [5, 8] });
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.useRealTimers(); });

it("withdraws media owner controls and exported-job polling after a same-context read failure", async () => {
  vi.spyOn(plotloomApi, "getVisualWorkbench")
    .mockResolvedValueOnce(emptyWorkbench)
    .mockRejectedValueOnce(new Error("refresh failed"));
  const poll = vi.spyOn(plotloomApi, "refreshImageJob").mockResolvedValue({ state: "accepted", candidates: [] });
  const saveDraft = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  const discardDraft = vi.spyOn(plotloomApi, "discardAuthoringDraft");
  await act(async () => root.render(createElement(ManagedMediaWorkbench, {
    projectId: "project-1", storyboard: demoProject.storyboard,
    bible: demoProject.storyBible, graph: demoProject.storyGraph,
    sceneBeats: demoProject.sceneBeats, selectedShot: demoProject.storyboard.shots[0],
    storyboardRevision: 1, storyBibleRevision: 1, mediaDraftsEnabled: true,
    review: null, readOnly: false,
  })));
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  expect((host.querySelector('[data-testid="managed-image-upload"]') as HTMLInputElement).disabled).toBe(false);
  await act(async () => vi.advanceTimersByTimeAsync(2900));
  const direction = host.querySelector('[data-testid="image-job-presentation-change"]') as HTMLTextAreaElement;
  const valueSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
  await act(async () => {
    valueSetter?.call(direction, "Keep the shot framing");
    direction.dispatchEvent(new Event("input", { bubbles: true }));
  });
  expect(direction.value).toBe("Keep the shot framing");
  expect(host.querySelector('[data-testid="image-job-direction-draft"]')).not.toBeNull();
  await act(async () => vi.advanceTimersByTimeAsync(200));
  expect(poll).toHaveBeenCalledTimes(1);
  expect(host.textContent).toContain("当前角色参考与关键帧状态未知");
  expect((host.querySelector('[data-testid="managed-image-upload"]') as HTMLInputElement).disabled).toBe(true);
  expect(host.querySelector('[data-testid="current-reviewed-keyframe"]')).toBeNull();
  await act(async () => vi.advanceTimersByTimeAsync(3100));
  expect(poll).toHaveBeenCalledTimes(1);
  expect(saveDraft).not.toHaveBeenCalled();
  expect(discardDraft).not.toHaveBeenCalled();
  expect((host.querySelector('[data-testid="image-job-presentation-change"]') as HTMLTextAreaElement).value).toBe("Keep the shot framing");
});
