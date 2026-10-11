import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { VideoPilotPanel } from "../src/video-pilot";
import { ReviewWorkflowReadProvider, useReviewWorkflowRead } from "../src/app/workspace/ReviewWorkflowReadContext";
import type { VideoJob } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }
async function harness() {
  const jobs = vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  const backend = vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, reason: "h3_video_not_configured" });
  const budget = vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
  const host = document.createElement("div"), root = createRoot(host);
  let projectId = "a", revision = 1, active = true, shot = demoProject.storyboard.shots[0], approvalId: string | undefined;
  function Guide() { const read = useReviewWorkflowRead(); return createElement("p", { "data-hint": true }, read?.stage === "shot-media" ? read.nextText : "等待当前镜头读取"); }
  const render = () => act(async () => root.render(createElement(ReviewWorkflowReadProvider, { projectId, revision, stage: active ? "shot-media" : undefined, entity: shot.id,
    children: [createElement(Guide, { key: "guide" }), active ? createElement(VideoPilotPanel, { key: "panel", projectId, projectRevision: revision, shot, approvalId, approvalCurrent: Boolean(approvalId), storyboard: demoProject.storyboard,
      graph: demoProject.storyGraph, sceneBeats: demoProject.sceneBeats, selectionRevision: 0, mediaReadPhase: "ready", readOnly: false }) : null] })));
  await render();
  return { jobs, backend, budget, render, get text() { return host.querySelector("[data-hint]")?.textContent; },
    activate: async (value: boolean) => { active = value; await render(); }, project: async (value: string) => { projectId = value; await render(); },
    revise: async () => { revision++; await render(); },
    select: async () => { shot = demoProject.storyboard.shots[1]; approvalId = "approval"; await render(); }, close: () => act(async () => root.unmount()) };
}
it("observes the media owner's reads once and invalidates advice for selected entity changes", async () => {
  const view = await harness();
  try {
    expect(view.text).toContain("前往分镜审核");
    await view.render();
    expect(view.jobs).toHaveBeenCalledOnce(); expect(view.backend).toHaveBeenCalledOnce(); expect(view.budget).toHaveBeenCalledOnce();
    await view.select(); expect(view.text).toContain("查看关键帧");
    expect(view.jobs).toHaveBeenCalledOnce();
  } finally { await view.close(); }
});
it("revalidates the existing video owner before reporting readiness for a new project revision", async () => {
  const view = await harness(), pending = deferred<{ jobs: VideoJob[] }>();
  try {
    view.jobs.mockReturnValueOnce(pending.promise); await view.revise();
    expect(view.text).toContain("正在读取镜头视频状态");
    expect(view.jobs).toHaveBeenCalledTimes(2);
    await act(async () => pending.resolve({ jobs: [] })); expect(view.text).toContain("前往分镜审核");
  } finally { await view.close(); }
});
it("withdraws hints on page exit and suppresses old project A-B-A completions", async () => {
  const view = await harness(), old = deferred<{ jobs: VideoJob[] }>(), current = deferred<{ jobs: VideoJob[] }>();
  try {
    await view.activate(false); expect(view.text).toBe("等待当前镜头读取");
    await view.activate(true);
    view.jobs.mockReturnValueOnce(old.promise); await view.project("b");
    view.jobs.mockReturnValueOnce(current.promise); await view.project("a");
    await act(async () => old.resolve({ jobs: [] })); expect(view.text).toContain("正在读取镜头视频状态");
    await act(async () => current.resolve({ jobs: [] })); expect(view.text).toContain("前往分镜审核");
  } finally { await view.close(); }
});
