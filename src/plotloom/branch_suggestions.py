"""Model prose bound to a frozen, code-planned Source structure."""
from pydantic import Field, field_validator
from .domain import CamelModel
from .generation.story_graph_topology import StoryGraphTopology
from .source_outline_contracts import SectionMap
from .source_structures import MAX_SOURCE_OPTIONS


class BranchNode(CamelModel):
    id: str
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=8000)

    @field_validator("title", "summary")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("branch prose must not be blank")
        return value.strip()


class BranchOption(CamelModel):
    id: str
    label: str = Field(min_length=1, max_length=300)
    consequence: str = Field(min_length=1, max_length=8000)

    @field_validator("label", "consequence")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("option prose must not be blank")
        return value.strip()


class BranchChoice(CamelModel):
    node_id: str
    question: str = Field(min_length=1, max_length=2000)
    options: list[BranchOption] = Field(min_length=2, max_length=MAX_SOURCE_OPTIONS)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("every choice needs a playback question")
        return value.strip()


class BranchJoin(CamelModel):
    id: str
    reconciliation: str = Field(min_length=1, max_length=8000)


class BranchSuggestion(CamelModel):
    nodes: list[BranchNode] = Field(min_length=1, max_length=128)
    choices: list[BranchChoice] = Field(max_length=128)
    joins: list[BranchJoin] = Field(max_length=128)
    clarifications: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("clarifications")
    @classmethod
    def nonblank(cls, value):
        if any(not item.strip() or len(item) > 2000 for item in value):
            raise ValueError("clarifications must be nonblank and bounded")
        return value


def bind_branches(proposal: BranchSuggestion, topology_data: dict) -> SectionMap:
    topology = StoryGraphTopology.model_validate(topology_data)
    if [node.id for node in proposal.nodes] != [node.id for node in topology.nodes]:
        raise ValueError("prose must preserve every planned node in order")
    if [choice.node_id for choice in proposal.choices] != [node.id for node in topology.nodes if node.kind.value == "decision"]:
        raise ValueError("every planned choice must be supplied exactly once")
    if [join.id for join in proposal.joins] != [join.id for join in topology.joins]:
        raise ValueError("every planned join must be supplied exactly once")
    choices = []
    for choice in proposal.choices:
        edges = [edge for edge in topology.edges if edge.source_node_id == choice.node_id]
        if [option.id for option in choice.options] != [edge.id for edge in edges]:
            raise ValueError("every planned option must be supplied exactly once in order")
        choices.append({"choiceId": choice.node_id, "sectionId": choice.node_id, "prompt": choice.question,
            "outcomes": [{"outcomeId": edge.id, "endingSectionId": edge.target_node_id, "label": option.label, "consequence": option.consequence} for edge, option in zip(edges, choice.options, strict=True)]})
    mapping = SectionMap.model_validate({"topology": topology_data,
        "sections": [{"sectionId": planned.id, "title": content.title, "summary": content.summary, "ending": planned.kind.value == "ending"} for planned, content in zip(topology.nodes, proposal.nodes, strict=True)],
        "choices": choices, "joinReconciliations": {join.id: join.reconciliation for join in proposal.joins}})
    mapping.validate_links()
    return mapping


class BranchTaskCandidate(CamelModel):
    job_id: str
    status: str
    suggestion: BranchSuggestion | None = None


class BranchTaskState(CamelModel):
    candidate: BranchTaskCandidate | None = None
    stale_reasons: list[str] = Field(default_factory=list)
    planned_topology: dict | None = None
    infeasible_reason: str | None = None
