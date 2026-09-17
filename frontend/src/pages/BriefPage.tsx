import { useState } from "react";
import type { ProjectBrief, StoryBible, StoryGraph } from "../types";
import { Button, Field, PageHeader, Panel } from "../components";

type BriefPageProps = {
  value: ProjectBrief;
  saving: boolean;
  onSave: (brief: ProjectBrief) => Promise<unknown>;
  onDraftChange?: (brief: ProjectBrief) => void;
  bible?: StoryBible;
  graph?: StoryGraph;
  proposalRunning?: boolean;
  proposalReady?: boolean;
  onGenerateProposal?: (brief: ProjectBrief) => Promise<void>;
  onReviewStage?: (stage: "bible" | "graph") => void;
  onContinueToPlanning?: () => void;
};

const defaultWorkingTitle = "未命名故事";

/**
 * The brief remains the canonical input. This page only composes its first two
 * canonical downstream stages into a review; it does not own proposal state.
 */
export function BriefPage({ value, saving, onSave, onDraftChange, bible, graph, proposalRunning = false, proposalReady = true, onGenerateProposal, onReviewStage, onContinueToPlanning }: BriefPageProps) {
  const [draft, setDraft] = useState(value);
  const set = <K extends keyof ProjectBrief>(key: K, next: ProjectBrief[K]) => setDraft((current) => {
    const updated = { ...current, [key]: next };
    onDraftChange?.(updated); return updated;
  });
  const numeric = <K extends keyof ProjectBrief>(key: K, raw: string) => set(key, Number(raw) as ProjectBrief[K]);
  const canonicalDraft = (): ProjectBrief => ({ ...draft, title: draft.title.trim() || defaultWorkingTitle });
  const hasProposal = Boolean(bible?.logline && graph?.nodes.length);
  const decisions = graph?.nodes.filter((node) => node.kind === "decision") || [];
  const endings = graph?.nodes.filter((node) => node.kind === "ending") || [];
  const graphNodes = new Map(graph?.nodes.map((node) => [node.id, node]) || []);
  const choiceEdges = (graph?.edges || []).filter((edge) => edge.kind === "choice");
  const choiceSources = (graph?.nodes || []).filter((node) => choiceEdges.some((edge) => edge.sourceNodeId === node.id));
  const choicesFor = (nodeId: string) => choiceEdges.filter((edge) => edge.sourceNodeId === nodeId);
  return <div className="page">
    <PageHeader eyebrow="01 · Synopsis → proposal" title="项目简报" description="从梗概生成可审阅故事提案；不会自动生成场景、分镜或媒体。" actions={<><Button variant="quiet" disabled={saving} onClick={() => void onSave(canonicalDraft())}>{saving ? "保存中…" : "保存简报"}</Button>{onGenerateProposal && <Button variant="primary" disabled={saving || proposalRunning || !draft.synopsis.trim()} onClick={() => void onGenerateProposal(canonicalDraft())}>{proposalRunning ? "正在生成提案…" : "生成故事提案"}</Button>}</>} />
    <div className="two-column wide-left">
      <Panel className="form-card">
        <div className="section-title"><span>Required input</span><strong>从一个梗概开始</strong></div>
        <Field label="片名"><input placeholder={defaultWorkingTitle} value={draft.title} onChange={(event) => set("title", event.target.value)} /><small>可选工作片名；留空时保存为“未命名故事”。</small></Field>
        <Field label="故事梗概"><textarea rows={5} value={draft.synopsis} onChange={(event) => set("synopsis", event.target.value)} /></Field>
        <div className="field-grid two">
          <Field label="类型"><input value={draft.genre || ""} onChange={(event) => set("genre", event.target.value)} /></Field>
          <Field label="视觉风格"><input value={draft.visualStyle || ""} onChange={(event) => set("visualStyle", event.target.value)} /></Field>
        </div>
        <div className="field-grid three">
          <Field label="语言"><select value={draft.language} onChange={(event) => set("language", event.target.value)}><option value="zh-CN">简体中文</option><option value="en-US">English</option></select></Field>
          <Field label="画幅"><select value={draft.aspectRatio} onChange={(event) => set("aspectRatio", event.target.value)}><option>16:9</option><option>9:16</option><option>1:1</option></select></Field>
          <Field label="目标游玩时长（秒）"><input type="number" min={30} max={3600} value={draft.targetPlaythroughSeconds} onChange={(event) => numeric("targetPlaythroughSeconds", event.target.value)} /><small>这是创作目标，不是生成后时长的承诺。</small></Field>
        </div>
      </Panel>
      <div className="stack">
        <Panel className="form-card">
          <details>
            <summary>高级生产范围设置</summary>
            <p className="event-detail">仅在需要时调整结构与镜头预算；这些是可编辑的生产默认值。</p>
          <div className="field-grid two">
            <Field label="每路径决定数"><input type="number" min={1} value={draft.decisionPointsPerPath} onChange={(event) => numeric("decisionPointsPerPath", event.target.value)} /></Field>
            <Field label="结局数"><input type="number" min={1} value={draft.endingCount} onChange={(event) => numeric("endingCount", event.target.value)} /></Field>
            <Field label="节点预算"><input type="number" min={3} value={draft.nodeBudget} onChange={(event) => numeric("nodeBudget", event.target.value)} /></Field>
            <Field label="最大出度"><input type="number" min={1} max={6} value={draft.maxOutDegree} onChange={(event) => numeric("maxOutDegree", event.target.value)} /></Field>
            <Field label="期望汇合数"><input type="number" min={0} value={draft.desiredJoinCount} onChange={(event) => numeric("desiredJoinCount", event.target.value)} /></Field>
          </div>
          <div className="range-summary"><span>每场分镜</span><strong>{draft.shotsPerSceneMin}–{draft.shotsPerSceneMax}</strong></div>
          <div className="field-grid two compact">
            <Field label="最少"><input type="number" min={1} value={draft.shotsPerSceneMin} onChange={(event) => numeric("shotsPerSceneMin", event.target.value)} /></Field>
            <Field label="最多"><input type="number" min={draft.shotsPerSceneMin} value={draft.shotsPerSceneMax} onChange={(event) => numeric("shotsPerSceneMax", event.target.value)} /></Field>
          </div>
          </details>
        </Panel>
      </div>
    </div>
    {hasProposal && bible && graph && <div className="stack proposal-review" data-testid="story-proposal-review">
      <Panel>
        <div className="section-title"><span>Reviewable proposal</span><strong>{bible.logline}</strong></div>
        <p>{bible.premise}</p>
        <div className="field-grid two">
          <div><strong>人物</strong><ul>{bible.characters.map((character) => <li key={character.id}>{character.name}{character.role ? ` · ${character.role}` : ""}{character.goal ? `：${character.goal}` : ""}</li>)}</ul></div>
          <div><strong>设定</strong><ul>{bible.locations.map((location) => <li key={location.id}>{location.name}{location.description ? `：${location.description}` : ""}</li>)}</ul></div>
        </div>
      </Panel>
      <Panel>
        <div className="section-title"><span>Branches and endings</span><strong>{decisions.length} 个决定 · {endings.length} 个结局</strong></div>
        {choiceSources.length ? <ul>{choiceSources.map((node) => <li key={node.id}><strong>{node.title}</strong>：{node.summary}<ul>{choicesFor(node.id).map((edge) => { const target = graphNodes.get(edge.targetNodeId); return <li key={edge.id}><strong>{edge.choiceText || "未命名选择"}</strong> → {target?.kind === "ending" ? "结局：" : "节点："}<strong>{target?.title || edge.targetNodeId}</strong>{target?.summary ? `：${target.summary}` : ""}</li>; })}</ul></li>)}</ul> : <p>此提案尚未定义选择节点。</p>}
        {endings.length ? <ul>{endings.map((node) => <li key={node.id}><strong>{node.title}</strong>：{node.summary}</li>)}</ul> : <p>此提案尚未定义结局。</p>}
      </Panel>
      <Panel>
        <div className="section-title"><span>Production scope</span><strong>仅 Story Bible 与剧情 DAG</strong></div>
        <p>已推导：{graph.nodes.length} 个叙事节点、{graph.edges.filter((edge) => edge.kind === "choice").length} 个选择、{endings.length} 个结局。下一阶段仍未生成场景、分镜或媒体。</p>
        <p>计划目标：每条路径约 {draft.targetPlaythroughSeconds} 秒、每场 {draft.shotsPerSceneMin}–{draft.shotsPerSceneMax} 个镜头；这些不是成本或实际时长估算。</p>
        {!proposalReady && <p className="event-detail">提案的上游内容已变更。请重新生成 Story Bible 与剧情 DAG 后，再进入分镜规划；不会覆盖任何下游内容。</p>}
        <div className="button-row"><Button variant="quiet" onClick={() => onReviewStage?.("bible")}>细化人物与设定</Button><Button variant="quiet" onClick={() => onReviewStage?.("graph")}>细化分支与结局</Button>{onContinueToPlanning && <Button variant="primary" disabled={!proposalReady} onClick={onContinueToPlanning}>接受提案，进入分镜规划</Button>}</div>
      </Panel>
    </div>}
  </div>;
}
