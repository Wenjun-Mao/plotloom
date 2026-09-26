import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { VideoPilotPanel, selectedRouteVideos } from "../src/video-pilot";
import { BranchingVideoPreview, branchingPreviewManifest } from "../src/branching-video-preview";
import { VideoSegmentReview } from "../src/video-segment-review";
import { plotloomApi } from "../src/api";
import type { ManagedAsset, SceneBeatPlan, Shot, StoryGraph, Storyboard, VideoBackend, VideoJob } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

function job(projectId: string, shotId: string): VideoJob {
  return {
    id: `job-${projectId}`, projectId, state: "prepared", cancelRequestedAt: null,
    requestedSeconds: 5, current: true, selected: false, selectionRevision: 0, providerPredictionId: null,
    outputHash: null, observed: null, error: null, reviews: [], snapshot: { shot: { id: shotId, title: `Shot ${shotId}` } },
  };
}

function selectedJob(id: string, order: number, overrides: Partial<VideoJob> = {}): VideoJob {
  return {
    ...job("project", `shot-${order}`), id, state: "ingested", selected: true,
    playbackSegment: {
      id: `segment-${id}`, videoJobId: id, shotId: `shot-${order}`,
      inFrame: 0, outFrame: 144, authoredDurationUnits: 6_000,
      sourceProbe: { frameCount: 192, fps: "24/1" },
      derivativeProbe: { frameCount: 144, fps: "24/1" },
      derivativeHash: `digest-${id}`, current: true, selected: true,
      selectedRevision: 1, createdAt: "2026-09-23T00:00:00Z",
    },
    snapshot: { shot: { id: `shot-${order}`, title: `Shot ${order}`, sceneId: "scene", order } },
    ...overrides,
  };
}

function routeContext(shotIds: string[], sceneId = "scene"): { storyboard: Storyboard; sceneBeats: SceneBeatPlan; graph: StoryGraph; routeId: string } {
  return {
    graph: {
      startNodeId: "start",
      nodes: [
        { id: "start", title: "Start", kind: "start", summary: "" },
        { id: "story-node", title: "Route scene", kind: "scene", summary: "" },
        { id: "end", title: "End", kind: "ending", summary: "" },
      ],
      edges: [
        { id: "first", sourceNodeId: "start", targetNodeId: "story-node", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
        { id: "last", sourceNodeId: "story-node", targetNodeId: "end", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      ],
      joinContracts: [],
    },
    sceneBeats: { scenes: [{ id: sceneId, storyNodeId: "story-node", title: "Route scene", order: 1 } as SceneBeatPlan["scenes"][number]], beats: [], dialogueCues: [] },
    storyboard: { shots: shotIds.map((id, index) => ({ id, sceneId, title: id, order: index + 1, durationUnits: 6_000 } as Shot)), shotBeatLinks: [] },
    routeId: "start/story-node/end",
  };
}

function props(projectId: string, shotId: string, sceneId?: string) {
  const route = routeContext([...new Set(shotId === "shot-3" ? ["shot-1", "shot-2", "shot-3"] : shotId === "new-shot" ? ["new-shot"] : ["shot-1", "shot-2"])]);
  return {
    projectId, shot: { id: shotId, title: `Shot ${shotId}`, sceneId } as Shot,
    approvalId: "approval", storyboardRevision: 1, selectionRevision: 1, readOnly: false,
    ...route,
    routeId: sceneId === "other" ? undefined : route.routeId,
  };
}

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
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

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

it("orders only current explicitly selected ingested candidates on one explicit route", () => {
  const first = selectedJob("first", 1);
  const second = selectedJob("second", 2);
  const stale = selectedJob("stale", 3, { current: false });
  const pending = selectedJob("pending", 4, { state: "submitted" });
  const unselected = selectedJob("unselected", 5, { selected: false });
  const otherScene = selectedJob("other", 1, { snapshot: { shot: { id: "other", sceneId: "other-scene", order: 1 } } });
  const route = routeContext(["shot-1", "shot-2", "shot-3"]);
  expect(selectedRouteVideos([second, stale, otherScene, pending, unselected, first], route.storyboard, route.sceneBeats, route.graph, route.routeId)?.jobs.map((item) => item.id)).toEqual(["first", "second"]);
  expect(selectedRouteVideos([second], route.storyboard, route.sceneBeats, route.graph, "missing")).toBeNull();
  const legacyWholeJob = selectedJob("legacy", 1, { playbackSegment: null });
  expect(selectedRouteVideos([legacyWholeJob], route.storyboard, route.sceneBeats, route.graph, route.routeId)?.jobs).toEqual([]);
  const wrongTiming = selectedJob("wrong-timing", 1, { playbackSegment: { ...first.playbackSegment!, authoredDurationUnits: 8_000 } });
  expect(selectedRouteVideos([wrongTiming], route.storyboard, route.sceneBeats, route.graph, route.routeId)?.jobs).toEqual([]);
});

it("orders consecutive route scenes and excludes a selected sibling branch", () => {
  const nodeKind = (id: string): StoryGraph["nodes"][number]["kind"] => {
    if (id === "start") return "start";
    if (id === "decision") return "decision";
    if (id === "end") return "ending";
    return "scene";
  };
  const graph: StoryGraph = {
    startNodeId: "start",
    nodes: ["start", "common", "decision", "left", "right", "end"].map((id) => ({ id, title: id, kind: nodeKind(id), summary: "" })),
    edges: [
      ["start", "common"], ["common", "decision"], ["decision", "left"], ["decision", "right"], ["left", "end"], ["right", "end"],
    ].map(([sourceNodeId, targetNodeId], index) => ({ id: `${index}`, sourceNodeId, targetNodeId, kind: sourceNodeId === "decision" ? "choice" as const : "continuation" as const, choiceText: null, stateEffects: {}, entityStateEffects: [] })),
    joinContracts: [],
  };
  const storyboard = { shots: [
    { id: "common-shot", sceneId: "common-scene", title: "Common", order: 1, durationUnits: 6_000 },
    { id: "left-shot", sceneId: "left-scene", title: "Left", order: 1, durationUnits: 6_000 },
    { id: "right-shot", sceneId: "right-scene", title: "Right", order: 1, durationUnits: 6_000 },
  ] as Shot[], shotBeatLinks: [] } satisfies Storyboard;
  const sceneBeats = { scenes: [
    { id: "common-scene", storyNodeId: "common", title: "Common", order: 1 },
    { id: "left-scene", storyNodeId: "left", title: "Left", order: 2 },
    { id: "right-scene", storyNodeId: "right", title: "Right", order: 2 },
  ] as SceneBeatPlan["scenes"], beats: [], dialogueCues: [] };
  const selected = [
    selectedJob("common", 1, { snapshot: { shot: { id: "common-shot", sceneId: "common-scene", order: 1 } } }),
    selectedJob("left", 1, { snapshot: { shot: { id: "left-shot", sceneId: "left-scene", order: 1 } } }),
    selectedJob("right", 1, { snapshot: { shot: { id: "right-shot", sceneId: "right-scene", order: 1 } } }),
  ];
  expect(selectedRouteVideos(selected, storyboard, sceneBeats, graph, "start/common/decision/left/end")?.jobs.map((job) => job.id)).toEqual(["common", "left"]);
});

function branchingFixture() {
  const graph: StoryGraph = {
    startNodeId: "start",
    nodes: ["start", "scene", "decision", "left", "right"].map((id) => ({
      id, title: id, kind: id === "start" ? "start" : id === "decision" ? "decision" : id === "left" || id === "right" ? "ending" : "scene", summary: "",
    })),
    edges: [
      ["start", "scene", "continuation"], ["scene", "decision", "continuation"], ["decision", "left", "choice"], ["decision", "right", "choice"],
    ].map(([sourceNodeId, targetNodeId, kind], index) => ({
      id: `edge-${index}`, sourceNodeId, targetNodeId, kind: kind as "choice" | "continuation", choiceText: kind === "choice" ? targetNodeId : null, stateEffects: {}, entityStateEffects: [],
    })),
    joinContracts: [],
  };
  const sceneBeats = { scenes: ["scene", "decision", "left", "right"].map((storyNodeId, index) => ({
    id: `${storyNodeId}-scene`, storyNodeId, title: storyNodeId, order: index + 1,
  })) as SceneBeatPlan["scenes"], beats: [], dialogueCues: [] };
  const storyboard = { shots: ["scene", "decision", "left", "right"].map((id) => ({
    id: `${id}-shot`, sceneId: `${id}-scene`, title: id, order: 1, durationUnits: 6_000,
  })) as Shot[], shotBeatLinks: [] } satisfies Storyboard;
  const selected = ["scene", "decision", "left", "right"].map((id) => selectedJob(`${id}-job`, 1, {
    snapshot: { shot: { id: `${id}-shot`, title: id, sceneId: `${id}-scene`, order: 1 } },
  }));
  return { graph, sceneBeats, storyboard, selected };
}

it("pins selected media by canonical node order and surfaces missing branching media", () => {
  const fixture = branchingFixture();
  const manifest = branchingPreviewManifest("project", fixture.selected, fixture.storyboard, fixture.sceneBeats, fixture.graph);
  expect(manifest.nodes.get("decision")?.jobs.map((job) => job.id)).toEqual(["decision-job"]);
  expect(manifest.nodes.get("right")?.missingShotTitles).toEqual([]);
  const missing = branchingPreviewManifest("project", fixture.selected.filter((job) => job.id !== "right-job"), fixture.storyboard, fixture.sceneBeats, fixture.graph);
  expect(missing.nodes.get("right")?.missingShotTitles).toEqual(["right"]);
});

it("does not mount branching playback while any route shot lacks a reviewed segment", async () => {
  const fixture = branchingFixture();
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected.filter((item) => item.id !== "right-job"),
    storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  expect(host.querySelector("[data-testid^='branching-video-job-']")).toBeNull();
  expect(host.querySelector('[data-testid="branching-missing-media"]')?.textContent).toContain("right");
});

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
  await act(async () => { [...host.querySelectorAll("button")].find((item) => item.textContent?.includes("生成待审片段"))?.click(); });
  expect(prepare).toHaveBeenCalledWith("old", candidate.id, 0, 144, 0);
  expect(select).not.toHaveBeenCalled();
  await act(async () => root.render(createElement(VideoSegmentReview, { projectId: "new", job: candidate, readOnly: false, onRefresh: refresh })));
  delayed.resolve({ ...selectedJob("segment-candidate", 1).playbackSegment!, id: "old-proposal", selected: false });
  await act(async () => { await delayed.promise; await Promise.resolve(); });
  expect(refresh).not.toHaveBeenCalled();
  expect(select).not.toHaveBeenCalled();
});

it("does not offer a rejected H3 take for another segment decision", async () => {
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
  expect([...host.querySelectorAll("button")].find((item) => item.textContent?.includes("生成待审片段"))?.disabled).toBe(true);
  expect([...host.querySelectorAll("button")].find((item) => item.textContent?.includes("确认用于故事"))?.disabled).toBe(true);
});

it("allows a current ingested take with no prepared segment to be rejected", async () => {
  const candidate = selectedJob("zero-proposals", 1, {
    selected: false, playbackSegment: null, segments: [], requestedSeconds: 8,
    snapshot: { shot: { id: "shot-1", durationUnits: 6_000 }, sourceTiming: { kind: "canonical", durationUnits: 6_000 } },
    observed: { durationSeconds: 8, width: 576, height: 1024, videoCodec: "h264", audioCodec: "aac", frameRate: 24, frameCount: 192 },
  });
  const review = vi.spyOn(plotloomApi, "reviewVideoJob").mockResolvedValue({} as never);
  const refresh = vi.fn().mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(true);
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
  expect(review).toHaveBeenCalledWith("project", candidate.id, "reject", "creator", "Reject before segment derivation", 0);
  expect(refresh).toHaveBeenCalledOnce();
});

it("waits at a decision, follows only the clicked edge, holds an ending, and ignores duplicate ended events", async () => {
  const fixture = branchingFixture();
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  await act(async () => { await Promise.resolve(); });
  const scene = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  expect(scene).not.toBeNull();
  await act(async () => { scene.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  const decision = host.querySelector('[data-testid="branching-video-job-decision-job"]') as HTMLVideoElement;
  expect(decision).not.toBeNull();
  expect(play).toHaveBeenCalledTimes(1);
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
  await act(async () => { decision.dispatchEvent(new Event("ended", { bubbles: true })); decision.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  const choices = [...host.querySelectorAll('[data-testid="branching-choices"] button')] as HTMLButtonElement[];
  expect(choices.map((choice) => choice.textContent)).toEqual(["left", "right"]);
  await act(async () => { choices.find((choice) => choice.textContent === "right")?.click(); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-video-job-right-job"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="branching-video-job-left-job"]')).toBeNull();
  expect(play).toHaveBeenCalledTimes(2);
  const right = host.querySelector('[data-testid="branching-video-job-right-job"]') as HTMLVideoElement;
  await act(async () => { right.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-video-job-right-job"]')).not.toBeNull();
  expect([...host.querySelectorAll("button")].some((button) => button.textContent === "重新开始分支预览")).toBe(true);
});

it("creates a fresh media episode when an ending is restarted", async () => {
  const fixture = branchingFixture();
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  const scene = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  await act(async () => { scene.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  const decision = host.querySelector('[data-testid="branching-video-job-decision-job"]') as HTMLVideoElement;
  await act(async () => { decision.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  await act(async () => { [...host.querySelectorAll('[data-testid="branching-choices"] button')].find((choice) => choice.textContent === "left")?.dispatchEvent(new MouseEvent("click", { bubbles: true })); await Promise.resolve(); });
  const ending = host.querySelector('[data-testid="branching-video-job-left-job"]') as HTMLVideoElement;
  await act(async () => { ending.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  ending.currentTime = 0.5;
  await act(async () => { [...host.querySelectorAll("button")].find((button) => button.textContent === "重新开始分支预览")?.click(); await Promise.resolve(); });
  const restarted = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  expect(restarted).not.toBe(scene);
  expect(restarted.currentTime).toBe(0);
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
});

it("does not auto-traverse a canonical decision with one outgoing edge, including an empty decision node", async () => {
  const fixture = branchingFixture();
  fixture.graph.edges = fixture.graph.edges.filter((edge) => edge.id !== "edge-3");
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  await act(async () => { await Promise.resolve(); });
  const scene = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  await act(async () => { scene.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  const decision = host.querySelector('[data-testid="branching-video-job-decision-job"]') as HTMLVideoElement;
  await act(async () => { decision.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-video-job-left-job"]')).toBeNull();
  expect(host.querySelector('[data-testid="branching-choices"]')?.textContent).toContain("left");

  const emptyGraph: StoryGraph = {
    startNodeId: "decision", nodes: [
      { id: "decision", title: "Only choice", kind: "decision", summary: "" }, { id: "end", title: "End", kind: "ending", summary: "" },
    ], edges: [{ id: "only", sourceNodeId: "decision", targetNodeId: "end", kind: "choice", choiceText: "Continue", stateEffects: {}, entityStateEffects: [] }], joinContracts: [],
  };
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: [], storyboard: { shots: [], shotBeatLinks: [] }, sceneBeats: { scenes: [], beats: [], dialogueCues: [] }, graph: emptyGraph,
  })));
  await act(async () => { await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-choices"]')?.textContent).toContain("Continue");
});

it("pauses replaced session media before a project change can leave it playing", async () => {
  const fixture = branchingFixture();
  const pause = vi.mocked(HTMLMediaElement.prototype.pause);
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  await act(async () => { await Promise.resolve(); });
  const oldPlayer = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  expect(oldPlayer).not.toBeNull();
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "replacement", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  expect(pause).toHaveBeenCalledWith();
});

it("turns a corrupt selected-media load error into a blocking gap without advancing", async () => {
  const fixture = branchingFixture();
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  const player = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  await act(async () => { player.dispatchEvent(new Event("error", { bubbles: true })); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-missing-media"]')?.textContent).toContain("scene");
  expect(host.querySelector('[data-testid="branching-missing-media"] a')?.getAttribute("href"))
    .toBe("?project=project&stage=storyboard&entity=shot%3Ascene-shot#shot-workbench");
  expect(host.querySelector('[data-testid="branching-video-job-scene-job"]')).toBeNull();
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
});

it("uses the explicit current-play control without changing the branching session", async () => {
  const fixture = branchingFixture();
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  await act(async () => { await Promise.resolve(); });
  await act(async () => { [...host.querySelectorAll("button")].find((button) => button.textContent === "播放当前")?.click(); await Promise.resolve(); });
  expect(play).toHaveBeenCalledTimes(1);
  expect(host.textContent).toContain("当前节点：scene");
});

it("scopes selected playback by project, scene, and current selected membership", async () => {
  const oldFirst = selectedJob("old-first", 1, { projectId: "old" });
  const oldSecond = selectedJob("old-second", 2, { projectId: "old" });
  const oldThird = selectedJob("old-third", 3, { projectId: "old", selected: false, snapshot: { shot: { id: "shot-3", title: "Third", sceneId: "scene", order: 3 } } });
  const otherScene = selectedJob("other-scene", 1, { projectId: "old", snapshot: { shot: { id: "other-scene", title: "Other", sceneId: "other", order: 1 } } });
  const newFirst = selectedJob("new-first", 1, { projectId: "new", snapshot: { shot: { id: "new-shot", title: "New", sceneId: "scene", order: 1 } } });
  let oldJobs = [oldFirst, oldSecond, oldThird, otherScene];
  const membershipReview = deferred<unknown>();
  vi.spyOn(plotloomApi, "getVideoJobs").mockImplementation(async (projectId) => ({
    jobs: projectId === "old" ? oldJobs : [newFirst],
  }));
  vi.spyOn(plotloomApi, "reviewVideoJob").mockImplementation(async () => {
    oldJobs = [oldFirst, oldSecond, { ...oldThird, selected: true }, otherScene];
    return membershipReview.promise;
  });

  await render("old", "shot-1", "scene");
  expect(host.querySelector('[data-testid="video-sequence-job-old-first"]')).not.toBeNull();
  await act(async () => { [...host.querySelectorAll("button")].find((item) => item.textContent === "下一镜头")?.click(); });
  expect(host.querySelector('[data-testid="video-sequence-job-old-second"]')).not.toBeNull();

  // A selected-member addition changes the exact scope even though the
  // project, scene, and previously active job are unchanged. It must reset
  // without borrowing that prior position or its pending autoplay.
  await render("old", "shot-3", "scene");
  await act(async () => {
    (host.querySelector('[data-testid="video-job-old-third"] button') as HTMLButtonElement | null)?.click();
    await Promise.resolve();
  });
  membershipReview.resolve(undefined);
  await act(async () => { await membershipReview.promise; await Promise.resolve(); await Promise.resolve(); });
  await render("old", "shot-3", "scene");
  expect(host.querySelector('[data-testid="video-sequence-job-old-first"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="video-sequence-job-old-second"]')).toBeNull();

  await render("new", "new-shot", "scene");
  expect(host.querySelector('[data-testid="video-sequence-job-new-first"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="video-sequence-job-old-second"]')).toBeNull();
  await render("new", "new-shot", "other");
  expect(host.querySelector("[data-testid^=video-sequence-job]")).toBeNull();
});

it("autoplays only the next current source, holds the final frame, and reports current rather than stale play rejection", async () => {
  const first = selectedJob("first", 1);
  const second = selectedJob("second", 2);
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [first, second] });
  const delayedAutomaticPlay = deferred<void>();
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockReturnValueOnce(delayedAutomaticPlay.promise);

  await render("project", "shot-1", "scene");
  const firstPlayer = host.querySelector('[data-testid="video-sequence-job-first"]') as HTMLVideoElement;
  await act(async () => { firstPlayer.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="video-sequence-job-second"]')).not.toBeNull();
  expect(play).toHaveBeenCalledTimes(1);

  await act(async () => { [...host.querySelectorAll("button")].find((item) => item.textContent === "上一镜头")?.click(); });
  expect(host.querySelector('[data-testid="video-sequence-job-first"]')).not.toBeNull();
  await act(async () => { delayedAutomaticPlay.reject(new Error("old source rejected")); await Promise.resolve(); });
  expect(host.querySelector('[role="status"]')).toBeNull();

  await act(async () => { [...host.querySelectorAll("button")].find((item) => item.textContent === "下一镜头")?.click(); });

  const secondPlayer = host.querySelector('[data-testid="video-sequence-job-second"]') as HTMLVideoElement;
  await act(async () => { secondPlayer.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="video-sequence-job-second"]')).not.toBeNull();
  expect(play).toHaveBeenCalledTimes(1);

  play.mockRejectedValueOnce(new Error("gesture required"));
  await act(async () => { [...host.querySelectorAll("button")].find((item) => item.textContent === "播放当前")?.click(); await Promise.resolve(); });
  expect(host.querySelector('[role="status"]')?.textContent).toContain("gesture required");
});
