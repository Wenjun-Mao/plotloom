import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { branchingPreviewManifest } from "../src/branching-video-preview";
import { VideoPilotPanel, selectedRouteVideos } from "../src/video-pilot";
import { isCurrentVideoSelection, videoNextAction } from "../src/features/media/video-next-action";
import { branchingFixture, props } from "./video-pilot-fixtures";
import type { VideoJob } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement;
let root: Root;

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValue({ revision: 0, assetId: null });
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: true, adapterId: "atlas_wan", adapterVersion: "1",
    provider: "atlascloud", model: "alibaba/wan-3.0/image-to-video", durationSeconds: 5, resolution: "720p",
    nativeAudio: true, requiresAspectPolicy: false, tracksPaidWanPilot: true });
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

function frozenFixture() {
  const fixture = branchingFixture();
  fixture.selected = fixture.selected.map(job => ({ ...job, current: false, inputStatus: "stale" as const }));
  return fixture;
}

it.each([false, true])("both players consume selected frozen media while actual-source invalidation=%s", async invalidated => {
  const fixture = frozenFixture();
  if (invalidated) {
    // Exact backend projection after an actual source/approval/selection change.
    fixture.selected[0] = { ...fixture.selected[0], selected: false,
      playbackSegment: { ...fixture.selected[0].playbackSegment!, selected: false, current: false } };
  }
  const routeId = "scene/decision/left";
  const ordered = selectedRouteVideos(fixture.selected, fixture.storyboard, fixture.sceneBeats, fixture.graph, routeId)!;
  const branching = branchingPreviewManifest("project", fixture.selected, fixture.storyboard, fixture.sceneBeats, fixture.graph);
  expect(ordered.missingShotTitles.length > 0).toBe(invalidated);
  expect(branching.nodes.get("scene")!.jobs.length).toBe(invalidated ? 0 : 1);
  expect(isCurrentVideoSelection(fixture.selected[0])).toBe(!invalidated);
  expect(videoNextAction([fixture.selected[0]], 6_000).includes("检查路径预览")).toBe(!invalidated);
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: fixture.selected });
  await act(async () => root.render(createElement(VideoPilotPanel, {
    ...props("project", "scene-shot", "scene-scene"), ...fixture,
    shot: fixture.storyboard.shots[0], routeId,
  })));
  await act(async () => { await Promise.resolve(); });
  const orderedPlayer = host.querySelector('[data-testid="video-sequence-job-scene-job"]');
  const branchingPlayer = host.querySelector('[data-testid="branching-video-job-scene-job"]');
  expect(Boolean(orderedPlayer)).toBe(!invalidated);
  expect(Boolean(branchingPlayer)).toBe(!invalidated);
  if (!invalidated) {
    expect(orderedPlayer?.getAttribute("src")).toBe(plotloomApi.selectedVideoPlaybackUrl("project", "scene-job"));
    expect(branchingPlayer?.getAttribute("src")).toBe(plotloomApi.selectedVideoPlaybackUrl("project", "scene-job"));
    expect(host.textContent).toContain("已为当前镜头选择播放片段");
    // Current-generation selection/reselection authority remains unchanged.
    const reselection = [...host.querySelectorAll("button")].find(button => button.textContent === "选择此候选");
    expect(reselection).toBeDefined(); expect(reselection?.disabled).toBe(true);
  }
});

it.each(["unresolved", "archived", "invalid", "selection", "segment", "duration", "scene", "project"] as const)(
  "frozen playback still rejects %s changes across both builders", mutation => {
    const fixture = frozenFixture(); let changed: VideoJob = fixture.selected[0];
    if (mutation === "unresolved") changed = { ...changed, state: "outcome_unknown" };
    if (mutation === "archived") changed = { ...changed, lifecycleStatus: "archived" };
    if (mutation === "invalid") changed = { ...changed, inputStatus: "invalid" };
    if (mutation === "selection") changed = { ...changed, selected: false };
    if (mutation === "segment") changed = { ...changed, playbackSegment: { ...changed.playbackSegment!, current: false } };
    if (mutation === "duration") changed = { ...changed, playbackSegment: { ...changed.playbackSegment!, authoredDurationUnits: 5_000 } };
    if (mutation === "scene") changed = { ...changed, snapshot: { shot: { id: "scene-shot", sceneId: "changed-scene" } } };
    if (mutation === "project") changed = { ...changed, projectId: "other" };
    const jobs = [changed, ...fixture.selected.slice(1)];
    // The route panel scopes API jobs to its project before calling its builder.
    const ordered = selectedRouteVideos(jobs.filter(job => job.projectId === "project"), fixture.storyboard, fixture.sceneBeats, fixture.graph, "scene/decision/left")!;
    const branching = branchingPreviewManifest("project", jobs, fixture.storyboard, fixture.sceneBeats, fixture.graph);
    expect(ordered.jobs.some(job => job.id === changed.id)).toBe(false);
    expect(branching.nodes.get("scene")!.jobs).toEqual([]);
  },
);
