"""Explicit input-bound machine echoes, never model-created canon authority."""
from __future__ import annotations


ECHO_CONTRACT_FILENAME = "outline-input-echoes.json"


def outline_echo_contract():
    return {"version": "plotloom.outline-input-echoes.v1", "routeLocalId": "R{oneBasedIndex:02d}"}


class OutlineEchoError(ValueError):
    def __init__(self, path):
        self.path = path
        super().__init__(f"{path}: omit the optional echo or preserve its frozen input identity exactly")


def outline_echo_roles(candidate, original):
    """One owner shared by primary validation and complete language inventory."""
    if original.stage != "outline":
        return {}
    from .content_language_classifier import string_leaves

    roles = {}

    def exact(path, value, expected, role="stable_identity", source_path=None):
        from .creative_handoff_identity import canonical_json
        if canonical_json(value) != canonical_json(expected):
            raise OutlineEchoError(path)
        for leaf, text in string_leaves(value, path):
            item = {"role": role}
            if source_path is not None and text:
                item["sourceSpan"] = {"path": source_path + leaf[len(path):],
                                      "start": 0, "end": len(text), "text": text}
            roles[leaf] = item

    settings = original.input_artifacts.get("outline-settings.json", {})
    params = candidate.get("params", {})
    if not isinstance(params, dict):
        raise OutlineEchoError("$.params")
    # These are stored IDs/enums, not the generated readable genre/style prose.
    for key in ("language", "aspectRatio", "shotCountPolicy", "genreSelections", "visualStyleSelections"):
        if key in params:
            if key not in settings:
                raise OutlineEchoError("$.params." + key)
            exact("$.params." + key, params[key], settings[key])

    if "sourceMetadata" in candidate:
        metadata = candidate["sourceMetadata"]
        allowed = {"kind", "title", "attribution", "rightsDeclaration", "adaptationIntent",
                   "inventedAdditions", "briefOrigin"}
        if not isinstance(metadata, dict) or set(metadata) - allowed:
            raise OutlineEchoError("$.sourceMetadata")
        for key, value in metadata.items():
            exact("$.sourceMetadata." + key, value, original.source.get(key),
                  role="stable_identity" if key in {"kind", "briefOrigin"} else "exact_source",
                  source_path=None if key in {"kind", "briefOrigin"} else "$.source." + key)

    topology = original.input_artifacts.get("story-topology.json")
    if "storyTopology" in candidate:
        from .generation.story_graph_topology_contracts import StoryGraphTopology
        if topology is None:
            raise OutlineEchoError("$.storyTopology")
        StoryGraphTopology.model_validate(topology)
        exact("$.storyTopology", candidate["storyTopology"], topology)

    plan = candidate.get("routePlan")
    if plan is None:
        return roles
    if not isinstance(plan, dict) or topology is None:
        raise OutlineEchoError("$.routePlan")
    from .generation.story_graph_topology_contracts import StoryGraphTopology
    parsed = StoryGraphTopology.model_validate(topology)
    nodes = {node.id: node for node in parsed.nodes}
    edges = {edge.id: edge for edge in parsed.edges}

    def references(items, field, allowed, prefix):
        if not isinstance(items, list):
            raise OutlineEchoError(prefix)
        for index, item in enumerate(items):
            path = f"{prefix}[{index}].{field}"
            if not isinstance(item, dict):
                raise OutlineEchoError(path)
            if field in item:
                if not isinstance(item[field], str) or item[field] not in allowed:
                    raise OutlineEchoError(path)
                exact(path, item[field], item[field])

    references(plan.get("nodeBindings", []), "nodeId", nodes, "$.routePlan.nodeBindings")
    references(plan.get("choices", []), "edgeId", {key for key, edge in edges.items() if edge.kind == "choice"}, "$.routePlan.choices")
    routes = plan.get("routes", [])
    if not isinstance(routes, list):
        raise OutlineEchoError("$.routePlan.routes")
    pairs = {(edge.source_node_id, edge.target_node_id) for edge in parsed.edges}
    for index, route in enumerate(routes):
        path = f"$.routePlan.routes[{index}]"
        if not isinstance(route, dict):
            raise OutlineEchoError(path)
        ids = route.get("nodeIds")
        if (not isinstance(ids, list) or not ids or any(not isinstance(node, str) or node not in nodes for node in ids)
                or ids[0] != parsed.start_node_id or nodes[ids[-1]].kind != "ending"
                or any(pair not in pairs for pair in zip(ids, ids[1:]))):
            raise OutlineEchoError(path + ".nodeIds")
        exact(path + ".nodeIds", ids, ids)
        if "id" in route:
            exact(path + ".id", route["id"], f"R{index + 1:02d}")
    return roles
