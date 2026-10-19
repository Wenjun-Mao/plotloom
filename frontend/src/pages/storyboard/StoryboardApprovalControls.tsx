import type { ApprovalDecision, StoryboardReview } from "../../types";
import { Button } from "../../components";
import { humanReviewLabel } from "../../human-review-attribution";

export function StoryboardApprovalControls({ review, error, pending, locked, canApprove, onDecide }: {
  review?: StoryboardReview | null; error: string; pending: boolean; locked: boolean;
  canApprove: boolean; onDecide: (decision: ApprovalDecision["decision"]) => void;
}) {
  return <>
    <div className="section-title"><span>覆盖检查与分镜批准</span><strong>{review?.activeApproval ? "已批准" : "等待批准"}</strong></div>
    {error && <div className="notice warning" role="alert">{error}</div>}
    {!review?.gateEvaluation && <div className="notice"><strong>尚无检查结果</strong><span>保存有效分镜后，会生成检查结果。</span></div>}
    {review?.activeApproval && <div className="notice"><strong>当前批准：{humanReviewLabel(review.activeApproval)}</strong><span>版本 {review.activeApproval.subjectRevision} · {review.activeApproval.createdAt}</span></div>}
    {review?.decisions.length ? <details><summary>批准记录 · {review.decisions.length}</summary>{review.decisions.map(closure =>
      <div className="approval-history" key={closure.decision.id}><strong>{closure.decision.decision === "approve" ? "批准" : "撤销批准"} · {humanReviewLabel(closure.decision)}</strong><small>{closure.active ? "当前生效" : closure.staleReasons.join("；")}</small></div>
    )}</details> : null}
    <div className="approval-actions" aria-busy={pending}>
      {review?.activeApproval
        ? <Button variant="quiet" disabled={locked} onClick={() => onDecide("revoke")}>{pending ? "正在撤销…" : "撤销批准"}</Button>
        : <Button variant="primary" disabled={locked || !canApprove} onClick={() => onDecide("approve")}>{pending ? "正在确认…" : "批准当前分镜"}</Button>}
    </div>
  </>;
}
