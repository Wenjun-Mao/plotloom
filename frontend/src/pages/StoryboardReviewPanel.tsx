import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import type { StoryboardReviewCandidate, StoryboardReviewState } from "../types";

/** F5A preserves upstream review evidence; it deliberately cannot create product shots. */
export function StoryboardReviewPanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [state, setState] = useState<StoryboardReviewState>();
  const [assignment, setAssignment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const active = useRef({ projectId, epoch: 0 });
  if (active.current.projectId !== projectId) active.current = { projectId, epoch: active.current.epoch + 1 };
  const owns = (session: { projectId: string; epoch: number }) => active.current === session;
  const load = useCallback(async (session = active.current) => {
    try {
      const next = await plotloomApi.getStoryboardSourceReview(session.projectId);
      if (owns(session)) setState(next);
    } catch (reason) {
      if (owns(session)) setError(reason instanceof Error ? reason.message : "Unable to load storyboard review.");
    }
  }, [projectId]);
  useEffect(() => {
    const session = active.current;
    setState(undefined); setAssignment(""); setError(""); setBusy(false);
    void load(session);
    return () => { if (owns(session)) active.current = { projectId: session.projectId, epoch: session.epoch + 1 }; };
  }, [projectId, load]);
  const run = <T,>(operation: () => Promise<T>, accepted?: (result: T) => void) => {
    const session = active.current;
    setBusy(true); setError("");
    void operation().then(async result => {
      if (!owns(session)) return;
      accepted?.(result);
      await load(session);
    }).catch(reason => {
      if (owns(session)) setError(reason instanceof Error ? reason.message : "Storyboard review operation failed.");
    }).finally(() => { if (owns(session)) setBusy(false); });
  };
  if (!state) return null;
  const { candidate, acceptedReview } = state;
  const reportJobId = candidate?.status === "ready" ? candidate.jobId : acceptedReview?.candidateJobId;
  return <article className="panel cast-panel" data-testid="storyboard-review">
    <header><span>08 · F5A novel-storyboard review</span><strong>{state.status === "stale" ? "上下文已过期" : acceptedReview ? `已接受 review r${acceptedReview.revision}` : candidate?.status === "ready" ? "可审核" : candidate?.status === "prepared" ? "等待 specialist" : "尚无 review"}</strong></header>
    <p>原始 storyboard.json 和上游报告是与 F4 script 绑定的评审证据，不是 Plotloom 的 shots、播放内容、媒体提示词或投产许可。</p>
    <div className="notice warning">不会创建 SceneBeats/Bible 投影、选择参考、H3 调度或时长变更。</div>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && <Button variant="primary" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.prepareStoryboardSourceReviewCandidate(projectId), result => setAssignment(result.assignment))}>准备并复制 storyboard specialist handoff</Button>}
    {candidate && <CandidateActions candidate={candidate} projectId={projectId} readOnly={readOnly} busy={busy} run={run} onAssignment={setAssignment} />}
    {candidate?.status === "ready" && <StoryboardInspection title="查看待接受 storyboard" value={candidate.storyboard} />}
    {acceptedReview && <section><small>已接受 review r{acceptedReview.revision} · F4 script r{acceptedReview.binding.scriptRevision} · hash {acceptedReview.contentHash.slice(0, 12)}</small><StoryboardInspection title="查看当前已接受 storyboard" value={acceptedReview.storyboard} /></section>}
    {reportJobId && <details><summary>打开原始只读上游报告</summary><iframe title="original derived upstream storyboard report" className="source-outline-report" sandbox="" src={plotloomApi.storyboardSourceReviewCandidateReportUrl(projectId, reportJobId)} /></details>}
    {assignment && <label>复制给 specialist 的冻结任务<textarea readOnly value={assignment} rows={5} /></label>}
    {error && <ErrorNotice message={error} />}
  </article>;
}

function CandidateActions({ candidate, projectId, readOnly, busy, run, onAssignment }: { candidate: StoryboardReviewCandidate; projectId: string; readOnly: boolean; busy: boolean; run: <T>(operation: () => Promise<T>, accepted?: (result: T) => void) => void; onAssignment: (value: string) => void }) {
  if (candidate.status === "prepared") return <div className="button-row"><Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.recoverStoryboardSourceReviewHandoff(projectId, candidate.jobId), result => { onAssignment(result.assignment); navigator.clipboard?.writeText(result.assignment).catch(() => undefined); })}>重新复制冻结 handoff</Button><Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.refreshStoryboardSourceReviewCandidate(projectId, candidate.jobId))}>刷新 specialist delivery</Button><Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelStoryboardSourceReviewCandidate(projectId, candidate.jobId))}>取消 handoff</Button></div>;
  if (candidate.status === "ready") return <div className="button-row"><Button variant="primary" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.acceptStoryboardSourceReviewCandidate(projectId, { jobId: candidate.jobId, expectedReviewRevision: candidate.expectedReviewRevision, binding: candidate.binding }))}>显式接受 review revision</Button><Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelStoryboardSourceReviewCandidate(projectId, candidate.jobId))}>拒绝并取消此 review</Button></div>;
  return null;
}

function StoryboardInspection({ title, value }: { title: string; value: Record<string, unknown> | null }) {
  const episodes = Array.isArray(value?.episodes) ? value.episodes.filter((item): item is Record<string, unknown> => !!item && typeof item === "object") : [];
  return <details><summary>{title}</summary><section className="source-outline-json">
    {episodes.map(episode => <section key={String(episode.ep)}><strong>Episode {String(episode.ep)}</strong>
      {Array.isArray(episode.segments) && episode.segments.map((segment: unknown, index) => {
        const row = segment && typeof segment === "object" ? segment as Record<string, unknown> : {};
        const cuts = Array.isArray(row.cuts) ? row.cuts : [];
        return <div key={String(row.id ?? index)}><p>{String(row.id ?? `segment ${index + 1}`)} · {cuts.map(cut => typeof cut === "object" && cut ? String((cut as Record<string, unknown>).seconds ?? "?") : "?").join(" + ")}s</p>
          <ul>{cuts.map((cut, cutIndex) => { const item = cut && typeof cut === "object" ? cut as Record<string, unknown> : {}; return <li key={cutIndex}>{String(item.seconds ?? "?")}s · {String(item.visual ?? item.description ?? item.camera ?? "visual direction unavailable")} {typeof item.dialogue === "string" ? `· ${item.dialogue}` : ""}</li>; })}</ul>
        </div>;
      })}
    </section>)}
    <details><summary>查看原始 JSON</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>
  </section></details>;
}
