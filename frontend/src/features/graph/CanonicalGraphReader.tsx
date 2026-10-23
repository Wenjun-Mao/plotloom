import { useEffect, useRef } from "react";
import { Field } from "../../components";
import { graphEntityKey, graphFocusKey, graphIssueTarget } from "../../graph-editor";
import type { StoryGraph, ValidationIssue } from "../../types";
import { CanonicalGraphCanvas } from "./CanonicalGraphCanvas";
import { footageModeLabels, storyNodeKindLabels } from "./presentation";

export function CanonicalGraphReader({ value, issues = [], onEntitySelect, selectedNodeId, onNodeSelect }: { value: StoryGraph; issues?: ValidationIssue[]; onEntitySelect?: (identity: string) => void; selectedNodeId?: string | null; onNodeSelect?: (identity: string) => void }) {
  const root = useRef<HTMLDivElement>(null), signature = JSON.stringify(issues);
  useEffect(() => {
    const target = issues.map(issue => graphIssueTarget(value, issue)).find(Boolean);
    if (!target) return;
    onEntitySelect?.(graphEntityKey(target.entity));
    const key = graphFocusKey(target.entity, target.field);
    [...(root.current?.querySelectorAll<HTMLElement>("[data-focus-key]") ?? [])].find(element => element.dataset.focusKey === key)?.focus();
  }, [signature, value]);
  return <div ref={root} className="canonical-graph-reader">
    <p>已接受路线 · {value.nodes.length} 个节点 · {value.edges.length} 条连接</p>
    <CanonicalGraphCanvas value={value} presentation="professional" selectedNodeId={selectedNodeId} onNodeSelect={onNodeSelect} />
    <details open><summary>节点、关系与汇合合同</summary>
      {value.nodes.map(node => <section key={node.id}><strong>{node.id} · {storyNodeKindLabels[node.kind]} · {footageModeLabels[node.footageMode]}</strong>
        <Field label="章节标题"><input readOnly value={node.title} data-focus-key={graphFocusKey({ kind: "node", id: node.id }, "title")} /></Field>
        <Field label="剧情摘要"><textarea readOnly value={node.summary} /></Field>
      </section>)}
      {value.edges.map(edge => <section key={edge.id}><strong>{edge.id} · {edge.sourceNodeId} → {edge.targetNodeId}</strong><p>{edge.choiceText}</p>
        {Object.entries(edge.stateEffects).map(([key, value]) => <Field key={key} label={`事实 ${key}`}><input readOnly value={JSON.stringify(value)} data-focus-key={graphFocusKey({ kind: "edge", id: edge.id }, `stateEffects.${key}`)} /></Field>)}
        <pre>{JSON.stringify(edge.entityStateEffects, null, 2)}</pre>
      </section>)}
      {value.joinContracts.map(join => <section key={join.id}><strong>{join.id} · {join.joinNodeId}</strong><pre>{JSON.stringify(join, null, 2)}</pre></section>)}
    </details>
  </div>;
}
