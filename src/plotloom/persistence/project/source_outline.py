"""CAS-bound persistence for the F1A source-to-outline review handoff."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from sqlalchemy import select

from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery, canonical_json
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...source_outline_contracts import (
    AcceptedOutlineRevision,
    OutlineAcceptRequest,
    OutlineCandidate,
    OutlineReopenRequest,
    SourceMaterial,
    SourceOutlineReviewState,
    SourceRevision,
)
from ..schema import (
    SourceOutlineCandidateRow,
    SourceOutlineHeadRow,
    SourceOutlineRevisionRow,
    SourceOutlineSourceRevisionRow,
)
from .access import ProjectPersistenceAccess


class ProjectSourceOutlinePersistence:
    """Own one accepted source and outline without translating upstream JSON."""

    def __init__(self, access: ProjectPersistenceAccess) -> None:
        self._access = access

    @staticmethod
    def _source(row: SourceOutlineSourceRevisionRow) -> SourceRevision:
        return SourceRevision(
            revision=row.revision,
            content_hash=row.content_hash,
            material=SourceMaterial.model_validate(row.material),
            created_at=row.created_at,
        )

    @staticmethod
    def _candidate(row: SourceOutlineCandidateRow) -> OutlineCandidate:
        return OutlineCandidate(
            job_id=row.job_id,
            source_revision=row.source_revision,
            expected_outline_revision=row.expected_outline_revision,
            status=row.status,
            delivery_id=row.delivery_id,
            manifest_hash=row.manifest_hash,
            outline=row.outline,
            report_available=row.report_html is not None,
            created_at=row.created_at,
            delivered_at=row.delivered_at,
        )

    @staticmethod
    def _outline(row: SourceOutlineRevisionRow) -> AcceptedOutlineRevision:
        return AcceptedOutlineRevision(
            revision=row.revision,
            source_revision=row.source_revision,
            candidate_job_id=row.candidate_job_id,
            content_hash=row.content_hash,
            outline=row.outline,
            accepted_at=row.accepted_at,
        )

    def _head(self, session: Any, project_id: str, *, create: bool) -> SourceOutlineHeadRow:
        row = session.get(SourceOutlineHeadRow, project_id)
        if row is None and create:
            row = SourceOutlineHeadRow(
                project_id=project_id,
                source_revision=0,
                outline_revision=0,
                candidate_job_id=None,
                outline_status="missing",
                updated_at=utc_now(),
            )
            session.add(row)
            session.flush()
        if row is None:
            raise NotFoundError("project source-outline review state is missing")
        return row

    def initialize(self, session: Any, project_id: str, *, created_at: Any) -> None:
        if session.get(SourceOutlineHeadRow, project_id) is None:
            session.add(SourceOutlineHeadRow(
                project_id=project_id,
                source_revision=0,
                outline_revision=0,
                candidate_job_id=None,
                outline_status="missing",
                updated_at=created_at,
            ))

    def get_state(self, project_id: str) -> SourceOutlineReviewState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            head = self._head(session, project_id, create=False)
            source = None
            if head.source_revision:
                source_row = session.scalar(select(SourceOutlineSourceRevisionRow).where(
                    SourceOutlineSourceRevisionRow.project_id == project_id,
                    SourceOutlineSourceRevisionRow.revision == head.source_revision,
                ))
                if source_row is None:
                    raise NotFoundError("accepted source revision is missing")
                source = self._source(source_row)
            candidate = session.get(SourceOutlineCandidateRow, head.candidate_job_id) if head.candidate_job_id else None
            if candidate is not None and candidate.project_id != project_id:
                raise InvalidTransitionError("source-outline candidate belongs to another project")
            outline = None
            if head.outline_revision:
                outline_row = session.scalar(select(SourceOutlineRevisionRow).where(
                    SourceOutlineRevisionRow.project_id == project_id,
                    SourceOutlineRevisionRow.revision == head.outline_revision,
                ))
                if outline_row is None:
                    raise NotFoundError("accepted outline revision is missing")
                outline = self._outline(outline_row)
            return SourceOutlineReviewState(
                source=source,
                candidate=self._candidate(candidate) if candidate is not None else None,
                accepted_outline=outline,
                outline_status=head.outline_status,
            )

    def save_source(
        self, project_id: str, *, expected_source_revision: int, material: SourceMaterial
    ) -> SourceOutlineReviewState:
        material.assert_safe()
        payload = material.model_dump(mode="json", by_alias=True)
        digest = sha256(canonical_json(payload)).hexdigest()
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._head(session, project_id, create=True)
            if head.source_revision != expected_source_revision:
                raise RevisionConflictError("source-outline source", expected_source_revision, head.source_revision)
            if head.source_revision:
                prior = session.scalar(select(SourceOutlineSourceRevisionRow).where(
                    SourceOutlineSourceRevisionRow.project_id == project_id,
                    SourceOutlineSourceRevisionRow.revision == head.source_revision,
                ))
                if prior is not None and prior.content_hash == digest:
                    return self._state_in_session(session, project_id, head)
            now = utc_now()
            head.source_revision += 1
            head.candidate_job_id = None
            head.outline_status = "reopened" if head.outline_revision else "missing"
            head.updated_at = now
            session.add(SourceOutlineSourceRevisionRow(
                id=new_id(), project_id=project_id, revision=head.source_revision,
                content_hash=digest, material=payload, created_at=now,
            ))
            return self._state_in_session(session, project_id, head)

    def prepare_candidate(self, project_id: str, request: CreativeHandoffRequest) -> OutlineCandidate:
        request.assert_secret_free()
        if request.project_id != project_id or request.stage != "outline":
            raise CreativeHandoffError("request_identity_mismatch", "outline request does not belong to this project")
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._head(session, project_id, create=True)
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
            existing = session.get(SourceOutlineCandidateRow, request.job_id)
            if existing is not None:
                if existing.project_id != project_id or existing.request != request.model_dump(mode="json", by_alias=True):
                    raise CreativeHandoffError("request_identity_mismatch", "creative job identifier is already bound to another request")
                return self._candidate(existing)
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
            return self._candidate(row)

    def admit_delivery(self, project_id: str, delivery: ValidatedCreativeDelivery) -> OutlineCandidate:
        request = delivery.request
        if request.project_id != project_id or request.stage != "outline":
            raise CreativeHandoffError("delivery_identity_mismatch", "delivery does not belong to this project outline")
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._head(session, project_id, create=True)
            candidate = session.get(SourceOutlineCandidateRow, request.job_id)
            if candidate is None or candidate.project_id != project_id:
                raise CreativeHandoffError("delivery_identity_mismatch", "delivery has no project-owned prepared candidate")
            if head.candidate_job_id != candidate.job_id:
                raise CreativeHandoffError("delivery_stale", "delivery is no longer the active outline candidate")
            if candidate.request != request.model_dump(mode="json", by_alias=True):
                raise CreativeHandoffError("delivery_identity_mismatch", "delivery request differs from prepared candidate")
            if candidate.source_revision != head.source_revision or candidate.expected_outline_revision != head.outline_revision:
                raise CreativeHandoffError("delivery_stale", "candidate source or accepted outline revision is stale")
            if candidate.status == "ready":
                if candidate.manifest_hash != delivery.manifest_hash:
                    raise CreativeHandoffError("delivery_conflict", "a different delivery already occupies this candidate")
                return self._candidate(candidate)
            candidate.status = "ready"
            candidate.delivery_id = delivery.manifest.delivery_id
            candidate.manifest_hash = delivery.manifest_hash
            candidate.outline = delivery.candidate
            candidate.report_html = delivery.report.decode("utf-8")
            candidate.delivered_at = utc_now()
            head.outline_status = "candidate_ready"
            head.updated_at = candidate.delivered_at
            return self._candidate(candidate)

    def accept_candidate(self, project_id: str, request: OutlineAcceptRequest) -> SourceOutlineReviewState:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._head(session, project_id, create=True)
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
            now = utc_now()
            content_hash = sha256(canonical_json(candidate.outline)).hexdigest()
            head.outline_revision += 1
            head.outline_status = "accepted"
            head.updated_at = now
            session.add(SourceOutlineRevisionRow(
                id=new_id(), project_id=project_id, revision=head.outline_revision,
                source_revision=head.source_revision, candidate_job_id=candidate.job_id,
                content_hash=content_hash, outline=candidate.outline, accepted_at=now,
            ))
            return self._state_in_session(session, project_id, head)

    def reopen_outline(self, project_id: str, request: OutlineReopenRequest) -> SourceOutlineReviewState:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._head(session, project_id, create=True)
            if head.outline_revision != request.expected_outline_revision:
                raise RevisionConflictError("source-outline outline", request.expected_outline_revision, head.outline_revision)
            if not head.outline_revision:
                raise InvalidTransitionError("no accepted outline exists to reopen")
            head.outline_status = "reopened"
            head.candidate_job_id = None
            head.updated_at = utc_now()
            return self._state_in_session(session, project_id, head)

    def candidate_report(self, project_id: str, job_id: str) -> str:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            candidate = session.get(SourceOutlineCandidateRow, job_id)
            if candidate is None or candidate.project_id != project_id or candidate.status != "ready" or candidate.report_html is None:
                raise NotFoundError("ready outline candidate report is unavailable")
            return candidate.report_html

    def candidate_request(self, project_id: str, job_id: str) -> CreativeHandoffRequest:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            candidate = session.get(SourceOutlineCandidateRow, job_id)
            if candidate is None or candidate.project_id != project_id:
                raise NotFoundError("project outline candidate is unavailable")
            return CreativeHandoffRequest.model_validate(candidate.request)

    def _state_in_session(self, session: Any, project_id: str, head: SourceOutlineHeadRow) -> SourceOutlineReviewState:
        source = None
        if head.source_revision:
            source_row = session.scalar(select(SourceOutlineSourceRevisionRow).where(
                SourceOutlineSourceRevisionRow.project_id == project_id,
                SourceOutlineSourceRevisionRow.revision == head.source_revision,
            ))
            if source_row is not None:
                source = self._source(source_row)
        candidate = session.get(SourceOutlineCandidateRow, head.candidate_job_id) if head.candidate_job_id else None
        outline = None
        if head.outline_revision:
            outline_row = session.scalar(select(SourceOutlineRevisionRow).where(
                SourceOutlineRevisionRow.project_id == project_id,
                SourceOutlineRevisionRow.revision == head.outline_revision,
            ))
            if outline_row is not None:
                outline = self._outline(outline_row)
        return SourceOutlineReviewState(
            source=source,
            candidate=self._candidate(candidate) if candidate is not None else None,
            accepted_outline=outline,
            outline_status=head.outline_status,
        )
