import type { APIRequestContext } from "@playwright/test";
import { demoProject } from "../../src/demo";
import type { SectionMap } from "../../src/types";
import { acknowledgeGraphMapping, currentFixtureMapping } from "./graph-authoring";
import { json } from "../f5a-fixture";

type NodeKind = SectionMap["topology"]["nodes"][number]["kind"];
export async function createCreatorGraph(request: APIRequestContext, origin: string, label: string, siblings = 2, chain = 1): Promise<string> {
  const root = `${origin}/api/v2/projects`;
  const created = await json(request.post(root, { headers: { "Idempotency-Key": `creator-${label}-${Date.now()}` }, data: { brief: { ...demoProject.brief, title: `图工作台 ${label}`, nodeBudget: 30, maxOutDegree: 6, decisionPointsPerPath: 2, endingCount: 2, desiredJoinCount: 1 } } }));
  const nodes: Array<{ id: string; kind: NodeKind }> = [{ id: "opening", kind: "start" }, { id: "choose", kind: "decision" }, ...Array.from({ length: siblings }, (_, index) => ({ id: `branch-${index + 1}`, kind: "scene" as const })), { id: "merge", kind: "join" }, ...Array.from({ length: chain }, (_, index) => ({ id: `step-${index + 1}`, kind: "scene" as const })), { id: "final-choice", kind: "decision" }, { id: "ending-a", kind: "ending" }, { id: "ending-b", kind: "ending" }];
  const edge = (id: string, sourceNodeId: string, targetNodeId: string, kind: "choice" | "continuation" = "continuation") => ({ id, sourceNodeId, targetNodeId, kind, stateEffects: {}, entityStateEffects: [] });
  const edges = [edge("opening-choice", "opening", "choose"), ...Array.from({ length: siblings }, (_, index) => edge(`option-${index + 1}`, "choose", `branch-${index + 1}`, "choice")), ...Array.from({ length: siblings }, (_, index) => edge(`branch-output-${index + 1}`, `branch-${index + 1}`, "merge")), edge("merge-step", "merge", "step-1"), ...Array.from({ length: Math.max(0, chain - 1) }, (_, index) => edge(`step-output-${index + 1}`, `step-${index + 1}`, `step-${index + 2}`)), edge("last-step-choice", `step-${chain}`, "final-choice"), edge("ending-option-a", "final-choice", "ending-a", "choice"), edge("ending-option-b", "final-choice", "ending-b", "choice")];
  const section = (node: typeof nodes[number]) => ({ sectionId: node.id, title: node.id === "opening" ? "风暴前的共同开场" : node.id.startsWith("branch") ? `并行发展 ${node.id.slice(-1)}：穿过长长的灯塔走廊` : node.id === "merge" ? "汇合：各条路线回到同一座气象站" : node.id === "ending-a" ? "结局 A" : node.id === "ending-b" ? "结局 B" : node.id,
    summary: "角色在风暴前确认自己的行动与后果。完整的中文剧情保留在右侧详情中。", ending: node.kind === "ending", footageMode: node.kind === "decision" || node.kind === "join" ? "route_only" as const : "footage" as const });
  const choices = ["choose", "final-choice"].map(id => ({ choiceId: id, sectionId: id, prompt: "观众选择下一步的行动。", outcomes: edges.filter(edge => edge.sourceNodeId === id).map(edge => ({ outcomeId: edge.id, label: id === "choose" ? `选择 ${edge.id.slice(-1)}：沿着海岸、穿过灯塔，回到气象站确认同伴的安全` : edge.targetNodeId === "ending-a" ? "保留灯塔" : "驶向远海", consequence: "主角明确选择这条路线，其他选择的后果仍保留。", endingSectionId: edge.targetNodeId })) }));
  const body: Omit<SectionMap, "seedTopology"> = { topologyOrigin: "author", topology: { startNodeId: "opening", nodes, edges, joins: [{ id: "merge-contract", joinNodeId: "merge", incomingNodeIds: Array.from({ length: siblings }, (_, index) => `branch-${index + 1}`), requiredStateKeys: [], allowedDifferences: [], notes: "保留各条路线的衔接" }] }, sections: nodes.map(section), choices, joinReconciliations: { "merge-contract": "同伴重新确认各自的行动，继续共同剧情。" } };
  const url = `${root}/${created.id}`, mapping = await currentFixtureMapping(request, url, body);
  await acknowledgeGraphMapping(request, url, mapping); return created.id;
}
