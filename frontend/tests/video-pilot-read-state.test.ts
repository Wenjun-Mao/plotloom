import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { VideoPilotPanel } from "../src/video-pilot";
import type { VideoJob } from "../src/types";

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
    id: `job-${projectId}`, projectId, state: "prepared", cancelRequestedAt: null,
    requestedSeconds: 5, current: true, selected: false, selectionRevision: 0,
    providerPredictionId: null, outputHash: null, observed: null, error: null,
    reviews: [], snapshot: { shot: { id: shot.id, title: "已保留镜头" } },
  };
}

async function render(projectId?: string) {
  await act(async () => root.render(createElement(VideoPilotPanel, {
    projectId, shot, storyboard: demoProject.storyboard, graph: demoProject.storyGraph,
    sceneBeats: demoProject.sceneBeats, selectionRevision: 0,
    mediaReadPhase: "ready", readOnly: false,
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
