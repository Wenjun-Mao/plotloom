import { useCallback, useEffect, useRef, useState } from "react";
import type { ManagedAsset, SceneBeatPlan, Shot, StoryGraph, Storyboard, VideoBackend, VideoJob, VideoPilotBudget } from "./types";
import { plotloomApi } from "./api";
import { Button, Panel } from "./components";
import { deriveRoutes, groupStoryboard } from "./model";
import { BranchingVideoPreview } from "./branching-video-preview";
import { MiniMaxH3DurationField, MiniMaxH3ProfileField, MiniMaxH3ReviewNotice, MiniMaxH3Summary, h3Profiles, h3QualifiedDurations, isMiniMaxH3Backend, selectedH3Profile } from "./video-backends/minimax-h3";

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
export type SelectedRouteSequence = {
  jobs: VideoJob[];
  missingShotTitles: string[];
  sourceIdentity: string;
};

/**
 * Projects selected jobs onto one author-selected, currently valid graph route.
 * The storyboard is the order authority: frozen job fields only establish that
 * a candidate belongs to one of its route-scoped shots.
 */
export function selectedRouteVideos(
  jobs: VideoJob[],
  storyboard: Storyboard,
  sceneBeats: SceneBeatPlan,
  graph: StoryGraph,
  routeId?: string,
): SelectedRouteSequence | null {
  if (!routeId) return null;
  const route = deriveRoutes(graph).find((candidate) => candidate.id === routeId);
  if (!route) return null;
  const routeShots = groupStoryboard(storyboard, sceneBeats, route)
    .flatMap((group) => group.shots.map((shot) => ({ shot, sceneId: group.sceneId })));
  const selectedByShotId = new Map<string, VideoJob[]>();
  jobs.forEach((job) => {
    const frozen = frozenShot(job);
    if (job.state !== "ingested" || !job.current || !job.selected || !frozen.id || !frozen.sceneId) return;
    selectedByShotId.set(frozen.id, [...(selectedByShotId.get(frozen.id) || []), job]);
  });
  const sequence = routeShots.flatMap(({ shot, sceneId }) => (
    (selectedByShotId.get(shot.id) || [])
      .filter((job) => frozenShot(job).sceneId === sceneId)
      .sort((left, right) => left.id.localeCompare(right.id))
  ));
  const missingShotTitles = routeShots
    .filter(({ shot, sceneId }) => !(selectedByShotId.get(shot.id) || []).some((job) => frozenShot(job).sceneId === sceneId))
    .map(({ shot }) => shot.title || shot.id);
  return {
    jobs: sequence,
    missingShotTitles,
    sourceIdentity: `${route.id}:${routeShots.map(({ shot, sceneId }) => `${sceneId}/${shot.id}/${shot.order}`).join("|")}`,
  };
}

function jobStatus(job: VideoJob): string {
  if (job.cancelRequestedAt) return "取消意图已记录：保留已知远端任务，但不会采用输出";
  if (!job.current) return "冻结输入已失效";
  if (job.selected) return "当前镜头的已显式选择";
  if (job.state === "discard_pending") return "正在永久删除候选媒体；可安全重试";
  if (job.state === "discarded") return "已永久删除候选媒体；仅保留最小记录";
  return "当前";
}

function OrderedVideoPlayback({ projectId, jobs, sourceIdentity }: { projectId: string; jobs: VideoJob[]; sourceIdentity: string }) {
  const player = useRef<HTMLVideoElement>(null);
  const identityFor = (job: VideoJob) => `${projectId}:${job.id}`;
  // A position is meaningful only inside one exact selected sequence. Keeping
  // the active source as an identity (rather than a numeric position) stops a
  // changed project, scene, or selection membership from borrowing playback.
  const scopeIdentity = `${projectId}:${sourceIdentity}:${jobs.map((job) => job.id).join("|")}`;
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

export function VideoPilotPanel({ projectId, shot, approvalId, storyboardRevision, selectionRevision, keyframe, storyboard, sceneBeats, graph, routeId, readOnly }: {
  projectId?: string; shot?: Shot; approvalId?: string; storyboardRevision?: number; selectionRevision: number;
  keyframe?: ManagedAsset; storyboard: Storyboard; sceneBeats: SceneBeatPlan; graph: StoryGraph; routeId?: string; readOnly: boolean;
}) {
  const [budget, setBudget] = useState<VideoPilotBudget | null>(null);
  const [backend, setBackend] = useState<VideoBackend | null>(null);
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [h3ProfileId, setH3ProfileId] = useState("");
  const [h3DurationSeconds, setH3DurationSeconds] = useState(5);
  const [h3InputFrameMode, setH3InputFrameMode] = useState<"reject_mismatch" | "cover_center_crop" | "contain_pad">("reject_mismatch");
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
    setBudget(null); setBackend(null); setJobs([]); setError(""); setH3ProfileId(""); setH3DurationSeconds(5); setH3InputFrameMode("reject_mismatch");
    void refresh().catch((reason) => setError(reason instanceof Error ? reason.message : "无法读取视频试点状态"));
    return () => { refreshToken.current += 1; };
  }, [projectId]);
  useEffect(() => {
    if (!isMiniMaxH3Backend(backend)) return;
    const profiles = h3Profiles(backend);
    if (profiles.some((profile) => profile.id === h3ProfileId)) return;
    setH3ProfileId(backend?.defaultProfileId && profiles.some((profile) => profile.id === backend.defaultProfileId)
      ? backend.defaultProfileId
      : profiles[0]?.id ?? "");
  }, [backend, h3ProfileId]);
  const prepare = async () => {
    if (!projectId || !shot || !approvalId || !storyboardRevision) return;
    const h3 = isMiniMaxH3Backend(backend);
    const profile = h3 ? selectedH3Profile(backend, h3ProfileId) : undefined;
    if (h3 && !profile) return;
    setError("");
    const request = {
      approvalId, shotId: shot.id, storyboardRevision, expectedSelectionRevision: selectionRevision,
      idempotencyKey: crypto.randomUUID(),
      ...(backend?.enabled ? {
        requestedDurationSeconds: h3 ? h3DurationSeconds : profile?.durationSeconds ?? backend.durationSeconds,
        resolution: profile ? `${profile.width}x${profile.height}` : backend.resolution,
        audio: backend.nativeAudio ? true as const : undefined,
      } : {}),
      ...(profile ? { profileId: profile.id } : {}),
      ...(h3 ? {
        aspectPolicy: h3AspectMismatch ? h3InputFrameMode : "reject_mismatch" as const,
        allowLetterbox: h3AspectMismatch && h3InputFrameMode === "contain_pad",
        allowCenterCrop: h3AspectMismatch && h3InputFrameMode === "cover_center_crop",
      } : {}),
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
  const selectedSequence = selectedRouteVideos(jobs.filter((job) => job.projectId === projectId), storyboard, sceneBeats, graph, routeId);
  const h3 = isMiniMaxH3Backend(backend);
  const availableH3Profiles = h3Profiles(backend);
  const availableH3Durations = h3QualifiedDurations(backend);
  const selectedProfile = h3 ? selectedH3Profile(backend, h3ProfileId) : undefined;
  const h3AspectMismatch = Boolean(
    selectedProfile && keyframe
      && keyframe.width * selectedProfile.height !== keyframe.height * selectedProfile.width,
  );
  const cannotPrepare = readOnly || !projectId || !shot || !approvalId || !storyboardRevision || backend?.enabled === false || (h3 && (!selectedProfile || !keyframe || (h3AspectMismatch && h3InputFrameMode === "reject_mismatch")));
  return <Panel data-testid="video-pilot-panel"><strong>{h3 ? "MiniMax H3 本地视频候选" : "P2 Wan 视频试点"}</strong>
    {h3 && backend
      ? <MiniMaxH3Summary backend={backend} profile={selectedProfile} />
      : <p>仅 5 秒 / 720p / 原生音频。提交后本地保守计入共享 100 秒额度；不会自动重试或回退。</p>}
    {backend?.enabled === false && <small className="notice warning">当前运行时未启用经审核的视频后端；不能冻结或提交新候选。</small>}
    {h3 && <MiniMaxH3ProfileField profiles={availableH3Profiles} value={h3ProfileId} onChange={setH3ProfileId} disabled={readOnly} />}
    {h3 && <MiniMaxH3DurationField values={availableH3Durations} value={h3DurationSeconds} onChange={setH3DurationSeconds} disabled={readOnly} />}
    {h3 && selectedProfile && keyframe && !h3AspectMismatch && <small className="notice" data-testid="h3-aspect-ready">当前审核关键帧 {keyframe.width}×{keyframe.height} 与 {selectedProfile.width}×{selectedProfile.height} 比例匹配；将以 reject_mismatch 冻结。</small>}
    {h3 && selectedProfile && keyframe && h3AspectMismatch && <div className="notice warning" data-testid="h3-aspect-preparation">
      <strong>当前审核关键帧 {keyframe.width}×{keyframe.height} 与 {selectedProfile.width}×{selectedProfile.height} 比例不符。</strong>
      <small>默认拒绝比例不符。以下选择只会冻结对原审核关键帧的网关输入处理，不会替换原始字节、来源、审核选择或当前性检查。</small>
      <label><input type="radio" name="h3-input-frame-mode" checked={h3InputFrameMode === "reject_mismatch"} disabled={readOnly} onChange={() => setH3InputFrameMode("reject_mismatch")} /> 保持拒绝比例不符（默认）</label>
      <label><input type="radio" name="h3-input-frame-mode" checked={h3InputFrameMode === "cover_center_crop"} disabled={readOnly || backend?.allowsCenterCrop === false} onChange={() => setH3InputFrameMode("cover_center_crop")} /> 允许网关居中裁切（保留原审核关键帧）</label>
      <label><input type="radio" name="h3-input-frame-mode" checked={h3InputFrameMode === "contain_pad"} disabled={readOnly || backend?.allowsLetterbox === false} onChange={() => setH3InputFrameMode("contain_pad")} /> 允许黑边画布（保留当前横幅构图）</label>
      {h3InputFrameMode === "cover_center_crop"
        ? <small data-testid="h3-center-crop-allowed">将以 cover_center_crop 冻结：仅网关对冻结的原图执行居中裁切；不会创建本地裁切或 ImageGen 比例适配。</small>
        : h3InputFrameMode === "contain_pad"
        ? <small data-testid="h3-letterbox-allowed">将以 contain_pad 冻结：黑边是明确的输入画面，不会跳过输出 profile、来源或审核选择检查。</small>
        : <small>请选择匹配的已审核图，或明确选择一种网关输入画面处理。</small>}
    </div>}
    {h3 && selectedProfile && !keyframe && <small className="notice warning">先为当前镜头审核选择一张关键帧，才能验证其与 H3 profile 的比例。</small>}
    {backend?.tracksPaidWanPilot !== false && <small>额度：{budget ? `${budget.reservedSeconds}/${budget.limitSeconds} 秒已保留，余 ${budget.remainingSeconds} 秒` : "读取中"}</small>}
    {h3 && <MiniMaxH3ReviewNotice />}
    <div className="button-row"><Button disabled={cannotPrepare} onClick={() => void prepare()}>生成另一候选（冻结当前审核关键帧）</Button></div>
    {shot && <small>仅显示当前镜头：{shot.title}（{shot.id}）</small>}
    {error && <small className="notice warning">{error}</small>}
    {projectId && selectedSequence && <section className="video-sequence-status" data-testid="video-route-sequence-status">
      <strong>已选择路径片段</strong>
      <small>{selectedSequence.jobs.length} 个已选择视频 / {selectedSequence.jobs.length + selectedSequence.missingShotTitles.length} 个路径镜头</small>
      {selectedSequence.missingShotTitles.length > 0 && <small className="notice warning">路径尚不完整：缺少 {selectedSequence.missingShotTitles.join("、")} 的已选择视频。</small>}
    </section>}
    {projectId && selectedSequence && selectedSequence.jobs.length > 0 && <OrderedVideoPlayback projectId={projectId} jobs={selectedSequence.jobs} sourceIdentity={selectedSequence.sourceIdentity} />}
    {projectId && <BranchingVideoPreview projectId={projectId} jobs={jobs} storyboard={storyboard} sceneBeats={sceneBeats} graph={graph} />}
    {visibleJobs.map((job) => <article key={job.id} data-testid={`video-job-${job.id}`}><strong>{frozenShot(job).title || frozenShot(job).id}</strong> · <strong>{job.state}</strong> · {job.requestedSeconds}s {job.observed ? `· ${job.observed.durationSeconds.toFixed(2)}s 实测` : ""}
      <small> · {jobStatus(job)}</small>
      <small> · 选择版本 {job.selectionRevision} · 冻结设置 {JSON.stringify(job.snapshot.request || {})}</small>
      {job.reviews.map((review) => <small key={review.id}> · 审阅：{review.reviewer} / {review.decision} / {review.note}</small>)}
      {job.state === "ingested" && projectId && <video controls preload="metadata" src={plotloomApi.videoJobMediaUrl(projectId, job.id)} data-testid={`video-job-player-${job.id}`} onPlay={(event) => document.querySelectorAll<HTMLVideoElement>("[data-testid^='video-job-player-']").forEach((video) => { if (video !== event.currentTarget) video.pause(); })} />}
      <div className="button-row">
        {job.state === "prepared" && <Button disabled={readOnly} onClick={() => void act(() => plotloomApi.submitVideoJob(projectId!, job.id), "提交未完成")}>提交一次</Button>}
        {(job.state === "submitted" || job.state === "retrieve_needed") && <Button disabled={readOnly} onClick={() => void act(() => plotloomApi.reconcileVideoJob(projectId!, job.id), "获取结果未完成")}>获取结果</Button>}
        {["prepared", "dispatching", "submitted", "retrieve_needed", "outcome_unknown"].includes(job.state) && !job.cancelRequestedAt && <Button variant="danger" disabled={readOnly} onClick={() => void act(() => plotloomApi.cancelVideoJob(projectId!, job.id), "取消意图未记录")}>记录取消意图</Button>}
        {job.state === "ingested" && <Button disabled={readOnly || !job.current} onClick={() => void act(() => plotloomApi.reviewVideoJob(projectId!, job.id, "select", "local reviewer", "Explicit candidate selection after audiovisual review.", job.selectionRevision), "选择未完成")}>选择此候选</Button>}
        {job.state === "ingested" && !job.selected && <Button variant="danger" disabled={readOnly} onClick={() => {
          if (window.confirm("永久删除此未选择视频候选？此操作不可撤销。")) void act(() => plotloomApi.discardVideoJob(projectId!, job.id, job.selectionRevision), "删除未完成");
        }}>永久删除</Button>}
        {job.state === "discard_pending" && <Button variant="danger" disabled={readOnly} onClick={() => void act(() => plotloomApi.discardVideoJob(projectId!, job.id, job.selectionRevision), "重试删除未完成")}>重试永久删除</Button>}
      </div>
      {job.error && <small>{job.error}</small>}</article>)}
    {shot && visibleJobs.length === 0 && <small>当前镜头尚无冻结的视频请求。</small>}
    {shot && visibleJobs.some((job) => job.state === "ingested" && !job.selected) && <Button variant="danger" disabled={readOnly} onClick={() => {
      const revision = visibleJobs[0]?.selectionRevision ?? 0;
      const ids = visibleJobs.filter((job) => job.state === "ingested" && !job.selected).map((job) => job.id);
      if (window.confirm(`永久删除这 ${ids.length} 个未选择视频候选？此操作不可撤销。`)) void act(() => plotloomApi.discardUnselectedVideoJobs(projectId!, shot.id, ids, revision), "批量删除未完成");
    }}>删除全部未选择候选</Button>}
  </Panel>;
}
