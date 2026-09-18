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
    AcceptedOutlineRevision, AcceptedSectionMapRevision,
    OutlineAcceptRequest,
    OutlineCandidate,
    OutlineReopenRequest,
    SectionMapSaveRequest,
    SourceMaterial,
    SourceOutlineReviewState,
    SourceRevision,
)
from ..schema import (
    SourceOutlineCandidateRow,
    SourceOutlineHeadRow,
    SourceOutlineRevisionRow,
    SourceOutlineSectionMapHeadRow,
    SourceOutlineSectionMapRevisionRow,
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

    @staticmethod
    def _section_map(row: SourceOutlineSectionMapRevisionRow) -> AcceptedSectionMapRevision:
        return AcceptedSectionMapRevision(
            revision=row.revision,
            source_revision=row.source_revision,
            outline_revision=row.outline_revision,
            outline_content_hash=row.outline_content_hash,
            content_hash=row.content_hash,
            mapping=row.mapping,
            accepted_at=row.accepted_at,
        )

    @staticmethod
    def _section_map_head(session: Any, project_id: str, *, create: bool) -> SourceOutlineSectionMapHeadRow:
        row = session.get(SourceOutlineSectionMapHeadRow, project_id)
        if row is None and create:
            row = SourceOutlineSectionMapHeadRow(
                project_id=project_id, revision=0, status="missing", stale_reasons=[], updated_at=utc_now()
            )
            session.add(row)
            session.flush()
        if row is None:
            raise NotFoundError("project section-map review state is missing")
        return row

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
        if session.get(SourceOutlineSectionMapHeadRow, project_id) is None:
            session.add(SourceOutlineSectionMapHeadRow(
                project_id=project_id, revision=0, status="missing", stale_reasons=[], updated_at=created_at,
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
            section_map_head = session.get(SourceOutlineSectionMapHeadRow, project_id)
            section_map = self._section_map_for_head(session, project_id, section_map_head) if section_map_head else None
            return SourceOutlineReviewState(
                source=source,
                candidate=self._candidate(candidate) if candidate is not None else None,
                accepted_outline=outline,
                outline_status=head.outline_status,
                accepted_section_map=section_map,
                section_map_status=section_map_head.status if section_map_head else "missing",
                section_map_stale_reasons=section_map_head.stale_reasons if section_map_head else [],
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
            self._assert_no_prepared_publication(session, project_id)
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
            self._mark_section_map_stale(
                session, project_id, f"accepted source revision changed to r{head.source_revision}", now
            )
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
                if existing.status != "prepared":
                    raise CreativeHandoffError("delivery_stale", "outline job identity is already terminal")
                return self._candidate(existing)
            self._assert_no_prepared_publication(session, project_id)
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
            if candidate.status == "cancelled":
                raise CreativeHandoffError("delivery_cancelled", "outline candidate was cancelled and cannot receive delivery")
            if candidate.status == "ready":
                if candidate.manifest_hash != delivery.manifest_hash:
                    raise CreativeHandoffError("delivery_conflict", "a different delivery already occupies this candidate")
                return self._candidate(candidate)
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
            candidate.status = "accepted"
            self._mark_section_map_stale(
                session, project_id, f"accepted outline revision changed to r{head.outline_revision}", now
            )
            session.add(SourceOutlineRevisionRow(
                id=new_id(), project_id=project_id, revision=head.outline_revision,
                source_revision=head.source_revision, candidate_job_id=candidate.job_id,
                content_hash=content_hash, outline=candidate.outline, accepted_at=now,
            ))
            return self._state_in_session(session, project_id, head)

    def save_section_map(self, project_id: str, request: SectionMapSaveRequest) -> SourceOutlineReviewState:
        """Accept one author-reviewed binary map bound to the exact outline revision."""

        request.mapping.validate_links()
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            outline_head = self._head(session, project_id, create=True)
            section_map_head = self._section_map_head(session, project_id, create=True)
            if section_map_head.revision != request.expected_section_map_revision:
                raise RevisionConflictError("source-outline section map", request.expected_section_map_revision, section_map_head.revision)
            if outline_head.source_revision != request.expected_source_revision:
                raise RevisionConflictError("source-outline source", request.expected_source_revision, outline_head.source_revision)
            if outline_head.outline_revision != request.expected_outline_revision:
                raise RevisionConflictError("source-outline outline", request.expected_outline_revision, outline_head.outline_revision)
            if not outline_head.outline_revision:
                raise InvalidTransitionError("an accepted outline is required before saving a section map")
            outline = session.scalar(select(SourceOutlineRevisionRow).where(
                SourceOutlineRevisionRow.project_id == project_id,
                SourceOutlineRevisionRow.revision == outline_head.outline_revision,
            ))
            if outline is None:
                raise NotFoundError("accepted outline revision is missing")
            if outline.content_hash != request.expected_outline_content_hash:
                raise RevisionConflictError("source-outline outline content", 0, 1)
            payload = request.mapping.model_dump(mode="json", by_alias=True)
            now = utc_now()
            section_map_head.revision += 1
            section_map_head.status = "current"
            section_map_head.stale_reasons = []
            section_map_head.updated_at = now
            session.add(SourceOutlineSectionMapRevisionRow(
                id=new_id(), project_id=project_id, revision=section_map_head.revision,
                source_revision=outline_head.source_revision, outline_revision=outline_head.outline_revision,
                outline_content_hash=outline.content_hash, content_hash=sha256(canonical_json(payload)).hexdigest(),
                mapping=payload, accepted_at=now,
            ))
            return self._state_in_session(session, project_id, outline_head)

    def reopen_outline(self, project_id: str, request: OutlineReopenRequest) -> SourceOutlineReviewState:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._head(session, project_id, create=True)
            if head.outline_revision != request.expected_outline_revision:
                raise RevisionConflictError("source-outline outline", request.expected_outline_revision, head.outline_revision)
            if not head.outline_revision:
                raise InvalidTransitionError("no accepted outline exists to reopen")
            self._assert_no_prepared_publication(session, project_id)
            head.outline_status = "reopened"
            head.candidate_job_id = None
            head.updated_at = utc_now()
            return self._state_in_session(session, project_id, head)

    def cancel_candidate(self, project_id: str, job_id: str) -> SourceOutlineReviewState:
        """Durably discard one manual publication before it can install canon."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._head(session, project_id, create=True)
            candidate = session.get(SourceOutlineCandidateRow, job_id)
            if candidate is None or candidate.project_id != project_id:
                raise NotFoundError("project outline candidate is unavailable")
            if candidate.status == "accepted":
                raise InvalidTransitionError("an accepted outline candidate cannot be cancelled")
            if candidate.status == "cancelled":
                return self._state_in_session(session, project_id, head)
            candidate.status = "cancelled"
            if head.candidate_job_id == candidate.job_id:
                head.outline_status = "reopened" if head.outline_revision else "missing"
                head.updated_at = utc_now()
            return self._state_in_session(session, project_id, head)

    def candidate_report(self, project_id: str, job_id: str) -> str:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            candidate = session.get(SourceOutlineCandidateRow, job_id)
            if candidate is None or candidate.project_id != project_id or candidate.status not in {"ready", "accepted"} or candidate.report_html is None:
                raise NotFoundError("ready outline candidate report is unavailable")
            return candidate.report_html

    def candidate_request(self, project_id: str, job_id: str) -> CreativeHandoffRequest:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            candidate = session.get(SourceOutlineCandidateRow, job_id)
            if candidate is None or candidate.project_id != project_id:
                raise NotFoundError("project outline candidate is unavailable")
            if candidate.status == "cancelled":
                raise CreativeHandoffError("delivery_cancelled", "outline candidate was cancelled and cannot be refreshed")
            return CreativeHandoffRequest.model_validate(candidate.request)

    @staticmethod
    def _assert_no_prepared_publication(session: Any, project_id: str) -> None:
        prepared = session.scalar(select(SourceOutlineCandidateRow.job_id).where(
            SourceOutlineCandidateRow.project_id == project_id,
            SourceOutlineCandidateRow.status == "prepared",
        ).limit(1))
        if prepared is not None:
            raise InvalidTransitionError(
                "cancel the prepared outline specialist publication before changing review state"
            )

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
        section_map_head = self._section_map_head(session, project_id, create=True)
        section_map = self._section_map_for_head(session, project_id, section_map_head)
        return SourceOutlineReviewState(
            source=source,
            candidate=self._candidate(candidate) if candidate is not None else None,
            accepted_outline=outline,
            outline_status=head.outline_status,
            accepted_section_map=section_map,
            section_map_status=section_map_head.status,
            section_map_stale_reasons=section_map_head.stale_reasons,
        )

    def _section_map_for_head(
        self, session: Any, project_id: str, head: SourceOutlineSectionMapHeadRow
    ) -> AcceptedSectionMapRevision | None:
        if not head.revision:
            return None
        row = session.scalar(select(SourceOutlineSectionMapRevisionRow).where(
            SourceOutlineSectionMapRevisionRow.project_id == project_id,
            SourceOutlineSectionMapRevisionRow.revision == head.revision,
        ))
        if row is None:
            raise NotFoundError("accepted section-map revision is missing")
        return self._section_map(row)

    def _mark_section_map_stale(self, session: Any, project_id: str, reason: str, now: Any) -> None:
        head = self._section_map_head(session, project_id, create=True)
        if not head.revision:
            return
        head.status = "stale"
        head.stale_reasons = [reason]
        head.updated_at = now
