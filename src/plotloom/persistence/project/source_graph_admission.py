"""Source-bound confirmation and canonical admission of one exact graph draft."""
from hashlib import sha256

from sqlalchemy import select

from ...creative_handoff_exchange import canonical_json
from ...domain import StageName, StageStatus, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...graph_authoring_drafts import GraphAuthoringDraft
from ...source_outline_contracts import (
    SectionMapGraphInstallRequest,
    SectionMapSaveRequest,
    SourceOutlineReviewState,
    compile_section_map_graph,
    validate_section_map_graph,
)
from ..schema import (
    AuthoringDraftRow,
    SourceOutlineGraphAdmissionRow,
    SourceOutlineRevisionRow,
    SourceOutlineSectionMapRevisionRow,
    SourceOutlineSourceRevisionRow,
)
from ..schema.project_source_outline import SourceGraphIdentityRow
from .graph_draft_context import assert_graph_draft_context, graph_draft_binding
from .production_rebuild_quiescence import assert_production_quiescent


class SourceGraphAdmission:
    def __init__(self, access, canonical, source):
        self._access, self._canonical, self._source = access, canonical, source

    def _exact_draft(self, session, project_id, expected_revision):
        row = session.scalar(select(AuthoringDraftRow).where(
            AuthoringDraftRow.project_id == project_id,
            AuthoringDraftRow.editor_scope == "story_graph", AuthoringDraftRow.entity_id == "root",
        ))
        if row is None or row.draft_revision != expected_revision:
            raise RevisionConflictError("story graph authoring draft", expected_revision, row.draft_revision if row else 0)
        draft = GraphAuthoringDraft.model_validate(row.payload)
        assert_graph_draft_context(session, self._access, project_id, draft)
        return row, draft

    def save_section_map(self, project_id: str, request: SectionMapSaveRequest) -> SourceOutlineReviewState:
        """Accept one author-reviewed structure bound to the exact outline revision."""

        request.mapping.validate_links()
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            assert_production_quiescent(self._access, session, project_id)
            graph_draft, draft = self._exact_draft(session, project_id, request.expected_graph_draft_revision)
            if draft.admitted_mapping() != request.mapping:
                raise InvalidTransitionError("确认内容必须与已保存的当前图草稿完全一致。")
            outline_head = self._source._head(session, project_id, create=True)
            section_map_head = self._source._section_map_head(session, project_id, create=True)
            from ...domain import ProjectBrief
            graph = compile_section_map_graph(request.mapping)
            brief = ProjectBrief.model_validate(project.brief)
            bible_head = self._access.rows.stage(session, project_id, StageName.STORY_BIBLE)
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE) if bible_head.status == StageStatus.READY.value else None
            validate_section_map_graph(graph, brief, bible)
            if section_map_head.revision != request.expected_section_map_revision:
                raise RevisionConflictError("source-outline section map", request.expected_section_map_revision, section_map_head.revision)
            if outline_head.source_revision != request.expected_source_revision:
                raise RevisionConflictError("source-outline source", request.expected_source_revision, outline_head.source_revision)
            if outline_head.outline_revision != request.expected_outline_revision:
                raise RevisionConflictError("source-outline outline", request.expected_outline_revision, outline_head.outline_revision)
            if not outline_head.outline_revision:
                raise InvalidTransitionError("an accepted outline is required before saving a section map")
            if outline_head.outline_status != "accepted":
                raise InvalidTransitionError("a current accepted outline is required before saving a section map")
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
            self._source._mark_source_map_graph_stale(
                session, project_id, f"accepted section-map revision changed to r{section_map_head.revision + 1}"
            )
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
            draft.binding_hash = graph_draft_binding(session, self._access, project_id)
            graph_draft.payload = draft.model_dump(mode="json", by_alias=True)
            graph_draft.draft_revision += 1
            graph_draft.updated_at = now
            return self._source._state_in_session(session, project_id, outline_head)

    def install_section_map_graph(
        self, project_id: str, request: SectionMapGraphInstallRequest
    ) -> SourceOutlineReviewState:
        """Atomically compile the current map into the sole routing authority."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            assert_production_quiescent(self._access, session, project_id)
            outline_head = self._source._head(session, project_id, create=True)
            map_head = self._source._section_map_head(session, project_id, create=True)
            if map_head.status != "current" or not map_head.revision:
                raise InvalidTransitionError("a current accepted section map is required before graph installation")
            if outline_head.outline_status != "accepted":
                raise InvalidTransitionError("the accepted outline must be current before graph installation")
            source = session.scalar(select(SourceOutlineSourceRevisionRow).where(
                SourceOutlineSourceRevisionRow.project_id == project_id,
                SourceOutlineSourceRevisionRow.revision == outline_head.source_revision,
            ))
            outline = session.scalar(select(SourceOutlineRevisionRow).where(
                SourceOutlineRevisionRow.project_id == project_id,
                SourceOutlineRevisionRow.revision == outline_head.outline_revision,
            ))
            mapping = self._source._section_map_for_head(session, project_id, map_head)
            if source is None or outline is None or mapping is None:
                raise NotFoundError("current source, outline, or section map is missing")
            self._source._assert_install_bindings(request, source, outline, mapping)
            graph_head = self._access.rows.stage(session, project_id, StageName.STORY_GRAPH)
            if graph_head.revision != request.expected_graph_revision:
                raise RevisionConflictError("stage:story_graph", request.expected_graph_revision, graph_head.revision)
            graph_draft, draft = self._exact_draft(session, project_id, request.expected_graph_draft_revision)
            if graph_draft.base_canonical_revision != request.expected_graph_revision:
                raise RevisionConflictError("story graph draft base", request.expected_graph_revision, graph_draft.base_canonical_revision)
            if draft.admitted_mapping() != mapping.mapping:
                raise InvalidTransitionError("当前图草稿与已确认来源结构不同；请先确认当前草稿。")
            admission = session.get(SourceOutlineGraphAdmissionRow, project_id)
            identity = session.get(SourceGraphIdentityRow, graph_head.entity_revision_id) if graph_head.entity_revision_id else None
            if graph_head.revision and (admission is None or admission.graph_revision != graph_head.revision or identity is None or identity.project_id != project_id or identity.canonical_revision != graph_head.revision or identity.content_hash != graph_head.content_hash):
                raise InvalidTransitionError("the current canonical graph is not source-map-owned and cannot be overwritten")
            graph = compile_section_map_graph(mapping.mapping)
            from ...domain import ProjectBrief
            bible_head = self._access.rows.stage(session, project_id, StageName.STORY_BIBLE)
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE) if bible_head.status == StageStatus.READY.value else None
            validate_section_map_graph(graph, ProjectBrief.model_validate(project.brief), bible)
            now = utc_now()
            installed = self._canonical.install_source_map_graph_in_session(
                session, project, graph, expected_revision=request.expected_graph_revision, now=now
            )
            session.delete(graph_draft)
            receipt = SourceOutlineGraphAdmissionRow(
                project_id=project_id,
                source_revision=source.revision, source_content_hash=source.content_hash,
                outline_revision=outline.revision, outline_content_hash=outline.content_hash,
                section_map_revision=mapping.revision, section_map_content_hash=mapping.content_hash,
                graph_revision=installed.revision, graph_content_hash=installed.content_hash or "",
                status="current", stale_reasons=[], installed_at=now,
            )
            self._record_identity(session, receipt, installed, installed.revision, now)
            session.merge(receipt)
            return self._source._state_in_session(session, project_id, outline_head)

    @staticmethod
    def _record_identity(session, admission, installed, authored_revision, now):
        binding = {name: getattr(admission, name) for name in (
            "source_revision", "source_content_hash", "outline_revision", "outline_content_hash",
            "section_map_revision", "section_map_content_hash",
        )}
        session.add(SourceGraphIdentityRow(
            entity_revision_id=installed.entity_revision_id, project_id=admission.project_id,
            canonical_revision=installed.revision, authored_revision=authored_revision,
            content_hash=installed.content_hash, source_binding=binding, admitted_at=now,
        ))

    def validate_graph_bible_in_session(self, session, project, bible):
        head = self._access.rows.stage(session, project.id, StageName.STORY_GRAPH)
        admission = session.get(SourceOutlineGraphAdmissionRow, project.id)
        identity = session.get(SourceGraphIdentityRow, head.entity_revision_id)
        if admission is None or identity is None or admission.status != "current" or admission.graph_revision != head.revision or identity.project_id != project.id or identity.canonical_revision != head.revision or identity.content_hash != head.content_hash:
            raise InvalidTransitionError("current graph requires exact source-owned identity")
        mapping = self._source._section_map_for_head(session, project.id, self._source._section_map_head(session, project.id, create=False))
        if mapping is None or mapping.revision != admission.section_map_revision or mapping.content_hash != admission.section_map_content_hash:
            raise InvalidTransitionError("current graph source mapping changed")
        graph = compile_section_map_graph(mapping.mapping)
        from ...domain import ProjectBrief
        from ..codec import stable_hash
        if stable_hash(graph.model_dump(mode="json", by_alias=False)) != head.content_hash:
            raise InvalidTransitionError("compiled source mapping differs from canonical graph")
        validate_section_map_graph(graph, ProjectBrief.model_validate(project.brief), bible)
        return graph, admission, identity

    def rebind_graph_bible_in_session(self, session, project, bible, *, now):
        graph, admission, identity = self.validate_graph_bible_in_session(session, project, bible)
        if not any(edge.entity_state_effects for edge in graph.edges):
            return
        head = self._access.rows.stage(session, project.id, StageName.STORY_GRAPH)
        installed = self._canonical.install_source_map_graph_in_session(
            session, project, graph, expected_revision=head.revision, now=now,
        )
        self._record_identity(session, admission, installed, identity.authored_revision, now)
        admission.graph_revision, admission.graph_content_hash = installed.revision, installed.content_hash
        admission.status, admission.stale_reasons, admission.installed_at = "current", [], now
