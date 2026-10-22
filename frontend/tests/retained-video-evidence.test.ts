import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { VideoSegmentReview } from "../src/video-segment-review";
import { VideoPilotPanel, selectedRouteVideos } from "../src/video-pilot";
import { videoNextAction, isCurrentVideoSelection } from "../src/features/media/video-next-action";
import type { VideoJob, VideoSegment } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement;
let root: Root;
const segment = (id: string, eligible = true): VideoSegment => ({
  id, videoJobId: "take", shotId: demoProject.storyboard.shots[0].id,
  inFrame: 0, outFrame: 120, authoredDurationUnits: 5_000,
  sourceProbe: { frameCount: 192, fps: "24/1" }, derivativeProbe: { frameCount: 120, fps: "24/1" },
  derivativeHash: "c".repeat(64), previewEligible: eligible, current: false, selected: false,
  selectedRevision: null, createdAt: "now",
});
const job = (changes: Partial<VideoJob> = {}): VideoJob => ({
  id: "take", projectId: "project", state: "ingested", lifecycleStatus: "archived", inputStatus: "current",
  current: false, selected: false, requestedSeconds: 8, selectionRevision: 1,
  cancelRequestedAt: null, providerPredictionId: "prediction", outputHash: "a".repeat(64), error: null,
  observed: { durationSeconds: 8, width: 576, height: 1024, videoCodec: "h264", audioCodec: "aac", frameCount: 192 },
  snapshot: { shot: demoProject.storyboard.shots[0], sourceTiming: { durationUnits: 5_000 }, provider: { adapterId: "minimax_h3_gateway" } },
  reviews: [], segments: [segment("one"), segment("two"), segment("invalid", false)], ...changes,
});

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("admits local retained preview choice in readonly mode but never production writes", async () => {
  const prepare = vi.spyOn(plotloomApi, "prepareVideoSegment");
  const select = vi.spyOn(plotloomApi, "selectVideoSegment");
  const review = vi.spyOn(plotloomApi, "reviewVideoJob");
  await act(async () => root.render(createElement(VideoSegmentReview, {
    projectId: "project", job: job(), readOnly: true, onRefresh: async () => {},
  })));
  expect(host.textContent).toContain("项目已归档");
  expect(host.textContent).not.toContain("没有足够");
  expect(host.textContent).toContain("不用于当前故事播放");
  const chooser = host.querySelector("select")!;
  expect(chooser.disabled).toBe(false);
  expect([...chooser.options].map(option => option.value)).toEqual(["one", "two"]);
  await act(async () => { chooser.value = "one"; chooser.dispatchEvent(new Event("change", { bubbles: true })); });
  expect(host.querySelector("video")?.getAttribute("src")).toBe(plotloomApi.videoSegmentPreviewUrl("project", "one"));
  for (const button of host.querySelectorAll("button")) expect(button.disabled).toBe(true);
  expect(prepare).not.toHaveBeenCalled(); expect(select).not.toHaveBeenCalled(); expect(review).not.toHaveBeenCalled();
});

it("does not confuse rejection or staleness with insufficient frozen frames", async () => {
  const rejected = job({ lifecycleStatus: "active", inputStatus: "stale", reviews: [{ id: "reject", decision: "reject", reviewer: "QA", note: "technical only", createdAt: "now" }] });
  expect(videoNextAction([rejected])).toContain("与当前分镜");
  expect(videoNextAction([rejected])).not.toContain("须明确重新开放");
  await act(async () => root.render(createElement(VideoSegmentReview, { projectId: "project", job: rejected, readOnly: false, onRefresh: async () => {} })));
  expect(host.textContent).not.toContain("没有足够");
  expect([...host.querySelectorAll("button")].find(button => button.textContent === "重新开放审阅")?.disabled).toBe(true);
});

it.each([null, [], "broken"])("contains malformed raw snapshot %j without inventing shot ownership", async snapshot => {
  const invalid = job({ lifecycleStatus: "active", inputStatus: "invalid", snapshot, segments: [] });
  expect(isCurrentVideoSelection({ ...invalid, current: true, selected: true, playbackSegment: segment("one") })).toBe(false);
  expect(() => selectedRouteVideos([invalid], demoProject.storyboard, demoProject.sceneBeats, demoProject.storyGraph, "missing")).not.toThrow();
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, reason: "h3_video_not_configured" });
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [invalid] });
  await act(async () => root.render(createElement(VideoPilotPanel, {
    projectId: "project", shot: demoProject.storyboard.shots[0], storyboard: demoProject.storyboard,
    graph: demoProject.storyGraph, sceneBeats: demoProject.sceneBeats, selectionRevision: 0,
    mediaReadPhase: "ready", readOnly: true,
  })));
  expect(host.textContent).toContain("无法确认镜头归属");
  expect(host.textContent).toContain(JSON.stringify(snapshot));
  expect(host.textContent).not.toContain("尚无冻结的视频请求");
});

it("preserves a genuine timing failure separately from archive guidance", async () => {
  await act(async () => root.render(createElement(VideoSegmentReview, {
    projectId: "project", job: job({ observed: { ...job().observed!, frameCount: 119 } }), readOnly: true, onRefresh: async () => {},
  })));
  expect(host.textContent).toContain("项目已归档");
  expect(host.textContent).toContain("没有足够");
});
