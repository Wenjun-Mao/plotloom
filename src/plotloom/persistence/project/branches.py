"""Advisory branch handoffs in the existing kind-discriminated candidate envelope."""
from typing import Any
from uuid import uuid4
from sqlalchemy import select
from ...branch_suggestions import BranchSuggestion, BranchTaskCandidate, BranchTaskState, bind_branches
from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery
from ...domain import utc_now
from ...exceptions import InvalidTransitionError, NotFoundError
from ...outline_settings import outline_settings
from ..schema import SourceOutlineCandidateRow
from .access import ProjectPersistenceAccess
from .creative_execution_pins import freeze_execution_pin


class ProjectBranchPersistence:
    def __init__(self, access: ProjectPersistenceAccess, outline: Any):
        self._access, self._outline = access, outline

    def _state(self, session, project_id):
        return self._outline._state_in_session(session, project_id, self._outline._head(session, project_id, create=True))

    def _basis(self, session, project_id):
        state = self._state(session, project_id)
        if not state.source or not state.accepted_outline or state.outline_status != "accepted" or state.accepted_outline.source_revision != state.source.revision:
            raise InvalidTransitionError("请先确认当前大纲，或返回保留的有效大纲，再准备剧情分支建议。")
        return {
            "sourceRevision": state.source.revision, "sourceContentHash": state.source.content_hash,
            "outline": state.accepted_outline.model_dump(mode="json", by_alias=True),
            "mapRevision": state.accepted_section_map.revision if state.accepted_section_map else 0,
            "topology": self._planned(session, project_id).model_dump(mode="json", by_alias=True),
        }

    def _planned(self, session, project_id):
        from ...domain import ProjectBrief
        from ...source_structures import planned_structure
        return planned_structure(project_id, ProjectBrief.model_validate(self._access.rows.project(session, project_id).brief))

    @staticmethod
    def _latest(session, project_id):
        return session.scalar(select(SourceOutlineCandidateRow).where(
            SourceOutlineCandidateRow.project_id == project_id,
            SourceOutlineCandidateRow.request["stage"].as_string() == "branches",
        ).order_by(SourceOutlineCandidateRow.created_at.desc(), SourceOutlineCandidateRow.job_id.desc()).limit(1))

    def _row(self, session, project_id, job_id):
        row = session.get(SourceOutlineCandidateRow, job_id)
        if row is None or row.project_id != project_id or row.request.get("stage") != "branches":
            raise NotFoundError("剧情分支建议任务不存在")
        return row

    def _current(self, session, project_id, row):
        if self._latest(session, project_id).job_id != row.job_id:
            raise CreativeHandoffError("delivery_stale", "分支建议已不是当前任务，请刷新。")
        project = self._access.rows.project(session, project_id)
        from ...domain import ProjectBrief
        request = CreativeHandoffRequest.model_validate(row.request)
        if request.source != self._basis(session, project_id) or request.input_artifacts["outline-settings.json"] != outline_settings(ProjectBrief.model_validate(project.brief)):
            raise CreativeHandoffError("delivery_stale", "来源、大纲、简报或已保存分支已变化，请取消旧建议后重新准备。")
        return request

    @staticmethod
    def _view(row):
        return {"jobId": row.job_id, "status": row.status, "suggestion": row.outline}

    def state(self, project_id):
        with self._access.leases.lifecycle_write() as session:
            self._access.rows.project(session, project_id)
            row = self._latest(session, project_id)
            reasons = []
            if row is not None and row.status != "cancelled":
                try:
                    self._current(session, project_id, row)
                except (CreativeHandoffError, InvalidTransitionError) as error:
                    reasons.append(str(error))
            planned, infeasible = None, None
            try:
                planned = self._planned(session, project_id).model_dump(mode="json", by_alias=True)
            except InvalidTransitionError as error:
                infeasible = str(error)
            return BranchTaskState(candidate=BranchTaskCandidate.model_validate(self._view(row)) if row else None, stale_reasons=reasons, planned_topology=planned, infeasible_reason=infeasible)

    def prepare(self, project_id, exchange):
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            prior = self._latest(session, project_id)
            if prior and prior.status in {"prepared", "ready"}:
                raise InvalidTransitionError("已有分支建议任务，请先审阅或取消它。")
            basis = self._basis(session, project_id)
            from ...domain import ProjectBrief
            request = CreativeHandoffRequest(
                job_id=f"ch_{uuid4().hex}", project_id=project_id, section_id="branches", stage="branches",
                expected_stage_revision=basis["mapRevision"], source=basis,
                input_artifacts={"branch-schema.json": BranchSuggestion.model_json_schema(by_alias=True), "outline-settings.json": outline_settings(ProjectBrief.model_validate(project.brief))},
                creative_brief="从冻结的已确认大纲和 topology 提出完整剧情分支建议：每个计划节点的标题和剧情、每个选择的问题与所有选项和后续剧情、每个汇合的叙事衔接。保留所有节点、选项与汇合的身份和顺序，不新增或删减结构。选项、完整播放路线和不同结局是不同概念。不要把分集猜测为路线节点；保留来源事实。缺失或歧义时提出明确建议并在 clarifications 披露依据。只有建议，绝不接受、保存或安装路线。按 branch-schema.json 输出；代码管理身份和链接。",
            )
            pin = exchange.current_execution_pin("branches")
            freeze_execution_pin(session, request, pin)
            row = SourceOutlineCandidateRow(job_id=request.job_id, project_id=project_id,
                source_revision=basis["sourceRevision"], expected_outline_revision=basis["outline"]["revision"],
                request=request.model_dump(mode="json", by_alias=True), status="prepared", delivery_id=None,
                manifest_hash=None, outline=None, report_html=None, created_at=utc_now(), delivered_at=None)
            session.add(row)
        return request

    def request(self, project_id, job_id):
        with self._access.leases.read() as session:
            row = self._row(session, project_id, job_id)
            if row.status != "prepared" or self._latest(session, project_id).job_id != job_id:
                raise NotFoundError("当前分支建议不再等待交付")
            return CreativeHandoffRequest.model_validate(row.request)

    def admit(self, project_id, delivery: ValidatedCreativeDelivery):
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            row = self._row(session, project_id, delivery.request.job_id)
            request = self._current(session, project_id, row)
            if request != delivery.request or delivery.manifest.stage != "branches" or delivery.manifest.job_id != row.job_id:
                raise CreativeHandoffError("delivery_identity_mismatch", "分支建议身份不匹配")
            if row.status != "prepared":
                raise CreativeHandoffError("delivery_stale", "分支建议任务已终止")
            try:
                proposal = BranchSuggestion.model_validate(delivery.candidate)
                mapping = bind_branches(proposal, request.source["topology"])
                from ...source_outline_contracts import compile_section_map_graph, validate_section_map_graph
                from ...domain import ProjectBrief
                validate_section_map_graph(compile_section_map_graph(mapping), ProjectBrief.model_validate(self._access.rows.project(session, project_id).brief))
            except ValueError as error:
                raise CreativeHandoffError("delivery_candidate_invalid", "分支建议不完整或链接无效，请检查助手交付。") from error
            row.status = "ready"; row.outline = proposal.model_dump(mode="json", by_alias=True)
            row.report_html = delivery.report.decode("utf-8"); row.delivery_id = delivery.manifest.delivery_id
            row.manifest_hash = delivery.manifest_hash; row.delivered_at = utc_now()
            from types import SimpleNamespace
            return SimpleNamespace(status=row.status)

    def draft(self, project_id, job_id):
        with self._access.leases.lifecycle_write() as session:
            row = self._row(session, project_id, job_id)
            request = self._current(session, project_id, row)
            if row.status != "ready":
                raise InvalidTransitionError("分支建议尚未交付")
            return bind_branches(BranchSuggestion.model_validate(row.outline), request.source["topology"])

    def cancel(self, project_id, job_id):
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            self._row(session, project_id, job_id).status = "cancelled"
