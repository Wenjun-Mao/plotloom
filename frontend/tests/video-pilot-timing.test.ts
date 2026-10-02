import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { VideoPilotPanel } from "../src/video-pilot";
import type { ManagedAsset, VideoBackend } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement;
let root: Root;
const keyframe: ManagedAsset = {
  id: "frame", projectId: "project", originalHash: "a".repeat(64), displayHash: "b".repeat(64),
  mimeType: "image/png", byteSize: 1, width: 832, height: 480, createdAt: "2026-10-02T00:00:00Z", provenance: null,
};
const backend: VideoBackend = {
  enabled: true, adapterId: "minimax_h3_gateway", nativeAudio: true, tracksPaidWanPilot: false,
  qualifiedDurationSeconds: Array.from({ length: 11 }, (_, index) => index + 5), defaultProfileId: "landscape",
  profiles: [{ id: "landscape", version: 2, label: "Landscape", quality: 8, orientation: "landscape", tier: "fast", width: 832, height: 480,
    durationSeconds: 5, fps: 24, frameCount: 124, nativeAudio: true }],
};

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue(backend);
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValue({ revision: 0, assetId: null });
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

async function render(durationUnits: number, requestSeconds: number) {
  await act(async () => root.render(createElement(VideoPilotPanel, {
    projectId: "project", shot: { ...demoProject.storyboard.shots[0], durationUnits },
    approvalId: "approval", storyboardRevision: 1, selectionRevision: 1, readOnly: false, keyframe,
    graph: demoProject.storyGraph, storyboard: demoProject.storyboard, sceneBeats: demoProject.sceneBeats,
  })));
  await act(async () => { await Promise.resolve(); });
  const duration = host.querySelector('[aria-label="H3 时长（已审核）"]') as HTMLSelectElement;
  await act(async () => { duration.value = String(requestSeconds); duration.dispatchEvent(new Event("change", { bubbles: true })); });
  return Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "读取当前来源")!;
}

it.each([[2500, 5, 124, "segment_required"], [6000, 6, 158, "segment_required"], [12000, 12, 294, "segment_required"], [8000, 8, 192, "source_exact"]])(
  "binds source %s ms to the actual %s-second/%s-frame request and %s intent", async (milliseconds, seconds, frames, intent) => {
    const preview = vi.spyOn(plotloomApi, "previewH3Prompt").mockResolvedValue({ sourceHash: "a".repeat(64), sources: [], compiledPrompt: null });
    const load = await render(Number(milliseconds), Number(seconds));
    expect(host.querySelector('[data-testid="h3-authored-timing"]')?.textContent).toContain(`${frames} 帧`);
    expect(load.disabled).toBe(false);
    await act(async () => { load.click(); await Promise.resolve(); });
    expect(preview).toHaveBeenCalledWith("project", expect.objectContaining({ requestedDurationSeconds: seconds, playbackIntent: intent }));
  },
);

it.each([[1001, 5], [6000, 5], [16000, 15]])("does not read a prompt for off-grid or uncovered source %s ms/request %s", async (milliseconds, seconds) => {
  const preview = vi.spyOn(plotloomApi, "previewH3Prompt");
  expect((await render(milliseconds, seconds)).disabled).toBe(true);
  expect(preview).not.toHaveBeenCalled();
});

it("does not infer a qualified request from an unavailable catalog", async () => {
  vi.mocked(plotloomApi.getVideoBackend).mockResolvedValue({ ...backend, qualifiedDurationSeconds: undefined });
  const preview = vi.spyOn(plotloomApi, "previewH3Prompt");
  expect((await render(2500, 5)).disabled).toBe(true);
  expect(preview).not.toHaveBeenCalled();
});
