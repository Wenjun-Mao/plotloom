"""Exact current context for the shared graph draft; no accepted authority copying."""
from sqlalchemy import select

from plotloom.brief_contracts import ProjectBrief
from plotloom.stage_contracts import StageName

from ...exceptions import InvalidTransitionError, RevisionConflictError
from ...graph_authoring_drafts import GraphAuthoringDraft
from ...source_outline_contracts import (
    SectionMap,
    SourceMaterial,
    validate_section_map_graph,
)
from ...source_structures import compile_structure, planned_structure
from ..codec import stable_hash
from ..schema import (
    SourceOutlineHeadRow,
    SourceOutlineRevisionRow,
    SourceOutlineSectionMapHeadRow,
    SourceOutlineSectionMapRevisionRow,
    SourceOutlineSourceRevisionRow,
)


def graph_draft_binding(session, access, project_id: str) -> str:
    project = access.rows.project(session, project_id)
    outline = session.get(SourceOutlineHeadRow, project_id)
    mapping = session.get(SourceOutlineSectionMapHeadRow, project_id)
    stages = [access.rows.stage(session, project_id, stage) for stage in
              (StageName.STORY_GRAPH, StageName.STORY_BIBLE)]
    source = session.scalar(select(SourceOutlineSourceRevisionRow).where(
        SourceOutlineSourceRevisionRow.project_id == project_id,
        SourceOutlineSourceRevisionRow.revision == outline.source_revision,
    )) if outline and outline.source_revision else None
    accepted_outline = session.scalar(select(SourceOutlineRevisionRow).where(
        SourceOutlineRevisionRow.project_id == project_id,
        SourceOutlineRevisionRow.revision == outline.outline_revision,
    )) if outline and outline.outline_revision else None
    accepted_map = session.scalar(select(SourceOutlineSectionMapRevisionRow).where(
        SourceOutlineSectionMapRevisionRow.project_id == project_id,
        SourceOutlineSectionMapRevisionRow.revision == mapping.revision,
    )) if mapping and mapping.revision else None
    return stable_hash({
        "brief": {"revision": project.revision, "content": project.brief},
        "source": {"revision": outline.source_revision, "hash": source.content_hash if source else None} if outline else None,
        "outline": {"revision": outline.outline_revision, "status": outline.outline_status,
                    "hash": accepted_outline.content_hash if accepted_outline else None} if outline else None,
        "map": {"revision": mapping.revision, "status": mapping.status,
                "hash": accepted_map.content_hash if accepted_map else None} if mapping else None,
        "stages": [{"stage": row.stage, "revision": row.revision,
                    "hash": row.content_hash, "status": row.status} for row in stages],
    })


def assert_graph_draft_context(session, access, project_id: str, draft: GraphAuthoringDraft) -> None:
    if draft.binding_hash != graph_draft_binding(session, access, project_id):
        raise RevisionConflictError("graph draft source/outline/brief context", 0, 1)


def assert_graph_draft_seed(session, access, project_id: str, draft: GraphAuthoringDraft, prior: GraphAuthoringDraft | None) -> None:
    if draft.mapping.seed_topology is None:
        authored = source_author_graph_mapping(session, access, project_id)
        if authored is None or draft.mapping.author_source_hash != authored["authorSourceHash"]:
            raise InvalidTransitionError("无规划种子的图草稿必须绑定当前已接受的作者结构来源。")
    if prior is not None:
        if (draft.mapping.seed_topology != prior.mapping.seed_topology
                or draft.mapping.author_source_hash != prior.mapping.author_source_hash):
            raise InvalidTransitionError("图草稿必须保留原始可信规划种子。")
        return
    if draft.mapping.seed_topology is None:
        return
    project = access.rows.project(session, project_id)
    seeds = [planned_structure(project_id, ProjectBrief.require_confirmed(project.brief))]
    head = session.get(SourceOutlineSectionMapHeadRow, project_id)
    if head and head.revision:
        row = session.scalar(select(SourceOutlineSectionMapRevisionRow).where(
            SourceOutlineSectionMapRevisionRow.project_id == project_id,
            SourceOutlineSectionMapRevisionRow.revision == head.revision,
        ))
        if row is not None:
            seeds.append(SectionMap.model_validate(row.mapping).seed_topology)
    if draft.mapping.seed_topology not in seeds:
        raise InvalidTransitionError("图草稿的种子不属于当前规划或已接受来源结构。")


def source_author_graph_mapping(session, access, project_id):
    """Only an exact accepted typed source can initialize a seedless draft."""
    from hashlib import sha256

    from ...creative_handoff_identity import canonical_json
    head = session.get(SourceOutlineHeadRow, project_id)
    row = session.scalar(select(SourceOutlineSourceRevisionRow).where(
        SourceOutlineSourceRevisionRow.project_id == project_id,
        SourceOutlineSourceRevisionRow.revision == head.source_revision,
    )) if head and head.source_revision else None
    if row is None:
        return None
    material = SourceMaterial.model_validate(row.material)
    if material.authored_structure is None:
        return None
    if row.content_hash != sha256(canonical_json(material.model_dump(mode="json", by_alias=True))).hexdigest():
        raise InvalidTransitionError("作者结构的已接受来源哈希不一致。")
    project = access.rows.project(session, project_id)
    material.authored_structure.validate_links()
    validate_section_map_graph(compile_structure(material.authored_structure), ProjectBrief.require_confirmed(project.brief))
    return {**material.authored_structure.model_dump(mode="json", by_alias=True),
        "seedTopology": None, "authorSourceHash": row.content_hash, "topologyOrigin": "author"}
