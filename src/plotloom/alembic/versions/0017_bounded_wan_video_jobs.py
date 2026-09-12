"""Persist P2's separate Wan ledger, frozen video jobs, and explicit reviews."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_bounded_wan_video_jobs"
down_revision = "0016_character_reference_identity_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_video_pilot_ledger",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("limit_seconds", sa.Integer(), nullable=False),
        sa.Column("reserved_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "v2_video_pilot_ledger_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ledger_id", sa.String(64), sa.ForeignKey("v2_video_pilot_ledger.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("video_job_id", sa.String(67), nullable=False),
        sa.Column("event", sa.String(48), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_video_pilot_ledger_events_ledger_created", "v2_video_pilot_ledger_events", ["ledger_id", "created_at"])
    op.create_table(
        "v2_video_jobs",
        sa.Column("id", sa.String(67), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("requested_seconds", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("provider_prediction_id", sa.String(200), nullable=True),
        sa.Column("output_uri", sa.Text(), nullable=True),
        sa.Column("output_hash", sa.String(64), nullable=True),
        sa.Column("observed", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("project_id", "idempotency_key", name="uq_v2_video_jobs_project_idempotency"),
    )
    op.create_index("ix_v2_video_jobs_project_created", "v2_video_jobs", ["project_id", "created_at"])
    op.create_table(
        "v2_video_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("video_job_id", sa.String(67), sa.ForeignKey("v2_video_jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewer", sa.String(160), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_video_reviews_job_created", "v2_video_reviews", ["video_job_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_v2_video_reviews_job_created", table_name="v2_video_reviews")
    op.drop_table("v2_video_reviews")
    op.drop_index("ix_v2_video_jobs_project_created", table_name="v2_video_jobs")
    op.drop_table("v2_video_jobs")
    op.drop_index("ix_v2_video_pilot_ledger_events_ledger_created", table_name="v2_video_pilot_ledger_events")
    op.drop_table("v2_video_pilot_ledger_events")
    op.drop_table("v2_video_pilot_ledger")
