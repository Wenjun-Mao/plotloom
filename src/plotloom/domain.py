from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Annotated, Any, Literal
from urllib.parse import parse_qsl, urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    """Canonical Python models with a strict camelCase HTTP representation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        validate_assignment=True,
    )


class StageName(str, Enum):
    STORY_BIBLE = "story_bible"
    STORY_GRAPH = "story_graph"
    SCENE_BEATS = "scene_beats"
    STORYBOARD = "storyboard"


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


class ProjectLifecycleStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    QUARANTINED = "quarantined"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_RUN_STATUSES: frozenset[RunStatus] = frozenset(
    {
        RunStatus.SUCCEEDED,
        RunStatus.QUARANTINED,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    }
)


class RunKind(str, Enum):
    PIPELINE = "pipeline"
    REBUILD = "rebuild"
    REPAIR = "repair"


class AttemptStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationAttemptKind(str, Enum):
    """Why a durable provider attempt exists within one frozen work unit."""

    PRIMARY = "primary"
    CORRECTION = "correction"


class WorkUnitStatus(str, Enum):
    """Lifecycle of one bounded provider work unit.

    This is deliberately separate from ``AttemptStatus``: a unit may have
    several attempts over its lifetime, while an ambiguous dispatched attempt
    leaves the unit in ``OUTCOME_UNKNOWN`` and must not be replayed blindly.
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    CANCELLED = "cancelled"
    OUTCOME_UNKNOWN = "outcome_unknown"


TERMINAL_WORK_UNIT_STATUSES: frozenset[WorkUnitStatus] = frozenset(
    {
        WorkUnitStatus.SUCCEEDED,
        WorkUnitStatus.FAILED,
        WorkUnitStatus.QUARANTINED,
        WorkUnitStatus.CANCELLED,
        WorkUnitStatus.OUTCOME_UNKNOWN,
    }
)


class WorkUnitFailureDisposition(str, Enum):
    """Explicit terminal meaning of a known failed work-unit attempt.

    Stable outcome codes explain what happened, but they are deliberately not
    parsed as an implicit state classifier. The application boundary must say
    whether it rejected model content for review or recorded an execution
    failure.
    """

    FAILED = "failed"
    QUARANTINED = "quarantined"


class FragmentReuseKind(str, Enum):
    """Why a child repair run can reuse a verified parent fragment."""

    UPSTREAM = "upstream"
    SIBLING = "sibling"


class StoryNodeKind(str, Enum):
    START = "start"
    SCENE = "scene"
    DECISION = "decision"
    JOIN = "join"
    ENDING = "ending"


class StoryEdgeKind(str, Enum):
    CONTINUATION = "continuation"
    CHOICE = "choice"


class CoverageRole(str, Enum):
    PRIMARY = "primary"
    SUPPORTING = "supporting"


class ShotSize(str, Enum):
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    FULL = "full"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    INSERT = "insert"


class ArtifactKind(str, Enum):
    PROMPT = "prompt"
    RESPONSE = "response"
    VALIDATION = "validation"
    CANDIDATE = "candidate"
    CANONICAL = "canonical"
    MEDIA = "media"


class MediaKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class MediaTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_MEDIA_TASK_STATUSES: frozenset[MediaTaskStatus] = frozenset(
    {
        MediaTaskStatus.SUCCEEDED,
        MediaTaskStatus.FAILED,
        MediaTaskStatus.CANCELLED,
    }
)


class ProjectBrief(CamelModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    synopsis: Annotated[str, Field(min_length=1)]
    genre: str | None = None
    visual_style: str | None = None
    language: str = "zh-CN"
    aspect_ratio: str = "16:9"
    target_playthrough_seconds: Annotated[int, Field(ge=1)] = 180
    decision_points_per_path: Annotated[int, Field(ge=0)] = 2
    ending_count: Annotated[int, Field(ge=1)] = 3
    node_budget: Annotated[int, Field(ge=1)] = 10
    max_out_degree: Annotated[int, Field(ge=1)] = 3
    desired_join_count: Annotated[int, Field(ge=0)] = 1
    shots_per_scene_min: Annotated[int, Field(ge=1)] = 2
    shots_per_scene_max: Annotated[int, Field(ge=1)] = 4

    @model_validator(mode="after")
    def validate_internal_limits(self) -> ProjectBrief:
        if self.shots_per_scene_min > self.shots_per_scene_max:
            raise ValueError("shots_per_scene_min must not exceed shots_per_scene_max")
        if self.ending_count > self.node_budget:
            raise ValueError("ending_count must not exceed node_budget")
        return self


class Character(CamelModel):
    id: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]
    role: str | None = None
    description: str = ""
    goal: str = ""
    traits: list[str] = Field(default_factory=list)
    visual_identity: str = ""
    continuity_rules: list[str] = Field(default_factory=list)


class Location(CamelModel):
    id: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]
    description: str = ""
    visual_identity: str = ""
    continuity_rules: list[str] = Field(default_factory=list)


class Prop(CamelModel):
    id: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]
    description: str = ""
    visual_identity: str = ""
    continuity_rules: list[str] = Field(default_factory=list)


class StoryBible(CamelModel):
    logline: Annotated[str, Field(min_length=1)]
    premise: Annotated[str, Field(min_length=1)]
    genre: str = ""
    tone: str = ""
    audience: str = ""
    narrative_promise: str = ""
    visual_language: str = ""
    themes: list[str] = Field(default_factory=list)
    world_rules: list[str] = Field(default_factory=list)
    known_facts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    source_notes: list[str] = Field(default_factory=list)
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    props: list[Prop] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entity_ids(self) -> StoryBible:
        for label, entities in (
            ("character", self.characters),
            ("location", self.locations),
            ("prop", self.props),
        ):
            ids = [entity.id for entity in entities]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate {label} ids")
        return self


class StoryNode(CamelModel):
    id: Annotated[str, Field(min_length=1)]
    title: Annotated[str, Field(min_length=1)]
    summary: Annotated[str, Field(min_length=1)]
    kind: StoryNodeKind


class StoryEdge(CamelModel):
    id: Annotated[str, Field(min_length=1)]
    source_node_id: Annotated[str, Field(min_length=1)]
    target_node_id: Annotated[str, Field(min_length=1)]
    kind: StoryEdgeKind = StoryEdgeKind.CONTINUATION
    choice_text: str | None = None
    state_effects: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def choice_edges_have_copy(self) -> StoryEdge:
        if self.kind == StoryEdgeKind.CHOICE and not self.choice_text:
            raise ValueError("choice edges require choice_text")
        return self


class JoinContract(CamelModel):
    id: Annotated[str, Field(min_length=1)]
    join_node_id: Annotated[str, Field(min_length=1)]
    incoming_node_ids: Annotated[list[str], Field(min_length=2)]
    required_state_keys: list[str] = Field(default_factory=list)
    allowed_differences: list[str] = Field(default_factory=list)
    reconciliation: str = ""
    notes: str = ""


class StoryGraph(CamelModel):
    start_node_id: Annotated[str, Field(min_length=1)]
    nodes: Annotated[list[StoryNode], Field(min_length=1)]
    edges: list[StoryEdge] = Field(default_factory=list)
    join_contracts: list[JoinContract] = Field(default_factory=list)


class ContinuityState(CamelModel):
    facts: dict[str, Any] = Field(default_factory=dict)
    character_states: dict[str, str] = Field(default_factory=dict)
    prop_states: dict[str, str] = Field(default_factory=dict)
    location_state: str | None = None
    screen_direction: str | None = None
    lighting: str | None = None
    sound: str | None = None
    notes: list[str] = Field(default_factory=list)


class DramaticScene(CamelModel):
    id: Annotated[str, Field(min_length=1)]
    story_node_id: Annotated[str, Field(min_length=1)]
    title: Annotated[str, Field(min_length=1)]
    objective: Annotated[str, Field(min_length=1)]
    location_id: str | None = None
    character_ids: list[str] = Field(default_factory=list)
    beat_ids: Annotated[list[str], Field(min_length=1)]
    entry_state: ContinuityState = Field(default_factory=ContinuityState)
    exit_state: ContinuityState = Field(default_factory=ContinuityState)


class Beat(CamelModel):
    id: Annotated[str, Field(min_length=1)]
    scene_id: Annotated[str, Field(min_length=1)]
    order: Annotated[int, Field(ge=1)]
    description: Annotated[str, Field(min_length=1)]
    purpose: Annotated[str, Field(min_length=1)]
    visible_event: str = ""
    dialogue: str = ""
    immediate_result: str = ""
    dramatic_change: str = ""
    entry_state: ContinuityState = Field(default_factory=ContinuityState)
    exit_state: ContinuityState = Field(default_factory=ContinuityState)
    continuity_anchors: list[str] = Field(default_factory=list)
    continuity_delta: dict[str, Any] = Field(default_factory=dict)


class SceneBeatPlan(CamelModel):
    scenes: list[DramaticScene] = Field(default_factory=list)
    beats: list[Beat] = Field(default_factory=list)


class Shot(CamelModel):
    id: Annotated[str, Field(min_length=1)]
    scene_id: Annotated[str, Field(min_length=1)]
    order: Annotated[int, Field(ge=1)]
    title: Annotated[str, Field(min_length=1)]
    shot_size: ShotSize
    duration_seconds: Annotated[float, Field(gt=0)]
    camera_angle: str = ""
    camera_movement: str = ""
    composition: str = ""
    visual_intent: str = ""
    motion_intent: str = ""
    action: str = ""
    dialogue: str = ""
    audio: str = ""
    transition: str = ""
    character_ids: list[str] = Field(default_factory=list)
    location_id: str | None = None
    prop_ids: list[str] = Field(default_factory=list)
    entry_state: ContinuityState = Field(default_factory=ContinuityState)
    exit_state: ContinuityState = Field(default_factory=ContinuityState)


class ShotBeatLink(CamelModel):
    shot_id: Annotated[str, Field(min_length=1)]
    beat_id: Annotated[str, Field(min_length=1)]
    role: CoverageRole = CoverageRole.PRIMARY
    coverage_weight: Annotated[float, Field(gt=0, le=1)] = 1.0


class Storyboard(CamelModel):
    shots: list[Shot] = Field(default_factory=list)
    shot_beat_links: list[ShotBeatLink] = Field(default_factory=list)


StagePayload = StoryBible | StoryGraph | SceneBeatPlan | Storyboard


class InitialStage(CamelModel):
    """One canonical stage supplied while a project is first created."""

    stage: StageName
    payload: dict[str, Any]

    @model_validator(mode="after")
    def normalize_payload(self) -> InitialStage:
        parsed = stage_payload_model(self.stage).model_validate(self.payload)
        object.__setattr__(self, "payload", parsed.model_dump(mode="json", by_alias=False))
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
    parent_revision_id: str | None = None
    content_hash: str
    input_revisions: dict[StageName, int] = Field(default_factory=dict)
    payload: dict[str, Any]
    created_at: datetime = Field(default_factory=utc_now)


class StageHead(CamelModel):
    stage: StageName
    status: StageStatus = StageStatus.MISSING
    revision: Annotated[int, Field(ge=0)] = 0
    entity_revision_id: str | None = None
    content_hash: str | None = None
    input_revisions: dict[StageName, int] = Field(default_factory=dict)
    stale_reasons: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_head_shape(self) -> StageHead:
        if self.status == StageStatus.MISSING:
            if self.revision != 0 or self.entity_revision_id is not None or self.content_hash is not None:
                raise ValueError("missing stage heads cannot reference a canonical revision")
        elif self.revision < 1 or self.entity_revision_id is None or self.content_hash is None:
            raise ValueError("ready/stale stage heads require a canonical revision")
        return self


class StageEnvelope(CamelModel):
    head: StageHead
    payload: StagePayload | None = None


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
            raise ValueError("canonical snapshots must contain exactly the four pipeline stage heads")
        if any(stage != head.stage for stage, head in self.stage_heads.items()):
            raise ValueError("canonical snapshot stage keys must match their heads")
        return self


class Project(CamelModel):
    id: str = Field(default_factory=new_id)
    revision: Annotated[int, Field(ge=1)] = 1
    lifecycle_revision: Annotated[int, Field(ge=1)] = 1
    lifecycle_status: ProjectLifecycleStatus = ProjectLifecycleStatus.ACTIVE
    archived_at: datetime | None = None
    brief: ProjectBrief
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_lifecycle_shape(self) -> Project:
        if self.lifecycle_status == ProjectLifecycleStatus.ACTIVE and self.archived_at is not None:
            raise ValueError("active projects cannot have an archived_at timestamp")
        if self.lifecycle_status == ProjectLifecycleStatus.ARCHIVED and self.archived_at is None:
            raise ValueError("archived projects require an archived_at timestamp")
        return self


class ProjectCreation(Project):
    """Authoritative aggregate returned by project creation and replay."""

    stages: list[StageEnvelope]


class LatestRunSummary(CamelModel):
    id: str
    kind: RunKind
    status: RunStatus
    requested_stages: list[StageName]
    created_at: datetime
    finished_at: datetime | None = None


class ProjectSummary(Project):
    stage_statuses: dict[StageName, StageStatus]
    latest_run: LatestRunSummary | None = None


class ProjectDuplicateResult(CamelModel):
    project: ProjectCreation
    copied_through: StageName | None = None
    omitted_stages: list[StageName]


class RepairSource(CamelModel):
    """Exact immutable evidence selected when an explicit repair is enqueued."""

    failed_attempt_id: Annotated[str, Field(min_length=1)]
    response_artifact_id: Annotated[str, Field(min_length=1)]
    validation_artifact_id: Annotated[str, Field(min_length=1)]
    reused_candidate_artifact_ids: dict[StageName, str] = Field(default_factory=dict)

    @field_validator("reused_candidate_artifact_ids")
    @classmethod
    def validate_candidate_ids(cls, value: dict[StageName, str]) -> dict[StageName, str]:
        if any(not artifact_id.strip() for artifact_id in value.values()):
            raise ValueError("reused candidate artifact IDs must not be blank")
        return value


class GenerationRun(CamelModel):
    id: str = Field(default_factory=new_id)
    project_id: str
    kind: RunKind
    parent_run_id: str | None = None
    repair_stage: StageName | None = None
    repair_source: RepairSource | None = None
    work_unit_repair_scope_id: str | None = None
    provider_snapshot: dict[str, Any] = Field(default_factory=dict)
    requested_stages: list[StageName]
    status: RunStatus = RunStatus.QUEUED
    canonical_snapshot: CanonicalSnapshot
    instructions: str | None = None
    legacy_unsealed: bool = False
    result_revision_ids: list[str] = Field(default_factory=list)
    error: str | None = None
    failure_code: str | None = None
    failed_stage: StageName | None = None
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("provider_snapshot", mode="before")
    @classmethod
    def validate_provider_snapshot(cls, value: Any) -> dict[str, Any]:
        return validate_public_provider_snapshot(value)

    @model_validator(mode="after")
    def validate_repair_lineage(self) -> GenerationRun:
        if not self.requested_stages:
            raise ValueError("generation runs require at least one requested stage")
        if len(self.requested_stages) != len(set(self.requested_stages)):
            raise ValueError("requested_stages must not contain duplicates")
        if self.requested_stages != [stage for stage in STAGE_ORDER if stage in self.requested_stages]:
            raise ValueError("requested_stages must follow canonical stage order")
        first_index = STAGE_ORDER.index(self.requested_stages[0])
        expected_range = list(
            STAGE_ORDER[first_index : first_index + len(self.requested_stages)]
        )
        if self.requested_stages != expected_range:
            raise ValueError("requested_stages must form one contiguous canonical stage range")
        if self.kind == RunKind.REPAIR:
            if self.parent_run_id is None or self.repair_stage is None:
                raise ValueError("repair runs require parentRunId and repairStage")
            if self.repair_stage not in self.requested_stages:
                raise ValueError("repairStage must belong to requestedStages")
            if self.work_unit_repair_scope_id is not None:
                if self.repair_source is not None:
                    raise ValueError("exact work-unit repairs cannot carry legacy repairSource")
                return self
            if self.repair_source is None:
                if self.status not in TERMINAL_RUN_STATUSES:
                    raise ValueError("non-terminal repair runs require repairSource")
                return self
            reused_stages = set(self.repair_source.reused_candidate_artifact_ids)
            repair_index = self.requested_stages.index(self.repair_stage)
            expected_reused = set(self.requested_stages[:repair_index])
            if reused_stages != expected_reused:
                raise ValueError("repairSource must freeze one candidate for every reused requested stage")
        elif (
            self.parent_run_id is not None
            or self.repair_stage is not None
            or self.repair_source is not None
            or self.work_unit_repair_scope_id is not None
        ):
            raise ValueError("only repair runs may carry repair lineage")
        return self


class GenerationAttempt(CamelModel):
    id: str = Field(default_factory=new_id)
    run_id: str
    work_unit_id: str | None = None
    stage: StageName
    attempt_number: Annotated[int, Field(ge=1)]
    attempt_kind: GenerationAttemptKind = GenerationAttemptKind.PRIMARY
    source_attempt_id: str | None = None
    status: AttemptStatus
    provider: str | None = None
    model: str | None = None
    error: str | None = None
    dispatched_at: datetime | None = None
    response_persisted_at: datetime | None = None
    provider_request_id: str | None = None
    outcome_unknown: bool = False
    outcome_code: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None


class Artifact(CamelModel):
    id: str = Field(default_factory=new_id)
    run_id: str
    attempt_id: str | None = None
    work_unit_id: str | None = None
    source_artifact_id: str | None = None
    stage: StageName | None = None
    kind: ArtifactKind
    media_type: str = "application/json"
    content: Any
    content_hash: str
    created_at: datetime = Field(default_factory=utc_now)


class MediaTask(CamelModel):
    id: str = Field(default_factory=new_id)
    project_id: str
    shot_id: str
    storyboard_revision: Annotated[int, Field(ge=1)]
    kind: MediaKind
    status: MediaTaskStatus = MediaTaskStatus.QUEUED
    derived_prompt: Annotated[str, Field(min_length=1)]
    prompt_components: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = None
    public_settings: dict[str, Any] = Field(default_factory=dict)
    provider_task_id: str | None = None
    output_uri: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("provider")
    @classmethod
    def validate_public_provider_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if contains_secret_value(normalized):
            raise ValueError("provider must be a public identifier, not a credential")
        return normalized or None

    @model_validator(mode="after")
    def validate_lifecycle_and_public_settings(self) -> MediaTask:
        if contains_secret_setting(self.public_settings) or contains_secret_value(
            self.public_settings
        ):
            raise ValueError("publicSettings must not contain credentials or other secrets")
        validate_public_base_urls(self.public_settings)
        if self.status == MediaTaskStatus.QUEUED:
            if self.started_at is not None or self.finished_at is not None:
                raise ValueError("queued media tasks cannot have lifecycle timestamps")
        elif self.status == MediaTaskStatus.RUNNING:
            if self.started_at is None or self.finished_at is not None:
                raise ValueError("running media tasks require startedAt and no finishedAt")
        else:
            if self.started_at is None or self.finished_at is None:
                raise ValueError("terminal media tasks require startedAt and finishedAt")
        if self.status == MediaTaskStatus.SUCCEEDED and not self.output_uri:
            raise ValueError("succeeded media tasks require outputUri")
        if self.status == MediaTaskStatus.FAILED and not self.error:
            raise ValueError("failed media tasks require an error")
        return self


class MediaPromptContext(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    brief: ProjectBrief
    story_bible: StoryBible
    shot: Shot
    storyboard_revision: Annotated[int, Field(ge=1)]


DEFAULT_PROVIDER_PROFILE_ID = "default"
DEFAULT_TEXT_PROVIDER = "openai-compatible"
DEFAULT_TEXT_BASE_URL = "https://api.atlascloud.ai/v1"
DEFAULT_TEXT_MODEL = "deepseek-v3"


class ProviderAuthMode(str, Enum):
    """The only credential behavior a trusted local provider may declare."""

    NONE = "none"
    BEARER = "bearer"


class ProviderProfileCapabilities(CamelModel):
    """Declared OpenAI-compatible text-model capabilities, not probe results."""

    chat_completions: bool = True
    json_object: bool = False
    json_schema: bool = False


class PublicProviderConfiguration(CamelModel):
    """The public, persisted fields of the local trusted default profile.

    Plotloom currently has one locally saved profile rather than an arbitrary
    browser-selected profile registry.  The fixed ID makes that control-plane
    boundary explicit while keeping the established provider-settings API
    compatible.  Its revision and digest are attached only when the profile is
    materialized as a snapshot below.
    """

    profile_id: str = DEFAULT_PROVIDER_PROFILE_ID
    text_provider: str | None = None
    text_base_url: str | None = None
    text_model: str | None = None
    text_auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER
    text_capabilities: ProviderProfileCapabilities = Field(
        default_factory=ProviderProfileCapabilities
    )
    text_context_window_tokens: Annotated[int, Field(ge=1)] = 32_768
    text_max_output_tokens: Annotated[int, Field(ge=1)] = 8_192
    text_temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.2
    text_max_concurrency: Annotated[int, Field(ge=1, le=32)] = 1
    text_connect_timeout_seconds: Annotated[float, Field(gt=0.0, le=300.0)] = 10.0
    text_attempt_timeout_seconds: Annotated[float, Field(gt=0.0, le=3_600.0)] = 300.0
    redirect_policy: Literal["no_follow"] = "no_follow"
    image_provider: str | None = None
    image_base_url: str | None = None
    image_model: str | None = None
    image_auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER
    video_provider: str | None = None
    video_base_url: str | None = None
    video_model: str | None = None
    video_auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER

    @model_validator(mode="before")
    @classmethod
    def reject_secret_material(cls, value: Any) -> Any:
        if contains_secret_setting(value) or contains_secret_value(value):
            raise ValueError("public provider configuration must not contain secrets")
        return value

    @field_validator("profile_id")
    @classmethod
    def validate_local_profile_id(cls, value: str) -> str:
        if value != DEFAULT_PROVIDER_PROFILE_ID:
            raise ValueError("only the trusted default provider profile may be selected")
        return value

    @field_validator(
        "text_provider",
        "text_model",
        "image_provider",
        "image_model",
        "video_provider",
        "video_model",
    )
    @classmethod
    def normalize_public_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("text_base_url", "image_base_url", "video_base_url")
    @classmethod
    def validate_public_api_root(cls, value: str | None) -> str | None:
        return validate_public_api_root(value)

    @model_validator(mode="after")
    def validate_text_token_budget(self) -> PublicProviderConfiguration:
        if self.text_max_output_tokens >= self.text_context_window_tokens:
            raise ValueError(
                "textMaxOutputTokens must be smaller than textContextWindowTokens"
            )
        return self


class ProviderSnapshot(PublicProviderConfiguration):
    """Canonical, secret-free provider profile frozen into a generation run."""

    # PublicProviderConfiguration keeps these optional because an empty saved
    # settings row means "use environment defaults". A run snapshot has crossed
    # that boundary and must be fully resolved before it is hashed and queued.
    text_provider: str = DEFAULT_TEXT_PROVIDER
    text_base_url: str = DEFAULT_TEXT_BASE_URL
    text_model: str = DEFAULT_TEXT_MODEL
    profile_version: Annotated[int, Field(ge=0)] = 0
    profile_hash: str = ""

    @model_validator(mode="after")
    def require_resolved_text_profile(self) -> ProviderSnapshot:
        if not self.text_provider or not self.text_base_url or not self.text_model:
            raise ValueError(
                "provider snapshots require a resolved text provider, base URL, and model"
            )
        return self

    @model_validator(mode="after")
    def verify_profile_hash(self) -> ProviderSnapshot:
        payload = self.model_dump(
            mode="json",
            by_alias=False,
            include=set(ProviderSnapshot.model_fields) - {"profile_hash"},
        )
        expected = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest()
        if self.profile_hash and self.profile_hash != expected:
            raise ValueError("provider profile hash does not match its public fields")
        object.__setattr__(self, "profile_hash", expected)
        return self


PUBLIC_PROVIDER_SETTING_FIELDS: tuple[str, ...] = tuple(
    PublicProviderConfiguration.model_fields
)


class ProviderSettings(PublicProviderConfiguration):
    """Trusted default profile plus local availability and persistence metadata."""

    profile_version: Annotated[int, Field(ge=0)] = 0
    profile_hash: str = ""
    text_key_available: bool = False
    image_key_available: bool = False
    video_key_available: bool = False
    revision: Annotated[int, Field(ge=0)] = 0
    updated_at: datetime | None = None

    @field_validator("profile_id")
    @classmethod
    def validate_local_profile_id(cls, value: str) -> str:
        # The compatibility settings projection may expose whichever named
        # text profile is active. Frozen historical ProviderSnapshot retains
        # the original default-only validator above.
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value):
            raise ValueError("profileId must match [a-z][a-z0-9_]{0,62}")
        return value

    @model_validator(mode="after")
    def verify_profile_hash(self) -> ProviderSettings:
        # The compatibility endpoint may project a V2 named text profile. In
        # that case its already-validated V2 hash is carried through verbatim;
        # blank hashes retain the legacy singleton calculation below.
        if self.profile_hash:
            return self
        payload = self.model_dump(
            mode="json",
            by_alias=False,
            include=set(ProviderSnapshot.model_fields) - {"profile_hash"},
        )
        expected = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest()
        object.__setattr__(self, "profile_hash", expected)
        return self


class RunTrace(CamelModel):
    run: GenerationRun
    attempts: list[GenerationAttempt] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    snapshot_is_current: bool


class GenerationPlanTrace(CamelModel):
    """Secret-free run-level plan persisted alongside a generation run."""

    run_id: str
    plan_hash: str
    plan: dict[str, Any]


class StagePlanTrace(CamelModel):
    """One immutable stage plan and its resolved dependency fingerprint."""

    id: str
    run_id: str
    stage: StageName
    stage_plan_hash: str
    dependency_hash: str
    plan: dict[str, Any]


class GenerationWorkUnitTrace(CamelModel):
    """Durable work-unit record exposed for diagnosis, not prompt execution."""

    id: str
    run_id: str
    stage_plan_id: str
    stage: StageName
    sequence: Annotated[int, Field(ge=1)]
    selector: dict[str, Any]
    input_hash: str
    dependency_hash: str
    unit_dependency_hash: str
    budget: dict[str, Any]
    estimated_input_tokens: Annotated[int, Field(ge=0)]
    context_window_tokens: Annotated[int, Field(ge=1)]
    status: WorkUnitStatus


class FrozenFragmentReuseSource(CamelModel):
    """One parent candidate frozen into an exact repair scope.

    This is deliberately metadata-only.  The candidate and its complete
    producer evidence remain immutable artifacts owned by the parent run;
    a child may only create a separately-owned, trusted re-binding through a
    corresponding :class:`FragmentReuseBinding`.
    """

    kind: FragmentReuseKind
    stage: StageName
    source_work_unit_id: str = Field(min_length=1)
    source_stage_plan_id: str = Field(min_length=1)
    source_stage_plan_hash: str = Field(min_length=1)
    source_generation_plan_hash: str = Field(min_length=1)
    source_selector: dict[str, Any]
    source_dependency_hash: str = Field(min_length=1)
    source_unit_dependency_hash: str = Field(min_length=1)
    source_input_hash: str = Field(min_length=1)
    source_producer_attempt_id: str = Field(min_length=1)
    source_response_artifact_id: str = Field(min_length=1)
    source_validation_artifact_id: str = Field(min_length=1)
    source_candidate_artifact_id: str = Field(min_length=1)
    source_candidate_content_hash: str = Field(min_length=1)


class WorkUnitRepairScope(CamelModel):
    """Immutable evidence and contract boundary for one exact child repair."""

    child_run_id: str = Field(min_length=1)
    parent_run_id: str = Field(min_length=1)
    target_work_unit_id: str = Field(min_length=1)
    stage: StageName
    source_generation_plan_hash: str = Field(min_length=1)
    source_provider_profile_hash: str = Field(min_length=1)
    source_story_graph_topology_hash: str | None = None
    source_stage_plan_id: str = Field(min_length=1)
    source_stage_plan_hash: str = Field(min_length=1)
    source_canonical_snapshot_hash: str = Field(min_length=1)
    target_selector: dict[str, Any]
    target_dependency_hash: str = Field(min_length=1)
    target_unit_dependency_hash: str = Field(min_length=1)
    target_input_hash: str = Field(min_length=1)
    failed_attempt_id: str = Field(min_length=1)
    response_artifact_id: str = Field(min_length=1)
    validation_artifact_id: str = Field(min_length=1)
    reuse_sources: list[FrozenFragmentReuseSource] = Field(default_factory=list)
    scope_hash: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class FragmentReuseBinding(CamelModel):
    """Immutable parent-to-child fragment mapping used only by exact repair."""

    id: str = Field(min_length=1)
    child_run_id: str = Field(min_length=1)
    child_stage_plan_id: str = Field(min_length=1)
    child_stage_plan_hash: str = Field(min_length=1)
    child_work_unit_id: str = Field(min_length=1)
    stage: StageName
    kind: FragmentReuseKind
    source_run_id: str = Field(min_length=1)
    source_work_unit_id: str = Field(min_length=1)
    source_stage_plan_id: str = Field(min_length=1)
    source_candidate_artifact_id: str = Field(min_length=1)
    source_candidate_content_hash: str = Field(min_length=1)
    source_stage_plan_hash: str = Field(min_length=1)
    source_selector: dict[str, Any]
    source_dependency_hash: str = Field(min_length=1)
    source_unit_dependency_hash: str = Field(min_length=1)
    source_input_hash: str = Field(min_length=1)
    source_producer_attempt_id: str = Field(min_length=1)
    source_response_artifact_id: str = Field(min_length=1)
    source_validation_artifact_id: str = Field(min_length=1)
    child_selector: dict[str, Any]
    child_dependency_hash: str = Field(min_length=1)
    child_unit_dependency_hash: str = Field(min_length=1)
    child_input_hash: str = Field(min_length=1)
    binding_hash: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class WorkUnitRepairEligibility(CamelModel):
    """Secret-free server decision; callers never infer repair eligibility."""

    work_unit_id: str = Field(min_length=1)
    stage: StageName
    eligible: bool
    reason_code: str | None = None


class WorkUnitRepairRunCreation(CamelModel):
    """Atomic idempotency result; only a newly-created child may be scheduled."""

    run: GenerationRun
    created: bool


class RunProgressAttempt(CamelModel):
    attempt_id: str
    attempt_number: Annotated[int, Field(ge=1)]
    attempt_kind: GenerationAttemptKind
    source_attempt_id: str | None = None
    status: AttemptStatus
    outcome_code: str | None = None
    outcome_unknown: bool = False
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    started_at: datetime
    finished_at: datetime | None = None


class RunProgressUnit(CamelModel):
    work_unit_id: str
    stage: StageName
    sequence: Annotated[int, Field(ge=1)]
    status: WorkUnitStatus
    max_attempts: Annotated[int, Field(ge=1)]
    latest_attempt: RunProgressAttempt | None = None
    sealed: bool
    repair_eligible: bool
    repair_reason_code: str | None = None


class RunProgressStage(CamelModel):
    stage: StageName
    stage_plan_id: str | None = None
    stage_plan_hash: str | None = None
    sealed: bool
    unit_count: Annotated[int, Field(ge=0)]
    completed_unit_count: Annotated[int, Field(ge=0)]
    quarantined_unit_count: Annotated[int, Field(ge=0)]
    repair_eligible_unit_ids: list[str] = Field(default_factory=list)


class RunProgressActions(CamelModel):
    can_resume: bool
    can_cancel: bool
    can_rebuild_stage: bool
    repair_eligible: bool


class RunProgress(CamelModel):
    """Small polling projection; never includes prompt, response, or payload."""

    run_id: str
    status: RunStatus
    failure_code: str | None = None
    failed_stage: StageName | None = None
    stage_progress: list[RunProgressStage] = Field(default_factory=list)
    work_units: list[RunProgressUnit] = Field(default_factory=list)
    actions: RunProgressActions


class SealedStageAggregateTrace(CamelModel):
    """Immutable exact-manifest aggregate eligible for canonical installation."""

    id: str
    run_id: str
    stage_plan_id: str
    stage: StageName
    manifest_hash: str
    manifest: dict[str, Any]
    payload: dict[str, Any]
    created_at: datetime


class StoryGraphTopologyTrace(CamelModel):
    """Frozen deterministic graph structure bound to one generation run."""

    run_id: str
    generation_plan_hash: str
    topology_hash: str
    topology: dict[str, Any]
    created_at: datetime


class RunExecutionTrace(CamelModel):
    """Additive work-unit evidence; the legacy RunTrace remains stable."""

    generation_plan: GenerationPlanTrace | None = None
    story_graph_topology: StoryGraphTopologyTrace | None = None
    stage_plans: list[StagePlanTrace] = Field(default_factory=list)
    work_units: list[GenerationWorkUnitTrace] = Field(default_factory=list)
    sealed_aggregates: list[SealedStageAggregateTrace] = Field(default_factory=list)


class StartupRecoveryPlan(CamelModel):
    """One-shot durable reconciliation actions for the local process runners."""

    resubmit_run_ids: list[str] = Field(default_factory=list)
    resubmit_media_task_ids: list[str] = Field(default_factory=list)
    resume_media_poll_task_ids: list[str] = Field(default_factory=list)
    terminated_run_ids: list[str] = Field(default_factory=list)
    terminated_media_task_ids: list[str] = Field(default_factory=list)


def stage_payload_model(stage: StageName) -> type[StagePayload]:
    return {
        StageName.STORY_BIBLE: StoryBible,
        StageName.STORY_GRAPH: StoryGraph,
        StageName.SCENE_BEATS: SceneBeatPlan,
        StageName.STORYBOARD: Storyboard,
    }[stage]


def upstream_stages(stage: StageName) -> tuple[StageName, ...]:
    index = STAGE_ORDER.index(stage)
    return STAGE_ORDER[:index]


def downstream_stages(stage: StageName) -> tuple[StageName, ...]:
    index = STAGE_ORDER.index(stage)
    return STAGE_ORDER[index + 1 :]


SECRET_SETTING_NAMES = frozenset(
    {
        "apikey",
        "key",
        "accesstoken",
        "refreshtoken",
        "token",
        "secret",
        "password",
        "authorization",
        "credential",
        "credentials",
    }
)


def is_secret_setting_name(name: object) -> bool:
    normalized = "".join(character for character in str(name).lower() if character.isalnum())
    return (
        normalized in SECRET_SETTING_NAMES
        or normalized.startswith("authorization")
        or normalized.endswith(
            ("apikey", "token", "secret", "password", "credential", "credentials")
        )
    )


def contains_secret_setting(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if is_secret_setting_name(key):
                return True
            if contains_secret_setting(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(contains_secret_setting(child) for child in value)
    return False


def contains_secret_value(value: Any) -> bool:
    """Detect structurally recognizable secrets without guessing arbitrary tokens."""

    if isinstance(value, dict):
        return any(contains_secret_value(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_secret_value(child) for child in value)
    if not isinstance(value, str):
        return False

    candidate = value.strip()
    lowered = candidate.lower()
    if lowered.startswith(("bearer ", "basic ", "sk-", "sk_", "xai-", "hf_", "aiza")):
        return True
    if "-----begin private key-----" in lowered:
        return True

    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        if parsed.username or parsed.password:
            return True
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        if any(is_secret_setting_name(key) for key, _ in query_items):
            return True

    assignment_name, separator, _assignment_value = candidate.partition("=")
    return bool(separator and is_secret_setting_name(assignment_name))


def validate_public_api_root(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "provider base URLs must be HTTP(S) roots with a host and without credentials, query, or fragment"
        )
    try:
        parsed.port
    except ValueError as error:
        raise ValueError("provider base URLs must use a valid port") from error
    return normalized


def validate_public_base_urls(value: Any) -> None:
    """Apply the trusted HTTP(S)-root contract to nested public *BaseUrl fields."""

    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = "".join(
                character for character in str(key).lower() if character.isalnum()
            )
            if normalized_key.endswith("baseurl"):
                if not isinstance(child, str):
                    raise ValueError("provider base URLs must be strings")
                validate_public_api_root(child)
            validate_public_base_urls(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            validate_public_base_urls(child)


def validate_public_provider_snapshot(value: Any) -> dict[str, Any]:
    """Validate the secret-free provider contract frozen into a durable run.

    Snapshots without ``profileSchemaVersion`` are historical V1 values.  They
    must continue through the exact pre-M1.5 Pydantic/hash path: adding V2
    defaults while merely reading an old run would change its plan and seal
    evidence.  Only explicitly versioned V2 snapshots use the named-profile
    contract.
    """

    candidate = {} if value is None else value
    if isinstance(candidate, dict) and (
        candidate.get("profileSchemaVersion") == 2
        or candidate.get("profile_schema_version") == 2
    ):
        # Local import keeps the domain module usable by the pure profile
        # contract without introducing a module import cycle.
        from .provider_profiles import TextProviderProfileSnapshot

        snapshot = TextProviderProfileSnapshot.model_validate(candidate)
        return snapshot.model_dump(mode="json", by_alias=True)
    snapshot = ProviderSnapshot.model_validate(candidate)
    return snapshot.model_dump(mode="json", by_alias=True)
