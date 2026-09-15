import { useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Connection,
  type Edge,
  type Node,
  type XYPosition,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { JoinContract, RequiredEntityState, StoryEdge, StoryGraph, StoryNode, ValidationIssue } from "../types";
import { Button, Field, PageHeader, Panel } from "../components";
import {
  addEdgeWithContractSync,
  addJoinContract,
  addNode,
  graphEntityKey,
  graphFocusKey,
  graphIssueTarget,
  incomingNodeIds,
  parseGraphEntityIdentity,
  patchEdge,
  patchJoinContract,
  patchNode,
  relationshipImpactForEdgeAddition,
  relationshipImpactForEdgeReconnect,
  relationshipImpactForEdgeRemoval,
  reconnectEdgeWithContractSync,
  relationshipImpactForNodeKindChange,
  relationshipImpactForNodeRemoval,
  relationshipImpactGroups,
  retainedSceneReferencesForNode,
  removeEdgeWithCascade,
  removeJoinContract,
  removeNodeWithCascade,
  setStartNode,
  stateEffectRowsToValue,
  stateEffectsToRows,
  type GraphEntityRef,
  type GraphIssueTarget,
  type RetainedSceneReference,
  type RelationshipImpact,
  type StateEffectRow,
  type StateEffectValueKind,
  type StoryNodeSceneReference,
} from "../graph-editor";

type FlowNode = Node<{ label: string; summary: string; kind: StoryNode["kind"] }>;
type FlowEdge = Edge<{ kind: StoryEdge["kind"]; stateEffects: Record<string, unknown> }>;

interface PendingImpact {
  impact: RelationshipImpact;
  retainedSceneReferences: RetainedSceneReference[];
  description: string;
  apply: () => void;
}

const nodeColors: Record<StoryNode["kind"], string> = {
  start: "#e9b45b", decision: "#d9975f", scene: "#7ed4f7", join: "#a88ae8", ending: "#5ac39a",
};

const nodeKinds: Array<StoryNode["kind"]> = ["scene", "decision", "join", "ending"];
const effectKinds: StateEffectValueKind[] = ["string", "number", "boolean", "null", "json"];

function toFlowNode(node: StoryNode, index: number, positions: Record<string, XYPosition>): FlowNode {
  const column = node.kind === "start" ? 0 : node.kind === "ending" ? 4 : node.kind === "join" ? 3 : node.kind === "decision" ? 1 : 2;
  return {
    id: node.id,
    position: positions[node.id] ?? { x: column * 260, y: (index % 4) * 145 },
    data: { label: node.title, summary: node.summary, kind: node.kind },
    className: `flow-node ${node.kind}`,
  };
}

function toFlowEdge(edge: StoryEdge): FlowEdge {
  return {
    id: edge.id,
    source: edge.sourceNodeId,
    target: edge.targetNodeId,
    label: edge.choiceText ?? undefined,
    data: { kind: edge.kind, stateEffects: edge.stateEffects },
    markerEnd: { type: MarkerType.ArrowClosed },
  };
}

function impactDescription(impact: RelationshipImpact, retainedSceneReferenceCount = 0): string {
  const items: string[] = [];
  if (impact.removedNodeIds.length) items.push(`${impact.removedNodeIds.length} 个节点`);
  if (impact.removedEdgeIds.length) items.push(`${impact.removedEdgeIds.length} 条边`);
  if (impact.removedContractIds.length) items.push(`${impact.removedContractIds.length} 个汇合合同`);
  if (impact.updatedContractIds.length) items.push(`${impact.updatedContractIds.length} 个汇合合同的来路清单`);
  const retained = retainedSceneReferenceCount
    ? `另有 ${retainedSceneReferenceCount} 个下游场景引用会被保留并变为过期。`
    : "";
  if (!items.length) return `此操作不删除其他剧情图关系。${retained}`;
  return `此操作会变更：${items.join("、")}。确认后无法从当前草稿自动还原。${retained}`;
}

function stringList(value: string): string[] {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function listValue(value: string[]): string {
  return value.join("\n");
}

function GraphEntityNavigator({ graph, selection, onSelect }: {
  graph: StoryGraph;
  selection: GraphEntityRef;
  onSelect: (entity: GraphEntityRef) => void;
}) {
  const selected = (entity: GraphEntityRef) => selection.kind === entity.kind && selection.id === entity.id;
  return <aside className="graph-entity-navigator" aria-label="剧情图实体列表">
    <header><span className="eyebrow">Accessible selection</span><h2>节点与关系</h2><p>使用此列表可稳定选择画布中的节点、关系和汇合合同。</p></header>
    <section aria-label="剧情节点"><h3>节点</h3>{graph.nodes.map((node) => {
      const entity: GraphEntityRef = { kind: "node", id: node.id };
      return <button type="button" key={node.id} data-testid={`graph-select-node-${node.id}`} aria-pressed={selected(entity)} onClick={() => onSelect(entity)}><strong>{node.title || "未命名节点"}</strong><small>{node.kind} · {node.id}</small></button>;
    })}</section>
    <section aria-label="剧情关系"><h3>关系</h3>{graph.edges.map((edge) => {
      const entity: GraphEntityRef = { kind: "edge", id: edge.id };
      return <button type="button" key={edge.id} data-testid={`graph-select-edge-${edge.id}`} aria-pressed={selected(entity)} onClick={() => onSelect(entity)}><strong>{edge.sourceNodeId} → {edge.targetNodeId}</strong><small>{edge.kind} · {edge.id}</small></button>;
    })}</section>
    <section aria-label="汇合合同"><h3>汇合合同</h3>{graph.joinContracts.length ? graph.joinContracts.map((contract) => {
      const entity: GraphEntityRef = { kind: "contract", id: contract.id };
      return <button type="button" key={contract.id} data-testid={`graph-select-contract-${contract.id}`} aria-pressed={selected(entity)} onClick={() => onSelect(entity)}><strong>{contract.joinNodeId}</strong><small>{contract.id}</small></button>;
    }) : <small className="graph-navigator-empty">尚无汇合合同。</small>}</section>
  </aside>;
}

export function GraphPage({
  value,
  stale,
  saving,
  entityId,
  sceneReferences = [],
  issues = [],
  onEntitySelect,
  onSave,
  onDraftChange,
}: {
  value: StoryGraph;
  stale: boolean;
  saving: boolean;
  entityId?: string;
  /** Read-only downstream references; deletion leaves these records intact. */
  sceneReferences?: readonly StoryNodeSceneReference[];
  issues?: ValidationIssue[];
  onEntitySelect?: (entityId: string) => void;
  onSave: (value: StoryGraph) => Promise<void>;
  onDraftChange?: (value: StoryGraph) => void;
}) {
  // StoryGraph is the sole authored draft. ReactFlow below is only a projection
  // so canvas movement can never silently alter or sanitize the graph contract.
  const [draft, setDraft] = useState(value);
  const [positions, setPositions] = useState<Record<string, XYPosition>>({});
  const [selection, setSelection] = useState<GraphEntityRef>({ kind: "node", id: value.startNodeId });
  const [pendingImpact, setPendingImpact] = useState<PendingImpact | undefined>(undefined);
  const [notice, setNotice] = useState<string | undefined>(undefined);
  const [effectRows, setEffectRows] = useState<StateEffectRow[]>([]);
  const [effectError, setEffectError] = useState<string | undefined>(undefined);
  const [issueFocus, setIssueFocus] = useState<GraphIssueTarget | undefined>(undefined);
  const issueSignature = JSON.stringify(issues);
  const lastIssueSignature = useRef<string | undefined>(undefined);
  const previousEntityId = useRef(entityId);

  const updateDraft = (transform: (current: StoryGraph) => StoryGraph) => {
    setDraft((current) => {
      const next = transform(current);
      onDraftChange?.(next);
      return next;
    });
  };

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    setPositions((current) => Object.fromEntries(
      draft.nodes.map((node, index) => [node.id, current[node.id] ?? toFlowNode(node, index, {}).position]),
    ));
  }, [draft.nodes]);

  const selectEntity = (entity: GraphEntityRef, emit = true) => {
    setSelection(entity);
    setNotice(undefined);
    if (emit) onEntitySelect?.(graphEntityKey(entity));
  };

  const focusIssue = (issue: ValidationIssue) => {
    const target = graphIssueTarget(draft, issue);
    if (!target) return;
    selectEntity(target.entity);
    setIssueFocus(target);
  };

  useEffect(() => {
    const previous = previousEntityId.current;
    previousEntityId.current = entityId;
    if (!entityId) {
      if (!previous) return;
      const fallback: GraphEntityRef = { kind: "node", id: draft.startNodeId };
      if (fallback.kind !== selection.kind || fallback.id !== selection.id) selectEntity(fallback, false);
      return;
    }
    const target = parseGraphEntityIdentity(entityId, draft);
    if (target && (target.kind !== selection.kind || target.id !== selection.id)) selectEntity(target, false);
  }, [draft, entityId, selection.id, selection.kind]);

  useEffect(() => {
    if (!issues.length) { lastIssueSignature.current = undefined; setIssueFocus(undefined); return; }
    if (issueSignature === lastIssueSignature.current) return;
    lastIssueSignature.current = issueSignature;
    const issue = issues.find((candidate) => graphIssueTarget(draft, candidate));
    if (issue) focusIssue(issue);
  }, [draft, issues, issueSignature]);

  useEffect(() => {
    if (!issueFocus || selection.kind !== issueFocus.entity.kind || selection.id !== issueFocus.entity.id) return;
    const key = graphFocusKey(issueFocus.entity, issueFocus.field);
    const target = [...document.querySelectorAll<HTMLElement>("[data-focus-key]")]
      .find((element) => element.dataset.focusKey === key)
      ?? [...document.querySelectorAll<HTMLElement>("[data-focus-key]")]
        .find((element) => (issueFocus.field.startsWith("stateEffects.") || issueFocus.field.startsWith("entityStateEffects.")) && element.dataset.focusKey === graphFocusKey(issueFocus.entity, issueFocus.field.startsWith("stateEffects.") ? "stateEffects" : "entityStateEffects"))
      ?? [...document.querySelectorAll<HTMLElement>("[data-entity-key]")]
        .find((element) => element.dataset.entityKey === graphEntityKey(issueFocus.entity));
    target?.focus();
  }, [effectRows, issueFocus, selection.id, selection.kind]);

  const flowNodes = useMemo(() => draft.nodes.map((node, index) => toFlowNode(node, index, positions)), [draft.nodes, positions]);
  const flowEdges = useMemo(() => draft.edges.map(toFlowEdge), [draft.edges]);
  const selectedNode = selection.kind === "node" ? draft.nodes.find((node) => node.id === selection.id) : undefined;
  const selectedEdge = selection.kind === "edge" ? draft.edges.find((edge) => edge.id === selection.id) : undefined;
  const selectedContract = selection.kind === "contract" ? draft.joinContracts.find((contract) => contract.id === selection.id) : undefined;
  const routeStats = useMemo(() => ({
    decisions: draft.nodes.filter((node) => node.kind === "decision").length,
    endings: draft.nodes.filter((node) => node.kind === "ending").length,
    joins: draft.nodes.filter((node) => node.kind === "join").length,
  }), [draft.nodes]);

  useEffect(() => {
    if (selectedEdge) {
      setEffectRows(stateEffectsToRows(selectedEdge.stateEffects));
      setEffectError(undefined);
    }
  }, [selectedEdge?.id]);

  const requestImpact = (impact: RelationshipImpact, apply: () => void, retainedSceneReferences: RetainedSceneReference[] = []) => {
    if (!impact.removedEdgeIds.length && !impact.removedContractIds.length && !impact.updatedContractIds.length && !retainedSceneReferences.length) {
      apply();
      return;
    }
    setPendingImpact({ impact, retainedSceneReferences, description: impactDescription(impact, retainedSceneReferences.length), apply });
  };

  const createNode = () => {
    const node: StoryNode = { id: crypto.randomUUID(), kind: "scene", title: "新场景", summary: "描述这个节点的叙事目的。" };
    updateDraft((current) => addNode(current, node));
    selectEntity({ kind: "node", id: node.id });
  };

  const connect = (connection: Connection) => {
    if (!connection.source || !connection.target || connection.source === connection.target) return;
    const edge: StoryEdge = {
      id: crypto.randomUUID(), sourceNodeId: connection.source, targetNodeId: connection.target,
      kind: "choice", choiceText: "新选择", stateEffects: {}, entityStateEffects: [],
    };
    requestImpact(relationshipImpactForEdgeAddition(draft, edge), () => {
      updateDraft((current) => addEdgeWithContractSync(current, edge));
      selectEntity({ kind: "edge", id: edge.id });
    });
  };

  const setEffectValue = (rows: StateEffectRow[]) => {
    setEffectRows(rows);
    const parsed = stateEffectRowsToValue(rows);
    if (parsed.errors.length) {
      setEffectError(parsed.errors.map((error) => `第 ${error.index + 1} 行：${error.code}`).join("；"));
      return;
    }
    setEffectError(undefined);
    if (selectedEdge) updateDraft((current) => patchEdge(current, selectedEdge.id, { stateEffects: parsed.value }));
  };

  const createJoinContract = (node: StoryNode) => {
    const incoming = incomingNodeIds(draft, node.id);
    if (incoming.length < 2) {
      setNotice("汇合合同需要至少两条不同来路。");
      return;
    }
    const contract: JoinContract = {
      id: crypto.randomUUID(), joinNodeId: node.id, incomingNodeIds: incoming,
      requiredStateKeys: [], allowedDifferences: [], reconciliation: "", notes: "",
    };
    updateDraft((current) => addJoinContract(current, contract));
    selectEntity({ kind: "contract", id: contract.id });
  };

  const save = () => {
    if (effectError) {
      setNotice("请先修复状态效果中的类型错误，再保存剧情图。");
      return;
    }
    void onSave(draft);
  };

  return <div className="page graph-page" data-testid="graph-editor">
    <PageHeader
      eyebrow="03 · Directed acyclic graph"
      title="剧情 DAG"
      description="稳定 ID 的故事关系编辑器。画布位置只在本地视图保存，绝不混入剧情图合同。"
      actions={<><span className={`stage-chip ${stale ? "stale" : "ready"}`}>{stale ? "待重建" : "DAG 合同有效"}</span><Button variant="primary" disabled={saving} onClick={save}>{saving ? "正在保存…" : "保存剧情图"}</Button></>}
    />
    {notice && <div className="notice error" role="alert">{notice}</div>}
    {issues.length > 0 && <Panel className="form-card" data-testid="graph-validation-issues">
      <div className="section-title"><span>合同问题</span><strong>{issues.length}</strong></div>
      <ul>{issues.map((issue, index) => {
        const target = graphIssueTarget(draft, issue);
        return <li key={`${issue.path}-${index}`}><button type="button" data-entity-key={target ? graphEntityKey(target.entity) : undefined} onClick={() => focusIssue(issue)}>{issue.path}: {issue.message}</button></li>;
      })}</ul>
    </Panel>}
    <div className="metric-strip"><div><small>节点</small><strong>{draft.nodes.length}</strong></div><div><small>决定</small><strong>{routeStats.decisions}</strong></div><div><small>汇合</small><strong>{routeStats.joins}</strong></div><div><small>结局</small><strong>{routeStats.endings}</strong></div></div>
    <div className="graph-workspace">
      <GraphEntityNavigator graph={draft} selection={selection} onSelect={selectEntity} />
      <div className="flow-shell" aria-label="剧情有向无环图编辑器">
        <div className="profile-actions"><Button type="button" onClick={createNode} data-testid="graph-node-add">添加节点</Button></div>
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          onConnect={connect}
          onNodeClick={(_, node) => selectEntity({ kind: "node", id: node.id })}
          onEdgeClick={(_, edge) => selectEntity({ kind: "edge", id: edge.id })}
          onNodeDragStop={(_, node) => setPositions((current) => ({ ...current, [node.id]: node.position }))}
          deleteKeyCode={null}
          fitView minZoom={0.25} maxZoom={1.8} colorMode="dark"
        >
          <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} color="#293340" />
          <MiniMap pannable zoomable nodeColor={(node) => nodeColors[(node.data?.kind as StoryNode["kind"]) || "scene"]} maskColor="rgba(5,8,12,.76)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <Panel className="node-inspector" data-entity-key={graphEntityKey(selection)}>
        <div className="section-title"><span>{selection.kind} inspector</span><strong>{selectedNode?.title ?? selectedEdge?.id ?? selectedContract?.id ?? "选择实体"}</strong></div>
        {selectedNode && <NodeInspector
          node={selectedNode} graph={draft}
          onPatch={(patch) => updateDraft((current) => patchNode(current, selectedNode.id, patch))}
          onKindChange={(kind) => {
            const impact = relationshipImpactForNodeKindChange(draft, selectedNode.id, kind);
            requestImpact(impact, () => updateDraft((current) => {
              const patched = patchNode(current, selectedNode.id, { kind });
              return impact.removedContractIds.length
                ? { ...patched, joinContracts: patched.joinContracts.filter((contract) => !impact.removedContractIds.includes(contract.id)) }
                : patched;
            }));
          }}
          onSetStart={() => requestImpact({ removedNodeIds: [], removedEdgeIds: [], affectedContractIds: [], removedContractIds: [], updatedContractIds: [], startNodeAffected: false }, () => updateDraft((current) => setStartNode(current, selectedNode.id)))}
          onDelete={() => {
            const impact = relationshipImpactForNodeRemoval(draft, selectedNode.id);
            if (impact.startNodeAffected) { setNotice("当前开场节点不能删除；请先将另一个节点设为开场。"); return; }
            const retainedSceneReferences = retainedSceneReferencesForNode(sceneReferences, selectedNode.id);
            requestImpact(impact, () => {
              updateDraft((current) => removeNodeWithCascade(current, selectedNode.id));
              selectEntity({ kind: "node", id: draft.startNodeId });
            }, retainedSceneReferences);
          }}
          onCreateContract={() => createJoinContract(selectedNode)}
          onSelectContract={(id) => selectEntity({ kind: "contract", id })}
        />}
        {selectedEdge && <EdgeInspector
          edge={selectedEdge} nodes={draft.nodes} rows={effectRows} effectError={effectError}
          onPatch={(patch) => updateDraft((current) => patchEdge(current, selectedEdge.id, patch))}
          onReconnect={(reconnect) => {
            try {
              const impact = relationshipImpactForEdgeReconnect(draft, selectedEdge.id, reconnect);
              requestImpact(impact, () => updateDraft((current) => reconnectEdgeWithContractSync(current, selectedEdge.id, reconnect)));
            } catch (error) {
              setNotice(error instanceof Error ? error.message : "无法重连关系");
            }
          }}
          onRowsChange={setEffectValue}
          onDelete={() => requestImpact(relationshipImpactForEdgeRemoval(draft, selectedEdge.id), () => {
            updateDraft((current) => removeEdgeWithCascade(current, selectedEdge.id));
            selectEntity({ kind: "node", id: selectedEdge.sourceNodeId });
          })}
        />}
        {selectedContract && <JoinContractInspector
          contract={selectedContract} incoming={incomingNodeIds(draft, selectedContract.joinNodeId)}
          onPatch={(patch) => updateDraft((current) => patchJoinContract(current, selectedContract.id, patch))}
          onDelete={() => requestImpact({ removedNodeIds: [], removedEdgeIds: [], affectedContractIds: [selectedContract.id], removedContractIds: [selectedContract.id], updatedContractIds: [], startNodeAffected: false }, () => {
            updateDraft((current) => removeJoinContract(current, selectedContract.id));
            selectEntity({ kind: "node", id: selectedContract.joinNodeId });
          })}
        />}
      </Panel>
    </div>
    {pendingImpact && <ImpactDialog pending={pendingImpact} onCancel={() => setPendingImpact(undefined)} onConfirm={() => { const apply = pendingImpact.apply; setPendingImpact(undefined); apply(); }} />}
  </div>;
}

function NodeInspector({ node, graph, onPatch, onKindChange, onSetStart, onDelete, onCreateContract, onSelectContract }: {
  node: StoryNode; graph: StoryGraph; onPatch: (patch: Partial<Omit<StoryNode, "id">>) => void; onKindChange: (kind: StoryNode["kind"]) => void; onSetStart: () => void; onDelete: () => void; onCreateContract: () => void; onSelectContract: (id: string) => void;
}) {
  const contracts = graph.joinContracts.filter((contract) => contract.joinNodeId === node.id);
  const entity: GraphEntityRef = { kind: "node", id: node.id };
  return <>
    <Field label="节点 ID"><input data-focus-key={graphFocusKey(entity, "id")} value={node.id} readOnly /></Field>
    <Field label="类型"><select data-focus-key={graphFocusKey(entity, "kind")} value={node.kind} disabled={node.id === graph.startNodeId} onChange={(event) => onKindChange(event.target.value as StoryNode["kind"])}>
      {node.id === graph.startNodeId && <option value="start">开场</option>}
      {nodeKinds.map((kind) => <option key={kind} value={kind}>{kind}</option>)}
    </select></Field>
    <Field label="标题"><input data-focus-key={graphFocusKey(entity, "title")} value={node.title} onChange={(event) => onPatch({ title: event.target.value })} /></Field>
    <Field label="剧情摘要"><textarea data-focus-key={graphFocusKey(entity, "summary")} rows={6} value={node.summary} onChange={(event) => onPatch({ summary: event.target.value })} /></Field>
    <Button type="button" data-focus-key={graphFocusKey(entity, "startNodeId")} variant="quiet" disabled={node.id === graph.startNodeId} onClick={onSetStart}>设为开场节点</Button>
    <Button type="button" variant="danger" disabled={node.id === graph.startNodeId} onClick={onDelete}>删除节点与关联边</Button>
    {node.kind === "join" && <>
      <Button type="button" onClick={onCreateContract}>添加汇合合同</Button>
      {contracts.map((contract) => <button type="button" key={contract.id} data-entity-key={graphEntityKey({ kind: "contract", id: contract.id })} onClick={() => onSelectContract(contract.id)}>编辑合同 {contract.id}</button>)}
    </>}
  </>;
}

function EdgeInspector({ edge, nodes, rows, effectError, onPatch, onReconnect, onRowsChange, onDelete }: {
  edge: StoryEdge; nodes: StoryNode[]; rows: StateEffectRow[]; effectError?: string; onPatch: (patch: Partial<Omit<StoryEdge, "id" | "sourceNodeId" | "targetNodeId">>) => void; onReconnect: (reconnect: { sourceNodeId: string; targetNodeId: string }) => void; onRowsChange: (rows: StateEffectRow[]) => void; onDelete: () => void;
}) {
  const entity: GraphEntityRef = { kind: "edge", id: edge.id };
  const updateRow = (index: number, patch: Partial<StateEffectRow>) => onRowsChange(rows.map((row, current) => current === index ? { ...row, ...patch } : row));
  const updateEntityEffect = (index: number, patch: Partial<RequiredEntityState>) => onPatch({
    entityStateEffects: edge.entityStateEffects.map((item, current) => current === index ? { ...item, ...patch } : item),
  });
  return <>
    <Field label="边 ID"><input data-focus-key={graphFocusKey(entity, "id")} value={edge.id} readOnly /></Field>
    <Field label="关系"><input value={`${edge.sourceNodeId} → ${edge.targetNodeId}`} readOnly /></Field>
    <div className="field-grid two compact">
      <Field label="起点节点"><select data-focus-key={graphFocusKey(entity, "sourceNodeId")} aria-label="边起点节点" value={edge.sourceNodeId} onChange={(event) => onReconnect({ sourceNodeId: event.target.value, targetNodeId: edge.targetNodeId })}>{nodes.map((node) => <option key={node.id} value={node.id}>{node.title} · {node.id}</option>)}</select></Field>
      <Field label="终点节点"><select data-focus-key={graphFocusKey(entity, "targetNodeId")} aria-label="边终点节点" value={edge.targetNodeId} onChange={(event) => onReconnect({ sourceNodeId: edge.sourceNodeId, targetNodeId: event.target.value })}>{nodes.map((node) => <option key={node.id} value={node.id}>{node.title} · {node.id}</option>)}</select></Field>
    </div>
    <Field label="类型"><select data-focus-key={graphFocusKey(entity, "kind")} value={edge.kind} onChange={(event) => {
      const kind = event.target.value as StoryEdge["kind"];
      onPatch({ kind, choiceText: kind === "continuation" ? null : edge.choiceText || "新选择" });
    }}><option value="choice">choice</option><option value="continuation">continuation</option></select></Field>
    {edge.kind === "choice" && <Field label="选择文案"><input data-focus-key={graphFocusKey(entity, "choiceText")} value={edge.choiceText ?? ""} onChange={(event) => onPatch({ choiceText: event.target.value })} /></Field>}
    <div className="section-title" data-focus-key={graphFocusKey(entity, "stateEffects")} tabIndex={-1}><span>状态效果</span><Button type="button" variant="quiet" onClick={() => onRowsChange([...rows, { key: "", kind: "string", value: "" }])}>添加效果</Button></div>
    {rows.map((row, index) => <div className="field-grid three compact" data-testid="graph-state-effect-row" key={`${index}-${row.key}`}>
      <input data-focus-key={row.key ? graphFocusKey(entity, `stateEffects.${row.key}`) : undefined} aria-label={`状态键 ${index + 1}`} value={row.key} placeholder="state.key" onChange={(event) => updateRow(index, { key: event.target.value })} />
      <select aria-label={`状态类型 ${index + 1}`} value={row.kind} onChange={(event) => updateRow(index, { kind: event.target.value as StateEffectValueKind, value: event.target.value === "null" ? "" : row.value })}>{effectKinds.map((kind) => <option key={kind} value={kind}>{kind}</option>)}</select>
      {row.kind === "boolean" ? <select aria-label={`状态值 ${index + 1}`} value={row.value} onChange={(event) => updateRow(index, { value: event.target.value })}><option value="true">true</option><option value="false">false</option></select> : <input aria-label={`状态值 ${index + 1}`} disabled={row.kind === "null"} value={row.value} placeholder={row.kind === "json" ? '{"key":"value"}' : "value"} onChange={(event) => updateRow(index, { value: event.target.value })} />}
      <Button type="button" variant="quiet" aria-label={`移除状态效果 ${index + 1}`} onClick={() => onRowsChange(rows.filter((_, current) => current !== index))}>移除</Button>
    </div>)}
    {effectError && <div className="notice error" role="alert">{effectError}</div>}
    <div className="section-title" data-focus-key={graphFocusKey(entity, "entityStateEffects")} tabIndex={-1}><span>实体状态效果</span><Button type="button" variant="quiet" onClick={() => onPatch({ entityStateEffects: [...edge.entityStateEffects, { entityType: "character", entityId: "", state: "" }] })}>添加实体状态</Button></div>
    <p className="field-hint">实体状态是故事圣经的显式引用；普通状态效果只保存任意 JSON 事实。</p>
    {edge.entityStateEffects.map((effect, index) => <div className="field-grid three compact" key={`${effect.entityType}:${effect.entityId}:${index}`}>
      <select aria-label={`实体状态类型 ${index + 1}`} value={effect.entityType} onChange={(event) => updateEntityEffect(index, { entityType: event.target.value as RequiredEntityState["entityType"] })}><option value="character">character</option><option value="location">location</option><option value="prop">prop</option></select>
      <input data-focus-key={graphFocusKey(entity, `entityStateEffects.${index}.entityId`)} aria-label={`实体状态 ID ${index + 1}`} value={effect.entityId} placeholder="Bible entity ID" onChange={(event) => updateEntityEffect(index, { entityId: event.target.value })} />
      <input data-focus-key={graphFocusKey(entity, `entityStateEffects.${index}.state`)} aria-label={`实体状态值 ${index + 1}`} value={effect.state} placeholder="Allowed state" onChange={(event) => updateEntityEffect(index, { state: event.target.value })} />
      <Button type="button" variant="quiet" aria-label={`移除实体状态 ${index + 1}`} onClick={() => onPatch({ entityStateEffects: edge.entityStateEffects.filter((_, current) => current !== index) })}>移除</Button>
    </div>)}
    <Button type="button" variant="danger" onClick={onDelete}>删除关系</Button>
  </>;
}

function JoinContractInspector({ contract, incoming, onPatch, onDelete }: {
  contract: JoinContract; incoming: string[]; onPatch: (patch: Partial<Omit<JoinContract, "id" | "joinNodeId" | "incomingNodeIds">>) => void; onDelete: () => void;
}) {
  const entity: GraphEntityRef = { kind: "contract", id: contract.id };
  return <>
    <Field label="合同 ID"><input data-focus-key={graphFocusKey(entity, "id")} value={contract.id} readOnly /></Field>
    <Field label="汇合节点"><input data-focus-key={graphFocusKey(entity, "joinNodeId")} value={contract.joinNodeId} readOnly /></Field>
    <Field label="当前来路 ID"><textarea data-focus-key={graphFocusKey(entity, "incomingNodeIds")} rows={Math.max(2, incoming.length)} value={listValue(incoming)} readOnly /></Field>
    <Field label="必须一致的状态键" hint="每行一个键"><textarea data-focus-key={graphFocusKey(entity, "requiredStateKeys")} rows={4} value={listValue(contract.requiredStateKeys)} onChange={(event) => onPatch({ requiredStateKeys: stringList(event.target.value) })} /></Field>
    <Field label="允许差异" hint="每行一项"><textarea data-focus-key={graphFocusKey(entity, "allowedDifferences")} rows={4} value={listValue(contract.allowedDifferences)} onChange={(event) => onPatch({ allowedDifferences: stringList(event.target.value) })} /></Field>
    <Field label="汇合处理"><textarea data-focus-key={graphFocusKey(entity, "reconciliation")} rows={4} value={contract.reconciliation} onChange={(event) => onPatch({ reconciliation: event.target.value })} /></Field>
    <Field label="备注"><textarea data-focus-key={graphFocusKey(entity, "notes")} rows={3} value={contract.notes} onChange={(event) => onPatch({ notes: event.target.value })} /></Field>
    <Button type="button" variant="danger" onClick={onDelete}>删除汇合合同</Button>
  </>;
}

function ImpactDialog({ pending, onCancel, onConfirm }: { pending: PendingImpact; onCancel: () => void; onConfirm: () => void }) {
  const groups = relationshipImpactGroups(pending.impact);
  return <div className="modal" role="dialog" aria-modal="true" aria-label="关系影响确认">
    <button className="modal-backdrop" aria-label="取消关系变更" onClick={onCancel} />
    <section className="modal-card compact">
      <header><div><span>Relationship impact</span><h2>关系影响确认</h2></div></header>
      <div className="modal-body"><p>{pending.description}</p><p>以下稳定 ID 会被删除或重写；请逐项确认。</p><ul className="relationship-impact-list">{groups.map((group) => <li key={group.key}><strong>{group.label}</strong><ul>{group.ids.map((id) => <li key={id}><code>{id}</code></li>)}</ul></li>)}{pending.retainedSceneReferences.length > 0 && <li><strong>保留并标为过期的下游场景</strong><p>这些 SceneBeat 记录不会被隐藏删除；保存剧情图后请在场景节拍阶段显式修复其失效引用。</p><ul>{pending.retainedSceneReferences.map((reference) => <li key={reference.sceneId}><code>{reference.sceneId}</code> · {reference.title || "未命名场景"}<small>{reference.path}</small></li>)}</ul></li>}</ul></div>
      <footer><Button type="button" variant="quiet" onClick={onCancel}>取消</Button><Button type="button" variant="danger" onClick={onConfirm}>确认变更</Button></footer>
    </section>
  </div>;
}
