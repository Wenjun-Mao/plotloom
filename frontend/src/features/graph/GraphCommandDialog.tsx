import { useEffect, useRef } from "react";
import { Button } from "../../components";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { GraphSafetyNotice } from "./GraphSafetyNotice";
import { GraphPreviewRecovery } from "./GraphPreviewRecovery";

const kinds = { start: "开场", scene: "故事发展", decision: "选择点", join: "汇合点", ending: "结局" };
export function GraphCommandDialog() {
  const owner = useGraphWorkbench(), dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (owner.preview && dialog.current && !dialog.current.open) dialog.current.showModal(); }, [owner.preview]);
  if (!owner.preview) return null;
  const impact = owner.preview.impact, proposed = owner.preview.result.mapping;
  const beforeMapping = owner.draft!.mapping;
  const endpoint = (id: string | null, result: boolean) => {
    if (id === null) return "待连接";
    const mapping = result ? proposed : beforeMapping, node = mapping.topology.nodes.find(node => node.id === id);
    const title = mapping.sections.find(section => section.sectionId === id)?.title.trim();
    return title || `${impact.addedNodeIds.includes(id) ? "新建" : "待命名"}${node ? kinds[node.kind] : "节点"}（待填写标题）`;
  };
  const beforeNodes = new Map(beforeMapping.topology.nodes.map(node => [node.id, node]));
  const afterNodes = new Map(proposed.topology.nodes.map(node => [node.id, node]));
  const beforeSections = new Map(beforeMapping.sections.map(section => [section.sectionId, section]));
  const afterSections = new Map(proposed.sections.map(section => [section.sectionId, section]));
  const changedNodeIds = impact.retainedNodeIds.filter(id => {
    const before = beforeNodes.get(id), after = afterNodes.get(id);
    return before && after && (before.kind !== after.kind
      || beforeSections.get(id)?.footageMode !== afterSections.get(id)?.footageMode);
  });
  const footageMode = (mode: "footage" | "route_only" | undefined) =>
    mode === "footage" ? "包含画面" : mode === "route_only" ? "仅路线控制点" : "未设置";
  const nodeChanges = changedNodeIds.map(id => {
    const before = beforeNodes.get(id)!, after = afterNodes.get(id)!;
    const beforeSection = beforeSections.get(id), afterSection = afterSections.get(id);
    const changes = [];
    if (before.kind !== after.kind) changes.push(`类型 ${kinds[before.kind]} → ${kinds[after.kind]}`);
    if (beforeSection?.footageMode !== afterSection?.footageMode) {
      changes.push(`画面 ${footageMode(beforeSection?.footageMode)} → ${footageMode(afterSection?.footageMode)}`);
    }
    return `${endpoint(id, false)}：${changes.join("；")}`;
  });
  const beforeJoins = new Map(beforeMapping.topology.joins.map(join => [join.id, join]));
  const afterJoins = new Map(proposed.topology.joins.map(join => [join.id, join]));
  const affectedJoinIds = impact.affectedJoinIds;
  const sameMembers = (left: string[], right: string[]) => {
    const leftSet = new Set(left), rightSet = new Set(right);
    return leftSet.size === rightSet.size && [...leftSet].every(id => rightSet.has(id));
  };
  const addedJoinIds = affectedJoinIds.filter(id => !beforeJoins.has(id) && afterJoins.has(id));
  const removedJoinIds = affectedJoinIds.filter(id => beforeJoins.has(id) && !afterJoins.has(id));
  const changedJoinInputIds = affectedJoinIds.filter(id => {
    const before = beforeJoins.get(id), after = afterJoins.get(id);
    return before && after && !sameMembers(before.incomingNodeIds, after.incomingNodeIds);
  });
  const otherChangedJoinIds = affectedJoinIds.filter(id => beforeJoins.has(id) && afterJoins.has(id)
    && !changedJoinInputIds.includes(id));
  const joinInputs = (join: NonNullable<ReturnType<typeof beforeJoins.get>>, result: boolean) =>
    join.incomingNodeIds.length ? join.incomingNodeIds.map(id => endpoint(id, result)).join("、") : "无直接输入";
  const joinDescriptions = new Map<string, string>();
  for (const id of addedJoinIds) {
    const join = afterJoins.get(id)!;
    joinDescriptions.set(id, `${endpoint(join.joinNodeId, true)}（直接输入：${joinInputs(join, true)}）`);
  }
  for (const id of removedJoinIds) {
    const join = beforeJoins.get(id)!;
    joinDescriptions.set(id, `${endpoint(join.joinNodeId, false)}（直接输入：${joinInputs(join, false)}）`);
  }
  for (const id of changedJoinInputIds) {
    const before = beforeJoins.get(id)!, after = afterJoins.get(id)!;
    joinDescriptions.set(id, `${endpoint(after.joinNodeId, true)}：${joinInputs(before, false)} → ${joinInputs(after, true)}`);
  }
  for (const id of otherChangedJoinIds) {
    const join = afterJoins.get(id)!;
    joinDescriptions.set(id, endpoint(join.joinNodeId, true));
  }
  const joinGroups: Array<[string, string[]]> = [
    ["新增汇合合同", addedJoinIds], ["移除汇合合同", removedJoinIds],
    ["汇合输入节点变化，需重新审阅", changedJoinInputIds], ["汇合合同字段变化", otherChangedJoinIds],
  ];
  const connections = [...new Set([...impact.addedEdgeIds, ...impact.changedEdgeIds, ...impact.removedEdgeIds])];
  const groups: Array<[string, string[]]> = [["新增节点", impact.addedNodeIds], ["删除节点", impact.removedNodeIds],
    ["修改节点类型或画面", changedNodeIds], ["新增连接", impact.addedEdgeIds], ["删除连接", impact.removedEdgeIds],
    ["修改连接", impact.changedEdgeIds], ...joinGroups, ["待连接", impact.pendingEdgeIds]];
  return <dialog ref={dialog} className="graph-command-dialog" aria-labelledby="graph-preview-title" onCancel={event => { event.preventDefault(); if (!owner.busy) owner.cancelPreview(); }}>
    <h2 id="graph-preview-title">确认结构修改</h2>
    <p>预览绑定当前已保存图草稿。确认一次完成整笔修改；取消不改变图。</p>
    {impact.addedNodeIds.length > 0 && <p><strong>新增节点：</strong>{impact.addedNodeIds.map(id => endpoint(id, true)).join("、")}</p>}
    {impact.removedNodeIds.length > 0 && <p><strong>删除节点：</strong>{impact.removedNodeIds.map(id => endpoint(id, false)).join("、")}</p>}
    {nodeChanges.length > 0 && <p aria-label="节点类型与画面变化"><strong>节点类型与画面变化：</strong>{nodeChanges.join("；")}</p>}
    {joinGroups.filter(([, ids]) => ids.length).map(([label, ids]) => <p key={label} aria-label={label}>
      <strong>{label}：</strong>{ids.map(id => joinDescriptions.get(id) ?? id).join("；")}
    </p>)}
    {connections.length > 0 && <table aria-label="精确连接修改预览"><thead><tr><th>选项或后续</th><th>修改前</th><th>确认后</th></tr></thead><tbody>{connections.map(id => {
      const before = owner.draft!.mapping.topology.edges.find(edge => edge.id === id), after = proposed.topology.edges.find(edge => edge.id === id);
      const option = proposed.choices.flatMap(choice => choice.outcomes).find(option => option.outcomeId === id) || owner.draft!.mapping.choices.flatMap(choice => choice.outcomes).find(option => option.outcomeId === id);
      return <tr key={id}><td>{option ? option.label || "待填写选项" : "普通后续"}<small> · {before ? after ? "修改连接" : "删除连接" : "新增连接"}</small></td><td>{before ? `${endpoint(before.sourceNodeId, false)} → ${endpoint(before.targetNodeId, false)}` : "新增"}</td><td>{after ? `${endpoint(after.sourceNodeId, true)} → ${endpoint(after.targetNodeId, true)}` : "删除"}</td></tr>;
    })}</tbody></table>}
    {impact.messages.map((message, index) => <p key={index}>{message}</p>)}
    <details><summary>结构技术详情 · 精确身份</summary>{groups.filter(([, ids]) => ids.length).map(([label, ids]) => <p key={label}><strong>{label}：</strong>{ids.join("、")}</p>)}</details>
    <GraphSafetyNotice />
    <GraphPreviewRecovery />
    <footer><Button disabled={owner.busy} onClick={owner.cancelPreview}>取消</Button><Button variant="primary" disabled={owner.readStatus !== "ready" || owner.stale || owner.previewConflict || Boolean(owner.state?.readOnlyReason)} busy={owner.busy} onClick={() => void owner.applyPreview()}>确认修改</Button></footer>
  </dialog>;
}
