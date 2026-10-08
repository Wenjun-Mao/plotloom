"""Frozen native bridge intent jobs over the existing specialist exchange."""
from contextlib import closing
from pathlib import Path
from typing import Any

from .creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from .creative_handoff_exchange import canonical_json, request_hash
from .domain import new_id
from .exceptions import InvalidTransitionError
from .image_job_contracts import ImageJobError
from .native_bridge_intent_contract import native_intent_suggestions, render_native_intent_report
from .production_bridge_intent_contract import MAX_INTENT_CONTEXT_CHARACTERS, intent_response_schema
from .project_storage.composition import ProjectFolderStorage
from .specialist_settings import SpecialistRegistry


class NativeBridgeIntentService:
    """Transport owns sends; the project bridge owns content and currentness."""

    def __init__(self, storage: ProjectFolderStorage, registry: SpecialistRegistry):
        self.storage, self.registry = storage, registry

    def configured(self) -> bool:
        return bool(self.registry.view()["text"]["taskId"])

    @staticmethod
    def _request(store: Any, project_id: str, job_id: str) -> tuple[CreativeHandoffRequest, dict]:
        data = store.repository.production_bridge_intent.load_job(project_id, job_id)
        if data["transport"] != "codex_native":
            raise InvalidTransitionError("job is not a native bridge intent candidate")
        request = CreativeHandoffRequest.model_validate(data["nativeRequest"])
        if request.job_id != job_id or request.project_id != project_id or request.stage != "bridge-intent":
            raise InvalidTransitionError("native intent request identity differs from project-owned job")
        return request, data

    def create(self, project_id: str, *, expected_revision: int, expected_hash: str) -> str:
        if not self.configured():
            raise ImageJobError("specialist_unconfigured", "请先在生成助手设置中配置 Codex 文字助手。")
        with closing(self.storage.projects.open(project_id)) as store:
            owner = store.repository.production_bridge_intent
            context, targets = owner.source_context(project_id, expected_revision=expected_revision, expected_hash=expected_hash)
            entries = store.production_bridge_state().proposal.intent_package.entries
            frozen_entries = [entry.model_dump(mode="json", by_alias=True) for entry in entries]
            if len(canonical_json({"context": context, "targets": frozen_entries})) > MAX_INTENT_CONTEXT_CHARACTERS:
                raise InvalidTransitionError("native intent context exceeds the bounded one-package limit")
            schema = intent_response_schema([entry["id"] for entry in targets])
            request = CreativeHandoffRequest(
                job_id="ch_" + new_id().replace("-", ""), project_id=project_id,
                section_id="production-bridge", stage="bridge-intent", expected_stage_revision=expected_revision,
                source=context, input_artifacts={"targets.json": {"entries": frozen_entries}, "intent-schema.json": schema},
                creative_brief="为冻结提案的全部目标提出中文戏剧意图，仅交付建议与报告，等待作者整包审阅。",
            )
            exchange = store.creative_handoff_exchange()
            pin = exchange.current_execution_pin(request.stage)
            digest = request_hash(request)
            job_id = owner.enqueue(project_id, expected_revision=expected_revision, expected_hash=expected_hash,
                profile_snapshot={}, prompt_trace={"prompt_version": "native-intent.v1", "rendered_hash": digest},
                prompt_messages=[], response_schema=schema, native_request=request, execution_pin=pin)
            # A crash before export retains a queued frozen request. Explicit send
            # can finish this exact export; preparation never submits anything.
            exchange.write_package(request, pin)
            return job_id

    def send(self, project_id: str, job_id: str) -> None:
        with closing(self.storage.projects.open(project_id)) as store:
            request, data = self._request(store, project_id, job_id)
            if data["status"] != "queued":
                raise InvalidTransitionError("only a never-sent native intent candidate can be sent")
            exchange = store.creative_handoff_exchange()
            frozen_pin = store.creative_handoff_execution_pin(request)
            if exchange.current_execution_pin(request.stage) != frozen_pin:
                raise CreativeHandoffError("execution_pin_mismatch", "当前执行版本与冻结任务不同；未发送，任务与执行锁定保持不变。")
            paths = exchange.write_package(request, frozen_pin)
            if Path(paths["deliveryPath"]).exists():
                raise InvalidTransitionError("native intent delivery already exists; do not send a second execution")
            owner = store.repository.production_bridge_intent

            def before_send():
                if not owner.mark_dispatched(project_id, job_id):
                    raise InvalidTransitionError("native intent proposal changed before sending")

            execution_root = Path(__file__).resolve().parents[2]
            try:
                self.registry.dispatch("text", job_id=job_id, package_path=paths["packagePath"], delivery_path=paths["deliveryPath"],
                    context={"projectId": project_id, "stage": "bridge-intent"}, before_send=before_send,
                    assignment=(f"Execute one frozen native Plotloom dramatic-intent job {job_id}. "
                        f"Use the exact execution checkout {execution_root} and its frozen revision; the task's original working directory is not execution authority. "
                        f"Read {execution_root}/.agents/skills/plotloom-intent-specialist/SKILL.md and {execution_root}/docs/creative-workflow/native-bridge-intent.md completely; use {execution_root}/scripts/native_bridge_intent.py. Then read "
                        f"{paths['packagePath']}/request.json and COPY_ASSIGNMENT.txt. "
                        f"The frozen package alone is authority. Write only its requested delivery files under {paths['deliveryPath']}. "
                        "Use the pinned local validator/renderer. Do not change code, canon, package, approvals or selections. "
                        "No API, provider fallback, image or video calls."))
            except ImageJobError as error:
                if error.code == "image_dispatch_outcome_unknown":
                    owner.finish_failure(project_id, job_id, status="outcome_unknown", code="native.dispatch_outcome_unknown",
                        message="发送结果不确定；请检查同一任务交付，不要重复发送。")
                raise

    def check(self, project_id: str, job_id: str) -> dict:
        with closing(self.storage.projects.open(project_id)) as store:
            request, data = self._request(store, project_id, job_id)
            self.registry.assert_creative_task_identity(job_id, project_id=project_id, stage=request.stage)
            if data["status"] == "queued":
                return {"state": "prepared", "candidateStatus": "queued"}
            delivery = self._delivery(store, request)
            if delivery is None:
                return self.registry.status(job_id) | {"candidateStatus": data["status"]}
            if data["status"] not in {"ready", "failed"}:
                suggestions = native_intent_suggestions(request, delivery.candidate)
                evidence = {"manifest": delivery.manifest.model_dump(mode="json", by_alias=True), "manifestHash": delivery.manifest_hash}
                store.repository.production_bridge_intent.finish_success(project_id, job_id, suggestions=suggestions,
                    response_evidence=evidence, response_hash=delivery.manifest.candidate.sha256, provider_request_id=None, usage=None,
                    native_provenance={"jobId": job_id, "transport": "codex_native", "requestHash": request_hash(request),
                        "manifestHash": delivery.manifest_hash, "executorProvenance": evidence["manifest"]["executorProvenance"],
                        "limitations": delivery.manifest.limitations, "responseHash": delivery.manifest.candidate.sha256})
            # Validated late delivery is terminal evidence, even when cancelled
            # or stale. Invalid/partial evidence cannot release the reservation.
            self.registry.complete_creative_task(job_id, project_id=project_id, stage=request.stage)
            return {"state": "completed", "candidateStatus": store.repository.production_bridge_intent.load_job(project_id, job_id)["status"]}

    @staticmethod
    def _delivery(store: Any, request: CreativeHandoffRequest):
        try:
            delivery = store.creative_handoff_exchange().read_delivery(request, store.creative_handoff_execution_pin(request))
        except CreativeHandoffError as error:
            if error.code == "delivery_partial":
                return None
            raise
        if delivery is not None:
            try:
                expected_report = render_native_intent_report(request, delivery.candidate)
            except (ValueError, KeyError) as error:
                raise CreativeHandoffError("native_intent_invalid_candidate", "戏剧意图交付不符合完整目标与建议合同；助手占用仍保留。") from error
            if delivery.report != expected_report:
                raise CreativeHandoffError("delivery_report_mismatch", "native intent report differs from its deterministic candidate view")
        return delivery

    def report(self, project_id: str, job_id: str) -> bytes:
        with closing(self.storage.projects.open(project_id)) as store:
            request, _data = self._request(store, project_id, job_id)
            delivery = self._delivery(store, request)
            if delivery is None:
                raise InvalidTransitionError("native intent report is not completely delivered")
            return delivery.report

    def cancel(self, project_id: str, job_id: str) -> None:
        with closing(self.storage.projects.open(project_id)) as store:
            self._request(store, project_id, job_id)
            store.repository.production_bridge_intent.cancel(project_id, job_id)

    def status(self, project_id: str, job_id: str) -> dict:
        with closing(self.storage.projects.open(project_id)) as store:
            request, data = self._request(store, project_id, job_id)
            self.registry.assert_creative_task_identity(job_id, project_id=project_id, stage=request.stage)
            evidence = data["responseEvidence"]
            return self.registry.status(job_id) | {"candidateStatus": data["status"], "reportAvailable": evidence is not None,
                "limitations": evidence["manifest"]["limitations"] if evidence else []}
