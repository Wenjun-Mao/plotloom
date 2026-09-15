import type { JoinContract, StoryEdge, StoryGraph, StoryNode, ValidationIssue } from "./types";

export type GraphEntityKind = "node" | "edge" | "contract";

export interface GraphEntityRef {
  kind: GraphEntityKind;
  id: string;
}

export type StateEffectValueKind = "string" | "number" | "boolean" | "null" | "json";

export interface StateEffectRow {
  key: string;
  kind: StateEffectValueKind;
  value: string;
}

export interface StateEffectRowError {
  index: number;
  code: "blank_key" | "duplicate_key" | "invalid_number" | "invalid_json";
}

export interface StateEffectRowsResult {
  value: Record<string, unknown>;
  errors: StateEffectRowError[];
}

export interface RelationshipImpact {
  removedNodeIds: string[];
  removedEdgeIds: string[];
  affectedContractIds: string[];
  removedContractIds: string[];
  updatedContractIds: string[];
  startNodeAffected: boolean;
}

/**
 * The confirmation UI must expose every stable relationship identity that an
 * operation can remove or rewrite. Keeping this projection in the domain
 * layer prevents a dialog from collapsing a cascade into an opaque count.
 */
export interface RelationshipImpactGroup {
  key: "removed-nodes" | "removed-edges" | "affected-contracts" | "removed-contracts" | "updated-contracts";
  label: string;
  ids: string[];
}

/** A downstream SceneBeat reference is retained, never cascade-deleted. */
export interface StoryNodeSceneReference {
  id: string;
  storyNodeId: string;
  title: string;
}

export interface RetainedSceneReference {
  sceneId: string;
  title: string;
  path: string;
}

export function relationshipImpactGroups(impact: RelationshipImpact): RelationshipImpactGroup[] {
  const groups: RelationshipImpactGroup[] = [
    { key: "removed-nodes", label: "将删除节点", ids: impact.removedNodeIds },
    { key: "removed-edges", label: "将删除关系", ids: impact.removedEdgeIds },
    { key: "affected-contracts", label: "受影响汇合合同", ids: impact.affectedContractIds },
    { key: "removed-contracts", label: "将删除汇合合同", ids: impact.removedContractIds },
    { key: "updated-contracts", label: "将更新汇合合同", ids: impact.updatedContractIds },
  ];
  return groups
    .map((group) => ({ ...group, ids: [...new Set(group.ids)].sort() }))
    .filter((group) => group.ids.length > 0);
}

export function retainedSceneReferencesForNode(
  scenes: readonly StoryNodeSceneReference[],
  storyNodeId: string,
): RetainedSceneReference[] {
  return scenes
    .filter((scene) => scene.storyNodeId === storyNodeId)
    .map((scene) => ({
      sceneId: scene.id,
      title: scene.title,
      path: `scene_beats.scenes.${scene.id}.storyNodeId`,
    }))
    .sort((left, right) => left.sceneId.localeCompare(right.sceneId));
}

/** The endpoint change is authored explicitly; contracts are only synchronized
 * by the companion apply function after the caller has shown this impact. */
export interface EdgeReconnect {
  sourceNodeId: string;
  targetNodeId: string;
}

const entityPrefix = "graph-";

export function graphEntityKey(entity: GraphEntityRef): string {
  return `${entityPrefix}${entity.kind}:${entity.id}`;
}

export function parseGraphEntityIdentity(value: string | undefined, graph: StoryGraph): GraphEntityRef | undefined {
  if (!value) return undefined;
  const match = /^graph-(node|edge|contract):(.*)$/.exec(value);
  if (match && match[2]) {
    const kind = match[1] as GraphEntityKind;
    const id = match[2];
    if (graphContainsEntity(graph, { kind, id })) return { kind, id };
    return undefined;
  }
  // M1-B0 used the bare node ID in links. Continue to read those links, while
  // all newly emitted identities remain namespaced across graph entity kinds.
  return graph.nodes.some((node) => node.id === value) ? { kind: "node", id: value } : undefined;
}

export function addNode(graph: StoryGraph, node: StoryNode): StoryGraph {
  assertAbsent(graph.nodes.map((item) => item.id), node.id, "node");
  return { ...graph, nodes: [...graph.nodes, node] };
}

export function patchNode(graph: StoryGraph, id: string, patch: Partial<Omit<StoryNode, "id">>): StoryGraph {
  return {
    ...graph,
    nodes: graph.nodes.map((node) => node.id === id ? { ...node, ...patch, id: node.id } : node),
  };
}

export function setStartNode(graph: StoryGraph, id: string): StoryGraph {
  if (!graph.nodes.some((node) => node.id === id)) throw new Error(`unknown story node: ${id}`);
  return {
    ...graph,
    startNodeId: id,
    nodes: graph.nodes.map((node) => {
      if (node.id === id) return { ...node, kind: "start" };
      // A start selection repairs an otherwise malformed draft too: the graph
      // contract has exactly one start role, independently of a stale pointer.
      if (node.kind === "start") return { ...node, kind: "scene" };
      return node;
    }),
  };
}

export function addEdge(graph: StoryGraph, edge: StoryEdge): StoryGraph {
  assertAbsent(graph.edges.map((item) => item.id), edge.id, "edge");
  return { ...graph, edges: [...graph.edges, edge] };
}

export function patchEdge(graph: StoryGraph, id: string, patch: Partial<Omit<StoryEdge, "id" | "sourceNodeId" | "targetNodeId">>): StoryGraph {
  return {
    ...graph,
    edges: graph.edges.map((edge) => edge.id === id ? { ...edge, ...patch, id: edge.id, sourceNodeId: edge.sourceNodeId, targetNodeId: edge.targetNodeId } : edge),
  };
}

export function relationshipImpactForEdgeReconnect(
  graph: StoryGraph,
  edgeId: string,
  reconnect: EdgeReconnect,
): RelationshipImpact {
  const edge = graph.edges.find((item) => item.id === edgeId);
  if (!edge) throw new Error(`unknown story edge: ${edgeId}`);
  assertKnownEdgeEndpoints(graph, reconnect);
  if (edge.sourceNodeId === reconnect.sourceNodeId && edge.targetNodeId === reconnect.targetNodeId) {
    return emptyImpact();
  }
  const reconnected = replaceEdgeEndpoints(graph, edgeId, reconnect);
  const affected = graph.joinContracts.filter((contract) => (
    incomingNodeIds(graph, contract.joinNodeId).join("\u0000")
      !== incomingNodeIds(reconnected, contract.joinNodeId).join("\u0000")
  ));
  const removedContractIds = affected
    .filter((contract) => incomingNodeIds(reconnected, contract.joinNodeId).length < 2)
    .map((contract) => contract.id);
  return emptyImpact({
    affectedContractIds: affected.map((contract) => contract.id),
    removedContractIds,
    updatedContractIds: affected
      .filter((contract) => !removedContractIds.includes(contract.id))
      .map((contract) => contract.id),
  });
}

/**
 * Apply a previously reviewed endpoint change. The edge ID and all non-endpoint
 * fields survive untouched. Only affected JoinContracts are normalized; callers
 * must obtain confirmation from relationshipImpactForEdgeReconnect first.
 */
export function reconnectEdgeWithContractSync(
  graph: StoryGraph,
  edgeId: string,
  reconnect: EdgeReconnect,
): StoryGraph {
  const impact = relationshipImpactForEdgeReconnect(graph, edgeId, reconnect);
  const reconnected = replaceEdgeEndpoints(graph, edgeId, reconnect);
  if (!impact.affectedContractIds.length) return reconnected;
  return {
    ...reconnected,
    joinContracts: reconnected.joinContracts.flatMap((contract) => {
      if (impact.removedContractIds.includes(contract.id)) return [];
      if (impact.updatedContractIds.includes(contract.id)) {
        return [{ ...contract, incomingNodeIds: incomingNodeIds(reconnected, contract.joinNodeId) }];
      }
      return [contract];
    }),
  };
}

export function addJoinContract(graph: StoryGraph, contract: JoinContract): StoryGraph {
  assertAbsent(graph.joinContracts.map((item) => item.id), contract.id, "join contract");
  return { ...graph, joinContracts: [...graph.joinContracts, contract] };
}

export function patchJoinContract(graph: StoryGraph, id: string, patch: Partial<Omit<JoinContract, "id" | "joinNodeId" | "incomingNodeIds">>): StoryGraph {
  return {
    ...graph,
    joinContracts: graph.joinContracts.map((contract) => contract.id === id
      ? { ...contract, ...patch, id: contract.id, joinNodeId: contract.joinNodeId, incomingNodeIds: contract.incomingNodeIds }
      : contract),
  };
}

export function removeJoinContract(graph: StoryGraph, id: string): StoryGraph {
  return { ...graph, joinContracts: graph.joinContracts.filter((contract) => contract.id !== id) };
}

export function incomingNodeIds(graph: StoryGraph, joinNodeId: string): string[] {
  return [...new Set(
    graph.edges
      .filter((edge) => edge.targetNodeId === joinNodeId)
      .map((edge) => edge.sourceNodeId),
  )].sort();
}

export function relationshipImpactForNodeRemoval(graph: StoryGraph, nodeId: string): RelationshipImpact {
  const removedEdgeIds = graph.edges
    .filter((edge) => edge.sourceNodeId === nodeId || edge.targetNodeId === nodeId)
    .map((edge) => edge.id);
  const removedContractIds = graph.joinContracts
    .filter((contract) => contract.joinNodeId === nodeId || contract.incomingNodeIds.includes(nodeId))
    .map((contract) => contract.id);
  return emptyImpact({
    removedNodeIds: graph.nodes.some((node) => node.id === nodeId) ? [nodeId] : [],
    removedEdgeIds,
    affectedContractIds: removedContractIds,
    removedContractIds,
    startNodeAffected: graph.startNodeId === nodeId,
  });
}

export function relationshipImpactForNodeKindChange(graph: StoryGraph, nodeId: string, nextKind: StoryNode["kind"]): RelationshipImpact {
  const current = graph.nodes.find((node) => node.id === nodeId);
  if (!current || current.kind !== "join" || nextKind === "join") return emptyImpact();
  const removedContractIds = graph.joinContracts
    .filter((contract) => contract.joinNodeId === nodeId)
    .map((contract) => contract.id);
  return emptyImpact({
    affectedContractIds: removedContractIds,
    removedContractIds,
  });
}

export function relationshipImpactForEdgeRemoval(graph: StoryGraph, edgeId: string): RelationshipImpact {
  const edge = graph.edges.find((item) => item.id === edgeId);
  if (!edge) return emptyImpact();
  const withoutEdge = { ...graph, edges: graph.edges.filter((item) => item.id !== edgeId) };
  const affected = graph.joinContracts.filter((contract) =>
    contract.joinNodeId === edge.targetNodeId
    && incomingNodeIds(graph, contract.joinNodeId).join("\u0000") !== incomingNodeIds(withoutEdge, contract.joinNodeId).join("\u0000"),
  );
  const removedContractIds = affected
    .filter((contract) => incomingNodeIds(withoutEdge, contract.joinNodeId).length < 2)
    .map((contract) => contract.id);
  return emptyImpact({
    removedEdgeIds: [edgeId],
    affectedContractIds: affected.map((contract) => contract.id),
    removedContractIds,
    updatedContractIds: affected
      .filter((contract) => !removedContractIds.includes(contract.id))
      .map((contract) => contract.id),
  });
}

export function relationshipImpactForEdgeAddition(graph: StoryGraph, edge: StoryEdge): RelationshipImpact {
  const affected = graph.joinContracts.filter((contract) => contract.joinNodeId === edge.targetNodeId);
  return emptyImpact({
    affectedContractIds: affected.map((contract) => contract.id),
    updatedContractIds: affected.map((contract) => contract.id),
  });
}

export function removeNodeWithCascade(graph: StoryGraph, nodeId: string): StoryGraph {
  const impact = relationshipImpactForNodeRemoval(graph, nodeId);
  if (impact.startNodeAffected) throw new Error("select another start node before deleting the current start node");
  return {
    ...graph,
    nodes: graph.nodes.filter((node) => node.id !== nodeId),
    edges: graph.edges.filter((edge) => !impact.removedEdgeIds.includes(edge.id)),
    joinContracts: graph.joinContracts.filter((contract) => !impact.removedContractIds.includes(contract.id)),
  };
}

export function removeEdgeWithCascade(graph: StoryGraph, edgeId: string): StoryGraph {
  const impact = relationshipImpactForEdgeRemoval(graph, edgeId);
  const withoutEdge = { ...graph, edges: graph.edges.filter((edge) => edge.id !== edgeId) };
  return {
    ...withoutEdge,
    joinContracts: graph.joinContracts.flatMap((contract) => {
      if (impact.removedContractIds.includes(contract.id)) return [];
      if (impact.updatedContractIds.includes(contract.id)) {
        return [{ ...contract, incomingNodeIds: incomingNodeIds(withoutEdge, contract.joinNodeId) }];
      }
      return [contract];
    }),
  };
}

export function addEdgeWithContractSync(graph: StoryGraph, edge: StoryEdge): StoryGraph {
  const next = addEdge(graph, edge);
  const impact = relationshipImpactForEdgeAddition(graph, edge);
  if (!impact.updatedContractIds.length) return next;
  return {
    ...next,
    joinContracts: next.joinContracts.map((contract) => impact.updatedContractIds.includes(contract.id)
      ? { ...contract, incomingNodeIds: incomingNodeIds(next, contract.joinNodeId) }
      : contract),
  };
}

export function stateEffectsToRows(value: Record<string, unknown>): StateEffectRow[] {
  return Object.entries(value)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, item]) => stateEffectRow(key, item));
}

export function stateEffectRowsToValue(rows: StateEffectRow[]): StateEffectRowsResult {
  const value: Record<string, unknown> = {};
  const errors: StateEffectRowError[] = [];
  const seen = new Set<string>();
  rows.forEach((row, index) => {
    const key = row.key.trim();
    if (!key) {
      errors.push({ index, code: "blank_key" });
      return;
    }
    if (seen.has(key)) {
      errors.push({ index, code: "duplicate_key" });
      return;
    }
    seen.add(key);
    if (row.kind === "string") value[key] = row.value;
    else if (row.kind === "boolean") value[key] = row.value === "true";
    else if (row.kind === "null") value[key] = null;
    else if (row.kind === "number") {
      const number = Number(row.value);
      if (!Number.isFinite(number)) errors.push({ index, code: "invalid_number" });
      else value[key] = number;
    } else {
      try {
        value[key] = JSON.parse(row.value);
      } catch {
        errors.push({ index, code: "invalid_json" });
      }
    }
  });
  return { value, errors };
}

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

function graphContainsEntity(graph: StoryGraph, entity: GraphEntityRef): boolean {
  if (entity.kind === "node") return graph.nodes.some((node) => node.id === entity.id);
  if (entity.kind === "edge") return graph.edges.some((edge) => edge.id === entity.id);
  return graph.joinContracts.some((contract) => contract.id === entity.id);
}

function stateEffectRow(key: string, value: unknown): StateEffectRow {
  if (value === null) return { key, kind: "null", value: "" };
  if (typeof value === "string") return { key, kind: "string", value };
  if (typeof value === "number") return { key, kind: "number", value: String(value) };
  if (typeof value === "boolean") return { key, kind: "boolean", value: String(value) };
  return { key, kind: "json", value: JSON.stringify(value) };
}

function assertAbsent(ids: string[], id: string, label: string): void {
  if (!id.trim()) throw new Error(`${label} ID must not be blank`);
  if (ids.includes(id)) throw new Error(`duplicate ${label} ID: ${id}`);
}

function assertKnownEdgeEndpoints(graph: StoryGraph, reconnect: EdgeReconnect): void {
  if (!graph.nodes.some((node) => node.id === reconnect.sourceNodeId)) {
    throw new Error(`unknown edge source node: ${reconnect.sourceNodeId}`);
  }
  if (!graph.nodes.some((node) => node.id === reconnect.targetNodeId)) {
    throw new Error(`unknown edge target node: ${reconnect.targetNodeId}`);
  }
  if (reconnect.sourceNodeId === reconnect.targetNodeId) {
    throw new Error("an edge cannot connect a node to itself");
  }
}

function replaceEdgeEndpoints(graph: StoryGraph, edgeId: string, reconnect: EdgeReconnect): StoryGraph {
  return {
    ...graph,
    edges: graph.edges.map((edge) => edge.id === edgeId
      ? { ...edge, sourceNodeId: reconnect.sourceNodeId, targetNodeId: reconnect.targetNodeId, id: edge.id }
      : edge),
  };
}

function emptyImpact(patch: Partial<RelationshipImpact> = {}): RelationshipImpact {
  return {
    removedNodeIds: [],
    removedEdgeIds: [],
    affectedContractIds: [],
    removedContractIds: [],
    updatedContractIds: [],
    startNodeAffected: false,
    ...patch,
  };
}
