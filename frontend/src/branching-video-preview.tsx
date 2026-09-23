import { useEffect, useMemo, useRef, useState } from "react";
import type { SceneBeatPlan, StoryEdge, StoryGraph, StoryNode, Storyboard, VideoJob } from "./types";
import { plotloomApi } from "./api";
import { Button } from "./components";

type FrozenShot = { id?: string; title?: string; sceneId?: string };

function frozenShot(job: VideoJob): FrozenShot {
  const candidate = job.snapshot.shot;
  return candidate && typeof candidate === "object" ? candidate as FrozenShot : {};
}

export type BranchingPreviewNode = {
  node: StoryNode;
  jobs: VideoJob[];
  missingShotTitles: string[];
  outgoing: StoryEdge[];
};

export type BranchingPreviewManifest = {
  identity: string;
  nodes: Map<string, BranchingPreviewNode>;
};

/**
 * This is deliberately a structural projection. Edge effects and join prose
 * remain authoring data, not an invented browser state machine.
 */
export function branchingPreviewManifest(
  projectId: string,
  jobs: VideoJob[],
  storyboard: Storyboard,
  sceneBeats: SceneBeatPlan,
  graph: StoryGraph,
): BranchingPreviewManifest {
  const selectedByShot = new Map<string, VideoJob[]>();
  jobs.forEach((job) => {
    const shot = frozenShot(job);
    if (job.projectId !== projectId || job.state !== "ingested" || !job.current || !job.selected || !job.playbackSegment?.current || !job.playbackSegment.selected || !shot.id || !shot.sceneId) return;
    selectedByShot.set(shot.id, [...(selectedByShot.get(shot.id) || []), job]);
  });
  const nodes = new Map<string, BranchingPreviewNode>();
  graph.nodes.forEach((node) => {
    const shots = sceneBeats.scenes
      .filter((scene) => scene.storyNodeId === node.id)
      .sort((left, right) => left.order - right.order)
      .flatMap((scene) => storyboard.shots
        .filter((shot) => shot.sceneId === scene.id)
        .sort((left, right) => left.order - right.order));
    const jobsForNode = shots.flatMap((shot) => (selectedByShot.get(shot.id) || [])
      .filter((job) => frozenShot(job).sceneId === shot.sceneId && job.playbackSegment?.authoredDurationUnits === shot.durationUnits)
      .sort((left, right) => left.id.localeCompare(right.id)));
    const missingShotTitles = shots
      .filter((shot) => !(selectedByShot.get(shot.id) || []).some((job) => frozenShot(job).sceneId === shot.sceneId && job.playbackSegment?.authoredDurationUnits === shot.durationUnits))
      .map((shot) => shot.title || shot.id);
    nodes.set(node.id, {
      node,
      jobs: jobsForNode,
      missingShotTitles,
      outgoing: graph.edges.filter((edge) => edge.sourceNodeId === node.id),
    });
  });
  const identity = JSON.stringify({
    projectId,
    start: graph.startNodeId,
    nodes: graph.nodes.map(({ id, kind }) => [id, kind]),
    edges: graph.edges.map(({ id, sourceNodeId, targetNodeId, kind, choiceText }) => [id, sourceNodeId, targetNodeId, kind, choiceText]),
    scenes: sceneBeats.scenes.map(({ id, storyNodeId, order }) => [id, storyNodeId, order]),
    shots: storyboard.shots.map(({ id, sceneId, order }) => [id, sceneId, order]),
    media: jobs.map((job) => [job.id, job.projectId, job.state, job.current, job.selected, frozenShot(job).id, frozenShot(job).sceneId, job.playbackSegment?.id, job.playbackSegment?.derivativeHash]),
  });
  return { identity, nodes };
}

export function BranchingVideoPreview({ projectId, jobs, storyboard, sceneBeats, graph, title = "暂停选择分支预览", restartLabel = "重新开始分支预览" }: {
  projectId: string;
  jobs: VideoJob[];
  storyboard: Storyboard;
  sceneBeats: SceneBeatPlan;
  graph: StoryGraph;
  title?: string;
  restartLabel?: string;
}) {
  const manifest = useMemo(
    () => branchingPreviewManifest(projectId, jobs, storyboard, sceneBeats, graph),
    [projectId, jobs, storyboard, sceneBeats, graph],
  );
  const player = useRef<HTMLVideoElement>(null);
  const transitionRef = useRef("");
  const handledMediaRef = useRef("");
  const autoplayedMediaRef = useRef("");
  const mediaFailureRef = useRef<string | null>(null);
  const currentMediaIdentityRef = useRef("");
  const [nodeId, setNodeId] = useState(graph.startNodeId);
  const [episode, setEpisode] = useState(0);
  const [visit, setVisit] = useState(0);
  const [clipIndex, setClipIndex] = useState(0);
  const [nodeComplete, setNodeComplete] = useState(false);
  const [shouldAutoplay, setShouldAutoplay] = useState(false);
  const [mediaFailure, setMediaFailure] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  const [playbackError, setPlaybackError] = useState("");
  const node = manifest.nodes.get(nodeId);
  const incompleteShots = [...manifest.nodes.values()].flatMap((item) => item.missingShotTitles);
  const current = node?.jobs[clipIndex];
  const nodeIdentity = `${manifest.identity}:${episode}:${visit}:${nodeId}`;
  const mediaIdentity = current ? `${nodeIdentity}:${current.id}` : "";
  currentMediaIdentityRef.current = mediaIdentity;

  useEffect(() => {
    setNodeId(graph.startNodeId);
    setVisit(0);
    setClipIndex(0);
    setNodeComplete(false);
    setShouldAutoplay(false);
    setMediaFailure(null);
    setHistory([]);
    setPlaybackError("");
    transitionRef.current = "";
    handledMediaRef.current = "";
    autoplayedMediaRef.current = "";
    mediaFailureRef.current = null;
  }, [manifest.identity, graph.startNodeId]);

  useEffect(() => {
    // Capture the committed element. On a keyed replacement React first mounts
    // the next media element, while this cleanup still pauses only the exact
    // superseded source rather than racing its next play() request.
    const active = player.current;
    return () => { active?.pause(); };
  }, [mediaIdentity]);

  const moveTo = (edge: StoryEdge, autoplay: boolean) => {
    if (transitionRef.current === nodeIdentity) return;
    transitionRef.current = nodeIdentity;
    setHistory((currentHistory) => [...currentHistory, edge.id]);
    setNodeId(edge.targetNodeId);
    setVisit((currentVisit) => currentVisit + 1);
    setClipIndex(0);
    if (autoplay) autoplayedMediaRef.current = "";
    setNodeComplete(false);
    setShouldAutoplay(autoplay);
    setMediaFailure(null);
    mediaFailureRef.current = null;
    setPlaybackError("");
  };
  const finishNode = (autoplaySuccessor: boolean) => {
    if (!node || incompleteShots.length || mediaFailureRef.current || transitionRef.current === nodeIdentity) return;
    if (node.node.kind === "decision" || node.node.kind === "ending" || node.outgoing.length !== 1) {
      setShouldAutoplay(false);
      setNodeComplete(true);
      return;
    }
    moveTo(node.outgoing[0], autoplaySuccessor);
  };

  useEffect(() => {
    if (!node || node.jobs.length || incompleteShots.length) return;
    // An empty structural chain may select the first playable node, but it
    // never manufactures the initial user gesture required to start media.
    finishNode(false);
  }, [nodeIdentity, node]); // Empty structural nodes may continue; missing media never does.

  useEffect(() => {
    const active = player.current;
    if (!shouldAutoplay || !mediaIdentity || !active || autoplayedMediaRef.current === mediaIdentity) return;
    autoplayedMediaRef.current = mediaIdentity;
    setShouldAutoplay(false);
    setMediaFailure(null);
    mediaFailureRef.current = null;
    void Promise.resolve(active.play()).catch((reason: unknown) => {
      if (player.current !== active || currentMediaIdentityRef.current !== mediaIdentity) return;
      const detail = reason instanceof Error && reason.message ? `：${reason.message}` : "";
      setPlaybackError(`无法自动播放下一镜头${detail}`);
    });
  }, [mediaIdentity, shouldAutoplay]);

  if (!node) {
    return <section className="video-sequence" data-testid="branching-video-preview">
      <strong>分支预览不可用</strong><small className="notice warning">起始节点不在当前 StoryGraph 中。</small>
    </section>;
  }
  const isDecision = node.node.kind === "decision" || node.outgoing.length > 1;
  const isEnding = node.node.kind === "ending" || node.outgoing.length === 0;
  const missingMedia = [...new Set([...incompleteShots, ...(mediaFailure ? [mediaFailure] : [])])];
  const play = () => {
    const active = player.current;
    if (!active || !mediaIdentity) {
      setPlaybackError("播放器尚未准备完成");
      return;
    }
    setPlaybackError("");
    void Promise.resolve(active.play()).catch((reason: unknown) => {
      if (player.current !== active || currentMediaIdentityRef.current !== mediaIdentity) return;
      const detail = reason instanceof Error && reason.message ? `：${reason.message}` : "";
      setPlaybackError(`无法播放当前镜头${detail}`);
    });
  };
  const restart = () => {
    transitionRef.current = "";
    handledMediaRef.current = "";
    autoplayedMediaRef.current = "";
    mediaFailureRef.current = null;
    setNodeId(graph.startNodeId);
    setEpisode((currentEpisode) => currentEpisode + 1);
    setVisit(0);
    setClipIndex(0);
    setNodeComplete(false);
    setShouldAutoplay(false);
    setMediaFailure(null);
    setHistory([]);
    setPlaybackError("");
  };
  const advanceClip = (endedIdentity: string | undefined) => {
    if (endedIdentity !== mediaIdentity || mediaFailureRef.current || handledMediaRef.current === endedIdentity || transitionRef.current === nodeIdentity) return;
    handledMediaRef.current = endedIdentity;
    if (clipIndex + 1 < node.jobs.length) {
      autoplayedMediaRef.current = "";
      setShouldAutoplay(true);
      setClipIndex((index) => index + 1);
      return;
    }
    finishNode(true);
  };
  return <section className="video-sequence" data-testid="branching-video-preview">
    <strong>{title}</strong>
    <small>当前节点：{node.node.title || node.node.id}。选择历史：{history.length ? history.join(" → ") : "尚未选择"}</small>
    {missingMedia.length > 0 && <small className="notice warning" data-testid="branching-missing-media">此节点缺少当前可用媒体：{missingMedia.join("、")}。预览不会跳过或生成缺失镜头。</small>}
    {!missingMedia.length && current && <>
      <video
        key={mediaIdentity}
        controls
        preload="metadata"
        ref={player}
        src={plotloomApi.selectedVideoPlaybackUrl(projectId, current.id)}
        data-testid={`branching-video-job-${current.id}`}
        data-playback-identity={mediaIdentity}
        onEnded={(event) => advanceClip(event.currentTarget.dataset.playbackIdentity)}
        onError={(event) => {
          if (event.currentTarget.dataset.playbackIdentity !== mediaIdentity || currentMediaIdentityRef.current !== mediaIdentity) return;
          const failure = frozenShot(current).title || frozenShot(current).id || current.id;
          mediaFailureRef.current = failure;
          setShouldAutoplay(false);
          setMediaFailure(failure);
        }}
      />
      <small>节点镜头 {clipIndex + 1}/{node.jobs.length}。{isDecision || isEnding ? "最后一帧停留，等待明确操作。" : "单一路径完成后继续。"}</small>
      <div className="button-row"><Button onClick={play}>播放当前</Button></div>
    </>}
    {!missingMedia.length && !current && <small>此节点没有已编排镜头。</small>}
    {playbackError && <small className="notice warning" role="status">{playbackError}</small>}
    {!missingMedia.length && nodeComplete && isDecision && <div className="button-row" data-testid="branching-choices">
      {node.outgoing.map((edge) => <Button key={edge.id} onClick={() => moveTo(edge, true)}>{edge.choiceText || `前往 ${manifest.nodes.get(edge.targetNodeId)?.node.title || edge.targetNodeId}`}</Button>)}
    </div>}
    {!missingMedia.length && nodeComplete && isEnding && <div className="button-row"><Button onClick={restart}>{restartLabel}</Button></div>}
  </section>;
}
