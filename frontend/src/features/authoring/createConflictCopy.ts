import { plotloomApi } from "../../api";
import type { DraftRecord } from "../../draft-registry";
import type { WorkspaceProject } from "../../types";
import { initialStagesThrough } from "../../project-creation";
import { serverStages } from "../../model";
import { saveWorkingDraft } from "./saveWorkingDraft";

/** Explicit copy preserves incomplete input without installing it as canonical. */
export async function createConflictCopy(record: DraftRecord, workspace: WorkspaceProject, idempotencyKey: string) {
  const scope = record.scope;
  if (scope === "story_graph") throw new Error("图草稿使用其来源绑定的显式恢复流程。");
  const index = scope === "brief" ? -1 : serverStages.indexOf(scope);
  const stages = index > 0 ? initialStagesThrough(workspace, serverStages[index - 1]) : [];
  const project = await plotloomApi.createProject({ brief: scope === "brief" ? null : workspace.brief, initialStages: stages }, idempotencyKey);
  const base = scope === "brief" ? project.revision : project.stages.find(stage => stage.head.stage === scope)?.head.revision ?? 0;
  const draft = await saveWorkingDraft(project.id, { editorScope: scope, entityId: "root", baseCanonicalRevision: base, expectedDraftRevision: 0, payload: record.payload as Record<string, unknown> });
  return { project, draft };
}
