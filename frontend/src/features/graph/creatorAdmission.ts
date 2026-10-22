import type { ProductionBridgeState, SourceOutlineReviewState } from "../../types";
import { mapsEqual } from "../../pages/sourceStructureModel";
import type { GraphAuthoringDraft } from "./contracts";

export function creatorAdmission(draft: GraphAuthoringDraft, source: SourceOutlineReviewState | null, canonicalRevision: number, production: ProductionBridgeState | undefined) {
  const accepted = source?.acceptedSectionMap, admission = source?.graphAdmission;
  const mappingConfirmed = Boolean(accepted && source?.sectionMapStatus === "current" && mapsEqual(draft.mapping, accepted.mapping) && Object.keys(draft.fieldBuffers).length === 0);
  const graphCurrent = Boolean(mappingConfirmed && admission?.status === "current" && admission.graphRevision === canonicalRevision
    && admission.sectionMapRevision === accepted!.revision && admission.sectionMapContentHash === accepted!.contentHash);
  const installBlocked = !mappingConfirmed || graphCurrent || production === undefined;
  const reason = production === undefined ? "投产状态尚未核对，暂不能应用路线。"
    : graphCurrent ? "当前图内容已应用到故事路线。"
    : !mappingConfirmed ? "先确认当前图内容，再应用到故事路线。" : "图内容已确认，等待显式应用到故事路线。";
  return { graphCurrent, installBlocked, reason };
}
