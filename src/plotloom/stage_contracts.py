from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from plotloom.brief_contracts import ProjectBrief
from plotloom.canonical_schema import (
    SceneBeatPlanV2,
    StoryBibleV2,
    StoryboardV2,
    StoryGraphV2,
)
from plotloom.contract_identity import new_id, utc_now
from plotloom.domain_base import CamelModel


class StageName(str, Enum):
    STORY_BIBLE = "story_bible"
    STORY_GRAPH = "story_graph"
    SCENE_BEATS = "scene_beats"
    STORYBOARD = "storyboard"


AuthoringDraftScope = Literal[
    "brief",
    "story_bible",
    "story_graph",
    "scene_beats",
    "storyboard",
    "visual_intent",
    "image_direction",
    "review_buffer",
]


STAGE_ORDER: tuple[StageName, ...] = (
    StageName.STORY_BIBLE,
    StageName.STORY_GRAPH,
    StageName.SCENE_BEATS,
    StageName.STORYBOARD,
)


class StageStatus(str, Enum):
    MISSING = "missing"
    READY = "ready"
    STALE = "stale"


StagePayload = StoryBibleV2 | StoryGraphV2 | SceneBeatPlanV2 | StoryboardV2


class InitialStage(CamelModel):
    """One canonical stage supplied while a project is first created."""

    stage: StageName
    payload: dict[str, Any]

    @model_validator(mode="after")
    def normalize_payload(self) -> InitialStage:
        parsed = stage_payload_model(self.stage, schema_version=2).model_validate(
            self.payload
        )
        object.__setattr__(
            self, "payload", parsed.model_dump(mode="json", by_alias=False)
        )
        return self


def validate_initial_stage_prefix(stages: list[InitialStage]) -> None:
    supplied = [stage.stage for stage in stages]
    expected = list(STAGE_ORDER[: len(supplied)])
    if supplied != expected:
        raise ValueError("initialStages must be an ordered canonical stage prefix")


class EntityRevision(CamelModel):
    id: str = Field(default_factory=new_id)
    project_id: str
    stage: StageName
    revision: Annotated[int, Field(ge=1)]
    schema_version: Literal[2]
    parent_revision_id: str | None = None
    content_hash: str
    input_revisions: dict[StageName, int] = Field(default_factory=dict)
    payload: dict[str, Any]
    created_at: datetime = Field(default_factory=utc_now)


class StageHead(CamelModel):
    stage: StageName
    status: StageStatus = StageStatus.MISSING
    revision: Annotated[int, Field(ge=0)] = 0
    schema_version: Literal[2]
    entity_revision_id: str | None = None
    content_hash: str | None = None
    input_revisions: dict[StageName, int] = Field(default_factory=dict)
    stale_reasons: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_head_shape(self) -> StageHead:
        if self.status == StageStatus.MISSING:
            if (
                self.revision != 0
                or self.entity_revision_id is not None
                or self.content_hash is not None
            ):
                raise ValueError(
                    "missing stage heads cannot reference a canonical revision"
                )
        elif (
            self.revision < 1
            or self.entity_revision_id is None
            or self.content_hash is None
        ):
            raise ValueError("ready/stale stage heads require a canonical revision")
        return self


class StageEnvelope(CamelModel):
    head: StageHead
    # Only the current canonical contract is executable.
    payload: StagePayload | None = None


class AuthoringDraft(CamelModel):
    """One server-acknowledged editor buffer below a project home.

    Draft revisions are deliberately independent from canonical revisions:
    canonical Save is an explicit operation that may consume only the exact
    acknowledged draft revision it was based on.
    """

    project_id: str
    editor_scope: AuthoringDraftScope
    entity_id: str = Field(min_length=1, max_length=160)
    base_canonical_revision: Annotated[int, Field(ge=0)]
    draft_revision: Annotated[int, Field(ge=1)]
    payload: dict[str, Any]
    updated_at: datetime = Field(default_factory=utc_now)


class CanonicalSnapshot(CamelModel):
    project_id: str
    project_revision: Annotated[int, Field(ge=1)]
    brief: ProjectBrief
    stage_heads: dict[StageName, StageHead]
    snapshot_hash: str
    captured_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_complete_stage_set(self) -> CanonicalSnapshot:
        if set(self.stage_heads) != set(STAGE_ORDER):
            raise ValueError(
                "canonical snapshots must contain exactly the four pipeline stage heads"
            )
        if any(stage != head.stage for stage, head in self.stage_heads.items()):
            raise ValueError("canonical snapshot stage keys must match their heads")
        return self


def stage_payload_model(
    stage: StageName | str, schema_version: int
) -> type[StagePayload]:
    """Select the current contract; retired schema evidence is never executed."""

    if schema_version != 2:
        raise ValueError(f"unsupported canonical schema version: {schema_version}")
    return {
        StageName.STORY_BIBLE: StoryBibleV2,
        StageName.STORY_GRAPH: StoryGraphV2,
        StageName.SCENE_BEATS: SceneBeatPlanV2,
        StageName.STORYBOARD: StoryboardV2,
    }[StageName(stage)]


def upstream_stages(stage: StageName) -> tuple[StageName, ...]:
    index = STAGE_ORDER.index(stage)
    return STAGE_ORDER[:index]


def downstream_stages(stage: StageName) -> tuple[StageName, ...]:
    index = STAGE_ORDER.index(stage)
    return STAGE_ORDER[index + 1 :]
