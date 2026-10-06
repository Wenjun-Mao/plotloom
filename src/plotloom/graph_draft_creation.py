"""Explicit current draft creation, never tolerant receiving-boundary defaults."""
from .graph_authoring_drafts import GraphAuthoringDraft, GraphMapDraft
from .source_graph_structure import structure_from_seed


def create_graph_draft(*, binding_hash, seed, mapping=None) -> GraphAuthoringDraft:
    if mapping is None:
        mapping = {
            "seedTopology": seed.model_dump(mode="json", by_alias=True),
            "topologyOrigin": "planner",
            "topology": structure_from_seed(seed).model_dump(mode="json", by_alias=True),
            "sections": [{"sectionId": node.id, "title": "", "summary": "",
                          "ending": node.kind.value == "ending", "footageMode": node.footage_mode} for node in seed.nodes],
            "choices": [{"choiceId": node.id, "sectionId": node.id, "prompt": "",
                         "outcomes": [{"outcomeId": edge.id, "label": "", "consequence": "",
                                      "endingSectionId": edge.target_node_id} for edge in seed.edges if edge.source_node_id == node.id]}
                        for node in seed.nodes if node.kind.value == "decision"],
            "joinReconciliations": {join.id: "" for join in seed.joins},
        }
    mapping = GraphMapDraft.model_validate(mapping)
    return GraphAuthoringDraft(binding_hash=binding_hash, mapping=mapping,
        row_hints={}, selected_node_id=mapping.topology.start_node_id, detached_endpoints={}, field_buffers={})
