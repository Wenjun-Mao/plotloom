import { Field } from "../../components";
import type { StoryEdge, StoryGraph, StoryNode } from "../../types";
import { footageModeLabels, storyNodeKindLabels } from "./presentation";

function titleFor(graph: StoryGraph, identity: string): string {
  const node = graph.nodes.find(item => item.id === identity);
  return node?.title || identity;
}

function effectText(edge: StoryEdge): string {
  const facts = Object.entries(edge.stateEffects).map(([key, value]) => `${key}：${typeof value === "string" ? value : JSON.stringify(value)}`);
  const entities = edge.entityStateEffects.map(effect => `${effect.entityType} · ${effect.entityId}：${effect.state}`);
  return [...facts, ...entities].join("\n") || "无状态效果";
}

function edgeDirection(graph: StoryGraph, edge: StoryEdge, node: StoryNode): string {
  const incoming = edge.targetNodeId === node.id;
  return `${incoming ? "输入" : "输出"} · ${titleFor(graph, edge.sourceNodeId)} → ${titleFor(graph, edge.targetNodeId)}`;
}

export function CreatorCanonicalStoryInspector({ graph, nodeId }: { graph: StoryGraph; nodeId: string | null }) {
  const node = graph.nodes.find(item => item.id === nodeId)
    ?? graph.nodes.find(item => item.id === graph.startNodeId)
    ?? graph.nodes[0];
  if (!node) return <p>当前规范图没有可查看的节点。</p>;
  const incident = graph.edges.filter(edge => edge.sourceNodeId === node.id || edge.targetNodeId === node.id);
  const joins = graph.joinContracts.filter(join => join.joinNodeId === node.id);
  return <div className="canonical-creator-story-inspector" data-node-id={node.id}>
    <Field label="章节标题"><input readOnly value={node.title} /></Field>
    <Field label="节点类型"><input readOnly value={storyNodeKindLabels[node.kind]} /></Field>
    <Field label="画面模式"><input readOnly value={footageModeLabels[node.footageMode]} /></Field>
    <Field label="剧情摘要"><textarea readOnly rows={5} value={node.summary} /></Field>

    <section className="canonical-creator-inspector-section">
      <h2>输入与后续</h2>
      {incident.length ? incident.map(edge => <article className="canonical-creator-edge" key={edge.id}>
        <strong>{edgeDirection(graph, edge, node)}</strong>
        <Field label={edge.kind === "choice" ? "选项文字" : "后续关系"}>
          <textarea readOnly rows={2} value={edge.choiceText || (edge.kind === "choice" ? "待填写选项" : "后续")} />
        </Field>
        <Field label="状态效果"><textarea readOnly rows={Math.min(5, Math.max(2, edge.stateEffects && Object.keys(edge.stateEffects).length + edge.entityStateEffects.length))} value={effectText(edge)} /></Field>
      </article>) : <p>没有输入或后续连接。</p>}
    </section>

    {joins.length > 0 && <section className="canonical-creator-inspector-section" aria-label="汇合合同">
      <h2>汇合详情</h2>
      {joins.map(join => <article className="canonical-creator-join" key={join.id}>
        <Field label="输入节点"><textarea readOnly rows={Math.max(2, join.incomingNodeIds.length)} value={join.incomingNodeIds.map(identity => titleFor(graph, identity)).join("\n") || "待连接"} /></Field>
        <Field label="必需状态"><textarea readOnly rows={2} value={join.requiredStateKeys.join("\n") || "无"} /></Field>
        <Field label="允许差异"><textarea readOnly rows={2} value={join.allowedDifferences.join("\n") || "无"} /></Field>
        <Field label="汇合衔接"><textarea readOnly rows={3} value={join.reconciliation} /></Field>
        <Field label="合同备注"><textarea readOnly rows={2} value={join.notes} /></Field>
      </article>)}
    </section>}

    <details className="canonical-creator-technical">
      <summary>稳定身份与完整结构</summary>
      <pre>{JSON.stringify({ node, edges: incident, joins }, null, 2)}</pre>
    </details>
  </div>;
}
