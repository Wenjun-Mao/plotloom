import { useCallback, useEffect, useRef, useState } from "react";
import type { ManagedAsset, ReviewedKeyframe, SceneBeatPlan, Shot, StoryGraph, Storyboard, VideoBackend, VideoJob, VideoPilotBudget } from "./types";
import { plotloomApi } from "./api";
import type { H3ReviewedDirections, VideoJobPrepareBody } from "./api";
import type { VideoEndFrameDecision } from "./api";
import { Button, Panel, Spinner } from "./components";
import { deriveRoutes, groupStoryboard } from "./model";
import { BranchingVideoPreview } from "./branching-video-preview";
import { VideoSegmentReview } from "./video-segment-review";
import { MiniMaxH3DurationField, MiniMaxH3ProfileField, MiniMaxH3QualityField, MiniMaxH3ReviewNotice, MiniMaxH3Summary, h3Profiles, h3QualifiedDurations, isMiniMaxH3Backend, selectedH3Profile } from "./video-backends/minimax-h3";
import { H3DirectionsReview } from "./h3-directions-review";
import { useH3MediaIdentity } from "./h3-review-context";
import type { MediaReadPhase } from "./features/media/useMediaWorkbenchData";
import { VideoEndFrameChoice } from "./video-end-frame";
import { useConfirmation } from "./confirmation";
import { h3Timing } from "./video-backends/minimax-h3-timing";
import { shotLabel } from "./shot-label";
import { nodeFootageGaps } from "./node-footage";
import { verifiedVideoGeometry } from "./features/media/verified-video-geometry";
import { ReviewedVideoPlayer } from "./features/media/ReviewedVideoPlayer";
import { isCurrentVideoSelection, videoNextAction } from "./features/media/video-next-action";
import { frozenVideoSnapshot } from "./features/media/frozen-video-snapshot";

type FrozenShot = { id?: string; title?: string; action?: string; sceneId?: string; order?: number };

function frozenShot(job: VideoJob): FrozenShot {
  const candidate = frozenVideoSnapshot(job)?.shot;
  return candidate && typeof candidate === "object" ? candidate as FrozenShot : {};
}

// ADR 0082 retains every proposed derivative and its original, even when
// neither is currently selected. The server remains the deletion authority.
function canDiscard(job: VideoJob): boolean {
  return job.state === "ingested" && !job.selected && !job.segments?.length;
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
    if (!isCurrentVideoSelection(job) || !frozen.id || !frozen.sceneId) return;
    selectedByShotId.set(frozen.id, [...(selectedByShotId.get(frozen.id) || []), job]);
  });
  const sequence = routeShots.flatMap(({ shot, sceneId }) => (
    (selectedByShotId.get(shot.id) || [])
      .filter((job) => frozenShot(job).sceneId === sceneId && job.playbackSegment?.authoredDurationUnits === shot.durationUnits)
      .sort((left, right) => left.id.localeCompare(right.id))
  ));
  const missingShotTitles = routeShots
    .filter(({ shot, sceneId }) => !(selectedByShotId.get(shot.id) || []).some((job) => frozenShot(job).sceneId === sceneId && job.playbackSegment?.authoredDurationUnits === shot.durationUnits))
    .map(({ shot }) => shotLabel(shot));
  const routeNodes = graph.nodes.filter(node => route.nodeIds.includes(node.id));
  missingShotTitles.push(...routeNodes.flatMap(node => nodeFootageGaps(node, sceneBeats, storyboard)));
  return {
    jobs: sequence,
    missingShotTitles,
    sourceIdentity: `${route.id}:${routeNodes.map(node => `${node.id}/${node.footageMode}`).join("|")}:${routeShots.map(({ shot, sceneId }) => `${sceneId}/${shot.id}/${shot.order}`).join("|")}:${sequence.map((job) => `${job.playbackSegment?.id}/${job.playbackSegment?.derivativeHash}`).join("|")}`,
  };
}

function jobStatus(job: VideoJob): string {
  if (job.cancelRequestedAt) return "取消意图已记录：保留已知远端任务，但不会采用输出";
  if (job.lifecycleStatus === "archived") return "项目已归档 · 保留媒体证据";
  if (job.inputStatus === "invalid") return "冻结输入证据未通过核验";
  if (job.inputStatus === "stale") return "冻结输入与当前内容不一致";
  if (job.selected) return "已为当前镜头选择播放片段";
  if (job.state === "discard_pending") return "正在永久删除候选媒体；可安全重试";
  if (job.state === "discarded") return "已永久删除候选媒体；仅保留最小记录";
  return "当前";
}

function isH3Job(job: VideoJob): boolean {
  const provider = frozenVideoSnapshot(job)?.provider;
  return typeof provider === "object" && provider !== null
    && (provider as Record<string, unknown>).adapterId === "minimax_h3_gateway";
}

function frozenH3Quality(job: VideoJob): string {
  const request = frozenVideoSnapshot(job)?.request;
  if (!request || typeof request !== "object") return "未知";
  const frozen = request as Record<string, unknown>;
  if (frozen.quality === 1 || frozen.quality === 8) return String(frozen.quality);
  return "未知";
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
    <small>{jobs.map((item) => shotLabel(frozenShot(item), item.id)).join(" → ")}</small>
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
    <small>当前 {index + 1}/{jobs.length}：{shotLabel(shot)}。最后一帧停留，需明确重启才会从头播放。</small>
    {playbackError && <small className="notice warning" role="status">{playbackError}</small>}
    <div className="button-row">
      <Button onClick={() => play(false)}>播放当前</Button>
      <Button onClick={() => play(true)}>重启当前</Button>
      <Button disabled={index === 0} onClick={() => { setAutoplayIdentity(null); setPlaybackError(""); setActiveIdentity(identityFor(jobs[index - 1])); }}>上一镜头</Button>
      <Button disabled={index + 1 >= jobs.length} onClick={() => { setAutoplayIdentity(null); setPlaybackError(""); setActiveIdentity(identityFor(jobs[index + 1])); }}>下一镜头</Button>
    </div>
  </section>;
}

export function VideoPilotPanel({ projectId, lifecycleRevision, lifecycleStatus, shot, approvalId, storyboardRevision, selectionRevision, keyframe, reviewedBinding, samePersonReviewId, mediaReadPhase, storyboard, sceneBeats, graph, routeId, readOnly }: {
  projectId?: string; shot?: Shot; approvalId?: string; storyboardRevision?: number; selectionRevision: number;
  lifecycleRevision?: number;
  lifecycleStatus?: "active" | "archived";
  keyframe?: ManagedAsset; storyboard: Storyboard; sceneBeats: SceneBeatPlan; graph: StoryGraph; routeId?: string; readOnly: boolean;
  reviewedBinding?: ReviewedKeyframe; samePersonReviewId?: string; mediaReadPhase: MediaReadPhase;
}) {
  const [budget, setBudget] = useState<VideoPilotBudget | null>(null);
  const [backend, setBackend] = useState<VideoBackend | null>(null);
  const [loadedJobs, setJobs] = useState<VideoJob[]>([]);
  const videoContext = JSON.stringify([projectId, lifecycleRevision]);
  const [loadedContext, setLoadedContext] = useState<string>();
  const [loadedProjectId, setLoadedProjectId] = useState<string>();
  const videoReadCurrent = loadedContext === videoContext;
  const jobs = videoReadCurrent ? loadedJobs : [];
  const { requestConfirmation, confirmation } = useConfirmation(JSON.stringify([projectId, shot?.id, selectionRevision, jobs.map(job => [job.id, job.selectionRevision, job.state, job.selected, job.current, job.segments?.map(segment => segment.id)])]), readOnly);
  const [h3ProfileId, setH3ProfileId] = useState("");
  const [h3DurationSeconds, setH3DurationSeconds] = useState(5);
  const [h3InputFrameMode, setH3InputFrameMode] = useState<"reject_mismatch" | "cover_center_crop" | "contain_pad">("reject_mismatch");
  const endFrameScope = JSON.stringify([projectId, shot?.id, approvalId, storyboardRevision]);
  const [endFrameState, setEndFrameState] = useState<{ scope: string; decision: VideoEndFrameDecision } | null>(null);
  const [endFrameDraftState, setEndFrameDraftState] = useState<{ scope: string; dirty: boolean } | null>(null);
  const [endFrameReadiness, setEndFrameReadiness] = useState<{ scope: string; ready: boolean } | null>(null);
  const [error, setError] = useState("");
  const refreshToken = useRef(0);
  const currentContextRef = useRef(videoContext);
  currentContextRef.current = videoContext;
  const refresh = async () => {
    if (!projectId) return;
    const requestedProjectId = projectId;
    if (videoContext !== currentContextRef.current) return;
    const token = ++refreshToken.current;
    setLoadedContext(undefined);
    setError("");
    try {
      const [nextBudget, nextBackend, nextJobs] = await Promise.all([
        plotloomApi.getVideoPilotBudget(), plotloomApi.getVideoBackend(), plotloomApi.getVideoJobs(requestedProjectId),
      ]);
      // Archive/restore changes read authority without remounting the editor.
      if (token !== refreshToken.current || videoContext !== currentContextRef.current) return;
      setBudget(nextBudget); setBackend(nextBackend); setJobs(nextJobs.jobs);
      setLoadedContext(videoContext);
      setLoadedProjectId(requestedProjectId);
    } catch (reason) {
      if (token === refreshToken.current && videoContext === currentContextRef.current) throw reason;
    }
  };
  useEffect(() => {
    setH3ProfileId(""); setH3DurationSeconds(5); setH3InputFrameMode("reject_mismatch");
  }, [projectId]);
  useEffect(() => {
    setLoadedContext(undefined); setError("");
    void refresh().catch((reason) => {
      if (videoContext === currentContextRef.current) setError(reason instanceof Error ? reason.message : "无法读取视频试点状态");
    });
    return () => { refreshToken.current += 1; };
  }, [videoContext]);
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
    if (h3 && !currentH3Timing.playbackIntent) throw new Error("当前 H3 请求目录、原稿帧网格或请求容量不适用");
    return {
      approvalId, shotId: shot.id, storyboardRevision, expectedSelectionRevision: selectionRevision,
      idempotencyKey: idempotencyKey ?? crypto.randomUUID(),
      playbackIntent: h3 ? currentH3Timing.playbackIntent! : "source_exact",
      ...(backend?.enabled ? {
        requestedDurationSeconds: h3 ? h3DurationSeconds : profile?.durationSeconds ?? backend.durationSeconds,
        resolution: profile ? `${profile.width}x${profile.height}` : backend.resolution,
        audio: backend.nativeAudio ? true as const : undefined,
      } : {}),
      ...(profile ? { profileId: profile.id } : {}),
      ...(h3 && seed !== undefined ? { seed } : {}),
      ...(h3 ? {
        aspectPolicy: h3InputFrameMode,
        allowLetterbox: h3InputFrameMode === "contain_pad",
        allowCenterCrop: h3InputFrameMode === "cover_center_crop",
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
    catch (reason) { if (videoContext === currentContextRef.current) setError(reason instanceof Error ? reason.message : "无法冻结视频请求"); }
  };
  const act = async (operation: () => Promise<unknown>, fallback: string) => {
    const actionContext = videoContext;
    setError("");
    try {
      await operation();
      if (actionContext !== currentContextRef.current) return;
      await refresh();
    }
    catch (reason) { if (actionContext === currentContextRef.current) setError(reason instanceof Error ? reason.message : fallback); }
  };
  const visibleJobs = shot ? jobs.filter((job) => frozenShot(job).id === shot.id) : [];
  const unassignedInvalidJobs = jobs.filter(job => job.inputStatus === "invalid" && !frozenShot(job).id);
  const navigableSegmentJob = visibleJobs.find((job) => isH3Job(job) && job.state === "ingested"
    && job.current && job.reviews.at(-1)?.decision !== "reject"
    && job.segments?.some((segment) => segment.current));
  const navigationJob = navigableSegmentJob
    ?? visibleJobs.find((job) => isH3Job(job) && job.state === "ingested" && job.current && job.reviews.at(-1)?.decision !== "reject")
    ?? visibleJobs.find((job) => isH3Job(job) && job.state === "ingested");
  const segmentAnchorJobId = navigationJob?.id;
  const hasReviewableSegment = Boolean(navigationJob?.segments?.some((segment) => segment.current)
    && navigationJob?.current && navigationJob?.reviews.at(-1)?.decision !== "reject");
  const hasPreviewSegment = Boolean(navigationJob?.segments?.some(segment => segment.previewEligible));
  const nextAction = videoNextAction(visibleJobs, shot?.durationUnits);
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
  const requestAspectPolicy = h3InputFrameMode;
  const currentEndFrame = endFrameState?.scope === endFrameScope ? endFrameState.decision : null;
  const endFrameDraftDirty = endFrameDraftState?.scope === endFrameScope && endFrameDraftState.dirty;
  const endFrameReady = endFrameReadiness?.scope === endFrameScope && endFrameReadiness.ready;
  const endFrameAspectReady = !currentEndFrame?.assetId || currentEndFrame.aspectPolicy === requestAspectPolicy;
  const endFrameApprovalReady = !currentEndFrame?.revision || (currentEndFrame.approvalId === approvalId && currentEndFrame.storyboardRevision === storyboardRevision);
  const mediaReady = mediaReadPhase === "ready" && videoReadCurrent;
  const mediaIdentity = useH3MediaIdentity({ projectId, shotId: shot?.id, ready: mediaReady,
    binding: reviewedBinding, keyframe, samePersonReviewId });
  const cannotPrepare = readOnly || !mediaReady || !projectId || !shot || !approvalId || !storyboardRevision || backend?.enabled === false || (h3 && (!selectedProfile || !keyframe || !currentEndFrame || !endFrameReady || endFrameDraftDirty || !endFrameAspectReady || !endFrameApprovalReady || (h3AspectMismatch && h3InputFrameMode === "reject_mismatch")));
  const currentH3Timing = h3Timing(shot?.durationUnits ?? 0, h3DurationSeconds, backend?.qualifiedDurationSeconds);
  const h3RequestedFrames = currentH3Timing.requestFrames;
  const h3TimingMismatch = h3 && !currentH3Timing.playbackIntent;
  // Empty jobs mean "none" only after an owned, complete project read. Do not
  // expose missing-media advice or production actions from an unknown snapshot.
  if (!projectId || loadedProjectId !== projectId) return <Panel className="video-pilot-workflow" data-testid="video-pilot-panel">
    <strong>镜头视频</strong>
    {!projectId ? <p>先保存项目，再查看或准备镜头视频。</p> : error ? <>
      <p className="notice warning" role="alert">无法读取镜头视频状态：{error}</p>
      <Button variant="quiet" onClick={() => void refresh().catch(reason => { if (videoContext === currentContextRef.current) setError(reason instanceof Error ? reason.message : "读取失败"); })}>重新读取镜头视频状态</Button>
    </> : <Spinner label="正在读取镜头视频状态" />}
  </Panel>;
  return <Panel className="video-pilot-workflow" data-testid="video-pilot-panel">
    <header className="video-workflow-header"><strong>原片 → 调整片段 → 预览 → 用于故事</strong>
      <small>{!videoReadCurrent ? "正在重新核实镜头视频；先前的选择和播放资格暂不使用。" : visibleJobs.length ? `当前镜头有 ${visibleJobs.length} 条视频请求记录；请求不代表原片已生成。只有明确选择的播放片段会进入故事。` : unassignedInvalidJobs.length ? "未找到可确认归属于当前镜头的原片候选；另有冻结证据损坏的请求记录。" : "当前镜头还没有原片候选。"}</small>
      <small className="video-next-action">{videoReadCurrent ? nextAction : error ? "视频读取未完成，请重新读取。" : <Spinner label="正在读取镜头视频状态" />}</small>
      {videoReadCurrent && <nav className="video-workflow-nav" aria-label="镜头视频工作流">
        {visibleJobs.length ? <a href="#shot-original">请求与原片</a> : <a href="#video-production">准备原片</a>}
        {navigationJob ? <a href={`#video-segment-review-${navigationJob.id}`}>调整片段</a> : <span aria-disabled="true">调整片段 · 待原片</span>}
        {hasPreviewSegment && navigationJob ? <a href={`#video-segment-preview-${navigationJob.id}`}>预览片段</a> : <span aria-disabled="true">预览片段 · 待准备</span>}
        {lifecycleStatus === "archived" ? <span aria-disabled="true">用于故事 · 已停用</span>
          : hasReviewableSegment && navigationJob ? <a href={`#video-segment-confirm-${navigationJob.id}`}>用于故事 · 确认</a> : <span aria-disabled="true">用于故事 · 待审核</span>}
        {visibleJobs.some((job) => job.selected) && <a href="#shot-story-preview">故事播放</a>}
      </nav>}</header>
    {!videoReadCurrent && error && <Button variant="quiet" onClick={() => void refresh().catch(reason => { if (videoContext === currentContextRef.current) setError(reason instanceof Error ? reason.message : "读取失败"); })}>重新读取镜头视频状态</Button>}
    {unassignedInvalidJobs.length > 0 && <div className="notice warning" role="alert">
      <strong>有 {unassignedInvalidJobs.length} 条视频请求的冻结证据未通过核验，无法确认镜头归属。</strong>
      <small>这些记录不会进入当前故事播放，也不会被自动删除或重新派发。</small>
      <details><summary>无法确认归属的请求详情</summary>{unassignedInvalidJobs.map(job => <div key={job.id}>
        <strong>{job.id}</strong><pre>{JSON.stringify(job.snapshot, null, 2)}</pre>
      </div>)}</details>
    </div>}
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
      原稿镜头时长 {(shot.durationUnits / 1000).toFixed(3)} 秒；后端请求 {h3DurationSeconds} 秒 / {h3RequestedFrames ?? "未知"} 帧{h3RequestedFrames !== undefined && `（约 ${(h3RequestedFrames / 24).toFixed(2)} 秒）`}。
      {h3TimingMismatch ? "当前请求目录不适用，或无法覆盖 24 fps 帧网格上的原稿时长，请审阅请求与原稿。" : `原稿需要 ${currentH3Timing.sourceFrames} 帧；仍须核验实测原片并审阅连续片段，不会自动裁切或选择。`}
    </small>}
    {h3 && projectId && shot && <VideoEndFrameChoice key={endFrameScope} projectId={projectId} shotId={shot.id}
      approvalId={approvalId} storyboardRevision={storyboardRevision} profile={selectedProfile}
      requestAspectPolicy={requestAspectPolicy} readOnly={readOnly}
      onDecision={(decision) => setEndFrameState({ scope: endFrameScope, decision })}
      onDraftChange={(dirty) => setEndFrameDraftState({ scope: endFrameScope, dirty })}
      onReadinessChange={(ready) => setEndFrameReadiness({ scope: endFrameScope, ready })} />}
    {h3 && selectedProfile && keyframe && !h3AspectMismatch && <div className="notice" data-testid="h3-aspect-ready"><small>当前审核关键帧 {keyframe.width}×{keyframe.height} 与 {selectedProfile.width}×{selectedProfile.height} 比例匹配。</small>
      <label>首帧与末帧统一输入处理<select value={h3InputFrameMode} disabled={readOnly} onChange={(event) => setH3InputFrameMode(event.target.value as typeof h3InputFrameMode)}>
        <option value="reject_mismatch">比例不符则拒绝</option><option value="contain_pad">黑边画布</option><option value="cover_center_crop">居中裁切</option>
      </select></label></div>}
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
          sourceIdentity={JSON.stringify([shot.id, approvalId, storyboardRevision, mediaIdentity, h3ProfileId, h3DurationSeconds, h3InputFrameMode, currentEndFrame?.revision, currentEndFrame?.originalHash, endFrameDraftDirty, loadedJobs.filter(job => job.projectId === projectId && frozenShot(job).id === shot.id).length])}
          sourceReady={mediaReady && Boolean(endFrameReady)}
          disabled={Boolean(cannotPrepare || h3TimingMismatch)} buildRequest={buildPrepareRequest}
          keyframeHash={keyframe?.originalHash ?? ""} endFrameHash={currentEndFrame?.originalHash ?? null} quality={selectedProfile?.quality ?? 0}
          requestedSeconds={h3DurationSeconds} frameCount={h3RequestedFrames ?? 0}
          onFreeze={(packageValue, seed, key) => prepare(packageValue, seed, key)} />
      : <div className="button-row"><Button disabled={cannotPrepare || h3TimingMismatch} onClick={() => void prepare()}>准备新视频任务（冻结当前审核关键帧）</Button></div>}
    </details>
    {error && <small className="notice warning">{error}</small>}
    {visibleJobs.map((job, index) => <article id={index === 0 ? "shot-original" : undefined} className="video-job-card" key={job.id} data-testid={`video-job-${job.id}`}><header><strong>原片 · {shotLabel(frozenShot(job))}</strong><span>{job.selected ? "已选择片段" : job.state === "ingested" ? job.current ? "待审原片" : "保留原片" : job.state}</span></header>
      <small>{isH3Job(job) ? `质量 ${frozenH3Quality(job)} · ` : ""}请求 {job.requestedSeconds} 秒 {job.observed ? `· 实测 ${job.observed.durationSeconds.toFixed(2)} 秒` : ""}</small>
      <small> · {jobStatus(job)}</small>
      <details className="video-technical-history"><summary>审核历史与技术详情</summary>
        <small>选择版本 {job.selectionRevision} · 原片编号 {job.id}</small>
        <pre>{JSON.stringify(frozenVideoSnapshot(job)?.request ?? job.snapshot, null, 2)}</pre>
        {job.reviews.map((review) => <small key={review.id}>审阅：{review.decision === "select" ? "选择" : review.decision === "reopen" ? "重新开放审阅" : "拒绝"}{review.reviewer ? ` · ${review.reviewer}` : ""}{review.note ? ` · ${review.note}` : ""}</small>)}
      </details>
      {job.state === "ingested" && projectId && <ReviewedVideoPlayer kind="原片" style={verifiedVideoGeometry(job.observed)}
        src={plotloomApi.videoJobMediaUrl(projectId, job.id)} testId={`video-job-player-${job.id}`} />}
      <div className="button-row">
        {job.state === "prepared" && <Button disabled={readOnly} onClick={() => void act(() => plotloomApi.submitVideoJob(projectId!, job.id), "提交未完成")}>提交一次</Button>}
        {(job.state === "submitted" || job.state === "retrieve_needed") && <Button disabled={readOnly} onClick={() => void act(() => plotloomApi.reconcileVideoJob(projectId!, job.id), "获取结果未完成")}>获取结果</Button>}
        {["prepared", "dispatching", "submitted", "retrieve_needed", "outcome_unknown"].includes(job.state) && !job.cancelRequestedAt && <Button variant="danger" disabled={readOnly} onClick={() => void act(() => plotloomApi.cancelVideoJob(projectId!, job.id), "取消意图未记录")}>记录取消意图</Button>}
        {job.state === "ingested" && !isH3Job(job) && <Button disabled={readOnly || !job.current} onClick={() => void act(() => plotloomApi.reviewVideoJob(projectId!, job.id, "select", "", "", job.selectionRevision), "选择未完成")}>选择此候选</Button>}
        {canDiscard(job) && <Button variant="danger" disabled={readOnly} onClick={() => {
          requestConfirmation({ title: "永久删除", message: "永久删除此未选择视频候选？此操作不可撤销。", details: `原片：${job.id}`, action: () => act(() => plotloomApi.discardVideoJob(projectId!, job.id, job.selectionRevision), "删除未完成") });
        }}>永久删除</Button>}
        {job.state === "discard_pending" && <Button variant="danger" disabled={readOnly} onClick={() => void act(() => plotloomApi.discardVideoJob(projectId!, job.id, job.selectionRevision), "重试删除未完成")}>重试永久删除</Button>}
      </div>
      {job.state === "ingested" && !job.selected && Boolean(job.segments?.length) && <small>此原片已有保留片段，不能永久删除；原片与片段证据会保留。</small>}
      {isH3Job(job) && projectId && job.state === "ingested" && <div id={job.id === segmentAnchorJobId ? "shot-segment" : undefined}><VideoSegmentReview key={`${projectId}:${job.id}`} projectId={projectId} job={job} readOnly={readOnly} onRefresh={refresh} /></div>}
      {job.error && <small>{job.error}</small>}</article>)}
    <section id="shot-story-preview" className="story-playback-section"><strong>预览 · 用于故事</strong>
      {!videoReadCurrent ? <p role="status">视频状态尚未核实，故事播放暂不可用。</p> : lifecycleStatus === "archived"
        ? <p>项目已归档，故事播放已停用；可在上方查看保留片段。恢复项目后需重新核对播放资格。</p> : <>
      <small>只有当前、已明确选择且可核验的播放片段会进入故事；待审原片不会自动播放。</small>
      {projectId && selectedSequence && <section className="video-sequence-status" data-testid="video-route-sequence-status">
        <strong>已选择路径片段</strong>
        <small>{selectedSequence.jobs.length} 个已选择视频 / {selectedSequence.jobs.length + selectedSequence.missingShotTitles.length} 个路径镜头</small>
        {selectedSequence.missingShotTitles.length > 0 && <small className="notice warning">路径尚不完整：缺少 {selectedSequence.missingShotTitles.join("、")} 的已选择视频。请回到对应镜头，审核片段后确认用于故事。</small>}
      </section>}
      {projectId && selectedSequence && selectedSequence.jobs.length > 0 && selectedSequence.missingShotTitles.length === 0 && <OrderedVideoPlayback projectId={projectId} jobs={selectedSequence.jobs} sourceIdentity={selectedSequence.sourceIdentity} />}
      {projectId && <BranchingVideoPreview projectId={projectId} jobs={jobs} storyboard={storyboard} sceneBeats={sceneBeats} graph={graph} />}
      </>}
    </section>
    {videoReadCurrent && shot && visibleJobs.length === 0 && !unassignedInvalidJobs.length && <small>当前镜头尚无冻结的视频请求。</small>}
    {shot && visibleJobs.some(canDiscard) && <Button variant="danger" disabled={readOnly} onClick={() => {
      const revision = visibleJobs[0]?.selectionRevision ?? 0;
      const ids = visibleJobs.filter(canDiscard).map((job) => job.id);
      requestConfirmation({ title: "批量永久删除", message: `永久删除这 ${ids.length} 个未选择且无保留片段的视频候选？此操作不可撤销。`, details: `镜头：${shot.id}\n原片：${ids.join("\n")}`, action: () => act(() => plotloomApi.discardUnselectedVideoJobs(projectId!, shot.id, ids, revision), "批量删除未完成") });
    }}>删除可清理的未选择候选</Button>}
    {confirmation}
  </Panel>;
}
