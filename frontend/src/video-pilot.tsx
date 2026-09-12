import { useEffect, useState } from "react";
import type { Shot, VideoJob, VideoPilotBudget } from "./types";
import { plotloomApi } from "./api";
import { Button, Panel } from "./components";

export function VideoPilotPanel({ projectId, shot, approvalId, storyboardRevision, selectionRevision, readOnly }: { projectId?: string; shot?: Shot; approvalId?: string; storyboardRevision?: number; selectionRevision: number; readOnly: boolean }) {
  const [budget, setBudget] = useState<VideoPilotBudget | null>(null);
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [error, setError] = useState("");
  const refresh = async () => {
    if (!projectId) return;
    const [nextBudget, nextJobs] = await Promise.all([plotloomApi.getVideoPilotBudget(), plotloomApi.getVideoJobs(projectId)]);
    setBudget(nextBudget); setJobs(nextJobs.jobs);
  };
  useEffect(() => { void refresh().catch((reason) => setError(reason instanceof Error ? reason.message : "无法读取视频试点状态")); }, [projectId]);
  const prepare = async () => {
    if (!projectId || !shot || !approvalId || !storyboardRevision) return;
    setError("");
    try { await plotloomApi.prepareVideoJob(projectId, { approvalId, shotId: shot.id, storyboardRevision, expectedSelectionRevision: selectionRevision, idempotencyKey: crypto.randomUUID() }); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "无法冻结视频请求"); }
  };
  return <Panel data-testid="video-pilot-panel"><strong>P2 Wan 视频试点</strong><p>仅 5 秒 / 720p / 原生音频。提交后本地保守计入共享 100 秒额度；不会自动重试或回退。</p>
    <small>额度：{budget ? `${budget.reservedSeconds}/${budget.limitSeconds} 秒已保留，余 ${budget.remainingSeconds} 秒` : "读取中"}</small>
    <div className="button-row"><Button disabled={readOnly || !projectId || !shot || !approvalId || !storyboardRevision} onClick={() => void prepare()}>冻结当前审核关键帧</Button></div>
    {error && <small className="notice warning">{error}</small>}
    {jobs.map((job) => <article key={job.id}><strong>{job.state}</strong> · {job.requestedSeconds}s {job.observed ? `· ${job.observed.durationSeconds.toFixed(2)}s 实测` : ""}
      {job.state === "ingested" && projectId && <video controls preload="metadata" src={plotloomApi.videoJobMediaUrl(projectId, job.id)} data-testid={`video-job-player-${job.id}`} />}
      <div className="button-row">{job.state === "prepared" && <Button disabled={readOnly} onClick={() => void plotloomApi.submitVideoJob(projectId!, job.id).then(refresh).catch((reason) => setError(String(reason)))}>提交一次</Button>}{job.state === "submitted" && <Button disabled={readOnly} onClick={() => void plotloomApi.reconcileVideoJob(projectId!, job.id).then(refresh).catch((reason) => setError(String(reason)))}>获取结果</Button>}{job.state === "ingested" && <Button disabled={readOnly || !job.current} onClick={() => void plotloomApi.reviewVideoJob(projectId!, job.id, "select", "local reviewer", "Explicit candidate selection after audiovisual review.").then(refresh).catch((reason) => setError(String(reason)))}>显式选择</Button>}</div>
      {job.error && <small>{job.error}</small>}</article>)}
  </Panel>;
}
