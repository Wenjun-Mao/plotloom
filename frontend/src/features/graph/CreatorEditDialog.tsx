import { useEffect, useRef, useState } from "react";
import { Button, Field } from "../../components";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { newGraphId } from "./contracts";
import type { GraphCommand } from "./contracts";
import { rowConnectionDefaults } from "./creatorLayout";
export type CreatorEdit = { type: "row"; rank: number; nodes: string[] } | { type: "insert"; rank: number; edgeId: string | null } | { type: "connection"; nodeId: string; endpoint: "source" | "target"; edgeId: string | null; targetNodeId?: string };

export function CreatorEditDialog({ action, onClose }: { action: CreatorEdit; onClose: () => void }) {
  const owner = useGraphWorkbench(), draft = owner.draft!, topology = draft.mapping.topology;
  const defaults = action.type === "row" ? rowConnectionDefaults(draft, action.nodes) : { parent: null, target: null };
  const [kind, setKind] = useState<"scene" | "decision" | "join" | "ending">("scene"), [source, setSource] = useState(defaults.parent || ""), [target, setTarget] = useState(defaults.target || "");
  const [reuse, setReuse] = useState(""), [edgeId, setEdge] = useState(action.type === "row" ? "" : action.edgeId || ""), [endpointNode, setEndpointNode] = useState(action.type === "connection" ? action.targetNodeId || "" : "");
  const [chosenEdge, setChosenEdge] = useState("");
  const [scaffold, setScaffold] = useState(true), dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  const title = (id: string) => draft.mapping.sections.find(section => section.sectionId === id)?.title || "待填写节点";
  const availableEdges = action.type === "connection" ? topology.edges.filter(edge => action.endpoint === "target" ? edge.sourceNodeId === action.nodeId : edge.targetNodeId === action.nodeId) : topology.edges;
  const detached = topology.nodes.filter(node => node.id !== topology.startNodeId && !topology.edges.some(edge => edge.targetNodeId === node.id && edge.sourceNodeId));
  const prepare = () => {
    let command: GraphCommand;
    if (action.type === "row") {
      command = reuse ? { operation: "reuse", nodeId: reuse, rowHint: action.rank, sourceNodeId: source || null, targetNodeId: target || null, incomingEdgeId: newGraphId(), outgoingEdgeId: newGraphId() }
        : { operation: "add", nodeId: newGraphId(), kind, rowHint: action.rank, createPendingChoices: kind === "decision" && scaffold, sourceNodeId: source || null, targetNodeId: kind === "ending" || kind === "decision" ? null : target || null, incomingEdgeId: newGraphId(), outgoingEdgeId: newGraphId() };
    } else if (action.type === "insert") command = { operation: "insert", nodeId: newGraphId(), kind, createPendingChoices: kind === "decision" && scaffold, rowHint: action.rank, edgeId: edgeId || null, continuationEdgeId: newGraphId() };
    else if (action.endpoint === "source") command = { operation: "replace_input", nodeId: action.nodeId, priorEdgeId: edgeId || null, chosenEdgeId: chosenEdge };
    else if (edgeId) command = { operation: "retarget", edgeId, endpoint: action.endpoint, nodeId: endpointNode || null };
    else command = { operation: "add_edge", edgeId: newGraphId(), sourceNodeId: action.nodeId, targetNodeId: endpointNode || null };
    onClose(); void owner.prepareCommand(command);
  };
  return <dialog ref={dialog} className="creator-edit-dialog" aria-label={action.type === "row" ? "向此行添加节点" : action.type === "insert" ? "插入新一行" : "编辑精确连接"} onCancel={event => { event.preventDefault(); onClose(); }}>
    <h2>{action.type === "row" ? "向此行添加节点" : action.type === "insert" ? "插入新一行" : "编辑精确连接"}</h2>
    {action.type !== "connection" && <>
      {action.type === "row" && <Field label="新建或复用"><select aria-label="新建或复用" value={reuse} onChange={event => { setReuse(event.target.value); if (event.target.value && topology.edges.some(edge => edge.sourceNodeId === event.target.value)) setTarget(""); }}><option value="">新建节点</option>{detached.map(node => <option key={node.id} value={node.id}>复用 {title(node.id)} · {node.kind}</option>)}</select></Field>}
      {!reuse && <Field label="节点类型"><select aria-label="新增节点类型" value={kind} onChange={event => setKind(event.target.value as typeof kind)}><option value="scene">故事发展</option><option value="decision">选择点</option><option value="join">汇合点</option><option value="ending">结局</option></select></Field>}
      {!reuse && kind === "decision" && <label><input type="checkbox" checked={scaffold} onChange={event => setScaffold(event.target.checked)} />建立两个待连接选项（恢复保留选项时可取消）</label>}
      {action.type === "row" && <><Field label="并行选项来自"><select aria-label="并行选项来自" value={source} onChange={event => setSource(event.target.value)}><option value="">暂不连接，不猜测父节点</option>{topology.nodes.filter(node => node.kind === "decision").map(node => <option key={node.id} value={node.id}>{title(node.id)}</option>)}</select></Field>
        <Field label="新增节点的后续"><select aria-label="新增节点的后续" disabled={!reuse && ["decision", "ending"].includes(kind)} value={target} onChange={event => setTarget(event.target.value)}><option value="">暂不连接</option>{topology.nodes.map(node => <option key={node.id} value={node.id}>{title(node.id)} · {node.kind}</option>)}</select></Field>
        <p>共同父节点与共同后续只是可修改的默认值。复用会保留已有正文、标识与输出；不会覆盖后续。</p></>}
      {action.type === "insert" && <><Field label="拆分的精确连接"><select aria-label="拆分的精确连接" value={edgeId} onChange={event => setEdge(event.target.value)}><option value="">创建未连接步骤，保留所有原连接</option>{topology.edges.map(edge => <option key={edge.id} value={edge.id}>{edge.id} · {edge.sourceNodeId ? title(edge.sourceNodeId) : "待定"} → {edge.targetNodeId ? title(edge.targetNodeId) : "待定"}</option>)}</select></Field><p>原连接的身份、选项与效果留在输入。原目标保留；选择点的后续需要明确填写，结局没有后续。</p></>}
    </>}
    {action.type === "connection" && <>
      <Field label={action.endpoint === "source" ? "要替换的原入口" : "精确选项或后续"}><select aria-label="精确选项或后续" value={edgeId} onChange={event => setEdge(event.target.value)}><option value="">{action.endpoint === "source" ? "新增入口，保留所有现有入口" : "新增输出连接"}</option>{availableEdges.map(edge => <option key={edge.id} value={edge.id}>{edge.id} · {draft.mapping.choices.flatMap(choice => choice.outcomes).find(option => option.outcomeId === edge.id)?.label || "普通连接"} · {edge.targetNodeId ? title(edge.targetNodeId) : "待连接"}</option>)}</select></Field>
      {action.endpoint === "source" ? <Field label="选择新的精确输入"><select aria-label="选择新的精确输入" value={chosenEdge} onChange={event => setChosenEdge(event.target.value)}><option value="">请选择哪个选项或后续</option>{topology.edges.filter(edge => edge.sourceNodeId).map(edge => <option key={edge.id} value={edge.id}>{title(edge.sourceNodeId!)} · {draft.mapping.choices.flatMap(choice => choice.outcomes).find(option => option.outcomeId === edge.id)?.label || "后续"} · {edge.id} → {edge.targetNodeId ? title(edge.targetNodeId) : "待连接"}</option>)}</select></Field>
        : <Field label="更改目标"><select aria-label="更改连接端点" value={endpointNode} onChange={event => setEndpointNode(event.target.value)}><option value="">明确保留待连接</option>{topology.nodes.map(node => <option key={node.id} value={node.id}>{title(node.id)} · {node.kind}</option>)}</select></Field>}
      <p>{action.endpoint === "source" ? "原入口保持待连接并保留标识与文字；所选输出的旧目标保留。两条连接变化一次确认。" : "修改一个精确端点，原目标与其他连接保留。"}任何兼容节点都可选择；服务器会验证自连接、循环、开场与容量。</p>
    </>}
    <footer><Button onClick={onClose}>取消</Button><Button variant="primary" disabled={owner.busy || action.type === "connection" && action.endpoint === "source" && !chosenEdge} onClick={prepare}>准备修改预览</Button></footer>
  </dialog>;
}
