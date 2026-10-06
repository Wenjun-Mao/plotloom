import type { SectionChoice, SectionMap, SourceTopology } from "../types";
import type { GraphMapDraft } from "../features/graph/contracts";
export const cloneMap = (mapping?: SectionMap | null): SectionMap | null => mapping ? structuredClone(mapping) : null;
const ordered = (value: unknown): unknown => Array.isArray(value) ? value.map(ordered) : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right)).map(([key, item]) => [key, ordered(item)])) : value;
export const mapsEqual = (left: GraphMapDraft | null, right?: GraphMapDraft | null) => JSON.stringify(ordered(left)) === JSON.stringify(ordered(right ?? null));
export const graphStructuresEqual = (left: GraphMapDraft, right: GraphMapDraft) => JSON.stringify(ordered({ topology: left.topology, footage: left.sections.map(({ sectionId, footageMode }) => ({ sectionId, footageMode })) })) === JSON.stringify(ordered({ topology: right.topology, footage: right.sections.map(({ sectionId, footageMode }) => ({ sectionId, footageMode })) }));
export const mapChoices = (mapping: SectionMap): SectionChoice[] => mapping.choices;
export function blankStructure(topology: SourceTopology): SectionMap {
  return { seedTopology: structuredClone(topology), topologyOrigin: "planner", topology: { startNodeId: topology.startNodeId, nodes: topology.nodes.map(node => ({ id: node.id, kind: node.kind })), edges: topology.edges.map(edge => ({ ...edge, stateEffects: {}, entityStateEffects: [] })), joins: topology.joins.map(join => ({ ...join, requiredStateKeys: [], allowedDifferences: [], notes: "Source structure narrative reconciliation." })) },
    sections: topology.nodes.map(node => ({ sectionId: node.id, title: "", summary: "", ending: node.kind === "ending", footageMode: node.footageMode })),
    choices: topology.nodes.filter(node => node.kind === "decision").map(node => ({ choiceId: node.id, sectionId: node.id, prompt: "", outcomes: topology.edges.filter(edge => edge.sourceNodeId === node.id).map(edge => ({ outcomeId: edge.id, endingSectionId: edge.targetNodeId, label: "", consequence: "" })) })),
    joinReconciliations: Object.fromEntries(topology.joins.map(join => [join.id, ""])),
  };
}
export function completeMap(mapping: GraphMapDraft | null): boolean {
  return Boolean(mapping && mapping.sections.length > 0 && mapping.sections.every(section => section.title.trim() && section.summary.trim())
    && mapping.topology.startNodeId !== null && mapping.topology.edges.every(edge => edge.sourceNodeId !== null && edge.targetNodeId !== null)
    && mapping.choices.every(choice => choice.prompt.trim() && choice.outcomes.length >= 2 && choice.outcomes.every(option => option.label.trim() && option.consequence.trim() && option.endingSectionId !== null))
    && mapping.topology.joins.every(join => join.incomingNodeIds.length >= 2)
    && Object.values(mapping.joinReconciliations).every(value => value.trim()));
}
