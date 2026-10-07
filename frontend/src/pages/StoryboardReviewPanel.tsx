import { ProjectReportFrame } from "../components/ProjectReportFrame";
import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { StoryboardReviewCandidate, StoryboardReviewState } from "../types";
import { StoryboardReviewInspection } from "./StoryboardReviewInspection";
import { ProductionBridgePanel } from "./ProductionBridgePanel";
import { ManualTaskAssignment } from "./ManualTaskAssignment";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";
import { useReviewActivation } from "./useReviewActivation";
import { StageGuide } from "../components/StageGuide";

/** F5A preserves upstream review evidence; it deliberately cannot create product shots. */
export function StoryboardReviewPanel({ projectId, readOnly: ownerReadOnly, onOpenShot, onInstalled, active: visible = true, refreshToken }: { projectId: string; readOnly: boolean; onOpenShot?: (shotId: string) => boolean | void; onInstalled: (projectId: string) => Promise<void>; active?: boolean; refreshToken?: unknown }) {
  const [state, setState] = useState<StoryboardReviewState>();
  const [assignment, setAssignment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [maxCutSeconds, setMaxCutSeconds] = useState(8);
  const active = useRef({ projectId, epoch: 0 });
  if (active.current.projectId !== projectId) active.current = { projectId, epoch: active.current.epoch + 1 };
  const owns = (session: { projectId: string; epoch: number }) => active.current === session;
  const load = useCallback(async (isCurrent: () => boolean) => {
    const session = active.current;
    if (owns(session)) setError("");
    try {
      const next = await plotloomApi.getStoryboardSourceReview(session.projectId);
      if (owns(session) && isCurrent()) { setState(next); return true; }
    } catch (reason) {
      if (owns(session) && isCurrent()) setError(reason instanceof Error ? reason.message : "Unable to load storyboard review.");
    }
    return false;
  }, [projectId]);
  useEffect(() => {
    const session = active.current;
    setState(undefined); setAssignment(""); setError(""); setBusy(false); setMaxCutSeconds(8);
    return () => { if (owns(session)) active.current = { projectId: session.projectId, epoch: session.epoch + 1 }; };
  }, [projectId, load]);
  const { checking, failed, recheck } = useReviewActivation({ projectId, active: visible, refreshToken, load });
  const readOnly = ownerReadOnly || checking || failed;
  const run = <T,>(operation: () => Promise<T>, accepted?: (result: T) => void) => {
    const session = active.current;
    setBusy(true); setError("");
    void operation().then(async result => {
      if (!owns(session)) return;
      accepted?.(result);
      await recheck();
    }).catch(reason => {
      if (owns(session)) setError(reason instanceof Error ? reason.message : "Storyboard review operation failed.");
    }).finally(() => { if (owns(session)) setBusy(false); });
  };
  if (!state) return <article id="storyboard-review" className="panel cast-panel" data-testid="storyboard-review">
    <header><span>分镜评审</span><strong>{error ? "无法加载" : "正在加载"}</strong></header>
    {error ? <><ErrorNotice message={error} /><Button variant="quiet" onClick={() => void recheck()}>重试加载分镜评审</Button></> : <Spinner />}
  </article>;
  const { candidate, acceptedReview } = state;
  const reportJobId = candidate?.status === "ready" ? candidate.jobId : acceptedReview?.candidateJobId;
  return <article id="storyboard-review" className="panel cast-panel" data-testid="storyboard-review">
    <header><span>分镜评审</span><strong>{checking ? "正在刷新" : failed ? "无法刷新" : reviewLabel(state)}</strong></header>
    {failed && <Button variant="quiet" onClick={() => void recheck()}>重试加载分镜评审</Button>}
    <StageGuide>{checking ? "正在核对当前分镜评审，请稍候。" : failed ? "读取失败，请先重试；暂时不能修改或投产。" : busy ? "正在处理分镜任务，请稍候。" : state.status === "stale" ? "剧本或其他上游内容已变化，请更新分镜评审后再投产；旧方案仍保留供参考。" : state.status === "accepted" && acceptedReview ? "分镜评审已确认。请在下方审阅投产提案；确认投产后才能进入正式镜头的媒体制作。" : candidate?.status === "ready" ? "审阅候选中每个镜头的动作、对白和预计时长，再确认使用。" : candidate?.status === "prepared" ? "分镜任务尚未交付；发送、等待和检查状态见任务区。" : "先确认剧本，再准备并发送分镜任务。这里不会自动生成图片或视频。"}</StageGuide>
    <p className="action-prerequisite">本页保留与已确认剧本对应的原始分镜方案。分镜评审确认与正式镜头投产是两个独立步骤；确认评审不会自动投产或生成媒体。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && <div className="button-row"><label>评审镜头上限（秒）<select value={maxCutSeconds} disabled={readOnly || busy} onChange={event => setMaxCutSeconds(Number(event.target.value))}>{[8, 10, 12, 15].map(seconds => <option key={seconds} value={seconds}>{seconds}</option>)}</select></label><Button variant="primary" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.prepareStoryboardSourceReviewCandidate(projectId, maxCutSeconds), result => setAssignment(result.assignment))}>准备分镜任务</Button></div>}
    {candidate && <small>冻结评审时长：单镜头 {candidate.binding.reviewMinCutSeconds}–{candidate.binding.reviewMaxCutSeconds} 秒；分段上限 {candidate.binding.reviewMaxSegmentSeconds} 秒。</small>}
    {candidate?.status === "prepared" && <SpecialistTaskActions projectId={projectId} stage="storyboard" jobId={candidate.jobId} disabled={readOnly || busy} sendDisabled={state.status === "stale"} onDelivered={recheck} />}
    {candidate && <CandidateActions candidate={candidate} projectId={projectId} readOnly={readOnly} stale={state.status === "stale"} busy={busy} run={run} />}
    {candidate?.status === "ready" && <StoryboardReviewInspection title="查看待审阅分镜" value={candidate.storyboard} />}
    {acceptedReview && <section><small>已确认评审 r{acceptedReview.revision} · 已确认剧本 r{acceptedReview.binding.scriptRevision} · hash {acceptedReview.contentHash.slice(0, 12)}</small><StoryboardReviewInspection title="查看当前已确认分镜" value={acceptedReview.storyboard} /></section>}
    {reportJobId && <details><summary>打开原始只读上游报告</summary><ProjectReportFrame sandbox="" title="original derived upstream storyboard report" className="source-outline-report" url={plotloomApi.storyboardSourceReviewCandidateReportUrl(projectId, reportJobId)} /></details>}
    {candidate?.status === "prepared" && <details><summary>查看任务说明（手动方式）</summary><Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.recoverStoryboardSourceReviewHandoff(projectId, candidate.jobId), result => setAssignment(result.assignment))}>恢复分镜任务</Button>{assignment && <ManualTaskAssignment key={`${projectId}:${candidate.jobId}:${assignment}`} assignment={assignment} taskName="分镜" />}</details>}
    {error && <ErrorNotice message={error} />}
    {acceptedReview && <ProductionBridgePanel projectId={projectId} readOnly={readOnly || state.status === "stale"} onOpenShot={onOpenShot} onInstalled={onInstalled} />}
  </article>;
}

function CandidateActions({ candidate, projectId, readOnly, stale, busy, run }: { candidate: StoryboardReviewCandidate; projectId: string; readOnly: boolean; stale: boolean; busy: boolean; run: <T>(operation: () => Promise<T>, accepted?: (result: T) => void) => void }) {
  if (candidate.status === "prepared") return <div className="button-row"><Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelStoryboardSourceReviewCandidate(projectId, candidate.jobId))}>取消此任务</Button></div>;
  if (candidate.status === "ready") return <div className="button-row"><Button variant="primary" disabled={readOnly || stale || busy} onClick={() => run(() => plotloomApi.acceptStoryboardSourceReviewCandidate(projectId, { jobId: candidate.jobId, expectedReviewRevision: candidate.expectedReviewRevision, binding: candidate.binding }))}>确认此分镜评审方案</Button><Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelStoryboardSourceReviewCandidate(projectId, candidate.jobId))}>拒绝并取消此评审</Button></div>;
  return null;
}

function reviewLabel(state: StoryboardReviewState): string {
  if (state.status === "stale") return "上下文已过期";
  if (state.candidate?.status === "ready") return "待审阅";
  if (state.candidate?.status === "prepared") return "任务尚未交付";
  if (state.acceptedReview) return `已确认评审 r${state.acceptedReview.revision}`;
  return "尚无评审";
}
