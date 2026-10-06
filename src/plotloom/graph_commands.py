"""Typed structural intent, immutable previews and exact impact identities."""
from typing import Annotated, Literal

from pydantic import Field

from .canonical_schema import StableId
from .domain_base import CamelModel
from .graph_authoring_drafts import GraphAuthoringDraft


class NewGraphNode(CamelModel):
    node_id: StableId
    kind: Literal["scene", "decision", "join", "ending"]
    row_hint: int = Field(ge=0, le=128)
    create_pending_choices: bool


class AddGraphNode(NewGraphNode):
    operation: Literal["add"]
    source_node_id: StableId | None
    target_node_id: StableId | None
    incoming_edge_id: StableId
    outgoing_edge_id: StableId


class InsertGraphNode(NewGraphNode):
    operation: Literal["insert"]
    edge_id: StableId | None
    continuation_edge_id: StableId


class ReuseGraphNode(CamelModel):
    operation: Literal["reuse"]
    node_id: StableId
    row_hint: int = Field(ge=0, le=128)
    source_node_id: StableId | None
    target_node_id: StableId | None
    incoming_edge_id: StableId
    outgoing_edge_id: StableId


class RetargetGraphEdge(CamelModel):
    operation: Literal["retarget"]
    edge_id: StableId
    endpoint: Literal["source", "target"]
    node_id: StableId | None


class ReplaceGraphInput(CamelModel):
    operation: Literal["replace_input"]
    node_id: StableId
    prior_edge_id: StableId | None
    chosen_edge_id: StableId


class DeleteGraphNode(CamelModel):
    operation: Literal["delete"]
    node_id: StableId
    method: Literal["only_delete", "safe_bypass"]


class ReassignGraphStart(CamelModel):
    operation: Literal["set_start"]
    node_id: StableId


class ChangeGraphNodeKind(CamelModel):
    operation: Literal["set_kind"]
    node_id: StableId
    kind: Literal["scene", "decision", "join", "ending"]
    footage_mode: Literal["footage", "route_only"]


class AddGraphEdge(CamelModel):
    operation: Literal["add_edge"]
    edge_id: StableId
    source_node_id: StableId
    target_node_id: StableId | None


class RemoveGraphEdge(CamelModel):
    operation: Literal["remove_edge"]
    edge_id: StableId


class AddGraphJoin(CamelModel):
    operation: Literal["add_join"]
    join_id: StableId
    node_id: StableId


class RemoveGraphJoin(CamelModel):
    operation: Literal["remove_join"]
    join_id: StableId


GraphCommand = Annotated[
    AddGraphNode | InsertGraphNode | RetargetGraphEdge | DeleteGraphNode | ReassignGraphStart
    | ChangeGraphNodeKind | AddGraphEdge | RemoveGraphEdge | AddGraphJoin | RemoveGraphJoin | ReuseGraphNode | ReplaceGraphInput,
    Field(discriminator="operation"),
]


class GraphCommandRequest(CamelModel):
    expected_draft_revision: int = Field(ge=1)
    command: GraphCommand


class GraphCommandApplyRequest(GraphCommandRequest):
    preview_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class GraphCommandImpact(CamelModel):
    added_node_ids: list[str]
    removed_node_ids: list[str]
    added_edge_ids: list[str]
    removed_edge_ids: list[str]
    changed_edge_ids: list[str]
    affected_join_ids: list[str]
    retained_node_ids: list[str]
    pending_edge_ids: list[str]
    messages: list[str]


class GraphCommandPreview(CamelModel):
    draft_revision: int
    binding_hash: str
    command: GraphCommand
    result: GraphAuthoringDraft
    impact: GraphCommandImpact
    preview_hash: str
