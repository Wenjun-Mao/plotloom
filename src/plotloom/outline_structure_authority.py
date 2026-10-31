"""F1 consumes either a real planner result or exact accepted author structure."""
from hashlib import sha256

from .creative_handoff_identity import canonical_json
from .source_outline_contracts import SourceMaterial, validate_section_map_graph
from .source_structures import compile_structure, planned_structure

SOURCE_STRUCTURE_FILENAME = "source-structure.json"
SOURCE_STRUCTURE_VERSION = "source.authored-structure.v1"


def outline_structure_inputs(project_id, brief, material: SourceMaterial):
    if material.authored_structure is None:
        return {"story-topology.json": planned_structure(project_id, brief).model_dump(mode="json", by_alias=True)}
    material.authored_structure.validate_links()
    validate_section_map_graph(compile_structure(material.authored_structure), brief)
    return {SOURCE_STRUCTURE_FILENAME: {"version": SOURCE_STRUCTURE_VERSION,
        "sourceHash": sha256(canonical_json(material.model_dump(mode="json", by_alias=True))).hexdigest(),
        "structure": material.authored_structure.model_dump(mode="json", by_alias=True)}}


def outline_structure_instructions(material: SourceMaterial):
    if material.authored_structure is None:
        return "Read inputs/story-topology.json: trusted code planned the feasible Brief structure. Author prose around every viewer choice, distinct ending and reconvergence without altering topology or treating episodes as route nodes. "
    return ("Read inputs/source-structure.json: this is the exact accepted author's structure, bound to sourceHash, not a generic planner result. "
        "Preserve every node, edge, choice label, route and ending in this source authority. Routes may have different numbers of choices within the Brief bound. "
        "Do not invent a planner seed, extra choice, routePlan or storyTopology echo. An optional sourceStructure echo must copy the entire frozen artifact exactly. ")
