import type { SceneBeatPlan, Shot, StoryGraph, Storyboard, VideoJob } from "../src/types";

export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

export function job(projectId: string, shotId: string): VideoJob {
  return {
    id: `job-${projectId}`, projectId, state: "prepared", lifecycleStatus: "active", inputStatus: "current", cancelRequestedAt: null,
    requestedSeconds: 5, current: true, selected: false, selectionRevision: 0, providerPredictionId: null,
    outputHash: null, observed: null, error: null, reviews: [], snapshot: { shot: { id: shotId, title: `Shot ${shotId}` } },
  };
}

export function selectedJob(id: string, order: number, overrides: Partial<VideoJob> = {}): VideoJob {
  return {
    ...job("project", `shot-${order}`), id, state: "ingested", selected: true,
    playbackSegment: {
      id: `segment-${id}`, videoJobId: id, shotId: `shot-${order}`,
      inFrame: 0, outFrame: 144, authoredDurationUnits: 6_000,
      sourceProbe: { frameCount: 192, fps: "24/1" },
      derivativeProbe: { frameCount: 144, fps: "24/1" },
      derivativeHash: `digest-${id}`, previewEligible: true, current: true, selected: true,
      selectedRevision: 1, createdAt: "2026-09-23T00:00:00Z",
    },
    snapshot: { shot: { id: `shot-${order}`, title: `Shot ${order}`, sceneId: "scene", order } },
    ...overrides,
  };
}

export function routeContext(shotIds: string[], sceneId = "scene"): { storyboard: Storyboard; sceneBeats: SceneBeatPlan; graph: StoryGraph; routeId: string } {
  return {
    graph: {
      startNodeId: "start",
      nodes: [
        { id: "start", title: "Route scene", kind: "start", footageMode: "footage", summary: "Opening footage." },
        { id: "end", title: "End", kind: "ending", footageMode: "footage", summary: "Ending footage." },
      ],
      edges: [{ id: "last", sourceNodeId: "start", targetNodeId: "end", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] }],
      joinContracts: [],
    },
    sceneBeats: { scenes: [
      { id: sceneId, storyNodeId: "start", title: "Route scene", order: 1 },
      { id: "ending-scene", storyNodeId: "end", title: "Ending", order: 1 },
    ] as SceneBeatPlan["scenes"], beats: [], dialogueCues: [] },
    storyboard: { shots: [...shotIds.map((id, index) => ({ id, sceneId, title: id, order: index + 1, durationUnits: 6_000 } as Shot)),
      { id: "ending-shot", sceneId: "ending-scene", title: "Ending", order: 1, durationUnits: 6_000 } as Shot], shotBeatLinks: [] },
    routeId: "start/end",
  };
}

export function endingJob(projectId = "project"): VideoJob {
  return selectedJob("ending-job", 1, { projectId, snapshot: { shot: { id: "ending-shot", sceneId: "ending-scene", order: 1 } } });
}

export function props(projectId: string, shotId: string, sceneId?: string) {
  const route = routeContext([...new Set(shotId === "shot-3" ? ["shot-1", "shot-2", "shot-3"] : shotId === "new-shot" ? ["new-shot"] : ["shot-1", "shot-2"])]);
  return {
    projectId, shot: { id: shotId, title: `Shot ${shotId}`, sceneId } as Shot,
    approvalId: "approval", storyboardRevision: 1, selectionRevision: 1, mediaReadPhase: "ready" as const, readOnly: false,
    ...route,
    routeId: sceneId === "other" ? undefined : route.routeId,
  };
}

export function branchingFixture() {
  const graph: StoryGraph = {
    startNodeId: "scene",
    nodes: ["scene", "decision", "left", "right"].map((id) => ({
      id, title: id, footageMode: "footage" as const, kind: id === "scene" ? "start" : id === "decision" ? "decision" : id === "left" || id === "right" ? "ending" : "scene", summary: "",
    })),
    edges: [
      ["start", "scene", "continuation"], ["scene", "decision", "continuation"], ["decision", "left", "choice"], ["decision", "right", "choice"],
    ].map(([sourceNodeId, targetNodeId, kind], index) => ({
      id: `edge-${index}`, sourceNodeId, targetNodeId, kind: kind as "choice" | "continuation", choiceText: kind === "choice" ? targetNodeId : null, stateEffects: {}, entityStateEffects: [],
    })),
    joinContracts: [],
  };
  graph.edges = graph.edges.filter(edge => edge.sourceNodeId !== "start");
  const sceneBeats = { scenes: ["scene", "decision", "left", "right"].map((storyNodeId, index) => ({
    id: `${storyNodeId}-scene`, storyNodeId, title: storyNodeId, order: index + 1,
  })) as SceneBeatPlan["scenes"], beats: [], dialogueCues: [] };
  const storyboard = { shots: ["scene", "decision", "left", "right"].map((id) => ({
    id: `${id}-shot`, sceneId: `${id}-scene`, title: id, order: 1, durationUnits: 6_000,
  })) as Shot[], shotBeatLinks: [] } satisfies Storyboard;
  const selected = ["scene", "decision", "left", "right"].map((id) => selectedJob(`${id}-job`, 1, {
    snapshot: { shot: { id: `${id}-shot`, title: id, sceneId: `${id}-scene`, order: 1 } },
  }));
  return { graph, sceneBeats, storyboard, selected };
}
