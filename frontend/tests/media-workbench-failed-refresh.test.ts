import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { ManagedMediaWorkbench } from "../src/features/media/ManagedMediaWorkbench";
import type { ImageJob, ManagedAsset, VisualWorkbench } from "../src/types";

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
  request: { kind: "original", frozenSnapshot: { shot: { id: demoProject.storyboard.shots[0].id } } }, requestHash: "hash", state: "exported", current: true,
  exportedAt: "2026-09-23T00:00:00Z", cancelledAt: null,
  cancellationReason: null, createdAt: "2026-09-23T00:00:00Z", deliveries: [],
};

beforeEach(() => {
  vi.useFakeTimers();
  window.sessionStorage.clear();
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getImageJobs").mockResolvedValue({ configured: false, jobs: [exportedJob] });
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockResolvedValue({ configured: false, proposals: [] });
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue({ intentGeneration: { status: "unavailable", reason: "not_configured" }, status: "missing", staleReasons: [], installedStageRevisions: null, installedStoryboardCurrent: false, hasInstallation: false, proposal: null });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, qualifiedDurationSeconds: [5, 8] });
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.useRealTimers(); });

it("renders a mixed-origin gallery from the common provenance DTO and keeps candidate controls usable", async () => {
  const assets: ManagedAsset[] = ["art_reference_proposal", "plotloom_keyframe_center_crop", "character_reference_proposal", "manual"].map((origin, index) => ({
    id: `asset-${index}`, projectId: "project-1", originalHash: "a".repeat(64), displayHash: "b".repeat(64),
    mimeType: "image/png", byteSize: 1024, width: 832, height: 480, createdAt: "2026-10-02T00:00:00Z",
    provenance: { origin, rights: "unknown", rightsNote: null, declaredAdditions: index === 3 ? ["lamp"] : [] },
  }));
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValue({ ...emptyWorkbench, assets });
  await act(async () => root.render(createElement(ManagedMediaWorkbench, {
    projectId: "project-1", storyboard: demoProject.storyboard,
    bible: demoProject.storyBible, graph: demoProject.storyGraph,
    sceneBeats: demoProject.sceneBeats, selectedShot: demoProject.storyboard.shots[0],
    storyboardRevision: 1, storyBibleRevision: 1, mediaDraftsEnabled: false, review: null, readOnly: false,
  })));
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  const cards = host.querySelectorAll('.media-candidate-grid[aria-label="候选图像比较"] .media-candidate');
  expect(cards.length).toBe(4);
  for (const origin of assets.map((asset) => asset.provenance!.origin)) expect(host.textContent).toContain(origin);
  expect(host.textContent).toContain("已知新增：lamp");
  await act(async () => (cards[0].querySelector("button") as HTMLButtonElement).click());
  expect(cards[0].querySelector("button")?.getAttribute("aria-pressed")).toBe("true");
});

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
  expect(host.textContent).not.toContain("尚未配置同机 exchange root");
  expect(host.textContent).not.toContain("尚未选择身份参考");
  expect(host.textContent).not.toContain("尚无 P1 job");
  expect((host.querySelector('[data-testid="managed-image-upload"]') as HTMLInputElement).disabled).toBe(true);
  expect(host.querySelector('[data-testid="current-reviewed-keyframe"]')).toBeNull();
  await act(async () => vi.advanceTimersByTimeAsync(3100));
  expect(poll).toHaveBeenCalledTimes(1);
  expect(saveDraft).not.toHaveBeenCalled();
  expect(discardDraft).not.toHaveBeenCalled();
  expect((host.querySelector('[data-testid="image-job-presentation-change"]') as HTMLTextAreaElement).value).toBe("Keep the shot framing");
});

it("keeps project image history accessible and attributes jobs to their frozen shots", async () => {
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValue(emptyWorkbench);
  vi.mocked(plotloomApi.getImageJobs).mockResolvedValue({ configured: true, jobs: [exportedJob, {
    ...exportedJob, id: "foreign-job", state: "cancelled", current: false,
    request: { kind: "original", frozenSnapshot: { shot: { id: "foreign-shot" } } },
  }] });
  await act(async () => root.render(createElement(ManagedMediaWorkbench, {
    projectId: "project-1", storyboard: demoProject.storyboard, bible: demoProject.storyBible,
    graph: demoProject.storyGraph, sceneBeats: demoProject.sceneBeats,
    selectedShot: demoProject.storyboard.shots[0], storyboardRevision: 1,
    storyBibleRevision: 1, mediaDraftsEnabled: false, review: null, readOnly: false,
  })));
  expect(host.querySelector('[data-testid="image-job-job-1"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="image-job-foreign-job"]')).toBeNull();
  const history = [...host.querySelectorAll("button")].find(button => button.textContent?.startsWith("查看全项目请求历史"))!;
  await act(async () => history.click());
  expect(host.querySelector('[data-testid="image-job-foreign-job"]')?.textContent).toContain("镜头：foreign-shot");
  const scoped = [...host.querySelectorAll("button")].find(button => button.textContent === "只看当前镜头请求")!;
  await act(async () => scoped.click());
  expect(host.querySelector('[data-testid="image-job-foreign-job"]')).toBeNull();
});
