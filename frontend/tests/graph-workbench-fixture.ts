import { vi } from "vitest";
import type { GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import type { GraphAuthoringDraft } from "../src/features/graph/contracts";

export function graphControllerFixture(changes: Partial<GraphWorkbenchController> = {}): GraphWorkbenchController {
  return { state: null, draft: null, selectedNodeId: null, busy: false, error: "", stale: false,
    preview: null, canUndo: false, refresh: vi.fn().mockResolvedValue(undefined), selectNode: vi.fn(),
    changeMapping: vi.fn(), changeDraft: vi.fn(), adoptMapping: vi.fn(), saveDraft: vi.fn().mockResolvedValue(true),
    confirmMapping: vi.fn().mockResolvedValue(true), installMapping: vi.fn().mockResolvedValue(true),
    prepareCommand: vi.fn().mockResolvedValue(undefined), cancelPreview: vi.fn(), applyPreview: vi.fn().mockResolvedValue(undefined),
    undo: vi.fn().mockResolvedValue(undefined), recover: vi.fn().mockResolvedValue(undefined), discard: vi.fn().mockResolvedValue(undefined), ...changes };
}
export function graphDraftFixture(): GraphAuthoringDraft {
  const nodes = [{ id: "opening", kind: "start" as const, footageMode: "footage" as const }, { id: "ending", kind: "ending" as const, footageMode: "footage" as const }];
  const edges = [{ id: "opening-ending", sourceNodeId: "opening", targetNodeId: "ending", kind: "continuation" as const }];
  return { bindingHash: "a".repeat(64), rowHints: {}, selectedNodeId: "opening", detachedEndpoints: {}, fieldBuffers: {},
    mapping: { seedTopology: { plannerVersion: "story_graph_topology.v3", projectId: "project", startNodeId: "opening", topologyHash: "b".repeat(64), structuralParameters: {}, nodes, edges, joins: [] },
      topologyOrigin: "planner", topology: { startNodeId: "opening", nodes: nodes.map(({ id, kind }) => ({ id, kind })), edges: edges.map(edge => ({ ...edge, stateEffects: {}, entityStateEffects: [] })), joins: [] },
      sections: nodes.map(node => ({ sectionId: node.id, title: node.id, summary: `${node.id} story`, ending: node.kind === "ending", footageMode: node.footageMode })), choices: [], joinReconciliations: {} } };
}
