import { serverStages } from "./model";
import type {
  InitialProjectStage,
  ProjectBrief,
  ProjectCreationRequest,
  ServerStageName,
  WorkspaceProject,
} from "./types";

const workspaceFieldForStage = {
  story_bible: "storyBible",
  story_graph: "storyGraph",
  scene_beats: "sceneBeats",
  storyboard: "storyboard",
} as const;

/**
 * Applies an editor's local draft to the workspace snapshot used for a save.
 * It deliberately does not mutate React state: a failed first save must leave
 * the editor's draft retryable and the project unsaved.
 */
export function workspaceWithStageDraft<T>(
  project: WorkspaceProject,
  stage: ServerStageName,
  payload: T,
): WorkspaceProject {
  return {
    ...project,
    [workspaceFieldForStage[stage]]: payload,
  } as WorkspaceProject;
}

/**
 * Builds the only prefix the server accepts when a stage is saved before the
 * project exists. Upstream payloads come from the current workspace snapshot;
 * callers put the active editor draft into that snapshot first.
 */
export function initialStagesThrough(
  project: WorkspaceProject,
  finalStage: ServerStageName,
): InitialProjectStage[] {
  const finalIndex = serverStages.indexOf(finalStage);
  if (finalIndex < 0) throw new Error(`Unknown canonical stage: ${finalStage}`);

  return serverStages.slice(0, finalIndex + 1).map((stage) => ({
    stage,
    payload: project[workspaceFieldForStage[stage]],
  }));
}

/** Keep a brief-only create compatible with callers that have not edited a stage. */
export function projectCreationRequest(
  brief: ProjectBrief,
  initialStages: InitialProjectStage[] = [],
): ProjectCreationRequest {
  return initialStages.length ? { brief, initialStages } : { brief };
}

/**
 * This exact serialization is both the HTTP body and the idempotency identity.
 * Identical canonical request bodies therefore retain their key after a
 * transport failure, while a changed draft receives a fresh key.
 */
export function projectCreationBody(request: ProjectCreationRequest): string {
  return JSON.stringify(request);
}
