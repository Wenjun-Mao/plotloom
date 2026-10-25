"""Complete initial inventory and source-bound material bundle contracts."""
from typing import Literal

from pydantic import Field, model_validator

from .provider_budgets import exceeds_budget
from .autopilot_contracts import ProvisionalFrame
from .contract_hash import stable_hash
from .domain import CamelModel, StageName
from .exceptions import InvalidTransitionError
from .source_structures import complete_routes


class MaterialSubject(CamelModel):
    owner: Literal["character-reference", "art-reference", "image"]
    id: str
    subject_type: Literal["scene", "prop"] | None = None
    scene_id: str | None = None
    character_ids: list[str] = Field(default_factory=list)
    consumer_character_id: str | None = Field(default=None, exclude_if=lambda value: value is None)

    @property
    def operation_key(self):
        return f"{self.owner}:{self.subject_type + ':' if self.subject_type else ''}{self.id}"


class MaterialInventory(CamelModel):
    version: Literal["pre-video.inventory.v1", "pre-video.inventory.v2"] = "pre-video.inventory.v2"
    entity_revision_id: str
    storyboard_revision: int
    storyboard_hash: str
    production_hash: str
    cast_revision: int
    art_revision: int
    subjects: list[MaterialSubject]
    route_count: int

    @model_validator(mode="after")
    def exact_keys(self):
        keys = [item.operation_key for item in self.subjects]
        if len(keys) != len(set(keys)):
            raise ValueError("material inventory identities must be unique")
        for subject in self.subjects:
            needs_consumer = self.version == "pre-video.inventory.v2" and subject.owner == "character-reference"
            if needs_consumer != (subject.consumer_character_id is not None):
                raise ValueError("current Cast inventory requires explicit consumer identity; other subjects and retained v1 do not")
        return self


def cast_reference_subjects(cast):
    consumers = {item.cast_character_id: item.consumer_character_id for item in cast.consumer_mappings}
    if set(consumers) != {item["id"] for item in cast.cast["characters"]}:
        raise InvalidTransitionError("every Cast reference requires its explicit accepted consumer mapping")
    return [MaterialSubject(owner="character-reference", id=item["id"], consumer_character_id=consumers[item["id"]])
        for item in cast.cast["characters"]]


def initial_inventory(store, policy, *, enforce_limits=True):
    # Complete inventory owns persistence; importing shared material models must
    # not initialize the repository that also consumes those models.
    from .persistence.project.autopilot_closure import production_closure

    cast = store.cast_state().accepted_cast
    art = store.art_state().accepted_art
    readiness_error = "complete material inventory requires current accepted text and installation"
    if cast is None or art is None:
        raise InvalidTransitionError(readiness_error)
    installation = store.production_bridge_installation()
    if installation is None or installation.status != "current":
        raise InvalidTransitionError(readiness_error)
    subjects = cast_reference_subjects(cast)
    for kind, key in (("scene", "scenes"), ("prop", "props")):
        subjects.extend(MaterialSubject(owner="art-reference", subject_type=kind, id=item["id"]) for item in art.art[key])
    repository = store.repository
    with repository._read() as session:
        load = lambda stage: repository._canonical._load_stage_payload(session, store.manifest.project_id, stage)
        graph, beats, board = load(StageName.STORY_GRAPH), load(StageName.SCENE_BEATS), load(StageName.STORYBOARD)
        routes = complete_routes(graph)
        reachable = {node for route in routes for node in route}
        filmed = {node.id for node in graph.nodes if node.id in reachable and node.footage_mode == "footage"}
        scenes = {scene.id for scene in beats.scenes if scene.story_node_id in filmed}
        for shot in board.shots:
            if shot.scene_id not in scenes:
                raise InvalidTransitionError("canonical shot is not reachable filmed material")
            if len(shot.character_ids) > 8:
                raise InvalidTransitionError("镜头可见角色超过八人；请接管调整，不能省略身份审阅。")
            subjects.append(MaterialSubject(owner="image", id=shot.id, scene_id=shot.scene_id, character_ids=shot.character_ids))
        head = repository._project_access.rows.stage(session, store.manifest.project_id, StageName.STORYBOARD)
        inventory = MaterialInventory(entity_revision_id=head.entity_revision_id, storyboard_revision=head.revision,
            storyboard_hash=head.content_hash, production_hash=production_closure(session, store.manifest.project_id),
            cast_revision=cast.revision, art_revision=art.revision, subjects=subjects, route_count=len(routes))
    if enforce_limits and (exceeds_budget(len(subjects), policy.max_images) or exceeds_budget(len(subjects) + 8, policy.max_jobs)):
        raise InvalidTransitionError("完整素材包超过冻结图片或任务上限；停止新增任务，已保留参考候选供你接管检查范围。")
    return inventory


def inventory_hash(inventory):
    return stable_hash(inventory.model_dump(mode="json", by_alias=True))


class GalleryMaterial(CamelModel):
    owner: Literal["character-reference", "art-reference"]
    id: str
    subject_type: Literal["scene", "prop"] | None = None
    job_id: str
    request_hash: str
    delivery_hash: str
    reference_decision_id: str
    asset_id: str
    original_hash: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class AutomaticMaterialBundle(CamelModel):
    version: Literal["pre-video.material.v1"] = "pre-video.material.v1"
    run_id: str
    policy_hash: str
    inventory: MaterialInventory
    references: list[GalleryMaterial]
    frames: list[ProvisionalFrame]

    @model_validator(mode="after")
    def complete_inventory(self):
        required = {(item.owner, item.subject_type, item.id) for item in self.inventory.subjects if item.owner != "image"}
        actual = [(item.owner, item.subject_type, item.id) for item in self.references]
        if required != set(actual) or len(actual) != len(required):
            raise ValueError("material bundle must include every required reference exactly once")
        shots = {item.id: item for item in self.inventory.subjects if item.owner == "image"}
        if set(shots) != {item.shot_id for item in self.frames} or len(self.frames) != len(shots):
            raise ValueError("material bundle must include every unique filmed frame exactly once")
        for frame in self.frames:
            subject = shots[frame.shot_id]
            if (frame.scene_id != subject.scene_id or [entry["characterId"] for entry in frame.character_identity] != subject.character_ids
                    or frame.storyboard_revision != self.inventory.storyboard_revision or frame.storyboard_hash != self.inventory.storyboard_hash):
                raise ValueError("material frame differs from its complete inventory")
        return self
