"""Persist accepted-art-bound F3B environment and prop studies."""

from alembic import op
import sqlalchemy as sa


revision = "0020_f3b_art_reference_studies"
down_revision = "0019_shot_video_candidate_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_art_reference_proposals",
        sa.Column("id", sa.String(67), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_type", sa.String(16), nullable=False),
        sa.Column("subject_id", sa.String(128), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_art_reference_proposals_project_created", "v2_art_reference_proposals", ["project_id", "created_at"])
    op.create_table(
        "v2_art_reference_proposal_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(67), sa.ForeignKey("v2_art_reference_proposals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("delivery_id", sa.String(128), nullable=True),
        sa.Column("manifest", sa.JSON(), nullable=True),
        sa.Column("manifest_hash", sa.String(64), nullable=True),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("diagnostic_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("proposal_id", "delivery_id", name="uq_v2_art_proposal_delivery_identity"),
    )
    op.create_index("uq_v2_art_proposal_final_delivery", "v2_art_reference_proposal_deliveries", ["proposal_id"], unique=True, sqlite_where=sa.text("delivery_id IS NOT NULL"))
    op.create_table(
        "v2_art_reference_proposal_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(67), sa.ForeignKey("v2_art_reference_proposals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("delivery_id", sa.String(36), sa.ForeignKey("v2_art_reference_proposal_deliveries.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("output_filename", sa.String(180), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("delivery_id", "asset_id", name="uq_v2_art_proposal_candidate_asset"),
    )


def downgrade() -> None:
    op.drop_table("v2_art_reference_proposal_candidates")
    op.drop_index("uq_v2_art_proposal_final_delivery", table_name="v2_art_reference_proposal_deliveries")
    op.drop_table("v2_art_reference_proposal_deliveries")
    op.drop_index("ix_v2_art_reference_proposals_project_created", table_name="v2_art_reference_proposals")
    op.drop_table("v2_art_reference_proposals")
