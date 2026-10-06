import { useEffect, useRef } from "react";
import { Button } from "../../components";
import { useGraphWorkbench } from "./GraphWorkbenchContext";

const kinds = { start: "开场", scene: "故事发展", decision: "选择点", join: "汇合点", ending: "结局" };
export function GraphCommandDialog() {
  const owner = useGraphWorkbench(), dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (owner.preview && dialog.current && !dialog.current.open) dialog.current.showModal(); }, [owner.preview]);
  if (!owner.preview) return null;
  const impact = owner.preview.impact, proposed = owner.preview.result.mapping;
  const endpoint = (id: string | null, result: boolean) => {
    if (id === null) return "待连接";
    const mapping = result ? proposed : owner.draft!.mapping, node = mapping.topology.nodes.find(node => node.id === id);
    const title = mapping.sections.find(section => section.sectionId === id)?.title.trim();
    return title || `${impact.addedNodeIds.includes(id) ? "新建" : "待命名"}${node ? kinds[node.kind] : "节点"}（待填写标题）`;
  };
  const connections = [...new Set([...impact.addedEdgeIds, ...impact.changedEdgeIds, ...impact.removedEdgeIds])];
  const groups = [["新增节点", impact.addedNodeIds], ["删除节点", impact.removedNodeIds], ["新增连接", impact.addedEdgeIds],
    ["删除连接", impact.removedEdgeIds], ["修改连接", impact.changedEdgeIds], ["需审阅汇合", impact.affectedJoinIds], ["待连接", impact.pendingEdgeIds]] as const;
  return <dialog ref={dialog} className="graph-command-dialog" aria-labelledby="graph-preview-title" onCancel={event => { event.preventDefault(); if (!owner.busy) owner.cancelPreview(); }}>
    <h2 id="graph-preview-title">确认结构修改</h2>
    <p>预览绑定当前已保存图草稿。确认一次完成整笔修改；取消不改变图。</p>
    {impact.addedNodeIds.length > 0 && <p><strong>新增节点：</strong>{impact.addedNodeIds.map(id => endpoint(id, true)).join("、")}</p>}
    {impact.removedNodeIds.length > 0 && <p><strong>删除节点：</strong>{impact.removedNodeIds.map(id => endpoint(id, false)).join("、")}</p>}
    {impact.affectedJoinIds.length > 0 && <p><strong>需审阅汇合：</strong>{impact.affectedJoinIds.map(id => endpoint(proposed.topology.joins.find(join => join.id === id)?.joinNodeId ?? owner.draft!.mapping.topology.joins.find(join => join.id === id)!.joinNodeId, proposed.topology.joins.some(join => join.id === id))).join("、")}</p>}
    {connections.length > 0 && <table aria-label="精确连接修改预览"><thead><tr><th>选项或后续</th><th>修改前</th><th>确认后</th></tr></thead><tbody>{connections.map(id => {
      const before = owner.draft!.mapping.topology.edges.find(edge => edge.id === id), after = proposed.topology.edges.find(edge => edge.id === id);
      const option = proposed.choices.flatMap(choice => choice.outcomes).find(option => option.outcomeId === id) || owner.draft!.mapping.choices.flatMap(choice => choice.outcomes).find(option => option.outcomeId === id);
      return <tr key={id}><td>{option ? option.label || "待填写选项" : "普通后续"}<small> · {before ? after ? "修改连接" : "删除连接" : "新增连接"}</small></td><td>{before ? `${endpoint(before.sourceNodeId, false)} → ${endpoint(before.targetNodeId, false)}` : "新增"}</td><td>{after ? `${endpoint(after.sourceNodeId, true)} → ${endpoint(after.targetNodeId, true)}` : "删除"}</td></tr>;
    })}</tbody></table>}
    {impact.messages.map((message, index) => <p key={index}>{message}</p>)}
    <details><summary>结构技术详情 · 精确身份</summary>{groups.filter(([, ids]) => ids.length).map(([label, ids]) => <p key={label}><strong>{label}：</strong>{ids.join("、")}</p>)}</details>
    {owner.error && <p role="alert">{owner.error}</p>}
    <footer><Button disabled={owner.busy} onClick={owner.cancelPreview}>取消</Button><Button variant="primary" busy={owner.busy} onClick={() => void owner.applyPreview()}>确认修改</Button></footer>
  </dialog>;
}
