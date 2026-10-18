"""Passing canonical gate facts, scoped to an exact SQL mutation snapshot."""
from sqlalchemy import select
from ...project_storage.proof_scope import sql_scalar
from ..schema import GateResultRow


def gates_pass(session, codecs, revision_id, *, gate_set_version=None, content_hash=None):
    def calculate():
        query = select(GateResultRow).where(GateResultRow.entity_revision_id == revision_id)
        if gate_set_version is not None:
            query = query.where(GateResultRow.gate_set_version == gate_set_version)
        rows = session.scalars(query).all()
        return bool(rows) and all((content_hash is None or row.content_hash == content_hash)
            and codecs.gate_result(row).passed for row in rows)
    return sql_scalar(session, "passing-canonical-gates", (revision_id, gate_set_version, content_hash), calculate)
