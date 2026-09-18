import { useCallback, useEffect, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import type { StoryboardReviewCandidate, StoryboardReviewState } from "../types";

/** F5A preserves upstream review evidence; it deliberately cannot create product shots. */
export function StoryboardReviewPanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [state, setState] = useState<StoryboardReviewState>();
  const [assignment, setAssignment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try { setState(await plotloomApi.getStoryboardSourceReview(projectId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load storyboard review."); }
  }, [projectId]);
  useEffect(() => { setState(undefined); setAssignment(""); setError(""); void load(); }, [load]);
  const run = <T,>(operation: () => Promise<T>, accepted?: (result: T) => void) => {
    setBusy(true); setError("");
    void operation().then(result => { accepted?.(result); return load(); }).catch(reason => setError(reason instanceof Error ? reason.message : "Storyboard review operation failed.")).finally(() => setBusy(false));
  };
  if (!state) return null;
  const { candidate, acceptedReview } = state;
  const reportJobId = candidate?.status === "ready" ? candidate.jobId : acceptedReview?.candidateJobId;
  return <article className="panel cast-panel" data-testid="storyboard-review">
    <header><span>08 · F5A novel-storyboard review</span><strong>{state.status === "stale" ? "上下文已过期" : acceptedReview ? `已接受 review r${acceptedReview.revision}` : candidate?.status === "ready" ? "可审核" : candidate?.status === "prepared" ? "等待 specialist" : "尚无 review"}</strong></header>
    <p>原始 storyboard.json 和上游报告是与 F4 script 绑定的评审证据，不是 Plotloom 的 shots、播放内容、媒体提示词或投产许可。</p>
    <div className="notice warning">不会创建 SceneBeats/Bible 投影、选择参考、H3 调度或时长变更。</div>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && <Button variant="primary" disabled={readOnly || busy || state.status === "stale"} onClick={() => run(() => plotloomApi.prepareStoryboardSourceReviewCandidate(projectId), result => setAssignment(result.assignment))}>准备并复制 storyboard specialist handoff</Button>}
    {candidate && <CandidateActions candidate={candidate} projectId={projectId} readOnly={readOnly} busy={busy} run={run} />}
    {candidate?.status === "ready" && <Json title="查看待接受 storyboard.json" value={candidate.storyboard} />}
    {acceptedReview && <section><small>已接受 review r{acceptedReview.revision} · F4 script r{acceptedReview.binding.scriptRevision} · hash {acceptedReview.contentHash.slice(0, 12)}</small><Json title="查看当前已接受原始 storyboard.json" value={acceptedReview.storyboard} /></section>}
    {reportJobId && <details><summary>打开原始只读上游报告</summary><iframe title="original derived upstream storyboard report" className="source-outline-report" sandbox="" src={plotloomApi.storyboardSourceReviewCandidateReportUrl(projectId, reportJobId)} /></details>}
    {assignment && <label>复制给 specialist 的冻结任务<textarea readOnly value={assignment} rows={5} /></label>}
    {error && <ErrorNotice message={error} />}
  </article>;
}

function CandidateActions({ candidate, projectId, readOnly, busy, run }: { candidate: StoryboardReviewCandidate; projectId: string; readOnly: boolean; busy: boolean; run: <T>(operation: () => Promise<T>, accepted?: (result: T) => void) => void }) {
  if (candidate.status === "prepared") return <div className="button-row"><Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.recoverStoryboardSourceReviewHandoff(projectId, candidate.jobId))}>重新复制冻结 handoff</Button><Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.refreshStoryboardSourceReviewCandidate(projectId, candidate.jobId))}>刷新 specialist delivery</Button><Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelStoryboardSourceReviewCandidate(projectId, candidate.jobId))}>取消 handoff</Button></div>;
  if (candidate.status === "ready") return <div className="button-row"><Button variant="primary" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.acceptStoryboardSourceReviewCandidate(projectId, { jobId: candidate.jobId, expectedReviewRevision: candidate.expectedReviewRevision, binding: candidate.binding }))}>显式接受 review revision</Button><Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelStoryboardSourceReviewCandidate(projectId, candidate.jobId))}>拒绝并取消此 review</Button></div>;
  return null;
}

function Json({ title, value }: { title: string; value: Record<string, unknown> | null }) { return <details><summary>{title}</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>; }
