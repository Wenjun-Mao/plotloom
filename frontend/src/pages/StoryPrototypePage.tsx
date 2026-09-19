import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { plotloomApi } from "../api";
import { Badge, ErrorNotice, Spinner } from "../components";
import { derivePrototypeRoutes, episodeForSection, episodesForRoute, prototypeReadiness, type PrototypeEpisode, type PrototypeRoute, type PrototypeScript, type ScriptLine } from "../story-prototype-model";
import type { AcceptedScriptRevision, StoryGraph } from "../types";

type PrototypeData = { graph: StoryGraph; script: PrototypeScript; accepted: AcceptedScriptRevision; projectTitle: string };

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
    void Promise.all([plotloomApi.getProject(projectId), plotloomApi.getStages(projectId), plotloomApi.getScript(projectId)])
      .then(([project, stages, scriptState]) => {
        const graphStage = stages.stages.find((stage) => stage.head.stage === "story_graph");
        const graph = graphStage?.payload as StoryGraph | null;
        if (!graph || !scriptState.acceptedScript) throw new Error("这个项目尚未同时具备可读的规范剧情图与已接受剧本。");
        const unavailable = prototypeReadiness(scriptState.status, graphStage?.head, scriptState.acceptedScript.binding);
        if (unavailable) throw new Error(unavailable);
        if (active) setData({ graph, script: scriptState.acceptedScript.script as PrototypeScript, accepted: scriptState.acceptedScript, projectTitle: project.brief.title });
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

  if (!projectId) return <PrototypeShell><section className="prototype-empty"><strong>需要一个项目</strong><p>从已接受 F4 剧本的项目打开此只读原型：在地址中加入 <code>?view=story-prototype&amp;project=…</code>。</p></section></PrototypeShell>;
  if (error) return <PrototypeShell><ErrorNotice message={error} /></PrototypeShell>;
  if (!data || !selectedRoute) return <PrototypeShell><div className="prototype-loading"><Spinner label="正在读取规范故事与剧本" /></div></PrototypeShell>;

  const selectedEpisode = episodeForSection(data.script, selectedNode);
  return <PrototypeShell>
    <header className="prototype-header">
      <a className="brand" href={`?project=${encodeURIComponent(projectId)}&stage=source`}><span className="brand-mark">PL</span><span><strong>Plotloom</strong><small>故事与分支 · 原型</small></span></a>
      <div><Badge tone="accent">只读原型</Badge><Badge tone="ok">已接受剧本 r{data.accepted.revision}</Badge></div>
    </header>
    <main className="story-prototype" data-testid="story-prototype">
      <section className="prototype-intro">
        <div><span className="eyebrow">故事 / 剧本</span><h1>{data.projectTitle || "故事与分支"}</h1><p>先选择一条路径或一个节点，再按阅读顺序查看对应的已接受剧本。界面为中文；下方英文内容保持原样。</p></div>
        <div className="prototype-version"><strong>当前阅读内容</strong><span>已接受剧本 r{data.accepted.revision}</span><small>原始候选报告与当前编辑版本分开保存；这里读取当前已接受剧本，不创建媒体。</small></div>
      </section>
      <BranchMap graph={data.graph} routes={routes} selectedRoute={selectedRoute} selectedNode={selectedNode} onNode={chooseNode} onRoute={setSelectedRouteId} />
      <section className="prototype-reading" aria-labelledby="prototype-reading-title">
        <div className="prototype-reading-header"><div><span className="eyebrow">阅读顺序</span><h2 id="prototype-reading-title">{routeTitle(selectedRoute)}</h2><p>已聚焦 {nodeTitle(data.graph, selectedNode)}。另一条同级结局不会混入此阅读路径。</p></div><Badge tone="warning">英文原文</Badge></div>
        <div className="script-reader" data-testid="route-reader">
          {episodesForRoute(data.script, selectedRoute).map(({ sectionId, episode }) => <EpisodeCard key={sectionId} graph={data.graph} sectionId={sectionId} episode={episode} focused={sectionId === selectedNode} onFocus={chooseNode} />)}
        </div>
        {selectedEpisode && !selectedRoute.sectionIds.includes(selectedNode) && <EpisodeCard graph={data.graph} sectionId={selectedNode} episode={selectedEpisode} focused onFocus={chooseNode} />}
      </section>
      <footer className="prototype-boundary"><strong>下一步边界</strong><span>这是 U2 的可审阅界面原型：它没有保存、接受、生成或播放操作。F5 复核也不会因此创建生产媒体。</span></footer>
      <details className="prototype-details"><summary>技术详情</summary><dl><div><dt>阶段</dt><dd>F4 screenplay</dd></div><div><dt>剧本 hash</dt><dd>{data.accepted.contentHash}</dd></div><div><dt>图版本</dt><dd>r{data.accepted.binding.graphRevision}</dd></div><div><dt>绑定</dt><dd>{data.accepted.binding.sectionBindings.map((item) => `${item.sectionId} → E${item.episode.toString().padStart(2, "0")}`).join(" · ")}</dd></div></dl></details>
    </main>
  </PrototypeShell>;
}

function PrototypeShell({ children }: { children: ReactNode }) { return <div className="prototype-shell">{children}</div>; }

function BranchMap({ graph, routes, selectedRoute, selectedNode, onNode, onRoute }: { graph: StoryGraph; routes: PrototypeRoute[]; selectedRoute: PrototypeRoute; selectedNode: string; onNode: (nodeId: string) => void; onRoute: (routeId: string) => void }) {
  const start = graph.nodes.find((node) => node.id === graph.startNodeId);
  const edges = graph.edges.filter((edge) => edge.sourceNodeId === graph.startNodeId);
  return <section className="branch-map" aria-labelledby="branch-map-title"><div className="branch-map-heading"><div><span className="eyebrow">分支地图</span><h2 id="branch-map-title">从一个开场，抵达两个不同后果</h2></div><p>选项来自规范 StoryGraph；后果来自它的 state effects。</p></div><div className="branch-canvas">
    {start && <button type="button" className={`branch-node start ${selectedNode === start.id ? "selected" : ""}`} aria-pressed={selectedNode === start.id} onClick={() => onNode(start.id)}><span>开场</span><strong>{start.title}</strong><small>{start.summary}</small></button>}
    <div className="branch-options">{edges.map((edge) => { const target = graph.nodes.find((node) => node.id === edge.targetNodeId); const route = routes.find((item) => item.sectionIds.at(-1) === edge.targetNodeId); const consequence = typeof edge.stateEffects.sourceMapConsequence === "string" ? edge.stateEffects.sourceMapConsequence : "查看结局的变化。"; return target && route ? <button type="button" key={edge.id} className={`branch-choice ${selectedRoute.id === route.id ? "selected" : ""}`} aria-pressed={selectedRoute.id === route.id} onClick={() => { onRoute(route.id); onNode(target.id); }}><span className="branch-line" aria-hidden="true" /><span className="choice-label">选择：{edge.choiceText || target.title}</span><strong>{target.title}</strong><small>后果：{consequence}</small></button> : null; })}</div>
  </div></section>;
}

function EpisodeCard({ graph, sectionId, episode, focused, onFocus }: { graph: StoryGraph; sectionId: string; episode: PrototypeEpisode; focused: boolean; onFocus: (id: string) => void }) {
  const lines = episode.scenes?.flatMap((scene) => scene.flow || []) || [];
  return <article className={`screenplay-section ${focused ? "focused" : ""}`} data-section-id={sectionId}><button type="button" className="screenplay-heading" onClick={() => onFocus(sectionId)}><span>章节 {sectionId} · E{episode.ep.toString().padStart(2, "0")}</span><strong>{nodeTitle(graph, sectionId)}</strong><small>{episode.targetSeconds ? `目标 ${episode.targetSeconds} 秒` : "已绑定剧本"}</small></button>{episode.hook && <p className="screenplay-context">{episode.hook}</p>}<div className="screenplay-lines">{lines.map((item, index) => <ScriptRow key={index} item={item} />)}</div>{episode.cliff && <p className="screenplay-terminal"><span>段落状态</span>{episode.cliff}</p>}</article>;
}

function ScriptRow({ item }: { item: ScriptLine }) { return item.line ? <div className="script-row dialogue"><span>{item.speaker || "角色"}</span><p>{item.line}</p><small>{item.delivery || ""}</small></div> : <div className="script-row action"><span>动作</span><p>{item.action || ""}</p></div>; }
function nodeTitle(graph: StoryGraph, nodeId: string): string { return graph.nodes.find((node) => node.id === nodeId)?.title || nodeId; }
function routeTitle(route: PrototypeRoute): string { return route.label || route.sectionIds.join(" → "); }
