import { useMemo, useState } from "react";
import {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Connection,
  type Edge,
  type Node,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { StoryGraph, StoryNode } from "../types";
import { Button, Field, PageHeader, Panel } from "../components";

type GraphNode = Node<{ label: string; summary: string; kind: StoryNode["kind"] }>;

const nodeColors: Record<StoryNode["kind"], string> = {
  start: "#e9b45b",
  decision: "#d9975f",
  scene: "#7ed4f7",
  join: "#a88ae8",
  ending: "#5ac39a",
};

function toFlowNode(node: StoryNode, index: number): GraphNode {
  const column = node.kind === "start" ? 0 : node.kind === "ending" ? 4 : node.kind === "join" ? 3 : node.kind === "decision" ? 1 : 2;
  return { id: node.id, position: { x: column * 260, y: (index % 4) * 145 }, data: { label: node.title, summary: node.summary, kind: node.kind }, className: `flow-node ${node.kind}` };
}

export function GraphPage({ value, stale, saving, onSave }: { value: StoryGraph; stale: boolean; saving: boolean; onSave: (value: StoryGraph) => Promise<void> }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<GraphNode>(value.nodes.map(toFlowNode));
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(value.edges.map((edge) => ({ id: edge.id, source: edge.sourceNodeId, target: edge.targetNodeId, label: edge.choiceText, data: { kind: edge.kind, stateEffects: edge.stateEffects }, markerEnd: { type: MarkerType.ArrowClosed } })));
  const [selectedId, setSelectedId] = useState(value.startNodeId);
  const selected = nodes.find((node) => node.id === selectedId);
  const routeStats = useMemo(() => ({ decisions: nodes.filter((node) => node.data.kind === "decision").length, endings: nodes.filter((node) => node.data.kind === "ending").length, joins: nodes.filter((node) => node.data.kind === "join").length }), [nodes]);
  const connect = (connection: Connection) => setEdges((current) => addEdge({ ...connection, id: crypto.randomUUID(), label: "新选择", data: { kind: "choice", stateEffects: {} }, markerEnd: { type: MarkerType.ArrowClosed } }, current));
  const patchSelected = (patch: Partial<GraphNode["data"]>) => setNodes((current) => current.map((node) => node.id === selectedId ? { ...node, data: { ...node.data, ...patch }, className: `flow-node ${patch.kind || node.data.kind}` } : node));
  const save = () => onSave({
    startNodeId: value.startNodeId,
    nodes: nodes.map((node) => ({ id: node.id, title: node.data.label, summary: node.data.summary, kind: node.data.kind })),
    edges: edges.filter((edge) => edge.source && edge.target).map((edge) => {
      const kind = edge.data?.kind === "continuation" ? "continuation" : "choice";
      return { id: edge.id, sourceNodeId: edge.source, targetNodeId: edge.target, kind, choiceText: kind === "choice" ? String(edge.label || "新选择") : null, stateEffects: typeof edge.data?.stateEffects === "object" && edge.data.stateEffects !== null ? edge.data.stateEffects as Record<string, unknown> : {} };
    }),
    joinContracts: value.joinContracts,
  });
  return <div className="page graph-page">
    <PageHeader eyebrow="03 · Directed acyclic graph" title="剧情 DAG" description="分支可以汇合，但不可形成环。画布位置只保留在本地视图，不会混入剧情图合同。" actions={<><span className={`stage-chip ${stale ? "stale" : "ready"}`}>{stale ? "待重建" : "DAG 合同有效"}</span><Button variant="primary" disabled={saving} onClick={() => void save()}>{saving ? "正在保存…" : "保存剧情图"}</Button></>} />
    <div className="metric-strip"><div><small>节点</small><strong>{nodes.length}</strong></div><div><small>决定</small><strong>{routeStats.decisions}</strong></div><div><small>汇合</small><strong>{routeStats.joins}</strong></div><div><small>结局</small><strong>{routeStats.endings}</strong></div></div>
    <div className="graph-workspace">
      <div className="flow-shell" aria-label="剧情有向无环图编辑器">
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={connect} onNodeClick={(_, node) => setSelectedId(node.id)} fitView minZoom={0.25} maxZoom={1.8} colorMode="dark">
          <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} color="#293340" />
          <MiniMap pannable zoomable nodeColor={(node) => nodeColors[(node.data?.kind as StoryNode["kind"]) || "scene"]} maskColor="rgba(5,8,12,.76)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <Panel className="node-inspector">
        <div className="section-title"><span>Node inspector</span><strong>{selected?.data.label || "选择节点"}</strong></div>
        {selected && <>
          <Field label="节点 ID"><input value={selected.id} readOnly /></Field>
          <Field label="类型"><select value={selected.data.kind} onChange={(event) => patchSelected({ kind: event.target.value as StoryNode["kind"] })}><option value="start">开场</option><option value="decision">决定</option><option value="scene">场景</option><option value="join">汇合</option><option value="ending">结局</option></select></Field>
          <Field label="标题"><input value={selected.data.label} onChange={(event) => patchSelected({ label: event.target.value })} /></Field>
          <Field label="剧情摘要"><textarea rows={6} value={selected.data.summary} onChange={(event) => patchSelected({ summary: event.target.value })} /></Field>
          <div className="node-position"><span>X {Math.round(selected.position.x)}</span><span>Y {Math.round(selected.position.y)}</span></div>
        </>}
      </Panel>
    </div>
  </div>;
}
