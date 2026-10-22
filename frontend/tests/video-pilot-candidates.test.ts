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

it("only recommends playback for current selected segments matching the authored duration", () => {
  const current = selectedJob("current", 1);
  expect(isCurrentVideoSelection(current)).toBe(true);
  expect(videoNextAction([current], 6_000)).toContain("检查路径预览");
  expect(videoNextAction([current], 5_000)).toContain("时长与当前镜头不一致");
  for (const historical of [
    { ...current, current: false },
    { ...current, playbackSegment: { ...current.playbackSegment!, current: false } },
    { ...current, playbackSegment: { ...current.playbackSegment!, selected: false } },
  ]) {
    expect(isCurrentVideoSelection(historical)).toBe(false);
    expect(videoNextAction([historical], 6_000)).not.toContain("检查路径预览");
  }
});

it("guides current unselected segments to review and rejected history to recovery", () => {
  const current = selectedJob("current", 1);
  const pending = { ...current, selected: false, playbackSegment: null, segments: [{ ...current.playbackSegment!, selected: false }] };
  expect(videoNextAction([pending], 6_000)).toContain("听看待审片段");
  expect(videoNextAction([{ ...pending, reviews: [{ id: "r", reviewer: "", note: "", decision: "reject", createdAt: "2026-10-04T00:00:00Z" }] }], 6_000)).toContain("被拒绝");
  expect(videoNextAction([], 6_000)).toContain("检查关键帧与视频请求");
});

it("does not describe an unconfigured H3 backend as the legacy Wan five-second pilot", async () => {
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, reason: "h3_video_not_configured", qualifiedDurationSeconds: [5, 8] });
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  await render("project", "shot-1");
  expect(host.textContent).toContain("准备或生成新的 MiniMax H3 原片");
  expect(host.textContent).toContain("H3 后端尚未配置");
  expect(host.textContent).not.toContain("P2 Wan 视频试点");
  expect(host.textContent).not.toContain("仅 5 秒 / 720p");
});

it("keeps retained H3 segment review visible when dispatch is unavailable", async () => {
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, reason: "h3_video_not_configured", qualifiedDurationSeconds: [5, 8] });
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [{
    ...selectedJob("retained-h3", 1, {
      projectId: "project", snapshot: {
        provider: { adapterId: "minimax_h3_gateway" },
        shot: { id: "shot-1", title: "Retained H3", sceneId: "scene", order: 1, durationUnits: 6_000 },
        sourceTiming: { kind: "canonical", durationUnits: 6_000 },
      },
    }), requestedSeconds: 8, observed: { frameCount: 192, durationSeconds: 8 } as VideoJob["observed"],
  }] });
  await render("project", "shot-1", "scene");
  expect(host.querySelector('[data-testid="video-segment-review-retained-h3"]')).not.toBeNull();
  expect(host.textContent).toContain("原稿镜头时长：6.000 秒");
  expect([...host.querySelectorAll("button")].some((button) => button.textContent === "选择此候选")).toBe(false);
});

it("targets one reviewable H3 job when another same-shot candidate was rejected", async () => {
  const snapshot = {
    provider: { adapterId: "minimax_h3_gateway" },
    shot: { id: "shot-1", title: "Shot 1", sceneId: "scene", order: 1, durationUnits: 6_000 },
    sourceTiming: { kind: "canonical", durationUnits: 6_000 },
  };
  const rejected = selectedJob("rejected", 1, {
    snapshot, selected: false, playbackSegment: null,
    segments: [{ ...selectedJob("rejected", 1).playbackSegment!, selected: false }],
    reviews: [{ id: "rejected-review", reviewer: "", note: "", decision: "reject", createdAt: "2026-09-23T00:00:00Z" }],
  });
  const reviewable = selectedJob("reviewable", 1, {
    snapshot, selected: false, playbackSegment: null,
    segments: [{ ...selectedJob("reviewable", 1).playbackSegment!, selected: false }],
    reviews: [],
  });
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [rejected, reviewable] });
  await render("project", "shot-1", "scene");
  const nav = host.querySelector(".video-workflow-nav")!;
  const links = [...nav.querySelectorAll("a")];
  expect(links.find((link) => link.textContent === "预览片段")?.getAttribute("href"))
    .toBe("#video-segment-preview-reviewable");
  expect(links.find((link) => link.textContent === "用于故事 · 确认")?.getAttribute("href"))
    .toBe("#video-segment-confirm-reviewable");
  expect(host.querySelector("#shot-segment")?.querySelector("#video-segment-preview-reviewable")).not.toBeNull();
  expect(host.querySelectorAll('[id^="video-segment-preview-"]')).toHaveLength(2);
});

it("does not let a deferred old-project submit refresh overwrite the new project", async () => {
  const oldSubmit = deferred<VideoJob>();
  const jobs = vi.spyOn(plotloomApi, "getVideoJobs").mockImplementation(async (projectId) => ({ jobs: [job(projectId, projectId === "old" ? "shot-old" : "shot-new")] }));
  vi.spyOn(plotloomApi, "submitVideoJob").mockReturnValue(oldSubmit.promise);
  await render("old", "shot-old");
  const submit = [...host.querySelectorAll("button")].find((item) => item.textContent === "提交一次");
  expect(submit).toBeDefined();
  await act(async () => submit?.click());
  await render("new", "shot-new");
  const oldCallsBeforeResolve = jobs.mock.calls.filter(([projectId]) => projectId === "old").length;
  await act(async () => { oldSubmit.resolve(job("old", "shot-old")); await Promise.resolve(); });
  expect(jobs.mock.calls.filter(([projectId]) => projectId === "old")).toHaveLength(oldCallsBeforeResolve);
  expect(host.textContent).toContain("Shot shot-new");
  expect(host.textContent).not.toContain("Shot shot-old");
});

it("keeps retrieval available after a known-ID cancel intent", async () => {
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [{ ...job("project", "shot"), state: "retrieve_needed", cancelRequestedAt: "2026-09-12T00:00:00Z" }] });
  await render("project", "shot");
  const retrieve = [...host.querySelectorAll("button")].find((item) => item.textContent === "获取结果");
  expect(retrieve?.disabled).toBe(false);
});

it("pauses every native candidate peer before allowing a new candidate to play", async () => {
  const first = { ...job("project", "shot"), id: "first", state: "ingested" as const };
  const second = { ...job("project", "shot"), id: "second", state: "ingested" as const };
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [first, second] });
  const paused: HTMLMediaElement[] = [];
  vi.mocked(HTMLMediaElement.prototype.pause).mockImplementation(function (this: HTMLMediaElement) {
    paused.push(this);
  });
  await render("project", "shot");
  const firstPlayer = host.querySelector('[data-testid="video-job-player-first"]') as HTMLVideoElement;
  const secondPlayer = host.querySelector('[data-testid="video-job-player-second"]') as HTMLVideoElement;
  expect(firstPlayer).not.toBeNull();
  expect(secondPlayer).not.toBeNull();
  await act(async () => { firstPlayer.dispatchEvent(new Event("play", { bubbles: true })); });
  expect(paused).toEqual([secondPlayer]);
});

it("binds H3 prompt review to an explicit gateway crop choice for a mismatched keyframe", async () => {
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({
    enabled: true, adapterId: "minimax_h3_gateway", adapterVersion: "6", provider: "minimax_h3_gateway",
    model: "minimax_h3_gateway_catalog_v7", durationSeconds: 5, resolution: "576x1024",
    width: 576, height: 1024, fps: 24, frameCount: 124, nativeAudio: true,
    requiresAspectPolicy: false, inputAspectPolicy: "reject_mismatch", allowsCenterCrop: true, tracksPaidWanPilot: false,
    defaultProfileId: "minimax_h3_quality8_portrait_576x1024_v2",
    qualifiedDurationSeconds: Array.from({ length: 11 }, (_, index) => index + 5),
    profiles: [{
      id: "minimax_h3_quality8_portrait_576x1024_v2", version: 2, label: "Portrait · Fast · 576 × 1024 · Quality 8", quality: 8,
      orientation: "portrait", tier: "fast", width: 576, height: 1024, durationSeconds: 5,
      fps: 24, frameCount: 124, nativeAudio: true,
    }, {
      id: "minimax_h3_quality1_portrait_576x1024_v2", version: 2, label: "Portrait · Fast · 576 × 1024 · Quality 1", quality: 1,
      orientation: "portrait", tier: "fast", width: 576, height: 1024, durationSeconds: 5,
      fps: 24, frameCount: 124, nativeAudio: true,
    }],
  });
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  const preview = vi.spyOn(plotloomApi, "previewH3Prompt").mockResolvedValue({ sourceHash: "a".repeat(64), sources: [], compiledPrompt: null });
  const wideKeyframe: ManagedAsset = {
    id: "wide", projectId: "project", originalHash: "a".repeat(64), displayHash: "b".repeat(64),
    mimeType: "image/png", byteSize: 1, width: 640, height: 360, createdAt: "2026-01-01T00:00:00Z", provenance: null,
  };
  await act(async () => root.render(createElement(VideoPilotPanel, {
    ...props("project", "shot", "scene"), shot: { ...props("project", "shot", "scene").shot, durationUnits: 5_000 }, keyframe: wideKeyframe,
  })));
  await act(async () => { await Promise.resolve(); });

  expect(host.textContent).toContain("准备或生成新的 MiniMax H3 原片");
  const load = [...host.querySelectorAll("button")].find((item) => item.textContent === "读取当前来源");
  expect(load?.disabled).toBe(true);
  expect(host.querySelector('[data-testid="h3-aspect-preparation"]')?.textContent).toContain("默认拒绝比例不符");
  const crop = host.querySelectorAll('input[type="radio"]')[1] as HTMLInputElement;
  expect(crop.checked).toBe(false);
  await act(async () => {
    crop.click();
    await Promise.resolve();
  });
  expect(load?.disabled).toBe(false);
  expect(host.querySelector('[data-testid="h3-center-crop-allowed"]')?.textContent).toContain("cover_center_crop");
  await act(async () => { load?.click(); await Promise.resolve(); });
  expect(preview).toHaveBeenCalledWith("project", expect.objectContaining({
    resolution: "576x1024", requestedDurationSeconds: 5, audio: true, aspectPolicy: "cover_center_crop", allowCenterCrop: true, allowLetterbox: false,
    profileId: "minimax_h3_quality8_portrait_576x1024_v2",
  }));
  const letterbox = host.querySelectorAll('input[type="radio"]')[2] as HTMLInputElement;
  await act(async () => {
    letterbox.click();
    await Promise.resolve();
  });
  expect(host.querySelector('[data-testid="h3-letterbox-allowed"]')?.textContent).toContain("contain_pad");
  await act(async () => { load?.click(); await Promise.resolve(); });
  expect(preview).toHaveBeenLastCalledWith("project", expect.objectContaining({
    aspectPolicy: "contain_pad", allowLetterbox: true, allowCenterCrop: false,
    profileId: "minimax_h3_quality8_portrait_576x1024_v2",
  }));
  expect(host.textContent).toContain("来源绑定");
  const quality = host.querySelector('[aria-label="H3 质量用途（必选）"]') as HTMLSelectElement;
  await act(async () => { quality.value = "1"; quality.dispatchEvent(new Event("change", { bubbles: true })); });
  expect(host.textContent).not.toContain("来源绑定");
  await act(async () => { load?.click(); await Promise.resolve(); });
  expect(preview).toHaveBeenLastCalledWith("project", expect.objectContaining({
    profileId: "minimax_h3_quality1_portrait_576x1024_v2",
  }));
  expect(host.textContent).toContain("来源绑定");
  const duration = host.querySelector('[aria-label="H3 时长（已审核）"]') as HTMLSelectElement;
  await act(async () => { duration.value = "8"; duration.dispatchEvent(new Event("change", { bubbles: true })); });
  expect(host.textContent).not.toContain("来源绑定");
  expect(load?.disabled).toBe(false);
  expect(host.textContent).not.toContain("100 秒额度");
});
