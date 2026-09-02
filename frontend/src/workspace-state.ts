import { emptyStageContent } from "./demo";
import { mergeProjectResponse, serverStages } from "./model";
import type {
  MediaTask,
  ProjectResource,
  QuarantineItem,
  RunTrace,
  SceneBeatPlan,
  ServerStageName,
  StageEnvelope,
  StoryBible,
  StoryGraph,
  Storyboard,
  WorkspaceProject,
} from "./types";

type EditableProjectScope = "brief" | ServerStageName;

/**
 * Editor drafts are intentionally reset only when their canonical owner or
 * revision changes. Unrelated App rerenders keep the same key and therefore
 * preserve unsaved browser edits.
 */
export function editorRevisionKey(project: WorkspaceProject, scope: EditableProjectScope): string {
  const owner = project.id || "unsaved";
  const revision = scope === "brief" ? project.revision : project.stageRevisions[scope];
  return `${owner}:${scope}:r${revision}`;
}

function payloadFor<T>(stages: StageEnvelope[], stage: ServerStageName, empty: T): T {
  const envelope = stages.find((candidate) => candidate.head.stage === stage);
  // A missing-stage envelope uses payload:null by contract. Treat both a
  // missing envelope and an explicit null as empty canonical content; neither
  // is permission to retain a demo or previously loaded project's payload.
  return envelope?.payload == null ? empty : envelope.payload as T;
}

export function hydrateWorkspaceProject(
  current: WorkspaceProject,
  incoming: ProjectResource,
  stages: StageEnvelope[],
): WorkspaceProject {
  const stageRevisions = Object.fromEntries(serverStages.map((stage) => [
    stage,
    stages.find((envelope) => envelope.head.stage === stage)?.head.revision || 0,
  ])) as WorkspaceProject["stageRevisions"];
  const staleStages = stages
    .filter((envelope) => envelope.head.status === "stale")
    .map((envelope) => envelope.head.stage);

  return mergeProjectResponse(
    { ...current, ...emptyStageContent },
    {
      ...incoming,
      stageRevisions,
      staleStages,
      storyBible: payloadFor<StoryBible>(stages, "story_bible", emptyStageContent.storyBible),
      storyGraph: payloadFor<StoryGraph>(stages, "story_graph", emptyStageContent.storyGraph),
      sceneBeats: payloadFor<SceneBeatPlan>(stages, "scene_beats", emptyStageContent.sceneBeats),
      storyboard: payloadFor<Storyboard>(stages, "storyboard", emptyStageContent.storyboard),
      quarantines: current.id === incoming.id ? current.quarantines : [],
    },
  );
}

export function quarantineItemsFromTrace(trace: RunTrace): QuarantineItem[] {
  if (trace.run.status !== "quarantined") return [];
  const failed = [...trace.attempts].reverse().find((attempt) => attempt.status === "failed");
  if (!failed) return [];
  const response = [...trace.artifacts]
    .reverse()
    .find((artifact) => artifact.attemptId === failed.id && artifact.kind === "response");
  const validation = [...trace.artifacts]
    .reverse()
    .find((artifact) => artifact.attemptId === failed.id && artifact.kind === "validation");
  const validationContent = validation?.content && typeof validation.content === "object"
    ? validation.content as Record<string, unknown>
    : {};
  const issues = Array.isArray(validationContent.issues) ? validationContent.issues : [];
  const firstIssue = issues.find((issue) => issue && typeof issue === "object") as Record<string, unknown> | undefined;
  const responseContent = response?.content && typeof response.content === "object"
    ? response.content as Record<string, unknown>
    : undefined;
  const rawResponse = typeof responseContent?.rawResponse === "string"
    ? responseContent.rawResponse
    : response
      ? JSON.stringify(response.content, null, 2)
      : "没有可展示的原始响应。";
  return [{
    id: failed.id,
    stage: failed.stage,
    code: typeof firstIssue?.code === "string" ? firstIssue.code : "QUARANTINED_OUTPUT",
    message: failed.error || (typeof firstIssue?.message === "string" ? firstIssue.message : "生成输出未通过阶段合同。"),
    rawOutput: rawResponse,
    repairHint: "检查验证证据，并为修复运行提供最小、明确的纠正指令。",
  }];
}

export function newestMediaTasksByShot(tasks: MediaTask[]): Record<string, MediaTask> {
  const indexed: Record<string, MediaTask> = {};
  // The project endpoint returns newest first. Keeping the first task for each
  // shot/kind makes refresh deterministic without resurrecting an older output.
  tasks.forEach((task) => {
    const key = `${task.shotId}:${task.kind}`;
    if (!indexed[key]) indexed[key] = task;
  });
  return indexed;
}
