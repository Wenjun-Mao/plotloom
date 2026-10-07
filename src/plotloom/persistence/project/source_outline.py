"""CAS-bound persistence for the F1A source-to-outline review handoff."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from sqlalchemy import select

from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery, canonical_json
from ...domain import StageName, StageStatus, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...source_outline_contracts import (
    AcceptedOutlineRevision, AcceptedSectionMapRevision,
    SectionMapGraphInstallRequest, SourceMapGraphAdmission,
    OutlineAcceptRequest,
    OutlineCandidate,
    OutlineReopenRequest,
    SectionMapSaveRequest,
    SourceMaterial,
    SourceOutlineReviewState,
    SourceRevision,
    compile_section_map_graph,
    validate_section_map_graph,
)
from ..schema import (
    AuthoringDraftRow,
    SourceOutlineCandidateRow,
    SourceOutlineGraphAdmissionRow,
    SourceOutlineHeadRow,
    SourceOutlineRevisionRow,
    SourceOutlineSectionMapHeadRow,
    SourceOutlineSectionMapRevisionRow,
    SourceOutlineSourceRevisionRow,
)
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .source_outline_mutations import SourceOutlineMutations


class ProjectSourceOutlinePersistence:
    """Own one accepted source and outline without translating upstream JSON."""

    def __init__(self, access: ProjectPersistenceAccess, canonical: ProjectCanonicalPersistence) -> None:
        self._access = access
        self._canonical = canonical
        self._mutations = SourceOutlineMutations(access, self)
        from .source_graph_admission import SourceGraphAdmission
        self._graph_writer = SourceGraphAdmission(access, canonical, self)

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
    def _graph_admission(row: SourceOutlineGraphAdmissionRow) -> SourceMapGraphAdmission:
        return SourceMapGraphAdmission(
            source_revision=row.source_revision,
            source_content_hash=row.source_content_hash,
            outline_revision=row.outline_revision,
            outline_content_hash=row.outline_content_hash,
            section_map_revision=row.section_map_revision,
            section_map_content_hash=row.section_map_content_hash,
            graph_revision=row.graph_revision,
            graph_content_hash=row.graph_content_hash,
            status=row.status,
            stale_reasons=row.stale_reasons,
            installed_at=row.installed_at,
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
            admission = session.get(SourceOutlineGraphAdmissionRow, project_id)
            return SourceOutlineReviewState(
                source=source,
                candidate=self._candidate(candidate) if candidate is not None else None,
                accepted_outline=outline,
                outline_status=head.outline_status,
                accepted_section_map=section_map,
                section_map_status=section_map_head.status if section_map_head else "missing",
                section_map_stale_reasons=section_map_head.stale_reasons if section_map_head else [],
                graph_admission=self._visible_graph_admission(session, project_id, admission),
            )

    def save_source(self, project_id: str, *, expected_source_revision: int, material: SourceMaterial) -> SourceOutlineReviewState:
        return self._mutations.save_source(project_id, expected_source_revision=expected_source_revision, material=material)

    def prepare_candidate(self, project_id: str, request: CreativeHandoffRequest, *, execution_pin: dict[str, str]) -> OutlineCandidate:
        return self._mutations.prepare_candidate(project_id, request, execution_pin=execution_pin)

    def admit_delivery(self, project_id: str, delivery: ValidatedCreativeDelivery) -> OutlineCandidate:
        return self._mutations.admit_delivery(project_id, delivery)

    def accept_candidate(self, project_id: str, request: OutlineAcceptRequest) -> SourceOutlineReviewState:
        return self._mutations.accept_candidate(project_id, request)

    def save_section_map(self, project_id: str, request: SectionMapSaveRequest) -> SourceOutlineReviewState:
        return self._graph_writer.save_section_map(project_id, request)

    def install_section_map_graph(self, project_id: str, request: SectionMapGraphInstallRequest) -> SourceOutlineReviewState:
        return self._graph_writer.install_section_map_graph(project_id, request)

    def reopen_outline(self, project_id: str, request: OutlineReopenRequest) -> SourceOutlineReviewState:
        return self._mutations.reopen_outline(project_id, request)

    def cancel_candidate(self, project_id: str, job_id: str) -> SourceOutlineReviewState:
        return self._mutations.cancel_candidate(project_id, job_id)

    def candidate_report(self, project_id: str, job_id: str) -> str:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            candidate = session.get(SourceOutlineCandidateRow, job_id)
            if candidate is None or candidate.project_id != project_id or candidate.request.get("stage") != "outline" or candidate.status not in {"ready", "accepted"} or candidate.report_html is None:
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
            graph_admission=self._visible_graph_admission(
                session, project_id, session.get(SourceOutlineGraphAdmissionRow, project_id)
            ),
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

    def _visible_graph_admission(
        self, session: Any, project_id: str, row: SourceOutlineGraphAdmissionRow | None
    ) -> SourceMapGraphAdmission | None:
        if row is None:
            return None
        admission = self._graph_admission(row)
        graph = self._access.rows.stage(session, project_id, StageName.STORY_GRAPH)
        if graph.revision != row.graph_revision or graph.content_hash != row.graph_content_hash:
            return admission.model_copy(update={
                "status": "stale",
                "stale_reasons": ["canonical graph identity changed outside this source-map admission"],
            })
        if graph.status != StageStatus.READY.value:
            return admission.model_copy(update={
                "status": "stale",
                "stale_reasons": [f"canonical graph is {graph.status}"],
            })
        return admission

    @staticmethod
    def _assert_install_bindings(
        request: SectionMapGraphInstallRequest,
        source: SourceOutlineSourceRevisionRow,
        outline: SourceOutlineRevisionRow,
        mapping: AcceptedSectionMapRevision,
    ) -> None:
        bindings = (
            ("source", request.expected_source_revision, source.revision),
            ("outline", request.expected_outline_revision, outline.revision),
            ("section map", request.expected_section_map_revision, mapping.revision),
        )
        for label, expected, actual in bindings:
            if expected != actual:
                raise RevisionConflictError(f"source-map graph {label}", expected, actual)
        hashes = (
            ("source", request.expected_source_content_hash, source.content_hash),
            ("outline", request.expected_outline_content_hash, outline.content_hash),
            ("section map", request.expected_section_map_content_hash, mapping.content_hash),
        )
        if any(expected != actual for _, expected, actual in hashes):
            raise RevisionConflictError("source-map graph input content", 0, 1)

    def _mark_source_map_graph_stale(self, session: Any, project_id: str, reason: str) -> None:
        admission = session.get(SourceOutlineGraphAdmissionRow, project_id)
        if admission is None:
            return
        admission.status = "stale"
        admission.stale_reasons = [reason]
        graph = self._access.rows.stage(session, project_id, StageName.STORY_GRAPH)
        if graph.revision != admission.graph_revision:
            return
        graph.status = StageStatus.STALE.value
        graph.stale_reasons = [reason]
        graph.updated_at = utc_now()
        beats = self._access.rows.stage(session, project_id, StageName.SCENE_BEATS)
        if beats.status != StageStatus.MISSING.value and beats.input_revisions.get(StageName.STORY_GRAPH.value) == graph.revision:
            beats.status = StageStatus.STALE.value
            beats.stale_reasons = [reason]
            beats.updated_at = graph.updated_at
            storyboard = self._access.rows.stage(session, project_id, StageName.STORYBOARD)
            if storyboard.status != StageStatus.MISSING.value and storyboard.input_revisions.get(StageName.SCENE_BEATS.value) == beats.revision:
                storyboard.status = StageStatus.STALE.value
                storyboard.stale_reasons = [reason]
                storyboard.updated_at = graph.updated_at
