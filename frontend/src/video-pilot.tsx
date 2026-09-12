import { useEffect, useRef, useState } from "react";
import type { Shot, VideoJob, VideoPilotBudget } from "./types";
import { plotloomApi } from "./api";
import { Button, Panel } from "./components";

function frozenShot(job: VideoJob): { id?: string; title?: string } {
  const candidate = job.snapshot.shot;
  return candidate && typeof candidate === "object" ? candidate as { id?: string; title?: string } : {};
}

function jobStatus(job: VideoJob): string {
  if (job.cancelRequestedAt) return "取消意图已记录：保留已知远端任务，但不会采用输出";
  if (!job.current) return "冻结输入已失效";
  if (job.selected) return "当前镜头的已显式选择";
  return "当前";
}

export function VideoPilotPanel({ projectId, shot, approvalId, storyboardRevision, selectionRevision, readOnly }: { projectId?: string; shot?: Shot; approvalId?: string; storyboardRevision?: number; selectionRevision: number; readOnly: boolean }) {
  const [budget, setBudget] = useState<VideoPilotBudget | null>(null);
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [error, setError] = useState("");
  const refreshToken = useRef(0);
  const currentProjectRef = useRef(projectId);
  currentProjectRef.current = projectId;
  const refresh = async () => {
    if (!projectId) return;
    const requestedProjectId = projectId;
    if (requestedProjectId !== currentProjectRef.current) return;
    const token = ++refreshToken.current;
    const [nextBudget, nextJobs] = await Promise.all([plotloomApi.getVideoPilotBudget(), plotloomApi.getVideoJobs(requestedProjectId)]);
    // A slow response from a formerly selected project cannot replace the
    // currently visible project's recovery controls or budget.
    if (token !== refreshToken.current || requestedProjectId !== currentProjectRef.current) return;
    setBudget(nextBudget); setJobs(nextJobs.jobs);
  };
  useEffect(() => {
    setBudget(null); setJobs([]); setError("");
    void refresh().catch((reason) => setError(reason instanceof Error ? reason.message : "无法读取视频试点状态"));
    return () => { refreshToken.current += 1; };
  }, [projectId]);
  const prepare = async () => {
    if (!projectId || !shot || !approvalId || !storyboardRevision) return;
    setError("");
    try { await plotloomApi.prepareVideoJob(projectId, { approvalId, shotId: shot.id, storyboardRevision, expectedSelectionRevision: selectionRevision, idempotencyKey: crypto.randomUUID() }); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "无法冻结视频请求"); }
  };
  const act = async (operation: () => Promise<unknown>, fallback: string) => {
    const actionProjectId = projectId;
    setError("");
    try {
      await operation();
      if (actionProjectId !== currentProjectRef.current) return;
      await refresh();
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : fallback); }
  };
  const visibleJobs = shot ? jobs.filter((job) => frozenShot(job).id === shot.id) : [];
  return <Panel data-testid="video-pilot-panel"><strong>P2 Wan 视频试点</strong><p>仅 5 秒 / 720p / 原生音频。提交后本地保守计入共享 100 秒额度；不会自动重试或回退。</p>
    <small>额度：{budget ? `${budget.reservedSeconds}/${budget.limitSeconds} 秒已保留，余 ${budget.remainingSeconds} 秒` : "读取中"}</small>
    <div className="button-row"><Button disabled={readOnly || !projectId || !shot || !approvalId || !storyboardRevision} onClick={() => void prepare()}>冻结当前审核关键帧</Button></div>
    {shot && <small>仅显示当前镜头：{shot.title}（{shot.id}）</small>}
    {error && <small className="notice warning">{error}</small>}
    {visibleJobs.map((job) => <article key={job.id} data-testid={`video-job-${job.id}`}><strong>{frozenShot(job).title || frozenShot(job).id}</strong> · <strong>{job.state}</strong> · {job.requestedSeconds}s {job.observed ? `· ${job.observed.durationSeconds.toFixed(2)}s 实测` : ""}
      <small> · {jobStatus(job)}</small>
      {job.state === "ingested" && projectId && <video controls preload="metadata" src={plotloomApi.videoJobMediaUrl(projectId, job.id)} data-testid={`video-job-player-${job.id}`} />}
      <div className="button-row">
        {job.state === "prepared" && <Button disabled={readOnly} onClick={() => void act(() => plotloomApi.submitVideoJob(projectId!, job.id), "提交未完成")}>提交一次</Button>}
        {(job.state === "submitted" || job.state === "retrieve_needed") && <Button disabled={readOnly} onClick={() => void act(() => plotloomApi.reconcileVideoJob(projectId!, job.id), "获取结果未完成")}>获取结果</Button>}
        {["prepared", "dispatching", "submitted", "retrieve_needed", "outcome_unknown"].includes(job.state) && !job.cancelRequestedAt && <Button variant="danger" disabled={readOnly} onClick={() => void act(() => plotloomApi.cancelVideoJob(projectId!, job.id), "取消意图未记录")}>记录取消意图</Button>}
        {job.state === "ingested" && <Button disabled={readOnly || !job.current} onClick={() => void act(() => plotloomApi.reviewVideoJob(projectId!, job.id, "select", "local reviewer", "Explicit candidate selection after audiovisual review."), "选择未完成")}>显式选择</Button>}
      </div>
      {job.error && <small>{job.error}</small>}</article>)}
    {shot && visibleJobs.length === 0 && <small>当前镜头尚无冻结的视频请求。</small>}
  </Panel>;
}
