import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { ShotPreparationSummary } from "../src/features/media/ShotPreparationSummary";
import type { ProductionBridgeState, VisualWorkbench } from "../src/types";
import { sourceSecondsToMilliseconds } from "../src/production-timing";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const emptyWorkbench: VisualWorkbench = { assets: [], selectionRevision: 0, visualIntents: [], reviewedKeyframes: [], characterReferences: { states: [], decisions: [] }, samePersonReviews: { revision: 0, reviews: [] }, previews: [] };

function bridge(seconds: number): ProductionBridgeState {
  return { intentGeneration: { status: "available" }, status: "accepted", staleReasons: [], installedStageRevisions: { storyboard: 1 }, installedStoryboardCurrent: true, hasInstallation: false, proposal: {
    presentation: { version: 1, reviewed: true, sourceHash: "f".repeat(64), sources: [], runtimeChoice: { choices: [] }, frozenEvidence: {} },
    revision: 2, contentHash: "a".repeat(64), inputs: {}, scenes: [], conflicts: [], advisories: [], installable: true, preparedAt: "2026-09-23T00:00:00Z",
    cuts: [{ shotId: "opening-s1-c1", sectionId: "opening", episode: 1, sceneIndex: 1, seconds, source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: 1 } }],
    intentPackage: { suggestionOrigin: "none", reviewState: "author_saved", entries: [] },
  } };
}

async function render(seconds: number, projectId = "one", mediaReadPhase: "loading" | "ready" | "error" = "ready", onRetryMedia?: () => void) {
  const shot = { ...demoProject.storyboard.shots[0], id: "opening-s1-c1", durationUnits: sourceSecondsToMilliseconds(seconds)! };
  await act(async () => root.render(createElement(ShotPreparationSummary, { projectId, shot, storyboardRevision: 1, draftChanged: false, review: null, workbench: emptyWorkbench, mediaReadPhase, onRetryMedia })));
  await act(async () => { await Promise.resolve(); });
}

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

it("shows the conditional eight-to-six path while keeping disabled dispatch distinct", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(6));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, adapterId: "minimax_h3_gateway", qualifiedDurationSeconds: [5, 8] });
  await render(6);
  expect(host.textContent).toContain("精确来源时长 6 秒");
  expect(host.textContent).toContain("缺少当前批准");
  expect(host.textContent).toContain("未配置；不能准备或提交视频");
  expect(host.querySelector('[data-testid="shot-duration-compatibility"]')?.textContent).toContain("6 秒原稿需要 144 帧；目录内 8 秒请求提供 192 帧容量");
  expect(host.querySelector('[data-testid="shot-duration-compatibility"]')?.textContent).toContain("连续片段须经人工听看并明确选择");
  expect(host.querySelector('[data-testid="shot-duration-compatibility"]')?.textContent).toContain("当前后端未配置，暂不能提交请求");
  expect(host.textContent).not.toContain("已明确选择");
});

it("does not call a catalog-matching eight-second shot ready when prerequisites are missing", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(8));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, qualifiedDurationSeconds: [5, 8] });
  await render(8);
  expect(host.querySelector('[data-testid="shot-duration-compatibility"]')?.textContent).toContain("8 秒在当前请求目录内");
  expect(host.textContent).toContain("缺少当前批准");
  expect(host.textContent).toContain("未配置；不能准备或提交视频");
  expect(host.textContent).toContain("批准分镜、审核素材和选用故事片段仍需在对应步骤完成");
});

it.each([[2.5, 60, 5, 124], [6, 144, 6, 158], [8, 192, 8, 192]])(
  "explains %s-second source coverage using the actual disabled H3 API projection", async (seconds, sourceFrames, requestSeconds, requestFrames) => {
    vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(seconds));
    vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({
      enabled: false, tracksPaidWanPilot: false, reason: "h3_video_not_configured",
      qualifiedDurationSeconds: Array.from({ length: 11 }, (_, index) => index + 5),
    });
    await render(seconds);
    const timing = host.querySelector('[data-testid="shot-duration-compatibility"]')?.textContent;
    expect(timing).toContain(`${seconds} 秒原稿需要 ${sourceFrames} 帧；目录内 ${requestSeconds} 秒请求提供 ${requestFrames} 帧容量`);
    expect(timing).toContain("当前后端未配置，暂不能提交请求");
    expect(host.textContent).toContain("未配置；不能准备或提交视频");
    expect(host.textContent).not.toContain("其他准备条件仍须审核");
  },
);

it.each([
  { enabled: false },
  { enabled: true, reason: "h3_video_not_configured" },
  { enabled: false, adapterId: "atlas_wan", reason: "h3_video_not_configured" },
])("does not infer H3 ownership from a generic or conflicting capability %j", async (capability) => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(2.5));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ ...capability, qualifiedDurationSeconds: [5, 8] });
  await render(2.5);
  expect(host.textContent).toContain("2.5 秒不在当前请求目录");
  expect(host.textContent).not.toContain("124 帧容量");
});

it("does not repaint a newly selected project with old bridge results", async () => {
  let resolveOld!: (value: ProductionBridgeState) => void;
  vi.spyOn(plotloomApi, "getProductionBridge").mockImplementation((id) => id === "old" ? new Promise((resolve) => { resolveOld = resolve; }) : Promise.resolve(bridge(6)));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, qualifiedDurationSeconds: [5, 8] });
  await render(6, "old");
  await render(6, "new");
  await act(async () => resolveOld(bridge(8)));
  expect(host.textContent).toContain("精确来源时长 6 秒");
  expect(host.textContent).not.toContain("精确来源时长 8 秒");
});

it("recovers bridge and backend read failures through a same-mounted-root retry", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge")
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(bridge(6));
  vi.spyOn(plotloomApi, "getVideoBackend")
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ enabled: false, adapterId: "minimax_h3_gateway", qualifiedDurationSeconds: [5, 8] });
  await render(6);
  expect(host.textContent).toContain("投产来源暂不可读取");
  expect(host.textContent).toContain("时长兼容性未知");
  await act(async () => Array.from(host.querySelectorAll("button")).find((button) => button.textContent?.includes("重试来源与视频能力读取"))!.click());
  await act(async () => { await Promise.resolve(); });
  expect(host.textContent).toContain("精确来源时长 6 秒");
  expect(host.textContent).toContain("目录内 8 秒请求提供 192 帧容量");
  expect(host.textContent).not.toContain("投产来源暂不可读取");
});

it.each([2.5, 1.001, 0.001])("reports actual current fractional source %s seconds without losing coordinates", async (seconds) => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(seconds));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: true, adapterId: "minimax_h3_gateway", qualifiedDurationSeconds: [5, 6, 8, 15] });
  await render(seconds);
  expect(host.textContent).toContain(`精确来源时长 ${seconds} 秒 · 当前绑定`);
  expect(host.textContent).toContain("段 1 / 段内场次 1 / 镜头 1");
  expect(host.querySelector('[data-testid="bridge-source-unavailable"]')).toBeNull();
  const timing = host.querySelector('[data-testid="shot-duration-compatibility"]')?.textContent;
  if (seconds === 2.5) {
    expect(timing).toContain("2.5 秒原稿需要 60 帧；目录内 5 秒请求提供 124 帧容量");
    expect(timing).toContain("不会自动裁切或用于故事");
    expect(timing).toContain("其他准备条件仍须审核");
  } else expect(timing).toContain("不在 24 fps 整数帧网格上");
});

it("uses the actual covering H3 catalog rather than the retired six-to-eight exception", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(6));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: true, adapterId: "minimax_h3_gateway", qualifiedDurationSeconds: [5, 6, 8] });
  await render(6);
  expect(host.textContent).toContain("目录内 6 秒请求提供 158 帧容量");
  expect(host.textContent).not.toContain("仅接受 8 秒原片");
});

it("reports insufficient capacity and an unavailable H3 catalog without admission claims", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(16));
  const backend = vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: true, adapterId: "minimax_h3_gateway", qualifiedDurationSeconds: [5, 15] });
  await render(16);
  expect(host.textContent).toContain("容量不足以覆盖 16 秒原稿");
  backend.mockResolvedValue({ enabled: true, adapterId: "minimax_h3_gateway" });
  await render(16, "new");
  expect(host.textContent).toContain("未知（请求目录不可用）");
});

it("does not apply H3 covering-frame admission to a different backend", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(2.5));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: true, adapterId: "atlas_wan", qualifiedDurationSeconds: [5, 8] });
  await render(2.5);
  expect(host.textContent).toContain("2.5 秒不在当前请求目录");
  expect(host.textContent).not.toContain("124 帧容量");
});

it("does not claim retained media evidence is current after a read error", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(6));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, qualifiedDurationSeconds: [5, 8] });
  const retry = vi.fn();
  await render(6, "one", "error", retry);
  expect(host.textContent).toContain("当前角色参考与关键帧状态未知");
  expect(host.textContent).toContain("角色身份参考：未知（读取失败）");
  expect(host.textContent).toContain("审核关键帧：未知（读取失败）");
  await act(async () => Array.from(host.querySelectorAll("button")).find((button) => button.textContent?.includes("重试媒体读取"))!.click());
  expect(retry).toHaveBeenCalledOnce();
});
