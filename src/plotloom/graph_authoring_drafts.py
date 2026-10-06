"""One recoverable current source-graph draft, distinct from playable admission."""
from typing import Literal

from pydantic import Field, model_validator

from .canonical_schema import StableId
from .domain_base import CamelModel
from .generation.story_graph_topology import StoryGraphTopology
from .source_graph_structure import SourceStructureEdge, SourceStructureJoin, SourceStructureNode
from .source_outline_contracts import SectionMap


class DraftStorySection(CamelModel):
    section_id: StableId
    title: str = Field(max_length=300)
    summary: str = Field(max_length=8_000)
    ending: bool
    footage_mode: Literal["footage", "route_only"]


class DetachedEndpoint(CamelModel):
    node_id: StableId
    title: str
    kind: str


class DraftSourceEdge(SourceStructureEdge):
    source_node_id: StableId | None
    target_node_id: StableId | None


class DraftSourceJoin(SourceStructureJoin):
    incoming_node_ids: list[StableId] = Field(max_length=128)


class DraftSourceStructure(CamelModel):
    start_node_id: StableId | None
    nodes: list[SourceStructureNode] = Field(max_length=128)
    edges: list[DraftSourceEdge]
    joins: list[DraftSourceJoin]


class DraftBranchOutcome(CamelModel):
    outcome_id: StableId
    label: str = Field(max_length=300)
    consequence: str = Field(max_length=8_000)
    ending_section_id: StableId | None


class DraftSectionChoice(CamelModel):
    choice_id: StableId
    section_id: StableId
    prompt: str = Field(max_length=2_000)
    outcomes: list[DraftBranchOutcome] = Field(max_length=6)


class GraphMapDraft(CamelModel):
    seed_topology: StoryGraphTopology
    topology_origin: Literal["planner", "author"]
    topology: DraftSourceStructure
    sections: list[DraftStorySection] = Field(max_length=128)
    choices: list[DraftSectionChoice]
    join_reconciliations: dict[str, str]

    @model_validator(mode="after")
    def require_section_identity(self):
        if [node.id for node in self.topology.nodes] != [section.section_id for section in self.sections]:
            raise ValueError("draft sections must exactly match node identity and order; prose may be blank")
        return self

    def admitted_mapping(self) -> SectionMap:
        """Current completeness receiving boundary; no repair or inferred fields."""
        return SectionMap.model_validate(self.model_dump(mode="json", by_alias=True))


class GraphAuthoringDraft(CamelModel):
    binding_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    mapping: GraphMapDraft
    row_hints: dict[StableId, int]
    selected_node_id: StableId | None
    detached_endpoints: dict[StableId, dict[Literal["source", "target"], DetachedEndpoint]]
    field_buffers: dict[str, str]

    def admitted_mapping(self) -> SectionMap:
        if self.field_buffers:
            raise ValueError("未完成的字段输入仍保留；请先检查并提交字段内容。")
        return self.mapping.admitted_mapping()
