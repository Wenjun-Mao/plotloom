import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { plotloomApi } from "../api";
import { Badge, ErrorNotice, Spinner } from "../components";
import { derivePrototypeRoutes, episodeForSection, episodesForRoute, prototypeReadiness, storyboardEpisodesForRoute, storyboardPrototypeReadiness, type PrototypeEpisode, type PrototypeRoute, type PrototypeScript, type PrototypeStoryboard, type PrototypeStoryboardEpisode, type ScriptLine } from "../story-prototype-model";
import type { AcceptedScriptRevision, AcceptedStoryboardReviewRevision, ArtReviewState, CastReviewState, StoryGraph } from "../types";

type PrototypeNames = { characters: Record<string, string>; props: Record<string, string>; scenes: Record<string, string> };
type PrototypeData = { graph: StoryGraph; script: PrototypeScript; accepted: AcceptedScriptRevision; projectTitle: string; names: PrototypeNames };
type StoryboardState =
  | { status: "loading" }
  | { status: "available"; storyboard: PrototypeStoryboard; review: AcceptedStoryboardReviewRevision }
  | { status: "unavailable"; message: string };
type ReaderMode = "screenplay" | "storyboard";

/** An opt-in reader: it has no mutation callback and loads canonical owners directly. */
export function StoryPrototypePage() {
  const projectId = new URLSearchParams(window.location.search).get("project") || "";
  const [data, setData] = useState<PrototypeData>();
  const [error, setError] = useState("");
  const [selectedRouteId, setSelectedRouteId] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [readerMode, setReaderMode] = useState<ReaderMode>("screenplay");
  const [storyboardState, setStoryboardState] = useState<StoryboardState>({ status: "loading" });

  useEffect(() => {
    if (!projectId) return;
    let active = true;
    setData(undefined);
    setError("");
    setStoryboardState({ status: "loading" });
    void Promise.all([
      plotloomApi.getProject(projectId),
      plotloomApi.getStages(projectId),
      plotloomApi.getScript(projectId),
      plotloomApi.getCast(projectId).catch(() => null),
      plotloomApi.getArt(projectId).catch(() => null),
    ])
      .then(([project, stages, scriptState, castState, artState]) => {
        const graphStage = stages.stages.find((stage) => stage.head.stage === "story_graph");
        const graph = graphStage?.payload as StoryGraph | null;
        const acceptedScript = scriptState.acceptedScript;
        if (!graph || !acceptedScript) throw new Error("这个项目尚未同时具备可阅读的故事和已确认剧本。");
        const unavailable = prototypeReadiness(scriptState.status, graphStage?.head, acceptedScript.binding);
        if (unavailable) throw new Error(unavailable);
        const loaded = { graph, script: acceptedScript.script as PrototypeScript, accepted: acceptedScript, projectTitle: project.brief.title, names: displayNames(castState, artState) };
        if (!active) return;
        setData(loaded);
        void plotloomApi.getStoryboardSourceReview(projectId)
          .then((reviewState) => {
            if (!active) return;
            const storyboardUnavailable = storyboardPrototypeReadiness(scriptState.status, graphStage?.head, acceptedScript, reviewState);
            const review = reviewState.acceptedReview;
            if (storyboardUnavailable || !review) {
              setStoryboardState({ status: "unavailable", message: storyboardUnavailable || "当前没有可阅读的已确认分镜评审。" });
              return;
            }
            setStoryboardState({ status: "available", storyboard: review.storyboard as PrototypeStoryboard, review });
          })
          .catch(() => { if (active) setStoryboardState({ status: "unavailable", message: "当前没有可阅读的已确认分镜评审。剧本仍可继续阅读。" }); });
      })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "无法读取故事原型。"); });
    return () => { active = false; };
  }, [projectId]);

  const routes = useMemo(() => data ? derivePrototypeRoutes(data.graph, data.accepted.binding.sectionBindings) : [], [data]);
  const selectedRoute = routes.find((route) => route.id === selectedRouteId) || routes[0];
  const selectedNode = selectedNodeId || selectedRoute?.sectionIds[0] || "";
  useEffect(() => {
    if (routes.length && !routes.some((route) => route.id === selectedRouteId)) setSelectedRouteId(routes[0].id);
  }, [routes, selectedRouteId]);

  const chooseNode = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    // The opening belongs to both paths. Keep a deliberately chosen path until
    // the reader selects a node that is outside it or clicks another branch.
    const containingRoute = selectedRoute?.sectionIds.includes(nodeId)
      ? selectedRoute
      : routes.find((route) => route.sectionIds.includes(nodeId));
    if (containingRoute) setSelectedRouteId(containingRoute.id);
  };

  if (!projectId) return <PrototypeShell><section className="prototype-empty"><strong>需要一个项目</strong><p>从已有已确认剧本和分镜评审的项目打开此只读阅读页：在地址中加入 <code>?view=story-prototype&amp;project=…</code>。</p></section></PrototypeShell>;
  if (error) return <PrototypeShell><ErrorNotice message={error} /></PrototypeShell>;
  if (!data || !selectedRoute) return <PrototypeShell><div className="prototype-loading"><Spinner label="正在读取故事和剧本" /></div></PrototypeShell>;

  const selectedEpisode = episodeForSection(data.script, selectedNode);
  return <PrototypeShell>
    <header className="prototype-header">
      <a className="brand" href={`?project=${encodeURIComponent(projectId)}&stage=source`}><span className="brand-mark">PL</span><span><strong>Plotloom</strong><small>故事与分支 · 原型</small></span></a>
      <div><Badge tone="accent">只读阅读</Badge><Badge tone="ok">已确认剧本</Badge></div>
    </header>
    <main className="story-prototype" data-testid="story-prototype">
      <CreatorStageNavigation projectId={projectId} />
      <section className="prototype-intro">
        <div><span className="eyebrow">故事 / 剧本 / 分镜</span><h1>{data.projectTitle || "故事与分支"}</h1><p>选择一条路径，再选择要阅读的已确认剧本或对应分镜评审。界面为中文；英文源内容保持原样。</p></div>
        <div className="prototype-version"><strong>当前阅读内容</strong><span>已确认剧本{storyboardState.status === "available" ? " / 已确认分镜评审" : ""}</span><small>这里不会更改内容、生成素材或将分镜转为产品镜头。</small></div>
      </section>
      <BranchMap graph={data.graph} routes={routes} selectedRoute={selectedRoute} selectedNode={selectedNode} onNode={chooseNode} onRoute={setSelectedRouteId} />
      <ReaderTabs mode={readerMode} storyboardAvailable={storyboardState.status === "available"} onMode={setReaderMode} />
      {readerMode === "screenplay" ? <ScreenplayReader graph={data.graph} script={data.script} names={data.names} route={selectedRoute} selectedNode={selectedNode} selectedEpisode={selectedEpisode} onFocus={chooseNode} /> : <StoryboardStage graph={data.graph} script={data.script} names={data.names} route={selectedRoute} state={storyboardState} onFocus={chooseNode} projectId={projectId} />}
      <footer className="prototype-boundary"><strong>阅读边界</strong><span>分镜中的时长是评审用预计时长，不代表实际音频或成片时长。此页只用于阅读当前绑定的故事、剧本和分镜评审，不能在这里保存、生成或投产。</span></footer>
      <details className="prototype-details"><summary>技术详情</summary><dl><div><dt>剧本版本</dt><dd>r{data.accepted.revision}</dd></div>{storyboardState.status === "available" && <><div><dt>分镜评审版本</dt><dd>r{storyboardState.review.revision}</dd></div><div><dt>内容标识</dt><dd>{storyboardState.review.contentHash}</dd></div></>}<div><dt>故事版本</dt><dd>r{data.accepted.binding.graphRevision}</dd></div><div><dt>章节对应</dt><dd>{data.accepted.binding.sectionBindings.map((item) => `${item.sectionId} → E${item.episode.toString().padStart(2, "0")}`).join(" · ")}</dd></div></dl></details>
    </main>
  </PrototypeShell>;
}

function ReaderTabs({ mode, storyboardAvailable, onMode }: { mode: ReaderMode; storyboardAvailable: boolean; onMode: (mode: ReaderMode) => void }) {
  return <nav className="reader-tabs" aria-label="阅读内容"><button type="button" className={mode === "screenplay" ? "selected" : ""} aria-pressed={mode === "screenplay"} onClick={() => onMode("screenplay")}>剧本</button><button type="button" className={mode === "storyboard" ? "selected" : ""} aria-pressed={mode === "storyboard"} onClick={() => onMode("storyboard")}>分镜{!storyboardAvailable ? " · 当前不可读" : ""}</button></nav>;
}

function ScreenplayReader({ graph, script, names, route, selectedNode, selectedEpisode, onFocus }: { graph: StoryGraph; script: PrototypeScript; names: PrototypeNames; route: PrototypeRoute; selectedNode: string; selectedEpisode: PrototypeEpisode | undefined; onFocus: (id: string) => void }) {
  return <section className="prototype-reading" aria-labelledby="prototype-reading-title"><div className="prototype-reading-header"><div><span className="eyebrow">剧本阅读</span><h2 id="prototype-reading-title">{routeTitle(route)}</h2><p>正在查看：{nodeTitle(graph, selectedNode)}。另一种结局会留在它自己的阅读路径里。</p></div><Badge tone="warning">英文原文</Badge></div><div className="script-reader" data-testid="route-reader">{episodesForRoute(script, route).map(({ sectionId, episode }) => <EpisodeCard key={sectionId} graph={graph} names={names} sectionId={sectionId} episode={episode} focused={sectionId === selectedNode} onFocus={onFocus} />)}</div>{selectedEpisode && !route.sectionIds.includes(selectedNode) && <EpisodeCard graph={graph} names={names} sectionId={selectedNode} episode={selectedEpisode} focused onFocus={onFocus} />}</section>;
}

function StoryboardStage({ graph, script, names, route, state, onFocus, projectId }: { graph: StoryGraph; script: PrototypeScript; names: PrototypeNames; route: PrototypeRoute; state: StoryboardState; onFocus: (id: string) => void; projectId: string }) {
  if (state.status === "loading") return <section className="prototype-reading"><Spinner label="正在检查当前分镜评审" /></section>;
  if (state.status === "unavailable") return <section className="prototype-reading storyboard-unavailable" data-testid="storyboard-unavailable"><div><span className="eyebrow">分镜阅读</span><h2>当前分镜不可读</h2><p>{state.message}</p></div><p>这不会影响已确认剧本；可切换回“剧本”继续按路径阅读。</p></section>;
  return <><StoryboardReader graph={graph} script={script} names={names} route={route} storyboard={state.storyboard} bindings={state.review.binding.sectionBindings} onFocus={onFocus} /><section className="prototype-report"><details><summary>打开原始上游报告（只读评审证据）</summary><iframe title="original upstream storyboard report" sandbox="" src={plotloomApi.storyboardSourceReviewCandidateReportUrl(projectId, state.review.candidateJobId)} /></details></section></>;
}

function PrototypeShell({ children }: { children: ReactNode }) { return <div className="prototype-shell">{children}</div>; }

function CreatorStageNavigation({ projectId }: { projectId: string }) {
  const workspaceUrl = (stage: string) => `?${new URLSearchParams({ project: projectId, stage }).toString()}`;
  const playUrl = `?${new URLSearchParams({ project: projectId, view: "play" }).toString()}`;
  return <nav className="creator-stage-navigation" aria-label="创作阶段">
    <a href={workspaceUrl("source")}>来源</a>
    <span>故事</span>
    <a href={workspaceUrl("bible")}>人物、地点、道具</a>
    <span className="unavailable" title="此阅读原型尚未提供美术审阅。">美术 · 尚未提供</span>
    <span className="current" aria-current="step">剧本</span>
    <a href={workspaceUrl("storyboard")}>分镜</a>
    <span className="unavailable" title="制作环节尚未接入此阅读原型。">制作 · 尚未提供</span>
    <a href={playUrl}>播放</a>
  </nav>;
}

function BranchMap({ graph, routes, selectedRoute, selectedNode, onNode, onRoute }: { graph: StoryGraph; routes: PrototypeRoute[]; selectedRoute: PrototypeRoute; selectedNode: string; onNode: (nodeId: string) => void; onRoute: (routeId: string) => void }) {
  const start = graph.nodes.find((node) => node.id === graph.startNodeId);
  const edges = graph.edges.filter((edge) => edge.sourceNodeId === graph.startNodeId);
  return <section className="branch-map" aria-labelledby="branch-map-title"><div className="branch-map-heading"><div><span className="eyebrow">分支地图</span><h2 id="branch-map-title">从一个开场，抵达两个不同后果</h2></div><p>选择从故事中来；每张卡都说明选择之后会发生什么。</p></div><div className="branch-canvas">
    {start && <button type="button" className={`branch-node start ${selectedNode === start.id ? "selected" : ""}`} aria-pressed={selectedNode === start.id} onClick={() => onNode(start.id)}><span>开场</span><strong>{start.title}</strong><small>{start.summary}</small></button>}
    <div className="branch-options">{edges.map((edge) => { const target = graph.nodes.find((node) => node.id === edge.targetNodeId); const route = routes.find((item) => item.sectionIds.at(-1) === edge.targetNodeId); const consequence = typeof edge.stateEffects.sourceMapConsequence === "string" ? edge.stateEffects.sourceMapConsequence : "查看结局的变化。"; return target && route ? <button type="button" key={edge.id} className={`branch-choice ${selectedRoute.id === route.id ? "selected" : ""}`} aria-pressed={selectedRoute.id === route.id} onClick={() => { onRoute(route.id); onNode(target.id); }}><span className="branch-line" aria-hidden="true" /><span className="choice-label">选择：{edge.choiceText || target.title}</span><strong>{target.title}</strong><small>后果：{consequence}</small></button> : null; })}</div>
  </div></section>;
}

function EpisodeCard({ graph, names, sectionId, episode, focused, onFocus }: { graph: StoryGraph; names: PrototypeNames; sectionId: string; episode: PrototypeEpisode; focused: boolean; onFocus: (id: string) => void }) {
  return <article className={`screenplay-section ${focused ? "focused" : ""}`} data-section-id={sectionId}><button type="button" className="screenplay-heading" onClick={() => onFocus(sectionId)}><span>第 {episode.ep.toString().padStart(2, "0")} 节</span><strong>{nodeTitle(graph, sectionId)}</strong><small>{episode.targetSeconds ? `章节目标时长 ${episode.targetSeconds} 秒` : "已对应剧本"}</small></button>{episode.hook && <p className="screenplay-context">{episode.hook}</p>}<div className="screenplay-scenes">{episode.scenes?.map((scene, index) => <section className="screenplay-scene" key={`${scene.sceneId || "scene"}:${index}`}><SceneHeading scene={scene} index={index} names={names} /><div className="screenplay-lines">{scene.flow?.map((item, lineIndex) => <ScriptRow key={lineIndex} item={item} names={names} />)}</div></section>)}</div>{episode.cliff && <p className="screenplay-terminal"><span>这一段的结果</span>{episode.cliff}</p>}</article>;
}

function SceneHeading({ scene, index, names }: { scene: NonNullable<PrototypeEpisode["scenes"]>[number]; index: number; names: PrototypeNames }) {
  const title = scene.sceneId ? names.scenes[scene.sceneId] || `场景 ${index + 1}` : `场景 ${index + 1}`;
  const characters = scene.characters?.map((id) => names.characters[id] || id) || [];
  const props = scene.props?.map((id) => names.props[id] || id) || [];
  return <header className="scene-heading"><strong>{title}</strong><div>{scene.lighting && <span>光线：{scene.lighting}</span>}{characters.length > 0 && <span>人物：{characters.join("、")}</span>}{props.length > 0 && <span>道具：{props.join("、")}</span>}</div></header>;
}

function ScriptRow({ item, names }: { item: ScriptLine; names: PrototypeNames }) { return item.line ? <div className="script-row dialogue"><span>{item.speaker ? names.characters[item.speaker] || item.speaker : "角色"}</span><p>{item.line}</p><small>{item.delivery || ""}</small></div> : <div className="script-row action"><span>动作</span><p>{item.action || ""}</p></div>; }

function StoryboardReader({ graph, script, names, route, storyboard, bindings, onFocus }: { graph: StoryGraph; script: PrototypeScript; names: PrototypeNames; route: PrototypeRoute; storyboard: PrototypeStoryboard; bindings: Array<{ sectionId: string; episode: number }>; onFocus: (id: string) => void }) {
  const episodes = storyboardEpisodesForRoute(storyboard, bindings, route);
  return <section className="storyboard-reader" aria-labelledby="storyboard-reader-title" data-testid="storyboard-reader"><div className="prototype-reading-header"><div><span className="eyebrow">分镜阅读</span><h2 id="storyboard-reader-title">按路径查看章节、段落与镜头</h2><p>镜头描述来自已确认分镜评审；没有随附图像时会明确说明。</p></div><Badge tone="accent">只读评审</Badge></div>{episodes.map(({ sectionId, episode }) => <StoryboardEpisodeCard key={sectionId} graph={graph} script={script} names={names} sectionId={sectionId} episode={episode} onFocus={onFocus} />)}</section>;
}

function StoryboardEpisodeCard({ graph, script, names, sectionId, episode, onFocus }: { graph: StoryGraph; script: PrototypeScript; names: PrototypeNames; sectionId: string; episode: PrototypeStoryboardEpisode; onFocus: (id: string) => void }) {
  const segments = episode.segments || [];
  return <article className="storyboard-episode" data-storyboard-section={sectionId}><button type="button" className="storyboard-episode-heading" onClick={() => onFocus(sectionId)}><span>章节 E{(episode.ep || 0).toString().padStart(2, "0")}</span><strong>{nodeTitle(graph, sectionId)}</strong><small>{segments.length ? `${segments.length} 个分段` : "源分镜未提供分段"}</small></button>{segments.map((segment, segmentIndex) => <StoryboardSegment key={segment.id || segmentIndex} segment={segment} index={segmentIndex} scene={sceneForSegment(script, sectionId, segment.sceneIndex, names)} />)}</article>;
}

function StoryboardSegment({ segment, index, scene }: { segment: NonNullable<PrototypeStoryboardEpisode["segments"]>[number]; index: number; scene: string | undefined }) {
  const cuts = segment.cuts || [];
  const duration = cuts.reduce((total, cut) => total + (typeof cut.seconds === "number" ? cut.seconds : 0), 0);
  return <section className="storyboard-segment"><header><div><span>分段 {index + 1}{segment.id ? ` · ${segment.id}` : ""}</span><strong>{scene || "源分镜未提供场景上下文"}</strong></div><small>{duration ? `分段预计 ${formatSeconds(duration)}` : "未提供分段时长"}</small></header><div className="storyboard-cuts">{cuts.length ? cuts.map((cut, cutIndex) => <article className="storyboard-cut" key={cutIndex}><div className="cut-index">镜头 {cutIndex + 1}</div><div className="cut-frame"><span>画面 / 动作</span><p>{cut.frame || "源分镜未提供画面描述。"}</p><small>未提供参考图像</small></div><dl><div><dt>预计时长</dt><dd>{typeof cut.seconds === "number" ? formatSeconds(cut.seconds) : "未提供"}</dd></div><div><dt>景别</dt><dd>{cut.size || "未提供"}</dd></div><div><dt>镜头运动</dt><dd>{cut.camera || "未提供"}</dd></div></dl></article>) : <p className="storyboard-missing">源分镜未提供镜头。</p>}</div>{segment.h3Prompt && <details className="generation-instructions"><summary>查看生成说明</summary><pre>{segment.h3Prompt}</pre></details>}</section>;
}

function sceneForSegment(script: PrototypeScript, sectionId: string, sceneIndex: number | undefined, names: PrototypeNames): string | undefined {
  if (!sceneIndex) return undefined;
  const scene = episodeForSection(script, sectionId)?.scenes?.[sceneIndex - 1];
  if (!scene) return undefined;
  return scene.sceneId ? names.scenes[scene.sceneId] || `场景 ${sceneIndex}` : `场景 ${sceneIndex}`;
}

function formatSeconds(value: number): string { return `${value.toFixed(value % 1 ? 1 : 0)} 秒`; }
function nodeTitle(graph: StoryGraph, nodeId: string): string { return graph.nodes.find((node) => node.id === nodeId)?.title || nodeId; }
function routeTitle(route: PrototypeRoute): string { return route.label || route.sectionIds.join(" → "); }

function displayNames(castState: CastReviewState | null, artState: ArtReviewState | null): PrototypeNames {
  const cast = castState?.acceptedCast?.cast;
  const art = artState?.acceptedArt?.art;
  return {
    characters: namesById(cast?.characters),
    props: namesById(art?.props),
    scenes: namesById(art?.scenes),
  };
}

function namesById(value: unknown): Record<string, string> {
  if (!Array.isArray(value)) return {};
  return Object.fromEntries(value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const entity = item as { id?: unknown; name?: unknown };
    return typeof entity.id === "string" && typeof entity.name === "string" ? [[entity.id, entity.name]] : [];
  }));
}
