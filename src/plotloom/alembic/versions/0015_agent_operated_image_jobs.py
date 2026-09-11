"""Persist frozen P1 production units, manual jobs, and delivery lineage."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0015_agent_operated_image_jobs"
down_revision = "0014_reviewed_visual_intent_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_production_units",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("approval_id", sa.String(36), sa.ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("storyboard_entity_revision_id", sa.String(36), sa.ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("shot_id", sa.String(100), nullable=False),
        sa.Column("scene_id", sa.String(100), nullable=False),
        sa.Column("storyboard_revision", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_production_units_project_id_created_at", "v2_production_units", ["project_id", "created_at"])
    op.create_table(
        "v2_image_jobs",
        sa.Column("id", sa.String(67), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("production_unit_id", sa.String(36), sa.ForeignKey("v2_production_units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("parent_job_id", sa.String(67), sa.ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("parent_candidate_asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_image_jobs_project_id_created_at", "v2_image_jobs", ["project_id", "created_at"])
    op.create_table(
        "v2_image_job_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(67), sa.ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("delivery_id", sa.String(128), nullable=True),
        sa.Column("manifest", sa.JSON(), nullable=True),
        sa.Column("manifest_hash", sa.String(64), nullable=True),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("diagnostic_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "delivery_id", name="uq_v2_image_job_delivery_identity"),
    )
    op.create_index("ix_v2_image_job_deliveries_job_id_created_at", "v2_image_job_deliveries", ["job_id", "created_at"])
    op.create_index(
        "uq_v2_image_job_final_delivery",
        "v2_image_job_deliveries",
        ["job_id"],
        unique=True,
        sqlite_where=sa.text("delivery_id IS NOT NULL"),
    )
    op.create_table(
        "v2_image_job_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(67), sa.ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("delivery_id", sa.String(36), sa.ForeignKey("v2_image_job_deliveries.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("output_filename", sa.String(180), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("delivery_id", "asset_id", name="uq_v2_image_job_candidate_delivery_asset"),
    )
    op.create_index("ix_v2_image_job_candidates_job_id_created_at", "v2_image_job_candidates", ["job_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_v2_image_job_candidates_job_id_created_at", table_name="v2_image_job_candidates")
    op.drop_table("v2_image_job_candidates")
    op.drop_index("uq_v2_image_job_final_delivery", table_name="v2_image_job_deliveries")
    op.drop_index("ix_v2_image_job_deliveries_job_id_created_at", table_name="v2_image_job_deliveries")
    op.drop_table("v2_image_job_deliveries")
    op.drop_index("ix_v2_image_jobs_project_id_created_at", table_name="v2_image_jobs")
    op.drop_table("v2_image_jobs")
    op.drop_index("ix_v2_production_units_project_id_created_at", table_name="v2_production_units")
    op.drop_table("v2_production_units")
