import { describe, expect, it } from "vitest";
import { demoProject, demoRun } from "../src/demo";
import { deriveRoutes, groupStoryboard, markDownstreamStale, summarizeWorkUnitStatuses, toggleContiguousStageRange, traceEvents } from "../src/model";
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
