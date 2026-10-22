"""Current material authority, distinct from append-only review/transport history."""
import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from sqlalchemy import select

from ...exceptions import InvalidTransitionError
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


@dataclass(frozen=True)
class _EncodedRows:
    """Fresh, already hashed row bytes owned only by one closure construction."""

    data: bytes


def _json_text(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _material_bytes(payload):
    chunks = [b"{"]
    for index, name in enumerate(sorted(payload)):
        if index:
            chunks.append(b",")
        chunks.extend((_json_text(name), b":"))
        value = payload[name]
        chunks.append(value.data if isinstance(value, _EncodedRows) else _json_text(value))
    chunks.append(b"}")
    # json.dumps completes before UTF-8 encoding in the canonical hash contract.
    # Serialize every ordinary extra first, so a later JSON error still precedes
    # an earlier lone surrogate's encoding error. Row bytes already passed UTF-8
    # at their original sort-key boundary.
    try:
        return b"".join(chunk.encode("utf-8") if isinstance(chunk, str) else chunk for chunk in chunks)
    except UnicodeEncodeError:
        # Reproduce the canonical exception's complete input and offsets, too.
        text = "".join(chunk if isinstance(chunk, str) else chunk.decode("utf-8") for chunk in chunks)
        return text.encode("utf-8")


def _hash_material(payload):
    return sha256(_material_bytes(payload)).hexdigest()


def material_closure(session, project_id, *, tables=MATERIAL_TABLES, include_cancellations=True):
    from ...project_storage.proof_scope import sql_scalar
    def calculate():
        payload = _material_payload(session, project_id, tables)
        if include_cancellations:
            _add_material_extras(session, project_id, payload)
        return _hash_material(payload)
    return sql_scalar(session, "material-closure", (project_id, tuple(tables), include_cancellations), calculate)


def _receipt_material_closures(session, project_id, *, expected_protected=None):
    """Build each segment afresh; refuse protected edits before allowed extras."""
    session.flush()
    payload = _material_payload(session, project_id, tuple(name for name in MATERIAL_TABLES if name != "v2_managed_assets"))
    protected = _hash_material(payload)
    if expected_protected is not None and protected != expected_protected:
        raise InvalidTransitionError("receipt reconciliation cannot change creative or human authority")
    payload.update(_material_payload(session, project_id, ("v2_managed_assets",)))
    _add_material_extras(session, project_id, payload)
    return protected, _hash_material(payload)


def _material_payload(session, project_id, tables):
    payload = {}
    for name in tables:
        table = Base.metadata.tables[name]
        rows = session.execute(select(table).where(table.c.project_id == project_id) if "project_id" in table.c
                               else select(table).where(table.c.id == project_id))
        keys = tuple(rows.keys())
        values = [{key: value.isoformat() if isinstance(value, datetime) else value
                   for key, value in zip(keys, row, strict=True)} for row in rows]
        encoded = []
        for value in values:
            data = _json_text(value).encode("utf-8")
            encoded.append((sha256(data).hexdigest(), data))
        # Sort by digest alone: equal digests retain the database's row order.
        encoded.sort(key=lambda item: item[0])
        payload[name] = _EncodedRows(b"[" + b",".join(data for _, data in encoded) + b"]")
    return payload


def _add_material_extras(session, project_id, payload):
    checkpoint_table = Base.metadata.tables["v2_autopilot_checkpoints"]
    inherited_table = Base.metadata.tables["v2_autopilot_inheritance"]
    inherited = select(inherited_table.c.id).where(inherited_table.c.project_id == project_id,
        inherited_table.c.run_id == checkpoint_table.c.run_id,
        inherited_table.c.operation_key == checkpoint_table.c.operation_key).exists()
    preparations = session.execute(select(checkpoint_table.c.id, checkpoint_table.c.evidence).where(checkpoint_table.c.project_id == project_id,
        checkpoint_table.c.evidence["geometryPreparation"].as_string().is_not(None), ~inherited)).all()
    lineage = [{"checkpointId": identifier, "geometryPreparation": evidence["geometryPreparation"]}
        for identifier, evidence in preparations if evidence.get("geometryPreparation") is not None]
    if lineage:
        payload["geometryPreparations"] = sorted(lineage, key=stable_hash)
    # Delivery/receipt progress is transport evidence, but a cancellation
    # explicitly withdraws the native owner's material applicability.
    payload["imageCancellations"] = {}
    for name in ("v2_image_jobs", "v2_character_reference_proposals", "v2_art_reference_proposals"):
        table = Base.metadata.tables[name]
        payload["imageCancellations"][name] = sorted(session.scalars(select(table.c.id).where(
            table.c.project_id == project_id, table.c.state == "cancelled")))


def production_closure(session, project_id):
    """Text/canonical installation changes withdraw machine image applicability."""
    return material_closure(session, project_id, tables=tuple(name for name in MATERIAL_TABLES
        if name in {"v2_projects", "v2_stage_heads", "v2_gate_results", "v2_source_outline_heads",
            "v2_source_outline_section_map_heads", "v2_source_outline_graph_admissions", "v2_source_graph_identities",
            "v2_cast_heads", "v2_art_heads", "v2_script_heads", "v2_storyboard_review_heads",
            "v2_production_bridge_heads", "v2_production_bridge_admissions"}), include_cancellations=False)
