"""Fresh presentation suggestions never mutate saved dramatic intent or approval."""
from contextlib import closing
from typing import Any

from .creative_handoff_contracts import CreativeHandoffRequest
from .creative_handoff_exchange import request_hash
from .domain import new_id
from .exceptions import InvalidTransitionError
from .image_job_contracts import ImageJobError
from .native_bridge_candidate_service import NativeBridgeCandidateService
from .native_bridge_presentation_contract import (
    MAX_PRESENTATION_SOURCES,
    presentation_response_schema,
    render_native_presentation_report,
)
from .native_bridge_request import assert_native_bridge_request_size


class NativeBridgePresentationService(NativeBridgeCandidateService):
    stage, name = "bridge-presentation", "presentation"
    render_report = staticmethod(render_native_presentation_report)

    def create(self, project_id: str, *, expected_revision: int, expected_hash: str) -> str:
        if not self.configured():
            raise ImageJobError("specialist_unconfigured", "请先在生成助手设置中配置 Codex 文字助手。")
        with closing(self.storage.projects.open(project_id)) as store:
            job_id = self.prepare_in_store(store, expected_revision=expected_revision, expected_hash=expected_hash)
            request, _data = self._request(store, project_id, job_id)
            store.creative_handoff_exchange().write_package(request, store.creative_handoff_execution_pin(request))
            return job_id

    def prepare_in_store(self, store, *, expected_revision, expected_hash):
        project_id = store.manifest.project_id
        owner = store.repository.production_bridge_intent
        context, _targets = owner.source_context(project_id, expected_revision=expected_revision, expected_hash=expected_hash)
        proposal = store.production_bridge_state().proposal
        package = proposal.presentation.model_dump(mode="json", by_alias=True)
        if not 0 < len(proposal.presentation.sources) <= MAX_PRESENTATION_SOURCES:
            raise InvalidTransitionError("presentation sources exceed the bounded one-package limit")
        context["intentPackage"] = proposal.intent_package.model_dump(mode="json", by_alias=True)
        schema = presentation_response_schema([source.id for source in proposal.presentation.sources])
        request = CreativeHandoffRequest(job_id="ch_" + new_id().replace("-", ""), project_id=project_id,
            section_id="production-bridge", stage=self.stage, expected_stage_revision=expected_revision,
            source=context, input_artifacts={"presentation-source.json": package, "presentation-schema.json": schema},
            creative_brief="为全部冻结来源提出呈现归属与忠实画面描述，保留每字与限制；仅提供可编辑建议，等待作者确认。")
        assert_native_bridge_request_size(request)
        exchange = store.creative_handoff_exchange()
        pin = exchange.current_execution_pin(self.stage)
        job = owner.enqueue(project_id, expected_revision=expected_revision, expected_hash=expected_hash,
            profile_snapshot={}, prompt_trace={"prompt_version": "native-presentation.v1", "rendered_hash": request_hash(request)},
            prompt_messages=[], response_schema=schema, native_request=request, execution_pin=pin)
        return job

    def _admit(self, store: Any, request: CreativeHandoffRequest, delivery: Any) -> None:
        store.repository.production_bridge_intent.finish_presentation(request.project_id, request.job_id,
            candidate=delivery.candidate, response_hash=delivery.manifest.candidate.sha256,
            response_evidence={"manifest": delivery.manifest.model_dump(mode="json", by_alias=True), "manifestHash": delivery.manifest_hash})
