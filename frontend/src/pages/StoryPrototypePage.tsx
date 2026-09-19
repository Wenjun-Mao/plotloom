import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { plotloomApi } from "../api";
import { Badge, ErrorNotice, Spinner } from "../components";
import { derivePrototypeRoutes, episodeForSection, episodesForRoute, prototypeReadiness, type PrototypeEpisode, type PrototypeRoute, type PrototypeScript, type ScriptLine } from "../story-prototype-model";
import type { AcceptedScriptRevision, ArtReviewState, CastReviewState, StoryGraph } from "../types";

type PrototypeNames = { characters: Record<string, string>; props: Record<string, string>; scenes: Record<string, string> };
type PrototypeData = { graph: StoryGraph; script: PrototypeScript; accepted: AcceptedScriptRevision; projectTitle: string; names: PrototypeNames };

/** An opt-in reader: it has no mutation callback and loads canonical owners directly. */
export function StoryPrototypePage() {
  const projectId = new URLSearchParams(window.location.search).get("project") || "";
  const [data, setData] = useState<PrototypeData>();
  const [error, setError] = useState("");
  const [selectedRouteId, setSelectedRouteId] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState("");

  useEffect(() => {
    if (!projectId) return;
    let active = true;
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
        if (!graph || !scriptState.acceptedScript) throw new Error("这个项目尚未同时具备可阅读的故事和已确认剧本。");
        const unavailable = prototypeReadiness(scriptState.status, graphStage?.head, scriptState.acceptedScript.binding);
        if (unavailable) throw new Error(unavailable);
        if (active) setData({ graph, script: scriptState.acceptedScript.script as PrototypeScript, accepted: scriptState.acceptedScript, projectTitle: project.brief.title, names: displayNames(castState, artState) });
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

  if (!projectId) return <PrototypeShell><section className="prototype-empty"><strong>需要一个项目</strong><p>从已有已确认剧本的项目打开此只读阅读页：在地址中加入 <code>?view=story-prototype&amp;project=…</code>。</p></section></PrototypeShell>;
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
        <div><span className="eyebrow">故事 / 剧本</span><h1>{data.projectTitle || "故事与分支"}</h1><p>选择一条路径或一个情节，再按顺序阅读对应剧本。界面为中文；下方英文内容保持原样。</p></div>
        <div className="prototype-version"><strong>当前阅读内容</strong><span>已确认剧本</span><small>这里显示目前确认的版本；不会更改内容，也不会生成素材。</small></div>
      </section>
      <BranchMap graph={data.graph} routes={routes} selectedRoute={selectedRoute} selectedNode={selectedNode} onNode={chooseNode} onRoute={setSelectedRouteId} />
      <section className="prototype-reading" aria-labelledby="prototype-reading-title">
        <div className="prototype-reading-header"><div><span className="eyebrow">阅读顺序</span><h2 id="prototype-reading-title">{routeTitle(selectedRoute)}</h2><p>正在查看：{nodeTitle(data.graph, selectedNode)}。另一种结局会留在它自己的阅读路径里。</p></div><Badge tone="warning">英文原文</Badge></div>
        <div className="script-reader" data-testid="route-reader">
          {episodesForRoute(data.script, selectedRoute).map(({ sectionId, episode }) => <EpisodeCard key={sectionId} graph={data.graph} names={data.names} sectionId={sectionId} episode={episode} focused={sectionId === selectedNode} onFocus={chooseNode} />)}
        </div>
        {selectedEpisode && !selectedRoute.sectionIds.includes(selectedNode) && <EpisodeCard graph={data.graph} names={data.names} sectionId={selectedNode} episode={selectedEpisode} focused onFocus={chooseNode} />}
      </section>
      <footer className="prototype-boundary"><strong>接下来</strong><span>本页只用于阅读故事和剧本，不能在这里保存或生成。制作素材仍需在各自的工作区单独处理。</span></footer>
      <details className="prototype-details"><summary>技术详情</summary><dl><div><dt>剧本版本</dt><dd>r{data.accepted.revision}</dd></div><div><dt>内容标识</dt><dd>{data.accepted.contentHash}</dd></div><div><dt>故事版本</dt><dd>r{data.accepted.binding.graphRevision}</dd></div><div><dt>章节对应</dt><dd>{data.accepted.binding.sectionBindings.map((item) => `${item.sectionId} → E${item.episode.toString().padStart(2, "0")}`).join(" · ")}</dd></div></dl></details>
    </main>
  </PrototypeShell>;
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
  return <article className={`screenplay-section ${focused ? "focused" : ""}`} data-section-id={sectionId}><button type="button" className="screenplay-heading" onClick={() => onFocus(sectionId)}><span>第 {episode.ep.toString().padStart(2, "0")} 节</span><strong>{nodeTitle(graph, sectionId)}</strong><small>{episode.targetSeconds ? `预计朗读时长约 ${episode.targetSeconds} 秒` : "已对应剧本"}</small></button>{episode.hook && <p className="screenplay-context">{episode.hook}</p>}<div className="screenplay-scenes">{episode.scenes?.map((scene, index) => <section className="screenplay-scene" key={`${scene.sceneId || "scene"}:${index}`}><SceneHeading scene={scene} index={index} names={names} /><div className="screenplay-lines">{scene.flow?.map((item, lineIndex) => <ScriptRow key={lineIndex} item={item} names={names} />)}</div></section>)}</div>{episode.cliff && <p className="screenplay-terminal"><span>这一段的结果</span>{episode.cliff}</p>}</article>;
}

function SceneHeading({ scene, index, names }: { scene: NonNullable<PrototypeEpisode["scenes"]>[number]; index: number; names: PrototypeNames }) {
  const title = scene.sceneId ? names.scenes[scene.sceneId] || `场景 ${index + 1}` : `场景 ${index + 1}`;
  const characters = scene.characters?.map((id) => names.characters[id] || id) || [];
  const props = scene.props?.map((id) => names.props[id] || id) || [];
  return <header className="scene-heading"><strong>{title}</strong><div>{scene.lighting && <span>光线：{scene.lighting}</span>}{characters.length > 0 && <span>人物：{characters.join("、")}</span>}{props.length > 0 && <span>道具：{props.join("、")}</span>}</div></header>;
}

function ScriptRow({ item, names }: { item: ScriptLine; names: PrototypeNames }) { return item.line ? <div className="script-row dialogue"><span>{item.speaker ? names.characters[item.speaker] || item.speaker : "角色"}</span><p>{item.line}</p><small>{item.delivery || ""}</small></div> : <div className="script-row action"><span>动作</span><p>{item.action || ""}</p></div>; }
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
