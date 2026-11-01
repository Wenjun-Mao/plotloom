import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { CompletedClips } from "../src/features/video-batch/CompletedClips";
import { plotloomApi } from "../src/api";
import { batchApi } from "../src/features/video-batch/api";
import type { VideoJob } from "../src/types";
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); document.body.replaceChildren(); });
function job(id: string, state: VideoJob["state"]): VideoJob {
  return { id, projectId: "p", state, current: true, selected: id === "a", selectionRevision: 3, outputHash: state === "ingested" ? id : null,
    observed: { durationSeconds: 8, width: 832, height: 480, videoCodec: "h264", audioCodec: "aac" }, snapshot: { shot: { id, sceneId: "scene", title: id }, request: { seed: 12 } },
    lifecycleStatus: "active", inputStatus: "current", cancelRequestedAt: null, requestedSeconds: 8, providerPredictionId: null, reviews: [], error: null };
}
it("reveals two completed clips on the open page while another remains pending, without selection writes", async () => {
  vi.useFakeTimers();
  const read = vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [job("a", "submitted"), job("b", "submitted"), job("c", "submitted")] });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  const select = vi.spyOn(plotloomApi, "reviewVideoJob");
  const host = document.createElement("div"), root = createRoot(host); document.body.append(host);
  try {
    await act(async () => root.render(createElement(CompletedClips, { projectId: "p", disabled: false, onBatch: vi.fn(), onOperator: vi.fn() })));
    expect(host.querySelectorAll("video")).toHaveLength(0);
    read.mockResolvedValue({ jobs: [job("a", "ingested"), job("b", "ingested"), job("c", "submitted")] });
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(host.querySelectorAll("video")).toHaveLength(2);
    expect([...host.querySelectorAll("video")].every(v => v.controls && v.preload === "none")).toBe(true);
    expect(host.textContent).toContain("scene / a / 原片 1");
    expect(select).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); vi.unstubAllGlobals(); }
});
it("uses the visual revision for a selected-shot alternative and retains command errors across completion polling", async () => {
  vi.useFakeTimers();
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [job("a", "ingested")] });
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValue({ selectionRevision: 16 } as Awaited<ReturnType<typeof plotloomApi.getVisualWorkbench>>);
  vi.spyOn(plotloomApi, "getStoryboardReview").mockResolvedValue({ head: { revision: 2 }, activeApproval: { id: "approval" } } as Awaited<ReturnType<typeof plotloomApi.getStoryboardReview>>);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  const setup = vi.spyOn(batchApi, "command").mockRejectedValue(new Error("stale source"));
  const host = document.createElement("div"), root = createRoot(host); document.body.append(host);
  try {
    await act(async () => root.render(createElement(CompletedClips, { projectId: "p", disabled: false, onBatch: vi.fn(), onOperator: vi.fn() })));
    await act(async () => [...host.querySelectorAll("button")].find(b => b.textContent === "重新生成…")!.click());
    await act(async () => [...host.querySelectorAll("button")].find(b => b.textContent === "准备新候选")!.click());
    expect(setup.mock.calls[0][2]).toMatchObject({ singleRequest: { shotId: "a", expectedSelectionRevision: 16, storyboardRevision: 2, playbackIntent: "whole_take" } });
    expect(host.textContent).toContain("stale source");
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(host.textContent).toContain("stale source");
  } finally { await act(async () => root.unmount()); vi.unstubAllGlobals(); }
});
