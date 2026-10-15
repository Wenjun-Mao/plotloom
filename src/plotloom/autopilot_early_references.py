"""Bounded exploratory reference discovery before complete installation inventory."""
from typing import Literal

from pydantic import Field

from .autopilot_contracts import POLICY_VERSION
from .autopilot_materials import MaterialSubject, cast_reference_subjects
from .domain import CamelModel, StageName
from .exceptions import InvalidTransitionError
from .image_job_contracts import ImageJobError
from .source_structures import complete_routes


class EarlyReferenceDiscovery(CamelModel):
    version: Literal["pre-video.early-references.v1"] = "pre-video.early-references.v1"
    cast_revision: int = Field(ge=1)
    cast_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    art_revision: int | None = None
    art_hash: str | None = None
    subjects: list[MaterialSubject]


def discover_early_references(store, view):
    if view.policy.version != POLICY_VERSION or not view.policy.early_reference_limit:
        return None
    adopted = {item["operationKey"] for item in view.checkpoints if item["state"] == "adopted"}
    if "characters" not in adopted:
        return None
    cast_state = store.cast_state()
    cast = cast_state.accepted_cast
    if cast_state.status != "accepted" or cast is None:
        raise InvalidTransitionError("early references require current accepted Cast")
    art_state = store.art_state() if "art" in adopted else None
    art = art_state.accepted_art if art_state is not None else None
    if art_state is not None and (art_state.status != "accepted" or art is None):
        raise InvalidTransitionError("early references require current accepted Art")
    cast_subjects = cast_reference_subjects(cast)
    art_subjects = []
    if art is not None:
        for kind, key in (("scene", "scenes"), ("prop", "props")):
            art_subjects.extend(MaterialSubject(owner="art-reference", subject_type=kind, id=item["id"]) for item in art.art[key])
    # Every reachable footage node requires filmed material. This is only a
    # demonstrated lower bound; final discovery still counts every actual shot.
    with store.repository._read() as session:
        graph = store.repository._canonical._load_stage_payload(session, view.project_id, StageName.STORY_GRAPH)
        reachable = {node for route in complete_routes(graph) for node in route}
        filmed = sum(node.id in reachable and node.footage_mode == "footage" for node in graph.nodes)
    lower_bound = len(cast_subjects) + len(art_subjects) + filmed
    if lower_bound > view.policy.max_images or lower_bound + 8 > view.policy.max_jobs:
        raise InvalidTransitionError("已知必需参考与拍摄素材超过冻结上限；停止新增任务，保留已有候选供你接管。")
    eligible = cast_subjects[:2] + art_subjects + cast_subjects[2:] if art is not None else cast_subjects[:2]
    return EarlyReferenceDiscovery(cast_revision=cast.revision, cast_hash=cast.content_hash,
        art_revision=art.revision if art is not None else None,
        art_hash=art.content_hash if art is not None else None, subjects=eligible)


def advance_early_references(controller, store, view, claim):
    discovery = discover_early_references(store, view)
    if discovery is None:
        return
    early_count = sum(bool(item["evidence"]["result"].get("earlyReference")) for item in view.checkpoints)
    for subject in discovery.subjects:
        checkpoint = controller.checkpoint(view, subject.operation_key)
        if checkpoint is None:
            if early_count >= view.policy.early_reference_limit:
                continue
            controller.prepare(store, view, claim, subject, discovery, subject.operation_key,
                initial_result={"earlyReference": discovery.model_dump(mode="json", by_alias=True)})
            # Preparation commits the one subject identity before any dispatch.
            return
        if checkpoint["state"] in {"delivered", "adopted"}:
            continue
        try:
            controller.native_step(store, view, claim, subject, discovery, checkpoint)
        except ImageJobError as error:
            if error.code not in {"codex_exec_outcome_unknown", "codex_exec_capacity_deferred"}:
                raise
            # The exact attempt remains reserved. Its uncertainty does not
            # change independent text inputs or authorize a second attempt.
