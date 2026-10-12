"""Shared dispatch-once transport for separately bound native bridge candidates."""
from contextlib import closing
from pathlib import Path
from typing import Any

from .creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from .exceptions import InvalidTransitionError
from .image_job_contracts import ImageJobError
from .project_storage.composition import ProjectFolderStorage
from .specialist_settings import SpecialistRegistry


class NativeBridgeCandidateService:
    """Transport owns sends; the project bridge owns content and currentness."""
    stage: str
    name: str
    render_report: Any

    def __init__(self, storage: ProjectFolderStorage, registry: SpecialistRegistry):
        self.storage, self.registry = storage, registry

    def configured(self) -> bool:
        return bool(self.registry.view()["text"]["taskId"])

    @classmethod
    def _request(cls, store: Any, project_id: str, job_id: str) -> tuple[CreativeHandoffRequest, dict]:
        data = store.repository.production_bridge_intent.load_job(project_id, job_id)
        if data["transport"] != "codex_native":
            raise InvalidTransitionError("job is not a native bridge candidate")
        request = CreativeHandoffRequest.model_validate(data["nativeRequest"])
        if request.job_id != job_id or request.project_id != project_id or request.stage != cls.stage:
            raise InvalidTransitionError("native candidate stage or identity differs from project-owned job")
        return request, data

    def send(self, project_id: str, job_id: str) -> None:
        with closing(self.storage.projects.open(project_id)) as store:
            return self.send_in_store(store, job_id)

    def send_in_store(self, store, job_id, *, before_send=None, expected_task_id=None, expected_bindings=None):
        project_id = store.manifest.project_id
        request, data = self._request(store, project_id, job_id)
        if data["status"] != "queued":
            raise InvalidTransitionError("only a never-sent native candidate can be sent")
        exchange = store.creative_handoff_exchange()
        frozen_pin = store.creative_handoff_execution_pin(request)
        if exchange.current_execution_pin(request.stage) != frozen_pin:
            raise CreativeHandoffError("execution_pin_mismatch", "当前执行版本与冻结任务不同；未发送，任务与执行锁定保持不变。")
        paths = exchange.write_package(request, frozen_pin)
        if Path(paths["deliveryPath"]).exists():
            raise InvalidTransitionError("native delivery already exists; do not send a second execution")
        owner = store.repository.production_bridge_intent

        def prepare_dispatch():
            if before_send is not None:
                before_send()
            elif not owner.mark_dispatched(project_id, job_id):
                raise InvalidTransitionError("native candidate proposal changed before sending")

        execution_root = Path(__file__).resolve().parents[2]
        try:
            self.registry.dispatch("text", job_id=job_id, package_path=paths["packagePath"], delivery_path=paths["deliveryPath"],
                    context={"projectId": project_id, "stage": self.stage}, before_send=prepare_dispatch, expected_task_id=expected_task_id, expected_bindings=expected_bindings,
                assignment=(f"Execute one frozen native Plotloom {self.name} suggestion job {job_id}. "
                    f"Use the exact execution checkout {execution_root} and its frozen revision; the task's original working directory is not execution authority. "
                    f"Read {execution_root}/.agents/skills/plotloom-{self.name}-specialist/SKILL.md and {execution_root}/docs/creative-workflow/native-bridge-{self.name}.md completely; use {execution_root}/scripts/native_bridge_{self.name}.py. Then read "
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
                self._admit(store, request, delivery)
            # Validated late delivery is terminal evidence, even when cancelled
            # or stale. Invalid/partial evidence cannot release the reservation.
            self.registry.complete_creative_task(job_id, project_id=project_id, stage=request.stage)
            return {"state": "completed", "candidateStatus": store.repository.production_bridge_intent.load_job(project_id, job_id)["status"]}

    def _delivery(self, store: Any, request: CreativeHandoffRequest):
        try:
            delivery = store.creative_handoff_exchange().read_delivery(request, store.creative_handoff_execution_pin(request))
        except CreativeHandoffError as error:
            if error.code == "delivery_partial":
                return None
            raise
        if delivery is not None:
            try:
                expected_report = self.render_report(request, delivery.candidate)
            except (ValueError, KeyError) as error:
                raise CreativeHandoffError("native_candidate_invalid", "助手交付不符合完整来源与建议合同；助手占用仍保留。") from error
            if delivery.report != expected_report:
                raise CreativeHandoffError("delivery_report_mismatch", "native report differs from its deterministic candidate view")
        return delivery

    def report(self, project_id: str, job_id: str) -> bytes:
        with closing(self.storage.projects.open(project_id)) as store:
            request, _data = self._request(store, project_id, job_id)
            delivery = self._delivery(store, request)
            if delivery is None:
                raise InvalidTransitionError("native report is not completely delivered")
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

    def _admit(self, store: Any, request: CreativeHandoffRequest, delivery: Any) -> None:
        raise NotImplementedError
