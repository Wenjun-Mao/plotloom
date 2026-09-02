import { describe, expect, it } from "vitest";
import { demoProject, demoRun, emptyStageContent } from "../src/demo";
import type { MediaTask, ProjectResource, RunTrace, ServerStageName, StageEnvelope } from "../src/types";
import { editorRevisionKey, hydrateWorkspaceProject, newestMediaTasksByShot, quarantineItemsFromTrace } from "../src/workspace-state";

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

  it("reconstructs an actionable quarantine item from durable trace evidence", () => {
    const trace: RunTrace = {
      run: { ...demoRun, id: "run-1", projectId: "p1", status: "quarantined", requestedStages: ["story_bible"] },
      attempts: [
        { id: "attempt-old", runId: "run-1", stage: "story_bible", attemptNumber: 1, status: "failed", provider: null, model: null, error: "old error", startedAt: "2026-08-29T00:00:00Z", finishedAt: "2026-08-29T00:00:01Z" },
        { id: "attempt-1", runId: "run-1", stage: "story_bible", attemptNumber: 2, status: "failed", provider: null, model: null, error: "schema invalid", startedAt: "2026-08-30T00:00:00Z", finishedAt: "2026-08-30T00:00:01Z" },
      ],
      artifacts: [
        { id: "old-response", runId: "run-1", attemptId: "attempt-old", sourceArtifactId: null, stage: "story_bible", kind: "response", mediaType: "application/json", content: { rawResponse: "OLD RAW" }, contentHash: "old", createdAt: "2026-08-29T00:00:01Z" },
        { id: "response-1", runId: "run-1", attemptId: "attempt-1", sourceArtifactId: null, stage: "story_bible", kind: "response", mediaType: "application/json", content: { rawResponse: "CURRENT RAW" }, contentHash: "raw", createdAt: "2026-08-30T00:00:01Z" },
        { id: "artifact-1", runId: "run-1", attemptId: "attempt-1", sourceArtifactId: null, stage: "story_bible", kind: "validation", mediaType: "application/json", content: { accepted: false, issues: [{ code: "missing.logline", message: "missing logline" }] }, contentHash: "abc", createdAt: "2026-08-30T00:00:02Z" },
      ],
      snapshotIsCurrent: true,
    };
    expect(quarantineItemsFromTrace(trace)[0]).toMatchObject({ id: "attempt-1", stage: "story_bible", message: "schema invalid" });
    expect(quarantineItemsFromTrace(trace)[0].code).toBe("missing.logline");
    expect(quarantineItemsFromTrace(trace)[0].rawOutput).toBe("CURRENT RAW");
  });
});
