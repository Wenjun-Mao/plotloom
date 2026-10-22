import type { AcceptedReviewState } from "../accepted-review-state";
import { ReviewContextNotice } from "./ReviewContextNotice";

export function AcceptedEvidenceNotice({ projectId, state }: { projectId: string; state: AcceptedReviewState }) {
  if (state.status !== "retained") return null;
  return <section aria-label="保留的已确认内容">
    <p>这份已确认内容仍保留供查阅，但不能作为当前编辑或继续制作的依据。</p>
    <ReviewContextNotice projectId={projectId} diagnostics={state.staleReasons} />
  </section>;
}
