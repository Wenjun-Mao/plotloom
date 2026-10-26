"""Bounded first-pass text adoption through the existing creative owners."""
from uuid import uuid4

from .art_contracts import ArtAcceptRequest
from .autopilot_contracts import CheckpointEvidence
from .cast_contracts import CastAcceptRequest, CastConsumerMapping
from .creative_commands import CREATIVE_METHODS
from .creative_handoff_identity import request_hash
from plotloom.stage_contracts import StageName
from .graph_draft_creation import create_graph_draft
from .outline_preparation import outline_request
from .persistence.codec import stable_hash
from .script_contracts import ScriptAcceptRequest
from .source_outline_contracts import OutlineAcceptRequest, SectionMapSaveRequest, SectionMapGraphInstallRequest, SourceMaterial
from .storyboard_review_contracts import DEFAULT_STORYBOARD_MAX_CUT_SECONDS, StoryboardReviewAcceptRequest

TEXT_STAGES = ("outline", "branches", "characters", "art", "script", "storyboard")


def adopt_brief_source(store):
    project = store.project()
    state = store.save_source_material(expected_source_revision=0,
        material=SourceMaterial(kind="synopsis", title=project.require_brief().title, text=project.require_brief().synopsis,
            brief_origin={"revision": project.revision,
                "contentHash": stable_hash(project.require_brief().model_dump(mode="json", by_alias=False))}))
    checkpoint = store.repository.autopilot.checkpoint("source", state="adopted",
        evidence=CheckpointEvidence(owner="source", subject_id="source", result={"revision": state.source.revision}))
    store.repository.autopilot.decide(checkpoint, subject={"revision": state.source.revision, "contentHash": state.source.content_hash}, rationale="原始已保存简报的精确来源投影；没有补写权利或作者意图。")


def prepare_text(store, stage, policy):
    job_id = "ch_" + uuid4().hex
    if stage == "outline":
        request = outline_request(store, job_id=job_id)
        store.prepare_outline_candidate(request)
    elif stage == "branches":
        request = store.repository.branches.prepare(store.manifest.project_id, store.creative_handoff_exchange())
    else:
        cast_style = "brief" if policy.effective_style_authority == "brief" else policy.render_style
        art_style = "brief" if policy.effective_style_authority == "brief" else policy.art_render_style
        if cast_style is None or art_style is None:
            raise ValueError("frozen preset authority is incomplete")
        methods = {"characters": (store.prepare_cast_candidate, {"render_style": cast_style}),
            "art": (store.prepare_art_candidate, {"render_style": art_style}),
            "script": (store.prepare_script_candidate, {"planned_storyboard_max_cut_seconds": DEFAULT_STORYBOARD_MAX_CUT_SECONDS}),
            "storyboard": (store.prepare_storyboard_review_candidate, {"max_cut_seconds": DEFAULT_STORYBOARD_MAX_CUT_SECONDS})}
        command, options = methods[stage]
        _candidate, request = command(job_id, **options)
    return request


def native_checkpoint_evidence(store, request):
    return CheckpointEvidence(owner=request.stage, subject_id=request.job_id, job_id=request.job_id,
        request_hash=request_hash(request), execution_pin=store.creative_handoff_execution_pin(request))


def adopt_text(store, stage, job_id):
    state = getattr(store, CREATIVE_METHODS[stage][0])()
    candidate = state.candidate
    project_id = store.manifest.project_id
    if stage == "outline":
        state = store.accept_outline_candidate(OutlineAcceptRequest(job_id=job_id,
            expected_source_revision=state.source.revision,
            expected_outline_revision=state.accepted_outline.revision if state.accepted_outline else 0))
        accepted = state.accepted_outline
    elif stage == "branches":
        return adopt_branches(store, job_id)
    elif stage == "characters":
        state = store.accept_cast_candidate(CastAcceptRequest(job_id=job_id,
            expected_cast_revision=state.accepted_cast.revision if state.accepted_cast else 0, binding=candidate.binding,
            consumer_mappings=[CastConsumerMapping(cast_character_id=entry["id"], consumer_character_id=entry["id"])
                for entry in candidate.cast["characters"]]))
        accepted = state.accepted_cast
    elif stage == "art":
        state = store.accept_art_candidate(ArtAcceptRequest(job_id=job_id,
            expected_art_revision=state.accepted_art.revision if state.accepted_art else 0, binding=candidate.binding))
        accepted = state.accepted_art
    elif stage == "script":
        state = store.accept_script_candidate(ScriptAcceptRequest(job_id=job_id,
            expected_script_revision=state.accepted_script.revision if state.accepted_script else 0, binding=candidate.binding))
        accepted = state.accepted_script
    else:
        state = store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=job_id,
            expected_review_revision=state.accepted_review.revision if state.accepted_review else 0, binding=candidate.binding))
        accepted = state.accepted_review
    return {"revision": accepted.revision, "contentHash": accepted.content_hash, "projectId": project_id}


def adopt_branches(store, job_id):
    mapping = store.branch_draft(job_id)
    graph_state = store.graph_workbench_state()
    draft = create_graph_draft(binding_hash=graph_state.binding_hash, seed=mapping.seed_topology,
        mapping=mapping.model_dump(mode="json", by_alias=True))
    receipt = store.save_authoring_draft(editor_scope="story_graph", entity_id="root",
        base_canonical_revision=graph_state.base_canonical_revision,
        expected_draft_revision=graph_state.draft.draft_revision if graph_state.draft else 0,
        payload=draft.model_dump(mode="json", by_alias=True))
    state = store.source_outline_state()
    store.save_section_map(SectionMapSaveRequest(expected_source_revision=state.source.revision,
        expected_outline_revision=state.accepted_outline.revision, expected_outline_content_hash=state.accepted_outline.content_hash,
        expected_section_map_revision=state.accepted_section_map.revision if state.accepted_section_map else 0,
        expected_graph_draft_revision=receipt.draft_revision, mapping=mapping))
    state = store.source_outline_state()
    saved = state.accepted_section_map
    head = store.authoring.get_stage_head(store.manifest.project_id, StageName.STORY_GRAPH)
    store.install_section_map_graph(SectionMapGraphInstallRequest(expected_source_revision=state.source.revision,
        expected_source_content_hash=state.source.content_hash, expected_outline_revision=state.accepted_outline.revision,
        expected_outline_content_hash=state.accepted_outline.content_hash, expected_section_map_revision=saved.revision,
        expected_section_map_content_hash=saved.content_hash, expected_graph_revision=head.revision,
        expected_graph_draft_revision=store.graph_workbench_state().draft.draft_revision))
    head = store.authoring.get_stage_head(store.manifest.project_id, StageName.STORY_GRAPH)
    return {"revision": head.revision, "contentHash": head.content_hash, "entityRevisionId": head.entity_revision_id}
