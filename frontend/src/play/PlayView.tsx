import { useEffect, useState } from "react";
import { plotloomApi } from "../api";
import { BranchingVideoPreview } from "../branching-video-preview";
import { ErrorNotice, Spinner } from "../components";
import type { SceneBeatPlan, StoryGraph, Storyboard, VideoJob } from "../types";

type PlayData = {
  title: string;
  graph: StoryGraph;
  sceneBeats: SceneBeatPlan;
  storyboard: Storyboard;
  jobs: VideoJob[];
};

function stagePayload<T>(stages: Awaited<ReturnType<typeof plotloomApi.getStages>>["stages"], stage: string): T | undefined {
  const payload = stages.find((item) => item.head.stage === stage)?.payload;
  return payload === null || payload === undefined ? undefined : payload as T;
}

function workbenchUrl(projectId: string) {
  return `?${new URLSearchParams({ project: projectId, stage: "storyboard" }).toString()}`;
}

/** A read-only projection over the existing project stages and selected media. */
export function PlayView() {
  const projectId = new URLSearchParams(window.location.search).get("project") || "";
  const [data, setData] = useState<PlayData>();
  const [error, setError] = useState("");

  useEffect(() => {
    if (!projectId) {
      setError("播放链接缺少项目标识。");
      return;
    }
    const controller = new AbortController();
    setData(undefined);
    setError("");
    void Promise.all([
      plotloomApi.getProject(projectId, controller.signal),
      plotloomApi.getStages(projectId, controller.signal),
      plotloomApi.getVideoJobs(projectId),
    ]).then(([project, stageResponse, videos]) => {
      if (controller.signal.aborted) return;
      const graph = stagePayload<StoryGraph>(stageResponse.stages, "story_graph");
      const sceneBeats = stagePayload<SceneBeatPlan>(stageResponse.stages, "scene_beats");
      const storyboard = stagePayload<Storyboard>(stageResponse.stages, "storyboard");
      if (!graph || !sceneBeats || !storyboard) {
        setError("这个项目尚未具备可播放的故事、场景或分镜内容。");
        return;
      }
      setData({ title: project.brief.title || "未命名故事", graph, sceneBeats, storyboard, jobs: videos.jobs });
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return;
      setError(reason instanceof Error ? reason.message : "无法加载播放内容。");
    });
    return () => controller.abort();
  }, [projectId]);

  return <main className="play-shell" data-testid="play-view">
    <header className="play-header">
      <a className="brand" href={projectId ? workbenchUrl(projectId) : "?stage=brief"}><div className="brand-mark">PL</div><div><strong>Plotloom</strong><small>PLAY VIEW</small></div></a>
      {projectId && <a className="button quiet" href={workbenchUrl(projectId)}>返回工作台</a>}
    </header>
    <section className="play-stage">
      {error ? <ErrorNotice message={error} /> : !data ? <div className="play-loading"><Spinner label="正在加载故事" /></div> : <>
        <span className="eyebrow">Interactive story</span>
        <h1>{data.title}</h1>
        <p>从开场开始；故事会在分歧处停下，等待你的选择。</p>
        <BranchingVideoPreview projectId={projectId} jobs={data.jobs} storyboard={data.storyboard} sceneBeats={data.sceneBeats} graph={data.graph} title="故事播放" restartLabel="从头开始" />
      </>}
    </section>
  </main>;
}
