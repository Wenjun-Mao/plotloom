import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { VideoPilotPanel, selectedRouteVideos } from "../src/video-pilot";
import { BranchingVideoPreview, branchingPreviewManifest } from "../src/branching-video-preview";
import { VideoSegmentReview } from "../src/video-segment-review";
import { plotloomApi } from "../src/api";
import { isCurrentVideoSelection, videoNextAction } from "../src/features/media/video-next-action";
import { frozenVideoSnapshot } from "../src/features/media/frozen-video-snapshot";
import { bridgeState, installedProduction } from "./production-bridge-fixture";
import type { ManagedAsset, SceneBeatPlan, Shot, StoryGraph, Storyboard, VideoBackend, VideoJob } from "../src/types";
import { branchingFixture, deferred, endingJob, job, props, routeContext, selectedJob } from "./video-pilot-fixtures";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;

let host: HTMLDivElement;

const dialogDescriptors = ["showModal", "close"].map(name => Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name));

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

afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); ["showModal", "close"].forEach((name, index) => { if (dialogDescriptors[index]) Object.defineProperty(HTMLDialogElement.prototype, name, dialogDescriptors[index]!); else Reflect.deleteProperty(HTMLDialogElement.prototype, name); }); });

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
    nodes: ["start", "common", "decision", "left", "right", "end"].map((id) => ({ id, title: id, kind: nodeKind(id), footageMode: "footage" as const, summary: "" })),
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

it("traverses a state-free route-only join without inventing footage", async () => {
  const fixture = branchingFixture();
  fixture.graph.nodes.filter(node => node.id === "left" || node.id === "right").forEach(node => { node.kind = "scene"; });
  fixture.graph.nodes.push(
    { id: "merge", title: "Merge", kind: "join", footageMode: "route_only", summary: "Routes reunite." },
    { id: "end", title: "End", kind: "ending", footageMode: "footage", summary: "Ending footage." },
  );
  fixture.graph.edges.push(...[["left", "merge"], ["right", "merge"], ["merge", "end"]].map(([sourceNodeId, targetNodeId]) => ({
    id: `${sourceNodeId}-${targetNodeId}`, sourceNodeId, targetNodeId, kind: "continuation" as const,
    choiceText: null, stateEffects: {}, entityStateEffects: [],
  })));
  fixture.graph.joinContracts.push({ id: "join-merge", joinNodeId: "merge", incomingNodeIds: ["left", "right"],
    requiredStateKeys: [], allowedDifferences: [], reconciliation: "The paths reunite.", notes: "" });
  fixture.sceneBeats.scenes.push({ id: "ending-scene", storyNodeId: "end", title: "Ending", order: 1 } as SceneBeatPlan["scenes"][number]);
  fixture.storyboard.shots.push({ id: "ending-shot", sceneId: "ending-scene", title: "Ending", order: 1, durationUnits: 6_000 } as Shot);
  fixture.selected.push(endingJob());
  const manifest = branchingPreviewManifest("project", fixture.selected, fixture.storyboard, fixture.sceneBeats, fixture.graph);
  expect(manifest.nodes.get("merge")?.jobs).toEqual([]);
  expect(manifest.nodes.get("merge")?.missingShotTitles).toEqual([]);
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  const finish = async (id: string) => {
    const player = host.querySelector(`[data-testid="branching-video-job-${id}"]`) as HTMLVideoElement;
    expect(player).not.toBeNull();
    await act(async () => { player.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  };
  await finish("scene-job");
  await finish("decision-job");
  await act(async () => { [...host.querySelectorAll('[data-testid="branching-choices"] button')]
    .find(button => button.textContent === "left")?.dispatchEvent(new MouseEvent("click", { bubbles: true })); await Promise.resolve(); });
  await finish("left-job");
  expect(host.querySelector('[data-testid="branching-video-job-ending-job"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="branching-video-job-right-job"]')).toBeNull();
  expect(host.textContent).toContain("选择历史：left");
});

it("blocks missing mandatory footage in branching and ordered playback", async () => {
  const fixture = branchingFixture();
  fixture.sceneBeats.scenes = fixture.sceneBeats.scenes.filter(scene => scene.storyNodeId !== "scene");
  fixture.storyboard.shots = fixture.storyboard.shots.filter(shot => shot.sceneId !== "scene-scene");
  const manifest = branchingPreviewManifest("project", fixture.selected, fixture.storyboard, fixture.sceneBeats, fixture.graph);
  expect(manifest.nodes.get("scene")?.missingShotTitles).toEqual(["scene（缺少已编排场景或镜头）"]);
  expect(selectedRouteVideos(fixture.selected, fixture.storyboard, fixture.sceneBeats, fixture.graph, "scene/decision/left")?.missingShotTitles)
    .toContain("scene（缺少已编排场景或镜头）");
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  expect(host.querySelector('[data-testid="branching-missing-media"]')?.textContent).toContain("缺少已编排场景或镜头");
  expect(host.querySelector('[data-testid^="branching-video-job"]')).toBeNull();
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
});

it("pins selected media by canonical node order and surfaces missing branching media", () => {
  const fixture = branchingFixture();
  const manifest = branchingPreviewManifest("project", fixture.selected, fixture.storyboard, fixture.sceneBeats, fixture.graph);
  expect(manifest.nodes.get("decision")?.jobs.map((job) => job.id)).toEqual(["decision-job"]);
  expect(manifest.nodes.get("right")?.missingShotTitles).toEqual([]);
  const missing = branchingPreviewManifest("project", fixture.selected.filter((job) => job.id !== "right-job"), fixture.storyboard, fixture.sceneBeats, fixture.graph);
  expect(missing.nodes.get("right")?.missingShotTitles).toEqual(["right"]);
});

it("keeps structural footage gaps and exact missing-clip recovery visible together", async () => {
  const fixture = branchingFixture();
  fixture.sceneBeats.scenes = fixture.sceneBeats.scenes.filter(scene => scene.storyNodeId !== "scene");
  fixture.storyboard.shots = fixture.storyboard.shots.filter(shot => shot.sceneId !== "scene-scene");
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected.filter(item => item.id !== "right-job"),
    storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  const warning = host.querySelector('[data-testid="branching-missing-media"]')!;
  expect(warning.querySelector("small")?.textContent).toContain("1 个镜头缺少当前已确认的播放片段");
  expect(warning.textContent).toContain("scene（缺少已编排场景或镜头）");
  expect(warning.querySelectorAll("a")).toHaveLength(1);
  expect(warning.querySelector("a")?.getAttribute("href")).toBe("?project=project&stage=storyboard&entity=shot%3Aright-shot#shot-workbench");
  expect(warning.querySelector("a")?.textContent).toBe("返回镜头 节点 4：right · 场次 1 · 镜头 1：right 审核片段");
  expect(host.querySelector('[data-testid^="branching-video-job"]')).toBeNull();
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
