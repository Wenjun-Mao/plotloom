"""Frozen native dramatic-intent candidates; presentation has a separate contract."""
from contextlib import closing
from typing import Any

from .creative_handoff_contracts import CreativeHandoffRequest
from .creative_handoff_exchange import request_hash
from .domain import new_id
from .image_job_contracts import ImageJobError
from .native_bridge_candidate_service import NativeBridgeCandidateService
from .native_bridge_intent_contract import (
    native_intent_suggestions,
    render_native_intent_report,
)
from .native_bridge_request import assert_native_bridge_request_size
from .production_bridge_intent_contract import intent_response_schema


class NativeBridgeIntentService(NativeBridgeCandidateService):
    stage, name = "bridge-intent", "intent"
    render_report = staticmethod(render_native_intent_report)

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
        context, targets = owner.source_context(project_id, expected_revision=expected_revision, expected_hash=expected_hash)
        entries = store.production_bridge_state().proposal.intent_package.entries
        frozen_entries = [entry.model_dump(mode="json", by_alias=True) for entry in entries]
        schema = intent_response_schema([entry["id"] for entry in targets])
        request = CreativeHandoffRequest(
            job_id="ch_" + new_id().replace("-", ""), project_id=project_id,
            section_id="production-bridge", stage="bridge-intent", expected_stage_revision=expected_revision,
            source=context, input_artifacts={"targets.json": {"entries": frozen_entries}, "intent-schema.json": schema},
            creative_brief="为冻结提案的全部目标提出中文戏剧意图，仅交付建议与报告，等待作者整包审阅。",
        )
        assert_native_bridge_request_size(request)
        exchange = store.creative_handoff_exchange()
        pin = exchange.current_execution_pin(request.stage)
        digest = request_hash(request)
        job_id = owner.enqueue(project_id, expected_revision=expected_revision, expected_hash=expected_hash,
            profile_snapshot={}, prompt_trace={"prompt_version": "native-intent.v1", "rendered_hash": digest},
            prompt_messages=[], response_schema=schema, native_request=request, execution_pin=pin)
        return job_id

    def _admit(self, store: Any, request: CreativeHandoffRequest, delivery: Any) -> None:
        suggestions = native_intent_suggestions(request, delivery.candidate)
        evidence = {"manifest": delivery.manifest.model_dump(mode="json", by_alias=True), "manifestHash": delivery.manifest_hash}
        store.repository.production_bridge_intent.finish_success(request.project_id, request.job_id, suggestions=suggestions,
            response_evidence=evidence, response_hash=delivery.manifest.candidate.sha256, provider_request_id=None, usage=None,
            native_provenance={"jobId": request.job_id, "transport": "codex_native", "requestHash": request_hash(request),
                "manifestHash": delivery.manifest_hash, "executorProvenance": evidence["manifest"]["executorProvenance"],
                "limitations": delivery.manifest.limitations, "responseHash": delivery.manifest.candidate.sha256})
