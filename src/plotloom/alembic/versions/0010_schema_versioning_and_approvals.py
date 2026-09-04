"""Version canonical payloads and add immutable review history.

Revision ID: 0010_v2_schema_approvals
Revises: 0009_v2_work_unit_repair_scopes
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_v2_schema_approvals"
down_revision = "0009_v2_work_unit_repair_scopes"
branch_labels = None
depends_on = None


def _add_required_schema_version(table_name: str) -> None:
    """Backfill only the new scalar column, leaving historical JSON untouched.

    SQLite requires a table rebuild to make an added column non-nullable.  The
    batch operation copies rows with SQL ``INSERT .. SELECT``; it does not
    decode/re-encode any JSON column.  The explicit UPDATE intentionally
    targets only ``schema_version`` so immutable payload, seal, and hash text
    remain byte-for-byte historical evidence.
    """

    op.add_column(table_name, sa.Column("schema_version", sa.Integer(), nullable=True))
    op.execute(sa.text(f"UPDATE {table_name} SET schema_version = 1 WHERE schema_version IS NULL"))
    with op.batch_alter_table(table_name) as batch:
        batch.alter_column("schema_version", existing_type=sa.Integer(), nullable=False)


def upgrade() -> None:
    _add_required_schema_version("v2_entity_revisions")
    _add_required_schema_version("v2_stage_heads")
    # Sealed aggregates are also stage payloads.  Without an explicit version,
    # a repair/planning read could accidentally apply V2 defaults to V1
    # evidence.  Backfilling this scalar remains payload-byte preserving.
    _add_required_schema_version("v2_sealed_stage_aggregates")

    op.create_table(
        "v2_gate_results",
        sa.Column("id", sa.String(length=256), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("v2_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_revision_id",
            sa.String(length=36),
            sa.ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("evaluation_input_hash", sa.String(length=64), nullable=False),
        sa.Column("gate_set_version", sa.String(length=128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("gate_id", sa.Text(), nullable=False),
        sa.Column("gate_version", sa.String(length=128), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("entity_path", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("entity_revision_id", "gate_set_version", "gate_id"),
        sa.UniqueConstraint("entity_revision_id", "gate_set_version", "sequence"),
    )
    op.create_index("ix_v2_gate_results_project_id", "v2_gate_results", ["project_id"])
    op.create_index(
        "ix_v2_gate_results_entity_revision_id", "v2_gate_results", ["entity_revision_id"]
    )

    op.create_table(
        "v2_approval_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("v2_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_revision_id",
            sa.String(length=36),
            sa.ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=128), nullable=False),
        sa.Column("subject_revision", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("canonical_input_revisions", sa.JSON(), nullable=False),
        sa.Column("gate_set_version", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reviewer", sa.String(length=256), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_v2_approval_decisions_project_id_created_at",
        "v2_approval_decisions",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_v2_approval_decisions_entity_revision_id",
        "v2_approval_decisions",
        ["entity_revision_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_v2_approval_decisions_entity_revision_id", table_name="v2_approval_decisions"
    )
    op.drop_index(
        "ix_v2_approval_decisions_project_id_created_at", table_name="v2_approval_decisions"
    )
    op.drop_table("v2_approval_decisions")
    op.drop_index("ix_v2_gate_results_entity_revision_id", table_name="v2_gate_results")
    op.drop_index("ix_v2_gate_results_project_id", table_name="v2_gate_results")
    op.drop_table("v2_gate_results")
    with op.batch_alter_table("v2_stage_heads") as batch:
        batch.drop_column("schema_version")
    with op.batch_alter_table("v2_entity_revisions") as batch:
        batch.drop_column("schema_version")
    with op.batch_alter_table("v2_sealed_stage_aggregates") as batch:
        batch.drop_column("schema_version")
