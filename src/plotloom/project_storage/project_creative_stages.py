"""Bound creative-stage commands; project home/lifecycle stay in ProjectStore."""
from __future__ import annotations

from ..art_contracts import ArtAcceptRequest, ArtCandidate, ArtReopenRequest, ArtReviewState, ArtSaveRequest
from ..art_style import ArtRenderStyle
from ..cast_style import CastRenderStyle
from ..cast_contracts import CastAcceptRequest, CastCancelReopenRequest, CastCandidate, CastReopenRequest, CastReviewState, CastSaveRequest
from ..creative_handoff_contracts import CreativeHandoffRequest
from ..creative_handoff_exchange import ValidatedCreativeDelivery
from ..production_bridge_contracts import ProductionBridgeAcceptRequest, ProductionBridgeIntentUpdateRequest, ProductionBridgePrepareRequest, ProductionBridgeState
from ..script_contracts import ScriptAcceptRequest, ScriptCandidate, ScriptReopenRequest, ScriptReviewState, ScriptSectionSaveRequest
from ..source_outline_contracts import OutlineAcceptRequest, OutlineCandidate, OutlineReopenRequest, SectionMapGraphInstallRequest, SectionMapSaveRequest, SourceMaterial, SourceOutlineReviewState
from ..storyboard_review_contracts import StoryboardReviewAcceptRequest, StoryboardReviewCandidate, StoryboardReviewState
from .project_creative_handoffs import ProjectCreativeHandoffs


class ProjectCreativeStages(ProjectCreativeHandoffs):
    def source_outline_state(self) -> SourceOutlineReviewState:
        return self.repository.source_outline.get_state(self.manifest.project_id)

    def graph_workbench_state(self):
        return self.repository.graph_workbench.get_state(self.manifest.project_id)

    def preview_graph_command(self, request):
        return self.repository.graph_workbench.preview(self.manifest.project_id, request)

    def apply_graph_command(self, request):
        return self.repository.graph_workbench.apply(self.manifest.project_id, request)

    def rebase_graph_draft(self, request):
        return self.repository.graph_workbench.rebase(self.manifest.project_id, request)

    def save_source_material(
        self, *, expected_source_revision: int, material: SourceMaterial
    ) -> SourceOutlineReviewState:
        return self.repository.source_outline.save_source(
            self.manifest.project_id,
            expected_source_revision=expected_source_revision,
            material=material,
        )

    def prepare_outline_candidate(self, request: CreativeHandoffRequest) -> OutlineCandidate:
        pin = self.creative_handoff_exchange().current_execution_pin(request.stage)
        return self.repository.source_outline.prepare_candidate(self.manifest.project_id, request, execution_pin=pin)

    def admit_outline_delivery(self, delivery: ValidatedCreativeDelivery) -> OutlineCandidate:
        return self.repository.source_outline.admit_delivery(self.manifest.project_id, delivery)

    def accept_outline_candidate(self, request: OutlineAcceptRequest) -> SourceOutlineReviewState:
        return self.repository.source_outline.accept_candidate(self.manifest.project_id, request)

    def reopen_outline(self, request: OutlineReopenRequest) -> SourceOutlineReviewState:
        return self.repository.source_outline.reopen_outline(self.manifest.project_id, request)

    def save_section_map(self, request: SectionMapSaveRequest) -> SourceOutlineReviewState:
        return self.repository.source_outline.save_section_map(self.manifest.project_id, request)

    def install_section_map_graph(self, request: SectionMapGraphInstallRequest) -> SourceOutlineReviewState:
        return self.repository.source_outline.install_section_map_graph(self.manifest.project_id, request)

    def cancel_outline_candidate(self, job_id: str) -> SourceOutlineReviewState:
        return self.repository.source_outline.cancel_candidate(self.manifest.project_id, job_id)

    def outline_candidate_report(self, job_id: str) -> str:
        return self.repository.source_outline.candidate_report(self.manifest.project_id, job_id)

    def outline_candidate_request(self, job_id: str) -> CreativeHandoffRequest:
        return self.repository.source_outline.candidate_request(self.manifest.project_id, job_id)


    def cast_state(self) -> CastReviewState:
        return self.repository.cast.get_state(self.manifest.project_id)

    def prepare_cast_candidate(self, job_id: str, *, render_style: CastRenderStyle) -> tuple[CastCandidate, CreativeHandoffRequest]:
        pin = self.creative_handoff_exchange().current_execution_pin("characters")
        return self.repository.cast.prepare_candidate(self.manifest.project_id, job_id, render_style=render_style, execution_pin=pin)

    def admit_cast_delivery(self, delivery: ValidatedCreativeDelivery) -> CastCandidate:
        return self.repository.cast.admit_delivery(self.manifest.project_id, delivery)

    def accept_cast_candidate(self, request: CastAcceptRequest) -> CastReviewState:
        return self.repository.cast.accept_candidate(self.manifest.project_id, request)

    def reopen_cast(self, request: CastReopenRequest) -> CastReviewState:
        return self.repository.cast.reopen(self.manifest.project_id, request)

    def save_reopened_cast(self, request: CastSaveRequest) -> CastReviewState:
        return self.repository.cast.save_reopened(self.manifest.project_id, request)

    def cancel_reopened_cast(self, request: CastCancelReopenRequest) -> CastReviewState:
        return self.repository.cast.cancel_reopen(self.manifest.project_id, request)

    def cancel_cast_candidate(self, job_id: str) -> CastReviewState:
        return self.repository.cast.cancel_candidate(self.manifest.project_id, job_id)

    def cast_consumer_identity(self, cast_character_id: str) -> str:
        return self.repository.cast.consumer_identity_for(self.manifest.project_id, cast_character_id)

    def cast_candidate_report(self, job_id: str) -> str:
        return self.repository.cast.candidate_report(self.manifest.project_id, job_id)

    def cast_candidate_request(self, job_id: str) -> CreativeHandoffRequest:
        return self.repository.cast.candidate_request(self.manifest.project_id, job_id)

    def art_state(self) -> ArtReviewState:
        return self.repository.art.get_state(self.manifest.project_id)

    def prepare_art_candidate(self, job_id: str, *, render_style: ArtRenderStyle) -> tuple[ArtCandidate, CreativeHandoffRequest]:
        pin = self.creative_handoff_exchange().current_execution_pin("art")
        return self.repository.art.prepare_candidate(self.manifest.project_id, job_id, render_style=render_style, execution_pin=pin)

    def admit_art_delivery(self, delivery: ValidatedCreativeDelivery) -> ArtCandidate:
        return self.repository.art.admit_delivery(self.manifest.project_id, delivery)

    def accept_art_candidate(self, request: ArtAcceptRequest) -> ArtReviewState:
        return self.repository.art.accept_candidate(self.manifest.project_id, request)

    def reopen_art(self, request: ArtReopenRequest) -> ArtReviewState:
        return self.repository.art.reopen(self.manifest.project_id, request)

    def save_reopened_art(self, request: ArtSaveRequest) -> ArtReviewState:
        return self.repository.art.save_reopened(self.manifest.project_id, request)

    def cancel_art_candidate(self, job_id: str) -> ArtReviewState:
        return self.repository.art.cancel_candidate(self.manifest.project_id, job_id)

    def art_candidate_report(self, job_id: str) -> str:
        return self.repository.art.candidate_report(self.manifest.project_id, job_id)

    def art_candidate_request(self, job_id: str) -> CreativeHandoffRequest:
        return self.repository.art.candidate_request(self.manifest.project_id, job_id)

    def script_state(self) -> ScriptReviewState:
        return self.repository.script.get_state(self.manifest.project_id)

    def prepare_script_candidate(self, job_id: str) -> tuple[ScriptCandidate, CreativeHandoffRequest]:
        pin = self.creative_handoff_exchange().current_execution_pin("script")
        return self.repository.script.prepare_candidate(self.manifest.project_id, job_id, execution_pin=pin)

    def admit_script_delivery(self, delivery: ValidatedCreativeDelivery) -> ScriptCandidate:
        return self.repository.script.admit_delivery(self.manifest.project_id, delivery)

    def accept_script_candidate(self, request: ScriptAcceptRequest) -> ScriptReviewState:
        return self.repository.script.accept_candidate(self.manifest.project_id, request)

    def reopen_script(self, request: ScriptReopenRequest) -> ScriptReviewState:
        return self.repository.script.reopen(self.manifest.project_id, request)

    def save_script_section(self, request: ScriptSectionSaveRequest) -> ScriptReviewState:
        return self.repository.script.save_section(self.manifest.project_id, request)

    def cancel_script_candidate(self, job_id: str) -> ScriptReviewState:
        return self.repository.script.cancel_candidate(self.manifest.project_id, job_id)

    def script_candidate_report(self, job_id: str) -> str:
        return self.repository.script.candidate_report(self.manifest.project_id, job_id)

    def script_candidate_request(self, job_id: str) -> CreativeHandoffRequest:
        return self.repository.script.candidate_request(self.manifest.project_id, job_id)

    def storyboard_review_state(self) -> StoryboardReviewState:
        return self.repository.storyboard_review.get_state(self.manifest.project_id)

    def prepare_storyboard_review_candidate(self, job_id: str, *, max_cut_seconds: int = 8) -> tuple[StoryboardReviewCandidate, CreativeHandoffRequest]:
        pin = self.creative_handoff_exchange().current_execution_pin("storyboard")
        return self.repository.storyboard_review.prepare_candidate(self.manifest.project_id, job_id, max_cut_seconds=max_cut_seconds, execution_pin=pin)

    def admit_storyboard_review_delivery(self, delivery: ValidatedCreativeDelivery) -> StoryboardReviewCandidate:
        return self.repository.storyboard_review.admit_delivery(self.manifest.project_id, delivery)

    def accept_storyboard_review_candidate(self, request: StoryboardReviewAcceptRequest) -> StoryboardReviewState:
        return self.repository.storyboard_review.accept_candidate(self.manifest.project_id, request)

    def cancel_storyboard_review_candidate(self, job_id: str) -> StoryboardReviewState:
        return self.repository.storyboard_review.cancel_candidate(self.manifest.project_id, job_id)

    def storyboard_review_candidate_report(self, job_id: str) -> str:
        return self.repository.storyboard_review.candidate_report(self.manifest.project_id, job_id)

    def storyboard_review_candidate_request(self, job_id: str) -> CreativeHandoffRequest:
        return self.repository.storyboard_review.candidate_request(self.manifest.project_id, job_id)

    def production_bridge_state(self) -> ProductionBridgeState:
        return self.repository.production_bridge.get_state(self.manifest.project_id)

    def update_production_bridge_presentation(self, request):
        return self.repository.production_bridge.update_presentation(self.manifest.project_id, request)

    def prepare_production_bridge(self, request: ProductionBridgePrepareRequest) -> ProductionBridgeState:
        return self.repository.production_bridge.prepare(self.manifest.project_id, request)

    def update_production_bridge_intent_package(self, request: ProductionBridgeIntentUpdateRequest) -> ProductionBridgeState:
        return self.repository.production_bridge.update_intent_package(self.manifest.project_id, request)

    def accept_production_bridge(self, request: ProductionBridgeAcceptRequest) -> ProductionBridgeState:
        return self.repository.production_bridge.accept(self.manifest.project_id, request)
