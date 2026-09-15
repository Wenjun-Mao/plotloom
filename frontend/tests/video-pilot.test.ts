import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { VideoPilotPanel, selectedSceneVideos } from "../src/video-pilot";
import { plotloomApi } from "../src/api";
import type { ManagedAsset, ReviewedKeyframe, Shot, VideoBackend, VideoJob } from "../src/types";

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
    requestedSeconds: 5, current: true, selected: false, providerPredictionId: null,
    outputHash: null, observed: null, error: null, snapshot: { shot: { id: shotId, title: `Shot ${shotId}` } },
  };
}

function selectedJob(id: string, order: number, overrides: Partial<VideoJob> = {}): VideoJob {
  return {
    ...job("project", `shot-${order}`), id, state: "ingested", selected: true,
    snapshot: { shot: { id: `shot-${order}`, title: `Shot ${order}`, sceneId: "scene", order } },
    ...overrides,
  };
}

function props(projectId: string, shotId: string, sceneId?: string) {
  return {
    projectId, shot: { id: shotId, title: `Shot ${shotId}`, sceneId } as Shot,
    approvalId: "approval", storyboardRevision: 1, selectionRevision: 1, readOnly: false,
  };
}

async function render(projectId: string, shotId: string, sceneId?: string) {
  await act(async () => root.render(createElement(VideoPilotPanel, props(projectId, shotId, sceneId))));
  await act(async () => { await Promise.resolve(); });
}

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({
    enabled: true, adapterId: "atlas_wan", adapterVersion: "1", provider: "atlascloud",
    model: "alibaba/wan-3.0/image-to-video", durationSeconds: 5, resolution: "720p",
    nativeAudio: true, requiresAspectPolicy: false, tracksPaidWanPilot: true,
  } satisfies VideoBackend);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

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

it("requires an explicit H3 letterbox opt-in for a mismatched keyframe", async () => {
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({
    enabled: true, adapterId: "minimax_h3_gateway", adapterVersion: "3", provider: "minimax_h3_gateway",
    model: "minimax_h3_fp8_turbo4_portrait_576x1024_v1", durationSeconds: 5, resolution: "576x1024",
    width: 576, height: 1024, fps: 24, frameCount: 124, nativeAudio: true,
    requiresAspectPolicy: false, inputAspectPolicy: "reject_mismatch", tracksPaidWanPilot: false,
    defaultProfileId: "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
    profiles: [{
      id: "minimax_h3_fp8_turbo4_portrait_576x1024_v1", version: 1, label: "Portrait · Fast · 576 × 1024",
      orientation: "portrait", tier: "fast", width: 576, height: 1024, durationSeconds: 5,
      fps: 24, frameCount: 124, nativeAudio: true,
    }],
  });
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  const prepare = vi.spyOn(plotloomApi, "prepareVideoJob").mockResolvedValue(job("project", "shot"));
  const reviewedKeyframe: ReviewedKeyframe = {
    id: "binding", assetId: "wide", shotId: "shot", sceneId: "scene", selectionRevision: 1,
    visualIntentId: "intent", visualIntentRevision: 1, compatibilityNote: "reviewed source",
  };
  const wideKeyframe: ManagedAsset = {
    id: "wide", projectId: "project", originalHash: "a".repeat(64), displayHash: "b".repeat(64),
    mimeType: "image/png", byteSize: 1, width: 640, height: 360, createdAt: "2026-01-01T00:00:00Z", provenance: null,
  };
  await act(async () => root.render(createElement(VideoPilotPanel, {
    ...props("project", "shot", "scene"), reviewedKeyframe, keyframe: wideKeyframe,
  })));
  await act(async () => { await Promise.resolve(); });

  expect(host.textContent).toContain("MiniMax H3 本地视频候选");
  const freeze = [...host.querySelectorAll("button")].find((item) => item.textContent === "冻结当前审核关键帧");
  expect(freeze?.disabled).toBe(true);
  expect(host.querySelector('[data-testid="h3-aspect-preparation"]')?.textContent).toContain("不会再以黑边或提交时裁切");
  expect([...host.querySelectorAll("button")].find((item) => item.textContent === "创建居中裁切候选")).toBeDefined();
  const letterbox = host.querySelector('input[type="checkbox"]') as HTMLInputElement;
  expect(letterbox.checked).toBe(false);
  await act(async () => {
    letterbox.click();
    await Promise.resolve();
  });
  expect(freeze?.disabled).toBe(false);
  expect(host.querySelector('[data-testid="h3-letterbox-allowed"]')?.textContent).toContain("contain_pad");
  await act(async () => { freeze?.click(); await Promise.resolve(); });
  expect(prepare).toHaveBeenCalledWith("project", expect.objectContaining({
    resolution: "576x1024", requestedDurationSeconds: 5, audio: true, aspectPolicy: "contain_pad", allowLetterbox: true,
    profileId: "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
  }));
  expect(host.textContent).not.toContain("100 秒额度");
});

it("orders only current explicitly selected ingested candidates for one scene", () => {
  const first = selectedJob("first", 1);
  const second = selectedJob("second", 2);
  const stale = selectedJob("stale", 3, { current: false });
  const pending = selectedJob("pending", 4, { state: "submitted" });
  const unselected = selectedJob("unselected", 5, { selected: false });
  const otherScene = selectedJob("other", 1, { snapshot: { shot: { id: "other", sceneId: "other-scene", order: 1 } } });
  expect(selectedSceneVideos([second, stale, otherScene, pending, unselected, first], "scene").map((item) => item.id)).toEqual(["first", "second"]);
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
