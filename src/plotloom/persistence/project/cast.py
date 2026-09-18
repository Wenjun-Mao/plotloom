"""Focused F2A owner for upstream cast review and explicit acceptance."""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from sqlalchemy import select

from ...cast_contracts import AcceptedCastRevision, CastAcceptRequest, CastBinding, CastCandidate, CastConsumerMapping, CastReopenRequest, CastReviewState, CastSaveRequest
from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery, canonical_json
from ...domain import StageName, StageStatus, contains_secret_setting, contains_secret_value, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ..schema.project_authoring import StageHeadRow
from ..schema.project_cast import CastCandidateRow, CastHeadRow, CastRevisionRow
from ..schema.project_source_outline import SourceOutlineGraphAdmissionRow, SourceOutlineHeadRow, SourceOutlineRevisionRow, SourceOutlineSectionMapHeadRow, SourceOutlineSectionMapRevisionRow, SourceOutlineSourceRevisionRow
from .access import ProjectPersistenceAccess


class ProjectCastPersistence:
    def __init__(self, access: ProjectPersistenceAccess) -> None:
        self._access = access

    def initialize(self, session: Any, project_id: str, *, created_at: Any) -> None:
        if session.get(CastHeadRow, project_id) is None:
            session.add(CastHeadRow(project_id=project_id, revision=0, candidate_job_id=None, status="missing", updated_at=created_at))

    @staticmethod
    def _candidate(row: CastCandidateRow) -> CastCandidate:
        return CastCandidate(job_id=row.job_id, expected_cast_revision=row.expected_cast_revision, binding=row.binding, status=row.status, delivery_id=row.delivery_id, manifest_hash=row.manifest_hash, cast=row.cast, report_available=row.report_html is not None, created_at=row.created_at, delivered_at=row.delivered_at)

    @staticmethod
    def _accepted(row: CastRevisionRow) -> AcceptedCastRevision:
        return AcceptedCastRevision(revision=row.revision, candidate_job_id=row.candidate_job_id, content_hash=row.content_hash, binding=row.binding, cast=row.cast, consumer_mappings=row.consumer_mappings, accepted_at=row.accepted_at)

    @staticmethod
    def _head(session: Any, project_id: str) -> CastHeadRow:
        row = session.get(CastHeadRow, project_id)
        if row is None:
            raise NotFoundError("project cast review state is missing")
        return row

    def _context(self, session: Any, project_id: str) -> tuple[CastBinding, dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Use one database snapshot for source, map, graph, and cast CAS inputs."""
        head = session.get(SourceOutlineHeadRow, project_id)
        map_head = session.get(SourceOutlineSectionMapHeadRow, project_id)
        if head is None or map_head is None or not head.source_revision or not head.outline_revision or not map_head.revision or head.outline_status != "accepted" or map_head.status != "current":
            raise InvalidTransitionError("an accepted source, outline, current section map, and installed graph are required before preparing cast")
        source = session.scalar(select(SourceOutlineSourceRevisionRow).where(SourceOutlineSourceRevisionRow.project_id == project_id, SourceOutlineSourceRevisionRow.revision == head.source_revision))
        outline = session.scalar(select(SourceOutlineRevisionRow).where(SourceOutlineRevisionRow.project_id == project_id, SourceOutlineRevisionRow.revision == head.outline_revision))
        mapping = session.scalar(select(SourceOutlineSectionMapRevisionRow).where(SourceOutlineSectionMapRevisionRow.project_id == project_id, SourceOutlineSectionMapRevisionRow.revision == map_head.revision))
        admission = session.get(SourceOutlineGraphAdmissionRow, project_id)
        graph = session.scalar(select(StageHeadRow).where(StageHeadRow.project_id == project_id, StageHeadRow.stage == StageName.STORY_GRAPH.value))
        if source is None or outline is None or mapping is None or admission is None or graph is None or admission.status != "current" or graph.status != StageStatus.READY.value:
            raise InvalidTransitionError("the accepted source-map-installed graph is not current")
        if not (admission.source_revision == source.revision and admission.source_content_hash == source.content_hash and admission.outline_revision == outline.revision and admission.outline_content_hash == outline.content_hash and admission.section_map_revision == mapping.revision and admission.section_map_content_hash == mapping.content_hash and admission.graph_revision == graph.revision and admission.graph_content_hash == graph.content_hash):
            raise InvalidTransitionError("the installed graph no longer matches the accepted source-map context")
        binding = CastBinding(source_revision=source.revision, source_content_hash=source.content_hash, outline_revision=outline.revision, outline_content_hash=outline.content_hash, section_map_revision=mapping.revision, section_map_content_hash=mapping.content_hash, graph_revision=graph.revision, graph_content_hash=graph.content_hash or "", section_ids=[str(item.get("sectionId", "")) for item in mapping.mapping.get("sections", [])])
        return binding, source.material, outline.outline, mapping.mapping

    def _stale(self, session: Any, project_id: str, binding: CastBinding) -> list[str]:
        try:
            current, *_ = self._context(session, project_id)
        except InvalidTransitionError as error:
            return [str(error)]
        fields = (("source_revision", "source"), ("outline_revision", "accepted outline"), ("section_map_revision", "section map"), ("graph_revision", "installed graph"), ("source_content_hash", "source"), ("outline_content_hash", "accepted outline"), ("section_map_content_hash", "section map"), ("graph_content_hash", "installed graph"))
        reasons = [f"{label} {'revision' if field.endswith('revision') else 'content'} changed" for field, label in fields if getattr(current, field) != getattr(binding, field)]
        return reasons + (["section context changed"] if current.section_ids != binding.section_ids else [])

    def get_state(self, project_id: str) -> CastReviewState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            head = self._head(session, project_id)
            candidate = session.get(CastCandidateRow, head.candidate_job_id) if head.candidate_job_id else None
            accepted = session.scalar(select(CastRevisionRow).where(CastRevisionRow.project_id == project_id, CastRevisionRow.revision == head.revision)) if head.revision else None
            binding = accepted.binding if accepted else candidate.binding if candidate else None
            stale = self._stale(session, project_id, CastBinding.model_validate(binding)) if binding else []
            return CastReviewState(candidate=self._candidate(candidate) if candidate else None, accepted_cast=self._accepted(accepted) if accepted else None, status="stale" if stale and accepted else head.status, stale_reasons=stale)

    def prepare_candidate(self, project_id: str, job_id: str) -> tuple[CastCandidate, CreativeHandoffRequest]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._head(session, project_id)
            binding, source, outline, section_map = self._context(session, project_id)
            if session.scalar(select(CastCandidateRow.job_id).where(CastCandidateRow.project_id == project_id, CastCandidateRow.status == "prepared").limit(1)):
                raise InvalidTransitionError("cancel the prepared cast specialist publication before changing review state")
            request = CreativeHandoffRequest(job_id=job_id, project_id=project_id, section_id="shared-cast", stage="characters", expected_stage_revision=head.revision, source=source, input_artifacts={"outline.json": outline, "section-map.json": section_map}, creative_brief="Create one upstream-shaped cast.json candidate for the accepted source, outline, and installed stable section context. Shared characters are authored once; preserve stable character IDs and make section presence/context explicit. This is a candidate only, not voice evidence, media generation, or project canon.")
            request.assert_secret_free()
            now = utc_now()
            row = CastCandidateRow(job_id=job_id, project_id=project_id, expected_cast_revision=head.revision, binding=binding.model_dump(mode="json", by_alias=True), request=request.model_dump(mode="json", by_alias=True), status="prepared", delivery_id=None, manifest_hash=None, cast=None, report_html=None, created_at=now, delivered_at=None)
            session.add(row)
            head.candidate_job_id, head.status, head.updated_at = job_id, "prepared", now
            return self._candidate(row), request

    def admit_delivery(self, project_id: str, delivery: ValidatedCreativeDelivery) -> CastCandidate:
        request = delivery.request
        if request.stage != "characters" or request.project_id != project_id:
            raise CreativeHandoffError("delivery_identity_mismatch", "delivery does not belong to this cast")
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head, row = self._head(session, project_id), session.get(CastCandidateRow, request.job_id)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.request != request.model_dump(mode="json", by_alias=True):
                raise CreativeHandoffError("delivery_stale", "delivery is not the current prepared cast")
            if row.status == "cancelled":
                raise CreativeHandoffError("delivery_cancelled", "cast candidate was cancelled")
            if row.status == "ready":
                if row.manifest_hash != delivery.manifest_hash:
                    raise CreativeHandoffError("delivery_conflict", "different delivery already occupies cast candidate")
                return self._candidate(row)
            if row.status != "prepared" or row.expected_cast_revision != head.revision or self._stale(session, project_id, CastBinding.model_validate(row.binding)):
                raise CreativeHandoffError("delivery_stale", "cast candidate context is stale")
            _validate_cast(delivery.candidate)
            row.status, row.delivery_id, row.manifest_hash, row.cast, row.report_html, row.delivered_at = "ready", delivery.manifest.delivery_id, delivery.manifest_hash, delivery.candidate, delivery.report.decode("utf-8"), utc_now()
            head.status, head.updated_at = "candidate_ready", row.delivered_at
            return self._candidate(row)

    def accept_candidate(self, project_id: str, request: CastAcceptRequest) -> CastReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head, row = self._head(session, project_id), session.get(CastCandidateRow, request.job_id)
            if head.revision != request.expected_cast_revision:
                raise RevisionConflictError("cast", request.expected_cast_revision, head.revision)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.status != "ready" or row.cast is None:
                raise InvalidTransitionError("cast candidate is not ready for explicit acceptance")
            binding = CastBinding.model_validate(row.binding)
            if binding != request.binding or self._stale(session, project_id, binding):
                raise CreativeHandoffError("delivery_stale", "cast candidate context changed before acceptance")
            cast = request.cast or row.cast
            _validate_cast(cast)
            ids = _cast_ids(row.cast)
            if _cast_ids(cast) != ids:
                raise ValueError("accepted cast cannot change frozen character IDs")
            _validate_mappings(ids, request.consumer_mappings)
            now = utc_now()
            head.revision += 1
            head.candidate_job_id, head.status, head.updated_at, row.status = None, "accepted", now, "accepted"
            self._save(session, project_id, head.revision, row.job_id, binding, cast, request.consumer_mappings, now)
        return self.get_state(project_id)

    def reopen(self, project_id: str, request: CastReopenRequest) -> CastReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._head(session, project_id)
            if head.revision != request.expected_cast_revision:
                raise RevisionConflictError("cast", request.expected_cast_revision, head.revision)
            if not head.revision:
                raise InvalidTransitionError("no accepted cast exists to reopen")
            if head.candidate_job_id and (row := session.get(CastCandidateRow, head.candidate_job_id)) and row.status in {"prepared", "ready"}:
                raise InvalidTransitionError("cancel the current cast specialist publication before reopening accepted cast")
            head.status, head.updated_at = "reopened", utc_now()
        return self.get_state(project_id)

    def save_reopened(self, project_id: str, request: CastSaveRequest) -> CastReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._head(session, project_id)
            if head.revision != request.expected_cast_revision:
                raise RevisionConflictError("cast", request.expected_cast_revision, head.revision)
            if head.status != "reopened":
                raise InvalidTransitionError("reopen the accepted cast before saving author edits")
            previous = session.scalar(select(CastRevisionRow).where(CastRevisionRow.project_id == project_id, CastRevisionRow.revision == head.revision))
            if previous is None:
                raise NotFoundError("accepted cast revision is missing")
            binding = CastBinding.model_validate(previous.binding)
            if binding != request.binding or self._stale(session, project_id, binding):
                raise CreativeHandoffError("delivery_stale", "accepted cast context changed before saving edits")
            _validate_cast(request.cast)
            ids = _cast_ids(previous.cast)
            if _cast_ids(request.cast) != ids:
                raise ValueError("reopened cast cannot change stable character IDs")
            _validate_mappings(ids, request.consumer_mappings)
            now = utc_now()
            head.revision, head.status, head.updated_at = head.revision + 1, "accepted", now
            self._save(session, project_id, head.revision, previous.candidate_job_id, binding, request.cast, request.consumer_mappings, now)
        return self.get_state(project_id)

    def cancel_candidate(self, project_id: str, job_id: str) -> CastReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head, row = self._head(session, project_id), session.get(CastCandidateRow, job_id)
            if row is None or row.project_id != project_id:
                raise NotFoundError("project cast candidate is unavailable")
            if row.status == "accepted":
                raise InvalidTransitionError("accepted cast candidate cannot be cancelled")
            if row.status != "cancelled":
                row.status = "cancelled"
            if head.candidate_job_id == job_id:
                head.candidate_job_id, head.status, head.updated_at = None, "accepted" if head.revision else "missing", utc_now()
        return self.get_state(project_id)

    def candidate_report(self, project_id: str, job_id: str) -> str:
        with self._access.leases.read() as session:
            row = session.get(CastCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status not in {"ready", "accepted"} or row.report_html is None:
                raise NotFoundError("ready cast report is unavailable")
            return row.report_html

    def candidate_request(self, project_id: str, job_id: str) -> CreativeHandoffRequest:
        with self._access.leases.read() as session:
            row = session.get(CastCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status == "cancelled":
                raise NotFoundError("project cast candidate is unavailable")
            return CreativeHandoffRequest.model_validate(row.request)

    def consumer_identity_for(self, project_id: str, cast_character_id: str) -> str:
        state = self.get_state(project_id)
        if state.accepted_cast is None:
            raise NotFoundError("accepted cast is unavailable")
        for mapping in state.accepted_cast.consumer_mappings:
            if mapping.cast_character_id == cast_character_id:
                return mapping.consumer_character_id
        raise NotFoundError("cast character has no consumer identity mapping")

    @staticmethod
    def _save(session: Any, project_id: str, revision: int, candidate_job_id: str, binding: CastBinding, cast: dict[str, Any], mappings: list[CastConsumerMapping], accepted_at: Any) -> None:
        session.add(CastRevisionRow(id=new_id(), project_id=project_id, revision=revision, candidate_job_id=candidate_job_id, content_hash=sha256(canonical_json(cast)).hexdigest(), binding=binding.model_dump(mode="json", by_alias=True), cast=cast, consumer_mappings=[item.model_dump(mode="json", by_alias=True) for item in mappings], accepted_at=accepted_at))


def _cast_ids(cast: dict[str, Any]) -> list[str]:
    characters = cast.get("characters")
    if not isinstance(characters, list) or not characters:
        raise ValueError("upstream cast must contain characters")
    ids = [item.get("id") for item in characters if isinstance(item, dict)]
    if len(ids) != len(characters) or any(not isinstance(item, str) or not item.strip() for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("each upstream cast character needs a unique stable id")
    return ids


def _validate_cast(cast: dict[str, Any]) -> None:
    if contains_secret_setting(cast) or contains_secret_value(cast):
        raise ValueError("cast must not contain credentials")
    if not isinstance(cast.get("source"), str) or not isinstance(cast.get("summary"), str):
        raise ValueError("upstream cast must retain source and summary")
    _cast_ids(cast)


def _validate_mappings(ids: list[str], mappings: list[CastConsumerMapping]) -> None:
    cast_ids = [item.cast_character_id for item in mappings]
    consumer_ids = [item.consumer_character_id for item in mappings]
    if set(cast_ids) != set(ids) or len(cast_ids) != len(ids) or len(set(cast_ids)) != len(cast_ids):
        raise ValueError("every accepted cast character needs exactly one explicit consumer mapping")
    if len(set(consumer_ids)) != len(consumer_ids):
        raise ValueError("consumer identity mappings must be one-to-one")
