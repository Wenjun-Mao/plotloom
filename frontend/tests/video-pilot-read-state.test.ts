import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { VideoPilotPanel } from "../src/video-pilot";
import type { VideoJob, VideoSegment } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLDivElement;
let root: Root;
const shot = demoProject.storyboard.shots[0];

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

function preparedJob(projectId: string): VideoJob {
  return {
    id: `job-${projectId}`, projectId, state: "prepared", lifecycleStatus: "active", inputStatus: "current", cancelRequestedAt: null,
    requestedSeconds: 5, current: true, selected: false, selectionRevision: 0,
    providerPredictionId: null, outputHash: null, observed: null, error: null,
    reviews: [], snapshot: { shot: { id: shot.id, title: "已保留镜头" } },
  };
}

async function render(projectId?: string, lifecycleRevision?: number, readOnly = false, lifecycleStatus: "active" | "archived" = "active") {
  await act(async () => root.render(createElement(VideoPilotPanel, {
    projectId, lifecycleRevision, lifecycleStatus, shot, storyboard: demoProject.storyboard, graph: demoProject.storyGraph,
    sceneBeats: demoProject.sceneBeats, selectionRevision: 0,
    mediaReadPhase: "ready", readOnly,
  })));
}

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, reason: "h3_video_not_configured" });
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
});

afterEach(async () => {
  await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks();
});

it("does not infer missing requests or expose production while jobs are unknown", async () => {
  const pending = deferred<{ jobs: VideoJob[] }>();
  vi.mocked(plotloomApi.getVideoJobs).mockReturnValue(pending.promise);
  await render("a");
  expect(host.textContent).toContain("正在读取镜头视频状态");
  expect(host.textContent).not.toContain("尚无冻结");
  expect(host.textContent).not.toContain("还没有原片候选");
  expect(host.querySelector(".video-workflow-nav")).toBeNull();
  expect(host.querySelector(".video-production")).toBeNull();
  await act(async () => pending.resolve({ jobs: [preparedJob("a")] }));
  expect(host.querySelector('[data-testid="video-job-job-a"]')).not.toBeNull();
  expect(host.textContent).not.toContain("尚无冻结");
});

it.each(["prepared", "submitted", "failed", "ingested"] as const)("describes %s jobs as request records, not proof of generated originals", async state => {
  vi.mocked(plotloomApi.getVideoJobs).mockResolvedValue({ jobs: [{ ...preparedJob("a"), state }] });
  await render("a");
  expect(host.textContent).toContain("1 条视频请求记录；请求不代表原片已生成");
  expect(host.textContent).not.toContain("1 个原片候选");
  expect(host.querySelector('a[href="#shot-original"]')?.textContent).toBe("请求与原片");
});

it("waits for all owned reads before confirming an empty job list", async () => {
  const backend = deferred<Awaited<ReturnType<typeof plotloomApi.getVideoBackend>>>();
  vi.mocked(plotloomApi.getVideoBackend).mockReturnValue(backend.promise);
  await render("a");
  expect(host.textContent).toContain("正在读取镜头视频状态");
  expect(host.textContent).not.toContain("尚无冻结");
  await act(async () => backend.resolve({ enabled: false, reason: "h3_video_not_configured" }));
  expect(host.textContent).toContain("当前镜头尚无冻结的视频请求");
});

it("reports an initial read failure and offers a read-only retry, not preparation", async () => {
  const prepare = vi.spyOn(plotloomApi, "prepareVideoJob");
  vi.mocked(plotloomApi.getVideoJobs).mockRejectedValueOnce(new Error("temporary read failure"))
    .mockResolvedValue({ jobs: [preparedJob("a")] });
  await render("a");
  expect(host.querySelector('[role="alert"]')?.textContent).toContain("无法读取镜头视频状态");
  expect(host.textContent).not.toContain("尚无冻结");
  const retry = [...host.querySelectorAll("button")].find(button => button.textContent === "重新读取镜头视频状态")!;
  await act(async () => retry.click());
  expect(host.querySelector('[data-testid="video-job-job-a"]')).not.toBeNull();
  expect(prepare).not.toHaveBeenCalled();
  expect(plotloomApi.getVideoJobs).toHaveBeenCalledTimes(2);
});

for (const settlement of ["success", "failure"] as const) {
  it(`contains a stale project read ${settlement} without replacing the new project's pending state`, async () => {
    const first = deferred<{ jobs: VideoJob[] }>();
    const second = deferred<{ jobs: VideoJob[] }>();
    vi.mocked(plotloomApi.getVideoJobs).mockImplementation(projectId => projectId === "a" ? first.promise : second.promise);
    await render("a");
    await render("b");
    await act(async () => {
      if (settlement === "success") first.resolve({ jobs: [preparedJob("a")] });
      else first.reject(new Error("old project failure"));
    });
    expect(host.textContent).toContain("正在读取镜头视频状态");
    expect(host.textContent).not.toContain("old project failure");
    expect(host.querySelector('[data-testid="video-job-job-a"]')).toBeNull();
    await act(async () => second.resolve({ jobs: [preparedJob("b")] }));
    expect(host.querySelector('[data-testid="video-job-job-b"]')).not.toBeNull();
  });
}

it("does not read or infer media state for an unsaved project", async () => {
  await render();
  expect(host.textContent).toContain("先保存项目");
  expect(host.textContent).not.toContain("尚无冻结");
  expect(plotloomApi.getVideoJobs).not.toHaveBeenCalled();
});

it.each(["success", "failure"])("owns held %s by lifecycle and rereads archive/restore without navigation", async settlement => {
  const archived = deferred<{ jobs: VideoJob[] }>();
  const restored = deferred<{ jobs: VideoJob[] }>();
  const get = vi.mocked(plotloomApi.getVideoJobs)
    .mockResolvedValueOnce({ jobs: [preparedJob("a")] })
    .mockReturnValueOnce(archived.promise)
    .mockReturnValueOnce(restored.promise);
  await render("a", 1);
  expect(host.querySelector('[data-testid="video-job-job-a"]')).not.toBeNull();
  await render("a", 2, true);
  expect(host.querySelector(".video-workflow-nav")).toBeNull();
  expect(host.querySelector('[data-testid="video-job-job-a"]')).toBeNull();
  await render("a", 3);
  await act(async () => {
    if (settlement === "success") archived.resolve({ jobs: [{ ...preparedJob("a"), id: "archived", lifecycleStatus: "archived", current: false }] });
    else archived.reject(new Error("old archived failure"));
  });
  expect(host.textContent).toContain("正在读取镜头视频状态");
  expect(host.textContent).not.toContain("old archived failure");
  expect(host.querySelector('[data-testid="video-job-archived"]')).toBeNull();
  await act(async () => restored.resolve({ jobs: [preparedJob("a")] }));
  expect(host.querySelector('[data-testid="video-job-job-a"]')).not.toBeNull();
  expect(get).toHaveBeenCalledTimes(3);
  await render("a", 3, true); await render("a", 3);
  expect(get).toHaveBeenCalledTimes(3);
});

function selectedJob(archived = false): VideoJob {
  const segment: VideoSegment = {
    id: "retained", videoJobId: "job-a", shotId: shot.id,
    inFrame: 0, outFrame: 120, authoredDurationUnits: 5_000,
    sourceProbe: { frameCount: 124, fps: "24/1" }, derivativeProbe: { frameCount: 120, fps: "24/1" },
    derivativeHash: "c".repeat(64), previewEligible: true, current: !archived, selected: !archived,
    selectedRevision: 1, createdAt: "now",
  };
  return { ...preparedJob("a"), state: "ingested", lifecycleStatus: archived ? "archived" : "active",
    current: !archived, selected: !archived,
    snapshot: { shot, sourceTiming: { durationUnits: 5_000 }, provider: { adapterId: "minimax_h3_gateway" } },
    observed: { durationSeconds: 5.167, width: 832, height: 480, videoCodec: "h264", audioCodec: "aac", frameCount: 124 },
    segments: [segment], playbackSegment: archived ? null : segment };
}

it("rereads archived retained previews and restores story controls only from a fresh active projection", async () => {
  const get = vi.mocked(plotloomApi.getVideoJobs)
    .mockResolvedValueOnce({ jobs: [selectedJob()] })
    .mockResolvedValueOnce({ jobs: [selectedJob(true)] })
    .mockResolvedValueOnce({ jobs: [selectedJob()] });
  await render("a", 1);
  expect(host.querySelector('a[href="#shot-story-preview"]')).not.toBeNull();
  await render("a", 2, true, "archived");
  expect(host.querySelector('a[href="#shot-story-preview"]')).toBeNull();
  expect(host.querySelector(".branching-video-preview")).toBeNull();
  expect(host.textContent).toContain("项目已归档，故事播放已停用");
  expect(host.textContent).not.toContain("缺少当前已确认的播放片段");
  expect(host.querySelector(".video-workflow-nav")?.textContent).toContain("用于故事 · 已停用");
  expect(host.querySelector(".video-workflow-nav")?.textContent).not.toContain("待审核");
  const chooser = host.querySelector<HTMLSelectElement>(".video-segment-review select")!;
  expect(chooser.disabled).toBe(false);
  expect(host.querySelector('[data-testid="video-segment-preview-retained"]')).not.toBeNull();
  expect([...host.querySelectorAll<HTMLButtonElement>(".video-segment-review button")].every(button => button.disabled)).toBe(true);
  await render("a", 3);
  expect(host.querySelector('a[href="#shot-story-preview"]')).not.toBeNull();
  expect(host.textContent).not.toContain("项目已归档，故事播放已停用");
  expect(get).toHaveBeenCalledTimes(3);
});

it.each(["success", "failure"])("ignores an initial active %s that settles after the archived projection", async settlement => {
  const active = deferred<{ jobs: VideoJob[] }>();
  vi.mocked(plotloomApi.getVideoJobs).mockReturnValueOnce(active.promise)
    .mockResolvedValueOnce({ jobs: [selectedJob(true)] });
  await render("a", 1);
  await render("a", 2, true, "archived");
  await act(async () => {
    if (settlement === "success") active.resolve({ jobs: [selectedJob()] });
    else active.reject(new Error("late active failure"));
  });
  expect(host.textContent).toContain("项目已归档，故事播放已停用");
  expect(host.textContent).not.toContain("late active failure");
  expect(host.querySelector('a[href="#shot-story-preview"]')).toBeNull();
});
