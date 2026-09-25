import { useCallback, useEffect, useRef, useState } from "react";
import type { ManagedAsset, SceneBeatPlan, Shot, StoryGraph, Storyboard, VideoBackend, VideoJob, VideoPilotBudget } from "./types";
import { plotloomApi } from "./api";
import type { H3ReviewedDirections, VideoJobPrepareBody } from "./api";
import { Button, Panel } from "./components";
import { deriveRoutes, groupStoryboard } from "./model";
import { BranchingVideoPreview } from "./branching-video-preview";
import { VideoSegmentReview } from "./video-segment-review";
import { MiniMaxH3DurationField, MiniMaxH3ProfileField, MiniMaxH3QualityField, MiniMaxH3ReviewNotice, MiniMaxH3Summary, h3Profiles, h3QualifiedDurations, isMiniMaxH3Backend, selectedH3Profile } from "./video-backends/minimax-h3";
import { H3DirectionsReview } from "./h3-directions-review";

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
    if (job.state !== "ingested" || !job.current || !job.selected || !job.playbackSegment?.current || !job.playbackSegment.selected || !frozen.id || !frozen.sceneId) return;
    selectedByShotId.set(frozen.id, [...(selectedByShotId.get(frozen.id) || []), job]);
  });
  const sequence = routeShots.flatMap(({ shot, sceneId }) => (
    (selectedByShotId.get(shot.id) || [])
      .filter((job) => frozenShot(job).sceneId === sceneId && job.playbackSegment?.authoredDurationUnits === shot.durationUnits)
      .sort((left, right) => left.id.localeCompare(right.id))
  ));
  const missingShotTitles = routeShots
    .filter(({ shot, sceneId }) => !(selectedByShotId.get(shot.id) || []).some((job) => frozenShot(job).sceneId === sceneId && job.playbackSegment?.authoredDurationUnits === shot.durationUnits))
    .map(({ shot }) => shot.title || shot.id);
  return {
    jobs: sequence,
    missingShotTitles,
    sourceIdentity: `${route.id}:${routeShots.map(({ shot, sceneId }) => `${sceneId}/${shot.id}/${shot.order}`).join("|")}:${sequence.map((job) => `${job.playbackSegment?.id}/${job.playbackSegment?.derivativeHash}`).join("|")}`,
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

function isH3Job(job: VideoJob): boolean {
  const provider = job.snapshot.provider;
  return typeof provider === "object" && provider !== null
    && (provider as Record<string, unknown>).adapterId === "minimax_h3_gateway";
}

function frozenH3Quality(job: VideoJob): string {
  const request = job.snapshot.request;
  if (!request || typeof request !== "object") return "未知";
  const frozen = request as Record<string, unknown>;
  if (frozen.quality === 1 || frozen.quality === 8) return String(frozen.quality);
  // Quality-1 V1 jobs predate an explicit quality field. Their profile ID
  // preserves its meaning; it is never inferred from today's UI selection.
  return typeof frozen.profileId === "string" && frozen.profileId.includes("_quality1_") ? "1" : "未知";
}

function OrderedVideoPlayback({ projectId, jobs, sourceIdentity }: { projectId: string; jobs: VideoJob[]; sourceIdentity: string }) {
  const player = useRef<HTMLVideoElement>(null);
  const identityFor = (job: VideoJob) => `${projectId}:${job.id}:${job.playbackSegment?.id}:${job.playbackSegment?.derivativeHash}`;
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
      src={plotloomApi.selectedVideoPlaybackUrl(projectId, current.id)}
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
  const buildPrepareRequest = (seed?: number, idempotencyKey?: string): VideoJobPrepareBody => {
    if (!shot || !approvalId || !storyboardRevision) throw new Error("请先选择并批准当前分镜");
    const h3 = isMiniMaxH3Backend(backend);
    const profile = h3 ? selectedH3Profile(backend, h3ProfileId) : undefined;
    if (h3 && !profile) throw new Error("请先选择 H3 视频规格");
    const aspectMismatch = Boolean(profile && keyframe && keyframe.width * profile.height !== keyframe.height * profile.width);
    return {
      approvalId, shotId: shot.id, storyboardRevision, expectedSelectionRevision: selectionRevision,
      idempotencyKey: idempotencyKey ?? crypto.randomUUID(),
      playbackIntent: h3 && shot.durationUnits === 6_000 && h3DurationSeconds === 8 ? "segment_required" as const : "source_exact" as const,
      ...(backend?.enabled ? {
        requestedDurationSeconds: h3 ? h3DurationSeconds : profile?.durationSeconds ?? backend.durationSeconds,
        resolution: profile ? `${profile.width}x${profile.height}` : backend.resolution,
        audio: backend.nativeAudio ? true as const : undefined,
      } : {}),
      ...(profile ? { profileId: profile.id } : {}),
      ...(h3 && seed !== undefined ? { seed } : {}),
      ...(h3 ? {
        aspectPolicy: aspectMismatch ? h3InputFrameMode : "reject_mismatch" as const,
        allowLetterbox: aspectMismatch && h3InputFrameMode === "contain_pad",
        allowCenterCrop: aspectMismatch && h3InputFrameMode === "cover_center_crop",
      } : {}),
    };
  };
  const prepare = async (reviewedDirections?: H3ReviewedDirections, seed?: number, idempotencyKey?: string) => {
    if (!projectId) return;
    setError("");
    try {
      const request = { ...buildPrepareRequest(seed, idempotencyKey), ...(reviewedDirections ? { reviewedDirections } : {}) };
      await plotloomApi.prepareVideoJob(projectId, request);
      await refresh();
    }
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
  const navigableSegmentJob = visibleJobs.find((job) => isH3Job(job) && job.state === "ingested"
    && job.current && job.reviews.at(-1)?.decision !== "reject"
    && job.segments?.some((segment) => segment.current));
  const navigationJob = navigableSegmentJob
    ?? visibleJobs.find((job) => isH3Job(job) && job.state === "ingested" && job.current && job.reviews.at(-1)?.decision !== "reject")
    ?? visibleJobs.find((job) => isH3Job(job) && job.state === "ingested");
  const segmentAnchorJobId = navigationJob?.id;
  const hasReviewableSegment = Boolean(navigationJob?.segments?.some((segment) => segment.current)
    && navigationJob?.current && navigationJob?.reviews.at(-1)?.decision !== "reject");
  const nextAction = visibleJobs.some((job) => job.selected)
    ? "当前镜头已有用于故事的片段；可在下方检查路径预览。"
    : visibleJobs.some((job) => job.state === "ingested" && job.segments?.some((segment) => segment.current))
      ? "下一步：听看待审片段，再明确确认用于故事。"
      : visibleJobs.some((job) => job.state === "ingested")
        ? "下一步：从原片选择连续帧，生成待审片段。"
        : "下一步：展开准备区，检查关键帧与视频请求。";
  // State refreshes are asynchronous. Never use an old project's retained
  // jobs to construct URLs under the newly selected project identity.
  const selectedSequence = selectedRouteVideos(jobs.filter((job) => job.projectId === projectId), storyboard, sceneBeats, graph, routeId);
  const h3 = isMiniMaxH3Backend(backend);
  const availableH3Profiles = h3Profiles(backend);
  const availableH3Durations = h3QualifiedDurations(backend);
  const selectedProfile = h3 ? selectedH3Profile(backend, h3ProfileId) : undefined;
  const h3Unavailable = backend?.enabled === false && backend.reason === "h3_video_not_configured";
  const h3AspectMismatch = Boolean(
    selectedProfile && keyframe
      && keyframe.width * selectedProfile.height !== keyframe.height * selectedProfile.width,
  );
  const cannotPrepare = readOnly || !projectId || !shot || !approvalId || !storyboardRevision || backend?.enabled === false || (h3 && (!selectedProfile || !keyframe || (h3AspectMismatch && h3InputFrameMode === "reject_mismatch")));
  const h3TimingMismatch = Boolean(h3 && shot && (
    shot.durationUnits === 6_000 ? h3DurationSeconds !== 8
      : shot.durationUnits === 8_000 ? h3DurationSeconds !== 8
      : h3DurationSeconds * 1_000 !== shot.durationUnits
  ));
  const h3RequestedFrames = h3DurationSeconds * 24 + (5 - h3DurationSeconds * 24 % 17) % 17;
  return <Panel className="video-pilot-workflow" data-testid="video-pilot-panel">
    <header className="video-workflow-header"><strong>原片 → 调整片段 → 预览 → 用于故事</strong>
      <small>{visibleJobs.length ? `当前镜头有 ${visibleJobs.length} 个原片候选；仅明确选择的片段会进入故事。` : "当前镜头还没有原片候选。"}</small>
      <small className="video-next-action">{nextAction}</small>
      <nav className="video-workflow-nav" aria-label="镜头视频工作流">
        {visibleJobs.length ? <a href="#shot-original">原片</a> : <a href="#video-production">准备原片</a>}
        {navigationJob ? <a href={`#video-segment-review-${navigationJob.id}`}>调整片段</a> : <span aria-disabled="true">调整片段 · 待原片</span>}
        {hasReviewableSegment && navigationJob ? <a href={`#video-segment-preview-${navigationJob.id}`}>预览片段</a> : <span aria-disabled="true">预览片段 · 待准备</span>}
        {hasReviewableSegment && navigationJob ? <a href={`#video-segment-confirm-${navigationJob.id}`}>用于故事 · 确认</a> : <span aria-disabled="true">用于故事 · 待审核</span>}
        {visibleJobs.some((job) => job.selected) && <a href="#shot-story-preview">故事播放</a>}
      </nav></header>
    <details id="video-production" className="video-production"><summary>{h3 || h3Unavailable ? "准备或生成新的 MiniMax H3 原片" : "准备或生成新的视频原片"}</summary>
    {h3 && backend
      ? <MiniMaxH3Summary backend={backend} profile={selectedProfile} />
      : h3Unavailable ? <p>H3 后端尚未配置；下方当前镜头时长目录仅供只读检查，不代表可提交。</p>
        : <p>仅 5 秒 / 720p / 原生音频。提交后本地保守计入共享 100 秒额度；不会自动重试或回退。</p>}
    {backend?.enabled === false && <small className="notice warning">当前运行时未启用经审核的视频后端；不能冻结或提交新候选。</small>}
    {h3 && <MiniMaxH3QualityField profiles={availableH3Profiles} value={h3ProfileId} onChange={setH3ProfileId} disabled={readOnly} />}
    {h3 && <MiniMaxH3ProfileField profiles={availableH3Profiles} value={h3ProfileId} onChange={setH3ProfileId} disabled={readOnly} />}
    {h3 && <MiniMaxH3DurationField values={availableH3Durations} value={h3DurationSeconds} onChange={setH3DurationSeconds} disabled={readOnly} />}
    {h3 && shot && <small className={h3TimingMismatch ? "notice warning" : "notice"} data-testid="h3-authored-timing">
      原稿镜头时长 {(shot.durationUnits / 1000).toFixed(3)} 秒；后端请求 {h3DurationSeconds} 秒 / {h3RequestedFrames} 帧（约 {(h3RequestedFrames / 24).toFixed(2)} 秒）。
      {shot.durationUnits === 6_000 ? "当前六秒原稿仅可请求八秒原片，再审阅连续 144 帧片段；不会自动裁切或选择。" : "请求时长不是实测播放时长；当前播放路径仍只支持已审核的六/八秒源镜头，其他时长的原片不能据此进入故事。"}
    </small>}
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
    {h3 && projectId && shot
      ? <H3DirectionsReview projectId={projectId}
          sourceIdentity={`${shot.id}:${storyboardRevision}:${selectionRevision}:${keyframe?.id ?? ""}:${h3ProfileId}:${h3DurationSeconds}:${h3InputFrameMode}:${visibleJobs.length}`}
          disabled={Boolean(cannotPrepare || h3TimingMismatch)} buildRequest={buildPrepareRequest}
          keyframeHash={keyframe?.originalHash ?? ""} quality={selectedProfile?.quality ?? 0}
          requestedSeconds={h3DurationSeconds} frameCount={h3RequestedFrames}
          onFreeze={(packageValue, seed, key) => prepare(packageValue, seed, key)} />
      : <div className="button-row"><Button disabled={cannotPrepare || h3TimingMismatch} onClick={() => void prepare()}>生成另一候选（冻结当前审核关键帧）</Button></div>}
    </details>
    {error && <small className="notice warning">{error}</small>}
    {visibleJobs.map((job, index) => <article id={index === 0 ? "shot-original" : undefined} className="video-job-card" key={job.id} data-testid={`video-job-${job.id}`}><header><strong>原片 · {frozenShot(job).title || "当前镜头"}</strong><span>{job.selected ? "已选择片段" : job.state === "ingested" ? "待审原片" : job.state}</span></header>
      <small>{isH3Job(job) ? `质量 ${frozenH3Quality(job)} · ` : ""}请求 {job.requestedSeconds} 秒 {job.observed ? `· 实测 ${job.observed.durationSeconds.toFixed(2)} 秒` : ""}</small>
      <small> · {jobStatus(job)}</small>
      <details className="video-technical-history"><summary>审核历史与技术详情</summary>
        <small>选择版本 {job.selectionRevision} · 原片编号 {job.id}</small>
        <pre>{JSON.stringify(job.snapshot.request || {}, null, 2)}</pre>
        {job.reviews.map((review) => <small key={review.id}>审阅：{review.decision === "select" ? "选择" : "拒绝"}{review.reviewer ? ` · ${review.reviewer}` : ""}{review.note ? ` · ${review.note}` : ""}</small>)}
      </details>
      {job.state === "ingested" && projectId && <video controls preload="metadata" src={plotloomApi.videoJobMediaUrl(projectId, job.id)} data-testid={`video-job-player-${job.id}`} onPlay={(event) => document.querySelectorAll<HTMLVideoElement>("[data-testid^='video-job-player-']").forEach((video) => { if (video !== event.currentTarget) video.pause(); })} />}
      <div className="button-row">
        {job.state === "prepared" && <Button disabled={readOnly} onClick={() => void act(() => plotloomApi.submitVideoJob(projectId!, job.id), "提交未完成")}>提交一次</Button>}
        {(job.state === "submitted" || job.state === "retrieve_needed") && <Button disabled={readOnly} onClick={() => void act(() => plotloomApi.reconcileVideoJob(projectId!, job.id), "获取结果未完成")}>获取结果</Button>}
        {["prepared", "dispatching", "submitted", "retrieve_needed", "outcome_unknown"].includes(job.state) && !job.cancelRequestedAt && <Button variant="danger" disabled={readOnly} onClick={() => void act(() => plotloomApi.cancelVideoJob(projectId!, job.id), "取消意图未记录")}>记录取消意图</Button>}
        {job.state === "ingested" && !isH3Job(job) && <Button disabled={readOnly || !job.current} onClick={() => void act(() => plotloomApi.reviewVideoJob(projectId!, job.id, "select", "", "", job.selectionRevision), "选择未完成")}>选择此候选</Button>}
        {job.state === "ingested" && !job.selected && <Button variant="danger" disabled={readOnly} onClick={() => {
          if (window.confirm("永久删除此未选择视频候选？此操作不可撤销。")) void act(() => plotloomApi.discardVideoJob(projectId!, job.id, job.selectionRevision), "删除未完成");
        }}>永久删除</Button>}
        {job.state === "discard_pending" && <Button variant="danger" disabled={readOnly} onClick={() => void act(() => plotloomApi.discardVideoJob(projectId!, job.id, job.selectionRevision), "重试删除未完成")}>重试永久删除</Button>}
      </div>
      {isH3Job(job) && projectId && job.state === "ingested" && <div id={job.id === segmentAnchorJobId ? "shot-segment" : undefined}><VideoSegmentReview key={`${projectId}:${job.id}`} projectId={projectId} job={job} readOnly={readOnly} onRefresh={refresh} /></div>}
      {job.error && <small>{job.error}</small>}</article>)}
    <section id="shot-story-preview" className="story-playback-section"><strong>预览 · 用于故事</strong>
      <small>只有当前、已明确选择且可核验的播放片段会进入故事；待审原片不会自动播放。</small>
      {projectId && selectedSequence && <section className="video-sequence-status" data-testid="video-route-sequence-status">
        <strong>已选择路径片段</strong>
        <small>{selectedSequence.jobs.length} 个已选择视频 / {selectedSequence.jobs.length + selectedSequence.missingShotTitles.length} 个路径镜头</small>
        {selectedSequence.missingShotTitles.length > 0 && <small className="notice warning">路径尚不完整：缺少 {selectedSequence.missingShotTitles.join("、")} 的已选择视频。请回到对应镜头，审核片段后确认用于故事。</small>}
      </section>}
      {projectId && selectedSequence && selectedSequence.jobs.length > 0 && selectedSequence.missingShotTitles.length === 0 && <OrderedVideoPlayback projectId={projectId} jobs={selectedSequence.jobs} sourceIdentity={selectedSequence.sourceIdentity} />}
      {projectId && <BranchingVideoPreview projectId={projectId} jobs={jobs} storyboard={storyboard} sceneBeats={sceneBeats} graph={graph} />}
    </section>
    {shot && visibleJobs.length === 0 && <small>当前镜头尚无冻结的视频请求。</small>}
    {shot && visibleJobs.some((job) => job.state === "ingested" && !job.selected) && <Button variant="danger" disabled={readOnly} onClick={() => {
      const revision = visibleJobs[0]?.selectionRevision ?? 0;
      const ids = visibleJobs.filter((job) => job.state === "ingested" && !job.selected).map((job) => job.id);
      if (window.confirm(`永久删除这 ${ids.length} 个未选择视频候选？此操作不可撤销。`)) void act(() => plotloomApi.discardUnselectedVideoJobs(projectId!, shot.id, ids, revision), "批量删除未完成");
    }}>删除全部未选择候选</Button>}
  </Panel>;
}
