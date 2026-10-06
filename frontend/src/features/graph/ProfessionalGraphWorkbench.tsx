import { useEffect, useMemo, useState } from "react";
import { ReactFlow, Controls, Background, MarkerType, type Node, type Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button, PageHeader } from "../../components";
import { plotloomApi } from "../../api";
import type { SourceOutlineReviewState, StoryGraph } from "../../types";
import { CanonicalGraphReader } from "./CanonicalGraphReader";
import { GraphDraftDiscard } from "./GraphDraftDiscard";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { GraphNodeDetails } from "./GraphNodeDetails";
import { GraphEdgeDetails } from "./GraphEdgeDetails";
import { GraphCommandDialog } from "./GraphCommandDialog";
import { newGraphId } from "./contracts";

export function ProfessionalGraphWorkbench({ projectId, canonical, readOnly, onOpenSource }: { projectId: string; canonical: StoryGraph; readOnly: boolean; onOpenSource: () => void }) {
  const owner = useGraphWorkbench(), mapping = owner.draft?.mapping;
  const [source, setSource] = useState<SourceOutlineReviewState | null>(null);
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [insertionEdge, setInsertionEdge] = useState("");
  useEffect(() => {
    let active = true;
    setSource(null);
    if (projectId) void plotloomApi.getSourceOutline(projectId).then(value => { if (active) setSource(value); });
    return () => { active = false; };
  }, [projectId, owner.state?.bindingHash]);
  const nodes = useMemo<Node[]>(() => mapping?.topology.nodes.map((node, index) => ({ id: node.id,
    position: positions[node.id] ?? { x: (owner.draft?.rowHints[node.id] ?? index) * 240, y: index % 3 * 140 },
    data: { label: mapping.sections.find(section => section.sectionId === node.id)?.title || "待填写节点" },
    className: `flow-node ${node.kind}` })) ?? [], [mapping, positions]);
  const edges = useMemo<Edge[]>(() => mapping?.topology.edges.flatMap(edge => edge.sourceNodeId && edge.targetNodeId ? [{
    id: edge.id, source: edge.sourceNodeId, target: edge.targetNodeId,
    label: mapping.choices.flatMap(choice => choice.outcomes).find(option => option.outcomeId === edge.id)?.label,
    markerEnd: { type: MarkerType.ArrowClosed },
  }] : []) ?? [], [mapping]);
  const disabled = readOnly || owner.busy || owner.stale || Boolean(owner.state?.readOnlyReason);
  if (!projectId) return <section className="page"><p>先保存项目，再从来源与大纲建立当前图草稿。</p></section>;
  if (owner.state?.readOnlyReason) return <section className="page"><p className="notice warning">{owner.state.readOnlyReason}</p><CanonicalGraphReader value={canonical} /></section>;
  return <section className="page professional-graph-workbench">
    <PageHeader eyebrow="专业工作台" title="剧情图与精确合同" description="与创作工作台共用当前图草稿。保存草稿、确认内容与应用路线分别进行。" />
    {owner.error && <p className="notice warning" role="alert">{owner.error}</p>}
    {owner.stale && <p className="notice warning">规范上下文已变化，图草稿仍保留。<Button disabled={owner.busy} onClick={() => void owner.recover()}>在当前版本恢复为新草稿</Button></p>}
    <div className="button-row">
      <Button disabled={disabled || !mapping} onClick={() => void owner.saveDraft()}>保存图草稿</Button>
      <Button disabled={disabled || !source} onClick={() => source && void owner.confirmMapping(source)}>确认图内容</Button>
      <Button disabled={disabled || !source?.acceptedSectionMap} onClick={() => source && void owner.installMapping(source)}>应用到故事路线</Button>
      <Button disabled={disabled || !owner.canUndo} onClick={() => void owner.undo()}>撤销结构修改</Button>
      <Button onClick={onOpenSource}>来源、建议与接受报告</Button>
      <GraphDraftDiscard disabled={disabled || !mapping} />
    </div>
    {mapping && <>
      <div className="button-row"><Button disabled={disabled} onClick={() => void owner.prepareCommand({ operation: "add", nodeId: newGraphId(), kind: "scene", createPendingChoices: false, rowHint: mapping.topology.nodes.length,
        sourceNodeId: null, targetNodeId: null, incomingEdgeId: newGraphId(), outgoingEdgeId: newGraphId() })}>新增未连接剧情节点</Button>
        <select aria-label="插入的精确连接" disabled={disabled} value={insertionEdge} onChange={event => setInsertionEdge(event.target.value)}><option value="">新增未连接步骤，不改变连接</option>{mapping.topology.edges.map(edge => <option key={edge.id} value={edge.id}>{edge.id} · {edge.sourceNodeId || "待定"} → {edge.targetNodeId || "待定"}</option>)}</select>
        <Button disabled={disabled} onClick={() => void owner.prepareCommand({ operation: "insert", nodeId: newGraphId(), kind: "scene", createPendingChoices: false, rowHint: 1, edgeId: insertionEdge || null, continuationEdgeId: newGraphId() })}>插入新一行…</Button>
      </div>
      <div className="graph-editor-layout"><div className="graph-canvas" style={{ height: 540 }}><ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={!disabled}
        nodesConnectable={!disabled} edgesReconnectable={!disabled}
        onNodeClick={(_, node) => owner.selectNode(node.id)}
        onNodeDragStop={(_, node) => setPositions(previous => ({ ...previous, [node.id]: node.position }))}
        onConnect={connection => { if (!disabled && connection.source) void owner.prepareCommand({ operation: "add_edge", edgeId: newGraphId(), sourceNodeId: connection.source, targetNodeId: connection.target }); }}
        onReconnect={(edge, connection) => {
          const old = mapping.topology.edges.find(item => item.id === edge.id);
          if (disabled || !old) return;
          const endpoint = connection.source !== old.sourceNodeId ? "source" : "target";
          void owner.prepareCommand({ operation: "retarget", edgeId: edge.id, endpoint, nodeId: endpoint === "source" ? connection.source : connection.target });
        }}><Background /><Controls /></ReactFlow></div>
        <aside className="panel"><h2>节点详情</h2><GraphNodeDetails disabled={disabled} /></aside>
      </div>
      <details><summary>全部稳定身份与待连接关系</summary>{mapping.topology.nodes.map(node => <Button key={node.id} variant="quiet" onClick={() => owner.selectNode(node.id)}>{mapping.sections.find(section => section.sectionId === node.id)?.title || node.id}</Button>)}
        {mapping.topology.edges.filter(edge => edge.sourceNodeId === null || edge.targetNodeId === null).map(edge => <GraphEdgeDetails key={edge.id} edge={edge} disabled={disabled} />)}
      </details>
    </>}
    <GraphCommandDialog />
  </section>;
}
