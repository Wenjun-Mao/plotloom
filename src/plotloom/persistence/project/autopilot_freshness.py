"""One launch admission shared by human preview and transactional start."""
from sqlalchemy import select
from ...exceptions import InvalidTransitionError
from ..schema import Base, PROJECT_TEXT_PIPELINE_TABLE_NAMES

INITIAL_TABLES = {"v2_projects", "v2_project_operational_states", "v2_stage_heads", "v2_source_outline_heads",
    "v2_cast_heads", "v2_art_heads", "v2_script_heads", "v2_source_outline_section_map_heads",
    "v2_storyboard_review_heads", "v2_production_bridge_heads"}


def assert_fresh(session, project_id):
    for name in PROJECT_TEXT_PIPELINE_TABLE_NAMES - INITIAL_TABLES:
        if session.execute(select(Base.metadata.tables[name]).limit(1)).first() is not None:
            raise InvalidTransitionError("autopilot starts only on a fresh saved Brief-only project")
    heads = Base.metadata.tables["v2_stage_heads"]
    if session.execute(select(heads).where(heads.c.project_id == project_id, heads.c.revision != 0)).first():
        raise InvalidTransitionError("autopilot cannot replace existing canonical work")
