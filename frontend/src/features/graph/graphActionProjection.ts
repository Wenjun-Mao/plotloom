import type { ProjectBrief } from "../../types";
import type { WorkspaceSourceReviewRead } from "../../app/workspace/useWorkspaceSourceReview";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { useWorkspaceProduction } from "./WorkspaceProductionContext";
import { creatorAdmission } from "./creatorAdmission";
import { creatorStructure } from "./creatorStructure";
import type { GraphWorkbenchController } from "./GraphWorkbenchContext";
import type { ProductionRead } from "./useCreatorProduction";
import { acceptedOutlineIsCurrent } from "../../app/workspace/sourceReviewCurrentness";

/** The same read-derived availability in both views; command owners still guard writes. */
export function useGraphActionProjection(brief: ProjectBrief, readOnly: boolean, source: Pick<WorkspaceSourceReviewRead, "status" | "value">) {
  const owner = useGraphWorkbench(), production = useWorkspaceProduction();
  return graphActionProjection(owner, brief, readOnly, source, production.data);
}

export function graphActionProjection(owner: GraphWorkbenchController, brief: ProjectBrief, readOnly: boolean, source: Pick<WorkspaceSourceReviewRead, "status" | "value">, production: ProductionRead | undefined) {
  const structure = owner.draft ? creatorStructure(owner.draft, brief) : null;
  const admission = owner.draft ? creatorAdmission(owner.draft, source.value, owner.state?.baseCanonicalRevision ?? -1, production?.bridge) : null;
  const disabled = readOnly || owner.readStatus !== "ready" || owner.busy || owner.stale || Boolean(owner.state?.readOnlyReason) || !owner.draft;
  const retainedPrerequisites = Boolean(source.value?.source && source.value.acceptedOutline);
  const prerequisites = source.status === "ready" && acceptedOutlineIsCurrent(source.value);
  const structuralBlock = !structure || structure.incomplete || structure.mismatches.length > 0;
  const status = owner.readStatus !== "ready" ? "当前图尚未核实，请先重新读取剧情图。"
    : owner.state?.readOnlyReason || (readOnly ? "当前项目只读。" : "")
    || (owner.stale ? "图草稿版本已过期，请先在当前版本恢复。" : "")
    || (source.status !== "ready" ? "来源与大纲尚未核实，请先重新读取。" : "")
    || (!retainedPrerequisites ? "先保存来源并确认大纲，再确认图内容。" : "")
    || (!prerequisites ? source.value?.source?.revision !== source.value?.acceptedOutline?.sourceRevision ? "来源已变化，请先确认当前来源的大纲。" : "大纲修订已打开，请先确认当前大纲。" : "")
    || (structure?.incomplete ? "当前图尚未完成，可保存草稿；请先完成正文与连接。" : "")
    || (structure?.mismatches.length ? "当前图与简报目标不同，请检查结构或明确调整简报目标。" : "")
    || admission?.reason || "当前图草稿尚未建立。";
  return { structure, admission, disabled, status,
    confirmDisabled: disabled || !prerequisites || structuralBlock || !production?.bridge,
    applyDisabled: disabled || !prerequisites || structuralBlock || admission?.installBlocked !== false };
}
