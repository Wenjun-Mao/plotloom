import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { VideoPilotPanel, selectedRouteVideos } from "../src/video-pilot";
import { BranchingVideoPreview, branchingPreviewManifest } from "../src/branching-video-preview";
import { VideoSegmentReview } from "../src/video-segment-review";
import { plotloomApi } from "../src/api";
import { isCurrentVideoSelection, videoNextAction } from "../src/features/media/video-next-action";
import { frozenVideoSnapshot } from "../src/features/media/frozen-video-snapshot";
import { bridgeState, installedProduction } from "./production-bridge-fixture";
import type { ManagedAsset, SceneBeatPlan, Shot, StoryGraph, Storyboard, VideoBackend, VideoJob } from "../src/types";
import { branchingFixture, deferred, endingJob, job, props, routeContext, selectedJob } from "./video-pilot-fixtures";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;

let host: HTMLDivElement;

const dialogDescriptors = ["showModal", "close"].map(name => Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name));

async function render(projectId: string, shotId: string, sceneId?: string) {
  await act(async () => root.render(createElement(VideoPilotPanel, props(projectId, shotId, sceneId))));
  await act(async () => { await Promise.resolve(); });
}

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValue({ revision: 0, assetId: null });
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({
    enabled: true, adapterId: "atlas_wan", adapterVersion: "1", provider: "atlascloud",
    model: "alibaba/wan-3.0/image-to-video", durationSeconds: 5, resolution: "720p",
    nativeAudio: true, requiresAspectPolicy: false, tracksPaidWanPilot: true,
  } satisfies VideoBackend);
});

afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); ["showModal", "close"].forEach((name, index) => { if (dialogDescriptors[index]) Object.defineProperty(HTMLDialogElement.prototype, name, dialogDescriptors[index]!); else Reflect.deleteProperty(HTMLDialogElement.prototype, name); }); });

it("prepares a synthetic review window without auto-selecting and ignores late unmounted work", async () => {
  const candidate = selectedJob("segment-candidate", 1, {
    selected: false, playbackSegment: null,
    observed: { durationSeconds: 8, width: 576, height: 1024, videoCodec: "h264", audioCodec: "aac", frameRate: 24, frameCount: 192 },
    requestedSeconds: 8,
    snapshot: { shot: { id: "shot-1", sceneId: "scene", durationUnits: 6_000 }, sourceTiming: { kind: "canonical", durationUnits: 6_000 } },
  });
  const delayed = deferred<NonNullable<VideoJob["playbackSegment"]>>();
  const prepare = vi.spyOn(plotloomApi, "prepareVideoSegment").mockReturnValue(delayed.promise);
  const select = vi.spyOn(plotloomApi, "selectVideoSegment").mockResolvedValue({} as never);
  const refresh = vi.fn().mockResolvedValue(undefined);
  await act(async () => root.render(createElement(VideoSegmentReview, { projectId: "old", job: candidate, readOnly: false, onRefresh: refresh })));
  await act(async () => { [...host.querySelectorAll("button")].find((item) => item.textContent?.includes("准备播放片段"))?.click(); });
  expect(prepare).toHaveBeenCalledWith("old", candidate.id, 0, 144, 0);
  expect(select).not.toHaveBeenCalled();
  await act(async () => root.render(createElement(VideoSegmentReview, { projectId: "new", job: candidate, readOnly: false, onRefresh: refresh })));
  delayed.resolve({ ...selectedJob("segment-candidate", 1).playbackSegment!, id: "old-proposal", selected: false });
  await act(async () => { await delayed.promise; await Promise.resolve(); });
  expect(refresh).not.toHaveBeenCalled();
  expect(select).not.toHaveBeenCalled();
});

it("keeps a rejected H3 take locked until its review is explicitly reopened", async () => {
  const segment = selectedJob("rejected-h3", 1).playbackSegment!;
  const candidate = selectedJob("rejected-h3", 1, {
    segments: [{ ...segment, selected: false }], playbackSegment: null, selected: false,
    requestedSeconds: 8,
    snapshot: { shot: { id: "shot-1", durationUnits: 6_000 }, sourceTiming: { kind: "canonical", durationUnits: 6_000 } },
    observed: { durationSeconds: 8, width: 576, height: 1024, videoCodec: "h264", audioCodec: "aac", frameRate: 24, frameCount: 192 },
    reviews: [{ id: "reject-review", reviewer: "creator", decision: "reject", note: "Unsafe cut", createdAt: "2026-09-23T00:00:00Z" }],
  });
  await act(async () => root.render(createElement(VideoSegmentReview, {
    projectId: "project", job: candidate, readOnly: false, onRefresh: async () => undefined,
  })));
  expect(host.textContent).toContain("此原片已拒绝");
  expect([...host.querySelectorAll("button")].find((item) => item.textContent?.includes("准备播放片段"))?.disabled).toBe(true);
  expect([...host.querySelectorAll("button")].find((item) => item.textContent?.includes("确认用于故事"))?.disabled).toBe(true);
  const reopenPanel = host.querySelector('[data-testid="video-review-reopen-rejected-h3"]')!;
  expect(reopenPanel.querySelector("input")?.required).toBe(true);
  expect(reopenPanel.querySelector("textarea")?.required).toBe(true);
  expect([...reopenPanel.querySelectorAll("button")].find((item) => item.textContent === "重新开放审阅")?.disabled).toBe(true);
});

it("reopens a rejected H3 review with required annotations and refreshes distinct history only", async () => {
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, reason: "h3_video_not_configured", qualifiedDurationSeconds: [5, 8] });
  const segment = selectedJob("review-reopen", 1).playbackSegment!;
  const rejected = selectedJob("review-reopen", 1, {
    selected: false, playbackSegment: null,
    segments: [{ ...segment, selected: false }],
    selectionRevision: 0,
    requestedSeconds: 8,
    observed: { durationSeconds: 8, width: 576, height: 1024, videoCodec: "h264", audioCodec: "aac", frameRate: 24, frameCount: 192 },
    snapshot: {
      provider: { adapterId: "minimax_h3_gateway" },
      shot: { id: "shot-1", title: "Shot 1", sceneId: "scene", order: 1, durationUnits: 6_000 },
      sourceTiming: { kind: "canonical", durationUnits: 6_000 },
    },
    reviews: [{ id: "old-rejection", reviewer: "creator", decision: "reject", note: "Unsafe cut", createdAt: "2026-09-23T00:00:00Z" }],
  });
  const reopened: VideoJob = {
    ...rejected, selectionRevision: 1,
    reviews: [...rejected.reviews, { id: "reopened", reviewer: "creator", decision: "reopen", note: "Reconsider camera move", createdAt: "2026-09-23T00:00:00.000001Z" }],
  };
  let reads = 0;
  vi.spyOn(plotloomApi, "getVideoJobs").mockImplementation(async () => ({ jobs: ++reads === 1 ? [rejected] : [reopened] }));
  const reopen = vi.spyOn(plotloomApi, "reopenVideoJobReview").mockResolvedValue({} as never);
  const prepareSegment = vi.spyOn(plotloomApi, "prepareVideoSegment").mockResolvedValue({} as never);
  const selectSegment = vi.spyOn(plotloomApi, "selectVideoSegment").mockResolvedValue({} as never);
  const prepareJob = vi.spyOn(plotloomApi, "prepareVideoJob").mockResolvedValue({} as never);
  const submitJob = vi.spyOn(plotloomApi, "submitVideoJob").mockResolvedValue({} as never);
  await render("project", "shot-1", "scene");

  const panel = host.querySelector('[data-testid="video-review-reopen-review-reopen"]')!;
  const reviewer = panel.querySelector("input")!;
  const reason = panel.querySelector("textarea")!;
  const button = [...panel.querySelectorAll("button")].find((item) => item.textContent === "重新开放审阅")!;
  expect(button.disabled).toBe(true);
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(reviewer, "creator");
    reviewer.dispatchEvent(new Event("input", { bubbles: true }));
  });
  expect(button.disabled).toBe(true);
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(reason, "Reconsider camera move");
    reason.dispatchEvent(new Event("input", { bubbles: true }));
  });
  expect(button.disabled).toBe(false);
  await act(async () => { button.click(); await Promise.resolve(); });

  expect(reopen).toHaveBeenCalledWith("project", "review-reopen", "creator", "Reconsider camera move", 0);
  expect(host.textContent).toContain("此前拒绝记录仍保留");
  expect(host.textContent).toContain("重新开放审阅");
  expect(host.textContent).toContain("Unsafe cut");
  expect(host.textContent).toContain("Reconsider camera move");
  expect(host.querySelector('[data-testid="video-review-reopen-review-reopen"]')).toBeNull();
  expect(prepareSegment).not.toHaveBeenCalled();
  expect(selectSegment).not.toHaveBeenCalled();
  expect(prepareJob).not.toHaveBeenCalled();
  expect(submitJob).not.toHaveBeenCalled();
});

it.each([
  { label: "read-only", readOnly: true, current: true },
  { label: "stale", readOnly: false, current: false },
])("disables rejected-take reopening when the review is $label", async ({ readOnly, current }) => {
  const segment = selectedJob("disabled-reopen", 1).playbackSegment!;
  const candidate = selectedJob("disabled-reopen", 1, {
    selected: false, playbackSegment: null, current,
    segments: [{ ...segment, selected: false }],
    snapshot: { provider: { adapterId: "minimax_h3_gateway" }, shot: { id: "shot-1", durationUnits: 6_000 }, sourceTiming: { kind: "canonical", durationUnits: 6_000 } },
    reviews: [{ id: "rejected", reviewer: "creator", decision: "reject", note: "Rejected", createdAt: "2026-09-23T00:00:00Z" }],
  });
  const reopen = vi.spyOn(plotloomApi, "reopenVideoJobReview");
  await act(async () => root.render(createElement(VideoSegmentReview, {
    projectId: "project", job: candidate, readOnly, onRefresh: async () => undefined,
  })));
  const panel = host.querySelector('[data-testid="video-review-reopen-disabled-reopen"]')!;
  expect(panel.querySelector("input")?.disabled).toBe(true);
  expect(panel.querySelector("textarea")?.disabled).toBe(true);
  expect([...panel.querySelectorAll("button")].find((item) => item.textContent === "重新开放审阅")?.disabled).toBe(true);
  expect(reopen).not.toHaveBeenCalled();
});

it("locks reopen annotations while the command is pending", async () => {
  const segment = selectedJob("busy-reopen", 1).playbackSegment!;
  const candidate = selectedJob("busy-reopen", 1, {
    selected: false, playbackSegment: null,
    segments: [{ ...segment, selected: false }],
    snapshot: { provider: { adapterId: "minimax_h3_gateway" }, shot: { id: "shot-1", durationUnits: 6_000 }, sourceTiming: { kind: "canonical", durationUnits: 6_000 } },
    reviews: [{ id: "rejected", reviewer: "creator", decision: "reject", note: "Rejected", createdAt: "2026-09-23T00:00:00Z" }],
  });
  const pending = deferred<unknown>();
  vi.spyOn(plotloomApi, "reopenVideoJobReview").mockReturnValue(pending.promise);
  await act(async () => root.render(createElement(VideoSegmentReview, {
    projectId: "project", job: candidate, readOnly: false, onRefresh: async () => undefined,
  })));
  const panel = host.querySelector('[data-testid="video-review-reopen-busy-reopen"]')!;
  const reviewer = panel.querySelector("input")!;
  const reason = panel.querySelector("textarea")!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(reviewer, "creator");
    reviewer.dispatchEvent(new Event("input", { bubbles: true }));
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(reason, "Reconsider");
    reason.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const button = [...panel.querySelectorAll("button")].find((item) => item.textContent === "重新开放审阅")!;
  await act(async () => { button.click(); await Promise.resolve(); });
  expect(button.disabled).toBe(true);
  expect(reviewer.disabled).toBe(true);
  expect(reason.disabled).toBe(true);
  await act(async () => { pending.resolve({}); await pending.promise; });
});

it("allows a current ingested take with no prepared segment to be rejected", async () => {
  const candidate = selectedJob("zero-proposals", 1, {
    selected: false, playbackSegment: null, segments: [], requestedSeconds: 8,
    snapshot: { shot: { id: "shot-1", durationUnits: 6_000 }, sourceTiming: { kind: "canonical", durationUnits: 6_000 } },
    observed: { durationSeconds: 8, width: 576, height: 1024, videoCodec: "h264", audioCodec: "aac", frameRate: 24, frameCount: 192 },
  });
  const review = vi.spyOn(plotloomApi, "reviewVideoJob").mockResolvedValue({} as never);
  const refresh = vi.fn().mockResolvedValue(undefined);
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
  await act(async () => root.render(createElement(VideoSegmentReview, {
    projectId: "project", job: candidate, readOnly: false, onRefresh: refresh,
  })));
  expect(host.querySelector('[data-testid^="video-segment-preview-"]')).toBeNull();
  const [reviewer, note] = [host.querySelector("input:not([type=number])")!, host.querySelector("textarea")!];
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(reviewer, "creator");
    reviewer.dispatchEvent(new Event("input", { bubbles: true }));
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(note, "Reject before segment derivation");
    note.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const reject = [...host.querySelectorAll("button")].find((item) => item.textContent?.includes("拒绝此原片"))!;
  expect(reject.disabled).toBe(false);
  await act(async () => { reject.click(); await Promise.resolve(); });
  expect(review).not.toHaveBeenCalled();
  await act(async () => { document.querySelector<HTMLDialogElement>("dialog")!.querySelectorAll<HTMLButtonElement>("button")[1].click(); });
  expect(review).toHaveBeenCalledWith("project", candidate.id, "reject", "creator", "Reject before segment derivation", 0);
  expect(refresh).toHaveBeenCalledOnce();
});
