import { emptyStageContent } from "./demo";
import { mergeProjectResponse, serverStages } from "./model";
import type {
  MediaTask,
  ProjectResource,
  QuarantineItem,
  RunProgress,
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
  // Legacy runs have no work-unit progress projection. Keep this reader only
  // for historical trace display; M1-R actions must come from server-issued
  // repair eligibility in `quarantineItemsFromProgress` below.
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
          ? "本次请求是否到达模型端未知；为避免重复生成，不能自动或精确重放。"
          : "该 work unit 已隔离；规范内容尚未安装。",
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
