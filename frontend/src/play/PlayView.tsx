import { useEffect, useState } from "react";
import { plotloomApi } from "../api";
import { BranchingVideoPreview } from "../branching-video-preview";
import { Button, ErrorNotice, Spinner } from "../components";
import { sourceWorkflowHref } from "../app/workspace/sourceWorkflowNavigation";
import type { SceneBeatPlan, StoryGraph, Storyboard, VideoJob } from "../types";

type PlayData = {
  title: string;
  graph: StoryGraph;
  sceneBeats: SceneBeatPlan;
  storyboard: Storyboard;
  jobs: VideoJob[];
};
type PlaybackPrerequisites = { kind: "missing-production"; missing: string[] };

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
  const [prerequisites, setPrerequisites] = useState<PlaybackPrerequisites>();
  const [readRevision, setReadRevision] = useState(0);

  useEffect(() => {
    if (!projectId) {
      setError("播放链接缺少项目标识。");
      return;
    }
    const controller = new AbortController();
    setData(undefined);
    setError("");
    setPrerequisites(undefined);
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
        setPrerequisites({ kind: "missing-production", missing: [!graph && "故事路线", !sceneBeats && "场景内容", !storyboard && "分镜内容"].filter((value): value is string => Boolean(value)) });
        return;
      }
      setData({ title: project.brief.title || "未命名故事", graph, sceneBeats, storyboard, jobs: videos.jobs });
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return;
      setError(reason instanceof Error ? reason.message : "无法加载播放内容。");
    });
    return () => controller.abort();
  }, [projectId, readRevision]);

  return <main className="play-shell" data-testid="play-view">
    <header className="play-header">
      <a className="brand" href={projectId ? workbenchUrl(projectId) : "?stage=brief"}><div className="brand-mark">PL</div><div><strong>Plotloom</strong><small>故事播放</small></div></a>
      {projectId && <a className="button quiet" href={workbenchUrl(projectId)}>返回工作台</a>}
    </header>
    <section className="play-stage">
      {error ? <><ErrorNotice message={error} />{projectId && <Button variant="quiet" onClick={() => setReadRevision(value => value + 1)}>重新读取播放内容</Button>}</> : prerequisites ? <section aria-labelledby="play-prerequisites-title">
        <h1 id="play-prerequisites-title">故事尚未准备好</h1>
        <p>尚未建立可播放的{prerequisites.missing.join("、")}。确认创作方案后，还需单独建立制作内容；确认方案不会自动完成这一步。</p>
        <a className="button quiet" href={sourceWorkflowHref(projectId, "storyboard-review")}>前往分镜评审与制作</a>
      </section> : !data ? <div className="play-loading"><Spinner label="正在加载故事" /></div> : <>
        <span className="eyebrow">互动故事</span>
        <h1>{data.title}</h1>
        <p>从开场开始；故事会在分歧处停下，等待你的选择。</p>
        <BranchingVideoPreview projectId={projectId} jobs={data.jobs} storyboard={data.storyboard} sceneBeats={data.sceneBeats} graph={data.graph} title="故事播放" restartLabel="从头开始" />
      </>}
    </section>
  </main>;
}
