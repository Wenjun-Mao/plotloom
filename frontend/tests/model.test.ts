import { describe, expect, it } from "vitest";
import { demoProject, demoRun } from "../src/demo";
import { deriveRoutes, groupStoryboard, markDownstreamStale, toggleContiguousStageRange, traceEvents } from "../src/model";
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
          id: "prompt", runId: run.id, attemptId: null, sourceArtifactId: null, stage: "story_bible", kind: "prompt", mediaType: "application/json", contentHash: "a".repeat(64), createdAt: "2026-08-30T00:00:00Z",
          content: { messages: [{ role: "system", content: "SYSTEM EXACT" }, { role: "user", content: "USER EXACT" }] },
        },
        {
          id: "validation", runId: run.id, attemptId: null, sourceArtifactId: null, stage: "story_bible", kind: "validation", mediaType: "application/json", contentHash: "b".repeat(64), createdAt: "2026-08-30T00:00:01Z",
          content: { accepted: false, issues: [{ code: "missing" }] },
        },
      ],
      snapshotIsCurrent: true,
    };
    const events = traceEvents(trace);
    expect(events[0]).toMatchObject({ systemPrompt: "SYSTEM EXACT", userPrompt: "USER EXACT", status: "ok" });
    expect(events[1]).toMatchObject({ status: "error" });
  });
});
