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

it("waits at a decision, follows only the clicked edge, holds an ending, and ignores duplicate ended events", async () => {
  const fixture = branchingFixture();
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  await act(async () => { await Promise.resolve(); });
  const scene = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  expect(scene).not.toBeNull();
  expect(host.textContent).toContain("选择历史：尚未选择");
  await act(async () => { scene.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  const decision = host.querySelector('[data-testid="branching-video-job-decision-job"]') as HTMLVideoElement;
  expect(decision).not.toBeNull();
  expect(play).toHaveBeenCalledTimes(1);
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
  await act(async () => { decision.dispatchEvent(new Event("ended", { bubbles: true })); decision.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  const choices = [...host.querySelectorAll('[data-testid="branching-choices"] button')] as HTMLButtonElement[];
  expect(choices.map((choice) => choice.textContent)).toEqual(["left", "right"]);
  await act(async () => { choices.find((choice) => choice.textContent === "right")?.click(); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-video-job-right-job"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="branching-video-job-left-job"]')).toBeNull();
  expect(host.textContent).toContain("选择历史：right");
  expect(host.textContent).not.toContain("选择历史：edge-");
  expect(play).toHaveBeenCalledTimes(2);
  const right = host.querySelector('[data-testid="branching-video-job-right-job"]') as HTMLVideoElement;
  await act(async () => { right.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-video-job-right-job"]')).not.toBeNull();
  expect([...host.querySelectorAll("button")].some((button) => button.textContent === "重新开始分支预览")).toBe(true);
});

it("creates a fresh media episode when an ending is restarted", async () => {
  const fixture = branchingFixture();
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  const scene = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  await act(async () => { scene.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  const decision = host.querySelector('[data-testid="branching-video-job-decision-job"]') as HTMLVideoElement;
  await act(async () => { decision.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  await act(async () => { [...host.querySelectorAll('[data-testid="branching-choices"] button')].find((choice) => choice.textContent === "left")?.dispatchEvent(new MouseEvent("click", { bubbles: true })); await Promise.resolve(); });
  const ending = host.querySelector('[data-testid="branching-video-job-left-job"]') as HTMLVideoElement;
  await act(async () => { ending.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  ending.currentTime = 0.5;
  await act(async () => { [...host.querySelectorAll("button")].find((button) => button.textContent === "重新开始分支预览")?.click(); await Promise.resolve(); });
  const restarted = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  expect(restarted).not.toBe(scene);
  expect(restarted.currentTime).toBe(0);
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
  expect(host.textContent).toContain("选择历史：尚未选择");
});

it("does not auto-traverse a canonical decision with one outgoing edge, including an empty decision node", async () => {
  const fixture = branchingFixture();
  fixture.graph.edges = fixture.graph.edges.filter((edge) => edge.id !== "edge-3");
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  await act(async () => { await Promise.resolve(); });
  const scene = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  await act(async () => { scene.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  const decision = host.querySelector('[data-testid="branching-video-job-decision-job"]') as HTMLVideoElement;
  await act(async () => { decision.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-video-job-left-job"]')).toBeNull();
  expect(host.querySelector('[data-testid="branching-choices"]')?.textContent).toContain("left");

  const emptyGraph = structuredClone(fixture.graph);
  emptyGraph.startNodeId = "decision";
  emptyGraph.nodes.find(node => node.id === "decision")!.footageMode = "route_only";
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected.filter(job => job.id !== "decision-job"),
    storyboard: { ...fixture.storyboard, shots: fixture.storyboard.shots.filter(shot => shot.id !== "decision-shot") },
    sceneBeats: { ...fixture.sceneBeats, scenes: fixture.sceneBeats.scenes.filter(scene => scene.storyNodeId !== "decision") }, graph: emptyGraph,
  })));
  await act(async () => { await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-choices"]')?.textContent).toContain("left");
});

it("pauses replaced session media before a project change can leave it playing", async () => {
  const fixture = branchingFixture();
  const pause = vi.mocked(HTMLMediaElement.prototype.pause);
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  await act(async () => { await Promise.resolve(); });
  const oldPlayer = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  expect(oldPlayer).not.toBeNull();
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "replacement", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  expect(pause).toHaveBeenCalledWith();
});

it("turns a corrupt selected-media load error into a blocking gap without advancing", async () => {
  const fixture = branchingFixture();
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  const player = host.querySelector('[data-testid="branching-video-job-scene-job"]') as HTMLVideoElement;
  await act(async () => { player.dispatchEvent(new Event("error", { bubbles: true })); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-missing-media"]')?.textContent).toContain("scene");
  expect(host.querySelector('[data-testid="branching-missing-media"] a')?.getAttribute("href"))
    .toBe("?project=project&stage=storyboard&entity=shot%3Ascene-shot#shot-workbench");
  expect(host.querySelector('[data-testid="branching-video-job-scene-job"]')).toBeNull();
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
});

it("uses the explicit current-play control without changing the branching session", async () => {
  const fixture = branchingFixture();
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  await act(async () => root.render(createElement(BranchingVideoPreview, {
    projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
  })));
  await act(async () => { await Promise.resolve(); });
  await act(async () => { [...host.querySelectorAll("button")].find((button) => button.textContent === "播放当前")?.click(); await Promise.resolve(); });
  expect(play).toHaveBeenCalledTimes(1);
  expect(host.textContent).toContain("当前段落：scene");
});

it("scopes selected playback by project, scene, and current selected membership", async () => {
  const oldFirst = selectedJob("old-first", 1, { projectId: "old" });
  const oldSecond = selectedJob("old-second", 2, { projectId: "old" });
  const oldThird = selectedJob("old-third", 3, { projectId: "old", selected: false, snapshot: { shot: { id: "shot-3", title: "Third", sceneId: "scene", order: 3 } } });
  const otherScene = selectedJob("other-scene", 1, { projectId: "old", snapshot: { shot: { id: "other-scene", title: "Other", sceneId: "other", order: 1 } } });
  const newFirst = selectedJob("new-first", 1, { projectId: "new", snapshot: { shot: { id: "new-shot", title: "New", sceneId: "scene", order: 1 } } });
  let oldJobs = [oldFirst, oldSecond, oldThird, otherScene, endingJob("old")];
  const membershipReview = deferred<unknown>();
  vi.spyOn(plotloomApi, "getVideoJobs").mockImplementation(async (projectId) => ({
    jobs: projectId === "old" ? oldJobs : [newFirst, endingJob("new")],
  }));
  vi.spyOn(plotloomApi, "reviewVideoJob").mockImplementation(async () => {
    oldJobs = [oldFirst, oldSecond, { ...oldThird, selected: true }, otherScene, endingJob("old")];
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
  await render("old", "shot-3", "scene");
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
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [first, second, endingJob()] });
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
  const endingPlayer = host.querySelector('[data-testid="video-sequence-job-ending-job"]') as HTMLVideoElement;
  expect(endingPlayer).not.toBeNull();
  await act(async () => { endingPlayer.dispatchEvent(new Event("ended", { bubbles: true })); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="video-sequence-job-ending-job"]')).not.toBeNull();
  expect(play).toHaveBeenCalledTimes(2);

  play.mockRejectedValueOnce(new Error("gesture required"));
  await act(async () => { [...host.querySelectorAll("button")].find((item) => item.textContent === "播放当前")?.click(); await Promise.resolve(); });
  expect(host.querySelector('[role="status"]')?.textContent).toContain("gesture required");
});

it("shows the source-bound question only after opening completion and closes on stale or failed ownership", async () => {
  const fixture = branchingFixture();
  fixture.graph.startNodeId = "decision";
  fixture.selected = fixture.selected.map(item => ({ ...item, snapshot: { ...frozenVideoSnapshot(item), sourceTiming: { kind: "f5_bridge" } } }));
  const sourceChoice = { choiceId: "decision", sectionId: "decision", prompt: "她今晚应该赴约吗？", outcomes: [
    { outcomeId: "edge-2", endingSectionId: "left", label: "left", consequence: "Left ending" },
    { outcomeId: "edge-3", endingSectionId: "right", label: "right", consequence: "Right ending" },
  ] };
  const read = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridgeState({ status: "accepted", installation: installedProduction({ runtimeChoice: { choices: [sourceChoice] } }) }));
  const renderFixture = () => root.render(createElement(BranchingVideoPreview, { projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph }));
  await act(async () => { renderFixture(); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-choice-question"]')).toBeNull();
  await act(async () => { host.querySelector("video")!.dispatchEvent(new Event("ended", { bubbles: true })); });
  expect(host.querySelector('[data-testid="branching-choice-question"]')?.textContent).toBe(sourceChoice.prompt);
  expect(host.querySelector('[data-testid="branching-choices"]')?.textContent).toContain("left");
  const next = deferred<Awaited<ReturnType<typeof plotloomApi.getProductionBridge>>>();
  read.mockReturnValue(next.promise);
  fixture.selected = fixture.selected.map(item => ({ ...item, snapshot: { ...frozenVideoSnapshot(item), sourceTiming: { kind: "f5_bridge", revision: 2 } } }));
  await act(async () => renderFixture());
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
  await act(async () => { next.reject(new Error("source ownership unavailable")); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
});

it.each(["stale", "foreign-current"])("canonical choices ignore %s bridge job history outside admitted playback", async (historyKind) => {
  const fixture = branchingFixture();
  fixture.graph.startNodeId = "decision";
  const historical = selectedJob("historical-bridge", 1, {
    current: historyKind !== "stale", selected: historyKind !== "stale",
    snapshot: { shot: { id: "retired-shot", sceneId: "retired-scene" }, sourceTiming: { kind: "f5_bridge" } },
  });
  const read = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridgeState({ status: "accepted", installation: installedProduction({ status: "outdated", runtimeChoice: null }) }));
  await act(async () => root.render(createElement(BranchingVideoPreview, { projectId: "project", jobs: [...fixture.selected, historical], storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph })));
  await act(async () => host.querySelector("video")!.dispatchEvent(new Event("ended", { bubbles: true })));
  expect(host.querySelector('[data-testid="branching-choices"]')?.textContent).toContain("left");
  expect(host.querySelector('[data-testid="branching-choices"]')?.textContent).toContain("right");
  expect(read).not.toHaveBeenCalled();
});
