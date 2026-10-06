"""Source-bound confirmation and canonical admission of one exact graph draft."""
from hashlib import sha256

from sqlalchemy import select

from ...creative_handoff_exchange import canonical_json
from ...domain import StageName, StageStatus, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...graph_authoring_drafts import GraphAuthoringDraft
from ...source_outline_contracts import (
    SectionMapSaveRequest, SectionMapGraphInstallRequest, SourceOutlineReviewState,
    compile_section_map_graph, validate_section_map_graph,
)
from ..schema import (
    AuthoringDraftRow, SourceOutlineRevisionRow, SourceOutlineSourceRevisionRow,
    SourceOutlineSectionMapRevisionRow, SourceOutlineGraphAdmissionRow,
)
from .graph_draft_context import assert_graph_draft_context, graph_draft_binding


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
            prior_mapping = self._source._section_map_for_head(session, project_id, section_map_head)
            if prior_mapping is not None:
                from ..schema import ProductionBridgeAdmissionRow
                realization_changed = [(item.section_id, item.footage_mode) for item in prior_mapping.mapping.sections] != [(item.section_id, item.footage_mode) for item in request.mapping.sections]
                if (prior_mapping.mapping.topology != request.mapping.topology or realization_changed) and session.get(ProductionBridgeAdmissionRow, project_id) is not None:
                    raise InvalidTransitionError("此项目已安装投产，当前流程不能替换其剧情结构。已保存内容与媒体仍保留。")
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
            if graph_head.revision and (admission is None or admission.graph_revision != graph_head.revision):
                raise InvalidTransitionError("the current canonical graph is not source-map-owned and cannot be overwritten")
            graph = compile_section_map_graph(mapping.mapping)
            from ...domain import ProjectBrief
            bible_head = self._access.rows.stage(session, project_id, StageName.STORY_BIBLE)
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE) if bible_head.status == StageStatus.READY.value else None
            validate_section_map_graph(graph, ProjectBrief.model_validate(project.brief), bible)
            from ..schema import ProductionBridgeAdmissionRow
            if session.get(ProductionBridgeAdmissionRow, project_id) is not None:
                raise InvalidTransitionError("已安装的投产内容受到保护；当前工作流不支持替换其剧情结构。")
            now = utc_now()
            installed = self._canonical.install_source_map_graph_in_session(
                session, project, graph, expected_revision=request.expected_graph_revision, now=now
            )
            session.delete(graph_draft)
            session.merge(SourceOutlineGraphAdmissionRow(
                project_id=project_id,
                source_revision=source.revision, source_content_hash=source.content_hash,
                outline_revision=outline.revision, outline_content_hash=outline.content_hash,
                section_map_revision=mapping.revision, section_map_content_hash=mapping.content_hash,
                graph_revision=installed.revision, graph_content_hash=installed.content_hash or "",
                status="current", stale_reasons=[], installed_at=now,
            ))
            return self._source._state_in_session(session, project_id, outline_head)
