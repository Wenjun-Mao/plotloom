"""Explicit input-bound machine echoes, never model-created canon authority."""
from __future__ import annotations


ECHO_CONTRACT_FILENAME = "outline-input-echoes.json"


def outline_echo_contract():
    return {"version": "plotloom.outline-input-echoes.v2",
            "candidateConstraints": {"forbiddenTopLevelFields": ["routePlan"]}}


class OutlineEchoError(ValueError):
    def __init__(self, path):
        self.path = path
        message = ("omit unsupported routePlan; keep authored explanations in existing Outline fields"
                   if path == "$.routePlan" else
                   "omit the optional echo or preserve its frozen input identity exactly")
        super().__init__(f"{path}: {message}")


def outline_echo_roles(candidate, original):
    """One owner shared by primary validation and complete language inventory."""
    if original.stage != "outline":
        return {}
    from .content_language_classifier import string_leaves

    contract = original.input_artifacts.get(ECHO_CONTRACT_FILENAME, {})
    if contract.get("version") == "plotloom.outline-input-echoes.v2" and "routePlan" in candidate:
        raise OutlineEchoError("$.routePlan")
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

    return roles
