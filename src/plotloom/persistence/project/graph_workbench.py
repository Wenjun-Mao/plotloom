"""One acknowledged graph draft with read-only previews and CAS transactions."""
from sqlalchemy import select
from pydantic import Field

from ...domain import AuthoringDraft, ProjectBrief, StageName, utc_now, new_id
from ...domain_base import CamelModel
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ...graph_authoring_drafts import GraphAuthoringDraft
from ...graph_command_execution import execute_graph_command
from ...graph_commands import GraphCommandApplyRequest, GraphCommandPreview, GraphCommandRequest
from ...graph_draft_creation import create_graph_draft
from ...source_outline_contracts import SectionMap
from ...source_structures import planned_structure
from ..codec import stable_hash
from ..schema import (
    AuthoringDraftRow, SourceOutlineGraphAdmissionRow, SourceOutlineSectionMapHeadRow,
    SourceOutlineSectionMapRevisionRow,
)
from .drafts import ProjectDraftPersistence
from .graph_draft_context import assert_graph_draft_context, assert_graph_draft_seed, graph_draft_binding


class GraphWorkbenchState(CamelModel):
    binding_hash: str
    base_canonical_revision: int
    draft: AuthoringDraft | None
    initial_payload: GraphAuthoringDraft | None
    read_only_reason: str | None


class GraphDraftRebaseRequest(CamelModel):
    expected_draft_revision: int = Field(ge=0)
    expected_binding_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload: GraphAuthoringDraft | None


class ProjectGraphWorkbenchPersistence:
    def __init__(self, access):
        self._access = access

    @staticmethod
    def _draft_row(session, project_id):
        return session.scalar(select(AuthoringDraftRow).where(
            AuthoringDraftRow.project_id == project_id,
            AuthoringDraftRow.editor_scope == "story_graph", AuthoringDraftRow.entity_id == "root",
        ))

    def _read_only_reason(self, session, project_id):
        graph = self._access.rows.stage(session, project_id, StageName.STORY_GRAPH)
        admission = session.get(SourceOutlineGraphAdmissionRow, project_id)
        if graph.revision and (admission is None or admission.graph_revision != graph.revision):
            return "当前路线没有来源结构绑定；可阅读与播放，不能通过来源工作台覆盖。请从新项目的来源与大纲开始。"
        return None

    def get_state(self, project_id) -> GraphWorkbenchState:
        with self._access.leases.read() as session:
            project = self._access.rows.project(session, project_id)
            binding = graph_draft_binding(session, self._access, project_id)
            row = self._draft_row(session, project_id)
            reason = self._read_only_reason(session, project_id)
            initial = None
            if row is None and reason is None:
                head = session.get(SourceOutlineSectionMapHeadRow, project_id)
                mapping = None
                if head and head.revision:
                    accepted = session.scalar(select(SourceOutlineSectionMapRevisionRow).where(
                        SourceOutlineSectionMapRevisionRow.project_id == project_id,
                        SourceOutlineSectionMapRevisionRow.revision == head.revision,
                    ))
                    if accepted:
                        mapping = SectionMap.model_validate(accepted.mapping)
                seed = mapping.seed_topology if mapping else planned_structure(project_id, ProjectBrief.model_validate(project.brief))
                initial = create_graph_draft(binding_hash=binding, seed=seed,
                    mapping=mapping.model_dump(mode="json", by_alias=True) if mapping else None)
            return GraphWorkbenchState(binding_hash=binding,
                base_canonical_revision=self._access.rows.stage(session, project_id, StageName.STORY_GRAPH).revision,
                draft=ProjectDraftPersistence._authoring_draft(row) if row else None,
                initial_payload=initial, read_only_reason=reason)

    def _preview(self, session, project_id, request):
        project = self._access.rows.project(session, project_id)
        self._access.guards.active(project)
        reason = self._read_only_reason(session, project_id)
        if reason:
            raise InvalidTransitionError(reason)
        row = self._draft_row(session, project_id)
        if row is None or row.draft_revision != request.expected_draft_revision:
            raise RevisionConflictError("graph command draft", request.expected_draft_revision, row.draft_revision if row else 0)
        draft = GraphAuthoringDraft.model_validate(row.payload)
        assert_graph_draft_context(session, self._access, project_id, draft)
        result, impact = execute_graph_command(draft, request.command, ProjectBrief.model_validate(project.brief))
        data = {"draftRevision": row.draft_revision, "bindingHash": draft.binding_hash,
                "command": request.command.model_dump(mode="json", by_alias=True),
                "result": result.model_dump(mode="json", by_alias=True), "impact": impact.model_dump(mode="json", by_alias=True)}
        return row, GraphCommandPreview.model_validate(data | {"previewHash": stable_hash(data)})

    def preview(self, project_id, request: GraphCommandRequest) -> GraphCommandPreview:
        with self._access.leases.read() as session:
            return self._preview(session, project_id, request)[1]

    def apply(self, project_id, request: GraphCommandApplyRequest) -> AuthoringDraft:
        with self._access.leases.lifecycle_write() as session:
            row, preview = self._preview(session, project_id, request)
            if preview.preview_hash != request.preview_hash:
                raise RevisionConflictError("graph command preview", request.expected_draft_revision, row.draft_revision)
            row.payload = preview.result.model_dump(mode="json", by_alias=True)
            row.draft_revision += 1
            row.updated_at = utc_now()
            session.flush()
            return ProjectDraftPersistence._authoring_draft(row)

    def rebase(self, project_id, request: GraphDraftRebaseRequest) -> AuthoringDraft:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            row = self._draft_row(session, project_id)
            if (row.draft_revision if row else 0) != request.expected_draft_revision:
                raise RevisionConflictError("graph recovery draft", request.expected_draft_revision, row.draft_revision if row else 0)
            binding = graph_draft_binding(session, self._access, project_id)
            if binding != request.expected_binding_hash:
                raise RevisionConflictError("graph recovery context", 0, 1)
            if row is None:
                if request.payload is None:
                    raise InvalidTransitionError("没有可恢复的图草稿内容。")
                assert_graph_draft_seed(session, self._access, project_id, request.payload, None)
                head = session.get(SourceOutlineSectionMapHeadRow, project_id)
                accepted = session.scalar(select(SourceOutlineSectionMapRevisionRow).where(
                    SourceOutlineSectionMapRevisionRow.project_id == project_id,
                    SourceOutlineSectionMapRevisionRow.revision == head.revision,
                )) if head and head.revision else None
                mapping = SectionMap.model_validate(accepted.mapping) if accepted else None
                if mapping and mapping.seed_topology != request.payload.mapping.seed_topology:
                    mapping = None
                # Seed authentication does not authenticate author edits. Recovery
                # without a prior receipt must use the same trusted baseline as
                # first-save admission, never compare untrusted content to itself.
                draft = create_graph_draft(binding_hash=binding, seed=request.payload.mapping.seed_topology,
                    mapping=mapping.model_dump(mode="json", by_alias=True) if mapping else None)
                row = AuthoringDraftRow(id=new_id(), project_id=project_id, editor_scope="story_graph", entity_id="root",
                    base_canonical_revision=self._access.rows.stage(session, project_id, StageName.STORY_GRAPH).revision,
                    draft_revision=0, payload=draft.model_dump(mode="json", by_alias=True), updated_at=utc_now())
                session.add(row)
            else:
                draft = GraphAuthoringDraft.model_validate(row.payload)
            if request.payload is not None:
                if request.payload.mapping.seed_topology != draft.mapping.seed_topology:
                    raise InvalidTransitionError("恢复内容必须保留此图草稿已认证的原始种子。")
                from ...graph_edit_safety import assert_edit_safe
                assert_edit_safe(draft, request.payload, ProjectBrief.model_validate(project.brief))
                draft = request.payload.model_copy(deep=True)
            # An explicit recovery retains authenticated original seed/content,
            # but receives no old acceptance authority on the changed base.
            draft.binding_hash = binding
            draft.mapping.topology_origin = "author"
            row.payload = draft.model_dump(mode="json", by_alias=True)
            row.base_canonical_revision = self._access.rows.stage(session, project_id, StageName.STORY_GRAPH).revision
            row.draft_revision += 1
            row.updated_at = utc_now()
            session.flush()
            return ProjectDraftPersistence._authoring_draft(row)
