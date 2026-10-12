"""Current material authority, distinct from append-only review/transport history."""
from datetime import datetime
from sqlalchemy import select

from ..codec import stable_hash
from ..schema import Base

# Current heads bind immutable revisions; content hashes protect their closure.
# Human rows participate so any later review change withdraws the handoff.
# Transport receipt/job state is not creative authority.
MATERIAL_TABLES = (
    "v2_projects", "v2_stage_heads", "v2_authoring_drafts", "v2_gate_results",
    "v2_source_outline_heads", "v2_source_outline_section_map_heads",
    "v2_source_outline_graph_admissions", "v2_source_graph_identities",
    "v2_cast_heads", "v2_art_heads", "v2_script_heads", "v2_storyboard_review_heads",
    "v2_production_bridge_heads", "v2_production_bridge_admissions",
    "v2_managed_assets", "v2_character_reference_states", "v2_character_reference_decisions",
    "v2_art_reference_decision_states", "v2_art_reference_decisions", "v2_shot_presentations",
    "v2_visual_selection_states", "v2_visual_intents", "v2_reviewed_shot_bindings",
    "v2_approval_decisions", "v2_same_person_review_states", "v2_same_person_reviews",
)


def material_closure(session, project_id, *, tables=MATERIAL_TABLES, include_cancellations=True):
    session.flush()
    payload = {}
    for name in tables:
        table = Base.metadata.tables[name]
        rows = session.execute(select(table).where(table.c.project_id == project_id) if "project_id" in table.c
                               else select(table).where(table.c.id == project_id)).mappings()
        values = [{key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()} for row in rows]
        payload[name] = sorted(values, key=stable_hash)
    if include_cancellations:
        # Delivery/receipt progress is transport evidence, but a cancellation
        # explicitly withdraws the native owner's material applicability.
        payload["imageCancellations"] = {}
        for name in ("v2_image_jobs", "v2_character_reference_proposals", "v2_art_reference_proposals"):
            table = Base.metadata.tables[name]
            payload["imageCancellations"][name] = sorted(session.scalars(select(table.c.id).where(
                table.c.project_id == project_id, table.c.state == "cancelled")))
    return stable_hash(payload)


def production_closure(session, project_id):
    """Text/canonical installation changes withdraw machine image applicability."""
    return material_closure(session, project_id, tables=tuple(name for name in MATERIAL_TABLES
        if name in {"v2_projects", "v2_stage_heads", "v2_gate_results", "v2_source_outline_heads",
            "v2_source_outline_section_map_heads", "v2_source_outline_graph_admissions", "v2_source_graph_identities",
            "v2_cast_heads", "v2_art_heads", "v2_script_heads", "v2_storyboard_review_heads",
            "v2_production_bridge_heads", "v2_production_bridge_admissions"}), include_cancellations=False)
