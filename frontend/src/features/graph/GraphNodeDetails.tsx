import { useState } from "react";
import { Button, Field } from "../../components";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { GraphEdgeDetails } from "./GraphEdgeDetails";
import { GraphJoinFields } from "./GraphJoinFields";
import { newGraphId } from "./contracts";
import { bypassUnavailableReason } from "./deletionEligibility";
import type { StoryNode } from "../../types";
import { storyNodeKinds, storyNodeKindLabels } from "./presentation";

export function GraphNodeDetails({ disabled }: { disabled: boolean }) {
  const owner = useGraphWorkbench(), mapping = owner.draft?.mapping;
  const node = mapping?.topology.nodes.find(node => node.id === owner.selectedNodeId);
  const section = mapping?.sections.find(section => section.sectionId === owner.selectedNodeId);
  const [deleting, setDeleting] = useState<string | null>(null);
  if (!mapping || !node || !section) return <p>选择一个节点查看内容与精确连接。</p>;
  const patchSection = (patch: Partial<typeof section>) => owner.changeMapping({ ...mapping,
    topologyOrigin: patch.footageMode ? "author" : mapping.topologyOrigin,
    sections: mapping.sections.map(item => item.sectionId === section.sectionId ? { ...item, ...patch } : item) });
  const choice = mapping.choices.find(choice => choice.sectionId === node.id);
  const joins = mapping.topology.joins.filter(join => join.joinNodeId === node.id);
  const incident = mapping.topology.edges.filter(edge => edge.sourceNodeId === node.id || edge.targetNodeId === node.id);
  const bypassReason = bypassUnavailableReason(owner.draft!, node.id);
  const patchChoice = (patch: Partial<NonNullable<typeof choice>>) => owner.changeMapping({ ...mapping,
    choices: mapping.choices.map(item => item.sectionId === node.id ? { ...item, ...patch } : item) });
  return <div className="graph-node-details" data-node-id={node.id}>
    <Field label="章节标题"><input disabled={disabled} value={section.title} onChange={event => patchSection({ title: event.target.value })} /></Field>
    <Field label="剧情摘要"><textarea rows={5} disabled={disabled} value={section.summary} onChange={event => patchSection({ summary: event.target.value })} /></Field>
    {(node.kind === "decision" || node.kind === "join") && <label><input type="checkbox" disabled={disabled} checked={section.footageMode === "footage"} onChange={event => patchSection({ footageMode: event.target.checked ? "footage" : "route_only" })} />包含画面与剧本场景</label>}
    {choice && <section><Field label="播放时的问题"><textarea rows={2} disabled={disabled} value={choice.prompt} onChange={event => patchChoice({ prompt: event.target.value })} /></Field>
      {choice.outcomes.map(option => <section key={option.outcomeId}><Field label="选项文字"><input disabled={disabled} value={option.label} onChange={event => patchChoice({ outcomes: choice.outcomes.map(item => item.outcomeId === option.outcomeId ? { ...item, label: event.target.value } : item) })} /></Field>
        <Field label="选择后的剧情"><textarea rows={2} disabled={disabled} value={option.consequence} onChange={event => patchChoice({ outcomes: choice.outcomes.map(item => item.outcomeId === option.outcomeId ? { ...item, consequence: event.target.value } : item) })} /></Field></section>)}
    </section>}
    <details open><summary>输入与输出连接 · {incident.length}</summary>{incident.map(edge => <GraphEdgeDetails key={edge.id} edge={edge} disabled={disabled} />)}
      <Button disabled={disabled || node.kind === "ending"} onClick={() => void owner.prepareCommand({ operation: "add_edge", edgeId: newGraphId(), sourceNodeId: node.id, targetNodeId: null })}>新增待连接输出</Button>
    </details>
    <details><summary>专业节点与汇合设置</summary>
      <Field label="节点类型"><select disabled={disabled || node.kind === "start"} value={node.kind} onChange={event => {
        const kind = event.target.value as Exclude<StoryNode["kind"], "start">;
        void owner.prepareCommand({ operation: "set_kind", nodeId: node.id, kind, footageMode: kind === "scene" || kind === "ending" ? "footage" : section.footageMode });
      }}>{storyNodeKinds.map(kind => <option key={kind} disabled={kind === "start" && node.kind !== "start"} value={kind}>{storyNodeKindLabels[kind]}</option>)}</select></Field>
      <Button disabled={disabled || node.kind !== "scene"} onClick={() => void owner.prepareCommand({ operation: "set_start", nodeId: node.id })}>明确设为开场</Button>
      <Button disabled={disabled || joins.length > 0} onClick={() => void owner.prepareCommand({ operation: "add_join", joinId: newGraphId(), nodeId: node.id })}>添加汇合合同</Button>
      {joins.map(join => <section key={join.id}><strong>汇合 {join.id}</strong><p>实际输入：{join.incomingNodeIds.join("、") || "待连接"}</p>
        <GraphJoinFields joinId={join.id} disabled={disabled} />
        <Field label="汇合衔接"><textarea rows={3} disabled={disabled} value={mapping.joinReconciliations[join.id]} onChange={event => owner.changeMapping({ ...mapping, joinReconciliations: { ...mapping.joinReconciliations, [join.id]: event.target.value } })} /></Field>
        <Field label="合同备注"><textarea rows={2} disabled={disabled} value={join.notes} onChange={event => owner.changeMapping({ ...mapping, topology: { ...mapping.topology, joins: mapping.topology.joins.map(item => item.id === join.id ? { ...item, notes: event.target.value } : item) } })} /></Field>
        <Button variant="danger" disabled={disabled} onClick={() => void owner.prepareCommand({ operation: "remove_join", joinId: join.id })}>删除此汇合合同</Button>
      </section>)}
    </details>
    <details><summary>身份与来源</summary><p>{node.id} · 原始规划 {mapping.seedTopology.topologyHash} · {mapping.topologyOrigin === "author" ? "作者修改" : "规划种子"}</p></details>
    <Button variant="danger" disabled={disabled || node.id === mapping.topology.startNodeId} onClick={() => setDeleting(node.id)}>删除节点…</Button>
    {deleting === node.id && <section aria-label="选择删除方法"><p>请选择方法。仅删除保留待连接输入和下游内容；安全绕过逐条验证输入，不猜测选择。</p>
      <Button disabled={disabled} onClick={() => { setDeleting(null); void owner.prepareCommand({ operation: "delete", nodeId: node.id, method: "only_delete" }); }}>仅删除，保留待连接</Button>
      {bypassReason ? <p className="muted">安全绕过不可用：{bypassReason}</p> : <Button disabled={disabled} onClick={() => { setDeleting(null); void owner.prepareCommand({ operation: "delete", nodeId: node.id, method: "safe_bypass" }); }}>预览安全绕过</Button>}
      <Button disabled={disabled} onClick={() => setDeleting(null)}>取消删除</Button>
    </section>}
  </div>;
}
