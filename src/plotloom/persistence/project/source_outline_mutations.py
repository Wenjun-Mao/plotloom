"""Transactional source and outline revision mutations; map ownership stays separate."""

from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

from sqlalchemy import select

from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery, canonical_json
from ...domain import ProjectBrief, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...outline_settings import assert_outline_settings_current
from ...source_outline_contracts import (
    OutlineAcceptRequest, OutlineCandidate, OutlineReopenRequest,
    SourceMaterial, SourceOutlineReviewState,
)
from ..schema import SourceOutlineCandidateRow, SourceOutlineRevisionRow, SourceOutlineSourceRevisionRow
from .access import ProjectPersistenceAccess
from .creative_execution_pins import freeze_execution_pin

if TYPE_CHECKING:
    from .source_outline import ProjectSourceOutlinePersistence


class SourceOutlineMutations:
    """Share the source owner's transaction/row contract without another repository."""

    def __init__(self, access: ProjectPersistenceAccess, owner: ProjectSourceOutlinePersistence) -> None:
        self._access = access
        self._owner = owner

    def save_source(
        self, project_id: str, *, expected_source_revision: int, material: SourceMaterial
    ) -> SourceOutlineReviewState:
        material.assert_safe()
        payload = material.model_dump(mode="json", by_alias=True)
        digest = sha256(canonical_json(payload)).hexdigest()
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._owner._head(session, project_id, create=True)
            if head.source_revision != expected_source_revision:
                raise RevisionConflictError("source-outline source", expected_source_revision, head.source_revision)
            self._owner._assert_no_prepared_publication(session, project_id)
            if head.source_revision:
                prior = session.scalar(select(SourceOutlineSourceRevisionRow).where(
                    SourceOutlineSourceRevisionRow.project_id == project_id,
                    SourceOutlineSourceRevisionRow.revision == head.source_revision,
                ))
                if prior is not None and prior.content_hash == digest:
                    return self._owner._state_in_session(session, project_id, head)
            now = utc_now()
            head.source_revision += 1
            head.candidate_job_id = None
            head.outline_status = "reopened" if head.outline_revision else "missing"
            head.updated_at = now
            self._owner._mark_section_map_stale(
                session, project_id, f"accepted source revision changed to r{head.source_revision}", now
            )
            self._owner._mark_source_map_graph_stale(
                session, project_id, f"accepted source revision changed to r{head.source_revision}"
            )
            session.add(SourceOutlineSourceRevisionRow(
                id=new_id(), project_id=project_id, revision=head.source_revision,
                content_hash=digest, material=payload, created_at=now,
            ))
            return self._owner._state_in_session(session, project_id, head)

    def prepare_candidate(self, project_id: str, request: CreativeHandoffRequest, *, execution_pin: dict[str, str]) -> OutlineCandidate:
        request.assert_secret_free()
        if request.project_id != project_id or request.stage != "outline":
            raise CreativeHandoffError("request_identity_mismatch", "outline request does not belong to this project")
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._owner._head(session, project_id, create=True)
            if not head.source_revision:
                raise InvalidTransitionError("an accepted source is required before preparing an outline")
            if request.expected_stage_revision != head.outline_revision:
                raise CreativeHandoffError("delivery_stale", "outline request is based on a stale accepted outline revision")
            source = session.scalar(select(SourceOutlineSourceRevisionRow).where(
                SourceOutlineSourceRevisionRow.project_id == project_id,
                SourceOutlineSourceRevisionRow.revision == head.source_revision,
            ))
            if source is None or request.source != source.material:
                raise CreativeHandoffError("request_identity_mismatch", "outline request does not match the accepted source revision")
            assert_outline_settings_current(request, ProjectBrief.model_validate(project.brief))
            existing = session.get(SourceOutlineCandidateRow, request.job_id)
            if existing is not None:
                if existing.project_id != project_id or existing.request != request.model_dump(mode="json", by_alias=True):
                    raise CreativeHandoffError("request_identity_mismatch", "creative job identifier is already bound to another request")
                if existing.status != "prepared":
                    raise CreativeHandoffError("delivery_stale", "outline job identity is already terminal")
                return self._owner._candidate(existing)
            self._owner._assert_no_prepared_publication(session, project_id)
            freeze_execution_pin(session, request, execution_pin)
            now = utc_now()
            row = SourceOutlineCandidateRow(
                job_id=request.job_id, project_id=project_id,
                source_revision=head.source_revision,
                expected_outline_revision=head.outline_revision,
                request=request.model_dump(mode="json", by_alias=True), status="prepared",
                delivery_id=None, manifest_hash=None, outline=None, report_html=None,
                created_at=now, delivered_at=None,
            )
            session.add(row)
            head.candidate_job_id = row.job_id
            head.outline_status = "candidate_ready" if not head.outline_revision else "reopened"
            head.updated_at = now
            return self._owner._candidate(row)

    def admit_delivery(self, project_id: str, delivery: ValidatedCreativeDelivery) -> OutlineCandidate:
        request = delivery.request
        if request.project_id != project_id or request.stage != "outline":
            raise CreativeHandoffError("delivery_identity_mismatch", "delivery does not belong to this project outline")
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._owner._head(session, project_id, create=True)
            candidate = session.get(SourceOutlineCandidateRow, request.job_id)
            if candidate is None or candidate.project_id != project_id:
                raise CreativeHandoffError("delivery_identity_mismatch", "delivery has no project-owned prepared candidate")
            if head.candidate_job_id != candidate.job_id:
                raise CreativeHandoffError("delivery_stale", "delivery is no longer the active outline candidate")
            if candidate.request != request.model_dump(mode="json", by_alias=True):
                raise CreativeHandoffError("delivery_identity_mismatch", "delivery request differs from prepared candidate")
            if candidate.source_revision != head.source_revision or candidate.expected_outline_revision != head.outline_revision:
                raise CreativeHandoffError("delivery_stale", "candidate source or accepted outline revision is stale")
            if candidate.status == "cancelled":
                raise CreativeHandoffError("delivery_cancelled", "outline candidate was cancelled and cannot receive delivery")
            assert_outline_settings_current(request, ProjectBrief.model_validate(project.brief))
            if candidate.status == "ready":
                if candidate.manifest_hash != delivery.manifest_hash:
                    raise CreativeHandoffError("delivery_conflict", "a different delivery already occupies this candidate")
                return self._owner._candidate(candidate)
            if candidate.status != "prepared":
                raise CreativeHandoffError("delivery_stale", "outline candidate is no longer awaiting delivery")
            candidate.status = "ready"
            candidate.delivery_id = delivery.manifest.delivery_id
            candidate.manifest_hash = delivery.manifest_hash
            candidate.outline = delivery.candidate
            candidate.report_html = delivery.report.decode("utf-8")
            candidate.delivered_at = utc_now()
            head.outline_status = "candidate_ready"
            head.updated_at = candidate.delivered_at
            return self._owner._candidate(candidate)

    def accept_candidate(self, project_id: str, request: OutlineAcceptRequest) -> SourceOutlineReviewState:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._owner._head(session, project_id, create=True)
            if head.source_revision != request.expected_source_revision:
                raise RevisionConflictError("source-outline source", request.expected_source_revision, head.source_revision)
            if head.outline_revision != request.expected_outline_revision:
                raise RevisionConflictError("source-outline outline", request.expected_outline_revision, head.outline_revision)
            if head.candidate_job_id != request.job_id:
                raise CreativeHandoffError("delivery_stale", "only the current outline candidate may be accepted")
            candidate = session.get(SourceOutlineCandidateRow, request.job_id)
            if candidate is None or candidate.project_id != project_id or candidate.status != "ready" or candidate.outline is None:
                raise InvalidTransitionError("outline candidate is not ready for explicit acceptance")
            if candidate.source_revision != head.source_revision or candidate.expected_outline_revision != head.outline_revision:
                raise CreativeHandoffError("delivery_stale", "candidate is stale at acceptance")
            assert_outline_settings_current(
                CreativeHandoffRequest.model_validate(candidate.request), ProjectBrief.model_validate(project.brief),
            )
            now = utc_now()
            content_hash = sha256(canonical_json(candidate.outline)).hexdigest()
            head.outline_revision += 1
            head.outline_status = "accepted"
            head.updated_at = now
            candidate.status = "accepted"
            self._owner._mark_section_map_stale(
                session, project_id, f"accepted outline revision changed to r{head.outline_revision}", now
            )
            self._owner._mark_source_map_graph_stale(
                session, project_id, f"accepted outline revision changed to r{head.outline_revision}"
            )
            session.add(SourceOutlineRevisionRow(
                id=new_id(), project_id=project_id, revision=head.outline_revision,
                source_revision=head.source_revision, candidate_job_id=candidate.job_id,
                content_hash=content_hash, outline=candidate.outline, accepted_at=now,
            ))
            return self._owner._state_in_session(session, project_id, head)

    def reopen_outline(self, project_id: str, request: OutlineReopenRequest) -> SourceOutlineReviewState:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._owner._head(session, project_id, create=True)
            if head.outline_revision != request.expected_outline_revision:
                raise RevisionConflictError("source-outline outline", request.expected_outline_revision, head.outline_revision)
            if not head.outline_revision:
                raise InvalidTransitionError("no accepted outline exists to reopen")
            self._owner._assert_no_prepared_publication(session, project_id)
            head.outline_status = "reopened"
            head.candidate_job_id = None
            head.updated_at = utc_now()
            return self._owner._state_in_session(session, project_id, head)

    def return_to_accepted(self, project_id, request):
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._owner._head(session, project_id, create=True)
            if (head.outline_revision != request.expected_outline_revision
                    or head.source_revision != request.expected_source_revision
                    or head.candidate_job_id != request.expected_candidate_job_id):
                raise InvalidTransitionError("当前来源、大纲或候选已变化，请刷新后再决定。")
            state = self._owner._state_in_session(session, project_id, head)
            outline = state.accepted_outline
            if (head.outline_status != "reopened" or outline is None
                    or outline.source_revision != head.source_revision
                    or outline.content_hash != request.expected_outline_content_hash):
                raise InvalidTransitionError("保留的大纲已不适用于当前来源，请审阅并确认新的候选。")
            if head.candidate_job_id:
                candidate = session.get(SourceOutlineCandidateRow, head.candidate_job_id)
                if candidate and candidate.status in {"prepared", "ready"}:
                    candidate.status = "cancelled"
            head.candidate_job_id = None
            head.outline_status = "accepted"
            head.updated_at = utc_now()
            return self._owner._state_in_session(session, project_id, head)

    def cancel_candidate(self, project_id: str, job_id: str) -> SourceOutlineReviewState:
        """Durably discard one manual publication before it can install canon."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._owner._head(session, project_id, create=True)
            candidate = session.get(SourceOutlineCandidateRow, job_id)
            if candidate is None or candidate.project_id != project_id:
                raise NotFoundError("project outline candidate is unavailable")
            if candidate.status == "accepted":
                raise InvalidTransitionError("an accepted outline candidate cannot be cancelled")
            if candidate.status == "cancelled":
                return self._owner._state_in_session(session, project_id, head)
            candidate.status = "cancelled"
            if head.candidate_job_id == candidate.job_id:
                head.outline_status = "reopened" if head.outline_revision else "missing"
                head.updated_at = utc_now()
            return self._owner._state_in_session(session, project_id, head)
