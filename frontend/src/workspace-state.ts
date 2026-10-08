import { emptyStageContent } from "./demo";
import { mergeProjectResponse, serverStages } from "./model";
import type {
  MediaTask,
  ProjectResource,
  QuarantineItem,
  RunProgress,
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
    // Creation provenance belongs only to an unsaved local workspace. A
    // server aggregate is canonical and must not carry a second bootstrap
    // instruction into later edits or duplicate/copy flows.
    { ...current, initialStageOnFirstSave: undefined, ...emptyStageContent },
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

/**
 * Turns the intentionally small server progress projection into a workbench
 * list. Eligibility is copied verbatim from the server: the browser never
 * infers it from trace evidence, output text, or a stale local snapshot.
 */
export function quarantineItemsFromProgress(progress: RunProgress | undefined): QuarantineItem[] {
  if (!progress) return [];
  return progress.workUnits
    .filter((unit): unit is typeof unit & { status: "quarantined" | "outcome_unknown" } => (
      unit.status === "quarantined" || unit.status === "outcome_unknown"
    ))
    .sort((left, right) => left.stage.localeCompare(right.stage) || left.sequence - right.sequence)
    .map((unit) => {
      const code = unit.repairReasonCode
        || unit.latestAttempt?.outcomeCode
        || (unit.status === "outcome_unknown" ? "outcome_unknown" : progress.failureCode || "work_unit.quarantined");
      return {
        id: unit.workUnitId,
        stage: unit.stage,
        status: unit.status,
        code,
        message: unit.status === "outcome_unknown"
          ? "本次模型请求的结果不确定；为避免重复生成，不能自动重试或单独重做。"
          : "这个子任务的输出已隔离；尚未保存为正式内容。",
        attempt: unit.latestAttempt,
        maxAttempts: unit.maxAttempts,
        sealed: unit.sealed,
        repairEligible: unit.repairEligible,
        repairReasonCode: unit.repairReasonCode,
      };
    });
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
