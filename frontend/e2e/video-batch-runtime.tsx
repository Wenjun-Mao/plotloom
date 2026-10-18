import { createRoot } from "react-dom/client";
import { useState, useEffect } from "react";
import { StoryboardPage } from "../src/pages/StoryboardPage";
import { plotloomApi } from "../src/api";
import type { Storyboard, StoryBible, StoryGraph, SceneBeatPlan, StageEnvelopesResponse, ProjectResource, StoryboardReview } from "../src/types";
import { VideoBatchPanel } from "../src/features/video-batch/VideoBatchPanel";
import "../src/styles.css";
import "../src/features/autopilot/autopilot.css";
import "../src/selection-controls.css";
import "../src/creator-ui.css";
const projectId = new URLSearchParams(location.search).get("project")!;
function Host() {
  const [dirty, setDirty] = useState(false);
  const [source, setSource] = useState<{stages:StageEnvelopesResponse;project:ProjectResource;review:StoryboardReview}>();
  const integrated = new URLSearchParams(location.search).get("page") === "storyboard";
  useEffect(() => { if(integrated) void Promise.all([plotloomApi.getStages(projectId),plotloomApi.getProject(projectId),plotloomApi.getStoryboardReview(projectId)]).then(([stages,project,review])=>setSource({stages,project,review})); }, []);
  const payload = (stage:string) => source!.stages.stages.find(item=>item.head.stage===stage)!.payload;

  return <><header className="topbar" style={{ position:"sticky",top:0,zIndex:20,minHeight:64,background:"var(--panel)" }}>Native batch fixture · synthetic provider media</header>
    <section className="recommended-workflow-guide" style={{position:"sticky",top:64,zIndex:19,minHeight:80,background:"var(--panel-2)"}}>完整制作与一次人工确认</section>
    <main style={{padding:"1rem 2rem"}}><p>真实项目/API/审核事务；仅生成传输为离线测试替身。没有业主创作认可。</p>
      <label>与后台完成无关的编辑<textarea aria-label="与后台完成无关的编辑" onChange={() => setDirty(true)} /></label>
      {integrated ? source && <StoryboardPage projectId={projectId} projectRevision={source.project.revision} lifecycleRevision={source.project.lifecycleRevision} lifecycleStatus="active"
        bible={payload("story_bible") as StoryBible} graph={payload("story_graph") as StoryGraph} sceneBeats={payload("scene_beats") as SceneBeatPlan}
        value={payload("storyboard") as Storyboard} revision={source.stages.stages.find(item=>item.head.stage==="storyboard")!.head.revision}
        stale={false} mediaTasks={{}} saving={false} readOnly={false} review={source.review} onSave={async()=>{}} /> : <VideoBatchPanel projectId={projectId} disabled={false} dirty={dirty} onStory={() => { document.getElementById("story-next")?.focus(); }} />}
      <div style={{height:1000}} /><section id="story-next" tabIndex={-1}>故事播放已明确选择全部片段</section>
    </main></>;
}
createRoot(document.getElementById("root")!).render(<Host />);
