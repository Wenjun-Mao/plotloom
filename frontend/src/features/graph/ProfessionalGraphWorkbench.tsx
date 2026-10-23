import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { ReactFlow, Controls, Background, MarkerType, type Node, type Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button, PageHeader } from "../../components";
import type { ProjectBrief, StoryGraph } from "../../types";
import type { WorkspaceSourceReviewRead } from "../../app/workspace/useWorkspaceSourceReview";
import { CanonicalGraphReader } from "./CanonicalGraphReader";
import { GraphDraftDiscard } from "./GraphDraftDiscard";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { GraphPreviewRecovery } from "./GraphPreviewRecovery";
import { GraphNodeDetails } from "./GraphNodeDetails";
import { GraphEdgeDetails } from "./GraphEdgeDetails";
import { GraphCommandDialog } from "./GraphCommandDialog";
import { newGraphId } from "./contracts";
import { GraphSafetyNotice } from "./GraphSafetyNotice";
import { GraphWorkflowActions } from "./GraphWorkflowActions";
import { professionalNavigation, useProfessionalPresentation } from "./ProfessionalPresentation";
import { useGraphActionProjection } from "./graphActionProjection";

export function ProfessionalGraphWorkbench({ projectId, canonical, brief, readOnly, sourceReview, onOpenSource }: { projectId: string; canonical: StoryGraph; brief: ProjectBrief; readOnly: boolean; sourceReview: WorkspaceSourceReviewRead; onOpenSource: () => void }) {
  const owner = useGraphWorkbench(), mapping = owner.draft?.mapping;
  const source = sourceReview.value;
  const actions = useGraphActionProjection(brief, readOnly, sourceReview);
  const presentation = useProfessionalPresentation();
  const [initialViewport] = useState(presentation.viewport);
  const [positions, setPositions] = useState(presentation.positions);
  useEffect(() => {
    if (!mapping) return;
    const identities = new Set(mapping?.topology.nodes.map(node => node.id));
    for (const id of Object.keys(presentation.positions)) if (!identities.has(id)) delete presentation.positions[id];
  }, [mapping, presentation]);
  const [insertionEdge, setInsertionEdge] = useState("");
  const nodes = useMemo<Node[]>(() => mapping?.topology.nodes.map((node, index) => ({ id: node.id,
    position: positions[node.id] ?? { x: (owner.draft?.rowHints[node.id] ?? index) * 240, y: index % 3 * 140 },
    data: { label: mapping.sections.find(section => section.sectionId === node.id)?.title || "待填写节点" },
    selected: owner.selectedNodeId === node.id, focusable: true, selectable: true,
    className: `flow-node ${node.kind}` })) ?? [], [mapping, positions, owner.selectedNodeId]);
  const edges = useMemo<Edge[]>(() => mapping?.topology.edges.flatMap(edge => edge.sourceNodeId && edge.targetNodeId ? [{
    id: edge.id, source: edge.sourceNodeId, target: edge.targetNodeId,
    label: mapping.choices.flatMap(choice => choice.outcomes).find(option => option.outcomeId === edge.id)?.label,
    markerEnd: { type: MarkerType.ArrowClosed },
  }] : []) ?? [], [mapping]);
  const disabled = readOnly || owner.readStatus !== "ready" || owner.busy || owner.stale || Boolean(owner.state?.readOnlyReason);
  const selectFromKeyboard = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const id = (event.target as Element).closest<HTMLElement>(".react-flow__node")?.dataset.id;
    if (!id) return;
    event.preventDefault(); event.stopPropagation(); owner.selectNode(id);
  };
  if (!projectId) return <section className="page"><p>先保存项目，再从来源与大纲建立当前图草稿。</p></section>;
  if (owner.state?.readOnlyReason) return <section className="page"><GraphPreviewRecovery /><p className="notice warning">{owner.state.readOnlyReason}</p><CanonicalGraphReader value={canonical} selectedNodeId={owner.selectedNodeId} onNodeSelect={owner.selectNode} /></section>;
  return <section className="page professional-graph-workbench">
    <PageHeader eyebrow="专业工作台" title="剧情图与结构规则" description="同一剧情图的专业视图：自由查看画布，编辑连接与结构规则。与创作工作台共用图草稿；保存、确认、应用仍是三项独立操作。" />
    <GraphSafetyNotice className="notice warning" />
    <GraphPreviewRecovery />
    {sourceReview.status === "failed" && <p className="notice warning" role="alert">无法读取来源与大纲：{sourceReview.error}<Button onClick={() => void sourceReview.refresh()}>重新读取来源与大纲</Button></p>}
    {owner.stale && <p className="notice warning">规范上下文已变化，图草稿仍保留。<Button disabled={owner.busy || owner.readStatus !== "ready"} onClick={() => void owner.recover()}>在当前版本恢复为新草稿</Button></p>}
    <GraphWorkflowActions
      save={{ disabled: disabled || !mapping, onClick: () => void owner.saveDraft() }}
      confirm={{ disabled: actions.confirmDisabled, onClick: () => source && void owner.confirmMapping(source) }}
      apply={{ disabled: actions.applyDisabled, onClick: () => source && void owner.installMapping(source) }}
      status={actions.status}
    />
    <div className="button-row">
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
      <div className="graph-editor-layout"><div className="graph-canvas" style={{ height: 540 }} onKeyDownCapture={selectFromKeyboard}><ReactFlow nodes={nodes} edges={edges} fitView={!initialViewport} defaultViewport={initialViewport} {...professionalNavigation} nodesDraggable={!disabled}
        nodesConnectable={!disabled} edgesReconnectable={!disabled}
        onNodeClick={(_, node) => owner.selectNode(node.id)}
        onMoveEnd={(_, viewport) => { presentation.viewport = viewport; }}
        onNodeDragStop={(_, node) => { presentation.positions = { ...presentation.positions, [node.id]: node.position }; setPositions(presentation.positions); }}
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
