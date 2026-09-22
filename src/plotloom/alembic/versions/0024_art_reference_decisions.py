"""Persist explicit F3B environment/prop reference decisions."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0024_art_reference_decisions"
down_revision = "0023_character_imported_appearances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_art_reference_decision_states",
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("subject_type", sa.String(16), primary_key=True),
        sa.Column("subject_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_decision_id", sa.String(36), sa.ForeignKey("v2_art_reference_decisions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "v2_art_reference_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_type", sa.String(16), nullable=False),
        sa.Column("subject_id", sa.String(128), nullable=False),
        sa.Column("reference_revision", sa.Integer(), nullable=False),
        sa.Column("accepted_art_revision", sa.Integer(), nullable=False),
        sa.Column("accepted_art_hash", sa.String(64), nullable=False),
        sa.Column("subject", sa.JSON(), nullable=False),
        sa.Column("subject_hash", sa.String(64), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset_hash", sa.String(64), nullable=False),
        sa.Column("proposal_id", sa.String(67), sa.ForeignKey("v2_art_reference_proposals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("v2_art_reference_proposal_candidates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_art_reference_decisions_project_subject", "v2_art_reference_decisions", ["project_id", "subject_type", "subject_id", "reference_revision"])


def downgrade() -> None:
    op.drop_index("ix_v2_art_reference_decisions_project_subject", table_name="v2_art_reference_decisions")
    op.drop_table("v2_art_reference_decision_states")
    op.drop_table("v2_art_reference_decisions")
