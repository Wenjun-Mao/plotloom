import type { AuthoringDraft, RequiredEntityState, SectionMap, SourceStructure, StoryNode } from "../../types";

export interface DraftEdge {
  id: string;
  sourceNodeId: string | null;
  targetNodeId: string | null;
  kind: "choice" | "continuation";
  stateEffects: Record<string, unknown>;
  entityStateEffects: RequiredEntityState[];
}
export interface GraphMapDraft extends Omit<SectionMap, "topology" | "choices"> {
  topology: Omit<SourceStructure, "startNodeId" | "edges"> & { startNodeId: string | null; edges: DraftEdge[] };
  choices: Array<{ choiceId: string; sectionId: string; prompt: string; outcomes: Array<{ outcomeId: string; label: string; consequence: string; endingSectionId: string | null }> }>;
}
export interface GraphAuthoringDraft {
  bindingHash: string;
  mapping: GraphMapDraft;
  rowHints: Record<string, number>;
  selectedNodeId: string | null;
  detachedEndpoints: Record<string, Partial<Record<"source" | "target", { nodeId: string; title: string; kind: string }>>>;
  fieldBuffers: Record<string, string>;
}
export interface GraphWorkbenchState {
  bindingHash: string;
  baseCanonicalRevision: number;
  draft: AuthoringDraft | null;
  initialPayload: GraphAuthoringDraft | null;
  readOnlyReason: string | null;
}
type NewNode = { nodeId: string; kind: Exclude<StoryNode["kind"], "start">; rowHint: number; createPendingChoices: boolean };
export type GraphCommand =
  | (NewNode & { operation: "add"; sourceNodeId: string | null; targetNodeId: string | null; incomingEdgeId: string; outgoingEdgeId: string })
  | (NewNode & { operation: "insert"; edgeId: string | null; continuationEdgeId: string })
  | { operation: "reuse"; nodeId: string; rowHint: number; sourceNodeId: string | null; targetNodeId: string | null; incomingEdgeId: string; outgoingEdgeId: string }
  | { operation: "retarget"; edgeId: string; endpoint: "source" | "target"; nodeId: string | null }
  | { operation: "replace_input"; nodeId: string; priorEdgeId: string | null; chosenEdgeId: string }
  | { operation: "delete"; nodeId: string; method: "only_delete" | "safe_bypass" }
  | { operation: "set_start"; nodeId: string }
  | { operation: "set_kind"; nodeId: string; kind: NewNode["kind"]; footageMode: "footage" | "route_only" }
  | { operation: "add_edge"; edgeId: string; sourceNodeId: string; targetNodeId: string | null }
  | { operation: "remove_edge"; edgeId: string }
  | { operation: "add_join"; joinId: string; nodeId: string }
  | { operation: "remove_join"; joinId: string };
export interface GraphCommandPreview {
  draftRevision: number;
  bindingHash: string;
  command: GraphCommand;
  result: GraphAuthoringDraft;
  impact: { addedNodeIds: string[]; removedNodeIds: string[]; addedEdgeIds: string[]; removedEdgeIds: string[]; changedEdgeIds: string[]; affectedJoinIds: string[]; retainedNodeIds: string[]; pendingEdgeIds: string[]; messages: string[] };
  previewHash: string;
}
export function readGraphDraft(value: unknown): GraphAuthoringDraft {
  const draft = value as GraphAuthoringDraft;
  if (!draft || !/^[a-f0-9]{64}$/.test(draft.bindingHash) || !draft.mapping || !draft.rowHints || !draft.detachedEndpoints || !draft.fieldBuffers
    || draft.mapping.seedTopology?.plannerVersion !== "story_graph_topology.v3"
    || !Array.isArray(draft.mapping.topology?.nodes) || !Array.isArray(draft.mapping.topology?.edges)
    || !Array.isArray(draft.mapping.sections) || !Array.isArray(draft.mapping.choices)
    || draft.mapping.sections.some(section => !["footage", "route_only"].includes(section.footageMode))) {
    throw new Error("图草稿不符合当前契约。内容已保留，请明确处理后重新创建当前草稿。");
  }
  return draft;
}
export const graphDraftKey = (projectId: string) => `${projectId}:story_graph:root`;
export const newGraphId = () => `graph-${crypto.randomUUID().replaceAll("-", "").slice(0, 24)}`;
