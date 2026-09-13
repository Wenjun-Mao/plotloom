import { useCallback, useEffect, useRef, useState } from "react";
import type { Shot, VideoBackend, VideoJob, VideoPilotBudget } from "./types";
import { plotloomApi } from "./api";
import { Button, Panel } from "./components";

type FrozenShot = { id?: string; title?: string; sceneId?: string; order?: number };

function frozenShot(job: VideoJob): FrozenShot {
  const candidate = job.snapshot.shot;
  return candidate && typeof candidate === "object" ? candidate as FrozenShot : {};
}

/**
 * A selected candidate is the only video that may enter ordered playback.
 * Keeping this projection here means stale, rejected, pending, and merely
 * ingested candidates cannot be made to look like an accepted adjoining cut.
 */
export function selectedSceneVideos(jobs: VideoJob[], sceneId?: string): VideoJob[] {
  if (!sceneId) return [];
  return jobs
    .filter((job) => job.state === "ingested" && job.current && job.selected && frozenShot(job).sceneId === sceneId)
    .sort((left, right) => (frozenShot(left).order ?? Number.MAX_SAFE_INTEGER) - (frozenShot(right).order ?? Number.MAX_SAFE_INTEGER) || left.id.localeCompare(right.id));
}

function jobStatus(job: VideoJob): string {
  if (job.cancelRequestedAt) return "取消意图已记录：保留已知远端任务，但不会采用输出";
  if (!job.current) return "冻结输入已失效";
  if (job.selected) return "当前镜头的已显式选择";
  return "当前";
}

function OrderedVideoPlayback({ projectId, jobs }: { projectId: string; jobs: VideoJob[] }) {
  const player = useRef<HTMLVideoElement>(null);
  const identityFor = (job: VideoJob) => `${projectId}:${job.id}`;
  // A position is meaningful only inside one exact selected sequence. Keeping
  // the active source as an identity (rather than a numeric position) stops a
  // changed project, scene, or selection membership from borrowing playback.
  const scopeIdentity = `${projectId}:${jobs.map((job) => job.id).join("|")}`;
  const renderedScopeRef = useRef(scopeIdentity);
  const scopeChanged = renderedScopeRef.current !== scopeIdentity;
  renderedScopeRef.current = scopeIdentity;
  const [activeIdentity, setActiveIdentity] = useState(() => jobs[0] ? identityFor(jobs[0]) : "");
  const [autoplayIdentity, setAutoplayIdentity] = useState<string | null>(null);
  const [playbackError, setPlaybackError] = useState("");
  const current = jobs.find((job) => identityFor(job) === activeIdentity) ?? jobs[0];
  const currentIdentity = current ? identityFor(current) : "";
  const currentIdentityRef = useRef(currentIdentity);
  currentIdentityRef.current = currentIdentity;
  const index = current ? jobs.findIndex((job) => job.id === current.id) : 0;

  useEffect(() => {
    // Scope changes are an explicit stop/reset boundary. In particular, they
    // must never turn a stale ended event into autoplay for a new selection.
    setActiveIdentity(jobs[0] ? identityFor(jobs[0]) : "");
    setAutoplayIdentity(null);
    setPlaybackError("");
  }, [scopeIdentity]);

  const attemptPlayback = useCallback((video: HTMLVideoElement, identity: string, automatic: boolean) => {
    setPlaybackError("");
    void video.play().catch((reason: unknown) => {
      // A late rejection from an unmounted or superseded source is historical,
      // not an error in the current reviewed candidate.
      if (player.current !== video || currentIdentityRef.current !== identity) return;
      const detail = reason instanceof Error && reason.message ? `：${reason.message}` : "";
      setPlaybackError(`${automatic ? "无法自动播放下一镜头" : "无法播放当前镜头"}${detail}`);
    });
  }, []);

  useEffect(() => {
    if (scopeChanged || !autoplayIdentity || autoplayIdentity !== currentIdentity || !player.current) return;
    const video = player.current;
    setAutoplayIdentity(null);
    attemptPlayback(video, currentIdentity, true);
  }, [attemptPlayback, autoplayIdentity, currentIdentity, scopeChanged]);

  if (!current) return null;
  const play = (restart: boolean) => {
    if (!player.current) return;
    if (restart) player.current.currentTime = 0;
    attemptPlayback(player.current, currentIdentity, false);
  };
  const advance = (endedIdentity: string | undefined) => {
    if (endedIdentity !== currentIdentity) return;
    if (index + 1 >= jobs.length) {
      // Do not reset: native video retains its final decoded frame until the
      // reviewer explicitly restarts or seeks, preserving cut-end inspection.
      return;
    }
    const nextIdentity = identityFor(jobs[index + 1]);
    setAutoplayIdentity(nextIdentity);
    setActiveIdentity(nextIdentity);
    setPlaybackError("");
  };
  const shot = frozenShot(current);
  return <section className="video-sequence" data-testid="video-sequence-player">
    <strong>已选择镜头顺序播放</strong>
    <small>{jobs.map((item) => frozenShot(item).title || frozenShot(item).id || item.id).join(" → ")}</small>
    <video
      key={currentIdentity}
      controls
      preload="metadata"
      ref={player}
      src={plotloomApi.videoJobMediaUrl(projectId, current.id)}
      data-testid={`video-sequence-job-${current.id}`}
      data-playback-identity={currentIdentity}
      onEnded={(event) => advance(event.currentTarget.dataset.playbackIdentity)}
    />
    <small>当前 {index + 1}/{jobs.length}：{shot.title || shot.id}。最后一帧停留，需明确重启才会从头播放。</small>
    {playbackError && <small className="notice warning" role="status">{playbackError}</small>}
    <div className="button-row">
      <Button onClick={() => play(false)}>播放当前</Button>
      <Button onClick={() => play(true)}>重启当前</Button>
      <Button disabled={index === 0} onClick={() => { setAutoplayIdentity(null); setPlaybackError(""); setActiveIdentity(identityFor(jobs[index - 1])); }}>上一镜头</Button>
      <Button disabled={index + 1 >= jobs.length} onClick={() => { setAutoplayIdentity(null); setPlaybackError(""); setActiveIdentity(identityFor(jobs[index + 1])); }}>下一镜头</Button>
    </div>
  </section>;
}

export function VideoPilotPanel({ projectId, shot, approvalId, storyboardRevision, selectionRevision, readOnly }: { projectId?: string; shot?: Shot; approvalId?: string; storyboardRevision?: number; selectionRevision: number; readOnly: boolean }) {
  const [budget, setBudget] = useState<VideoPilotBudget | null>(null);
  const [backend, setBackend] = useState<VideoBackend | null>(null);
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [aspectPolicy, setAspectPolicy] = useState<"" | "cover_center_crop" | "contain_pad" | "reject_mismatch">("");
  const [error, setError] = useState("");
  const refreshToken = useRef(0);
  const currentProjectRef = useRef(projectId);
  currentProjectRef.current = projectId;
  const refresh = async () => {
    if (!projectId) return;
    const requestedProjectId = projectId;
    if (requestedProjectId !== currentProjectRef.current) return;
    const token = ++refreshToken.current;
    const [nextBudget, nextBackend, nextJobs] = await Promise.all([
      plotloomApi.getVideoPilotBudget(), plotloomApi.getVideoBackend(), plotloomApi.getVideoJobs(requestedProjectId),
    ]);
    // A slow response from a formerly selected project cannot replace the
    // currently visible project's recovery controls or budget.
    if (token !== refreshToken.current || requestedProjectId !== currentProjectRef.current) return;
    setBudget(nextBudget); setBackend(nextBackend); setJobs(nextJobs.jobs);
  };
  useEffect(() => {
    setBudget(null); setBackend(null); setJobs([]); setError("");
    void refresh().catch((reason) => setError(reason instanceof Error ? reason.message : "无法读取视频试点状态"));
    return () => { refreshToken.current += 1; };
  }, [projectId]);
  const prepare = async () => {
    if (!projectId || !shot || !approvalId || !storyboardRevision) return;
    if (backend?.requiresAspectPolicy && !aspectPolicy) return;
    setError("");
    const request = {
      approvalId, shotId: shot.id, storyboardRevision, expectedSelectionRevision: selectionRevision,
      idempotencyKey: crypto.randomUUID(),
      ...(backend?.enabled ? {
        requestedDurationSeconds: backend.durationSeconds,
        resolution: backend.resolution,
        audio: backend.nativeAudio ? true as const : undefined,
      } : {}),
      ...(backend?.requiresAspectPolicy ? { aspectPolicy: aspectPolicy as "cover_center_crop" | "contain_pad" | "reject_mismatch" } : {}),
    };
    try { await plotloomApi.prepareVideoJob(projectId, request); await refresh(); }
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
  // State refreshes are asynchronous. Never use an old project's retained
  // jobs to construct URLs under the newly selected project identity.
  const selectedSequence = selectedSceneVideos(jobs.filter((job) => job.projectId === projectId), shot?.sceneId);
  const h3 = backend?.enabled && backend.adapterId === "minimax_h3_gateway";
  const h3NeedsAspectChoice = Boolean(backend?.requiresAspectPolicy);
  const cannotPrepare = readOnly || !projectId || !shot || !approvalId || !storyboardRevision || backend?.enabled === false || (h3NeedsAspectChoice && !aspectPolicy);
  return <Panel data-testid="video-pilot-panel"><strong>{h3 ? "MiniMax H3 本地视频候选" : "P2 Wan 视频试点"}</strong>
    {h3
      ? <p>固定 Spark H3 profile：{backend.width}×{backend.height} / 约 {backend.durationSeconds?.toFixed(2)} 秒 / 原生音频。提交后由私有网关容量控制；不会计入 Wan 付费秒数，也不会自动重试。</p>
      : <p>仅 5 秒 / 720p / 原生音频。提交后本地保守计入共享 100 秒额度；不会自动重试或回退。</p>}
    {backend?.enabled === false && <small className="notice warning">当前运行时未启用经审核的视频后端；不能冻结或提交新候选。</small>}
    {h3NeedsAspectChoice && <label><span>关键帧比例处理（必选）</span><select value={aspectPolicy} onChange={(event) => setAspectPolicy(event.target.value as typeof aspectPolicy)} disabled={readOnly}>
      <option value="">请选择，绝不静默拉伸</option>
      <option value="cover_center_crop">居中裁切以填满 16:9</option>
      <option value="contain_pad">完整保留并以黑边填充 16:9</option>
      <option value="reject_mismatch">比例不符时拒绝提交</option>
    </select></label>}
    {backend?.tracksPaidWanPilot !== false && <small>额度：{budget ? `${budget.reservedSeconds}/${budget.limitSeconds} 秒已保留，余 ${budget.remainingSeconds} 秒` : "读取中"}</small>}
    {h3 && <small>原生音频并不自动构成可接受对白；需在候选回放中人工检查可懂度、口型、表演与跨镜连续性。</small>}
    <div className="button-row"><Button disabled={cannotPrepare} onClick={() => void prepare()}>冻结当前审核关键帧</Button></div>
    {shot && <small>仅显示当前镜头：{shot.title}（{shot.id}）</small>}
    {error && <small className="notice warning">{error}</small>}
    {projectId && selectedSequence.length > 0 && <OrderedVideoPlayback projectId={projectId} jobs={selectedSequence} />}
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
