import { describe, expect, it } from "vitest";
import { demoProject, demoRun } from "../src/demo";
import { deriveRoutes, groupStoryboard, markDownstreamStale, summarizeWorkUnitStatuses, toggleContiguousStageRange, traceEvents } from "../src/model";
import { derivePrototypeRoutes, episodesForRoute, prototypeReadiness, storyboardEpisodesForRoute, storyboardPrototypeReadiness } from "../src/story-prototype-model";
import type { RunTrace } from "../src/types";

describe("Plotloom workspace model", () => {
  it("uses canonical brief and graph HTTP field names", () => {
    expect(demoProject.brief).toMatchObject({
      synopsis: expect.any(String),
      targetPlaythroughSeconds: 180,
      decisionPointsPerPath: 2,
    });
    expect(demoProject.brief).not.toHaveProperty("premise");
    expect(demoProject.storyGraph.edges[0]).toMatchObject({
      sourceNodeId: "arrival",
      targetNodeId: "diagnose",
      kind: "continuation",
      stateEffects: {},
    });
  });

  it("derives complete DAG routes without following cycles", () => {
    const routes = deriveRoutes(demoProject.storyGraph);
    expect(routes).toHaveLength(6);
    expect(routes.every((route) => route.nodeIds[0] === "arrival")).toBe(true);
    expect(routes.some((route) => route.nodeIds.at(-1) === "ending_choice")).toBe(true);
  });

  it("derives both F1B routes from the three canonical authored section IDs", () => {
    const routes = deriveRoutes({
      startNodeId: "tide-entry",
      nodes: [
        { id: "tide-entry", title: "气象站", summary: "选择电力去向。", kind: "start" },
        { id: "dock-ending", title: "码头结局", summary: "码头得电。", kind: "ending" },
        { id: "beacon-ending", title: "灯塔结局", summary: "灯塔得电。", kind: "ending" },
      ],
      edges: [
        { id: "dock-route", sourceNodeId: "tide-entry", targetNodeId: "dock-ending", kind: "choice", choiceText: "供电码头", stateEffects: {}, entityStateEffects: [] },
        { id: "beacon-route", sourceNodeId: "tide-entry", targetNodeId: "beacon-ending", kind: "choice", choiceText: "供电灯塔", stateEffects: {}, entityStateEffects: [] },
      ],
      joinContracts: [],
    });
    expect(routes).toEqual([
      { id: "tide-entry/dock-ending", label: "供电码头 → 码头结局", nodeIds: ["tide-entry", "dock-ending"] },
      { id: "tide-entry/beacon-ending", label: "供电灯塔 → 灯塔结局", nodeIds: ["tide-entry", "beacon-ending"] },
    ]);
  });

  it("maps accepted F4 bindings onto canonical routes and excludes the sibling ending", () => {
    const graph = {
      startNodeId: "opening",
      nodes: [
        { id: "opening", title: "Storm warning", summary: "One cable.", kind: "start" as const },
        { id: "beacon", title: "Beacon lit", summary: "Sailors see home.", kind: "ending" as const },
        { id: "dock", title: "Dock lit", summary: "Boats stay together.", kind: "ending" as const },
      ],
      edges: [
        { id: "beacon-path", sourceNodeId: "opening", targetNodeId: "beacon", kind: "choice" as const, choiceText: "Light the beacon", stateEffects: { sourceMapConsequence: "The dock loses power." }, entityStateEffects: [] },
        { id: "dock-path", sourceNodeId: "opening", targetNodeId: "dock", kind: "choice" as const, choiceText: "Light the dock", stateEffects: { sourceMapConsequence: "The beacon goes dark." }, entityStateEffects: [] },
      ], joinContracts: [],
    };
    const script = { sectionBindings: [{ sectionId: "opening", episode: 1 }, { sectionId: "beacon", episode: 2 }, { sectionId: "dock", episode: 3 }], episodes: [{ ep: 1 }, { ep: 2 }, { ep: 3 }] };
    const routes = derivePrototypeRoutes(graph, script.sectionBindings);

    expect(routes.map((route) => route.sectionIds)).toEqual([["opening", "beacon"], ["opening", "dock"]]);
    expect(episodesForRoute(script, routes[0]).map((item) => item.sectionId)).toEqual(["opening", "beacon"]);
    expect(episodesForRoute(script, routes[0]).map((item) => item.sectionId)).not.toContain("dock");
  });

  it("refuses stale/reopened script state and an out-of-binding canonical graph", () => {
    const binding = { graphRevision: 4, graphContentHash: "graph-hash" };
    const currentHead = { status: "ready" as const, revision: 4, contentHash: "graph-hash" };

    expect(prototypeReadiness("accepted", currentHead, binding)).toBeUndefined();
    expect(prototypeReadiness("stale", currentHead, binding)).toContain("不是可阅读的已接受版本");
    expect(prototypeReadiness("reopened", currentHead, binding)).toContain("不是可阅读的已接受版本");
    expect(prototypeReadiness("accepted", { ...currentHead, status: "stale" }, binding)).toContain("剧情图不可用或已过期");
    expect(prototypeReadiness("accepted", { ...currentHead, contentHash: "newer-graph-hash" }, binding)).toContain("不是当前版本");
  });

  it("admits only the current accepted F5A review and preserves F4 route order", () => {
    const binding = { graphRevision: 4, graphContentHash: "graph-hash", sectionBindings: [{ sectionId: "opening", episode: 1 }, { sectionId: "beacon", episode: 2 }] } as any;
    const script = { revision: 3, contentHash: "script-hash", binding };
    const review = { status: "accepted", acceptedReview: { binding: { ...binding, scriptRevision: 3, scriptContentHash: "script-hash" }, storyboard: { episodes: [{ ep: 2, segments: [] }, { ep: 1, segments: [] }] } } } as any;
    const graph = { startNodeId: "opening", nodes: [{ id: "opening", title: "Opening", summary: "", kind: "start" }, { id: "beacon", title: "Beacon", summary: "", kind: "ending" }], edges: [{ id: "edge", sourceNodeId: "opening", targetNodeId: "beacon", kind: "choice", choiceText: "Beacon", stateEffects: {}, entityStateEffects: [] }], joinContracts: [] } as any;
    const routes = derivePrototypeRoutes(graph, binding.sectionBindings);

    expect(storyboardPrototypeReadiness("accepted", { status: "ready", revision: 4, contentHash: "graph-hash" }, script, review)).toBeUndefined();
    expect(storyboardEpisodesForRoute(review.acceptedReview.storyboard, binding.sectionBindings, routes[0]).map((item) => item.episode.ep)).toEqual([1, 2]);
    expect(storyboardPrototypeReadiness("accepted", { status: "ready", revision: 4, contentHash: "graph-hash" }, script, { ...review, status: "stale" })).toContain("没有可阅读的已接受分镜评审");
    expect(storyboardPrototypeReadiness("accepted", { status: "ready", revision: 4, contentHash: "graph-hash" }, script, { ...review, acceptedReview: { ...review.acceptedReview, binding: { ...review.acceptedReview.binding, scriptContentHash: "old-script" } } })).toContain("绑定的剧本不是当前已接受版本");
    expect(storyboardPrototypeReadiness("accepted", { status: "ready", revision: 4, contentHash: "graph-hash" }, script, { ...review, acceptedReview: { ...review.acceptedReview, binding: { ...review.acceptedReview.binding, graphContentHash: "old-graph" } } })).toContain("绑定的故事图不是当前版本");
    expect(storyboardPrototypeReadiness("accepted", { status: "ready", revision: 4, contentHash: "graph-hash" }, script, { ...review, acceptedReview: { ...review.acceptedReview, binding: { ...review.acceptedReview.binding, sectionBindings: [{ sectionId: "opening", episode: 1 }, { sectionId: "beacon", episode: 3 }] } } })).toContain("章节对应与当前剧本不一致");
  });

  it("marks only downstream stages stale", () => {
    const updated = markDownstreamStale({ ...demoProject, staleStages: [] }, "story_graph");
    expect(updated.staleStages).toEqual(["scene_beats", "storyboard"]);
  });

  it("filters grouped shots to nodes present on the selected route", () => {
    const route = deriveRoutes(demoProject.storyGraph)[0];
    const filtered = groupStoryboard(demoProject.storyboard, demoProject.sceneBeats, route);
    expect(filtered.every((group) => route.nodeIds.includes(group.storyNodeId))).toBe(true);
  });

  it("keeps manual pipeline selections as one dependency-safe contiguous range", () => {
    expect(toggleContiguousStageRange(["story_bible"], "storyboard")).toEqual([
      "story_bible", "story_graph", "scene_beats", "storyboard",
    ]);
    expect(toggleContiguousStageRange(
      ["story_bible", "story_graph", "scene_beats", "storyboard"],
      "story_graph",
    )).toEqual(["story_bible"]);
  });

  it("maps durable prompt messages and rejected validation into the inspector contract", () => {
    const run = { ...demoRun, id: "run", projectId: "project", status: "quarantined" as const, requestedStages: ["story_bible" as const] };
    const trace: RunTrace = {
      run,
      attempts: [],
      artifacts: [
        {
          id: "prompt", runId: run.id, attemptId: null, workUnitId: null, sourceArtifactId: null, stage: "story_bible", kind: "prompt", mediaType: "application/json", contentHash: "a".repeat(64), createdAt: "2026-08-30T00:00:00Z",
          content: { messages: [{ role: "system", content: "SYSTEM EXACT" }, { role: "user", content: "USER EXACT" }] },
        },
        {
          id: "validation", runId: run.id, attemptId: null, workUnitId: null, sourceArtifactId: null, stage: "story_bible", kind: "validation", mediaType: "application/json", contentHash: "b".repeat(64), createdAt: "2026-08-30T00:00:01Z",
          content: { accepted: false, issues: [{ code: "missing" }] },
        },
      ],
      snapshotIsCurrent: true,
    };
    const events = traceEvents(trace);
    expect(events[0]).toMatchObject({ systemPrompt: "SYSTEM EXACT", userPrompt: "USER EXACT", status: "ok" });
    expect(events[1]).toMatchObject({ status: "error" });
  });

  it("shows bounded attempt outcome, failure, and correction lineage", () => {
    const run = { ...demoRun, providerSnapshot: { maxSemanticCorrections: 2 } };
    const trace: RunTrace = {
      run,
      attempts: [{
        id: "attempt-2", runId: run.id, workUnitId: "unit-1", stage: "story_bible", attemptNumber: 2,
        attemptKind: "correction", sourceAttemptId: "attempt-1", status: "failed", provider: "fixture", model: "model",
        error: "schema rejected", dispatchedAt: null, responsePersistedAt: "2026-08-30T00:00:01Z", providerRequestId: null,
        outcomeUnknown: false, outcomeCode: "schema_invalid", startedAt: "2026-08-30T00:00:00Z", finishedAt: "2026-08-30T00:00:02Z",
      }],
      artifacts: [{
        id: "response-2", runId: run.id, attemptId: "attempt-2", workUnitId: "unit-1", sourceArtifactId: null,
        stage: "story_bible", kind: "response", mediaType: "application/json", contentHash: "c".repeat(64),
        createdAt: "2026-08-30T00:00:01Z", content: { usage: { inputTokens: 120, outputTokens: 45 } },
      }], snapshotIsCurrent: true,
    };

    const [event] = traceEvents(trace);
    expect(event.title).toBe("Attempt 2/3 · failed");
    expect(event.detail).toContain("Outcome: schema_invalid");
    expect(event.detail).toContain("Lineage: correction ← attempt-1");
    expect(event.detail).toContain("Elapsed: 2000 ms");
    expect(event.detail).toContain("Tokens: input 120 · output 45");
    expect(event.detail).toContain("Failure: schema rejected");
  });

  it("adds the frozen story topology to the same inspectable trace timeline", () => {
    const topology = { nodes: ["start", "ending"], edges: [["start", "ending"]] };
    const events = traceEvents({ run: demoRun, attempts: [], artifacts: [], snapshotIsCurrent: true }, {
      generationPlan: null,
      storyGraphTopology: { runId: demoRun.id, generationPlanHash: "plan-hash-123456", topologyHash: "topology-hash-123456", topology, createdAt: "2026-08-30T00:00:03Z" },
      stagePlans: [], workUnits: [], sealedAggregates: [],
    });

    expect(events).toContainEqual(expect.objectContaining({
      stage: "story_graph", title: "Story graph topology frozen", payload: topology,
    }));
  });

  it("keeps infrastructure failures distinct from quarantined model content", () => {
    const unit = {
      id: "unit", runId: demoRun.id, stagePlanId: "stage-plan", stage: "story_bible" as const,
      sequence: 1, selector: {}, inputHash: "input", dependencyHash: "dependency",
      unitDependencyHash: "unit-dependency", budget: {}, estimatedInputTokens: 1,
      contextWindowTokens: 32768, status: "failed" as const,
    };
    const execution = {
      generationPlan: null, storyGraphTopology: null, stagePlans: [], sealedAggregates: [],
      workUnits: [unit, { ...unit, id: "unit-2", sequence: 2, status: "quarantined" as const }],
    };

    expect(summarizeWorkUnitStatuses(execution)).toBe("1 failed · 1 quarantined");
  });
});
