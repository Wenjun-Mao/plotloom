"""Focused F2A owner for candidate-only upstream casts and explicit acceptance."""
from __future__ import annotations

from hashlib import sha256
from typing import Any
from sqlalchemy import select

from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery, canonical_json
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...cast_contracts import (
    AcceptedCastRevision, CastAcceptRequest, CastBinding, CastCandidate, CastConsumerMapping,
    CastReopenRequest, CastReviewState,
)
from ..schema.project_cast import CastCandidateRow, CastHeadRow, CastRevisionRow
from .access import ProjectPersistenceAccess
from .source_outline import ProjectSourceOutlinePersistence


class ProjectCastPersistence:
    def __init__(self, access: ProjectPersistenceAccess, source_outline: ProjectSourceOutlinePersistence) -> None:
        self._access, self._source_outline = access, source_outline

    def initialize(self, session: Any, project_id: str, *, created_at: Any) -> None:
        if session.get(CastHeadRow, project_id) is None:
            session.add(CastHeadRow(project_id=project_id, revision=0, candidate_job_id=None, status="missing", updated_at=created_at))

    @staticmethod
    def _candidate(row: CastCandidateRow) -> CastCandidate:
        return CastCandidate(job_id=row.job_id, expected_cast_revision=row.expected_cast_revision,
            binding=row.binding, status=row.status, delivery_id=row.delivery_id, manifest_hash=row.manifest_hash,
            cast=row.cast, report_available=row.report_html is not None, created_at=row.created_at, delivered_at=row.delivered_at)

    @staticmethod
    def _accepted(row: CastRevisionRow) -> AcceptedCastRevision:
        return AcceptedCastRevision(revision=row.revision, candidate_job_id=row.candidate_job_id,
            content_hash=row.content_hash, binding=row.binding, cast=row.cast,
            consumer_mappings=row.consumer_mappings, accepted_at=row.accepted_at)

    @staticmethod
    def _head(session: Any, project_id: str) -> CastHeadRow:
        row = session.get(CastHeadRow, project_id)
        if row is None: raise NotFoundError("project cast review state is missing")
        return row

    def _current_binding(self, project_id: str) -> CastBinding:
        source = self._source_outline.get_state(project_id)
        if source.source is None or source.accepted_outline is None or source.accepted_section_map is None:
            raise InvalidTransitionError("an accepted source, outline, and current section map are required before preparing cast")
        if source.outline_status != "accepted" or source.section_map_status != "current":
            raise InvalidTransitionError("accepted source/outline/section-map context is not current")
        mapping = source.accepted_section_map.mapping
        return CastBinding(source_revision=source.source.revision, source_content_hash=source.source.content_hash,
            outline_revision=source.accepted_outline.revision, outline_content_hash=source.accepted_outline.content_hash,
            section_map_revision=source.accepted_section_map.revision, section_map_content_hash=source.accepted_section_map.content_hash,
            section_ids=[section.section_id for section in mapping.sections])

    def _stale_reasons(self, project_id: str, binding: CastBinding) -> list[str]:
        try: current = self._current_binding(project_id)
        except InvalidTransitionError as error: return [str(error)]
        reasons: list[str] = []
        for field, label in (("source_revision", "source"), ("outline_revision", "accepted outline"), ("section_map_revision", "section map")):
            if getattr(current, field) != getattr(binding, field): reasons.append(f"{label} revision changed")
        for field, label in (("source_content_hash", "source"), ("outline_content_hash", "accepted outline"), ("section_map_content_hash", "section map")):
            if getattr(current, field) != getattr(binding, field): reasons.append(f"{label} content changed")
        if current.section_ids != binding.section_ids: reasons.append("section context changed")
        return reasons

    def get_state(self, project_id: str) -> CastReviewState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id); head = self._head(session, project_id)
            candidate = session.get(CastCandidateRow, head.candidate_job_id) if head.candidate_job_id else None
            accepted = session.scalar(select(CastRevisionRow).where(CastRevisionRow.project_id == project_id, CastRevisionRow.revision == head.revision)) if head.revision else None
            binding = accepted.binding if accepted else candidate.binding if candidate else None
            stale = self._stale_reasons(project_id, CastBinding.model_validate(binding)) if binding else []
            status = "stale" if stale and accepted else head.status
            return CastReviewState(candidate=self._candidate(candidate) if candidate else None, accepted_cast=self._accepted(accepted) if accepted else None, status=status, stale_reasons=stale)

    def prepare_candidate(self, project_id: str, request: CreativeHandoffRequest, binding: CastBinding) -> CastCandidate:
        request.assert_secret_free()
        if request.project_id != project_id or request.stage != "characters":
            raise CreativeHandoffError("request_identity_mismatch", "characters request does not belong to this project")
        if self._stale_reasons(project_id, binding): raise CreativeHandoffError("delivery_stale", "cast request context is stale")
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id); self._access.guards.active(project); head = self._head(session, project_id)
            if head.revision != request.expected_stage_revision:
                raise CreativeHandoffError("delivery_stale", "cast request is based on stale accepted cast")
            if session.scalar(select(CastCandidateRow.job_id).where(CastCandidateRow.project_id == project_id, CastCandidateRow.status == "prepared").limit(1)):
                raise InvalidTransitionError("cancel the prepared cast specialist publication before changing review state")
            now = utc_now(); row = CastCandidateRow(job_id=request.job_id, project_id=project_id, expected_cast_revision=head.revision,
                binding=binding.model_dump(mode="json", by_alias=True), request=request.model_dump(mode="json", by_alias=True), status="prepared", delivery_id=None, manifest_hash=None, cast=None, report_html=None, created_at=now, delivered_at=None)
            session.add(row); head.candidate_job_id=row.job_id; head.status="prepared"; head.updated_at=now
            return self._candidate(row)

    def admit_delivery(self, project_id: str, delivery: ValidatedCreativeDelivery) -> CastCandidate:
        request=delivery.request
        if request.stage != "characters" or request.project_id != project_id: raise CreativeHandoffError("delivery_identity_mismatch", "delivery does not belong to this cast")
        with self._access.leases.lifecycle_write() as session:
            project=self._access.rows.project(session, project_id); self._access.guards.active(project); head=self._head(session, project_id); row=session.get(CastCandidateRow, request.job_id)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.request != request.model_dump(mode="json", by_alias=True): raise CreativeHandoffError("delivery_stale", "delivery is not the current prepared cast")
            if row.status == "cancelled": raise CreativeHandoffError("delivery_cancelled", "cast candidate was cancelled")
            if row.status == "ready":
                if row.manifest_hash != delivery.manifest_hash: raise CreativeHandoffError("delivery_conflict", "different delivery already occupies cast candidate")
                return self._candidate(row)
            if row.status != "prepared" or row.expected_cast_revision != head.revision or self._stale_reasons(project_id, CastBinding.model_validate(row.binding)): raise CreativeHandoffError("delivery_stale", "cast candidate context is stale")
            _validate_cast(delivery.candidate)
            row.status="ready"; row.delivery_id=delivery.manifest.delivery_id; row.manifest_hash=delivery.manifest_hash; row.cast=delivery.candidate; row.report_html=delivery.report.decode("utf-8"); row.delivered_at=utc_now(); head.status="candidate_ready"; head.updated_at=row.delivered_at
            return self._candidate(row)

    def accept_candidate(self, project_id: str, request: CastAcceptRequest) -> CastReviewState:
        with self._access.leases.lifecycle_write() as session:
            project=self._access.rows.project(session, project_id); self._access.guards.active(project); head=self._head(session, project_id)
            if head.revision != request.expected_cast_revision: raise RevisionConflictError("cast", request.expected_cast_revision, head.revision)
            row=session.get(CastCandidateRow, request.job_id)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.status != "ready" or row.cast is None: raise InvalidTransitionError("cast candidate is not ready for explicit acceptance")
            binding=CastBinding.model_validate(row.binding)
            if binding != request.binding or self._stale_reasons(project_id, binding): raise CreativeHandoffError("delivery_stale", "cast candidate context changed before acceptance")
            accepted_cast = request.cast if request.cast is not None else row.cast
            _validate_cast(accepted_cast)
            ids=_cast_ids(row.cast)
            if _cast_ids(accepted_cast) != ids: raise ValueError("accepted cast cannot change frozen character IDs")
            pairs={(item.cast_character_id,item.consumer_character_id) for item in request.consumer_mappings}
            if {item[0] for item in pairs} != set(ids) or len(pairs) != len(ids): raise ValueError("every accepted cast character needs one explicit consumer mapping")
            now=utc_now(); head.revision += 1; head.status="accepted"; head.updated_at=now; row.status="accepted"
            session.add(CastRevisionRow(id=new_id(),project_id=project_id,revision=head.revision,candidate_job_id=row.job_id,content_hash=sha256(canonical_json(accepted_cast)).hexdigest(),binding=row.binding,cast=accepted_cast,consumer_mappings=[item.model_dump(mode="json",by_alias=True) for item in request.consumer_mappings],accepted_at=now))
        return self.get_state(project_id)

    def reopen(self, project_id: str, request: CastReopenRequest) -> CastReviewState:
        with self._access.leases.lifecycle_write() as session:
            project=self._access.rows.project(session, project_id); self._access.guards.active(project); head=self._head(session, project_id)
            if head.revision != request.expected_cast_revision: raise RevisionConflictError("cast",request.expected_cast_revision,head.revision)
            if not head.revision: raise InvalidTransitionError("no accepted cast exists to reopen")
            head.status="reopened"; head.candidate_job_id=None; head.updated_at=utc_now()
        return self.get_state(project_id)

    def cancel_candidate(self, project_id: str, job_id: str) -> CastReviewState:
        with self._access.leases.lifecycle_write() as session:
            project=self._access.rows.project(session, project_id); self._access.guards.active(project); head=self._head(session, project_id); row=session.get(CastCandidateRow, job_id)
            if row is None or row.project_id != project_id: raise NotFoundError("project cast candidate is unavailable")
            if row.status == "accepted": raise InvalidTransitionError("accepted cast candidate cannot be cancelled")
            row.status="cancelled"; head.status="reopened" if head.revision else "missing"; head.updated_at=utc_now()
        return self.get_state(project_id)

    def candidate_report(self, project_id: str, job_id: str) -> str:
        with self._access.leases.read() as session:
            row=session.get(CastCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status not in {"ready","accepted"} or row.report_html is None: raise NotFoundError("ready cast report is unavailable")
            return row.report_html
    def candidate_request(self, project_id: str, job_id: str) -> CreativeHandoffRequest:
        with self._access.leases.read() as session:
            row=session.get(CastCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status == "cancelled": raise NotFoundError("project cast candidate is unavailable")
            return CreativeHandoffRequest.model_validate(row.request)

def _cast_ids(cast: dict[str, Any]) -> list[str]:
    characters=cast.get("characters")
    if not isinstance(characters,list) or not characters: raise ValueError("upstream cast must contain characters")
    ids=[item.get("id") for item in characters if isinstance(item,dict)]
    if len(ids)!=len(characters) or any(not isinstance(item,str) or not item.strip() for item in ids) or len(set(ids))!=len(ids): raise ValueError("each upstream cast character needs a unique stable id")
    return ids

def _validate_cast(cast: dict[str, Any]) -> None:
    if not isinstance(cast.get("source"),str) or not isinstance(cast.get("summary"),str): raise ValueError("upstream cast must retain source and summary")
    _cast_ids(cast)
