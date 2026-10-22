import type { ProjectBrief } from "../../types";
import type { GraphAuthoringDraft } from "./contracts";
import { completeMap } from "../../pages/sourceStructureModel";

export function creatorStructure(draft: GraphAuthoringDraft, brief: ProjectBrief) {
  const { topology } = draft.mapping, routes: string[][] = [], seen = new Set<string>();
  const walk = (id: string, path: string[]) => {
    if (path.includes(id) || path.length > topology.nodes.length || routes.length >= 256) return;
    seen.add(id); const next = [...path, id], node = topology.nodes.find(node => node.id === id);
    if (node?.kind === "ending") { routes.push(next); return; }
    topology.edges.filter(edge => edge.sourceNodeId === id && edge.targetNodeId).forEach(edge => walk(edge.targetNodeId!, next));
  };
  if (topology.startNodeId) walk(topology.startNodeId, []);
  const choices = routes.map(route => route.filter(id => topology.nodes.find(node => node.id === id)?.kind === "decision").length);
  const actual = { nodes: topology.nodes.length, endings: topology.nodes.filter(node => node.kind === "ending").length, joins: topology.joins.length, choices: [...new Set(choices)], routes: routes.length,
    pending: topology.edges.filter(edge => !edge.sourceNodeId || !edge.targetNodeId).length, detached: topology.nodes.filter(node => !seen.has(node.id)).length,
    degree: Math.max(0, ...topology.nodes.map(node => topology.edges.filter(edge => edge.sourceNodeId === node.id).length)) };
  const mismatches = [actual.nodes > brief.nodeBudget && "节点超过简报上限", actual.endings !== brief.endingCount && "结局数量与简报不同",
    actual.joins !== brief.desiredJoinCount && "汇合数量与简报不同", actual.choices.some(count => count !== brief.decisionPointsPerPath) && "完整播放的选择次数与简报不同", actual.degree > Math.min(6, brief.maxOutDegree) && "选择选项超过简报上限"].filter(Boolean) as string[];
  const incomplete = !completeMap(draft.mapping) || actual.pending > 0 || actual.detached > 0 || !routes.length || Object.keys(draft.fieldBuffers).length > 0;
  return { actual, mismatches, incomplete, routes, truncated: routes.length >= 256 };
}
