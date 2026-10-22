import { describe, expect, it } from "vitest";
import { demoProject, emptyStageContent } from "../src/demo";
import type { MediaTask, ProjectResource, RunProgress, ServerStageName, StageEnvelope } from "../src/types";
import { editorRevisionKey, hydrateWorkspaceProject, newestMediaTasksByShot, quarantineItemsFromProgress } from "../src/workspace-state";

const mediaTask = (overrides: Partial<MediaTask>): MediaTask => ({
  id: "task",
  projectId: "project",
  shotId: "shot-1",
  storyboardRevision: 1,
  kind: "image",
  status: "queued",
  derivedPrompt: "prompt",
  promptComponents: {},
  provider: "fixture",
  publicSettings: {},
  providerTaskId: null,
  outputUri: null,
  error: null,
  createdAt: "2026-08-30T00:00:00Z",
  updatedAt: "2026-08-30T00:00:00Z",
  startedAt: null,
  finishedAt: null,
  ...overrides,
});

const stages = (payload: unknown = null): StageEnvelope[] => (["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((stage) => ({
  head: {
    stage,
    revision: 0,
    status: "missing",
    entityRevisionId: null,
    contentHash: null,
    schemaVersion: 2,
    inputRevisions: {},
    staleReasons: [],
    updatedAt: "2026-08-30T00:00:00Z",
  },
  payload,
}));

const projectResource = (id = "project-real"): ProjectResource => ({
  id,
  revision: 3,
  brief: { ...demoProject.brief, title: "真实项目" },
  createdAt: "2026-08-30T00:00:00Z",
  updatedAt: "2026-08-30T00:00:00Z",
  lifecycleRevision: 1,
  lifecycleStatus: "active",
  archivedAt: null,
});

describe("workspace hydration contracts", () => {
  it("treats payload:null as empty canonical content even for the same project id", () => {
    const current = { ...demoProject, id: "project-real" };
    const hydrated = hydrateWorkspaceProject(current, projectResource(), stages());

    expect(hydrated.storyBible).toEqual(emptyStageContent.storyBible);
    expect(hydrated.storyGraph).toEqual(emptyStageContent.storyGraph);
    expect(hydrated.sceneBeats).toEqual(emptyStageContent.sceneBeats);
    expect(hydrated.storyboard).toEqual(emptyStageContent.storyboard);
  });

  it("changes editor identity only for owner or relevant canonical revision changes", () => {
    const project = { ...demoProject, id: "p1" };
    expect(editorRevisionKey(project, "story_bible")).toBe("p1:story_bible:r1");
    expect(editorRevisionKey({ ...project, updatedAt: "later" }, "story_bible")).toBe("p1:story_bible:r1");
    expect(editorRevisionKey({ ...project, stageRevisions: { ...project.stageRevisions, story_bible: 2 } }, "story_bible")).toBe("p1:story_bible:r2");
  });

  it("keeps only the newest media task for each shot and kind", () => {
    const tasks: MediaTask[] = [
      mediaTask({ id: "new", status: "succeeded", outputUri: "new.png" }),
      mediaTask({ id: "old", status: "succeeded", outputUri: "old.png" }),
      mediaTask({ id: "video", kind: "video", status: "running", startedAt: "2026-08-30T00:00:01Z" }),
    ];
    expect(newestMediaTasksByShot(tasks)).toEqual({
      "shot-1:image": tasks[0],
      "shot-1:video": tasks[2],
    });
  });

  it("uses server-issued repair eligibility and never infers it from stale, sealed, or unknown work units", () => {
    const progress: RunProgress = {
      runId: "run-1",
      status: "quarantined",
      failureCode: "run.quarantined",
      failedStage: "story_graph",
      stageProgress: [],
      actions: { canResume: false, canCancel: false, canRebuildStage: true, repairEligible: true },
      workUnits: [
        {
          workUnitId: "unknown", stage: "story_graph", sequence: 1, status: "outcome_unknown", maxAttempts: 3,
          latestAttempt: { attemptId: "a-unknown", attemptNumber: 1, attemptKind: "primary", sourceAttemptId: null, status: "failed", outcomeCode: "network.outcome_unknown", outcomeUnknown: true, startedAt: "2026-08-30T00:00:00Z", finishedAt: "2026-08-30T00:00:01Z", inputTokens: null, outputTokens: null, durationMs: 1000 },
          sealed: false, repairEligible: false, repairReasonCode: "repair.target_outcome_unknown",
        },
        {
          workUnitId: "sealed", stage: "story_graph", sequence: 2, status: "quarantined", maxAttempts: 3,
          latestAttempt: { attemptId: "a-sealed", attemptNumber: 3, attemptKind: "correction", sourceAttemptId: "a-2", status: "failed", outcomeCode: "schema.invalid", outcomeUnknown: false, startedAt: "2026-08-30T00:00:00Z", finishedAt: "2026-08-30T00:00:01Z", inputTokens: 10, outputTokens: 20, durationMs: 1000 },
          sealed: true, repairEligible: false, repairReasonCode: "repair.target_sealed",
        },
        {
          workUnitId: "stale", stage: "story_graph", sequence: 3, status: "quarantined", maxAttempts: 3,
          latestAttempt: { attemptId: "a-stale", attemptNumber: 3, attemptKind: "correction", sourceAttemptId: "a-2", status: "failed", outcomeCode: "schema.invalid", outcomeUnknown: false, startedAt: "2026-08-30T00:00:00Z", finishedAt: "2026-08-30T00:00:01Z", inputTokens: 10, outputTokens: 20, durationMs: 1000 },
          sealed: false, repairEligible: false, repairReasonCode: "repair.snapshot_stale",
        },
      ],
    };

    const items = quarantineItemsFromProgress(progress);

    expect(items).toHaveLength(3);
    expect(items.every((item) => item.repairEligible === false)).toBe(true);
    expect(items.map((item) => item.repairReasonCode)).toEqual([
      "repair.target_outcome_unknown", "repair.target_sealed", "repair.snapshot_stale",
    ]);
    expect(JSON.stringify(items)).not.toContain("rawResponse");
    expect(items[0].message).toContain("请求的结果不确定");
    expect(items[0].message).not.toContain("是否到达");
  });
});
