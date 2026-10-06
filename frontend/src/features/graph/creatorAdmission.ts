import type { SourceOutlineReviewState } from "../../types";
import { graphStructuresEqual, mapsEqual } from "../../pages/sourceStructureModel";
import type { GraphAuthoringDraft } from "./contracts";

export function creatorAdmission(draft: GraphAuthoringDraft, source: SourceOutlineReviewState | null, canonicalRevision: number, hasInstallation: boolean | undefined) {
  const accepted = source?.acceptedSectionMap, admission = source?.graphAdmission;
  const mappingConfirmed = Boolean(accepted && source?.sectionMapStatus === "current" && mapsEqual(draft.mapping, accepted.mapping) && Object.keys(draft.fieldBuffers).length === 0);
  const graphCurrent = Boolean(mappingConfirmed && admission?.status === "current" && admission.graphRevision === canonicalRevision
    && admission.sectionMapRevision === accepted!.revision && admission.sectionMapContentHash === accepted!.contentHash);
  const structureBlocked = Boolean(hasInstallation && accepted && !graphStructuresEqual(draft.mapping, accepted.mapping));
  const installBlocked = !mappingConfirmed || graphCurrent || hasInstallation !== false;
  const reason = hasInstallation ? "此项目已有投产内容，当前流程不能重新安装剧情图或替换结构；草稿、已安装镜头与媒体保留。"
    : hasInstallation === undefined ? "投产状态尚未核对，暂不能应用路线。"
    : graphCurrent ? "当前图内容已应用到故事路线。"
    : !mappingConfirmed ? "先确认当前图内容，再应用到故事路线。" : "图内容已确认，等待显式应用到故事路线。";
  return { graphCurrent, structureBlocked, installBlocked, reason };
}
