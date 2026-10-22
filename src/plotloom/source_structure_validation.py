"""Exact receiving checks for current authored source structures."""
def validate_structure_links(mapping):
    topology = mapping.topology
    if [section.section_id for section in mapping.sections] != [node.id for node in topology.nodes]:
        raise ValueError("source sections must exactly match authored node order and identity")
    expected = [node for node in topology.nodes if node.kind.value == "decision"]
    if [choice.section_id for choice in mapping.choices] != [node.id for node in expected]:
        raise ValueError("every authored viewer choice must be present exactly once in order")
    for section, node in zip(mapping.sections, topology.nodes, strict=True):
        if section.ending != (node.kind.value == "ending") or not section.title.strip() or not section.summary.strip():
            raise ValueError("node prose or ending role is invalid")
    for choice in mapping.choices:
        edges = [edge for edge in topology.edges if edge.source_node_id == choice.section_id]
        if choice.choice_id != choice.section_id or not choice.prompt.strip():
            raise ValueError("choice identity or question is invalid")
        if [(option.outcome_id, option.ending_section_id) for option in choice.outcomes] != [(edge.id, edge.target_node_id) for edge in edges]:
            raise ValueError("options must preserve authored identity, order and target links")
        if any(not option.label.strip() or not option.consequence.strip() for option in choice.outcomes):
            raise ValueError("every option needs a label and subsequent story")
    if set(mapping.join_reconciliations) != {join.id for join in topology.joins} or any(not value.strip() for value in mapping.join_reconciliations.values()):
        raise ValueError("every authored join needs a narrative reconciliation")
