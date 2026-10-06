import type { StoryGraph, ValidationIssue } from "./types";

export interface GraphEntityRef { kind: "node" | "edge" | "contract"; id: string }
export function graphEntityKey(entity: GraphEntityRef): string { return `graph-${entity.kind}:${entity.id}`; }

export interface GraphIssueTarget {
  entity: GraphEntityRef;
  field: string;
}

export function graphFocusKey(entity: GraphEntityRef, field: string): string {
  return `graph:${entity.kind}:${entity.id}:${field}`;
}

export function graphIssueTarget(graph: StoryGraph, issue: ValidationIssue): GraphIssueTarget | undefined {
  const path = issue.path.replace(/^storyGraph\./, "");
  const match = /^(nodes|edges|joinContracts)\.([^.]+)(?:\.(.*))?$/.exec(path);
  if (!match) {
    return path === "startNodeId"
      ? { entity: { kind: "node", id: graph.startNodeId }, field: "startNodeId" }
      : undefined;
  }
  const [, collection, token, remainder = "entity"] = match;
  if (collection === "nodes") {
    const node = /^\d+$/.test(token) ? graph.nodes[Number(token)] : graph.nodes.find((candidate) => candidate.id === token);
    return node ? { entity: { kind: "node", id: node.id }, field: remainder.split(".")[0] || "entity" } : undefined;
  }
  if (collection === "edges") {
    const edge = /^\d+$/.test(token) ? graph.edges[Number(token)] : graph.edges.find((candidate) => candidate.id === token);
    const stateEffectPath = remainder.split(".");
    const field = (stateEffectPath[0] === "stateEffects" || stateEffectPath[0] === "entityStateEffects") && stateEffectPath[1]
      ? `${stateEffectPath[0]}.${stateEffectPath[1]}${stateEffectPath[2] ? `.${stateEffectPath[2]}` : ""}`
      : stateEffectPath[0] || "entity";
    return edge ? { entity: { kind: "edge", id: edge.id }, field } : undefined;
  }
  const contract = /^\d+$/.test(token)
    ? graph.joinContracts[Number(token)]
    : graph.joinContracts.find((candidate) => candidate.id === token);
  return contract ? { entity: { kind: "contract", id: contract.id }, field: remainder.split(".")[0] || "entity" } : undefined;
}

export function issueFocusTarget(graph: StoryGraph, issues: ValidationIssue[]): GraphEntityRef | undefined {
  for (const issue of issues) {
    const target = graphIssueTarget(graph, issue);
    if (target) return target.entity;
  }
  return undefined;
}
