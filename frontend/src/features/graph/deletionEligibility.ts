import type { GraphAuthoringDraft } from "./contracts";

/** Conservative offer check; the immutable server preview still validates the transaction. */
export function bypassUnavailableReason(draft: GraphAuthoringDraft, nodeId: string): string | null {
  const topology = draft.mapping.topology, node = topology.nodes.find(node => node.id === nodeId);
  if (!node || nodeId === topology.startNodeId || !["scene", "join"].includes(node.kind)) return "仅剧情或汇合节点可绕过；开场受到保护。";
  const incoming = topology.edges.filter(edge => edge.targetNodeId === nodeId);
  const outgoing = topology.edges.filter(edge => edge.sourceNodeId === nodeId);
  if (!incoming.length || incoming.some(edge => !edge.sourceNodeId) || outgoing.length !== 1 || !outgoing[0].targetNodeId) return "需要明确的输入与恰好一条已连接后续。";
  const continuation = outgoing[0], target = continuation.targetNodeId!;
  if (target === topology.startNodeId || target === nodeId || incoming.some(edge => edge.sourceNodeId === target)) return "绕过会产生开场输入或自连接。";
  if (Object.keys(continuation.stateEffects).length || continuation.entityStateEffects.length || Object.keys(draft.fieldBuffers).some(key => key.startsWith(`edge:${continuation.id}:`))) return "后续有独立效果或未完成输入，不能合并或丢弃。";
  const hasJoin = topology.joins.some(join => join.joinNodeId === target);
  const sources = new Set([...incoming, ...topology.edges.filter(edge => edge.targetNodeId === target && edge.id !== continuation.id)].map(edge => edge.sourceNodeId));
  if (!hasJoin && (incoming.length > 1 || sources.size > 1)) return "多输入不能绕过到没有汇合合同的单入口节点。";
  const targetSection = draft.mapping.sections.find(section => section.sectionId === target);
  if (targetSection?.footageMode === "route_only" && incoming.some(edge => edge.entityStateEffects.length)) return "目标没有画面，不能接收场景入口状态效果。";
  return null;
}
