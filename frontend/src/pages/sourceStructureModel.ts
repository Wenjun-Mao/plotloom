import type { SectionChoice, SectionMap, SourceTopology } from "../types";
export const emptyMap = (): SectionMap => ({ sections: [], choice: null });
export const cloneMap = (mapping?: SectionMap | null): SectionMap => structuredClone({ sections: [], choice: null, topology: null, choices: [], joinReconciliations: {}, ...mapping });
const ordered = (value: unknown): unknown => Array.isArray(value) ? value.map(ordered) : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right)).map(([key, item]) => [key, ordered(item)])) : value;
export const mapsEqual = (left: SectionMap, right?: SectionMap | null) => JSON.stringify(ordered(cloneMap(left))) === JSON.stringify(ordered(cloneMap(right)));
export const mapChoices = (mapping: SectionMap): SectionChoice[] => mapping.topology ? mapping.choices || [] : mapping.choice ? [mapping.choice] : [];
export function blankStructure(topology: SourceTopology): SectionMap {
  return { topology, choice: null,
    sections: topology.nodes.map(node => ({ sectionId: node.id, title: "", summary: "", ending: node.kind === "ending" })),
    choices: topology.nodes.filter(node => node.kind === "decision").map(node => ({ choiceId: node.id, sectionId: node.id, prompt: "", outcomes: topology.edges.filter(edge => edge.sourceNodeId === node.id).map(edge => ({ outcomeId: edge.id, endingSectionId: edge.targetNodeId, label: "", consequence: "" })) })),
    joinReconciliations: Object.fromEntries(topology.joins.map(join => [join.id, ""])),
  };
}
export function completeMap(mapping: SectionMap): boolean {
  return mapping.sections.length > 0 && mapping.sections.every(section => section.title.trim() && section.summary.trim())
    && mapChoices(mapping).every(choice => choice.prompt.trim() && choice.outcomes.every(option => option.label.trim() && option.consequence.trim()))
    && Object.values(mapping.joinReconciliations || {}).every(value => value.trim());
}
