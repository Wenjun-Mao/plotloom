import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { ShotPreparationSummary } from "../src/features/media/ShotPreparationSummary";
import type { ProductionBridgeState, VisualWorkbench } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const emptyWorkbench: VisualWorkbench = { assets: [], selectionRevision: 0, visualIntents: [], reviewedKeyframes: [], characterReferences: { states: [], decisions: [] }, samePersonReviews: { revision: 0, reviews: [] }, previews: [] };

function bridge(seconds: number): ProductionBridgeState {
  return { status: "accepted", staleReasons: [], installedStageRevisions: { storyboard: 1 }, installedStoryboardCurrent: true, proposal: {
    revision: 2, contentHash: "a".repeat(64), inputs: {}, scenes: [], conflicts: [], advisories: [], installable: true, preparedAt: "2026-09-23T00:00:00Z",
    cuts: [{ shotId: "opening-s1-c1", sectionId: "opening", episode: 1, sceneIndex: 1, seconds, source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: 1 } }],
    intentPackage: { suggestionOrigin: "none", reviewState: "author_saved", entries: [] },
  } };
}

async function render(seconds: number, projectId = "one") {
  const shot = { ...demoProject.storyboard.shots[0], id: "opening-s1-c1", durationUnits: seconds * 1000 };
  await act(async () => root.render(createElement(ShotPreparationSummary, { projectId, shot, storyboardRevision: 1, draftChanged: false, review: null, workbench: emptyWorkbench, mediaLoaded: true })));
  await act(async () => { await Promise.resolve(); });
}

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

it("shows disabled backend and incompatible six-second source as distinct blockers", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(6));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, qualifiedDurationSeconds: [5, 8] });
  await render(6);
  expect(host.textContent).toContain("精确来源时长 6 秒");
  expect(host.textContent).toContain("缺少当前批准");
  expect(host.textContent).toContain("未配置；不能准备或提交视频");
  expect(host.querySelector('[data-testid="shot-duration-compatibility"]')?.textContent).toContain("6 秒不在当前请求目录");
  expect(host.textContent).not.toContain("已配置");
});

it("does not call a catalog-matching eight-second shot ready when prerequisites are missing", async () => {
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridge(8));
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false, qualifiedDurationSeconds: [5, 8] });
  await render(8);
  expect(host.querySelector('[data-testid="shot-duration-compatibility"]')?.textContent).toContain("8 秒在当前请求目录内");
  expect(host.textContent).toContain("缺少当前批准");
  expect(host.textContent).toContain("未配置；不能准备或提交视频");
  expect(host.textContent).toContain("不是投产许可");
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
