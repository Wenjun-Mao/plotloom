import type { AcceptedScriptRevision } from "../../types";
import type { AcceptedReviewState } from "../../accepted-review-state";
import { ScriptContentReview } from "./ScriptContentReview";

export function ScriptEpisodeView({ accepted, acceptedState, sectionId }: { accepted: AcceptedScriptRevision; acceptedState: AcceptedReviewState["status"]; sectionId: string }) {
  const stateLabel = acceptedState === "current" ? "当前已确认剧本" : acceptedState === "reopened" ? "已确认剧本的编辑中保存版本" : "保留的已确认剧本";
  return <ScriptContentReview
    title={`${stateLabel} r${accepted.revision} · 节点 ${sectionId}`}
    statusDescription={acceptedState === "retained" ? "此版本是保留的历史证据；它不会因此恢复当前审核资格。" : undefined}
    script={accepted.script}
    binding={accepted.binding}
    sectionId={sectionId}
  />;
}
